"""
Authentication Service for Google OAuth
Handles user authentication and JWT token management
"""

from datetime import datetime, timedelta
from typing import Optional
import httpx
from jose import JWTError, jwt
from loguru import logger
from pydantic import BaseModel

from app.core.config import settings


class TokenData(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None


class User(BaseModel):
    email: str
    name: str
    picture: Optional[str] = None
    is_premium: bool = False
    created_at: datetime = datetime.utcnow()


# In-memory user store (replace with database in production)
users_db: dict[str, User] = {}


class AuthService:
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        logger.info("Auth Service initialized")

    def get_google_auth_url(self, redirect_uri: str) -> str:
        """Generate Google OAuth URL for user to authenticate"""
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent"
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"

    async def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str
    ) -> dict:
        """Exchange authorization code for access tokens"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri
                }
            )
            response.raise_for_status()
            return response.json()

    async def get_user_info(self, access_token: str) -> dict:
        """Get user info from Google using access token"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()

    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + (
            expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        to_encode.update({"exp": expire})
        return jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )

    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify JWT token and return user data"""
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            email: str = payload.get("email")
            if email is None:
                return None
            return TokenData(
                email=email,
                name=payload.get("name"),
                picture=payload.get("picture")
            )
        except JWTError as e:
            logger.error(f"JWT verification failed: {e}")
            return None

    def get_or_create_user(self, user_info: dict) -> User:
        """Get existing user or create new one"""
        email = user_info.get("email")

        if email in users_db:
            logger.info(f"Existing user logged in: {email}")
            return users_db[email]

        # Create new user
        user = User(
            email=email,
            name=user_info.get("name", "User"),
            picture=user_info.get("picture"),
            is_premium=False,  # Default to free tier
            created_at=datetime.utcnow()
        )
        users_db[email] = user
        logger.info(f"New user created: {email}")
        return user

    def get_user(self, email: str) -> Optional[User]:
        """Get user by email"""
        return users_db.get(email)

    def set_premium(self, email: str, is_premium: bool) -> bool:
        """Set user premium status"""
        if email in users_db:
            users_db[email].is_premium = is_premium
            logger.info(f"User {email} premium status: {is_premium}")
            return True
        return False


auth_service = AuthService()
