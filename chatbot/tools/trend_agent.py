import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from db import get_connection
from llm_config import llm
from utils.history import format_history_for_prompt

load_dotenv()

_TREND_SYSTEM_PROMPT = """
You are a senior fashion retail analyst. Give sharp, executive-ready trend answers.

DATA FIELDS:
- momentum_score: composite trend signal between -1.0 (max decline) and +1.0 (max growth).
  CRITICAL: This is a DECIMAL, not a percentage. -0.874 means -0.874, NOT -87.4%.
- trend_direction: 'Rising', 'Stable', or 'Falling' — the primary signal.
- lifecycle_stage: 'emerging', 'plateau', 'declining'
- attr_key: the attribute type (pattern, material, color_family, fit, neck_type, sleeve_type)

OUTPUT FORMAT:
1. One sentence key finding (bold).
2. A tight markdown table — 2 to 5 rows based on what makes sense. Don't pad.
3. One sentence business action with key numbers bolded.

TABLE RULES:
- 2–5 rows. Use judgment — show only rows that directly answer the question.
- For "declining" questions: pick rows with LOWEST (most negative) momentum_score.
- For "rising/trending" questions: pick rows with HIGHEST momentum_score AND trend_direction='Rising'.
- For "cross-channel" questions: show the SAME attr_value on both Amazon and Nordstrom — 2 rows per attribute.
  Never show the same PATTERN+CHANNEL pair twice.
- Plain text only inside cells — no ** markers inside cells.
- Column headers: attr_value→PATTERN, platform→CHANNEL, trend_direction→TREND, lifecycle_stage→STAGE.
- VELOCITY column: copy the exact momentum_score decimal. e.g. momentum_score=-0.874 → VELOCITY=-0.874.
  NEVER multiply by 100. NEVER add a % sign. -0.874 is correct. -87.4% is WRONG.
- If only 1–2 rows exist for the question, show only those rows. Do not pad with unrelated rows.
- Never invent numbers.

EXAMPLE — declining fastest:
**Short Sleeve is in the steepest decline across both channels.**
| PATTERN | CHANNEL | VELOCITY | TREND |
|---------|---------|---------|-------|
| Short Sleeve | Amazon | -0.49 | Falling |
| Short Sleeve | Nordstrom | -0.61 | Falling |
Cut Short Sleeve from the next buy cycle — **-0.61** on Nordstrom confirms structural, not seasonal decline.

EXAMPLE — rising:
**Cartoon print is the only rising pattern right now, exclusively on Amazon.**
| PATTERN | CHANNEL | VELOCITY | STAGE |
|---------|---------|---------|-------|
| Cartoon | Amazon | +0.24 | emerging |
Invest in **Cartoon** prints on Amazon — the only pattern with positive momentum in the current data.

EXAMPLE — cross-channel comparison:
**Crew Neck leads on Amazon while Nordstrom has not picked it up yet.**
| PATTERN | CHANNEL | VELOCITY | TREND |
|---------|---------|---------|-------|
| Crew Neck | Amazon | +0.26 | Rising |
| Crew Neck | Nordstrom | -0.31 | Falling |
**+0.57 momentum gap** — push Crew Neck on Amazon while evaluating Nordstrom assortment.
""".strip()

# Balanced dataset: all Rising/Stable + top 15 Falling, filtered by attr_key when specified
_TREND_SCORES_QUERY = """
WITH aggregated AS (
    SELECT
        ts.attr_value                                                                AS pattern,
        ts.attr_key,
        ts.platform,
        ROUND(AVG(ts.momentum_score)::numeric, 3)                                    AS momentum_score,
        SUM(ts.review_count)                                                         AS review_count,
        ROUND(AVG(ts.avg_rating)::numeric, 2)                                        AS avg_rating,
        SUM(ts.product_count)                                                        AS product_count,
        (array_agg(ts.trend_direction  ORDER BY ts.review_count DESC NULLS LAST))[1] AS trend_direction,
        (array_agg(ts.lifecycle_stage  ORDER BY ts.review_count DESC NULLS LAST))[1] AS lifecycle_stage,
        (array_agg(ts.retailer_action  ORDER BY ts.review_count DESC NULLS LAST))[1] AS retailer_action
    FROM trend_scores ts
    WHERE 1=1 {attr_filter}
    GROUP BY ts.attr_value, ts.attr_key, ts.platform
),
rising_stable AS (
    SELECT * FROM aggregated
    WHERE trend_direction IN ('Rising', 'Stable')
    ORDER BY momentum_score DESC NULLS LAST
),
declining AS (
    SELECT * FROM aggregated
    WHERE trend_direction NOT IN ('Rising', 'Stable')
    ORDER BY momentum_score ASC NULLS LAST
    LIMIT 15
)
SELECT * FROM rising_stable
UNION ALL
SELECT * FROM declining
ORDER BY momentum_score DESC NULLS LAST
"""

# Maps question keywords → attr_key value in trend_scores
_ATTR_KEY_MAP = [
    (re.compile(r'\bpattern', re.I),                              'pattern'),
    (re.compile(r'\b(material|fabric|cotton|polyester|nylon|silk|wool|linen|elastane|spandex)\b', re.I), 'material'),
    (re.compile(r'\bcolor',   re.I),                              'color_family'),
    (re.compile(r'\bfit\b',   re.I),                              'fit'),
    (re.compile(r'\bneck\b',  re.I),                              'neck_type'),
    (re.compile(r'\bsleeve\b',re.I),                              'sleeve_type'),
]


def _detect_attr_key(question: str) -> str | None:
    for pattern, key in _ATTR_KEY_MAP:
        if pattern.search(question):
            return key
    return None


def _fetch_trend_data(attr_key: str | None = None) -> list[dict]:
    if attr_key:
        filter_clause = f"AND ts.attr_key = '{attr_key}'"
    else:
        filter_clause = ""
    query = _TREND_SCORES_QUERY.replace("{attr_filter}", filter_clause)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def _calculate_confidence(data: list[dict]) -> float:
    if not data:
        return 0.0
    total = sum(int(row.get("review_count") or 0) for row in data)
    if total > 5000:
        return 0.95
    if total > 1000:
        return 0.85
    if total > 100:
        return 0.70
    return 0.50


def _build_trend_answer(question: str, data: list[dict], chat_history: list) -> str:
    history_ctx = format_history_for_prompt(chat_history, max_messages=2)
    prompt = (
        f"{history_ctx}"
        f"User question:\n{question}\n\n"
        f"Trend data (momentum_score is a decimal -1.0 to +1.0, NOT a percentage):\n"
        f"{json.dumps(data, default=str)}"
    )
    return llm.generate_response(
        system_prompt=_TREND_SYSTEM_PROMPT,
        user_prompt=prompt,
        temperature=0,
    )


def run_trend_engine_agent(
    question: str,
    intent_response: dict,
    chat_history: list,
) -> dict:
    try:
        attr_key = _detect_attr_key(question)
        data = _fetch_trend_data(attr_key)

        if not data:
            return {
                "success": False,
                "confidence": 0.0,
                "source": "trend_engine_agent",
                "response": "No trend data is available yet — run predictions first.",
            }

        confidence = _calculate_confidence(data)
        response = _build_trend_answer(
            question=question,
            data=data,
            chat_history=chat_history,
        )

        return {
            "success": True,
            "confidence": confidence,
            "source": "trend_engine_agent",
            "data": data,
            "response": response,
        }

    except Exception as exc:
        return {
            "success": False,
            "confidence": 0.0,
            "source": "trend_engine_agent",
            "response": f"Trend agent failed: {exc}",
        }
