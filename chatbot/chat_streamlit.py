import os
import sys
import uuid
import random

# ── Path bootstrap ────────────────────────────────────────────────────────────
_CHATBOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chatbot")
if _CHATBOT_DIR not in sys.path:
    sys.path.insert(0, _CHATBOT_DIR)

import pandas as pd
import streamlit as st

from db import get_connection
from embedding_manager import count_embeddings, run_pipeline, setup_table
from orchestrator import orchestrator
from utils.redis_cache import redis_cache

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Retail Intelligence Chat",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.70rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-right: 6px;
}
.badge-sql      { background:#dbeafe; color:#1d4ed8; }
.badge-vector   { background:#dcfce7; color:#15803d; }
.badge-trend    { background:#fef9c3; color:#a16207; }
.badge-hybrid   { background:#ede9fe; color:#7c3aed; }
.badge-fallback { background:#f3f4f6; color:#6b7280; }
.conf           { font-size:0.70rem; color:#9ca3af; }
.resolved-q     {
    font-size: 0.75rem;
    color: #6366f1;
    padding: 4px 10px;
    background: #eef2ff;
    border-left: 3px solid #6366f1;
    border-radius: 4px;
    margin-bottom: 6px;
}
.stButton > button {
    text-align: left !important;
    white-space: normal !important;
    height: auto !important;
    padding: 6px 10px !important;
    font-size: 0.78rem !important;
}
</style>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
def _new_session_id() -> str:
    return str(uuid.uuid4())

if "session_id" not in st.session_state:
    st.session_state.session_id = _new_session_id()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

# ── One-time table bootstrap ──────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _bootstrap() -> bool:
    try:
        setup_table()
        return True
    except Exception:
        return False

_bootstrap()

# ── Status helpers ────────────────────────────────────────────────────────────

def _db_ok() -> bool:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except Exception:
        return False


def _chunk_count() -> int | None:
    try:
        return count_embeddings()
    except Exception:
        return None

# ── Dynamic suggestions (DB-driven) ──────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def _dynamic_suggestions() -> list[str]:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT
                        col.name  AS color,
                        c.name    AS category,
                        b.name    AS brand,
                        c.gender
                    FROM product_variants pv
                    JOIN colors     col ON pv.color_id     = col.color_id
                    JOIN products   p   ON pv.product_id   = p.product_id
                    JOIN categories c   ON p.category_id   = c.category_id
                    JOIN brands     b   ON p.brand_id      = b.brand_id
                    JOIN reviews    r   ON p.product_id    = r.product_id
                    WHERE r.rating_avg >= 4.0
                      AND col.name IS NOT NULL
                    ORDER BY RANDOM()
                    LIMIT 8
                """)
                rows = cur.fetchall()

        candidates: list[str] = []
        for color, category, brand, gender in rows:
            c, cat = color.lower(), category.lower()
            g = (gender or "").lower()
            candidates.append(f"Suggest me a {c} {cat} with the highest ratings")
            candidates.append(f"What do customers say about {brand} products?")
            if g in ("men", "women"):
                candidates.append(f"Which {c} {g}'s {cat} are customers loving?")
            candidates.append(f"Best {cat} under $50 with good reviews?")

        candidates.extend([
            "What patterns are trending right now?",
            "Which products have the most reviews?",
            "Show me the top 10 highest rated products",
            "What colors are most popular this season?",
            "Which brands have the most consistent quality?",
            "Are there any highly rated products available in XL?",
            "What do customers say about fabric quality?",
        ])

        seen: set[str] = set()
        unique = [s for s in candidates if not (s in seen or seen.add(s))]
        random.shuffle(unique)
        return unique[:8]

    except Exception:
        return [
            "Suggest me a black t-shirt with the highest ratings",
            "What patterns are trending right now?",
            "Which products have the best customer reviews?",
            "Show me the top 10 most reviewed products",
            "What colors are most popular in women's dresses?",
            "Best value products under $50?",
            "What do customers say about fabric quality?",
            "Which brands have the most consistent quality?",
        ]

# ── Badge / meta rendering ────────────────────────────────────────────────────

_BADGE = {
    "sql_agent":          ("SQL",      "badge-sql"),
    "vector_agent":       ("Vector",   "badge-vector"),
    "trend_engine_agent": ("Trend",    "badge-trend"),
    "hybrid_agent":       ("Hybrid",   "badge-hybrid"),
    "fallback_agent":     ("Fallback", "badge-fallback"),
    "fallback":           ("Fallback", "badge-fallback"),
}


def _render_meta(intent: dict, source: str, resolved_question: str | None) -> None:
    agent = intent.get("agent") or source or ""
    confidence = float(intent.get("confidence") or 0)
    reason = intent.get("reason") or ""

    label, cls = _BADGE.get(agent, ("Unknown", "badge-fallback"))
    filled = round(confidence * 5)
    bar = "●" * filled + "○" * (5 - filled)

    st.markdown(
        f'<span class="badge {cls}">{label}</span>'
        f'<span class="conf">{bar} {confidence:.0%}'
        f"{' — ' + reason if reason else ''}</span>",
        unsafe_allow_html=True,
    )

    if resolved_question:
        st.markdown(
            f'<div class="resolved-q">🔍 Understood as: <em>{resolved_question}</em></div>',
            unsafe_allow_html=True,
        )

# ── Source panels ─────────────────────────────────────────────────────────────

def _render_sql_block(query: str, data: list[dict], label: str) -> None:
    with st.expander(label, expanded=False):
        if query:
            st.code(query, language="sql")
        if data:
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        elif query:
            st.caption("Query returned no rows.")


def _render_vector_block(chunks: list[dict], label: str) -> None:
    with st.expander(label, expanded=False):
        for chunk in chunks:
            sim = chunk.get("similarity", 0)
            ctype = chunk.get("chunk_type", "")
            pid = chunk.get("product_id", "")
            st.markdown(
                f"**Similarity:** {sim:.2%} &nbsp;|&nbsp; "
                f"**Type:** `{ctype}` &nbsp;|&nbsp; "
                f"**Product ID:** {pid}"
            )
            st.markdown(chunk.get("review_text", ""))
            st.divider()


def _render_sources(tool_response: dict) -> None:
    if not tool_response:
        return
    source = tool_response.get("source", "")

    if source == "sql_agent":
        data = tool_response.get("data") or []
        _render_sql_block(tool_response.get("query", ""), data, f"SQL Results · {len(data)} rows")

    elif source == "vector_agent":
        chunks = tool_response.get("data") or []
        if chunks:
            _render_vector_block(chunks, f"Review Sources · {len(chunks)} chunks")

    elif source == "hybrid_agent":
        sql_data = tool_response.get("sql_data") or []
        sql_query = tool_response.get("sql_query", "")
        vector_data = tool_response.get("vector_data") or []
        if sql_data or sql_query:
            _render_sql_block(sql_query, sql_data, f"Matching Products · {len(sql_data)} found")
        if vector_data:
            _render_vector_block(vector_data, f"Customer Reviews · {len(vector_data)} chunks")

    elif source == "trend_engine_agent":
        data = tool_response.get("data") or []
        if data:
            with st.expander("Trend Analytics Data", expanded=False):
                st.dataframe(pd.DataFrame(data), use_container_width=True)


def _render_debug(debug: dict) -> None:
    intent = debug.get("intent") or {}
    tool_response = debug.get("tool_response") or {}
    resolved_question = debug.get("resolved_question")
    source = tool_response.get("source", "")

    _render_meta(intent=intent, source=source, resolved_question=resolved_question)
    _render_sources(tool_response)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🛍️ Retail Intelligence")
    st.divider()

    # Status row
    col_db, col_redis, col_em = st.columns(3)
    with col_db:
        if _db_ok():
            st.success("DB ✓")
        else:
            st.error("DB ✗")
    with col_redis:
        if redis_cache.is_redis_available:
            st.success("Redis ✓")
        else:
            st.warning("Cache ⚠")
    with col_em:
        chunks = _chunk_count()
        if chunks:
            st.success(f"{chunks} emb")
        elif chunks == 0:
            st.warning("0 emb")
        else:
            st.error("—")

    st.divider()

    # Embedding pipeline
    st.subheader("Embeddings")
    force = st.checkbox("Force re-embed", value=False)
    if st.button("▶ Run Embedding Pipeline", use_container_width=True):
        with st.spinner("Embedding reviews into pgvector…"):
            result = run_pipeline(force=force)
        if result["status"] == "success":
            st.success(result["message"])
            st.cache_data.clear()
            st.rerun()
        elif result["status"] == "skipped":
            st.info(result["message"])
        else:
            st.error(result.get("message", "Unknown error"))

    st.divider()

    # Session management
    st.subheader("Session")

    # Show history length
    session_id = st.session_state.session_id
    history_len = len(st.session_state.messages)
    st.caption(f"{history_len // 2} exchange(s) in this session")

    if st.button("🗑 Clear Chat & New Session", use_container_width=True):
        # Delete ALL Redis data for this session (privacy)
        orchestrator.clear_session(session_id)
        # Reset Streamlit state — new UUID = fresh isolated session
        st.session_state.messages = []
        st.session_state.pending_question = None
        st.session_state.session_id = _new_session_id()
        st.rerun()

    with st.expander("ℹ️ Privacy", expanded=False):
        st.caption(
            "Your conversation is stored in Redis and expires automatically after 1 hour. "
            "Clicking 'Clear Chat' immediately deletes all session data from Redis. "
            "Sessions are identified by a random UUID — no personal data is stored."
        )
        st.caption(f"Session ID: `{st.session_state.session_id[:16]}…`")

    st.divider()

    # Dynamic suggested questions
    st.subheader("Try asking…")
    suggestions = _dynamic_suggestions()
    for q in suggestions:
        if st.button(q, use_container_width=True, key=f"sug_{hash(q)}"):
            st.session_state.pending_question = q

# ── Main chat area ─────────────────────────────────────────────────────────────
st.title("Retail Analytics Assistant")
st.caption(
    "Ask about products, reviews, pricing, trends, or availability. "
    "Context from your conversation is automatically used to answer follow-up questions."
)

if chunks == 0:
    st.warning(
        "No embeddings found. Click **▶ Run Embedding Pipeline** in the sidebar "
        "before asking review or recommendation questions.",
        icon="⚠️",
    )

# Replay chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("debug"):
            _render_debug(msg["debug"])

# ── Input: ALWAYS render chat_input so it stays visible ───────────────────────
chat_input = st.chat_input("Ask something about your retail data…")

pending = st.session_state.pending_question
if pending:
    st.session_state.pending_question = None  # consume immediately

user_input = chat_input or pending

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            result = orchestrator.process_question(
                session_id=st.session_state.session_id,
                question=user_input,
            )

        response = result.get("response") or "Unable to process the request."
        st.markdown(response)

        debug = {
            "intent": result.get("intent"),
            "tool_response": result.get("tool_response"),
            "resolved_question": result.get("resolved_question"),
        }
        if result.get("intent") or result.get("tool_response"):
            _render_debug(debug)

    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
        "debug": debug,
    })
