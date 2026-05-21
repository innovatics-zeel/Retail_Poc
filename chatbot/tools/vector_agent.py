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

_REVIEW_SYSTEM_PROMPT = """
You are a fashion retail analyst interpreting customer review data.

You have structured review data with: product title, platform, rating_avg, review_count,
and star distribution (stars_1_pct through stars_5_pct as percentages).

Rules:
1. Answer the specific question directly in the first sentence.
2. Use stars_1_pct + stars_2_pct as the complaint/dissatisfaction signal.
3. Use stars_4_pct + stars_5_pct as the satisfaction signal.
4. Reference specific products and numbers from the data.
5. Be concise — under 80 words unless more detail is needed.
6. Never invent opinions or review text — only use the star distribution data.
""".strip()

_CATEGORY_MAP = {
    re.compile(r"\b(men|mens|men's|t-shirt|tshirt)\b", re.I): "mens_tshirts",
    re.compile(r"\b(women|womens|women's|dress|gown)\b", re.I): "womens_dresses",
}

_PLATFORM_MAP = {
    re.compile(r"\bamazon\b", re.I): "amazon",
    re.compile(r"\bnordstrom\b", re.I): "nordstrom",
}


def _detect_category(question: str) -> str | None:
    for pattern, cat in _CATEGORY_MAP.items():
        if pattern.search(question):
            return cat
    return None


def _detect_platform(question: str) -> str | None:
    for pattern, plat in _PLATFORM_MAP.items():
        if pattern.search(question):
            return plat
    return None


def _fetch_review_data(question: str) -> list[dict]:
    category = _detect_category(question)
    platform = _detect_platform(question)

    filters = ["r.review_count > 0", "r.stars_1_pct IS NOT NULL"]
    params: list = []

    if category:
        filters.append("c.name = %s")
        params.append(category)
    if platform:
        filters.append("pl.name = %s")
        params.append(platform)

    where = " AND ".join(filters)

    # Sort by complaint rate (1+2 star %) to surface most-complained products
    query = f"""
        SELECT p.title, pl.name AS platform, c.name AS category,
               r.rating_avg, r.review_count,
               r.stars_1_pct, r.stars_2_pct, r.stars_3_pct,
               r.stars_4_pct, r.stars_5_pct
        FROM reviews r
        JOIN products p ON r.product_id = p.product_id
        JOIN platforms pl ON p.platform_id = pl.id
        JOIN categories c ON p.category_id = c.category_id
        WHERE {where}
        ORDER BY (COALESCE(r.stars_1_pct, 0) + COALESCE(r.stars_2_pct, 0)) DESC,
                 r.review_count DESC
        LIMIT 10
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def run_vector_agent(
    question: str,
    intent_response: dict,
    chat_history: list,
) -> dict:
    try:
        data = _fetch_review_data(question)

        if not data:
            return {
                "success": False,
                "confidence": 0.0,
                "source": "vector_agent",
                "response": "No review data found for that query. Try asking about men's t-shirts or women's dresses.",
            }

        history_ctx = format_history_for_prompt(chat_history, max_messages=2)
        prompt = (
            f"{history_ctx}"
            f"Question: {question}\n\n"
            f"Review data (star percentages show customer satisfaction distribution):\n"
            f"{json.dumps(data[:5], default=str)}"
        )

        response = llm.generate_response(
            system_prompt=_REVIEW_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0,
        )

        avg_rating = sum(float(r.get("rating_avg") or 0) for r in data) / len(data)
        confidence = min(0.9, 0.5 + (avg_rating - 3.0) * 0.1)

        return {
            "success": True,
            "confidence": round(confidence, 2),
            "source": "vector_agent",
            "data": data,
            "response": response,
        }

    except Exception as exc:
        return {
            "success": False,
            "confidence": 0.0,
            "source": "vector_agent",
            "response": f"Review analysis failed: {exc}",
        }
