import json

from llm_config import llm

_INTENT_SYSTEM_PROMPT = """
You are an intent classification system for a fashion retail analytics assistant.

Classify the user's question into exactly one of these five agents:

────────────────────────────────────────────────────
1. sql_agent
   Use for PURE structured data queries with no need for review sentiment.
   Triggers: counts, rankings, inventory checks, price comparisons, availability,
   listing products by a single attribute (category, brand, price range).
   Examples:
   - "How many products are out of stock?"
   - "What are the top 10 most reviewed products?"
   - "Show all products from Nike under $40."
   - "What is the average price per category?"

2. vector_agent
   Use when the question is ENTIRELY about customer sentiment, opinions,
   review themes, or subjective quality perception — no filtering by structured
   attributes (color, size, brand, price) is needed.
   Examples:
   - "What do customers say about sizing?"
   - "Are buyers happy with the fabric quality?"
   - "What are the most common complaints?"
   - "Which products have the most negative reviews?"

3. trend_engine_agent
   Use for questions about fashion trends, rising/declining patterns, momentum,
   attribute popularity over time, or review velocity.
   Examples:
   - "What patterns are trending right now?"
   - "Which colors are becoming more popular?"
   - "What styles are losing popularity?"
   - "Which materials are customers preferring more this season?"

4. hybrid_agent
   Use when the question combines BOTH structured attribute filtering
   (color, size, brand, price, category, rating) AND review/recommendation context.
   This is the right choice for "suggest / recommend / best / worth buying" questions
   that reference specific attributes.
   Examples:
   - "Suggest me a black t-shirt with the highest ratings."
   - "Which red dresses are customers loving?"
   - "Best value cotton shirts under $30?"
   - "Are Nike polo shirts worth buying?"
   - "Recommend a dress that customers say is comfortable."
   - "What blue products have the best reviews?"
   - "Which brand makes the best quality jeans?"
   - "Find me highly rated products available in XL."

5. fallback
   Use for anything outside fashion retail analytics, greetings, unrelated topics,
   or requests the system cannot support.
   Examples:
   - "What's the weather today?"
   - "Tell me a joke."
   - "How do I cook pasta?"
   - "Who is the president?"

────────────────────────────────────────────────────
Routing rules:
- If the question mentions a specific color/size/brand/material AND asks for
  suggestions, recommendations, or review opinions → hybrid_agent
- If the question ONLY asks for a list/count/rank with no sentiment → sql_agent
- If the question ONLY asks about customer feelings/opinions with no attribute filter → vector_agent
- If the question is about fashion trend momentum/velocity → trend_engine_agent
- Anything else → fallback

Respond with ONLY valid JSON. No explanation, no markdown, no extra text.
{"agent": "<agent_name>", "confidence": <0.0–1.0>, "reason": "<one short sentence>"}
""".strip()


def detect_intent(question: str, chat_history: list) -> dict:
    history_context = ""
    if chat_history:
        recent = chat_history[-4:]
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
