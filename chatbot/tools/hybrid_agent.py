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
from tools.vector_agent import _fetch_review_data
from utils.history import format_history_for_prompt

load_dotenv()

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

    history_ctx = format_history_for_prompt(chat_history, max_messages=2)

    display_sql = sql_data[:5]
    sql_section = (
        json.dumps(display_sql, default=str)
        if display_sql else "No structured product data available."
    )

    if vector_chunks:
        review_section = json.dumps(vector_chunks[:5], default=str)
    else:
        review_section = "No customer review data available."

    prompt = (
        f"{history_ctx}"
        f"Current question:\n{question}\n\n"
        f"Product Data ({len(display_sql)} results):\n{sql_section}\n\n"
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
            try:
                sql_data = _execute_sql(query)
            except Exception as sql_err:
                # Retry once with error feedback
                from tools.sql_agent import _generate_sql as _gen
                query = _gen(question, chat_history, error_feedback=str(sql_err))
                if _validate_sql(query):
                    sql_data = _execute_sql(query)
            sql_query = query
            sql_success = True
    except Exception as exc:
        print(f"[hybrid_agent] SQL component failed: {exc}")

    vector_chunks: list[dict] = []
    try:
        vector_chunks = _fetch_review_data(question)
    except Exception as exc:
        print(f"[hybrid_agent] Review component failed: {exc}")

    if not sql_success and not vector_chunks:
        return {
            "success": False,
            "confidence": 0.0,
            "source": "hybrid_agent",
            "response": (
                "No matching products found for those attributes in our database. "
                "Try broader criteria — e.g. drop the color filter or use a different category."
            ),
        }

    # If SQL returned results but no reviews, still answer from product data
    if sql_success and not sql_data:
        return {
            "success": False,
            "confidence": 0.0,
            "source": "hybrid_agent",
            "response": (
                "No products matched those exact filters. "
                "Try broadening the search — e.g. remove the color or fit constraint."
            ),
        }

    sql_confidence = float(intent_response.get("confidence", 0.5)) if sql_success else 0.0
    confidence = round(sql_confidence, 4)

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
