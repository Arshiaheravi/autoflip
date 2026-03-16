import re
from typing import Optional


def parse_price(text: str) -> Optional[float]:
    if not text:
        return None
    text_lower = text.lower()
    if "####" in text or "on sale" in text_lower or "call" in text_lower:
        return None
    price_part = text
    for split_word in ["AS IS", "PLUS", "Plus", "plus"]:
        if split_word in price_part:
            price_part = price_part.split(split_word)[0]
    price_part = price_part.strip()
    dollar_match = re.search(r'\$([\d.,]+)', price_part)
    if dollar_match:
        num_str = dollar_match.group(1)
        dot_count = num_str.count('.')
        if dot_count > 1:
            parts = num_str.split('.')
            if len(parts[-1]) == 2:
                whole = ''.join(parts[:-1])
                num_str = whole + '.' + parts[-1]
            else:
                num_str = num_str.replace('.', '').replace(',', '')
        elif dot_count == 1:
            num_str = num_str.replace(',', '')
        else:
            num_str = num_str.replace(',', '')
        try:
            val = float(num_str)
            if val > 100:
                return val
        except ValueError:
            pass
    return None


def parse_mileage(text: str) -> Optional[int]:
    if not text:
        return None
    clean = text.replace(",", "").replace(" ", "").replace("km", "").replace("KM", "")
    match = re.search(r'(\d+)', clean)
    if match:
        return int(match.group(1))
    return None


def extract_year(title: str) -> Optional[int]:
    match = re.search(r'(19|20)\d{2}', title)
    if match:
        return int(match.group(0))
    return None
