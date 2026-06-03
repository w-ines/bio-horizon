"""
Main bio-horizon Deep Agent - Biomedical Intelligence Agent.
Replaces smolagents CodeAgent with LangChain Deep Agents.
"""

import logging
import os
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# In-memory cache — fast access during a session
_memory_cache: dict = {}


def create_biomedical_agent(
    tools: Optional[List] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.3,
    max_steps: int = 7,
    conversation_id: Optional[str] = None,
    stream_callback=None,
):
    """
    Create the main bio-horizon Deep Agent with biomedical tools.
    
    Args:
        tools: List of LangChain tools (if None, uses default tools)
        model_name: LLM model name (defaults to env OPEN_AI_MODEL)
        temperature: LLM temperature (default: 0.3 for focused responses)
        max_steps: Maximum agent steps (default: 5)
        
    Returns:
        SimpleAgentExecutor with conversation memory
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
    from langchain_core.runnables import RunnablePassthrough
    
    # Import available tools
    from deepagents.tools.knowledge.rag_tool import retrieve_knowledge

    from deepagents.tools.biomedical.pubmed_tool import pubmed_search
    from deepagents.tools.biomedical.corpus_ingestion_tool import (
        create_corpus_ingestion_job,
        check_ingestion_job_status
    )
    from deepagents.tools.biomedical.search_articles_tool import search_ingested_articles

    # Configure LLM
    model_name = model_name or os.getenv("OPEN_AI_MODEL", "gpt-4o")
    base_url = os.getenv("BASE_URL", "https://openrouter.ai/api/v1")
    api_key = os.getenv("OPEN_ROUTER_KEY") or os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise RuntimeError(
            "No API key found. Set OPEN_ROUTER_KEY or OPENAI_API_KEY environment variable."
        )
    
    llm = ChatOpenAI(
        model=model_name,
        temperature=temperature,
        openai_api_base=base_url,
        openai_api_key=api_key,
    )
    
    # Default tools if none provided
    if tools is None:
        tools = [
            pubmed_search,
            retrieve_knowledge,
            create_corpus_ingestion_job,
            check_ingestion_job_status,
            search_ingested_articles,
        ]
    
    # bind_tools() for structured function calling (GPT-4o-mini supports this)
    llm_with_tools = llm.bind_tools(tools)
    
    # Create a simple agent executor wrapper with conversation memory
    class SimpleAgentExecutor:
        def __init__(self, llm, tools, max_iterations=7, conversation_id=None, stream_callback=None):
            self.llm = llm
            self.tools = {tool.name: tool for tool in tools}
            self.max_iterations = max_iterations
            self.conversation_id = conversation_id or "default"
            self.stream_callback = stream_callback
            
            # Load history from Supabase into cache on first access
            if self.conversation_id not in _memory_cache:
                self._hydrate_from_persistence()
            
            self.system_prompt = """You are Bio-Horizon, an intelligent biomedical research assistant.
You MUST be proactive: when the user asks a question, USE YOUR TOOLS immediately to find the answer. NEVER ask the user to reformulate or search themselves.

## Workflow
1. **Simple question** about a biomedical topic: call pubmed_search to get recent articles, then synthesize a clear answer.
2. **Large-scale analysis** ("analyze all literature", "ingest corpus"): call create_corpus_ingestion_job with processing_mode="full" (NER+KG via PubTator3, ~1-3 min).
3. **Explore ingested data**: call search_ingested_articles after a job completes.
4. **Local knowledge**: call retrieve_knowledge to search uploaded documents and Knowledge Graph.
5. **Check job progress**: call check_ingestion_job_status with the job_id.

## Rules
- ALWAYS answer in English by default, unless the user explicitly requests another language.
- Cite sources with [PMID: ...] format.
- Be precise: medical information requires accuracy.
- Never say \"I couldn't find information\" without having attempted at least one tool call.
- If a tool returns no results, rephrase the query and retry once.
- If the question is clearly outside the biomedical domain and no tool is relevant, answer directly from your general knowledge. Do NOT force a tool call."""
        

        def _hydrate_from_persistence(self):
            """Load conversation history from Supabase into in-memory cache."""
            try:
                from deepagents.memory import load_history
                rows = load_history(conversation_id=self.conversation_id, limit=20)
                msgs = []
                for r in rows:
                    if r.role == "user":
                        msgs.append(HumanMessage(content=r.content))
                    elif r.role == "assistant":
                        msgs.append(AIMessage(content=r.content))
                _memory_cache[self.conversation_id] = msgs
                if msgs:
                    logger.info("[memory] Loaded %d messages from persistence for %s", len(msgs), self.conversation_id)
            except Exception as e:
                logger.debug("[memory] Could not hydrate from persistence: %s", e)
                _memory_cache[self.conversation_id] = []

        def _persist_message(self, role: str, content: str):
            """Dual-write: save to in-memory cache + Supabase."""
            # In-memory
            msg = HumanMessage(content=content) if role == "user" else AIMessage(content=content)
            _memory_cache.setdefault(self.conversation_id, []).append(msg)
            # Supabase (async-safe, non-blocking on failure)
            try:
                from deepagents.memory import save_message
                save_message(conversation_id=self.conversation_id, role=role, content=content)
            except Exception as e:
                logger.debug("[memory] Supabase save skipped: %s", e)

        def invoke(self, input_dict):
            """Execute the agent with structured tool calling loop."""
            user_input = input_dict.get("input", "")
            
            # Build messages with conversation history
            messages = [HumanMessage(content=self.system_prompt)]
            
            # Add conversation history (last 10 messages to avoid context overflow)
            history = _memory_cache.get(self.conversation_id, [])
            if history:
                messages.extend(history[-10:])
            
            # Add current user message
            messages.append(HumanMessage(content=user_input))
            
            for iteration in range(self.max_iterations):
                # Stream thought
                if self.stream_callback:
                    self.stream_callback({"type": "thought", "content": f" Thinking... (step {iteration + 1}/{self.max_iterations})"})
                
                # Call LLM with bound tools
                response = self.llm.invoke(messages)
                messages.append(response)
                
                # Check for structured tool calls
                tool_calls = response.tool_calls or []
                
                if not tool_calls:
                    # No tool calls — this is the final answer
                    answer = response.content or ""
                    if not answer.strip():
                        logger.warning("[agent] Empty response at step %d", iteration + 1)
                        messages.append(HumanMessage(content="Please respond to the user's question. Use your tools if needed."))
                        continue
                    
                    logger.info("[agent] Final answer at step %d (length=%d)", iteration + 1, len(answer))
                    
                    if self.stream_callback:
                        self.stream_callback({"type": "answer", "content": answer})
                    
                    # Dual-write: in-memory + Supabase
                    self._persist_message("user", user_input)
                    self._persist_message("assistant", answer)
                    return {"output": answer}
                
                # Execute tool calls
                logger.info("[agent] Step %d: %d tool call(s): %s", iteration + 1, len(tool_calls), [tc['name'] for tc in tool_calls])
                
                for tool_call in tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_id = tool_call.get("id", f"call_{iteration}")
                    
                    if self.stream_callback:
                        self.stream_callback({"type": "action", "content": f" Using tool: {tool_name}", "args": str(tool_args)[:100]})
                    
                    if tool_name in self.tools:
                        try:
                            result = self.tools[tool_name].invoke(tool_args)
                            result_str = str(result)
                            
                            if self.stream_callback:
                                preview = result_str[:300] + "..." if len(result_str) > 300 else result_str
                                self.stream_callback({"type": "observation", "content": f" Tool result received", "preview": preview})
                            
                            messages.append(ToolMessage(content=result_str, tool_call_id=tool_id))
                        except Exception as e:
                            logger.error("[agent] Tool %s error: %s", tool_name, e)
                            if self.stream_callback:
                                self.stream_callback({"type": "error", "content": f" Tool error: {str(e)}"})
                            messages.append(ToolMessage(content=f"Error: {str(e)}", tool_call_id=tool_id))
                    else:
                        messages.append(ToolMessage(content=f"Error: Tool '{tool_name}' not found.", tool_call_id=tool_id))
            
            # Max iterations reached
            final_response = "I apologize, but I reached the maximum number of steps. Please try rephrasing your question."
            self._persist_message("user", user_input)
            self._persist_message("assistant", final_response)
            return {"output": final_response}
    
    return SimpleAgentExecutor(
        llm_with_tools, tools,
        max_iterations=max_steps,
        conversation_id=conversation_id,
        stream_callback=stream_callback,
    )


def create_simple_rag_agent(
    model_name: Optional[str] = None,
    temperature: float = 0.3,
):
    """
    Create a simple RAG-only agent (no planning, just retrieval + answer).
    Useful for quick queries that don't need complex reasoning.
    
    Args:
        model_name: LLM model name
        temperature: LLM temperature
        
    Returns:
        Simple agent for RAG queries
    """
    from langchain_openai import ChatOpenAI
    from langchain.agents import create_tool_calling_agent, AgentExecutor
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from deepagents.tools.knowledge.rag_tool import retrieve_knowledge
    
    # Configure LLM
    model_name = model_name or os.getenv("OPEN_AI_MODEL", "gpt-4o")
    base_url = os.getenv("BASE_URL", "https://openrouter.ai/api/v1")
    api_key = os.getenv("OPEN_ROUTER_KEY") or os.getenv("OPENAI_API_KEY")
    
    llm = ChatOpenAI(
        model=model_name,
        temperature=temperature,
        openai_api_base=base_url,
        openai_api_key=api_key,
    )
    
    # Simple prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful medical assistant. Use retrieve_knowledge to search documents and answer questions.
Always cite sources using [Source N] format."""),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    # Create agent
    tools = [retrieve_knowledge]
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    return agent_executor
