"""
attribute_parser.py
Normalizes raw text from product pages into structured apparel attributes.
No external API calls — pure regex + keyword matching.
"""
import re
from typing import Optional


# ── Color normalization ───────────────────────────────────────
COLOR_FAMILY_MAP = {
    "black": ["black", "charcoal", "onyx", "jet"],
    "white": ["white", "cream", "ivory", "off-white", "snow"],
    "grey":  ["grey", "gray", "ash", "silver", "slate"],
    "blue":  ["blue", "navy", "cobalt", "royal blue", "sky blue", "denim", "teal", "indigo"],
    "red":   ["red", "crimson", "burgundy", "maroon", "wine", "scarlet"],
    "green": ["green", "olive", "forest", "mint", "sage", "khaki"],
    "pink":  ["pink", "rose", "blush", "coral", "mauve"],
    "yellow":["yellow", "mustard", "gold", "amber", "lemon"],
    "orange":["orange", "rust", "terracotta", "peach"],
    "purple":["purple", "lavender", "violet", "plum"],
    "brown": ["brown", "tan", "camel", "mocha", "chocolate", "beige"],
    "multi": ["multicolor", "multi", "print", "tie-dye", "ombre"],
}

# ── Material normalization ────────────────────────────────────
MATERIAL_FAMILY_MAP = {
    "cotton":    ["cotton", "100% cotton", "pure cotton"],
    "polyester": ["polyester", "poly"],
    "blend":     ["blend", "mixed", "cotton blend", "poly blend", "spandex", "elastane", "lycra"],
    "linen":     ["linen"],
    "rayon":     ["rayon", "viscose"],
    "wool":      ["wool", "merino"],
    "denim":     ["denim", "chambray"],
}

# ── Pattern keywords ──────────────────────────────────────────
PATTERN_KEYWORDS = {
    "Solid":    ["solid", "plain", "basic"],
    "Striped":  ["striped", "stripes", "stripe"],
    "Graphic":  ["graphic", "print", "logo", "text", "slogan"],
    "Plaid":    ["plaid", "check", "checkered", "tartan"],
    "Floral":   ["floral", "flower", "botanical"],
    "Abstract": ["abstract", "geometric", "pattern"],
    "Tie-Dye":  ["tie-dye", "tiedye", "dye"],
}

# ── Fit keywords ──────────────────────────────────────────────
FIT_KEYWORDS = {
    "Regular":   ["regular", "classic", "standard"],
    "Slim":      ["slim", "fitted", "skinny", "tailored"],
    "Relaxed":   ["relaxed", "loose", "comfort"],
    "Oversized": ["oversized", "boxy", "boyfriend", "longline"],
}

# ── Neck type keywords ────────────────────────────────────────
NECK_KEYWORDS = {
    "Round Neck": ["round neck", "crew neck", "crewneck", "round collar"],
    "V-Neck":     ["v-neck", "v neck", "vneck"],
    "Polo":       ["polo", "collar"],
    "Henley":     ["henley"],
    "Scoop":      ["scoop neck", "scoop"],
    "Mock Neck":  ["mock neck", "turtleneck", "funnel neck"],
}

# ── Sleeve keywords ───────────────────────────────────────────
SLEEVE_KEYWORDS = {
    "Short Sleeve":    ["short sleeve", "short-sleeve", "half sleeve"],
    "Long Sleeve":     ["long sleeve", "long-sleeve", "full sleeve"],
    "Sleeveless":      ["sleeveless", "no sleeve", "tank"],
    "3/4 Sleeve":      ["3/4 sleeve", "three-quarter"],
}


def _match_keywords(text: str, keyword_map: dict) -> Optional[str]:
    text_lower = text.lower()
    for label, keywords in keyword_map.items():
        for kw in keywords:
            if kw in text_lower:
                return label
    return None


def get_color_family(color: Optional[str]) -> Optional[str]:
    if not color:
        return None
    color_lower = color.lower()
    for family, variants in COLOR_FAMILY_MAP.items():
        if any(v in color_lower for v in variants):
            return family
    return "other"


def get_material_family(material: Optional[str]) -> Optional[str]:
    if not material:
        return None
    return _match_keywords(material, MATERIAL_FAMILY_MAP) or "other"


def parse_pattern(text: str) -> Optional[str]:
    return _match_keywords(text, PATTERN_KEYWORDS)


def parse_fit(text: str) -> Optional[str]:
    return _match_keywords(text, FIT_KEYWORDS)


def parse_neck_type(text: str) -> Optional[str]:
    return _match_keywords(text, NECK_KEYWORDS)


def parse_sleeve_type(text: str) -> Optional[str]:
    return _match_keywords(text, SLEEVE_KEYWORDS)


def parse_price(price_str: str) -> Optional[float]:
    """Extract float from '$29.99', '29.99', '$29.99 - $39.99' (takes first)."""
    if not price_str:
        return None
    match = re.search(r"[\d,]+\.?\d*", price_str.replace(",", ""))
    return float(match.group()) if match else None


def parse_rating(rating_str: str) -> Optional[float]:
    """Extract rating float from '4.5 out of 5 stars', '4.5'."""
    if not rating_str:
        return None
    match = re.search(r"(\d+\.?\d*)", rating_str)
    return float(match.group()) if match else None


def parse_review_count(count_str: str) -> int:
    """Extract int from '1,234 ratings', '1234 reviews'."""
    if not count_str:
        return 0
    cleaned = count_str.replace(",", "").replace(".", "")
    match = re.search(r"\d+", cleaned)
    return int(match.group()) if match else 0
