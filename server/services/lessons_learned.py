"""Lessons Learned system for Seline to improve from mistakes."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..logging_config import logger


class LessonsLearnedService:
    """Manages lessons learned from errors and user feedback."""

    def __init__(self, lessons_file: Optional[Path] = None):
        """Initialize the lessons learned service."""
        if lessons_file is None:
            lessons_file = Path(__file__).parent.parent / "data" / "lessons_learned.json"

        self.lessons_file = lessons_file
        self.lessons_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize file if it doesn't exist
        if not self.lessons_file.exists():
            self._save_lessons([])

    def _load_lessons(self) -> List[Dict[str, Any]]:
        """Load lessons from file."""
        try:
            with open(self.lessons_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.error(f"Failed to load lessons: {exc}")
            return []

    def _save_lessons(self, lessons: List[Dict[str, Any]]) -> None:
        """Save lessons to file."""
        try:
            with open(self.lessons_file, "w", encoding="utf-8") as f:
                json.dump(lessons, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.error(f"Failed to save lessons: {exc}")

    def add_lesson(
        self,
        category: str,
        problem: str,
        solution: str,
        context: Optional[str] = None
    ) -> None:
        """
        Add a new lesson learned.

        Args:
            category: Category of the lesson (e.g., "agent_delegation", "tool_usage")
            problem: Description of the problem encountered
            solution: How to solve or avoid the problem
            context: Optional additional context
        """
        lessons = self._load_lessons()

        lesson = {
            "category": category,
            "problem": problem,
            "solution": solution,
            "context": context,
            "learned_at": datetime.utcnow().isoformat(),
            "occurrences": 1
        }

        # Check if similar lesson exists
        for existing in lessons:
            if (existing["category"] == category and
                existing["problem"].lower() == problem.lower()):
                # Increment occurrences instead of adding duplicate
                existing["occurrences"] = existing.get("occurrences", 1) + 1
                existing["last_seen"] = datetime.utcnow().isoformat()
                logger.info(
                    f"Incremented existing lesson in category '{category}'",
                    extra={"occurrences": existing["occurrences"]}
                )
                self._save_lessons(lessons)
                return

        # Add new lesson
        lessons.append(lesson)
        self._save_lessons(lessons)

        logger.info(
            f"New lesson learned in category '{category}'",
            extra={"problem": problem[:100]}
        )

    def get_lessons(
        self,
        category: Optional[str] = None,
        min_occurrences: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Get lessons, optionally filtered by category.

        Args:
            category: Optional category filter
            min_occurrences: Minimum occurrences to include

        Returns:
            List of lessons matching criteria
        """
        lessons = self._load_lessons()

        filtered = [
            lesson for lesson in lessons
            if lesson.get("occurrences", 1) >= min_occurrences
        ]

        if category:
            filtered = [l for l in filtered if l["category"] == category]

        # Sort by occurrences (most common first)
        filtered.sort(key=lambda x: x.get("occurrences", 1), reverse=True)

        return filtered

    def format_lessons_for_prompt(self, max_lessons: int = 10) -> str:
        """
        Format lessons for inclusion in system prompt.

        Args:
            max_lessons: Maximum number of lessons to include

        Returns:
            Formatted string ready for prompt injection
        """
        lessons = self.get_lessons()

        if not lessons:
            return ""

        # Take top lessons by occurrence
        top_lessons = lessons[:max_lessons]

        output = ["## 📚 LESSONS LEARNED\n"]
        output.append("These are mistakes you've made before. **AVOID REPEATING THEM:**\n")

        for i, lesson in enumerate(top_lessons, 1):
            occurrences = lesson.get("occurrences", 1)
            output.append(f"\n### Lesson {i} ({occurrences}x)")
            output.append(f"**Problem:** {lesson['problem']}")
            output.append(f"**Solution:** {lesson['solution']}")
            if lesson.get("context"):
                output.append(f"**Context:** {lesson['context']}")

        return "\n".join(output)

    def auto_learn_from_error(self, error_type: str, error_message: str) -> None:
        """
        Automatically learn from common error patterns.

        Args:
            error_type: Type of error (e.g., "RuntimeError", "ToolError")
            error_message: Error message
        """
        # Pattern: Tool iteration limit
        if "tool iteration limit" in error_message.lower():
            self.add_lesson(
                category="agent_delegation",
                problem="Atteint la limite d'itérations d'outils sans réponse finale",
                solution="Après la réponse d'un agent, donner IMMÉDIATEMENT une réponse finale en texte plain. Ne PAS rappeler send_message_to_agent.",
                context=f"Error: {error_message[:200]}"
            )

        # Pattern: Duplicate messages
        elif "duplicate" in error_message.lower():
            self.add_lesson(
                category="messaging",
                problem="Envoi de messages dupliqués à l'utilisateur",
                solution="Ne jamais appeler send_message_to_user avec le même texte plusieurs fois. Vérifier si le message a déjà été envoyé.",
                context=f"Error: {error_message[:200]}"
            )

        # Pattern: Agent not responding
        elif "agent" in error_message.lower() and "timeout" in error_message.lower():
            self.add_lesson(
                category="agent_delegation",
                problem="Timeout lors de l'attente d'une réponse d'agent",
                solution="Donner des instructions plus claires et concises aux agents. Si timeout, informer l'utilisateur et continuer.",
                context=f"Error: {error_message[:200]}"
            )


# Global singleton
_lessons_service: Optional[LessonsLearnedService] = None


def get_lessons_service() -> LessonsLearnedService:
    """Get the global lessons learned service."""
    global _lessons_service
    if _lessons_service is None:
        _lessons_service = LessonsLearnedService()
    return _lessons_service
