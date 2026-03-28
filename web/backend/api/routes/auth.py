"""Authentication endpoints."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from core.auth import create_access_token, verify_credentials

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse:
    """Authenticate and return JWT token."""
    if not verify_credentials(body.email, body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(body.email)
    return LoginResponse(access_token=token)
