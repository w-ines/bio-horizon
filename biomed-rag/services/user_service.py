"""User service — CRUD operations on users table via Supabase."""

import hashlib
from datetime import datetime
from typing import Optional

from api.schemas.user import UserCreate, UserUpdate


class UserService:
    """Handles user-related business logic and database operations."""

    @staticmethod
    def _get_client():
        from storage.supabase_client import get_supabase_client
        return get_supabase_client()

    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def create(user: UserCreate) -> dict:
        """Create a new user."""
        supabase = UserService._get_client()

        # Check if email already exists
        existing = supabase.table("users").select("id").eq("email", user.email).execute()
        if existing.data:
            raise ValueError(f"User with email {user.email} already exists")

        data = {
            "email": user.email,
            "full_name": user.full_name,
            "password_hash": UserService._hash_password(user.password),
            "frequency": user.frequency,
            "delivery_time": user.delivery_time.isoformat(),
            "timezone": user.timezone,
            "language": user.language,
            "is_active": True,
            "is_verified": False,
        }

        result = supabase.table("users").insert(data).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def get_by_id(user_id: str) -> Optional[dict]:
        """Get user by ID."""
        supabase = UserService._get_client()
        result = supabase.table("users") \
            .select("*") \
            .eq("id", user_id) \
            .is_("deleted_at", "null") \
            .execute()
        return result.data[0] if result.data else None

    @staticmethod
    def get_by_email(email: str) -> Optional[dict]:
        """Get user by email."""
        supabase = UserService._get_client()
        result = supabase.table("users") \
            .select("*") \
            .eq("email", email) \
            .is_("deleted_at", "null") \
            .execute()
        return result.data[0] if result.data else None

    @staticmethod
    def update(user_id: str, user: UserUpdate) -> Optional[dict]:
        """Update user preferences."""
        supabase = UserService._get_client()
        data = user.model_dump(exclude_none=True)

        if "delivery_time" in data and data["delivery_time"] is not None:
            data["delivery_time"] = data["delivery_time"].isoformat()

        if not data:
            return UserService.get_by_id(user_id)

        result = supabase.table("users") \
            .update(data) \
            .eq("id", user_id) \
            .is_("deleted_at", "null") \
            .execute()
        return result.data[0] if result.data else None

    @staticmethod
    def delete(user_id: str) -> bool:
        """Soft-delete a user."""
        supabase = UserService._get_client()
        result = supabase.table("users") \
            .update({"deleted_at": datetime.utcnow().isoformat(), "is_active": False}) \
            .eq("id", user_id) \
            .is_("deleted_at", "null") \
            .execute()
        return bool(result.data)
