"""
Hybrid agent: combines structured SQL filtering with vector review retrieval.
Use for questions that need both product attributes (color, price, category, brand)
AND customer opinion/review context — e.g. "suggest a black t-shirt with good reviews".
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from llm_config import llm
from tools.sql_agent import _generate_sql, _validate_sql, _execute_sql
from tools.vector_agent import _search_similar_chunks, _average_similarity
from utils.history import format_history_for_prompt

load_dotenv()

_TOP_K_HYBRID = int(os.getenv("HYBRID_TOP_K", 3))
_MIN_SIM_HYBRID = float(os.getenv("HYBRID_MIN_SIMILARITY", 0.20))

_HYBRID_SYSTEM_PROMPT = """
You are a fashion retail analytics assistant that combines structured product data
with customer review insights to give complete, actionable recommendations.

You will receive:
1. SQL product results — structured data (titles, brands, prices, ratings, attributes)
2. Customer review excerpts — what real buyers say about these or similar products

Rules:
1. Use ONLY the data provided. Never invent products, ratings, or prices.
2. Lead with concrete product recommendations from the SQL data (name, brand, price, rating).
3. Enrich recommendations with relevant customer sentiment from the reviews.
4. If SQL data is empty, rely solely on review context and state that clearly.
5. If review data is empty, rely solely on product data and state that clearly.
6. Use conversation context to make your answer feel like a natural continuation.
7. Always mention rating and price when available.
""".strip()


def _build_combined_response(
    question: str,
    sql_data: list[dict],
    vector_chunks: list[dict],
    chat_history: list,
) -> str:
    import json

    history_ctx = format_history_for_prompt(chat_history, max_messages=4)

    sql_section = (
        json.dumps(sql_data, default=str, indent=2)
        if sql_data else "No structured product data available."
    )

    if vector_chunks:
        review_parts = [
            f"[Review {i} | similarity={c['similarity']:.2%}]\n{c['review_text']}"
            for i, c in enumerate(vector_chunks, 1)
        ]
        review_section = "\n\n".join(review_parts)
    else:
        review_section = "No customer review data available."

    prompt = (
        f"{history_ctx}"
        f"Current question:\n{question}\n\n"
        f"Product Data ({len(sql_data)} results):\n{sql_section}\n\n"
        f"Customer Review Context:\n{review_section}"
    )

    return llm.generate_response(
        system_prompt=_HYBRID_SYSTEM_PROMPT,
        user_prompt=prompt,
        temperature=0,
    )


def run_hybrid_agent(
    question: str,
    intent_response: dict,
    chat_history: list,
) -> dict:
    sql_data: list[dict] = []
    sql_query: str = ""
    sql_success = False

    try:
        query = _generate_sql(question, chat_history)
        if _validate_sql(query):
            sql_data = _execute_sql(query)
            sql_query = query
            sql_success = True
    except Exception as exc:
        print(f"[hybrid_agent] SQL component failed: {exc}")

    vector_chunks: list[dict] = []
    try:
        vector_chunks = _search_similar_chunks(
            question=question,
            top_k=_TOP_K_HYBRID,
            min_similarity=_MIN_SIM_HYBRID,
        )
    except Exception as exc:
        print(f"[hybrid_agent] Vector component failed: {exc}")

    if not sql_success and not vector_chunks:
        return {
            "success": False,
            "confidence": 0.0,
            "source": "hybrid_agent",
            "response": (
                "I couldn't retrieve product or review data for that question. "
                "Try rephrasing with specific attributes like color, category, or brand."
            ),
        }

    sql_confidence = float(intent_response.get("confidence", 0.5)) if sql_success else 0.0
    vec_confidence = _average_similarity(vector_chunks) if vector_chunks else 0.0
    confidence = round(max(sql_confidence, vec_confidence), 4)

    response = _build_combined_response(
        question=question,
        sql_data=sql_data,
        vector_chunks=vector_chunks,
        chat_history=chat_history,
    )

    return {
        "success": True,
        "confidence": confidence,
        "source": "hybrid_agent",
        "sql_query": sql_query,
        "sql_data": sql_data,
        "vector_data": vector_chunks,
        "response": response,
    }
