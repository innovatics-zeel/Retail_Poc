import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from db import get_connection
from embedding_manager import embed_query, _TABLE
from llm_config import llm
from utils.history import format_history_for_prompt

load_dotenv()

_TOP_K = int(os.getenv("TOP_K_RESULTS", 5))
_MIN_SIMILARITY = float(os.getenv("VECTOR_MIN_SIMILARITY", 0.30))

_VECTOR_SYSTEM_PROMPT = """
You are a fashion review intelligence assistant.

Analyze the retrieved customer review chunks and provide business insights.

Rules:
1. Only use information present in the retrieved review context.
2. Never invent customer opinions, ratings, or product details.
3. If the context is insufficient, say so clearly.
4. Structure insights: Sentiment Summary → Key Positives → Key Complaints → Business Recommendation.
5. Use the conversation context to make your answer feel like a natural continuation.
""".strip()


def _search_similar_chunks(question: str, top_k: int, min_similarity: float) -> list[dict]:
    query_vec = embed_query(question)
    vec_str = "[" + ",".join(str(x) for x in query_vec) + "]"

    sql = f"""
    SELECT product_id, chunk_type, review_text, similarity
    FROM (
        SELECT
            product_id,
            chunk_type,
            review_text,
            1 - (embedding <=> %s::vector) AS similarity
        FROM {_TABLE}
    ) ranked
    WHERE similarity >= %s
    ORDER BY similarity DESC
    LIMIT %s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (vec_str, min_similarity, top_k))
            rows = cur.fetchall()

    return [
        {
            "product_id": row[0],
            "chunk_type": row[1],
            "review_text": row[2],
            "similarity": round(float(row[3]), 4),
        }
        for row in rows
    ]


def _build_review_summary(
    question: str,
    chunks: list[dict],
    chat_history: list,
) -> str:
    history_ctx = format_history_for_prompt(chat_history, max_messages=2)

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Chunk {i} | type={chunk['chunk_type']} | similarity={chunk['similarity']:.2%}]\n"
            f"{chunk['review_text']}"
        )
    review_context = "\n\n---\n\n".join(context_parts)

    prompt = (
        f"{history_ctx}"
        f"Current question:\n{question}\n\n"
        f"Retrieved Review Context:\n{review_context}"
    )

    return llm.generate_response(
        system_prompt=_VECTOR_SYSTEM_PROMPT,
        user_prompt=prompt,
        temperature=0,
    )


def _average_similarity(chunks: list[dict]) -> float:
    if not chunks:
        return 0.0
    return round(sum(c["similarity"] for c in chunks) / len(chunks), 4)


def run_vector_agent(
    question: str,
    intent_response: dict,
    chat_history: list,
) -> dict:
    try:
        chunks = _search_similar_chunks(
            question=question,
            top_k=_TOP_K,
            min_similarity=_MIN_SIMILARITY,
        )

        if not chunks:
            return {
                "success": False,
                "confidence": 0.0,
                "source": "vector_agent",
                "response": (
                    "No sufficiently similar reviews were found for your question. "
                    "Try rephrasing or asking about a specific product attribute."
                ),
            }

        confidence = _average_similarity(chunks)
        response = _build_review_summary(
            question=question,
            chunks=chunks,
            chat_history=chat_history,
        )

        return {
            "success": True,
            "confidence": confidence,
            "source": "vector_agent",
            "data": chunks,
            "response": response,
        }

    except Exception as exc:
        return {
            "success": False,
            "confidence": 0.0,
            "source": "vector_agent",
            "response": f"Vector agent failed: {exc}",
        }
