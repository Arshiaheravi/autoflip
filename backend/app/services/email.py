"""
Email notification service — SendGrid-powered deal alerts.

Usage:
  - SENDGRID_API_KEY must be set in backend/.env to activate emails.
  - SENDGRID_FROM_EMAIL (optional, defaults to 'alerts@autoflip.ca').
  - If the key is missing, all functions log a warning and return silently.
  - Feature auto-activates the moment the owner adds the key.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "alerts@autoflip.ca")
FROM_NAME = "AutoFlip Intelligence"

# Minimum score to trigger a deal alert email
ALERT_MIN_SCORE = 8


def _format_currency(val: Optional[float]) -> str:
    if val is None:
        return "N/A"
    return f"${val:,.0f}"


def _build_html_email(listing: dict) -> str:
    """Build a beautiful HTML email for a BUY deal alert."""
    title = listing.get("title", "Vehicle")
    price = _format_currency(listing.get("price"))
    profit_best = _format_currency(listing.get("profit_best"))
    profit_worst = _format_currency(listing.get("profit_worst"))
    market_value = _format_currency(listing.get("market_value"))
    score = listing.get("deal_score", "?")
    damage = listing.get("damage", "Unknown")
    mileage = listing.get("mileage")
    mileage_str = f"{mileage:,} km" if mileage else "N/A"
    source = listing.get("source", "").replace("_", " ").title()
    url = listing.get("url", "#")
    photo = listing.get("photo", "")
    colour = listing.get("colour", "")
    brand = listing.get("brand", "")
    year = listing.get("year", "")

    # Score badge colour
    score_color = "#22c55e"  # green for BUY

    photo_html = ""
    if photo:
        photo_html = f"""
        <div style="margin-bottom: 20px;">
          <img src="{photo}" alt="{title}" style="width: 100%; max-width: 480px; height: 240px;
               object-fit: cover; border-radius: 8px; display: block; margin: 0 auto;" />
        </div>
        """

    details_rows = ""
    details = [
        ("Auction Price", price),
        ("Market Value", market_value),
        ("Damage", damage or "None listed"),
        ("Mileage", mileage_str),
        ("Colour", colour or "N/A"),
        ("Brand Status", brand or "Clean"),
        ("Source", source),
    ]
    for label, value in details:
        details_rows += f"""
        <tr>
          <td style="padding: 8px 12px; color: #9ca3af; font-size: 13px; border-bottom: 1px solid #27272a;">{label}</td>
          <td style="padding: 8px 12px; color: #f4f4f5; font-size: 13px; font-weight: 600; border-bottom: 1px solid #27272a;">{value}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>🚗 BUY Deal Alert — {title}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #09090b; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #09090b; padding: 32px 16px;">
    <tr>
      <td align="center">
        <table width="100%" style="max-width: 560px; background-color: #18181b; border-radius: 12px; border: 1px solid #27272a; overflow: hidden;">

          <!-- Header -->
          <tr>
            <td style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); padding: 24px 28px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <div style="color: white; font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 6px; opacity: 0.8;">AutoFlip Intelligence</div>
                    <div style="color: white; font-size: 22px; font-weight: 900; letter-spacing: -0.5px;">🚗 BUY Deal Alert</div>
                    <div style="color: rgba(255,255,255,0.7); font-size: 12px; margin-top: 4px;">New deal just found — act fast before it's gone</div>
                  </td>
                  <td align="right" style="vertical-align: top;">
                    <div style="background: {score_color}; color: white; font-size: 28px; font-weight: 900; width: 56px; height: 56px; border-radius: 12px; display: inline-flex; align-items: center; justify-content: center; text-align: center; line-height: 56px;">
                      {score}
                    </div>
                    <div style="color: rgba(255,255,255,0.7); font-size: 10px; text-align: center; margin-top: 4px; letter-spacing: 1px;">SCORE</div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding: 24px 28px;">

              <!-- Title -->
              <h2 style="margin: 0 0 20px; color: #f4f4f5; font-size: 18px; font-weight: 800; line-height: 1.3;">{title}</h2>

              {photo_html}

              <!-- Profit box -->
              <div style="background: linear-gradient(135deg, rgba(34,197,94,0.12) 0%, rgba(34,197,94,0.05) 100%); border: 1px solid rgba(34,197,94,0.25); border-radius: 10px; padding: 20px; margin-bottom: 24px; text-align: center;">
                <div style="color: #9ca3af; font-size: 11px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 8px;">Estimated Profit Range</div>
                <div style="color: #22c55e; font-size: 30px; font-weight: 900; letter-spacing: -1px;">{profit_best}</div>
                <div style="color: #6b7280; font-size: 13px; margin-top: 4px;">Best case &nbsp;|&nbsp; Worst case: <span style="color: #d1d5db; font-weight: 600;">{profit_worst}</span></div>
              </div>

              <!-- Details table -->
              <table width="100%" cellpadding="0" cellspacing="0" style="border: 1px solid #27272a; border-radius: 8px; overflow: hidden; margin-bottom: 24px;">
                <tbody>
                  {details_rows}
                </tbody>
              </table>

              <!-- CTA -->
              <div style="text-align: center;">
                <a href="{url}" style="display: inline-block; background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); color: white; font-size: 15px; font-weight: 700; text-decoration: none; padding: 14px 36px; border-radius: 8px; letter-spacing: -0.3px;">
                  View This Deal →
                </a>
              </div>

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color: #09090b; padding: 20px 28px; border-top: 1px solid #27272a;">
              <p style="margin: 0; color: #6b7280; font-size: 11px; text-align: center; line-height: 1.6;">
                You're receiving this because you have an active AutoFlip Pro subscription.<br />
                <a href="#" style="color: #7c3aed; text-decoration: none;">Manage notification preferences</a>
                &nbsp;·&nbsp;
                <a href="#" style="color: #7c3aed; text-decoration: none;">Unsubscribe</a>
                <br /><br />
                © {datetime.now(timezone.utc).year} AutoFlip Intelligence · Ontario, Canada
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _build_plain_text(listing: dict) -> str:
    """Build plain-text fallback for the email."""
    title = listing.get("title", "Vehicle")
    price = _format_currency(listing.get("price"))
    profit_best = _format_currency(listing.get("profit_best"))
    score = listing.get("deal_score", "?")
    url = listing.get("url", "#")
    damage = listing.get("damage", "Unknown")
    mileage = listing.get("mileage")
    mileage_str = f"{mileage:,} km" if mileage else "N/A"

    return f"""AutoFlip Intelligence — BUY Deal Alert (Score: {score}/10)

{title}

Auction Price:   {price}
Profit (best):   {profit_best}
Damage:          {damage or 'None listed'}
Mileage:         {mileage_str}

View Deal: {url}

---
You're receiving this because you have an active AutoFlip Pro subscription.
© {datetime.now(timezone.utc).year} AutoFlip Intelligence · Ontario, Canada
"""


async def send_deal_alert_email(to_email: str, to_name: str, listing: dict) -> bool:
    """
    Send a BUY deal alert email to a single subscriber.

    Returns True if sent successfully, False otherwise.
    If SENDGRID_API_KEY is not set, logs a warning and returns False silently.
    """
    api_key = os.getenv("SENDGRID_API_KEY")
    if not api_key:
        logger.warning("SENDGRID_API_KEY not set — deal alert emails disabled")
        return False

    # Import here to avoid import errors if sendgrid not installed
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail, To, From, Content, HtmlContent, PlainTextContent
    except ImportError:
        logger.warning("sendgrid package not installed — deal alert emails disabled")
        return False

    title = listing.get("title", "A new BUY deal")
    subject = f"🚗 BUY Deal Alert: {title} (Score {listing.get('deal_score', '8+')})"

    try:
        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        message = Mail(
            from_email=(FROM_EMAIL, FROM_NAME),
            to_emails=to_email,
            subject=subject,
            html_content=_build_html_email(listing),
            plain_text_content=_build_plain_text(listing),
        )
        response = sg.send(message)
        status = response.status_code
        if status in (200, 201, 202):
            logger.info("Deal alert email sent to %s (status %s) — %s", to_email, status, title)
            return True
        else:
            logger.error("SendGrid returned status %s for %s", status, to_email)
            return False
    except Exception as e:
        logger.error("Failed to send deal alert email to %s: %s", to_email, e)
        return False


async def send_bulk_deal_alerts(listing: dict, db) -> int:
    """
    Find all Pro subscribers who haven't been alerted about this listing yet,
    and send them a deal alert email.

    Returns number of emails sent.
    """
    api_key = os.getenv("SENDGRID_API_KEY")
    if not api_key:
        logger.warning("SENDGRID_API_KEY not set — skipping bulk deal alerts")
        return 0

    listing_id = listing.get("id", "")
    if not listing_id:
        return 0

    # Find Pro subscribers who haven't already been alerted about this listing
    try:
        subscribers = await db.users.find(
            {
                "plan": "pro",
                "subscription_status": "active",
                "alerted_listings": {"$ne": listing_id},
            },
            {"email": 1, "name": 1, "id": 1, "_id": 0},
        ).to_list(1000)
    except Exception as e:
        logger.error("Failed to query subscribers for deal alert: %s", e)
        return 0

    if not subscribers:
        logger.debug("No eligible subscribers to alert for listing %s", listing_id)
        return 0

    sent_count = 0
    for subscriber in subscribers:
        success = await send_deal_alert_email(
            to_email=subscriber["email"],
            to_name=subscriber.get("name", ""),
            listing=listing,
        )
        if success:
            sent_count += 1
            # Mark this listing as alerted for this user
            try:
                await db.users.update_one(
                    {"id": subscriber["id"]},
                    {"$addToSet": {"alerted_listings": listing_id}},
                )
            except Exception as e:
                logger.warning("Failed to mark listing %s as alerted for user %s: %s",
                               listing_id, subscriber["id"], e)

    if sent_count > 0:
        logger.info("Sent %d deal alert emails for listing: %s", sent_count, listing.get("title", ""))

    return sent_count
