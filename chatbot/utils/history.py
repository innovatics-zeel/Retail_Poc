"""
Shared utility: format recent chat history for injection into LLM prompts.
All tool agents import this to provide coherent, context-aware responses.
"""

_MAX_CONTENT_CHARS = 350
_SEPARATOR = "\n" + "─" * 40 + "\n"


def format_history_for_prompt(
    chat_history: list,
    max_messages: int = 6,
) -> str:
    """
    Returns a formatted string of the last `max_messages` messages suitable
    for prepending to an LLM prompt.

    Returns an empty string if history is empty (no overhead for first question).
    """
    if not chat_history:
        return ""

    recent = chat_history[-max_messages:]
    lines = []
    for msg in recent:
        role = "User" if msg["role"] == "user" else "Assistant"
        content = str(msg.get("message", "")).strip()
        if len(content) > _MAX_CONTENT_CHARS:
            content = content[:_MAX_CONTENT_CHARS] + "…"
        lines.append(f"{role}: {content}")

    return (
        "Conversation context (for reference only — answer the current question):\n"
        + "\n".join(lines)
        + _SEPARATOR
    )
