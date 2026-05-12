import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from db import get_connection
from llm_config import llm
from utils.history import format_history_for_prompt

load_dotenv()

_TREND_SYSTEM_PROMPT = """
You are a fashion trend intelligence assistant.

Interpret structured trend analytics data and surface actionable business insights.

Rules:
1. Only use numbers and facts present in the provided analytics data.
2. Never invent trends, ratings, or review counts.
3. If data is limited, state that confidence is low.
4. Structure: Trend Overview → Rising Attributes → Notable Observations → Business Recommendation.
5. Use the conversation context to make your answer feel like a natural continuation.
""".strip()

_TREND_QUERY = """
SELECT
    pt.name                              AS pattern,
    col.name                             AS color,
    mat.name                             AS material,
    COUNT(DISTINCT p.product_id)         AS product_count,
    ROUND(AVG(r.rating_avg)::numeric, 2) AS avg_rating,
    SUM(r.review_count)                  AS total_reviews
FROM products p
JOIN product_variants pv ON p.product_id  = pv.product_id
LEFT JOIN patterns  pt  ON pv.pattern_id  = pt.pattern_id
LEFT JOIN colors    col ON pv.color_id    = col.color_id
LEFT JOIN materials mat ON pv.material_id = mat.material_id
LEFT JOIN reviews   r   ON p.product_id  = r.product_id
GROUP BY pt.name, col.name, mat.name
ORDER BY total_reviews DESC NULLS LAST
LIMIT 20
"""


def _fetch_trend_data() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(_TREND_QUERY)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def _calculate_confidence(data: list[dict]) -> float:
    if not data:
        return 0.0
    total = sum(int(row.get("total_reviews") or 0) for row in data)
    if total > 5000:
        return 0.95
    if total > 1000:
        return 0.85
    if total > 100:
        return 0.70
    return 0.50


def _build_trend_summary(
    question: str,
    data: list[dict],
    chat_history: list,
) -> str:
    history_ctx = format_history_for_prompt(chat_history, max_messages=4)
    prompt = (
        f"{history_ctx}"
        f"Current question:\n{question}\n\n"
        f"Trend Analytics Data:\n"
        f"{json.dumps(data, default=str, indent=2)}"
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
        data = _fetch_trend_data()

        if not data:
            return {
                "success": False,
                "confidence": 0.0,
                "source": "trend_engine_agent",
                "response": "No trend data is available in the database.",
            }

        confidence = _calculate_confidence(data)
        response = _build_trend_summary(
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
