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

_SQL_CACHE_TTL = int(os.getenv("SQL_CACHE_TTL", 300))

# ─── VERIFIED schema from information_schema (columns confirmed in DB) ───────
_SQL_SYSTEM_PROMPT = """
You are a PostgreSQL query generator for a fashion retail database.

════════════════════════════════════════════════
ABSOLUTE RULES
════════════════════════════════════════════════
1. Output ONLY a raw SQL SELECT statement — no markdown, no explanation, no backticks.
2. Never use INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE.
3. ONLY use table and column names listed in the schema below — never invent any.
4. Add LIMIT 50 unless the query is a pure aggregation (COUNT/SUM/AVG/GROUP BY).
5. Use ILIKE for all user-supplied text filters.
6. Use consistent table aliases from the schema.
7. NEVER use self-joins or duplicate table aliases (pl1/pl2, p1/p2, pv1/pv2).
   For platform comparison always use a single JOIN + GROUP BY pl.name.
8. Every non-aggregated SELECT column MUST appear in the GROUP BY clause.
9. Only apply WHERE filters explicitly stated in the CURRENT question.
   Do NOT carry over product names, attributes, or categories from previous questions in the conversation.
10. NEVER join trend_scores for product listing queries. trend_scores is ONLY for trend/momentum questions.
    Product queries use: products, platforms, brands, categories, product_variants, reviews only.
11. For price comparison between platforms: use PERCENTILE_CONT per platform with GROUP BY pl.name.
    Return median_price per row (one row per platform). NEVER compute a subtracted "gap" column.

════════════════════════════════════════════════
EXACT DATABASE SCHEMA (verified)
════════════════════════════════════════════════

products  alias=p
  product_id    INTEGER  PK
  platform_id   SMALLINT FK→platforms.id   ← platform/channel is HERE, not on variants
  brand_id      INTEGER  FK→brands.brand_id
  category_id   INTEGER  FK→categories.category_id
  title         TEXT
  url           TEXT
  material      TEXT     (raw text, not FK)
  neck_type     VARCHAR
  sleeve_type   VARCHAR
  fit           VARCHAR
  pattern       VARCHAR
  scraped_at    TIMESTAMPTZ

platforms  alias=pl   ← THE channel/retailer table — NEVER use "channels"
  id            SMALLINT PK
  name          VARCHAR  e.g. 'amazon', 'nordstrom'
  display_name  VARCHAR  e.g. 'Amazon', 'Nordstrom'
  base_url      TEXT

brands  alias=b
  brand_id  INTEGER PK
  name      VARCHAR

categories  alias=c
  category_id  INTEGER PK
  name         VARCHAR  e.g. 'mens_tshirts', 'womens_dresses'
  gender       VARCHAR

product_variants  alias=pv   ← NO platform_id here — platform is on products
  variant_id      INTEGER  PK
  product_id      INTEGER  FK→products.product_id
  color_id        INTEGER  FK→colors.color_id
  size_id         INTEGER  FK→sizes.size_id
  material_id     INTEGER  FK→materials.material_id
  neck_type_id    INTEGER  FK→neck_types.neck_type_id
  sleeve_type_id  INTEGER  FK→sleeve_types.sleeve_type_id
  fit_id          INTEGER  FK→fits.fit_id
  pattern_id      INTEGER  FK→patterns.pattern_id
  is_available    BOOLEAN
  price           NUMERIC
  original_price  NUMERIC
  discount_pct    NUMERIC
  currency        VARCHAR
  low_stock       BOOLEAN
  scraped_at      TIMESTAMPTZ

reviews  alias=r
  review_id     INTEGER PK
  product_id    INTEGER FK→products.product_id
  rating_avg    NUMERIC  (1.0–5.0)
  review_count  INTEGER
  fit_feedback  VARCHAR
  stars_1_pct   SMALLINT
  stars_2_pct   SMALLINT
  stars_3_pct   SMALLINT
  stars_4_pct   SMALLINT
  stars_5_pct   SMALLINT
  pros          JSON
  cons          JSON
  comment_json  JSONB

Lookup tables — each has (<name>_id INTEGER PK, name VARCHAR):
  colors        alias=col  — color_id, name, color_family
  sizes         alias=sz   — size_id, label, sort_order, size_system
  materials     alias=mat  — material_id, name
  neck_types    alias=nt   — neck_type_id, name
  sleeve_types  alias=slv  — sleeve_type_id, name
  fits          alias=f    — fit_id, name
  patterns      alias=pt   — pattern_id, name

trend_scores  alias=ts  — pre-computed per-attribute trend signals
  score_id           INTEGER  PK
  category           VARCHAR  e.g. 'mens_tshirts'
  platform           VARCHAR  e.g. 'amazon'   ← plain text, no FK
  attr_key           VARCHAR  e.g. 'material','fit','pattern','color_family'
  attr_value         VARCHAR  e.g. 'Polyester','Slim Fit','Graphic'
  trend_direction    VARCHAR  'rising','declining','stable'
  lifecycle_stage    VARCHAR  'emerging','plateau','declining'
  momentum_score     NUMERIC  (higher = stronger trend)
  review_count       BIGINT
  review_growth_pct  NUMERIC
  avg_rating         NUMERIC
  rating_delta       NUMERIC
  product_count      INTEGER
  new_product_share  NUMERIC
  latest_week_share  NUMERIC
  previous_week_share NUMERIC
  weeks_observed     INTEGER
  retailer_action    TEXT
  explanation        TEXT
  computed_at        TIMESTAMPTZ

TABLES THAT DO NOT EXIST — never reference them:
  channels, channel, retailers, retailer, stores, shops, inventory

════════════════════════════════════════════════
QUERY EXAMPLES
════════════════════════════════════════════════

-- Standard product listing with platform
SELECT p.product_id, p.title, b.name AS brand, c.name AS category,
       pl.name AS platform, r.rating_avg, r.review_count,
       MIN(pv.price) AS min_price
FROM products p
JOIN platforms pl ON p.platform_id = pl.id
JOIN brands b ON p.brand_id = b.brand_id
JOIN categories c ON p.category_id = c.category_id
JOIN product_variants pv ON p.product_id = pv.product_id
LEFT JOIN reviews r ON p.product_id = r.product_id
GROUP BY p.product_id, p.title, b.name, c.name, pl.name, r.rating_avg, r.review_count
ORDER BY r.rating_avg DESC NULLS LAST
LIMIT 15;

-- Price gap / median price comparison between platforms
-- One row per platform. NEVER subtract prices or compute a gap column — return median_price per channel.
-- The analyst will compute the gap from the two rows.
SELECT pl.name AS platform,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pv.price) AS median_price,
       COUNT(DISTINCT p.product_id) AS product_count
FROM products p
JOIN platforms pl ON p.platform_id = pl.id
JOIN categories c ON p.category_id = c.category_id
JOIN product_variants pv ON p.product_id = pv.product_id
WHERE pv.price IS NOT NULL
  AND c.name ILIKE '%mens_tshirts%'
GROUP BY pl.name
ORDER BY pl.name;

-- Mark-down candidates: available, high price, fewest reviews
SELECT p.title, pl.name AS platform,
       MIN(pv.price) AS min_price,
       COALESCE(r.review_count, 0) AS review_count,
       ROUND(r.rating_avg::numeric, 2) AS rating
FROM products p
JOIN platforms pl ON p.platform_id = pl.id
JOIN product_variants pv ON p.product_id = pv.product_id
LEFT JOIN reviews r ON p.product_id = r.product_id
WHERE pv.is_available = TRUE AND pv.price IS NOT NULL
GROUP BY p.product_id, p.title, pl.name, r.review_count, r.rating_avg
ORDER BY review_count ASC NULLS FIRST, min_price DESC
LIMIT 15;

-- Nordstrom-only attributes using trend_scores
SELECT attr_key, attr_value, trend_direction, lifecycle_stage,
       ROUND(momentum_score::numeric,3) AS momentum, product_count
FROM trend_scores
WHERE platform ILIKE '%nordstrom%'
ORDER BY momentum_score DESC NULLS LAST
LIMIT 15;
-- NOTE: trend_direction values are 'Rising', 'Falling', 'Stable' (capitalized)

-- Whitespace: categories/attributes with low product count but rising trend
SELECT attr_key, attr_value, category, platform, product_count,
       trend_direction, ROUND(momentum_score::numeric,3) AS momentum
FROM trend_scores
WHERE product_count <= 3 AND trend_direction = 'Rising'
ORDER BY momentum_score DESC NULLS LAST
LIMIT 15;

-- Fastest declining
SELECT attr_key, attr_value, category, platform,
       ROUND(momentum_score::numeric,3) AS momentum, trend_direction
FROM trend_scores
WHERE trend_direction = 'Falling'
ORDER BY momentum_score ASC NULLS LAST
LIMIT 15;
""".strip()

_RESPONSE_SYSTEM_PROMPT = """
You are a senior fashion retail analyst. Give a sharp, executive-ready answer — like a pro analyst on a call, not a data dump.

OUTPUT FORMAT:
1. One sentence key finding (bold).
2. A tight markdown table — 2 to 5 rows. Use judgment: 2 rows if comparing 2 platforms; up to 5 for product lists.
3. One sentence business recommendation with the most important number bolded.

TABLE RULES:
- 2–5 rows based on what makes sense. Never exceed 5. Don't pad with irrelevant rows.
- Use business-friendly headers: platform→CHANNEL, min_price/median_price→PRICE, title→PRODUCT, rating_avg→RATING.
- Plain text only inside table cells — no ** bold ** markers inside cells.
- Only include columns that vary meaningfully across rows. Drop constant columns and mention them in the recommendation instead.
- For mark-down queries: always include PRODUCT column. Include PRICE and REVIEWS columns.
- For platform price comparison: 2 rows (one per platform), columns CHANNEL + MEDIAN PRICE. Compute the gap in the recommendation sentence only — no "gap" column in the table.
- For product listings: PRODUCT + PRICE + RATING. Nothing else unless specifically relevant.
- NEVER include review_growth_pct, trend columns, or momentum in product listing tables — those are trend data, not product data.
- Never invent numbers. If rows exist, describe them — never say "no matching records."

EXAMPLE — mark-down:
**Start with these 5 Nordstrom products: high price, zero reviews, no sell-through.**
| PRODUCT | PRICE | REVIEWS |
|---------|-------|---------|
| Ambuto Print Sleeveless Dress | $2,178 | 0 |
| Lucy Floral Tie Waist Minidress | $583 | 0 |
| Dimosa Sleeveless Midi Wrap Dress | $485 | 0 |
| Tipped Cotton Stretch Jersey T-Shirt | $392 | 0 |
| Hibiscus Square Neck Trumpet Gown | $351 | 0 |
All 5 have **zero reviews** — mark down by 20-30% to trigger first conversions.

EXAMPLE — platform price comparison:
**Amazon prices men's t-shirts 62% lower than Nordstrom.**
| CHANNEL | MEDIAN PRICE |
|---------|-------------|
| Amazon | $27.50 |
| Nordstrom | $44.99 |
**$17.49 gap** — consider repositioning Nordstrom SKUs as premium or adjusting price point to close the gap.

EXAMPLE — top-rated products:
**Nordstrom's highest-rated women's dresses average 4.5 stars.**
| PRODUCT | PRICE | RATING |
|---------|-------|--------|
| Ambuto Print Sleeveless Dress | $248 | 4.8 |
| Lucy Floral Tie Waist Minidress | $583 | 4.6 |
| Dimosa Sleeveless Midi Wrap Dress | $485 | 4.5 |
Prioritize restocking the **top 3** — high rating signals strong sell-through potential.
""".strip()

_BLOCKED_STATEMENT_STARTERS = frozenset(
    word.upper()
    for word in ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
                 "TRUNCATE", "CREATE", "GRANT", "REVOKE"]
)


def _validate_sql(query: str) -> bool:
    tokens = query.strip().split()
    if not tokens or tokens[0].upper() != "SELECT":
        return False
    return not any(t.upper().rstrip(";") in _BLOCKED_STATEMENT_STARTERS for t in tokens[1:])


def _generate_sql(question: str, chat_history: list, error_feedback: str = None) -> str:
    history_ctx = format_history_for_prompt(chat_history, max_messages=4)
    prompt = f"{history_ctx}Question:\n{question}\n\nGenerate a PostgreSQL SELECT query."
    if error_feedback:
        prompt += f"\n\nPrevious attempt failed with: {error_feedback}\nFix the query — only use columns and tables listed in the schema."
    return llm.generate_response(
        system_prompt=_SQL_SYSTEM_PROMPT,
        user_prompt=prompt,
        temperature=0,
    ).strip()


def _execute_sql(query: str) -> list[dict]:
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


def _build_response(question: str, data: list[dict], chat_history: list) -> str:
    history_ctx = format_history_for_prompt(chat_history, max_messages=2)
    display = data[:15]
    prompt = (
        f"{history_ctx}"
        f"Question:\n{question}\n\n"
        f"SQL Result ({len(data)} rows, showing {len(display)}):\n"
        f"{json.dumps(display, default=str)}"
    )
    return llm.generate_response(
        system_prompt=_RESPONSE_SYSTEM_PROMPT,
        user_prompt=prompt,
        temperature=0,
    )


def run_sql_agent(question: str, intent_response: dict, chat_history: list) -> dict:
    try:
        query = _generate_sql(question, chat_history)

        if not _validate_sql(query):
            return {
                "success": False,
                "confidence": 0.0,
                "source": "sql_agent",
                "response": "The generated SQL was unsafe and was not executed.",
            }

        # Auto-retry once on SQL error with error feedback
        try:
            data = _execute_sql(query)
        except Exception as sql_err:
            query = _generate_sql(question, chat_history, error_feedback=str(sql_err))
            if not _validate_sql(query):
                raise
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
