from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.core.security import MIN_PASSWORD_LENGTH
from app.schemas.common import CamelModel


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=200)
    remember: bool = False

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class ResetPasswordRequest(CamelModel):
    token: str = Field(min_length=10, max_length=200)
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=200)


class TokenResponse(BaseModel):
    """OAuth2 password-flow response (API clients and the Swagger "Authorize" button)."""

    access_token: str
    token_type: str = "bearer"
