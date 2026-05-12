"""
Session-scoped chat memory backed by Redis (in-memory fallback if Redis is down).

Key design decisions:
- History is capped at MAX_CHAT_HISTORY messages (sliding window).
- delete_session() explicitly removes ALL keys for a session — call this on
  "Clear Chat" so no user data lingers in Redis beyond what they expect.
- Session keys follow the pattern  chat_history:<uuid>  so they never
  contain any personally identifiable information.
- TTL is applied to every write (default 1 h), so abandoned sessions
  self-expire without any manual cleanup.
"""

import os

from utils.redis_cache import redis_cache

_MAX_HISTORY = int(os.getenv("MAX_CHAT_HISTORY", 20))


class MemoryManager:
    # ── Key builders ──────────────────────────────────────────────────────────

    @staticmethod
    def _history_key(session_id: str) -> str:
        return f"chat_history:{session_id}"

    @staticmethod
    def _question_key(session_id: str, question: str) -> str:
        return f"question_count:{session_id}:{question.strip().lower()}"

    # ── Message persistence ───────────────────────────────────────────────────

    def save_message(
        self,
        session_id: str,
        role: str,
        message: str,
    ) -> None:
        key = self._history_key(session_id)
        history: list = redis_cache.get_data(key) or []

        history.append({"role": role, "message": message})

        # Enforce sliding window — keep only the most recent N messages
        if len(history) > _MAX_HISTORY:
            history = history[-_MAX_HISTORY:]

        redis_cache.set_data(key, history)

    def get_chat_history(self, session_id: str) -> list:
        return redis_cache.get_data(self._history_key(session_id)) or []

    # ── Repeat-question detection ─────────────────────────────────────────────

    def increment_question_count(self, session_id: str, question: str) -> None:
        key = self._question_key(session_id, question)
        entry = redis_cache.get_data(key) or {"count": 0}
        entry["count"] += 1
        redis_cache.set_data(key, entry)

    def get_question_count(self, session_id: str, question: str) -> int:
        entry = redis_cache.get_data(self._question_key(session_id, question))
        return entry["count"] if entry else 0

    # ── Session lifecycle (privacy) ───────────────────────────────────────────

    def delete_session(self, session_id: str) -> None:
        """
        Permanently remove all Redis data associated with this session.
        Call this when the user explicitly clears their chat so no history
        persists beyond their intent.
        """
        # Delete the conversation log
        redis_cache.delete_data(self._history_key(session_id))

        # Delete all question-count entries for this session
        redis_cache.delete_pattern(f"question_count:{session_id}:*")


memory_manager = MemoryManager()
