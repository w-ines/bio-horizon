"""Topic service — CRUD operations on topics table + PubMed search execution."""

import time as time_mod
from datetime import datetime
from typing import Optional, List

from api.schemas.topic import TopicCreate, TopicUpdate


class TopicService:
    """Handles topic-related business logic and database operations."""

    @staticmethod
    def _get_client():
        from storage.supabase_client import get_supabase_client
        return get_supabase_client()

    @staticmethod
    def create(user_id: str, topic: TopicCreate) -> dict:
        """Create a new topic for a user."""
        supabase = TopicService._get_client()
        data = topic.model_dump()
        data["user_id"] = user_id
        data["is_active"] = True
        data["total_articles_found"] = 0

        result = supabase.table("topics").insert(data).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def get_by_id(topic_id: str) -> Optional[dict]:
        """Get topic by ID."""
        supabase = TopicService._get_client()
        result = supabase.table("topics") \
            .select("*") \
            .eq("id", topic_id) \
            .is_("deleted_at", "null") \
            .execute()
        return result.data[0] if result.data else None

    @staticmethod
    def list_by_user(user_id: str) -> List[dict]:
        """List all active topics for a user."""
        supabase = TopicService._get_client()
        result = supabase.table("topics") \
            .select("*") \
            .eq("user_id", user_id) \
            .is_("deleted_at", "null") \
            .order("created_at", desc=False) \
            .execute()
        return result.data or []

    @staticmethod
    def update(topic_id: str, topic: TopicUpdate) -> Optional[dict]:
        """Update a topic."""
        supabase = TopicService._get_client()
        data = topic.model_dump(exclude_none=True)

        if not data:
            return TopicService.get_by_id(topic_id)

        result = supabase.table("topics") \
            .update(data) \
            .eq("id", topic_id) \
            .is_("deleted_at", "null") \
            .execute()
        return result.data[0] if result.data else None

    @staticmethod
    def delete(topic_id: str) -> bool:
        """Soft-delete a topic."""
        supabase = TopicService._get_client()
        result = supabase.table("topics") \
            .update({"deleted_at": datetime.utcnow().isoformat(), "is_active": False}) \
            .eq("id", topic_id) \
            .is_("deleted_at", "null") \
            .execute()
        return bool(result.data)

    @staticmethod
    def execute_search(topic_id: str) -> dict:
        """Execute a PubMed search for a specific topic and record results."""
        supabase = TopicService._get_client()

        # Get topic
        topic = TopicService.get_by_id(topic_id)
        if not topic:
            raise ValueError(f"Topic {topic_id} not found")

        # Build search parameters from topic config
        from core_tools.pubmed_tool import PubMedSearchEngine

        engine = PubMedSearchEngine()
        filters = topic.get("filters", {})

        start_time = time_mod.time()

        search_result = engine.search(
            query=topic["query"],
            max_results=topic.get("max_results", 20),
            sort=topic.get("sort_by", "relevance"),
            mindate=filters.get("mindate", ""),
            maxdate=filters.get("maxdate", ""),
            publication_types=filters.get("publication_types"),
            journals=filters.get("journals"),
            language=filters.get("language"),
            species=filters.get("species"),
            use_cache=True,
        )

        execution_time_ms = int((time_mod.time() - start_time) * 1000)

        result = search_result.get("esearchresult", {})
        pmids = result.get("idlist", []) or []
        total = int(result.get("count", 0) or 0)

        # Fetch article details
        articles = []
        if pmids:
            articles = engine.fetch_articles(pmids)

        # Determine new articles (not seen before by this user)
        existing_pmids = set()
        try:
            existing = supabase.table("user_articles") \
                .select("pmid") \
                .eq("user_id", topic["user_id"]) \
                .execute()
            existing_pmids = {row["pmid"] for row in (existing.data or [])}
        except Exception:
            pass

        new_pmids = [p for p in pmids if p not in existing_pmids]

        # Record search history
        try:
            supabase.table("topic_searches").insert({
                "topic_id": topic_id,
                "user_id": topic["user_id"],
                "query": topic["query"],
                "filters": filters,
                "total_results": total,
                "new_articles": len(new_pmids),
                "pmids": pmids,
                "execution_time_ms": execution_time_ms,
                "status": "success",
            }).execute()
        except Exception as e:
            print(f"[topic_service] Failed to record search history: {e}")

        # Store new articles for user
        for article in articles:
            if article.get("pmid") in new_pmids:
                try:
                    supabase.table("user_articles").insert({
                        "user_id": topic["user_id"],
                        "topic_id": topic_id,
                        "pmid": article["pmid"],
                        "title": article.get("title", ""),
                        "abstract": article.get("abstract", ""),
                        "journal": article.get("journal", ""),
                        "pub_date": article.get("pub_date", ""),
                        "authors": article.get("authors", []),
                        "mesh_terms": article.get("mesh_terms", []),
                    }).execute()
                except Exception:
                    pass  # Duplicate or other error

        # Update topic metadata
        try:
            supabase.table("topics").update({
                "last_search_at": datetime.utcnow().isoformat(),
                "total_articles_found": topic.get("total_articles_found", 0) + len(new_pmids),
            }).eq("id", topic_id).execute()
        except Exception as e:
            print(f"[topic_service] Failed to update topic metadata: {e}")

        return {
            "topic_id": topic_id,
            "query": topic["query"],
            "total_results": total,
            "new_articles": len(new_pmids),
            "pmids": pmids,
            "articles": articles,
            "execution_time_ms": execution_time_ms,
        }
