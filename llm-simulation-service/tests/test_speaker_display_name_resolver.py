from src.speaker_display_name_resolver import SpeakerDisplayNameResolver
from src.prompt_specification import AgentPromptSpecification, SystemPromptSpecification


class TestSpeakerDisplayNameResolver:
    def test_resolve_from_prompt_spec(self):
        prompt = SystemPromptSpecification(
            name="spec",
            version="1",
            description="",
            agents={"agent": AgentPromptSpecification(name="Sales", prompt="", tools=[])},
        )
        resolver = SpeakerDisplayNameResolver(prompt)
        assert resolver.resolve_display_name("agent_agent", "agent") == "Sales"

    def test_resolve_default_names(self):
        resolver = SpeakerDisplayNameResolver(None)
        assert resolver.resolve_display_name("client", None) == "Client"
        assert resolver.resolve_display_name("agent_support", None) == "Support Agent"

    def test_handle_missing_prompt_spec(self):
        resolver = SpeakerDisplayNameResolver({})
        assert resolver.resolve_display_name("agent", "missing") == "Agent"

