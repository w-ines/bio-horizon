"""LangChain tool wrapper for PubMed search.

This wrapper allows Deep Agents to search PubMed articles.
It calls the core_tools.pubmed_tool logic.
"""

from langchain.tools import tool

from core_tools.pubmed_tool import search_pubmed


@tool
def pubmed_search(
    query: str,
    max_results: int = 10,
    sort_by: str = "relevance"
) -> str:
    """Search PubMed for biomedical articles.
    
    Args:
        query: Search query (natural language or PubMed syntax)
        max_results: Maximum number of results to return (default: 10)
        sort_by: Sort order - "relevance" or "date" (default: "relevance")
    
    Returns:
        JSON string with list of articles (PMID, title, abstract, authors, journal, date)
    
    Examples:
        - "Alzheimer disease treatment 2024"
        - "GLP-1 agonists neuroprotection"
        - "BRCA1 mutations breast cancer"
    """
    import json
    sort_mapping = {
        "relevance": "relevance",
        "date": "pub_date",
        "pub_date": "pub_date"
    }

    if sort_by not in sort_mapping:
        return json.dumps({
            "error": f"Invalid sort_by value: {sort_by}. Use 'relevance' or 'date'."
        }, ensure_ascii=False)

    try:
        results = search_pubmed(
            query=query,
            max_results=max_results,
            sort=sort_mapping[sort_by]
        )
        
        # Format results for agent
        formatted = []
        for article in results.get("articles", []):
            formatted.append({
                "pmid": article.get("pmid"),
                "title": article.get("title"),
                "abstract": article.get("abstract", "")[:500],  # Truncate for context
                "journal": article.get("journal"),
                "date": article.get("pub_date"),
                "authors": article.get("authors", [])[:3]  # First 3 authors
            })
        
        return json.dumps({
            "count": len(formatted),
            "articles": formatted
        }, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)