from unittest.mock import Mock, patch

from src.evaluator import ConversationEvaluator
from src.openai_wrapper import OpenAIWrapper


@patch("src.evaluator.PromptSpecificationManager")
def test_format_conversation_roles(mock_manager):
    # Avoid loading real prompt specifications
    mock_manager.return_value.load_specification.return_value = Mock(get_agent_prompt=Mock(return_value=None))
    evaluator = ConversationEvaluator(Mock(spec=OpenAIWrapper), "test_spec")

    history = [
        {"turn": 1, "speaker": "client", "content": "Hello"},
        {"turn": 2, "speaker": "agent_flow_manager", "content": "Hi"},
        {"turn": 3, "speaker": "agent_nomenclature_lookup", "content": "Here"},
        {"turn": 4, "speaker": "client", "content": "Bye"},
        {"turn": 5, "speaker": "agent_agent", "content": "Done"},
    ]

    formatted = evaluator._format_conversation_for_evaluation(history)

    assert "Ход 1 - client: Hello" in formatted
    assert "Ход 2 - flow_manager: Hi" in formatted
    assert "Ход 3 - nomenclature_lookup: Here" in formatted
    assert "Ход 4 - client: Bye" in formatted
    assert "Ход 5 - agent: Done" in formatted
