"""
PubMed Bulk Ingestion Tool

Handles large-scale PubMed corpus ingestion using NCBI History Server.
Designed for processing hundreds of thousands of articles without timeouts.

Features:
- History Server pagination (usehistory=y)
- Batch processing (200 articles per batch)
- No memory accumulation (streaming)
- Suitable for async job processing
"""

import logging
from typing import Any, Dict, List, Optional

import requests

from core_tools.pubmed_utils import (
    get_env,
    get_ncbi_base_url,
    add_ncbi_credentials,
    parse_efetch_xml,
)
from core_tools.rate_limiter import get_rate_limiter, RetryConfig, retry_with_backoff

logger = logging.getLogger(__name__)


# =============================================================================
# PubMed Bulk Ingestion Engine
# =============================================================================

class PubMedBulkEngine:
    """
    PubMed bulk ingestion engine using NCBI History Server.
    
    This engine is optimized for large-scale corpus ingestion:
    - Uses History Server to avoid passing large PMID lists
    - Paginates through results in batches of 200
    - No caching (results are too large)
    - Designed for async job processing
    """
    
    def __init__(self, email: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize bulk ingestion engine.
        
        Args:
            email: NCBI email (recommended by NCBI)
            api_key: NCBI API key (increases rate limit to 10 req/s)
        """
        self.email = email or get_env("NCBI_EMAIL")
        self.api_key = api_key or get_env("NCBI_API_KEY")
        self.tool_name = get_env("NCBI_TOOL", "med-assist")
        self.base_url = get_ncbi_base_url()
        
        self.rate_limiter = get_rate_limiter(has_api_key=bool(self.api_key))
        self.retry_config = RetryConfig(max_retries=3, initial_delay=2.0, max_delay=30.0)
    
    def _add_credentials(self, params: Dict[str, Any]) -> None:
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
            publication_types: Filter by publication type
            journals: Filter by journal names
            language: Filter by language (e.g., "eng")
            species: Filter by species (e.g., ["Humans"])
        
        Returns:
            Advanced Entrez query string
        """
        parts = [base_query]
        
        if publication_types:
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
        
        if journals:
            journal_query = " OR ".join([f'"{j}"[Journal]' for j in journals])
            parts.append(f"({journal_query})")
        
        if language:
            parts.append(f"{language}[Language]")
        
        if species:
            species_query = " OR ".join([f'"{s}"[Organism]' for s in species])
            parts.append(f"({species_query})")
        
        return " AND ".join(parts)
    
    def search_with_history(
        self,
        query: str,
        sort: str = "relevance",
        mindate: str = "",
        maxdate: str = "",
        publication_types: Optional[List[str]] = None,
        journals: Optional[List[str]] = None,
        language: Optional[str] = None,
        species: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Search PubMed using History Server for large result sets.
        
        Instead of returning PMIDs, this stores results on NCBI's server
        and returns WebEnv + QueryKey tokens for pagination.
        
        Args:
            query: Base search query
            sort: Sort order (relevance, pub_date, Author, JournalName)
            mindate: Minimum publication date (YYYY or YYYY/MM or YYYY/MM/DD)
            maxdate: Maximum publication date
            publication_types: Filter by publication types
            journals: Filter by journal names
            language: Filter by language code (e.g., "eng")
            species: Filter by species/organism
        
        Returns:
            dict: {
                "web_env": str,      # WebEnv token for pagination
                "query_key": str,    # QueryKey for this search
                "count": int,        # Total number of results
                "query": str         # The advanced query used
            }
        
        Example:
            >>> engine = PubMedBulkEngine()
            >>> result = engine.search_with_history("diabetes mellitus", mindate="2023")
            >>> print(f"Found {result['count']} articles")
            >>> # Now paginate through results with fetch_batch()
        """
        advanced_query = self._build_advanced_query(
            query, publication_types, journals, language, species
        )
        
        url = f"{self.base_url}/esearch.fcgi"
        
        params = {
            "db": "pubmed",
            "term": advanced_query,
            "retmode": "json",
            "usehistory": "y",
            "retmax": 0,
        }
        
        if sort:
            params["sort"] = sort
        
        if mindate or maxdate:
            params["datetype"] = "pdat"
            if mindate:
                params["mindate"] = mindate
            if maxdate:
                params["maxdate"] = maxdate
        
        self._add_credentials(params)
        
        logger.info(f"🔍 PubMed History search: {advanced_query[:80]}...")
        
        # Apply rate limiting
        self.rate_limiter.acquire_sync()
        
        # Make request with retry
        def _make_request():
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            return response.json()
        
        import asyncio
        result = asyncio.run(retry_with_backoff(_make_request, config=self.retry_config))
        
        esearch_result = result.get("esearchresult", {})
        web_env = esearch_result.get("webenv", "")
        query_key = esearch_result.get("querykey", "")
        count = int(esearch_result.get("count", 0))
        
        if not web_env or not query_key:
            raise ValueError("NCBI did not return WebEnv/QueryKey. History Server may be unavailable.")
        
        logger.info(f"✅ History search complete: {count:,} results stored (WebEnv={web_env[:20]}...)")
        
        return {
            "web_env": web_env,
            "query_key": query_key,
            "count": count,
            "query": advanced_query,
        }
    
    def fetch_batch(
        self,
        web_env: str,
        query_key: str,
        retstart: int = 0,
        retmax: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        Fetch a batch of articles using History Server tokens.
        
        This allows pagination through large result sets without
        re-executing the search or passing PMIDs.
        
        Args:
            web_env: WebEnv token from search_with_history()
            query_key: QueryKey from search_with_history()
            retstart: Starting index (0-based)
            retmax: Number of articles to fetch (max 500, recommended 200)
        
        Returns:
            List of article dictionaries with metadata
        
        Example:
            >>> # Fetch first 200 articles
            >>> batch1 = engine.fetch_batch(web_env, query_key, retstart=0, retmax=200)
            >>> # Fetch next 200 articles
            >>> batch2 = engine.fetch_batch(web_env, query_key, retstart=200, retmax=200)
        """
        if not web_env or not query_key:
            raise ValueError("web_env and query_key are required")
        
        retmax = max(1, min(int(retmax), 500))
        retstart = max(0, int(retstart))
        
        url = f"{self.base_url}/efetch.fcgi"
        
        params = {
            "db": "pubmed",
            "query_key": query_key,
            "WebEnv": web_env,
            "retstart": retstart,
            "retmax": retmax,
            "retmode": "xml",
            "rettype": "abstract",
        }
        
        self._add_credentials(params)
        
        logger.info(f"📄 Fetching batch: retstart={retstart}, retmax={retmax}")
        
        # Apply rate limiting
        self.rate_limiter.acquire_sync()
        
        # Make request with retry
        def _make_request():
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.text
        
        import asyncio
        xml_data = asyncio.run(retry_with_backoff(_make_request, config=self.retry_config))
        
        articles = parse_efetch_xml(xml_data)
        
        logger.info(f"✅ Fetched {len(articles)} articles")
        
        return articles
    
    def fetch_all_batches(
        self,
        web_env: str,
        query_key: str,
        total_count: int,
        batch_size: int = 200,
        max_batches: Optional[int] = None,
    ):
        """
        Generator that yields batches of articles.
        
        This is a convenience method for iterating through all results.
        Use this in async workers to process large result sets.
        
        Args:
            web_env: WebEnv token from search_with_history()
            query_key: QueryKey from search_with_history()
            total_count: Total number of results (from search_with_history)
            batch_size: Number of articles per batch (default 200)
            max_batches: Optional limit on number of batches to fetch
        
        Yields:
            Tuple of (batch_index, articles_list)
        
        Example:
            >>> result = engine.search_with_history("diabetes")
            >>> for batch_idx, articles in engine.fetch_all_batches(
            ...     result['web_env'], result['query_key'], result['count']
            ... ):
            ...     print(f"Processing batch {batch_idx}: {len(articles)} articles")
            ...     # Process articles (NER, KG ingestion, etc.)
        """
        batch_idx = 0
        retstart = 0
        
        while retstart < total_count:
            if max_batches and batch_idx >= max_batches:
                logger.info(f"⚠️  Reached max_batches limit ({max_batches})")
                break
            
            articles = self.fetch_batch(web_env, query_key, retstart, batch_size)
            
            if not articles:
                logger.warning(f"⚠️  No articles returned at retstart={retstart}")
                break
            
            yield (batch_idx, articles)
            
            batch_idx += 1
            retstart += batch_size
        
        logger.info(f"✅ Completed fetching {batch_idx} batches")
