import hashlib
import json
import os
from typing import Iterator

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from db import get_connection
from utils.redis_cache import redis_cache

load_dotenv()

_EMBEDDING_DIM = 384
_TABLE = os.getenv("VECTOR_TABLE", "review_embeddings")
_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
_MAX_COMMENTS = int(os.getenv("EMBEDDING_MAX_COMMENTS", 10))
_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", 32))
_MIN_COMMENT_LENGTH = 20

# BGE asymmetric retrieval: queries need this prefix; documents do not.
_BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(_EMBEDDING_MODEL)
    return _model


def _to_pgvector(v: list[float]) -> str:
    return "[" + ",".join(str(x) for x in v) + "]"


_EMBEDDING_CACHE_TTL = int(os.getenv("EMBEDDING_CACHE_TTL", 3600))


def embed_query(text: str) -> list[float]:
    """
    Embed a query string using the BGE asymmetric prefix.
    Results are cached in Redis (TTL=1 h) — same text always produces the same
    vector, so caching is safe and eliminates repeated GPU/CPU inference calls.
    """
    full_text = _BGE_QUERY_PREFIX + text
    cache_key = "emb:" + hashlib.sha256(full_text.encode("utf-8")).hexdigest()[:32]

    cached = redis_cache.get_data(cache_key)
    if cached is not None:
        return cached

    model = _get_model()
    vec = model.encode(full_text, normalize_embeddings=True)
    result = vec.tolist()

    redis_cache.set_data(cache_key, result, ttl=_EMBEDDING_CACHE_TTL)
    return result


# ── Table setup ───────────────────────────────────────────────────────────────

_DDL_STATEMENTS = [
    "CREATE EXTENSION IF NOT EXISTS vector",
    f"""
    CREATE TABLE IF NOT EXISTS {_TABLE} (
        id          SERIAL PRIMARY KEY,
        product_id  INTEGER      NOT NULL,
        chunk_index INTEGER      NOT NULL,
        chunk_type  VARCHAR(50)  NOT NULL,
        review_text TEXT         NOT NULL,
        embedding   vector({_EMBEDDING_DIM}) NOT NULL,
        created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
        UNIQUE (product_id, chunk_index)
    )
    """,
    f"""
    CREATE INDEX IF NOT EXISTS {_TABLE}_embedding_idx
        ON {_TABLE} USING hnsw (embedding vector_cosine_ops)
    """,
]


def setup_table() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            for stmt in _DDL_STATEMENTS:
                cur.execute(stmt)


def count_embeddings() -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {_TABLE}")
            return cur.fetchone()[0]


# ── Data fetch ────────────────────────────────────────────────────────────────

_FETCH_QUERY = """
WITH product_attrs AS (
    SELECT
        pv.product_id,
        ARRAY_AGG(DISTINCT col.name)  FILTER (WHERE col.name IS NOT NULL) AS colors,
        ARRAY_AGG(DISTINCT m.name)    FILTER (WHERE m.name   IS NOT NULL) AS materials,
        ARRAY_AGG(DISTINCT f.name)    FILTER (WHERE f.name   IS NOT NULL) AS fits,
        ARRAY_AGG(DISTINCT pt.name)   FILTER (WHERE pt.name  IS NOT NULL) AS patterns,
        ARRAY_AGG(DISTINCT nt.name)   FILTER (WHERE nt.name  IS NOT NULL) AS neck_types,
        ARRAY_AGG(DISTINCT st.name)   FILTER (WHERE st.name  IS NOT NULL) AS sleeve_types,
        MIN(pv.price)                                                      AS min_price,
        MAX(pv.price)                                                      AS max_price
    FROM product_variants pv
    LEFT JOIN colors      col ON pv.color_id       = col.color_id
    LEFT JOIN materials   m   ON pv.material_id    = m.material_id
    LEFT JOIN fits        f   ON pv.fit_id         = f.fit_id
    LEFT JOIN patterns    pt  ON pv.pattern_id     = pt.pattern_id
    LEFT JOIN neck_types  nt  ON pv.neck_type_id   = nt.neck_type_id
    LEFT JOIN sleeve_types st ON pv.sleeve_type_id = st.sleeve_type_id
    GROUP BY pv.product_id
)
SELECT
    p.product_id,
    p.title,
    b.name          AS brand,
    c.name          AS category,
    c.gender,
    pa.colors,
    pa.materials,
    pa.fits,
    pa.patterns,
    pa.neck_types,
    pa.sleeve_types,
    pa.min_price,
    pa.max_price,
    r.rating_avg,
    r.review_count,
    r.comment_json
FROM products p
LEFT JOIN brands        b  ON p.brand_id    = b.brand_id
LEFT JOIN categories    c  ON p.category_id = c.category_id
LEFT JOIN product_attrs pa ON p.product_id  = pa.product_id
LEFT JOIN reviews       r  ON p.product_id  = r.product_id
"""


def _fetch_products() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(_FETCH_QUERY)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


# ── Text chunking ─────────────────────────────────────────────────────────────

def _join_list(items: list | None) -> str:
    if not items:
        return "N/A"
    return ", ".join(str(i) for i in items if i)


def _format_price(val) -> str:
    if val is None:
        return "N/A"
    return f"${float(val):.2f}"


def _build_metadata_chunk(product: dict) -> str:
    lines = [
        f"Product: {product.get('title') or 'Unknown'}",
        f"Brand: {product.get('brand') or 'N/A'}",
        f"Category: {product.get('category') or 'N/A'} ({product.get('gender') or 'N/A'})",
        f"Colors: {_join_list(product.get('colors'))}",
        f"Materials: {_join_list(product.get('materials'))}",
        f"Fit: {_join_list(product.get('fits'))}",
        f"Patterns: {_join_list(product.get('patterns'))}",
        f"Neck Types: {_join_list(product.get('neck_types'))}",
        f"Sleeve Types: {_join_list(product.get('sleeve_types'))}",
        f"Price Range: {_format_price(product.get('min_price'))} – {_format_price(product.get('max_price'))}",
    ]
    if product.get("rating_avg") is not None:
        lines.append(f"Average Rating: {float(product['rating_avg']):.1f} / 5.0")
    if product.get("review_count") is not None:
        lines.append(f"Total Reviews: {product['review_count']}")
    return "\n".join(lines)


def _build_review_chunk(product: dict, comment: str) -> str:
    return (
        f"Product: {product.get('title') or 'Unknown'} "
        f"({product.get('brand') or 'N/A'}, {product.get('category') or 'N/A'})\n"
        f"Customer Review: {comment}"
    )


def _extract_comments(comment_json) -> list[str]:
    if not comment_json:
        return []
    if isinstance(comment_json, str):
        try:
            comment_json = json.loads(comment_json)
        except (json.JSONDecodeError, ValueError):
            return []
    if not isinstance(comment_json, list):
        return []

    comments = []
    for item in comment_json:
        text = None
        if isinstance(item, dict):
            text = item.get("comment") or item.get("text") or item.get("body")
        elif isinstance(item, str):
            text = item
        if text and isinstance(text, str):
            cleaned = text.strip()
            if len(cleaned) >= _MIN_COMMENT_LENGTH:
                comments.append(cleaned)
    return comments


def _iter_chunks(product: dict) -> Iterator[tuple[int, str, str]]:
    yield 0, "metadata", _build_metadata_chunk(product)

    comments = _extract_comments(product.get("comment_json"))[:_MAX_COMMENTS]
    for idx, comment in enumerate(comments, start=1):
        yield idx, "review", _build_review_chunk(product, comment)


# ── Upsert ────────────────────────────────────────────────────────────────────

_UPSERT_SQL = f"""
INSERT INTO {_TABLE} (product_id, chunk_index, chunk_type, review_text, embedding)
VALUES (%s, %s, %s, %s, %s::vector)
ON CONFLICT (product_id, chunk_index)
DO UPDATE SET
    chunk_type  = EXCLUDED.chunk_type,
    review_text = EXCLUDED.review_text,
    embedding   = EXCLUDED.embedding,
    created_at  = NOW()
"""


def _upsert_chunks(rows: list[tuple]) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(_UPSERT_SQL, rows)


# ── Pipeline entry point ──────────────────────────────────────────────────────

def run_pipeline(force: bool = False) -> dict:
    setup_table()

    if not force:
        existing = count_embeddings()
        if existing > 0:
            return {
                "status": "skipped",
                "message": (
                    f"Table already contains {existing} chunks. "
                    "Pass force=True to re-embed."
                ),
                "count": existing,
            }

    model = _get_model()
    products = _fetch_products()

    if not products:
        return {
            "status": "error",
            "message": "No products found in the database.",
            "count": 0,
        }

    total_chunks = 0
    failed_products = 0

    for product in products:
        try:
            chunks = list(_iter_chunks(product))
            texts = [text for _, _, text in chunks]

            embeddings = model.encode(
                texts,
                batch_size=_BATCH_SIZE,
                normalize_embeddings=True,
                show_progress_bar=False,
            )

            rows = [
                (
                    product["product_id"],
                    chunk_idx,
                    chunk_type,
                    text,
                    _to_pgvector(emb.tolist()),
                )
                for (chunk_idx, chunk_type, text), emb in zip(chunks, embeddings)
            ]

            _upsert_chunks(rows)
            total_chunks += len(rows)

        except Exception as exc:
            failed_products += 1
            print(f"[embedding_manager] product {product.get('product_id')} failed: {exc}")

    return {
        "status": "success",
        "message": (
            f"Embedded {len(products) - failed_products} products "
            f"into {total_chunks} chunks. "
            f"({failed_products} products failed)"
        ),
        "count": total_chunks,
        "failed": failed_products,
    }


if __name__ == "__main__":
    result = run_pipeline(force=False)
    print(result["message"])
