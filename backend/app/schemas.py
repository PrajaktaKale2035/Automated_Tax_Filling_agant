"""Pydantic schemas for request/response validation.

Phase 0: trimmed to User / UserProfile / Auth / Chat / Health.
US-flavored TaxForm/Dependent/W2Form/Form1099/UserInputData schemas removed
along with the underlying SQLAlchemy models. Form16 / ITR1Filing schemas
live in api/filing_v2.py (request/response models close to their handlers).
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class User(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None


# ---------------------------------------------------------------------------
# User Profile
# ---------------------------------------------------------------------------

class UserProfileBase(BaseModel):
    preferred_mode: str = "novice"
    theme: str = "light"
    language: str = "en"
    notifications_enabled: bool = True
    preferred_regime: str = "new"  # India: "old" | "new"


class UserProfileUpdate(BaseModel):
    preferred_mode: Optional[str] = None
    theme: Optional[str] = None
    language: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    preferred_regime: Optional[str] = None


class UserProfile(UserProfileBase):
    id: int
    user_id: int
    interaction_count: int
    help_requests: int
    interaction_speed_avg_ms: int
    error_rate_percent: float
    cognitive_load_score: float

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Chat / Agent
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    message: str
    conversation_history: List[Dict[str, str]] = []
    context: Optional[Dict[str, Any]] = {}


class ChatResponse(BaseModel):
    response: str
    conversation_history: List[Dict[str, str]]
    metadata: Optional[Dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthCheck(BaseModel):
    status: str
    database: bool
    timestamp: datetime
    version: str = "1.0.0"
