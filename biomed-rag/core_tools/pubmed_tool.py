"""
PubMed Search Tool for Medical Literature Retrieval

Uses NCBI E-utilities API (ESearch + EFetch).

Environment variables (.env):
    NCBI_API_KEY        - NCBI API key (increases rate limit from 3 to 10 req/sec)
    PUBMED_API_KEY      - Fallback api key name if you stored the NCBI key under this name
    NCBI_EMAIL          - Your email (recommended by NCBI)
    NCBI_TOOL           - Tool name identifier (default: med-assist)
    NCBI_BASE_URL       - NCBI base URL (default: https://eutils.ncbi.nlm.nih.gov/entrez/eutils)
    PUBMED_USE_NCBI     - Toggle to use NCBI API (default: true)
"""

import os
import logging
import hashlib
from typing import Any, Dict, List, Optional
from datetime import timedelta

import requests
from dotenv import load_dotenv

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Redis not available. Install with: pip install redis")

load_dotenv()
logger = logging.getLogger(__name__)


# =============================================================================
# Redis Cache Manager
# =============================================================================

class CacheManager:
    """Redis cache manager for PubMed queries."""
    
    def __init__(self):
        self.redis_client = None
        self.enabled = False
        
        if REDIS_AVAILABLE:
            try:
                redis_url = _env("REDIS_URL", "redis://localhost:6379/0")
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                self.enabled = True
                logger.info("✅ Redis cache enabled")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Caching disabled.")
                self.enabled = False
    
    def get(self, key: str) -> Optional[str]:
        """Get cached value."""
        if not self.enabled:
            return None
        try:
            return self.redis_client.get(key)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: str, ttl: int = 86400):
        """Set cached value with TTL (default 24h)."""
        if not self.enabled:
            return
        try:
            self.redis_client.setex(key, ttl, value)
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
    
    @staticmethod
    def make_key(prefix: str, *args) -> str:
        """Generate cache key from arguments."""
        content = ":".join(str(arg) for arg in args)
        hash_suffix = hashlib.md5(content.encode()).hexdigest()[:12]
        return f"{prefix}:{hash_suffix}"


# =============================================================================
# Configuration helpers
# =============================================================================

def _env(name: str, default: str = "") -> str:
    """Get environment variable with default."""
    return os.getenv(name, default)


# =============================================================================
# PubMed Search Engine Class
# =============================================================================

class PubMedSearchEngine:
    """PubMed search engine with advanced filtering and caching."""
    
    def __init__(self, email: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize PubMed search engine.
        
        Args:
            email: NCBI email (recommended by NCBI)
            api_key: NCBI API key (increases rate limit to 10 req/s)
        """
        self.email = email or _env("NCBI_EMAIL")
        self.api_key = api_key or _env("NCBI_API_KEY")
        self.tool_name = _env("NCBI_TOOL", "med-assist")
        self.base_url = _ncbi_base_url()
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
        xml_data = ncbi_fetch(pmids[:200])
        articles = ncbi_parse_efetch_xml(xml_data)
        
        return articles


# =============================================================================
# NCBI E-utilities backend
# =============================================================================

def _ncbi_base_url() -> str:
    base = _env("NCBI_BASE_URL", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils").strip()
    return base.rstrip("/")


def _add_ncbi_credentials_to_params(params: Dict[str, Any]) -> None:
    """Add NCBI credentials to request parameters (in-place). Helper for standalone functions."""
    email = _env("NCBI_EMAIL")
    api_key = _env("NCBI_API_KEY")
    tool_name = _env("NCBI_TOOL", "med-assist")
    
    if email:
        params["email"] = email
    if tool_name:
        params["tool"] = tool_name
    if api_key:
        params["api_key"] = api_key


def ncbi_fetch(pmids: List[str], rettype: str = "abstract") -> str:
    """
    Fetch article details from PubMed via NCBI EFetch API.
    Returns XML with abstracts and metadata.
    """
    if not pmids:
        return ""
    
    url = f"{_ncbi_base_url()}/efetch.fcgi"
    
    params = {
        "db": "pubmed",
        "id": ",".join(pmids[:200]),  # Max 200 per request
        "retmode": "xml",
        "rettype": rettype,
    }
    
    # Add NCBI credentials
    _add_ncbi_credentials_to_params(params)
    
    logger.info(f"📄 NCBI EFetch: {len(pmids)} PMIDs")
    
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.text


def ncbi_parse_efetch_xml(xml_text: str) -> List[Dict[str, Any]]:
    """
    Parse EFetch XML response into structured article data.
    """
    import xml.etree.ElementTree as ET
    
    articles = []
    
    try:
        root = ET.fromstring(xml_text)
        
        for article in root.findall(".//PubmedArticle"):
            medline = article.find("MedlineCitation")
            if medline is None:
                continue
            
            pmid_elem = medline.find("PMID")
            pmid = pmid_elem.text if pmid_elem is not None else ""
            
            article_elem = medline.find("Article")
            if article_elem is None:
                continue
            
            # Title
            title_elem = article_elem.find("ArticleTitle")
            title = title_elem.text if title_elem is not None else ""
            
            # Abstract
            abstract_elem = article_elem.find("Abstract/AbstractText")
            abstract = abstract_elem.text if abstract_elem is not None else ""
            
            # Journal
            journal_elem = article_elem.find("Journal/Title")
            journal = journal_elem.text if journal_elem is not None else ""
            
            # Publication date
            pub_date = ""
            date_elem = article_elem.find("Journal/JournalIssue/PubDate")
            if date_elem is not None:
                year = date_elem.find("Year")
                month = date_elem.find("Month")
                if year is not None:
                    pub_date = year.text
                    if month is not None:
                        pub_date = f"{month.text} {pub_date}"
            
            # Authors
            authors = []
            for author in article_elem.findall("AuthorList/Author"):
                lastname = author.find("LastName")
                forename = author.find("ForeName")
                if lastname is not None:
                    name = lastname.text
                    if forename is not None:
                        name = f"{forename.text} {name}"
                    authors.append(name)
            
            # MeSH terms
            mesh_terms = []
            for mesh in medline.findall("MeshHeadingList/MeshHeading/DescriptorName"):
                if mesh.text:
                    mesh_terms.append(mesh.text)
            
            articles.append({
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "journal": journal,
                "pub_date": pub_date,
                "authors": authors,
                "mesh_terms": mesh_terms,
            })
    
    except ET.ParseError as e:
        logger.error(f"XML parse error: {e}")
    
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
    use_ncbi_setting = _env("PUBMED_USE_NCBI", "true").lower().strip()
    if use_ncbi_setting in {"false", "0", "no"}:
        return {
            "error": "PUBMED_USE_NCBI is disabled (no custom connector is implemented)",
            "query": query,
            "provider": "ncbi",
            "pmids": [],
            "articles": [],
            "total": 0,
        }

    if _env("PUBMED_API_KEY") and not _env("NCBI_API_KEY"):
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
