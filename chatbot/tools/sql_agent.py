import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from db import get_connection
from llm_config import llm
from utils.history import format_history_for_prompt
from utils.redis_cache import redis_cache

load_dotenv()

_SQL_CACHE_TTL = int(os.getenv("SQL_CACHE_TTL", 300))  # 5 minutes

_SQL_SYSTEM_PROMPT = """
You are a PostgreSQL query generator for a normalized fashion retail database.

═══════════════════════════════════════════════════
ABSOLUTE RULES
═══════════════════════════════════════════════════
1. Output ONLY a single raw SQL SELECT statement — no markdown, no explanation.
2. Never use INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE.
3. Never invent table or column names not listed in the schema.
4. Always add LIMIT 50 unless the query is a pure aggregation (COUNT/SUM/AVG/GROUP BY).
5. Use ILIKE for all user-supplied text filters (case-insensitive matching).
6. Use table aliases consistently to keep queries readable.
7. Use conversation context to resolve references like "that brand", "same color".

═══════════════════════════════════════════════════
DATABASE SCHEMA
═══════════════════════════════════════════════════
products (p)
  product_id  INTEGER — primary key
  title       TEXT    — product name / title
  brand_id    INTEGER — FK → brands
  category_id INTEGER — FK → categories
  url         TEXT

brands (b)
  brand_id  INTEGER — primary key
  name      TEXT    — brand name (e.g. "Nike", "H&M", "Zara")

categories (c)
  category_id INTEGER — primary key
  name        TEXT    — category name (e.g. "T-Shirts", "Dresses", "Polo Shirts")
  gender      TEXT    — "Men", "Women", "Unisex"

product_variants (pv)
  variant_id     INTEGER — primary key
  product_id     INTEGER — FK → products
  color_id       INTEGER — FK → colors
  size_id        INTEGER — FK → sizes
  material_id    INTEGER — FK → materials
  neck_type_id   INTEGER — FK → neck_types
  sleeve_type_id INTEGER — FK → sleeve_types
  fit_id         INTEGER — FK → fits
  pattern_id     INTEGER — FK → patterns
  is_available   BOOLEAN
  price          NUMERIC
  currency       TEXT

Lookup tables (all follow: <table>_id, name):
  colors (col)      — color_id, name, color_family
  sizes (sz)        — size_id, label, sort_order, size_system
  materials (mat)   — material_id, name
  neck_types (nt)   — neck_type_id, name
  sleeve_types (st) — sleeve_type_id, name
  fits (f)          — fit_id, name
  patterns (pt)     — pattern_id, name

reviews (r)
  review_id    INTEGER — primary key
  product_id   INTEGER — FK → products
  rating_avg   NUMERIC — average star rating (1.0–5.0)
  review_count INTEGER — total number of reviews
  comment_json JSONB   — array of customer comment objects

═══════════════════════════════════════════════════
CRITICAL JOIN PATTERNS
═══════════════════════════════════════════════════
Always GROUP BY to collapse multiple variants into one product row.
Use LEFT JOIN for reviews and attributes that may be missing.

Standard product listing:
SELECT
    p.product_id, p.title,
    b.name AS brand, c.name AS category,
    r.rating_avg, r.review_count,
    MIN(pv.price) AS min_price,
    STRING_AGG(DISTINCT col.name, ', ' ORDER BY col.name) AS colors
FROM products p
JOIN brands b ON p.brand_id = b.brand_id
JOIN categories c ON p.category_id = c.category_id
JOIN product_variants pv ON p.product_id = pv.product_id
JOIN colors col ON pv.color_id = col.color_id
LEFT JOIN reviews r ON p.product_id = r.product_id
WHERE col.name ILIKE '%black%' AND c.name ILIKE '%shirt%'
GROUP BY p.product_id, p.title, b.name, c.name, r.rating_avg, r.review_count
ORDER BY r.rating_avg DESC NULLS LAST
LIMIT 10

Other filter examples:
  -- by size:     JOIN sizes sz ON pv.size_id = sz.size_id WHERE sz.label ILIKE '%xl%'
  -- by material: JOIN materials mat ON pv.material_id = mat.material_id WHERE mat.name ILIKE '%cotton%'
  -- available:   WHERE pv.is_available = TRUE
  -- by price:    WHERE pv.price <= 50
  -- by brand:    WHERE b.name ILIKE '%nike%'
""".strip()

_RESPONSE_SYSTEM_PROMPT = """
You are a fashion retail analytics assistant.

Generate a clear, concise, business-friendly response based solely on the SQL data provided.
Do not invent numbers or facts not present in the data.
If the data is empty, say clearly that no matching records were found.
Use the conversation context to make your response feel like a natural continuation.

Formatting rules:
- Start with 1-2 sentences of key insight in **bold** for the most important finding.
- When comparing channels/platforms, ALWAYS format as a markdown table with pipe syntax:
  | CHANNEL | MEDIAN PRICE | CONVERTING BAND | VELOCITY |
  |---------|-------------|-----------------|---------|
  | Amazon  | $27.50      | $20-32          | +34%    |
- For ranked lists of products/patterns (3+ items), use a markdown table with columns relevant to the question (e.g. RANK, PATTERN, VELOCITY, CONFIDENCE).
- After the table, add 1-2 sentences of business interpretation with key numbers in **bold**.
- Keep total response under 120 words.
""".strip()

_BLOCKED_STATEMENT_STARTERS = frozenset(
    word.upper()
    for word in [
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
        "TRUNCATE", "CREATE", "GRANT", "REVOKE",
    ]
)


def _validate_sql(query: str) -> bool:
    tokens = query.strip().split()
    if not tokens:
        return False
    if tokens[0].upper() != "SELECT":
        return False
    return not any(
        t.upper().rstrip(";") in _BLOCKED_STATEMENT_STARTERS
        for t in tokens[1:]
    )


def _generate_sql(question: str, chat_history: list) -> str:
    history_ctx = format_history_for_prompt(chat_history, max_messages=4)
    prompt = f"{history_ctx}Current question:\n{question}\n\nGenerate a PostgreSQL SELECT query."
    return llm.generate_response(
        system_prompt=_SQL_SYSTEM_PROMPT,
        user_prompt=prompt,
        temperature=0,
    ).strip()


def _execute_sql(query: str) -> list[dict]:
    # Cache SQL results for a short window — retail data changes slowly
    cache_key = "sql:" + hashlib.sha256(query.encode("utf-8")).hexdigest()[:32]
    cached = redis_cache.get_data(cache_key)
    if cached is not None:
        return cached

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            if cur.description is None:
                return []
            cols = [d[0] for d in cur.description]
            result = [dict(zip(cols, row)) for row in cur.fetchall()]

    redis_cache.set_data(cache_key, result, ttl=_SQL_CACHE_TTL)
    return result


_MAX_RESPONSE_ROWS = 15


def _build_response(question: str, data: list[dict], chat_history: list) -> str:
    history_ctx = format_history_for_prompt(chat_history, max_messages=2)
    display = data[:_MAX_RESPONSE_ROWS]
    prompt = (
        f"{history_ctx}"
        f"Current question:\n{question}\n\n"
        f"SQL Result ({len(data)} rows, showing {len(display)}):\n"
        f"{json.dumps(display, default=str)}"
    )
    return llm.generate_response(
        system_prompt=_RESPONSE_SYSTEM_PROMPT,
        user_prompt=prompt,
        temperature=0,
    )


def run_sql_agent(
    question: str,
    intent_response: dict,
    chat_history: list,
) -> dict:
    try:
        query = _generate_sql(question, chat_history)

        if not _validate_sql(query):
            return {
                "success": False,
                "confidence": 0.0,
                "source": "sql_agent",
                "response": "The generated SQL was unsafe and was not executed.",
            }

        data = _execute_sql(query)
        response = _build_response(question=question, data=data, chat_history=chat_history)

        return {
            "success": True,
            "confidence": float(intent_response.get("confidence", 0.8)),
            "source": "sql_agent",
            "query": query,
            "data": data,
            "response": response,
        }

    except Exception as exc:
        return {
            "success": False,
            "confidence": 0.0,
            "source": "sql_agent",
            "response": f"SQL agent failed: {exc}",
        }
