"""
Auth routes — /api/auth/register, /api/auth/login, /api/auth/me, /api/auth/subscribe
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel
from typing import Optional

from ..database import db
from ..services.auth import (
    UserCreate, UserLogin, TokenResponse,
    hash_password, verify_password,
    create_access_token, decode_token, safe_user,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth")


# ──────────────────────────────────────────────────────────────────────────────
# Helper: get current user from Bearer token header
# ──────────────────────────────────────────────────────────────────────────────
async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Extract and validate Bearer token, return user document."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


# ──────────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ──────────────────────────────────────────────────────────────────────────────
class SubscribeRequest(BaseModel):
    plan: str = "pro"                  # "free" | "pro"
    billing_period: str = "monthly"    # "monthly" | "yearly"
    subscription_status: str = "active"  # "active" | "inactive" | "cancelled"
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/register
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate):
    """Create a new user account and return a JWT."""
    email_lower = body.email.lower().strip()

    # Duplicate check
    existing = await db.users.find_one({"email": email_lower})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Password strength: min 6 chars
    if len(body.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 6 characters",
        )

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    user_doc = {
        "id": user_id,
        "email": email_lower,
        "name": body.name.strip() or email_lower.split("@")[0],
        "password_hash": hash_password(body.password),
        "plan": "free",
        "subscription_status": "inactive",
        "created_at": now,
        "updated_at": now,
    }
    await db.users.insert_one(user_doc)
    logger.info("New user registered: %s", email_lower)

    token = create_access_token(user_id, email_lower)
    return {"access_token": token, "token_type": "bearer", "user": safe_user(user_doc)}


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/login
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin):
    """Authenticate with email + password, return JWT."""
    email_lower = body.email.lower().strip()
    user = await db.users.find_one({"email": email_lower}, {"_id": 0})

    # Use constant-time comparison to prevent timing attacks
    if not user or not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    logger.info("User logged in: %s", email_lower)
    token = create_access_token(user["id"], email_lower)
    return {"access_token": token, "token_type": "bearer", "user": safe_user(user)}


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/auth/me
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/me")
async def me(authorization: Optional[str] = Header(None)):
    """Return the currently authenticated user."""
    user = await get_current_user(authorization)
    return safe_user(user)


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/subscribe
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/subscribe")
async def subscribe(body: SubscribeRequest, authorization: Optional[str] = Header(None)):
    """
    Update the authenticated user's subscription plan and status.

    Called by the Stripe webhook handler (or directly from the frontend for dev/test).
    Validates plan values, updates the user document, and returns the updated user.
    """
    user = await get_current_user(authorization)

    # Validate plan value
    valid_plans = ("free", "pro")
    if body.plan not in valid_plans:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid plan '{body.plan}'. Must be one of: {valid_plans}",
        )

    valid_statuses = ("active", "inactive", "cancelled", "past_due")
    if body.subscription_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid subscription_status. Must be one of: {valid_statuses}",
        )

    valid_billing = ("monthly", "yearly")
    if body.billing_period not in valid_billing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid billing_period. Must be one of: {valid_billing}",
        )

    now = datetime.now(timezone.utc).isoformat()

    update_fields: dict = {
        "plan": body.plan,
        "subscription_status": body.subscription_status,
        "billing_period": body.billing_period,
        "updated_at": now,
    }

    # Optionally store Stripe IDs for webhook reconciliation
    if body.stripe_customer_id:
        update_fields["stripe_customer_id"] = body.stripe_customer_id
    if body.stripe_subscription_id:
        update_fields["stripe_subscription_id"] = body.stripe_subscription_id

    # If upgrading to pro, record the subscription start time
    if body.plan == "pro" and user.get("plan") != "pro":
        update_fields["subscribed_at"] = now
        logger.info("User upgraded to Pro: %s (billing: %s)", user["email"], body.billing_period)
    elif body.plan == "free" and user.get("plan") == "pro":
        update_fields["cancelled_at"] = now
        logger.info("User downgraded to Free: %s", user["email"])

    await db.users.update_one({"id": user["id"]}, {"$set": update_fields})

    # Return the updated user
    updated_user = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return safe_user(updated_user)


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/logout  (client just discards the token, but we log it)
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """Stateless logout — client should discard the token."""
    # JWT is stateless; just return success.
    # In future: maintain a token denylist in Redis.
    return {"message": "Logged out successfully"}
