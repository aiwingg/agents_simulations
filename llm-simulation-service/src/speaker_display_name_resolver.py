"""Resolve human friendly display names for conversation speakers."""

from typing import Any, Dict

from src.logging_utils import get_logger


class SpeakerDisplayNameResolver:
    """Resolve speaker display names using prompt specifications."""

    def __init__(self, prompt_spec: Any | None) -> None:
        self.logger = get_logger()
        self.display_map = self._build_display_name_map(prompt_spec)

    def resolve_display_name(self, speaker: str, agent_id: str | None) -> str:
        if agent_id and agent_id in self.display_map:
            return self.display_map[agent_id]
        return self._get_default_display_name(speaker)

    def _build_display_name_map(self, prompt_spec: Any | None) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        if not prompt_spec:
            return mapping
        try:
            agents = getattr(prompt_spec, "agents", {})
            for agent_id, spec in agents.items():
                if hasattr(spec, "name"):
                    mapping[agent_id] = spec.name
                elif isinstance(spec, dict):
                    mapping[agent_id] = spec.get("name", agent_id)
        except Exception as exc:  # pragma: no cover - log but don't crash
            self.logger.log_error("Failed to build display name map", exception=exc)
        return mapping

    @staticmethod
    def _get_default_display_name(speaker: str) -> str:
        if speaker == "client":
            return "Client"
        if speaker.startswith("agent_"):
            agent_type = speaker.replace("agent_", "")
            return "Agent" if agent_type == "agent" else f"{agent_type.capitalize()} Agent"
        return speaker.capitalize() if speaker else "Unknown"
