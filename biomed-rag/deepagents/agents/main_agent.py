"""
Main bio-horizon Deep Agent - Biomedical Intelligence Agent.
Replaces smolagents CodeAgent with LangChain Deep Agents.
"""

import json as _json
import logging
import os
import re
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
    max_steps: int = 5,
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
            # More tools will be added as they are migrated
        ]
    
    # Bind tools to LLM
    llm_with_tools = llm.bind_tools(tools)
    
    # Create a simple agent executor wrapper with conversation memory
    class SimpleAgentExecutor:
        def __init__(self, llm_with_tools, tools, max_iterations=5, conversation_id=None, stream_callback=None):
            self.llm = llm_with_tools
            self.tools = {tool.name: tool for tool in tools}
            self.max_iterations = max_iterations
            self.conversation_id = conversation_id or "default"
            self.stream_callback = stream_callback
            
            # Load history from Supabase into cache on first access
            if self.conversation_id not in _memory_cache:
                self._hydrate_from_persistence()
            
            self.system_prompt = """You are Bio-Horizon, an intelligent biomedical research assistant.
You MUST be proactive: when the user asks a question, USE YOUR TOOLS immediately to find the answer. NEVER ask the user to reformulate or search themselves.

## Available tools
1. **pubmed_search(query, max_results, sort_by)** — Search PubMed for recent biomedical literature. Use this for any question about treatments, drugs, diseases, clinical trials, or emerging research.
2. **retrieve_knowledge(query, top_k, enable_kg)** — Search the local knowledge base of uploaded documents and the Knowledge Graph.

## Workflow (follow this order strictly)
1. **Check conversation history**: Read ALL previous messages. If the user's question (or a very similar one) was already answered, reuse that answer directly. Do NOT call any tool.
2. **Follow-up on existing results**: If the user asks about details, comparisons, or sub-questions about results already in the conversation, answer from context. Only call a tool if you need specific NEW data not present in the history.
3. **New topic only**: If the question is about something NOT covered in the conversation history, THEN call pubmed_search (with a well-crafted English query, sort_by="date" for recent topics) AND retrieve_knowledge.
4. Synthesize results into a clear, evidence-based answer with citations.

## Rules
- Never repeat a tool call if the answer is already in the conversation.
- Never say "I couldn't find information" without having attempted at least one tool call on a NEW topic.
- Cite sources with [Source N] or [PMID: ...] format.
- Answer in the same language as the user's question.
- Be precise: medical information requires accuracy.
- If a tool returns no results, rephrase the query and retry once."""
        
        @staticmethod
        def _parse_text_tool_calls(content: str) -> list:
            """
            Fallback parser: detect text-based function calls in LLM output.
            Handles patterns like: <function=tool_name>{"arg": "val"}
            Returns list of dicts compatible with tool_call format.
            """
            if not content:
                return []
            pattern = r'<function=([^>]+)>(\{.*?\})'
            matches = re.findall(pattern, content, re.DOTALL)
            calls = []
            for name, args_str in matches:
                try:
                    args = _json.loads(args_str)
                    calls.append({
                        "name": name.strip(),
                        "args": args,
                        "id": f"text_call_{len(calls)}",
                    })
                except _json.JSONDecodeError:
                    continue
            return calls

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
            """Execute the agent with tool calling loop."""
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
                
                # Call LLM
                response = self.llm.invoke(messages)
                messages.append(response)
                
                # Check if LLM wants to use tools
                tool_calls = response.tool_calls or []
                
                # Fallback: parse text-based tool calls if model didn't use structured format
                if not tool_calls and response.content:
                    text_calls = self._parse_text_tool_calls(response.content)
                    if text_calls:
                        logger.info("[agent] Detected %d text-based tool call(s), converting", len(text_calls))
                        tool_calls = text_calls
                
                if not tool_calls:
                    # No tool calls, return final answer
                    answer = response.content or ""
                    if not answer.strip():
                        logger.warning("[agent] LLM returned empty content at step %d", iteration + 1)
                        continue  # Retry instead of returning empty
                    
                    if self.stream_callback:
                        self.stream_callback({"type": "answer", "content": answer})
                    
                    # Dual-write: in-memory + Supabase
                    self._persist_message("user", user_input)
                    self._persist_message("assistant", answer)
                    return {"output": answer}
                
                # Execute tool calls
                for tool_call in tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    # Stream action
                    if self.stream_callback:
                        args_preview = str(tool_args)[:100]
                        self.stream_callback({"type": "action", "content": f" Using tool: {tool_name}", "args": args_preview})
                    
                    if tool_name in self.tools:
                        try:
                            # Execute tool
                            tool_result = self.tools[tool_name].invoke(tool_args)
                            
                            # Stream observation with detailed preview
                            if self.stream_callback:
                                result_str = str(tool_result)
                                # Get first 300 chars for preview
                                result_preview = result_str[:300] + "..." if len(result_str) > 300 else result_str
                                # Count results if it's a list/array
                                result_count = ""
                                if isinstance(tool_result, (list, tuple)):
                                    result_count = f" ({len(tool_result)} items)"
                                elif isinstance(tool_result, dict) and "documents" in tool_result:
                                    result_count = f" ({len(tool_result.get('documents', []))} documents)"
                                
                                self.stream_callback({
                                    "type": "observation", 
                                    "content": f" Tool result received{result_count}",
                                    "preview": result_preview
                                })
                            
                            messages.append(
                                ToolMessage(
                                    content=str(tool_result),
                                    tool_call_id=tool_call["id"]
                                )
                            )
                        except Exception as e:
                            if self.stream_callback:
                                self.stream_callback({"type": "error", "content": f" Tool error: {str(e)}"})
                            
                            messages.append(
                                ToolMessage(
                                    content=f"Error executing tool: {str(e)}",
                                    tool_call_id=tool_call["id"]
                                )
                            )
            
            # Max iterations reached
            final_response = "I apologize, but I reached the maximum number of steps. Please try rephrasing your question."
            
            # Dual-write even on max iterations
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
