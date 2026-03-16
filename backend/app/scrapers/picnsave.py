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


async def scrape_picnsave() -> list:
    """Scrape Pic N Save rebuildable cars (all pages)."""
    listings = []
    page = 1
    max_pages = 10

    try:
        async with httpx.AsyncClient(timeout=30, headers=HEADERS, follow_redirects=True) as http:
            while page <= max_pages:
                url = "https://picnsave.ca/rebuildable-cars/"
                if page > 1:
                    url += f"page/{page}/"

                resp = await http.get(url)
                if resp.status_code != 200:
                    break

                soup = BeautifulSoup(resp.text, 'html.parser')
                products = soup.find_all('li', class_=lambda c: c and 'product' in str(c))

                if not products:
                    break

                for prod in products:
                    title_el = prod.find('h2')
                    title = title_el.get_text(strip=True) if title_el else ""
                    if not title:
                        continue

                    price_el = prod.find(class_='woocommerce-Price-amount') or prod.find(class_='price')
                    price_text = price_el.get_text(strip=True) if price_el else ""
                    price = parse_price(price_text)

                    link_el = prod.find('a', href=True)
                    detail_url = link_el['href'] if link_el else ""

                    img_el = prod.find('img', src=True)
                    photo = img_el.get('src', '') if img_el else ""
                    if photo and 'placeholder' in photo.lower():
                        photo = ""

                    all_text = prod.get_text(separator='|', strip=True)
                    brand = ""
                    mileage_text = ""
                    for part in all_text.split('|'):
                        part = part.strip()
                        if part.lower().startswith('brand:'):
                            brand = part.split(':', 1)[1].strip()
                        elif part.lower().startswith('mileage:'):
                            mileage_text = part.split(':', 1)[1].strip()

                    mileage = parse_mileage(mileage_text)
                    year = extract_year(title)

                    damage = ""
                    description = ""
                    detail_photos = []
                    if detail_url:
                        await asyncio.sleep(0.5)
                        try:
                            detail_resp = await http.get(detail_url)
                            if detail_resp.status_code == 200:
                                dsoup = BeautifulSoup(detail_resp.text, 'html.parser')
                                desc_el = dsoup.find(class_='woocommerce-product-details__short-description') or dsoup.find(class_='product_meta')
                                if desc_el:
                                    desc_text = desc_el.get_text(strip=True)
                                    description = desc_text[:500]
                                    for line in desc_text.split('\n'):
                                        if 'damage' in line.lower().strip():
                                            damage = line.strip()

                                for el in dsoup.find_all(['p', 'div', 'span']):
                                    text = el.get_text(strip=True)
                                    if 'damage' in text.lower() and len(text) < 100:
                                        damage = text.split(':')[-1].strip() if ':' in text else text

                                for img in dsoup.find_all('img', src=True):
                                    src = img['src']
                                    if 'wp-content/uploads' in src and 'placeholder' not in src.lower() and src not in detail_photos:
                                        detail_photos.append(src)
                        except Exception as e:
                            logger.warning(f"  PicNSave detail failed {detail_url}: {e}")

                    listing = {
                        "source": "picnsave",
                        "url": detail_url,
                        "title": title,
                        "price": price,
                        "price_raw": price_text,
                        "status": "for_sale",
                        "colour": "",
                        "mileage": mileage,
                        "damage": damage,
                        "brand": brand,
                        "description": description,
                        "photo": detail_photos[0] if detail_photos else photo,
                        "photos": detail_photos[:5] if detail_photos else ([photo] if photo else []),
                        "year": year,
                    }
                    listings.append(listing)
                    logger.info(f"  Scraped: {title} - ${price}")

                next_page = soup.find('a', class_='next')
                if not next_page:
                    break
                page += 1
                await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"PicNSave scraper error: {e}")
    return listings
