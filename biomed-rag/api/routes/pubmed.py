"""PubMed search endpoints."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from api.schemas.pubmed import PubMedSearchRequest

router = APIRouter()


@router.post("/search")
async def pubmed_search(request: PubMedSearchRequest):
    """Search PubMed with advanced filters."""
    try:
        from core_tools.pubmed_tool import PubMedSearchEngine
        engine = PubMedSearchEngine()
        search_result = engine.search(
            query=request.query,
            max_results=request.max_results,
            start=request.start,
            sort=request.sort,
            mindate=request.mindate,
            maxdate=request.maxdate,
            publication_types=request.publication_types,
            journals=request.journals,
            language=request.language if request.language else None,
            species=request.species,
            use_cache=True,
        )
        result = search_result.get("esearchresult", {})
        pmids = result.get("idlist", []) or []
        total = int(result.get("count", 0) or 0)

        articles = []
        if request.fetch_details and pmids:
            articles = engine.fetch_articles(pmids)

        return {
            "provider": "ncbi",
            "query": request.query,
            "total": total,
            "start": request.start,
            "max_results": request.max_results,
            "pmids": pmids,
            "articles": articles,
        }
    except Exception as e:
        print(f"[pubmed/search] error: {e}")
        import traceback; traceback.print_exc()
        return JSONResponse({"error": str(e), "pmids": [], "articles": [], "total": 0}, status_code=500)
