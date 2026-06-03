"""
Conversational Retrieval Chain with Knowledge Graph integration.
Uses LangChain Expression Language (LCEL) for composable chains.
"""

from typing import List, Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

from rag.retriever import get_retriever
from deepagents.memory import load_history, save_message


def format_docs(docs: List[Any]) -> str:
    """Format retrieved documents for context."""
    formatted = []
    for i, doc in enumerate(docs, 1):
        content = doc.page_content
        metadata = doc.metadata or {}
        
        # Add KG context if available
        kg_entities = metadata.get("kg_entities", [])
        kg_relationships = metadata.get("kg_relationships", [])
        
        source_info = metadata.get("filename", metadata.get("source", f"Document {i}"))
        formatted.append(f"[Source {i}: {source_info}]\n{content}")
        
        # Add KG enrichment info
        if kg_entities:
            entity_names = [e["label"] for e in kg_entities[:3]]
            formatted.append(f"Related entities: {', '.join(entity_names)}")
        
        if kg_relationships:
            rel_summary = f"{len(kg_relationships)} relationships found in Knowledge Graph"
            formatted.append(rel_summary)
        
        formatted.append("\n---\n")
    
    return "\n".join(formatted)


def format_chat_history(messages: List[Dict[str, str]]) -> List[Any]:
    """Convert stored messages to LangChain format."""
    formatted = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        
        if role == "user":
            formatted.append(HumanMessage(content=content))
        elif role == "assistant":
            formatted.append(AIMessage(content=content))
    
    return formatted


def create_rag_chain(
    *,
    conversation_id: str,
    top_k: int = 5,
    enable_kg_enrichment: bool = True,
    kg_weight: float = 0.3,
    model_name: Optional[str] = None,
    temperature: float = 0.3
):
    """
    Create a conversational RAG chain with KG enrichment.
    
    Args:
        conversation_id: Conversation ID for memory
        top_k: Number of documents to retrieve
        enable_kg_enrichment: Enable Knowledge Graph enrichment
        kg_weight: Weight for KG score in hybrid ranking
        model_name: LLM model name (defaults to env OPEN_AI_MODEL)
        temperature: LLM temperature
    
    Returns:
        Runnable chain
    """
    import os
    
    # Get retriever with KG enrichment
    retriever = get_retriever(
        top_k=top_k,
        enable_kg_enrichment=enable_kg_enrichment,
        kg_weight=kg_weight
    )
    
    # Configure LLM
    model_name = model_name or os.getenv("OPEN_AI_MODEL", "gpt-3.5-turbo")
    base_url = os.getenv("BASE_URL", "http://localhost:11434/v1")
    api_key = os.getenv("OPENAI_API_KEY", "not-needed")
    
    llm = ChatOpenAI(
        model=model_name,
        temperature=temperature,
        openai_api_base=base_url,
        openai_api_key=api_key
    )
    
    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful medical assistant with access to a knowledge base and a medical Knowledge Graph.

Use the provided context to answer questions accurately. When answering:
1. Cite sources using [Source N] format
2. Use Knowledge Graph relationships to provide deeper insights
3. If the context doesn't contain the answer, say so clearly
4. For medical information, be precise and cite evidence

Context from documents and Knowledge Graph:
{context}

Previous conversation:
{chat_history}"""),
        ("user", "{question}")
    ])
    
    # Load conversation history
    def get_chat_history(_):
        """Load chat history from memory."""
        messages = load_history(conversation_id=conversation_id, limit=10)
        return format_chat_history(messages)
    
    # Create the chain using LCEL
    chain = (
        {
            "context": lambda x: format_docs(retriever.get_relevant_documents(x["question"])),
            "chat_history": RunnableLambda(get_chat_history),
            "question": RunnablePassthrough()
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return chain


def query_rag(
    question: str,
    *,
    conversation_id: str,
    top_k: int = 5,
    enable_kg_enrichment: bool = True,
    save_to_memory: bool = True
) -> str:
    """
    Query the RAG system with KG enrichment.
    
    Args:
        question: User question
        conversation_id: Conversation ID for memory
        top_k: Number of documents to retrieve
        enable_kg_enrichment: Enable Knowledge Graph enrichment
        save_to_memory: Save question and answer to memory
    
    Returns:
        Answer string
    """
    # Create chain
    chain = create_rag_chain(
        conversation_id=conversation_id,
        top_k=top_k,
        enable_kg_enrichment=enable_kg_enrichment
    )
    
    # Get answer
    answer = chain.invoke({"question": question})
    
    # Save to memory
    if save_to_memory:
        save_message(
            conversation_id=conversation_id,
            role="user",
            content=question
        )
        save_message(
            conversation_id=conversation_id,
            role="assistant",
            content=answer
        )
    
    return answer


# Example usage
if __name__ == "__main__":
    # Test the RAG chain
    result = query_rag(
        question="What are the side effects of aspirin?",
        conversation_id="test_conversation",
        enable_kg_enrichment=True
    )
    
    print("Answer:", result)