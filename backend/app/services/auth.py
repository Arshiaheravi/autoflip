"""
Authentication service — JWT + bcrypt
Handles user creation, password verification, and token generation.
"""
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "autoflip-dev-secret-change-in-production-2025")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7  # 7 days


# ──────────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ──────────────────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str = ""


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


# ──────────────────────────────────────────────────────────────────────────────
# Password helpers
# ──────────────────────────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    """Return bcrypt hash of the plain-text password."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the stored hash."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────────────────────
# JWT helpers
# ──────────────────────────────────────────────────────────────────────────────
def create_access_token(user_id: str, email: str) -> str:
    """Create a signed JWT that expires in ACCESS_TOKEN_EXPIRE_HOURS."""
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT. Returns payload dict or None."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        logger.debug("JWT decode failed: %s", e)
        return None


def safe_user(user_doc: dict) -> dict:
    """Strip sensitive fields before returning to client.

    Always returns a consistent shape — never exposes password_hash,
    Stripe IDs, or other internal fields.
    """
    return {
        "id": user_doc.get("id"),
        "email": user_doc.get("email"),
        "name": user_doc.get("name", ""),
        "plan": user_doc.get("plan", "free"),
        "billing_period": user_doc.get("billing_period", "monthly"),
        "subscription_status": user_doc.get("subscription_status", "inactive"),
        "created_at": user_doc.get("created_at"),
        "subscribed_at": user_doc.get("subscribed_at"),
    }
