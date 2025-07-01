from autogen_agentchat.messages import TextMessage, ToolCallRequestEvent, ToolCallExecutionEvent
from autogen_core._types import FunctionCall
from autogen_core.models import FunctionExecutionResult


class AutogenMessageBuilder:
    """Helpers to create AutoGen messages for tests."""

    @staticmethod
    def create_text_message(content: str, speaker: str):
        return TextMessage(source=speaker, content=content)

    @staticmethod
    def create_tool_call_request(tool_calls, speaker: str):
        return ToolCallRequestEvent(source=speaker, content=tool_calls)

    @staticmethod
    def create_tool_execution_event(results):
        return ToolCallExecutionEvent(source="tool", content=results)

    @staticmethod
    def create_function_call(call_id: str, name: str, arguments: str) -> FunctionCall:
        return FunctionCall(id=call_id, name=name, arguments=arguments)

    @staticmethod
    def create_execution_result(call_id: str, name: str, content: str) -> FunctionExecutionResult:
        return FunctionExecutionResult(call_id=call_id, name=name, content=content, is_error=False)

