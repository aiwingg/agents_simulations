from src.conversation_adapter import ConversationAdapter
from src.prompt_specification import AgentPromptSpecification, SystemPromptSpecification
from tests.test_utils.autogen_message_builders import AutogenMessageBuilder as B


class TestConversationAdapterIntegration:
    def test_extract_conversation_history_success(self):
        fc = B.create_function_call("c1", "find", "{}")
        exec_res = B.create_execution_result("c1", "find", "{\"result\": 1}")
        messages = [
            B.create_text_message("Hi", "client"),
            B.create_tool_call_request([fc], "sales_agent"),
            B.create_tool_execution_event([exec_res]),
            B.create_text_message("done", "sales_agent"),
        ]
        prompt = SystemPromptSpecification(
            name="spec",
            version="1",
            description="",
            agents={
                "sales_agent": AgentPromptSpecification(name="Sales", prompt="", tools=[]),
                "client": AgentPromptSpecification(name="Client", prompt="", tools=[]),
            },
        )
        history = ConversationAdapter.extract_conversation_history(messages, prompt)
        assert len(history) == 2
        assert history[0]["speaker_display"] == "Client"
        assert history[1]["tool_calls"]
        assert history[1]["tool_results"]


