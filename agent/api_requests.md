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
