"""
Send email via SendGrid with SMTP fallback. Silent fail if keys missing.
Use for: any new email feature. This pattern already exists in backend/app/services/email_alerts.py

Saved by agent on 2026-03-16.
"""

# IMPORTANT: The full implementation already lives in backend/app/services/email_alerts.py
# Import from there — do NOT re-implement.
#
# from ..services.email_alerts import send_email
#
# Usage:
# await send_email(
#     to_email="user@example.com",
#     subject="Your subject",
#     html_content="<h1>Hello</h1>",
#     text_content="Hello"
# )
#
# The function:
# 1. Tries SendGrid if SENDGRID_API_KEY is in env
# 2. Falls back to SMTP if SMTP_HOST, SMTP_USER, SMTP_PASS are in env
# 3. Silently logs a warning and returns False if neither is configured
# 4. Never raises — always safe to call

# Pattern for bulk alerts (already in email_alerts.py):
# from ..services.email_alerts import send_bulk_deal_alerts
# await send_bulk_deal_alerts(listing_doc, db)
# This queries db.users for plan=pro + subscription_status=active + not already alerted
# Marks listing ID in user.alerted_listings using $addToSet (idempotent)
