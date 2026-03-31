"""
PubMed Search Tool for Medical Literature Retrieval

Uses NCBI E-utilities API (ESearch + EFetch).
For bulk ingestion, use pubmed_corpus.py instead.

Environment variables (.env):
    NCBI_API_KEY        - NCBI API key (increases rate limit from 3 to 10 req/sec)
    PUBMED_API_KEY      - Fallback api key name if you stored the NCBI key under this name
    NCBI_EMAIL          - Your email (recommended by NCBI)
    NCBI_TOOL           - Tool name identifier (default: med-assist)
    NCBI_BASE_URL       - NCBI base URL (default: https://eutils.ncbi.nlm.nih.gov/entrez/eutils)
    PUBMED_USE_NCBI     - Toggle to use NCBI API (default: true)
"""

import logging
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

from core_tools.pubmed_utils import (
    get_env,
    get_ncbi_base_url,
    add_ncbi_credentials,
    CacheManager,
    parse_efetch_xml,
    fetch_articles_xml,
)

load_dotenv()
logger = logging.getLogger(__name__)


# Note: CacheManager and other utilities are now in pubmed_utils.py


# =============================================================================
# PubMed Search Engine Class
# ============================================================================

class PubMedSearchEngine:
    """PubMed search engine with advanced filtering and caching."""
    
    def __init__(self, email: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize PubMed search engine.
        
        Args:
            email: NCBI email (recommended by NCBI)
            api_key: NCBI API key (increases rate limit to 10 req/s)
        """
        self.email = email or get_env("NCBI_EMAIL")
        self.api_key = api_key or get_env("NCBI_API_KEY")
        self.tool_name = get_env("NCBI_TOOL", "med-assist")
        self.base_url = get_ncbi_base_url()
        self.cache = CacheManager()
    
    def _add_ncbi_credentials(self, params: Dict[str, Any]) -> None:
        """Add NCBI credentials to request parameters (in-place)."""
        if self.email:
            params["email"] = self.email
        if self.tool_name:
            params["tool"] = self.tool_name
        if self.api_key:
            params["api_key"] = self.api_key
    
    def _build_advanced_query(
        self,
        base_query: str,
        publication_types: Optional[List[str]] = None,
        journals: Optional[List[str]] = None,
        language: Optional[str] = None,
        species: Optional[List[str]] = None,
    ) -> str:
        """
        Build advanced Entrez query with filters.
        
        Args:
            base_query: Base search query
            publication_types: Filter by publication type (e.g., ["Clinical Trial", "Meta-Analysis"])
            journals: Filter by journal names (e.g., ["Nature", "Science"])
            language: Filter by language (e.g., "eng")
            species: Filter by species (e.g., ["Humans", "Mice"])
        
        Returns:
            Advanced Entrez query string
        """
        parts = [base_query]
        
        # Publication types filter
        if publication_types:
            # Map common names to PubMed publication types
            type_mapping = {
                "Clinical Trial": "Clinical Trial",
                "Meta-Analysis": "Meta-Analysis",
                "Review": "Review",
                "Systematic Review": "Systematic Review",
                "RCT": "Randomized Controlled Trial",
                "Randomized Controlled Trial": "Randomized Controlled Trial",
                "Case Reports": "Case Reports",
                "Research Article": "Journal Article",
            }
            mapped_types = [type_mapping.get(pt, pt) for pt in publication_types]
            type_query = " OR ".join([f'"{t}"[Publication Type]' for t in mapped_types])
            parts.append(f"({type_query})")
        
        # Journals filter
        if journals:
            journal_query = " OR ".join([f'"{j}"[Journal]' for j in journals])
            parts.append(f"({journal_query})")
        
        # Language filter
        if language:
            parts.append(f"{language}[Language]")
        
        # Species filter
        if species:
            species_query = " OR ".join([f'"{s}"[Organism]' for s in species])
            parts.append(f"({species_query})")
        
        return " AND ".join(parts)
    
    def search(
        self,
        query: str,
        max_results: int = 20,
        start: int = 0,
        sort: str = "relevance",
        mindate: str = "",
        maxdate: str = "",
        publication_types: Optional[List[str]] = None,
        journals: Optional[List[str]] = None,
        language: Optional[str] = None,
        species: Optional[List[str]] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Search PubMed with advanced filters.
        
        Args:
            query: Base search query
            max_results: Maximum results to return (1-10000)
            start: Starting index for pagination
            sort: Sort order (relevance, pub_date, Author, JournalName)
            mindate: Minimum publication date (YYYY or YYYY/MM or YYYY/MM/DD)
            maxdate: Maximum publication date
            publication_types: Filter by publication types
            journals: Filter by journal names
            language: Filter by language code (e.g., "eng")
            species: Filter by species/organism
            use_cache: Use Redis cache if available
        
        Returns:
            Dict with PMIDs and metadata
        """
        # Build advanced query
        advanced_query = self._build_advanced_query(
            query, publication_types, journals, language, species
        )
        
        # Check cache
        cache_key = None
        if use_cache:
            cache_key = self.cache.make_key(
                "pubmed_search",
                advanced_query,
                max_results,
                start,
                sort,
                mindate,
                maxdate,
            )
            cached = self.cache.get(cache_key)
            if cached:
                import json
                logger.info(f"💾 Cache hit for query: {query[:50]}...")
                return json.loads(cached)
        
        # Execute search
        url = f"{self.base_url}/esearch.fcgi"
        
        params = {
            "db": "pubmed",
            "term": advanced_query,
            "retmode": "json",
            "retmax": max(1, min(int(max_results), 10000)),
            "retstart": max(0, int(start)),
        }
        
        if sort:
            params["sort"] = sort
        
        if mindate or maxdate:
            params["datetype"] = "pdat"
            if mindate:
                params["mindate"] = mindate
            if maxdate:
                params["maxdate"] = maxdate
        
        # Add NCBI credentials
        self._add_ncbi_credentials(params)
        
        logger.info(f"🔍 PubMed search: {advanced_query[:80]}... (max={max_results})")
        
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        result = response.json()
        
        # Cache result
        if use_cache and cache_key:
            import json
            self.cache.set(cache_key, json.dumps(result), ttl=86400)  # 24h
        
        return result
    
    def fetch_articles(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch article details for given PMIDs.
        
        Args:
            pmids: List of PubMed IDs
        
        Returns:
            List of article dictionaries with metadata
        """
        if not pmids:
            return []
        
        # Batch fetch (max 200 per request)
        xml_data = fetch_articles_xml(pmids[:200])
        articles = parse_efetch_xml(xml_data)
        
        return articles



# =============================================================================
# Main search_pubmed tool
# =============================================================================

def search_pubmed(
    query: str,
    max_results: int = 20,
    start: int = 0,
    sort: str = "relevance",
    mindate: str = "",
    maxdate: str = "",
    fetch_details: bool = True,
    publication_types: Optional[List[str]] = None,
    journals: Optional[List[str]] = None,
    language: str = "",
    species: Optional[List[str]] = None,
) -> dict:
    """
    Search PubMed for medical literature with advanced filtering.
    
    Args:
        query: Search query (supports PubMed syntax: MeSH terms, [Title/Abstract], etc.)
               Examples: "alzheimer treatment", "COVID-19[Title] AND vaccine[MeSH]"
        max_results: Maximum number of results to return (1-10000, default: 20)
        start: Starting index for pagination (default: 0)
        sort: Sort order - "relevance", "pub_date", "Author", "JournalName"
        mindate: Minimum publication date (format: YYYY or YYYY/MM or YYYY/MM/DD)
        maxdate: Maximum publication date (format: YYYY or YYYY/MM or YYYY/MM/DD)
        fetch_details: If True, fetch article details (title, abstract, authors)
        publication_types: Filter by publication types (e.g., ["Clinical Trial", "Meta-Analysis", "Review", "RCT"])
        journals: Filter by journal names (e.g., ["Nature", "Science", "Cell"])
        language: Filter by language code (e.g., "eng" for English)
        species: Filter by species/organism (e.g., ["Humans", "Mice"])
    
    Returns:
        dict: {
            "provider": "ncbi",
            "query": str,
            "total": int,
            "start": int,
            "max_results": int,
            "pmids": list[str],
            "articles": list[dict],  # If fetch_details=True
            "error": str  # If error occurred
        }
    
    Examples:
        >>> search_pubmed("alzheimer treatment", max_results=10)
        >>> search_pubmed("COVID-19 vaccine", mindate="2023", maxdate="2024")
        >>> search_pubmed("cancer immunotherapy", publication_types=["Clinical Trial", "RCT"])
        >>> search_pubmed("CRISPR", journals=["Nature", "Science"], language="eng")
        >>> search_pubmed("diabetes", species=["Humans"], publication_types=["Meta-Analysis"])
    """
    use_ncbi_setting = get_env("PUBMED_USE_NCBI", "true").lower().strip()
    if use_ncbi_setting in {"false", "0", "no"}:
        return {
            "error": "PUBMED_USE_NCBI is disabled (no custom connector is implemented)",
            "query": query,
            "provider": "ncbi",
            "pmids": [],
            "articles": [],
            "total": 0,
        }

    if get_env("PUBMED_API_KEY") and not get_env("NCBI_API_KEY"):
        logger.warning(
            "PUBMED_API_KEY is set but NCBI_API_KEY is not set. "
            "This tool uses NCBI E-utilities and will only send an API key if NCBI_API_KEY is provided."
        )

    # Validate parameters
    max_results = max(1, min(int(max_results), 10000))
    start = max(0, int(start))
    
    try:
        # Initialize search engine
        engine = PubMedSearchEngine()
        
        # Search with advanced filters
        search_result = engine.search(
            query=query,
            max_results=max_results,
            start=start,
            sort=sort,
            mindate=mindate,
            maxdate=maxdate,
            publication_types=publication_types,
            journals=journals,
            language=language if language else None,
            species=species,
            use_cache=True,
        )
        
        result = search_result.get("esearchresult", {})
        pmids = result.get("idlist", []) or []
        total = int(result.get("count", 0) or 0)
        
        response = {
            "provider": "ncbi",
            "query": query,
            "total": total,
            "start": start,
            "max_results": max_results,
            "pmids": pmids,
            "articles": [],
        }
        
        # Fetch article details if requested
        if fetch_details and pmids:
            articles = engine.fetch_articles(pmids)
            response["articles"] = articles
            logger.info(f"✅ Found {total} results, fetched {len(articles)} articles")
        else:
            logger.info(f"✅ Found {total} results, {len(pmids)} PMIDs")
        
        return response
    
    except requests.exceptions.Timeout:
        logger.error(f"⏱️ Timeout querying PubMed: {query[:50]}...")
        return {
            "error": "Timeout while querying PubMed",
            "query": query,
            "provider": "ncbi",
            "pmids": [],
            "articles": [],
            "total": 0,
        }
    
    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, "status_code", None)
        text = getattr(e.response, "text", "")[:500]
        logger.error(f"❌ HTTP {status} from PubMed: {text}")
        return {
            "error": f"HTTP error {status} from PubMed",
            "status_code": status,
            "details": text,
            "query": query,
            "provider": "ncbi",
            "pmids": [],
            "articles": [],
            "total": 0,
        }
    
    except Exception as e:
        logger.error(f"❌ PubMed search error: {e}")
        return {
            "error": str(e),
            "query": query,
            "provider": "ncbi",
            "pmids": [],
            "articles": [],
            "total": 0,
        }
