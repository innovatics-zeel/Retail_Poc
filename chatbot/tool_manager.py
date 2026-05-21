import os
import re

from dotenv import load_dotenv

from tools.fallback_agent import run_fallback_agent
from tools.hybrid_agent import run_hybrid_agent
from tools.sql_agent import run_sql_agent
from tools.trend_agent import run_trend_engine_agent
from tools.vector_agent import run_vector_agent

load_dotenv()

_CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.75))
_REPEAT_QUESTION_THRESHOLD = int(os.getenv("REPEAT_QUESTION_THRESHOLD", 2))

# Hard keyword overrides — bypass LLM intent classification for known patterns
_SQL_OVERRIDE = re.compile(
    r'\b(mark\s?down|markdown|mark-down|zero.review|no.review|discount candidate|'
    r'slow.moving|overstock|price\s?gap|price\s?diff|median\s?price|price\s?compar|'
    r'whitespace|underserved|which stock|top.rated|best.rated|highest.rated|'
    r'most expensive|cheapest|lowest price)\b',
    re.I,
)
_TREND_OVERRIDE = re.compile(
    r'\b(trending|trend|momentum|rising|declining|fastest|lifecycle|velocity|'
    r'cross.channel|pattern.*channel|channel.*pattern|'
    r'outperform|doing better|perform better|gaining|losing momentum|'
    r'both channel|both platform|amazon.*nordstrom|nordstrom.*amazon|'
    r'color.*trend|sleeve.*trend|neck.*trend|fit.*trend|fabric.*trend|material.*trend)\b',
    re.I,
)


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

        # Python-level overrides — SQL check first, then trend (trend overrides LLM if matched)
        if _SQL_OVERRIDE.search(question):
            selected_agent = "sql_agent"
        elif _TREND_OVERRIDE.search(question):
            selected_agent = "trend_engine_agent"

        if confidence < _CONFIDENCE_THRESHOLD and not force_execute and selected_agent == "fallback":
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
