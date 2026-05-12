"""
Context resolver — rewrites ambiguous follow-up questions into fully
self-contained standalone questions using recent conversation history.

Example:
  History : "Show me black cotton t-shirts"  →  assistant listed 5 products
  Question: "What is the price of it?"
  Resolved: "What is the price of the black cotton t-shirts listed earlier?"

Only fires when the question contains reference words (pronouns / demonstratives)
or is short enough to likely be a follow-up. Skipped for first questions or
when history is empty, so it adds zero latency for most messages.
"""

import os

from dotenv import load_dotenv
from llm_config import llm

load_dotenv()

_ENABLED = os.getenv("ENABLE_CONTEXT_RESOLUTION", "true").lower() == "true"

# Words that signal the question might reference something from history
_REFERENCE_TOKENS = frozenset([
    "it", "its", "this", "that", "they", "them", "these", "those",
    "one", "ones", "same", "similar", "previous", "earlier", "above",
    "mentioned", "shown", "listed", "that one", "those ones",
    "the product", "the item", "such products",
])

# Short questions are almost always follow-ups
_SHORT_QUESTION_THRESHOLD = 6  # words

_SYSTEM_PROMPT = """
You are a question-rewriting assistant for a fashion retail analytics chatbot.

Given a recent conversation and a follow-up question, rewrite the question
into a completely self-contained, standalone question that is unambiguous
without any conversation context.

Rules:
1. If the question is already standalone and unambiguous, return it EXACTLY unchanged.
2. Replace vague pronouns ("it", "this", "that", "they", "those", etc.) with
   the specific subject from the conversation.
3. Resolve relative references ("the one shown", "that product", "those items").
4. Keep the rewritten question natural and concise.
5. Return ONLY the final question — no explanation, no quotes, no prefix.
6. Never change the user's intent.

Examples:

History:
  User: Show me black t-shirts with high ratings
  Assistant: Here are the top 5 black t-shirts ranked by rating…
Question: What is the price of it?
Output: What is the price range of the black t-shirts shown earlier?

History:
  User: What Nike products are available?
  Assistant: Nike offers 12 products including polo shirts and hoodies…
Question: Are any of them available in XL?
Output: Are any Nike products available in XL?

History:
  User: What patterns are trending?
  Assistant: The top trending patterns are floral, striped, and solid…
Question: Tell me more about the top one
Output: Tell me more about the floral pattern which is the top trending pattern.
""".strip()


def _needs_resolution(question: str) -> bool:
    tokens = set(question.lower().split())
    if tokens & _REFERENCE_TOKENS:
        return True
    if len(question.split()) <= _SHORT_QUESTION_THRESHOLD:
        return True
    return False


def resolve_question(question: str, chat_history: list) -> str:
    """
    Returns a standalone version of `question`.
    Returns the original question unchanged if no resolution is needed.
    """
    if not _ENABLED or not chat_history or not _needs_resolution(question):
        return question

    # Build a compact conversation snippet (last 3 exchanges = 6 messages)
    recent = chat_history[-6:]
    lines = []
    for msg in recent:
        role = "User" if msg["role"] == "user" else "Assistant"
        content = msg["message"]
        if len(content) > 400:
            content = content[:400] + "…"
        lines.append(f"{role}: {content}")

    prompt = (
        "Conversation history:\n"
        + "\n".join(lines)
        + f"\n\nFollow-up question to rewrite:\n{question}"
    )

    try:
        resolved = llm.generate_response(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0,
        ).strip()

        # Sanity: if the model returned something very long or empty, fall back
        if not resolved or len(resolved) > 300:
            return question

        return resolved

    except Exception:
        return question
