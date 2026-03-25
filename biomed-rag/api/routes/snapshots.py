"""
Snapshots API routes.

Provides endpoints for creating and managing KG snapshots.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class SnapshotCreateRequest(BaseModel):
    """Request to create a new KG snapshot."""
    query: str = Field(..., description="PubMed search query")
    max_results: int = Field(100, description="Maximum number of articles to fetch")
    week_label: Optional[str] = Field(None, description="Week label (e.g., 2026-W12). Auto-generated if not provided.")


@router.post("/create")
async def create_snapshot(request: SnapshotCreateRequest):
    """
    Create a new KG snapshot from PubMed articles.
    
    Pipeline: PubMed → NER → KG → Snapshot (Supabase + File)
    """
    try:
        from kg.snapshots import create_snapshot_from_pubmed
        
        snapshot_id, filepath = create_snapshot_from_pubmed(
            query=request.query,
            max_results=request.max_results,
            week_label=request.week_label
        )
        
        return {
            "success": True,
            "snapshot_id": snapshot_id,
            "filepath": filepath,
            "message": f"Snapshot created successfully"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_snapshots():
    """List all available KG snapshots."""
    try:
        from kg.snapshots import list_available_snapshots, get_week_label
        
        snapshots = list_available_snapshots()
        
        return {
            "snapshots": snapshots,
            "current_week": get_week_label(),
            "total_count": len(snapshots)
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{snapshot_id}")
async def get_snapshot(snapshot_id: int):
    """Get metadata for a specific snapshot."""
    try:
        from kg.snapshots import get_snapshot_metadata
        
        metadata = get_snapshot_metadata(snapshot_id)
        
        if not metadata:
            raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")
        
        return metadata
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
