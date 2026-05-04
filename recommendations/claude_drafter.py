"""
claude_drafter.py — Sends a detected pattern to Claude and gets a structured recommendation.

Each call produces one recommendation with fields:
    Observation / Action / Evidence / Impact / Confidence
"""
from __future__ import annotations
import sys
import json
sys.path.insert(0, ".")

from loguru import logger
import anthropic

from config.settings import settings

_PATTERN_LABELS = {
    "emerging_star":       "Emerging Star",
    "declining_attribute": "Declining Attribute",
    "underserved_niche":   "Underserved Niche",
    "review_leader":       "Review Leader",
    "cross_platform_gap":  "Cross-Platform Gap",
    "rating_outlier":      "Rating Outlier",
}

_SYSTEM = """\
You are a senior retail merchandising strategist. You will receive a detected market pattern
with supporting evidence from scraped US apparel marketplace data.

Generate ONE specific, evidence-backed recommendation. Format EXACTLY as:

Observation: <one sentence, what the data shows>
Action: <concrete, specific action the brand should take>
Evidence: <cite 2-3 numbers directly from the evidence block>
Impact: <expected business outcome within 4-8 weeks>
Confidence: <High / Medium / Low>

Rules: no generic advice, cite numbers, each section ≤ 30 words.\
"""


def draft_recommendation(pattern: dict) -> dict:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    label = _PATTERN_LABELS.get(pattern["pattern_type"], pattern["pattern_type"])
    user_msg = (
        f"Pattern type: {label}\n"
        f"Category: {pattern['category']}\n"
        f"Platform: {pattern['platform']}\n"
        f"Attribute: {pattern['attr_key']} = {pattern['attr_value']}\n\n"
        f"Evidence:\n{json.dumps(pattern['evidence'], indent=2)}\n\n"
        "Generate the recommendation."
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        system=_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = response.content[0].text.strip()
    parsed = _parse(raw)

    return {
        **pattern,
        "recommendation_text": raw,
        "observation": parsed.get("observation", ""),
        "action":      parsed.get("action", ""),
        "impact":      parsed.get("impact", ""),
        "confidence":  parsed.get("confidence", "Medium"),
    }


def _parse(text: str) -> dict:
    out: dict = {}
    for line in text.splitlines():
        for field in ("Observation", "Action", "Evidence", "Impact", "Confidence"):
            if line.startswith(f"{field}:"):
                out[field.lower()] = line[len(field) + 1:].strip()
    return out


def draft_all(patterns: list[dict]) -> list[dict]:
    recs: list[dict] = []
    for p in patterns:
        try:
            rec = draft_recommendation(p)
            recs.append(rec)
            logger.info(f"claude_drafter: drafted for {p['pattern_type']} / {p['attr_value']}")
        except Exception as exc:
            logger.error(f"claude_drafter: failed for {p}: {exc}")
    return recs
