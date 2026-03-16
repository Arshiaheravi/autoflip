from datetime import datetime
from typing import Optional

# ─── MSRP Reference Data (Canadian $, approximate new base MSRP) ───
MSRP_DATA = {
    "civic": 30000, "corolla": 28000, "camry": 35000, "accord": 40000,
    "cr-v": 38000, "crv": 38000, "rav4": 38000, "rav-4": 38000,
    "highlander": 48000, "tacoma": 45000, "tundra": 55000, "4runner": 52000,
    "land cruiser": 75000, "landcruiser": 75000, "prius": 36000,
    "sienna": 48000, "forester": 38000, "outback": 40000, "impreza": 30000,
    "wrx": 38000, "crosstrek": 34000, "mazda3": 28000, "cx-5": 36000, "cx5": 36000,
    "cx-30": 30000, "cx-50": 42000, "cx-90": 50000,
    "rogue": 36000, "pathfinder": 46000, "sentra": 24000, "altima": 34000,
    "frontier": 42000, "murano": 44000,
    "elantra": 26000, "sonata": 34000, "tucson": 36000, "santa fe": 42000,
    "palisade": 52000, "kona": 30000, "ioniq": 45000,
    "forte": 25000, "k5": 34000, "sportage": 36000, "sorento": 42000,
    "telluride": 52000, "seltos": 30000, "carnival": 45000, "niro": 35000,
    "f150": 52000, "f-150": 52000, "f250": 62000, "f-250": 62000,
    "escape": 36000, "edge": 42000, "explorer": 48000, "bronco": 48000,
    "mustang": 38000, "ranger": 42000, "maverick": 32000,
    "silverado": 52000, "equinox": 38000, "traverse": 44000, "blazer": 42000,
    "colorado": 40000, "tahoe": 65000, "suburban": 70000,
    "trax": 28000, "malibu": 30000,
    "sierra": 55000, "terrain": 38000, "acadia": 44000, "yukon": 68000,
    "ram": 52000, "ram 1500": 52000, "ram 2500": 60000,
    "wrangler": 48000, "grand cherokee": 55000, "cherokee": 42000,
    "gladiator": 50000, "compass": 36000,
    "challenger": 42000, "charger": 42000, "durango": 48000,
    "3 series": 52000, "5 series": 68000, "x1": 46000, "x3": 52000, "x5": 72000,
    "c-class": 52000, "e-class": 70000, "glc": 55000, "gle": 70000,
    "a3": 40000, "a4": 48000, "q3": 42000, "q5": 50000, "q7": 65000,
    "golf": 32000, "jetta": 28000, "tiguan": 36000, "atlas": 44000, "taos": 32000,
    "rx350": 60000, "rx": 60000, "nx": 48000, "es": 50000, "is": 45000,
    "rdx": 48000, "mdx": 58000, "tlx": 48000,
    "xt4": 42000, "xt5": 52000, "xt6": 58000, "escalade": 85000,
    "model 3": 50000, "model y": 55000, "model s": 95000, "model x": 100000,
    "sidewinder": 22000, "ski doo": 18000, "ski-doo": 18000, "backcountry": 20000,
    "cooper": 32000, "mini": 32000,
}

BRAND_RETENTION = {
    "toyota": 1.18, "lexus": 1.22, "honda": 1.14, "acura": 1.08,
    "subaru": 1.12, "mazda": 1.06, "porsche": 1.25,
    "jeep": 1.08, "ram": 1.05, "gmc": 1.02, "ford": 0.98,
    "chevrolet": 0.92, "dodge": 0.88, "chrysler": 0.82,
    "hyundai": 0.96, "hyundia": 0.96, "kia": 0.94, "nissan": 0.90, "mitsubishi": 0.82,
    "bmw": 0.92, "mercedes": 0.90, "audi": 0.88,
    "volkswagen": 0.88, "volkswagon": 0.88, "volvo": 0.90,
    "tesla": 1.05, "cadillac": 0.85, "buick": 0.82,
    "lincoln": 0.82, "infiniti": 0.80, "genesis": 0.88,
    "fiat": 0.68, "jaguar": 0.70, "land rover": 0.72,
    "yamaha": 0.85, "ski-doo": 0.80, "mini": 0.78,
}

BODY_TYPE_KEYWORDS = {
    1.30: ["f150", "f-150", "f250", "f-250", "sierra", "silverado", "ram 1500", "ram 2500", "tundra", "tacoma", "ranger", "frontier", "colorado", "gladiator", "maverick"],
    1.20: ["wrangler", "4runner", "land cruiser", "landcruiser", "bronco"],
    1.15: ["rav4", "rav-4", "crv", "cr-v", "forester", "rogue", "escape", "equinox", "sportage", "tucson", "cx-5", "cx5", "crosstrek", "seltos", "kona", "taos", "cx-30"],
    1.12: ["highlander", "grand cherokee", "palisade", "telluride", "explorer", "traverse", "pathfinder", "santa fe", "sorento", "tahoe", "suburban", "yukon", "4 runner"],
    1.08: ["hybrid", "plug in", "plug-in", "hev", "phev"],
    1.05: ["sienna", "odyssey", "carnival", "van", "promaster", "transit"],
    0.95: ["sedan", "civic", "corolla", "sentra", "elantra", "forte", "accent", "jetta", "mazda3"],
    0.90: ["coupe", "convertible"],
}

TRIM_TIERS = {
    1.25: ["limited", "platinum", "calligraphy", "ultimate", "denali", "king ranch", "high country", "pinnacle"],
    1.15: ["lariat", "sport", "gt", "rs", "performance", "st", "type r", "type-r", "trd pro", "trail boss", "rubicon", "sahara", "overland"],
    1.10: ["se", "sel", "xlt", "ex", "ex-l", "touring", "preferred", "premium", "awd", "4x4", "all wheel"],
    1.05: ["le", "xle", "sx", "lx", "base"],
}

COLOR_MULTIPLIER = {
    "white": 1.04, "black": 1.03, "silver": 1.02, "grey": 1.02, "gray": 1.02,
    "blue": 1.00, "red": 0.99, "dark blue": 1.01, "dark grey": 1.02,
    "brown": 0.95, "beige": 0.94, "gold": 0.93, "orange": 0.93,
    "green": 0.93, "yellow": 0.91, "purple": 0.90, "pink": 0.88,
}

DEPRECIATION_CURVE = {
    0: 1.00, 1: 0.82, 2: 0.72, 3: 0.63, 4: 0.55, 5: 0.48,
    6: 0.42, 7: 0.37, 8: 0.32, 9: 0.28, 10: 0.25,
    11: 0.22, 12: 0.19, 13: 0.17, 14: 0.15, 15: 0.13,
    16: 0.11, 17: 0.10, 18: 0.09, 19: 0.08, 20: 0.07,
}

REPAIR_COST_MAP = {
    "FRONT":          [3000, 6500],
    "FRONT END":      [3000, 6500],
    "LEFT FRONT":     [2800, 6000],
    "RIGHT FRONT":    [2800, 6000],
    "REAR":           [2000, 4500],
    "LEFT REAR":      [2000, 4500],
    "RIGHT REAR":     [2000, 4500],
    "LEFT DOORS":     [1500, 3500],
    "RIGHT DOORS":    [1500, 3500],
    "DOORS":          [1500, 3500],
    "LEFT SIDE":      [2000, 4500],
    "RIGHT SIDE":     [2000, 4500],
    "ROOF":           [2500, 6000],
    "UNDERCARRIAGE":  [3000, 7000],
    "ROLLOVER":       [6000, 16000],
    "FIRE":           [4000, 12000],
    "FLOOD":          [4000, 12000],
}
DEFAULT_REPAIR = [500, 1500]

SAFETY_INSPECTION_COST = 100
STRUCTURAL_INSPECTION_COST = 400
VIN_VERIFICATION_COST = 75
APPRAISAL_FEE = 150
OMVIC_FEE = 22
MTO_TRANSFER_FEE = 32
REBUILT_TITLE_PROCESS = STRUCTURAL_INSPECTION_COST + VIN_VERIFICATION_COST + APPRAISAL_FEE


def _find_msrp(title_lower: str) -> Optional[float]:
    best_match = None
    best_len = 0
    for model, msrp in MSRP_DATA.items():
        if model in title_lower and len(model) > best_len:
            best_match = msrp
            best_len = len(model)
    return best_match


def _get_brand(title_lower: str) -> tuple:
    for brand, mult in BRAND_RETENTION.items():
        if brand in title_lower:
            return brand, mult
    return "unknown", 0.90


def _get_body_type_mult(title_lower: str) -> float:
    for mult, keywords in BODY_TYPE_KEYWORDS.items():
        if any(k in title_lower for k in keywords):
            return mult
    return 1.0


def _get_trim_mult(title_lower: str) -> float:
    for mult, keywords in TRIM_TIERS.items():
        if any(k in title_lower for k in keywords):
            return mult
    return 1.0


def _get_color_mult(colour: str) -> float:
    if not colour:
        return 1.0
    c = colour.lower().strip()
    for color_name, mult in COLOR_MULTIPLIER.items():
        if color_name in c:
            return mult
    return 0.97


def _get_depreciation(age: int) -> float:
    if age <= 0:
        return 1.0
    if age in DEPRECIATION_CURVE:
        return DEPRECIATION_CURVE[age]
    if age > 20:
        return max(0.04, 0.07 - (age - 20) * 0.005)
    return 0.07


def _get_mileage_adjustment(mileage: int, age: int) -> float:
    if not mileage or mileage <= 0:
        return 1.0
    avg_km_year = 18000
    expected = max(avg_km_year, age * avg_km_year)
    ratio = mileage / expected
    if ratio <= 0.5:
        return 1.08
    elif ratio <= 0.7:
        return 1.05
    elif ratio <= 0.9:
        return 1.02
    elif ratio <= 1.1:
        return 1.00
    elif ratio <= 1.3:
        return 0.96
    elif ratio <= 1.5:
        return 0.92
    elif ratio <= 1.8:
        return 0.87
    elif ratio <= 2.0:
        return 0.82
    else:
        return max(0.70, 0.82 - (ratio - 2.0) * 0.06)


def estimate_market_value(title: str, year: int, mileage: int = None,
                          colour: str = "", brand_status: str = "") -> dict:
    current_year = datetime.now().year
    age = max(0, current_year - year)
    title_lower = title.lower()

    msrp = _find_msrp(title_lower)
    msrp_source = "model_match"
    if not msrp:
        _, brand_mult = _get_brand(title_lower)
        body_mult = _get_body_type_mult(title_lower)
        msrp = 35000 * brand_mult * body_mult
        msrp_source = "estimated"

    dep_factor = _get_depreciation(age)
    brand_name, brand_mult = _get_brand(title_lower)
    body_mult = _get_body_type_mult(title_lower)
    trim_mult = _get_trim_mult(title_lower)
    color_mult = _get_color_mult(colour)
    mileage_mult = _get_mileage_adjustment(mileage, age) if mileage else 1.0

    clean_value = msrp * dep_factor * brand_mult * body_mult * trim_mult * color_mult * mileage_mult

    is_salvage = brand_status and "SALVAGE" in brand_status.upper()
    is_rebuilt = brand_status and "REBUILT" in brand_status.upper()
    title_mult = 1.0
    title_note = "clean_title"
    if is_salvage:
        title_mult = 0.55
        title_note = "salvage_title"
    elif is_rebuilt:
        title_mult = 0.75
        title_note = "rebuilt_title"

    formula_value = round(clean_value * title_mult, 0)
    formula_value = max(formula_value, 800)

    return {
        "market_value": formula_value,
        "formula_value": formula_value,
        "autotrader_median": None,
        "autotrader_count": 0,
        "blend_method": "formula_only",
        "msrp": round(msrp, 0),
        "msrp_source": msrp_source,
        "depreciation": round(dep_factor, 3),
        "brand": brand_name,
        "brand_mult": brand_mult,
        "body_mult": body_mult,
        "trim_mult": trim_mult,
        "color_mult": color_mult,
        "mileage_mult": round(mileage_mult, 3),
        "title_status": title_note,
        "title_mult": title_mult,
        "age": age,
    }


def get_repair_range(damage_text: str, severity: str = "", is_salvage: bool = False) -> tuple:
    base_low = 0
    base_high = 0
    damage_source = "listed"

    if not damage_text or damage_text.strip() == "" or damage_text.upper() == "NONE":
        base_low, base_high = DEFAULT_REPAIR
        damage_source = "none"
    else:
        d = damage_text.upper().strip()
        matched = False
        for key, val in REPAIR_COST_MAP.items():
            if key in d:
                base_low, base_high = val
                matched = True
                break
        if not matched:
            if "ROLL" in d:
                base_low, base_high = 6000, 16000
            elif "FIRE" in d or "BURN" in d:
                base_low, base_high = 4000, 12000
            elif "FLOOD" in d or "WATER" in d:
                base_low, base_high = 4000, 12000
            elif "HIT" in d or "IMPACT" in d or "COLLISION" in d:
                base_low, base_high = 2500, 5500
            elif "RUST" in d:
                base_low, base_high = 1500, 4500
            elif "REAR" in d:
                base_low, base_high = 2000, 4500
            elif "SIDE" in d or "DOOR" in d:
                base_low, base_high = 1500, 3500
            elif "ROOF" in d:
                base_low, base_high = 2500, 6000
            else:
                base_low, base_high = 2000, 5000
                damage_source = "unknown_type"

    sev_mult = 1.0
    if severity:
        sev = severity.lower()
        if sev == "minor":
            sev_mult = 0.7
        elif sev == "moderate":
            sev_mult = 1.0
        elif sev == "severe":
            sev_mult = 1.4
        elif sev == "total":
            sev_mult = 1.8

    repair_low = round(base_low * sev_mult)
    repair_high = round(base_high * sev_mult)

    safety = SAFETY_INSPECTION_COST
    salvage_process = REBUILT_TITLE_PROCESS if is_salvage else 0

    total_low = repair_low + safety + salvage_process
    total_high = repair_high + safety + salvage_process

    breakdown = {
        "repair_labour_parts_low": repair_low,
        "repair_labour_parts_high": repair_high,
        "safety_inspection": safety,
        "salvage_to_rebuilt_cost": salvage_process,
        "severity_applied": severity or "moderate",
        "damage_source": damage_source,
    }
    return total_low, total_high, breakdown


def calculate_ontario_fees(purchase_price: float, is_salvage: bool = False) -> dict:
    hst = round(purchase_price * 0.13, 2)
    return {
        "hst": hst,
        "omvic": OMVIC_FEE,
        "mto_transfer": MTO_TRANSFER_FEE,
        "safety_cert": SAFETY_INSPECTION_COST,
        "total": round(hst + OMVIC_FEE + MTO_TRANSFER_FEE + SAFETY_INSPECTION_COST, 0),
    }


def calc_deal_score(best_profit: float, worst_profit: float, roi_best: float = 0) -> tuple:
    avg_profit = (best_profit + worst_profit) / 2

    if avg_profit >= 5000:
        score = 10
    elif avg_profit >= 4000:
        score = 9
    elif avg_profit >= 3000:
        score = 8
    elif avg_profit >= 2000:
        score = 7
    elif avg_profit >= 1200:
        score = 6
    elif avg_profit >= 500:
        score = 5
    elif avg_profit >= 0:
        score = 4
    elif avg_profit >= -500:
        score = 3
    elif avg_profit >= -1500:
        score = 2
    else:
        score = 1

    if roi_best and roi_best > 100:
        score = min(10, score + 2)
    elif roi_best and roi_best > 60:
        score = min(10, score + 1)
    elif roi_best and roi_best < -30:
        score = max(1, score - 2)
    elif roi_best and roi_best < -10:
        score = max(1, score - 1)

    if worst_profit < -2000 and score > 3:
        score = max(3, score - 1)

    if score >= 8:
        label = "BUY"
    elif score >= 5:
        label = "WATCH"
    else:
        label = "SKIP"
    return score, label
