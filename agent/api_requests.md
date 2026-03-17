# API Keys Needed

The agent codes features fully, then logs here what key is needed to activate them.
**Your only job: find the key, paste it into `backend/.env`, save the file.**
The feature turns on automatically — no other action needed.

Check boxes below as you add each key: `[ ]` → `[x]`

---

_(No keys needed yet — agent will add entries here as it builds features)_

---
## [ ] SendGrid — HIGH priority — 2026-03-16 03:54

**Add this to `backend/.env`:**
```
SENDGRID_API_KEY=your_key_here
```

**What this unlocks:** Automatic BUY deal alert emails — whenever a new vehicle with deal score ≥ 8 is found at auction, every Pro subscriber instantly receives a beautiful HTML email with the car photo, profit estimate, and a direct link to the listing. Also needs SENDGRID_FROM_EMAIL (optional, defaults to alerts@autoflip.ca).

**How to get the key:** 1. Go to https://sendgrid.com and create a free account (100 emails/day free). 2. Go to Settings → API Keys → Create API Key → choose "Full Access". 3. Copy the key (starts with SG.) and paste it into backend/.env as SENDGRID_API_KEY=SG.xxxxxxx. 4. Optionally also set SENDGRID_FROM_EMAIL=youremail@yourdomain.com (must be a verified sender in SendGrid).

_Feature is fully implemented and will activate automatically once you add the key._

---
## [ ] Stripe — HIGH priority — 2026-03-16

**Add all four to `backend/.env`:**
```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PRICE_MONTHLY_ID=price_...
STRIPE_PRICE_YEARLY_ID=price_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

**What this unlocks:** Full Stripe payment flow — users click "Upgrade to Pro" on PricingPage, get redirected to Stripe Checkout ($4.99/mo or $39.99/yr), complete payment, and land back on Dashboard with a "Welcome to Pro!" banner. Webhook handler automatically upgrades `user.plan → 'pro'` and handles subscription cancellations and payment failures.

**How to get the keys:**
1. Go to https://dashboard.stripe.com and create a free account.
2. In **Developers → API keys**: copy the **Secret key** (`sk_test_...` for test mode, `sk_live_...` for production).
3. In **Products → Add product**: create "AutoFlip Pro" with two prices: $4.99/month recurring and $39.99/year recurring. Copy each **Price ID** (`price_...`).
4. In **Developers → Webhooks → Add endpoint**: set URL to `https://yourdomain.com/api/stripe/webhook`, select events: `checkout.session.completed`, `customer.subscription.deleted`, `customer.subscription.updated`, `invoice.payment_failed`. Copy the **Signing secret** (`whsec_...`).
5. Optionally also set `FRONTEND_URL=https://yourdomain.com` (defaults to http://localhost:3000).

_Feature is 100% implemented. App never crashes without these keys — Stripe simply shows a 402 error to the user instead of the checkout button._
