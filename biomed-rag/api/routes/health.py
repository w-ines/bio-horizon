"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    print("[health] /health called")
    return {"status": "ok"}
