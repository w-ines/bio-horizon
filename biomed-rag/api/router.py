"""
Main API router — combines all sub-routers.
Each domain has its own file in api/routes/.
"""

from fastapi import APIRouter

from api.routes import health, cache, kg, conversations, pubmed, ner, upload, ask, users, topics, signals, snapshots, watch_topics

api_router = APIRouter()

# Core endpoints (no prefix)
api_router.include_router(health.router,        prefix="/health",         tags=["Health"])
api_router.include_router(ask.router,           prefix="/ask",            tags=["Agent"])
api_router.include_router(upload.router,        prefix="/upload",         tags=["Upload"])

# Domain-specific endpoints (prefixed)
api_router.include_router(cache.router,         prefix="/cache",          tags=["Cache"])
api_router.include_router(kg.router,            prefix="/kg",             tags=["Knowledge Graph"])
api_router.include_router(conversations.router,  prefix="/conversations",  tags=["Conversations"])
api_router.include_router(pubmed.router,         prefix="/pubmed",         tags=["PubMed"])
api_router.include_router(ner.router,            prefix="/ner",            tags=["NER"])
api_router.include_router(signals.router,        prefix="/signals",        tags=["Signals"])
api_router.include_router(snapshots.router,      prefix="/snapshots",      tags=["Snapshots"])
api_router.include_router(watch_topics.router,   prefix="/watch-topics",   tags=["Watch Topics"])

# Topic Tracking
api_router.include_router(users.router,          prefix="/users",          tags=["Users"])
api_router.include_router(topics.router,         prefix="/topics",         tags=["Topics"])
