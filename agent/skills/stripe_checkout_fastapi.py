"""
Skill: stripe_checkout_fastapi
Pattern: Stripe Checkout Session creation + webhook handler for FastAPI/Motor (async MongoDB)

Key lessons:
- Use stripe.checkout.Session.create() (sync) inside FastAPI async routes — stripe-python is sync by default
- Webhook: always read raw bytes with `await request.body()` before signature verification
- Store stripe_customer_id on user to reuse existing Stripe customers (prevents duplicates)
- Pass client_reference_id=user_id for correlation in webhook handler
- Webhook events to handle: checkout.session.completed, customer.subscription.deleted,
  customer.subscription.updated, invoice.payment_failed
- Graceful degradation: if STRIPE_SECRET_KEY not set, return 402 (never crash)
- After checkout: success_url=f"{frontend_url}/?checkout=success&session_id={{CHECKOUT_SESSION_ID}}"
  Frontend: detect ?checkout=success, show banner, clear with window.history.replaceState
"""

# BACKEND — stripe_routes.py pattern
CREATE_CHECKOUT_PATTERN = '''
@router.post("/create-checkout-session")
async def create_checkout_session(body: CheckoutRequest, authorization: Optional[str] = Header(None)):
    stripe = _get_stripe()  # returns None if STRIPE_SECRET_KEY missing
    if not stripe:
        raise HTTPException(status_code=402, detail="Payment not configured")
    user = await get_current_user(authorization)
    price_id = os.getenv("STRIPE_PRICE_YEARLY_ID" if body.billing_period == "yearly" else "STRIPE_PRICE_MONTHLY_ID")
    session_kwargs = dict(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{frontend_url}/?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{frontend_url}/pricing",
        client_reference_id=user["id"],
        metadata={"user_id": user["id"], "billing_period": body.billing_period},
    )
    if user.get("stripe_customer_id"):
        session_kwargs["customer"] = user["stripe_customer_id"]  # reuse existing customer
    else:
        session_kwargs["customer_email"] = user["email"]
    session = stripe.checkout.Session.create(**session_kwargs)
    return {"url": session.url, "session_id": session.id}
'''

# WEBHOOK — always use raw body
WEBHOOK_PATTERN = '''
@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()  # CRITICAL: raw bytes for signature verification
    sig_header = request.headers.get("stripe-signature", "")
    event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("client_reference_id")
        billing_period = (session.get("metadata") or {}).get("billing_period", "monthly")
        await db.users.update_one({"id": user_id}, {"$set": {
            "plan": "pro", "subscription_status": "active",
            "billing_period": billing_period,
            "stripe_customer_id": session.get("customer"),
        }})
    return {"status": "ok"}
'''

# FRONTEND — api.js + PricingPage.jsx pattern
FRONTEND_PATTERN = '''
// api.js
export const stripeApi = {
  createCheckoutSession: (billingPeriod) =>
    api.post("/stripe/create-checkout-session", { billing_period: billingPeriod }),
};

// PricingPage.jsx — handleUpgrade
async function handleUpgrade() {
  if (!isAuthenticated) { onSignup && onSignup(); return; }
  setCheckoutLoading(true);
  try {
    const res = await stripeApi.createCheckoutSession(billingPeriod);
    window.location.href = res.data.url;  // external redirect — NOT React Router navigate()
  } catch (err) {
    setCheckoutError(err?.response?.data?.detail || "Checkout unavailable");
  } finally {
    setCheckoutLoading(false);
  }
}

// Dashboard.jsx — detect success on return
useEffect(() => {
  const params = new URLSearchParams(window.location.search);
  if (params.get("checkout") === "success") {
    setCheckoutSuccess(true);
    window.history.replaceState({}, "", window.location.pathname);  // clean URL
    setTimeout(() => setCheckoutSuccess(false), 8000);
  }
}, []);
'''
