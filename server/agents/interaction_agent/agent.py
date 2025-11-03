"""Interaction agent helpers for prompt construction."""

from html import escape
from pathlib import Path
from typing import Dict, List

from ...services.execution import get_agent_roster
from ...services.user_profile import get_user_profile

_prompt_path = Path(__file__).parent / "system_prompt.md"
SYSTEM_PROMPT = _prompt_path.read_text(encoding="utf-8").strip()


# Load and return the pre-defined system prompt from markdown file with user profile
def build_system_prompt() -> str:
    """Return the system prompt for the interaction agent with user profile information."""
    profile_store = get_user_profile()
    profile = profile_store.load()

    user_context = []
    if profile.get("userName"):
        user_context.append(f"- User's name: {profile['userName']}")
    if profile.get("birthDate"):
        user_context.append(f"- User's date of birth: {profile['birthDate']}")
    if profile.get("location"):
        user_context.append(f"- User's location: {profile['location']}")

    if user_context:
        profile_section = "\n\n# USER PROFILE\n\nYou have access to the following information about the user:\n\n" + "\n".join(user_context) + "\n\nUse this information to personalize your responses when relevant. Remember these details naturally without explicitly mentioning you have this information unless necessary."
        return SYSTEM_PROMPT + profile_section

    return SYSTEM_PROMPT


# Build structured message with conversation history, active agents, and current turn
def prepare_message_with_history(
    latest_text: str,
    transcript: str,
    message_type: str = "user",
) -> List[Dict[str, str]]:
    """Compose a message that bundles history, roster, and the latest turn."""
    sections: List[str] = []

    sections.append(_render_conversation_history(transcript))
    sections.append(f"<active_agents>\n{_render_active_agents()}\n</active_agents>")
    sections.append(_render_current_turn(latest_text, message_type))

    content = "\n\n".join(sections)
    return [{"role": "user", "content": content}]


# Format conversation transcript into XML tags for LLM context
def _render_conversation_history(transcript: str) -> str:
    history = transcript.strip()
    if not history:
        history = "None"
    return f"<conversation_history>\n{history}\n</conversation_history>"


# Format currently active execution agents into XML tags for LLM awareness
def _render_active_agents() -> str:
    roster = get_agent_roster()
    roster.load()
    agents = roster.get_agents()

    if not agents:
        return "None"

    rendered: List[str] = []
    for agent_name in agents:
        name = escape(agent_name or "agent", quote=True)
        rendered.append(f'<agent name="{name}" />')

    return "\n".join(rendered)


# Wrap the current message in appropriate XML tags based on sender type
def _render_current_turn(latest_text: str, message_type: str) -> str:
    tag = "new_agent_message" if message_type == "agent" else "new_user_message"
    body = latest_text.strip()
    return f"<{tag}>\n{body}\n</{tag}>"
