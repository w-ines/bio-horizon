"""
PubMed Common Utilities

Shared utilities for PubMed tools (cache, NCBI credentials, XML parsing).
"""

import os
import logging
import hashlib
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

load_dotenv()
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration helpers
# =============================================================================

def get_env(name: str, default: str = "") -> str:
    """Get environment variable with default."""
    return os.getenv(name, default)


def get_ncbi_base_url() -> str:
    """Get NCBI base URL from environment."""
    base = get_env("NCBI_BASE_URL", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils").strip()
    return base.rstrip("/")


def add_ncbi_credentials(params: Dict[str, Any]) -> None:
    """Add NCBI credentials to request parameters (in-place)."""
    email = get_env("NCBI_EMAIL")
    api_key = get_env("NCBI_API_KEY")
    tool_name = get_env("NCBI_TOOL", "med-assist")
    
    if email:
        params["email"] = email
    if tool_name:
        params["tool"] = tool_name
    if api_key:
        params["api_key"] = api_key


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
                redis_url = get_env("REDIS_URL", "redis://localhost:6379/0")
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
# NCBI XML Parser
# =============================================================================

def parse_efetch_xml(xml_text: str) -> List[Dict[str, Any]]:
    """
    Parse EFetch XML response into structured article data.
    
    Args:
        xml_text: XML response from NCBI EFetch
    
    Returns:
        List of article dictionaries with metadata
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
            
            # Article IDs (PMC, DOI) from PubmedData
            pmc_id = ""
            doi = ""
            pubmed_data = article.find("PubmedData")
            if pubmed_data is not None:
                for aid in pubmed_data.findall("ArticleIdList/ArticleId"):
                    id_type = aid.get("IdType", "")
                    if id_type == "pmc" and aid.text:
                        pmc_id = aid.text  # e.g. "PMC12345678"
                    elif id_type == "doi" and aid.text:
                        doi = aid.text

            # Build URLs
            pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
            pdf_url = ""
            if pmc_id:
                pmc_num = pmc_id.replace("PMC", "")
                pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/pdf/"

            articles.append({
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "journal": journal,
                "pub_date": pub_date,
                "authors": authors,
                "mesh_terms": mesh_terms,
                "pmc_id": pmc_id,
                "doi": doi,
                "pubmed_url": pubmed_url,
                "pdf_url": pdf_url,
            })
    
    except ET.ParseError as e:
        logger.error(f"XML parse error: {e}")
    
    return articles


# =============================================================================
# NCBI EFetch wrapper
# =============================================================================

def fetch_articles_xml(pmids: List[str], rettype: str = "abstract") -> str:
    """
    Fetch article details from PubMed via NCBI EFetch API.
    
    Args:
        pmids: List of PubMed IDs (max 200)
        rettype: Return type (abstract, medline, etc.)
    
    Returns:
        XML response text
    """
    if not pmids:
        return ""
    
    url = f"{get_ncbi_base_url()}/efetch.fcgi"
    
    params = {
        "db": "pubmed",
        "id": ",".join(pmids[:200]),
        "retmode": "xml",
        "rettype": rettype,
    }
    
    add_ncbi_credentials(params)
    
    logger.info(f"📄 NCBI EFetch: {len(pmids)} PMIDs")
    
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.text
