import json

from llm_config import llm

_INTENT_SYSTEM_PROMPT = """
Classify the user's retail analytics question into one of five agents. Respond with ONLY valid JSON — no explanation, no markdown.
{"agent": "<agent_name>", "confidence": <0.0–1.0>, "reason": "<one short sentence>"}

Agents:
1. sql_agent — counts, rankings, inventory, price comparisons, listing by attribute, mark-down candidates, overstock, which products to discount. e.g. "How many products are out of stock?", "Which stock should I mark down?", "What's the highest-priced slow-moving item?"
2. vector_agent — customer sentiment/opinions/reviews with no attribute filter. e.g. "What do customers say about sizing?"
3. trend_engine_agent — trend momentum, rising/declining attributes over time, lifecycle stage, velocity direction. e.g. "Which colors are trending?", "What's declining fastest?", "Which pattern has the strongest momentum?"
4. hybrid_agent — BOTH attribute filtering AND review/recommendation context. e.g. "Suggest a black t-shirt with good reviews."
5. fallback — greetings, anything outside fashion retail analytics, unclear questions.

Routing rules (in priority order):
- greetings, "hello", "hi", off-topic → fallback
- "mark down", "markdown", "discount", "overstock", "clear inventory", "which stock", "slow moving" → sql_agent
- "whitespace", "gap", "underserved", "missing", "opportunity" → sql_agent
- "nordstrom only", "amazon only", "platform only", specific platform comparison → sql_agent
- "median price", "price gap", "price band", "converting" → sql_agent
- attribute filter + recommendation/opinion → hybrid_agent
- only list/count/rank/price → sql_agent
- only sentiment, no filter → vector_agent
- "trend", "trending", "momentum", "rising", "declining", "fastest", "lifecycle", "velocity", "watch" → trend_engine_agent
- else → fallback
""".strip()


def detect_intent(question: str, chat_history: list) -> dict:
    history_context = ""
    if chat_history:
        recent = chat_history[-2:]
        lines = [f"{m['role'].capitalize()}: {m['message']}" for m in recent]
        history_context = "\nRecent conversation:\n" + "\n".join(lines)

    user_prompt = f"Question: {question}{history_context}"

    try:
        raw = llm.generate_response(
            system_prompt=_INTENT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0,
        )

        result = json.loads(raw.strip())

        valid_agents = {
            "sql_agent",
            "vector_agent",
            "trend_engine_agent",
            "hybrid_agent",
            "fallback",
        }
        if result.get("agent") not in valid_agents:
            result["agent"] = "fallback"

        result.setdefault("confidence", 0.5)
        result.setdefault("reason", "")

        return result

    except (json.JSONDecodeError, KeyError, Exception):
        return {
            "agent": "fallback",
            "confidence": 0.3,
            "reason": "intent classification failed",
        }
