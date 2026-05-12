import os

from dotenv import load_dotenv

from tools.fallback_agent import run_fallback_agent
from tools.hybrid_agent import run_hybrid_agent
from tools.sql_agent import run_sql_agent
from tools.trend_agent import run_trend_engine_agent
from tools.vector_agent import run_vector_agent

load_dotenv()

_CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.75))
_REPEAT_QUESTION_THRESHOLD = int(os.getenv("REPEAT_QUESTION_THRESHOLD", 2))


def execute_tool(
    question: str,
    intent_response: dict,
    repeated_question_count: int,
    chat_history: list,
) -> dict:
    try:
        selected_agent = intent_response.get("agent")
        confidence = float(intent_response.get("confidence", 0))
        force_execute = repeated_question_count >= _REPEAT_QUESTION_THRESHOLD

        if confidence < _CONFIDENCE_THRESHOLD and not force_execute:
            return run_fallback_agent(question=question, reason="low_confidence")

        if selected_agent == "sql_agent":
            return run_sql_agent(
                question=question,
                intent_response=intent_response,
                chat_history=chat_history,
            )

        if selected_agent == "vector_agent":
            return run_vector_agent(
                question=question,
                intent_response=intent_response,
                chat_history=chat_history,
            )

        if selected_agent == "trend_engine_agent":
            return run_trend_engine_agent(
                question=question,
                intent_response=intent_response,
                chat_history=chat_history,
            )

        if selected_agent == "hybrid_agent":
            return run_hybrid_agent(
                question=question,
                intent_response=intent_response,
                chat_history=chat_history,
            )

        return run_fallback_agent(question=question, reason="unsupported_agent")

    except Exception as exc:
        return {
            "success": False,
            "confidence": 0.0,
            "source": "tool_manager",
            "response": f"Tool execution failed: {exc}",
        }
