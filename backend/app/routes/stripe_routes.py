"""
Stripe routes — /api/stripe/create-checkout-session, /api/stripe/webhook

Env vars required to activate (all optional — app runs without them):
  STRIPE_SECRET_KEY         — your Stripe secret key (sk_test_... or sk_live_...)
  STRIPE_WEBHOOK_SECRET     — from Stripe Dashboard > Webhooks > signing secret
  STRIPE_PRICE_MONTHLY_ID   — Stripe Price ID for $4.99/month plan
  STRIPE_PRICE_YEARLY_ID    — Stripe Price ID for $39.99/year plan
  FRONTEND_URL              — base URL for success/cancel redirects (default: http://localhost:3000)
"""
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel

from ..database import db
from .auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stripe")


def _get_stripe():
    """Return configured stripe module, or None if STRIPE_SECRET_KEY not set."""
    secret_key = os.getenv("STRIPE_SECRET_KEY")
    if not secret_key:
        return None
    try:
        import stripe as _stripe
        _stripe.api_key = secret_key
        return _stripe
    except ImportError:
        logger.warning("stripe package not installed")
        return None


class CheckoutRequest(BaseModel):
    billing_period: str = "monthly"  # "monthly" | "yearly"


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/stripe/create-checkout-session
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/create-checkout-session")
async def create_checkout_session(
    body: CheckoutRequest,
    authorization: Optional[str] = Header(None),
):
    """
    Create a Stripe Checkout session for the authenticated user.
    Returns {"url": "...", "session_id": "..."} — frontend redirects to url.
    Returns 402 gracefully if Stripe keys are not configured.
    """
    stripe = _get_stripe()
    if not stripe:
        logger.warning("STRIPE_SECRET_KEY not set — checkout disabled")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment not configured. Set STRIPE_SECRET_KEY in .env to enable checkout.",
        )

    user = await get_current_user(authorization)

    if body.billing_period not in ("monthly", "yearly"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="billing_period must be 'monthly' or 'yearly'",
        )

    price_id = (
        os.getenv("STRIPE_PRICE_YEARLY_ID")
        if body.billing_period == "yearly"
        else os.getenv("STRIPE_PRICE_MONTHLY_ID")
    )
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Stripe price ID not configured for billing_period='{body.billing_period}'. "
                "Set STRIPE_PRICE_MONTHLY_ID and STRIPE_PRICE_YEARLY_ID in .env."
            ),
        )

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

    try:
        session_kwargs: dict = dict(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{frontend_url}/?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{frontend_url}/pricing",
            client_reference_id=user["id"],
            metadata={"user_id": user["id"], "billing_period": body.billing_period},
        )
        # Reuse existing Stripe customer to avoid duplicate customer records
        if user.get("stripe_customer_id"):
            session_kwargs["customer"] = user["stripe_customer_id"]
        else:
            session_kwargs["customer_email"] = user["email"]

        session = stripe.checkout.Session.create(**session_kwargs)
        logger.info(
            "Stripe checkout session created for %s (billing: %s)",
            user["email"], body.billing_period,
        )
        return {"url": session.url, "session_id": session.id}

    except stripe.error.StripeError as e:
        logger.error("Stripe error creating checkout session: %s", str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/stripe/webhook
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events.
    Uses raw request body for signature verification — do NOT parse as JSON first.

    Handled events:
      checkout.session.completed      → upgrade user to pro
      customer.subscription.deleted   → cancel user subscription
      customer.subscription.updated   → sync subscription status
      invoice.payment_failed          → mark user as past_due
    """
    stripe = _get_stripe()
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    if not stripe or not webhook_secret:
        logger.warning("Stripe webhook received but keys not configured — ignoring")
        return {"status": "ignored"}

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=403, detail="Invalid Stripe signature")

    event_type = event["type"]
    now = datetime.now(timezone.utc).isoformat()
    logger.info("Stripe webhook: %s (id=%s)", event_type, event.get("id"))

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("client_reference_id") or (
            session.get("metadata") or {}
        ).get("user_id")
        billing_period = (session.get("metadata") or {}).get("billing_period", "monthly")

        if user_id:
            await db.users.update_one(
                {"id": user_id},
                {"$set": {
                    "plan": "pro",
                    "subscription_status": "active",
                    "billing_period": billing_period,
                    "stripe_customer_id": session.get("customer"),
                    "stripe_subscription_id": session.get("subscription"),
                    "subscribed_at": now,
                    "updated_at": now,
                }},
            )
            logger.info("User %s upgraded to Pro (checkout.session.completed)", user_id)

    elif event_type == "customer.subscription.deleted":
        customer_id = event["data"]["object"].get("customer")
        if customer_id:
            await db.users.update_one(
                {"stripe_customer_id": customer_id},
                {"$set": {
                    "plan": "free",
                    "subscription_status": "cancelled",
                    "cancelled_at": now,
                    "updated_at": now,
                }},
            )
            logger.info("Subscription cancelled for Stripe customer %s", customer_id)

    elif event_type == "customer.subscription.updated":
        sub = event["data"]["object"]
        customer_id = sub.get("customer")
        sub_status = sub.get("status", "")
        if customer_id and sub_status:
            mapped = (
                "active" if sub_status == "active"
                else "past_due" if sub_status == "past_due"
                else "cancelled"
            )
            await db.users.update_one(
                {"stripe_customer_id": customer_id},
                {"$set": {"subscription_status": mapped, "updated_at": now}},
            )

    elif event_type == "invoice.payment_failed":
        customer_id = event["data"]["object"].get("customer")
        if customer_id:
            await db.users.update_one(
                {"stripe_customer_id": customer_id},
                {"$set": {"subscription_status": "past_due", "updated_at": now}},
            )
            logger.warning("Payment failed for Stripe customer %s — marked past_due", customer_id)

    return {"status": "ok"}
