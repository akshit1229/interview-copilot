"""
Rolling conversation history manager.
Maintains a bounded window of interviewer questions and AI-generated answers.
"""

from app.config import settings


class ConversationHistory:
    """Thread-safe rolling window of interview conversation turns."""

    def __init__(self, max_turns: int | None = None):
        self.max_turns = max_turns or settings.MAX_HISTORY_TURNS
        self._turns: list[dict] = []

    def add_question(self, text: str):
        """Record an interviewer question."""
        self._turns.append({"role": "user", "content": text})
        self._trim()

    def add_answer(self, text: str):
        """Record the AI-generated answer."""
        self._turns.append({"role": "assistant", "content": text})
        self._trim()

    def _trim(self):
        """Keep only the last N turns (each Q+A = 2 turns)."""
        max_items = self.max_turns * 2
        if len(self._turns) > max_items:
            self._turns = self._turns[-max_items:]

    def get_messages(self) -> list[dict]:
        """Return history as OpenAI-format message list."""
        return list(self._turns)

    def get_formatted_text(self) -> str:
        """Return history as readable text for prompt context."""
        lines = []
        for turn in self._turns:
            prefix = "Q" if turn["role"] == "user" else "A"
            lines.append(f"{prefix}: {turn['content']}")
        return "\n".join(lines)

    def clear(self):
        """Clear all history (e.g., for a new interview session)."""
        self._turns.clear()

    @property
    def turn_count(self) -> int:
        """Number of Q&A pairs recorded."""
        return len(self._turns) // 2
