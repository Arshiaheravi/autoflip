"""
Email alert service — sends BUY deal notifications to subscribed users.

Uses SendGrid if SENDGRID_API_KEY is set, falls back to SMTP if
SMTP_HOST / SMTP_USER / SMTP_PASSWORD are set.
If neither is configured, logs a warning and returns silently.

The feature is 100% coded. It activates automatically the moment
the owner adds SENDGRID_API_KEY (or SMTP_*) to backend/.env.
"""
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", "alerts@autoflip.ca")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "AutoFlip Intelligence")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Minimum deal score to trigger an alert
ALERT_MIN_SCORE = 8


def _format_currency(amount: Optional[float]) -> str:
    if amount is None:
        return "N/A"
    return f"${amount:,.0f}"


def _build_deal_alert_html(listing: dict) -> str:
    """Build a clean, mobile-friendly HTML email for a BUY deal."""
    title = listing.get("title", "Vehicle")
    price = _format_currency(listing.get("price"))
    profit_best = _format_currency(listing.get("profit_best"))
    profit_worst = _format_currency(listing.get("profit_worst"))
    market_value = _format_currency(listing.get("market_value"))
    score = listing.get("deal_score", "?")
    damage = listing.get("damage", "N/A")
    mileage_raw = listing.get("mileage")
    mileage = f"{mileage_raw:,} km" if mileage_raw else "N/A"
    source = listing.get("source", "auction").replace("_", " ").title()
    listing_url = listing.get("url", "#")
    listing_id = listing.get("id", "")
    app_url = f"{FRONTEND_URL}?deal={listing_id}" if listing_id else FRONTEND_URL
    photo = listing.get("photo", "")
    brand = listing.get("brand", "")
    colour = listing.get("colour", "N/A")
    roi_best = listing.get("roi_best")
    roi_str = f"{roi_best:.0f}%" if roi_best is not None else "N/A"

    photo_html = ""
    if photo:
        photo_html = f'<img src="{photo}" alt="{title}" style="width:100%;max-width:600px;height:240px;object-fit:cover;border-radius:8px 8px 0 0;display:block;" />'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>🔥 BUY Deal Alert — {title}</title>
</head>
<body style="margin:0;padding:0;background:#09090b;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#09090b;padding:24px 0;">
    <tr><td align="center">
      <table width="100%" style="max-width:600px;background:#18181b;border-radius:12px;border:1px solid #27272a;overflow:hidden;">

        <!-- Header -->
        <tr><td style="background:#18181b;padding:20px 24px;border-bottom:1px solid #27272a;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td>
                <span style="font-size:22px;font-weight:900;color:#fff;letter-spacing:-0.5px;">⚡ AutoFlip</span>
                <span style="display:block;font-size:11px;color:#71717a;letter-spacing:2px;text-transform:uppercase;">Intelligence</span>
              </td>
              <td align="right">
                <span style="display:inline-block;background:#22c55e20;border:1px solid #22c55e40;color:#22c55e;
                             padding:4px 12px;border-radius:999px;font-size:12px;font-weight:700;">
                  🔥 BUY DEAL
                </span>
              </td>
            </tr>
          </table>
        </td></tr>

        <!-- Photo -->
        {photo_html}

        <!-- Deal body -->
        <tr><td style="padding:24px;">

          <!-- Title + source -->
          <p style="margin:0 0 4px 0;font-size:11px;color:#71717a;text-transform:uppercase;letter-spacing:1px;">{source}</p>
          <h2 style="margin:0 0 16px 0;font-size:22px;font-weight:800;color:#fff;line-height:1.2;">{title}</h2>

          <!-- Score badge -->
          <div style="display:inline-block;background:#22c55e;color:#fff;padding:6px 16px;
                      border-radius:8px;font-size:16px;font-weight:900;margin-bottom:20px;">
            Score {score}/10 &nbsp;·&nbsp; BUY
          </div>

          <!-- Key numbers grid -->
          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
            <tr>
              <td width="50%" style="padding:0 8px 12px 0;">
                <div style="background:#09090b;border:1px solid #27272a;border-radius:8px;padding:14px;">
                  <p style="margin:0 0 2px 0;font-size:10px;color:#71717a;text-transform:uppercase;letter-spacing:1px;">Auction Price</p>
                  <p style="margin:0;font-size:22px;font-weight:900;color:#fff;">{price}</p>
                </div>
              </td>
              <td width="50%" style="padding:0 0 12px 8px;">
                <div style="background:#09090b;border:1px solid #27272a;border-radius:8px;padding:14px;">
                  <p style="margin:0 0 2px 0;font-size:10px;color:#71717a;text-transform:uppercase;letter-spacing:1px;">Market Value</p>
                  <p style="margin:0;font-size:22px;font-weight:900;color:#fff;">{market_value}</p>
                </div>
              </td>
            </tr>
            <tr>
              <td width="50%" style="padding:0 8px 12px 0;">
                <div style="background:#22c55e10;border:1px solid #22c55e30;border-radius:8px;padding:14px;">
                  <p style="margin:0 0 2px 0;font-size:10px;color:#22c55e;text-transform:uppercase;letter-spacing:1px;">Best Profit</p>
                  <p style="margin:0;font-size:22px;font-weight:900;color:#22c55e;">{profit_best}</p>
                </div>
              </td>
              <td width="50%" style="padding:0 0 12px 8px;">
                <div style="background:#09090b;border:1px solid #27272a;border-radius:8px;padding:14px;">
                  <p style="margin:0 0 2px 0;font-size:10px;color:#71717a;text-transform:uppercase;letter-spacing:1px;">Worst Profit</p>
                  <p style="margin:0;font-size:22px;font-weight:900;color:#fff;">{profit_worst}</p>
                </div>
              </td>
            </tr>
          </table>

          <!-- Details row -->
          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
            <tr>
              <td style="padding:0 6px 8px 0;width:25%;">
                <p style="margin:0 0 2px 0;font-size:10px;color:#71717a;">ROI</p>
                <p style="margin:0;font-size:14px;font-weight:700;color:#fff;">{roi_str}</p>
              </td>
              <td style="padding:0 6px 8px 0;width:25%;">
                <p style="margin:0 0 2px 0;font-size:10px;color:#71717a;">Mileage</p>
                <p style="margin:0;font-size:14px;font-weight:700;color:#fff;">{mileage}</p>
              </td>
              <td style="padding:0 6px 8px 0;width:25%;">
                <p style="margin:0 0 2px 0;font-size:10px;color:#71717a;">Colour</p>
                <p style="margin:0;font-size:14px;font-weight:700;color:#fff;">{colour}</p>
              </td>
              <td style="padding:0 0 8px 0;width:25%;">
                <p style="margin:0 0 2px 0;font-size:10px;color:#71717a;">Title</p>
                <p style="margin:0;font-size:14px;font-weight:700;color:#fff;">{brand or 'N/A'}</p>
              </td>
            </tr>
            {"" if damage == "N/A" else f'''<tr><td colspan="4">
                <p style="margin:0 0 2px 0;font-size:10px;color:#71717a;">Damage</p>
                <p style="margin:0;font-size:14px;font-weight:700;color:#f59e0b;">{damage}</p>
              </td></tr>'''}
          </table>

          <!-- CTAs -->
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td width="50%" style="padding-right:8px;">
                <a href="{app_url}"
                   style="display:block;background:#2563eb;color:#fff;text-align:center;
                          padding:12px 0;border-radius:8px;font-weight:700;font-size:14px;
                          text-decoration:none;">
                  View in AutoFlip →
                </a>
              </td>
              <td width="50%" style="padding-left:8px;">
                <a href="{listing_url}"
                   style="display:block;background:#27272a;color:#fff;text-align:center;
                          padding:12px 0;border-radius:8px;font-weight:700;font-size:14px;
                          text-decoration:none;">
                  Auction Listing ↗
                </a>
              </td>
            </tr>
          </table>

        </td></tr>

        <!-- Footer -->
        <tr><td style="padding:16px 24px;border-top:1px solid #27272a;text-align:center;">
          <p style="margin:0 0 4px 0;font-size:11px;color:#52525b;">
            AutoFlip Intelligence · Ontario, Canada
          </p>
          <p style="margin:0;font-size:11px;color:#3f3f46;">
            You're receiving this because you subscribed to BUY deal alerts.
            <a href="{FRONTEND_URL}/unsubscribe" style="color:#71717a;">Unsubscribe</a>
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _build_deal_alert_text(listing: dict) -> str:
    """Plain-text fallback for the deal alert email."""
    title = listing.get("title", "Vehicle")
    price = _format_currency(listing.get("price"))
    profit_best = _format_currency(listing.get("profit_best"))
    score = listing.get("deal_score", "?")
    listing_url = listing.get("url", "#")
    source = listing.get("source", "auction").replace("_", " ").title()
    return (
        f"🔥 BUY DEAL ALERT — AutoFlip Intelligence\n"
        f"{'=' * 48}\n\n"
        f"{title}\n"
        f"Source: {source}\n"
        f"Score: {score}/10 (BUY)\n\n"
        f"Auction Price: {price}\n"
        f"Best Profit:   {profit_best}\n\n"
        f"View listing: {listing_url}\n\n"
        f"—\nAutoFlip Intelligence · Ontario, Canada\n"
        f"To unsubscribe: {FRONTEND_URL}/unsubscribe\n"
    )


async def send_deal_alert_sendgrid(to_email: str, listing: dict) -> bool:
    """Send a deal alert email via SendGrid. Returns True on success."""
    if not SENDGRID_API_KEY:
        return False
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email, To, Content

        title = listing.get("title", "Vehicle")
        subject = f"🔥 BUY Deal: {title} — Score {listing.get('deal_score', '?')}/10"

        message = Mail(
            from_email=Email(EMAIL_FROM, EMAIL_FROM_NAME),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", _build_deal_alert_html(listing)),
            plain_text_content=Content("text/plain", _build_deal_alert_text(listing)),
        )

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        if response.status_code in (200, 202):
            logger.info("Deal alert sent via SendGrid to %s (listing: %s)", to_email, title)
            return True
        else:
            logger.warning("SendGrid returned status %s for %s", response.status_code, to_email)
            return False
    except Exception as e:
        logger.error("SendGrid send failed for %s: %s", to_email, e)
        return False


async def send_deal_alert_smtp(to_email: str, listing: dict) -> bool:
    """Send a deal alert email via SMTP (Gmail / Outlook / custom).
    Returns True on success. Falls back gracefully if not configured."""
    if not SMTP_USER or not SMTP_PASSWORD:
        return False
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        title = listing.get("title", "Vehicle")
        subject = f"🔥 BUY Deal: {title} — Score {listing.get('deal_score', '?')}/10"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{EMAIL_FROM_NAME} <{SMTP_USER}>"
        msg["To"] = to_email

        msg.attach(MIMEText(_build_deal_alert_text(listing), "plain"))
        msg.attach(MIMEText(_build_deal_alert_html(listing), "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())

        logger.info("Deal alert sent via SMTP to %s (listing: %s)", to_email, title)
        return True
    except Exception as e:
        logger.error("SMTP send failed for %s: %s", to_email, e)
        return False


async def send_deal_alert(to_email: str, listing: dict) -> bool:
    """
    Send a BUY deal alert email to a single subscriber.

    Priority: SendGrid → SMTP → silent skip (no crash).
    Returns True if sent, False if skipped/failed.
    """
    if not SENDGRID_API_KEY and (not SMTP_USER or not SMTP_PASSWORD):
        logger.warning(
            "Email alerts disabled — set SENDGRID_API_KEY or SMTP_USER+SMTP_PASSWORD in .env"
        )
        return False

    # Try SendGrid first
    if SENDGRID_API_KEY:
        return await send_deal_alert_sendgrid(to_email, listing)

    # Fall back to SMTP
    return await send_deal_alert_smtp(to_email, listing)
