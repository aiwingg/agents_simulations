import pytest
from unittest.mock import AsyncMock, patch

from src.batch_processor import BatchProcessor

class DummyStorage:
    def load_all_batches(self):
        return {}
    def save_batch_metadata(self, batch_data):
        pass

@pytest.mark.asyncio
async def test_timeout_conversation_evaluated():
    # Patch storage to avoid filesystem writes
    with patch('src.batch_processor.PersistentBatchStorage', return_value=DummyStorage()):
        processor = BatchProcessor("test_key", concurrency=1)

    scenario = {"name": "sc", "variables": {}}
    batch_id = processor.create_batch_job([scenario], prompt_spec_name="test_prompts")

    conversation_result = {
        'session_id': 's123',
        'scenario': 'sc',
        'status': 'timeout',
        'error': 'timeout after 5',
        'total_turns': 2,
        'duration_seconds': 5,
        'conversation_history': [],
        'start_time': '2024-01-01T00:00:00',
        'end_time': '2024-01-01T00:00:05'
    }
    evaluation_result = {
        'score': 2,
        'comment': 'partial ok',
        'evaluation_status': 'success'
    }

    with patch('src.autogen_conversation_engine.AutogenConversationEngine') as MockEngine, \
         patch('src.evaluator.ConversationEvaluator') as MockEvaluator:
        mock_engine = MockEngine.return_value
        mock_engine.run_conversation_with_tools = AsyncMock(return_value=conversation_result)
        mock_eval = MockEvaluator.return_value
        mock_eval.evaluate_conversation = AsyncMock(return_value=evaluation_result)

        result = await processor._process_single_scenario(scenario, 0, batch_id)
        mock_eval.evaluate_conversation.assert_awaited_once_with(conversation_result)

    assert result['status'] == 'timeout'
    assert result['score'] == evaluation_result['score']
    assert result['comment'] == evaluation_result['comment']
    assert result['duration_seconds'] == conversation_result['duration_seconds']
    assert result['start_time'] == conversation_result['start_time']
    assert result['end_time'] == conversation_result['end_time']
