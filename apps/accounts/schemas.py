"""
Pydantic schemas for accounts slice.
VSA-compliant type safety for user authentication and profiles.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, validator


class UserRegistration(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    password_confirm: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=30)
    last_name: str = Field(..., min_length=1, max_length=30)
    organization: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = Field(None, max_length=50)

    @validator("password_confirm")
    def passwords_match(cls, v, values):
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match")
        return v


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str = Field(..., min_length=1)
    remember_me: bool = Field(default=False)


class UserProfileUpdate(BaseModel):
    """Schema for user profile updates."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=30)
    last_name: Optional[str] = Field(None, min_length=1, max_length=30)
    organization: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = Field(None, max_length=50)
    bio: Optional[str] = Field(None, max_length=500)
    website: Optional[str] = Field(None, max_length=200)
    timezone: Optional[str] = Field(None, max_length=50)
    email_notifications: Optional[bool] = None


class UserProfileResponse(BaseModel):
    """Schema for user profile responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    first_name: str
    last_name: str
    organization: Optional[str]
    role: Optional[str]
    bio: Optional[str]
    website: Optional[str]
    timezone: str
    email_notifications: bool
    is_active: bool
    date_joined: datetime
    last_login: Optional[datetime]
    session_count: int
    total_results_reviewed: int


class PasswordChange(BaseModel):
    """Schema for password change requests."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)
    new_password_confirm: str = Field(..., min_length=8, max_length=128)

    @validator("new_password_confirm")
    def passwords_match(cls, v, values):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("New passwords do not match")
        return v


class PasswordReset(BaseModel):
    """Schema for password reset requests."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""

    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)
    new_password_confirm: str = Field(..., min_length=8, max_length=128)

    @validator("new_password_confirm")
    def passwords_match(cls, v, values):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("New passwords do not match")
        return v


class UserActivityLog(BaseModel):
    """Schema for user activity logging."""

    id: str
    user_id: str
    activity_type: str
    description: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime


class UserPreferences(BaseModel):
    """Schema for user preferences."""

    theme: str = Field(default="light", regex="^(light|dark)$")
    language: str = Field(default="en", max_length=5)
    results_per_page: int = Field(default=25, ge=10, le=100)
    auto_save_interval: int = Field(default=300, ge=60, le=3600)  # seconds
    notification_preferences: dict = Field(default_factory=dict)
    dashboard_layout: dict = Field(default_factory=dict)


class AccountSummary(BaseModel):
    """Schema for account summary information."""

    user_id: str
    total_sessions: int
    active_sessions: int
    completed_sessions: int
    total_results_processed: int
    total_results_reviewed: int
    account_created: datetime
    last_activity: Optional[datetime]
    subscription_status: str
    storage_used_mb: float
    api_usage_current_month: int
