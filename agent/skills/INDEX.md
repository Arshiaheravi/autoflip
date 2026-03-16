# Skill Library

Reusable patterns saved by the agent. Check here before writing from scratch.

- **mongodb_upsert_with_history** — Upsert a listing and track price history atomically (`agent/skills/mongodb_upsert_with_history.py`)
- **httpx_scraper_base** — Resilient httpx scraper with retry, User-Agent, timeout, BeautifulSoup parse (`agent/skills/httpx_scraper_base.py`)
- **fastapi_jwt_dependency** — FastAPI dependency that validates JWT and returns current user (`agent/skills/fastapi_jwt_dependency.py`)
- **sendgrid_with_smtp_fallback** — Send email via SendGrid with SMTP fallback and silent fail if keys missing (`agent/skills/sendgrid_with_smtp_fallback.py`)
