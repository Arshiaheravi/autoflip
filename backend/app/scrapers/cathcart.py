import re
import logging
import asyncio
import httpx
from bs4 import BeautifulSoup
from ..utils.parsers import parse_price, parse_mileage, extract_year

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


async def scrape_cathcart(page_url: str, source_name: str) -> list:
    """Scrape Cathcart Auto listing page and detail pages."""
    listings = []
    try:
        async with httpx.AsyncClient(timeout=30, headers=HEADERS, follow_redirects=True) as http:
            resp = await http.get(page_url)
            if resp.status_code != 200:
                logger.error(f"Failed to fetch {page_url}: {resp.status_code}")
                return []
            soup = BeautifulSoup(resp.text, 'html.parser')

            h1_tags = soup.find_all('h1')
            card_data = {}

            for h1 in h1_tags:
                title = h1.get_text(strip=True)
                if not title or len(title) < 5:
                    continue
                year = extract_year(title)
                if not year:
                    continue

                search = h1
                link_el = None
                for _ in range(8):
                    search = search.parent
                    if not search:
                        break
                    link_el = search.find('a', href=lambda h: h and '/inventory/' in h)
                    if link_el:
                        break

                url = link_el['href'] if link_el else None
                if not url:
                    continue

                container = h1.parent
                h3s = []
                for _ in range(5):
                    if not container:
                        break
                    h3s = container.find_all('h3')
                    if h3s:
                        break
                    container = container.parent

                price_text = ""
                status = "for_sale"
                if h3s:
                    for h3 in h3s:
                        h3_text = h3.get_text(strip=True)
                        if '$' in h3_text or 'AS IS' in h3_text.upper() or 'PLUS HST' in h3_text.upper():
                            price_text = h3_text
                        elif 'COMING SOON' in h3_text.upper():
                            status = "coming_soon"
                        elif 'FOR SALE' in h3_text.upper():
                            status = "for_sale"
                        elif 'SOLD' in h3_text.upper():
                            status = "sold"

                photo = None
                if link_el:
                    img = link_el.find('img', src=lambda s: s and 'wp-content/uploads' in s and 'logo' not in s)
                    if img:
                        photo = img['src']
                if not photo and container:
                    img = container.find('img', src=lambda s: s and 'wp-content/uploads' in s and 'logo' not in s)
                    if img:
                        photo = img['src']

                card_data[url] = {
                    "title": title,
                    "price_text": price_text,
                    "status": status,
                    "photo": photo,
                    "url": url,
                }

            for url, card in card_data.items():
                await asyncio.sleep(0.5)
                try:
                    detail_resp = await http.get(url)
                    if detail_resp.status_code != 200:
                        continue
                    detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')

                    colour = ""
                    mileage_text = ""
                    damage = ""
                    brand = ""
                    description = ""

                    for strong in detail_soup.find_all('strong'):
                        label = strong.get_text(strip=True).lower().rstrip(':')
                        sibling_text = ""
                        for sib in strong.next_siblings:
                            if hasattr(sib, 'get_text'):
                                t = sib.get_text(strip=True)
                            else:
                                t = str(sib).strip()
                            if t:
                                sibling_text = t
                                break

                        if 'colour' in label:
                            colour = sibling_text
                        elif 'mileage' in label:
                            mileage_text = sibling_text
                        elif 'damage' in label:
                            damage = sibling_text
                        elif 'brand' in label:
                            brand = sibling_text
                        elif 'description' in label:
                            parent_text = strong.parent.get_text(strip=True) if strong.parent else ""
                            desc_match = re.split(r'description:', parent_text, flags=re.IGNORECASE)
                            if len(desc_match) > 1:
                                description = desc_match[1].strip()[:500]

                    photos = []
                    for img in detail_soup.find_all('img', src=True):
                        src = img['src']
                        if 'wp-content/uploads' in src and 'logo' not in src.lower():
                            if src not in photos:
                                photos.append(src)

                    price = parse_price(card["price_text"])
                    mileage = parse_mileage(mileage_text)
                    year = extract_year(card["title"])

                    listing = {
                        "source": source_name,
                        "url": url,
                        "title": card["title"],
                        "price": price,
                        "price_raw": card["price_text"],
                        "status": card["status"],
                        "colour": colour,
                        "mileage": mileage,
                        "damage": damage,
                        "brand": brand,
                        "description": description,
                        "photo": photos[0] if photos else card.get("photo"),
                        "photos": photos[:5],
                        "year": year,
                    }
                    listings.append(listing)
                    logger.info(f"  Scraped: {card['title']} - ${price}")

                except Exception as e:
                    logger.warning(f"  Failed detail page {url}: {e}")
                    price = parse_price(card["price_text"])
                    year = extract_year(card["title"])
                    listings.append({
                        "source": source_name, "url": url, "title": card["title"],
                        "price": price, "price_raw": card["price_text"], "status": card["status"],
                        "colour": "", "mileage": None, "damage": "", "brand": "",
                        "description": "", "photo": card.get("photo"), "photos": [],
                        "year": year,
                    })

    except Exception as e:
        logger.error(f"Scraper error for {page_url}: {e}")
    return listings
