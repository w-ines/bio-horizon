"""User management endpoints."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from api.schemas.user import UserCreate, UserUpdate, UserResponse
from services.user_service import UserService

router = APIRouter()


@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate):
    """Register a new user."""
    try:
        result = UserService.create(user)
        return result
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get user by ID."""
    result = UserService.get_by_id(user_id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, user: UserUpdate):
    """Update user preferences."""
    result = UserService.update(user_id, user)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.delete("/{user_id}")
async def delete_user(user_id: str):
    """Soft-delete a user."""
    success = UserService.delete(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "deleted", "user_id": user_id}
