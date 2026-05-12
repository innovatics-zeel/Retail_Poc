"""
Orchestrator — the single entry point that handles one user turn.

Flow per question:
  1. Persist user message → Redis (session memory)
  2. Load full chat history for this session
  3. Context resolution: rewrite ambiguous follow-ups into standalone questions
     e.g. "what was the price of it?" → "what was the price of the black t-shirt?"
  4. Classify intent of the resolved question (sql / vector / trend / hybrid / fallback)
  5. Execute the appropriate tool agent, passing history for contextual responses
  6. Persist assistant response → Redis
  7. Return the final answer + all debug artefacts
"""

from context_resolver import resolve_question
from intent_agent import detect_intent
from memory_manager import memory_manager
from tool_manager import execute_tool


class Orchestrator:
    def process_question(
        self,
        session_id: str,
        question: str,
    ) -> dict:
        try:
            # 1. Save user turn
            memory_manager.save_message(session_id=session_id, role="user", message=question)

            # 2. Load history (includes the message we just saved)
            chat_history = memory_manager.get_chat_history(session_id)

            # 3. Resolve context — history is everything BEFORE the current question
            prior_history = chat_history[:-1]  # exclude the message we just appended
            resolved_question = resolve_question(question, prior_history)

            # 4. Repeat-question tracking (on the original wording)
            repeated_count = memory_manager.get_question_count(session_id, question)
            memory_manager.increment_question_count(session_id, question)

            # 5. Intent detection on the resolved (standalone) question
            intent_response = detect_intent(
                question=resolved_question,
                chat_history=prior_history,
            )

            # 6. Tool execution — agents receive full history for contextual responses
            tool_response = execute_tool(
                question=resolved_question,
                intent_response=intent_response,
                repeated_question_count=repeated_count,
                chat_history=prior_history,
            )

            final_response = tool_response.get("response") or "Unable to process the request."

            # 7. Save assistant turn
            memory_manager.save_message(
                session_id=session_id,
                role="assistant",
                message=final_response,
            )

            return {
                "success": True,
                "response": final_response,
                "resolved_question": resolved_question if resolved_question != question else None,
                "intent": intent_response,
                "tool_response": tool_response,
            }

        except Exception as exc:
            return {
                "success": False,
                "response": f"Error processing request: {exc}",
                "resolved_question": None,
                "intent": None,
                "tool_response": None,
            }

    def clear_session(self, session_id: str) -> None:
        """Explicitly delete all Redis data for this session (privacy)."""
        memory_manager.delete_session(session_id)


orchestrator = Orchestrator()
