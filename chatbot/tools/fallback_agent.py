import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_config import llm

_FALLBACK_SYSTEM_PROMPT = """
You are a fashion retail analytics assistant with a strictly defined scope.

Supported topics:
- Fashion trends and pattern analysis
- Product analytics and attribute insights
- Customer review intelligence and sentiment
- Pricing and availability analysis
- Trend forecasting for retail

Rules:
1. Politely decline to answer anything outside the supported topics above.
2. When declining, redirect the user toward a supported topic.
3. Keep responses concise and professional.
4. Never hallucinate information.
""".strip()

_GUIDANCE = {
    "low_confidence": (
        "The question was ambiguous or unclear for this system. "
        "Try asking about fashion trends, product attributes, customer reviews, "
        "pricing, or availability."
    ),
    "unsupported_agent": (
        "This type of request is not currently supported. "
        "Supported areas: trend analysis, review intelligence, "
        "pricing analytics, product attribute insights."
    ),
}

_DEFAULT_GUIDANCE = (
    "This assistant specialises in fashion retail analytics — trends, reviews, pricing, and product insights."
)


def run_fallback_agent(
    question: str,
    reason: str = "general",
) -> dict:
    try:
        guidance = _GUIDANCE.get(reason, _DEFAULT_GUIDANCE)
        prompt = f"User Question:\n{question}\n\nContext:\n{guidance}\n\nProvide a short, professional response."

        response = llm.generate_response(
            system_prompt=_FALLBACK_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0,
        )

        return {
            "success": True,
            "confidence": 0.3,
            "source": "fallback_agent",
            "response": response,
        }

    except Exception:
        return {
            "success": False,
            "confidence": 0.0,
            "source": "fallback_agent",
            "response": (
                "This assistant focuses on fashion analytics and retail trend intelligence. "
                "Please ask about products, trends, reviews, or pricing."
            ),
        }
