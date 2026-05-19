"""
llm_drafter.py — Drafts evidence-backed recommendations via the configured LLM.

Uses chatbot/llm_config.py, so recommendations follow the same provider settings
as the conversational layer:
    LLM_PROVIDER=groq
    GROQ_API_KEY=...
    GROQ_MODEL=...
"""
from __future__ import annotations

import json
import os
import sys

from loguru import logger

sys.path.insert(0, ".")

_CHATBOT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "chatbot")
)
if _CHATBOT_DIR not in sys.path:
    sys.path.insert(0, _CHATBOT_DIR)

from llm_config import llm  # noqa: E402

_PATTERN_LABELS = {
    "emerging_star":       "Emerging Star",
    "declining_attribute": "Declining Attribute",
    "underserved_niche":   "Underserved Niche",
    "review_leader":       "Review Leader",
    "cross_platform_gap":  "Cross-Platform Gap",
    "rating_outlier":      "Rating Outlier",
}

_SYSTEM = """\
You are a senior retail merchandising strategist for a fashion brand.
You will receive a detected market pattern from scraped marketplace data.

Generate ONE recommendation that a senior merchandiser or category manager
would take seriously. It must be specific, evidence-backed, and tied to a
realistic brand decision such as listing variants, changing price-band emphasis,
prioritizing materials, or reducing exposure.

Format EXACTLY as:

Observation: <specific data observation>
Action: <concrete brand action>
Reasoning: <why this action follows from the evidence>
Evidence: <cite 2-3 exact metrics from the evidence block>
Impact: <expected business impact in 4-8 weeks>
Confidence: <High / Medium / Low>

Rules:
- No generic advice.
- Cite numbers directly from the evidence block.
- If lifecycle_stage or retailer_action exists, align the Action to it.
- Keep each section under 35 words.
- Do not invent metrics that are not in the evidence block.
- Confidence criteria — use exactly one:
  High: momentum_score > 0.20 AND review_count > 2000 AND lifecycle = emerging or accelerating
  Medium: momentum_score 0.08–0.20 OR review_count 500–2000 OR lifecycle = plateau
  Low: momentum_score < 0.08 OR conflicting signals OR lifecycle = dead/declining
"""


def draft_recommendation(pattern: dict) -> dict:
    label = _PATTERN_LABELS.get(pattern["pattern_type"], pattern["pattern_type"])
    user_msg = (
        f"Pattern type: {label}\n"
        f"Category: {pattern['category']}\n"
        f"Platform: {pattern['platform']}\n"
        f"Attribute: {pattern['attr_key']} = {pattern['attr_value']}\n\n"
        f"Evidence:\n{json.dumps(pattern['evidence'], indent=2)}\n\n"
        "Generate the recommendation."
    )

    raw = llm.generate_response(_SYSTEM, user_msg, temperature=0).strip()
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
    field_map = {
        "Observation": "observation",
        "Action": "action",
        "Reasoning": "reasoning",
        "Evidence": "evidence_text",
        "Impact": "impact",
        "Confidence": "confidence",
    }
    for line in text.splitlines():
        for label, key in field_map.items():
            prefix = f"{label}:"
            if line.startswith(prefix):
                out[key] = line[len(prefix):].strip()
    if out.get("confidence") not in {"High", "Medium", "Low"}:
        out["confidence"] = "Medium"
    return out


def draft_all(patterns: list[dict]) -> list[dict]:
    recs: list[dict] = []
    for pattern in patterns:
        try:
            rec = draft_recommendation(pattern)
            recs.append(rec)
            logger.info(
                "llm_drafter: drafted via {} for {} / {}",
                llm.provider,
                pattern["pattern_type"],
                pattern["attr_value"],
            )
        except Exception as exc:
            logger.error(f"llm_drafter: failed for {pattern}: {exc}")
    return recs
