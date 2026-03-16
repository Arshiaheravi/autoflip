import base64
import logging
import os
import httpx
import anthropic as _anthropic

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


async def detect_damage_from_photo(photo_urls, source: str = "", brand_status: str = "") -> dict:
    """Use Claude vision to analyze multiple car photos and detect damage type + severity."""
    # Disabled — returns empty result, no API calls made
    return {"damage": "", "severity": "unknown", "confidence": 0}
    if not ANTHROPIC_API_KEY:
        return {"damage": "", "severity": "unknown", "confidence": 0}

    if isinstance(photo_urls, str):
        photo_urls = [photo_urls]
    photo_urls = [u for u in photo_urls if u][:3]
    if not photo_urls:
        return {"damage": "", "severity": "unknown", "confidence": 0}

    try:
        image_blocks = []
        async with httpx.AsyncClient(timeout=15, headers=HEADERS, follow_redirects=True) as http:
            for url in photo_urls:
                try:
                    resp = await http.get(url)
                    if resp.status_code == 200:
                        content_type = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
                        if content_type not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
                            content_type = "image/jpeg"
                        img_b64 = base64.standard_b64encode(resp.content).decode('utf-8')
                        image_blocks.append({
                            "type": "image",
                            "source": {"type": "base64", "media_type": content_type, "data": img_b64}
                        })
                except Exception:
                    continue

        if not image_blocks:
            return {"damage": "", "severity": "unknown", "confidence": 0}

        is_salvage_lot = source in ("cathcart_rebuilders", "picnsave") or (brand_status and "SALVAGE" in brand_status.upper())
        context_note = ""
        if is_salvage_lot:
            context_note = (
                "CRITICAL CONTEXT: This vehicle is listed on a SALVAGE / REBUILDABLE car lot. "
                "It almost certainly has damage — it would not be on a salvage lot otherwise. "
                "Look very carefully for: dents, misaligned panels, scratches, paint damage, "
                "cracked bumpers, broken lights, rust, frame damage, missing parts, "
                "flood marks, fire damage, broken glass, airbag deployment signs. "
                "Even if the damage looks minor, REPORT IT. Do NOT say NONE unless the vehicle "
                "is genuinely perfect (extremely unlikely for a salvage lot car). "
            )

        system_prompt = (
            "You are an expert automotive damage assessor specializing in salvage and insurance vehicles. "
            f"{context_note}"
            "Analyze ALL provided photos of this vehicle and respond ONLY with a JSON object (no markdown, no explanation) with these fields:\n"
            '{"damage_type": "FRONT|REAR|LEFT FRONT|RIGHT FRONT|LEFT REAR|RIGHT REAR|LEFT SIDE|RIGHT SIDE|LEFT DOORS|RIGHT DOORS|ROLLOVER|FIRE|FLOOD|ROOF|UNDERCARRIAGE|NONE", '
            '"severity": "minor|moderate|severe|total", '
            '"confidence": 0.0-1.0, '
            '"details": "specific description of damage observed across all photos"}\n'
            "If multiple damage areas exist, pick the PRIMARY / most costly one for damage_type. "
            "Be specific in details — mention crumpled panels, broken headlights, airbag deployment, etc."
        )

        user_content = image_blocks + [{
            "type": "text",
            "text": f"Analyze these {len(image_blocks)} photo(s) of a vehicle from a {'salvage/rebuildable' if is_salvage_lot else 'used car'} lot. Identify the primary damage area and severity. Return only the JSON."
        }]

        client = _anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model="claude-opus-4-6",
            max_tokens=512,
            thinking={"type": "adaptive"},
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}]
        )

        import json
        response_text = next((b.text for b in response.content if b.type == "text"), "")
        clean = response_text.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
            clean = clean.rsplit("```", 1)[0]
        result = json.loads(clean)
        logger.info(f"  AI damage detection ({len(image_blocks)} photos): {result.get('damage_type')} ({result.get('severity')}) conf={result.get('confidence')}")
        return {
            "damage": result.get("damage_type", ""),
            "severity": result.get("severity", "unknown"),
            "confidence": result.get("confidence", 0),
            "details": result.get("details", ""),
        }
    except Exception as e:
        logger.warning(f"  AI damage detection failed: {e}")
        return {"damage": "", "severity": "unknown", "confidence": 0}
