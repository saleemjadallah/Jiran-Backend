from typing import Self

from pydantic import EmailStr, Field, model_validator

from app.models.user import UserRole
from app.schemas.base import ORMBaseModel


class RegisterRequest(ORMBaseModel):
    email: EmailStr = Field(..., examples=["user@soukloop.com"])
    username: str = Field(..., min_length=3, max_length=50, examples=["dubai_style"])
    password: str = Field(..., min_length=8, examples=["StrongPass!2024"])
    phone: str = Field(..., min_length=8, max_length=20, examples=["+971501234567"])
    full_name: str = Field(..., max_length=255, examples=["Layla Al Falasi"])
    role: UserRole = Field(default=UserRole.BUYER)


class LoginRequest(ORMBaseModel):
    identifier: str = Field(..., examples=["user@soukloop.com"], description="Email or username")
    password: str = Field(..., examples=["StrongPass!2024"])


class TokenResponse(ORMBaseModel):
    access_token: str = Field(..., examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    refresh_token: str = Field(..., examples=["def50200a1b8..."])
    token_type: str = Field(default="bearer", examples=["bearer"])
    expires_in: int = Field(..., description="Access token expiry in seconds", examples=[900])


class SendOTPRequest(ORMBaseModel):
    email: EmailStr | None = Field(default=None, examples=["user@soukloop.com"])
    phone: str | None = Field(default=None, examples=["+971501234567"])

    @model_validator(mode="after")
    def validate_identifier(self) -> Self:
        if not self.email and not self.phone:
            raise ValueError("Either email or phone must be provided")
        return self


class VerifyOTPRequest(ORMBaseModel):
    email: EmailStr | None = Field(default=None)
    phone: str | None = Field(default=None)
    otp_code: str = Field(..., min_length=4, max_length=8, examples=["123456"])

    @model_validator(mode="after")
    def validate_identifier(self) -> Self:
        if not self.email and not self.phone:
            raise ValueError("Either email or phone must be provided")
        return self


class RefreshTokenRequest(ORMBaseModel):
    refresh_token: str = Field(..., examples=["def50200a1b8..."])


class PasswordResetRequest(ORMBaseModel):
    email: EmailStr = Field(..., examples=["user@soukloop.com"])


class PasswordResetConfirm(ORMBaseModel):
    token: str = Field(..., examples=["reset-token"])
    new_password: str = Field(..., min_length=8, examples=["NewSecurePass!2024"])
