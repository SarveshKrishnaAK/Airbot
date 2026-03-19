"""
Authentication Routes for Google OAuth
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from loguru import logger

from app.services.auth_service import auth_service, User, TokenData
from app.core.config import settings
from app.core.rate_limiter import rate_limiter, get_client_ip


router = APIRouter()
security = HTTPBearer(auto_error=False)


class LoginResponse(BaseModel):
    auth_url: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    email: str
    name: str
    picture: Optional[str]
    is_premium: bool


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[TokenData]:
    """Dependency to get current user from JWT token"""
    if credentials is None:
        return None

    token_data = auth_service.verify_token(credentials.credentials)
    return token_data


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """Dependency that requires authentication"""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token_data = auth_service.verify_token(credentials.credentials)
    if token_data is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return token_data


async def require_premium(
    token_data: TokenData = Depends(require_auth)
) -> TokenData:
    """Dependency that requires premium user"""
    user = auth_service.get_user(token_data.email)
    has_member_access = user.is_premium if user else auth_service.is_student_member(token_data.email)
    if not has_member_access:
        raise HTTPException(
            status_code=403,
            detail="Only @student.tce.edu Google accounts can access this feature"
        )
    return token_data


@router.get("/login")
async def login(request: Request):
    """Initiate Google OAuth login flow"""
    client_ip = get_client_ip(request)
    if not rate_limiter.allow(f"auth:login:{client_ip}", limit=20, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many login attempts. Please try again shortly.")

    redirect_uri = f"{settings.BACKEND_URL}/auth/callback"
    auth_url = auth_service.get_google_auth_url(redirect_uri)
    return {"auth_url": auth_url}


@router.get("/callback")
async def callback(code: str, request: Request):
    """Handle Google OAuth callback"""
    try:
        client_ip = get_client_ip(request)
        if not rate_limiter.allow(f"auth:callback:{client_ip}", limit=30, window_seconds=60):
            raise HTTPException(status_code=429, detail="Too many callback attempts. Please try again shortly.")

        redirect_uri = f"{settings.BACKEND_URL}/auth/callback"

        # Exchange code for tokens
        tokens = await auth_service.exchange_code_for_tokens(code, redirect_uri)
        access_token = tokens.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to get access token")

        # Get user info from Google
        user_info = await auth_service.get_user_info(access_token)

        # Create or get user
        user = auth_service.get_or_create_user(user_info)

        # Create our JWT token
        jwt_token = auth_service.create_access_token({
            "email": user.email,
            "name": user.name,
            "picture": user.picture
        })

        # Redirect to frontend with token in URL fragment (not sent to server logs)
        frontend_url = f"{settings.FRONTEND_URL}/auth-success.html#token={jwt_token}"
        return RedirectResponse(url=frontend_url)

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        error_url = f"{settings.FRONTEND_URL}/auth-error.html?error={str(e)}"
        return RedirectResponse(url=error_url)


@router.get("/me", response_model=UserResponse)
async def get_me(token_data: TokenData = Depends(require_auth)):
    """Get current user info"""
    user = auth_service.get_user(token_data.email)
    if not user:
        return UserResponse(
            email=token_data.email,
            name=token_data.name or token_data.email,
            picture=token_data.picture,
            is_premium=auth_service.is_student_member(token_data.email)
        )

    return UserResponse(
        email=user.email,
        name=user.name,
        picture=user.picture,
        is_premium=user.is_premium
    )


@router.post("/logout")
async def logout(token_data: TokenData = Depends(require_auth)):
    """Logout user (client should discard token)"""
    return {"message": "Logged out successfully"}


@router.get("/verify")
async def verify_token(token_data: TokenData = Depends(require_auth)):
    """Verify if token is valid"""
    return {
        "valid": True,
        "email": token_data.email,
        "name": token_data.name
    }
