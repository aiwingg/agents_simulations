import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from src.scenario_processor import ScenarioProcessor
from src.batch_progress_tracker import BatchProgressTracker
from src.batch_processor import BatchJob, BatchStatus
from src.openai_wrapper import OpenAIWrapper


class DummyWrapper(OpenAIWrapper):
    def __init__(self):
        pass


@pytest.mark.asyncio
async def test_process_scenario_timeout():
    job = BatchJob(
        batch_id="b1",
        scenarios=[{"name": "sc"}],
        status=BatchStatus.PENDING,
        created_at=datetime.now(),
        prompt_spec_name="spec",
    )
    tracker = BatchProgressTracker(job)
    processor = ScenarioProcessor(DummyWrapper(), tracker)

    conversation_result = {
        "session_id": "s1",
        "status": "timeout",
        "error": "t",
        "total_turns": 1,
        "duration_seconds": 5,
        "conversation_history": [],
        "start_time": "s",
        "end_time": "e",
    }
    evaluation_result = {"score": 2, "comment": "ok", "evaluation_status": "s"}

    with (
        patch("src.autogen_conversation_engine.AutogenConversationEngine") as MockEngine,
        patch("src.evaluator.ConversationEvaluator") as MockEval,
    ):
        MockEngine.return_value.run_conversation_with_tools = AsyncMock(return_value=conversation_result)
        MockEval.return_value.evaluate_conversation = AsyncMock(return_value=evaluation_result)

        result = await processor.process_scenario({"name": "sc"}, 0, "b1", "spec", True)
        MockEval.return_value.evaluate_conversation.assert_awaited_once_with(conversation_result)

    assert result["status"] == "timeout"
    assert result["score"] == evaluation_result["score"]
    assert tracker.job.completed_scenarios == 1


@pytest.mark.asyncio
async def test_engine_isolation():
    job = BatchJob(
        batch_id="b2",
        scenarios=[{"name": "a"}, {"name": "b"}],
        status=BatchStatus.PENDING,
        created_at=datetime.now(),
        prompt_spec_name="spec",
    )
    tracker = BatchProgressTracker(job)
    processor = ScenarioProcessor(DummyWrapper(), tracker)

    with patch("src.autogen_conversation_engine.AutogenConversationEngine") as MockEngine:
        MockEngine.return_value.run_conversation_with_tools = AsyncMock(return_value={"status": "failed"})
        with patch("src.evaluator.ConversationEvaluator"):
            await processor.process_scenario({"name": "a"}, 0, "b2", "spec", True)
            await processor.process_scenario({"name": "b"}, 1, "b2", "spec", True)

        assert MockEngine.call_count == 2
@pytest.mark.asyncio
async def test_process_scenario_success():
    job = BatchJob(
        batch_id="b3",
        scenarios=[{"name": "sc"}],
        status=BatchStatus.PENDING,
        created_at=datetime.now(),
        prompt_spec_name="spec",
    )
    tracker = BatchProgressTracker(job)
    processor = ScenarioProcessor(DummyWrapper(), tracker)

    conversation_result = {
        "session_id": "s2",
        "status": "completed",
        "total_turns": 3,
        "duration_seconds": 4,
        "conversation_history": [],
        "start_time": "s",
        "end_time": "e",
    }
    evaluation_result = {"score": 5, "comment": "ok", "evaluation_status": "s"}

    with (
        patch("src.autogen_conversation_engine.AutogenConversationEngine") as MockEngine,
        patch("src.evaluator.ConversationEvaluator") as MockEval,
    ):
        MockEngine.return_value.run_conversation_with_tools = AsyncMock(return_value=conversation_result)
        MockEval.return_value.evaluate_conversation = AsyncMock(return_value=evaluation_result)

        result = await processor.process_scenario({"name": "sc"}, 0, "b3", "spec", True)
        MockEval.return_value.evaluate_conversation.assert_awaited_once_with(conversation_result)

    assert result["status"] == "completed"
    assert result["score"] == evaluation_result["score"]
    assert tracker.job.completed_scenarios == 1
    assert tracker.job.failed_scenarios == 0


@pytest.mark.asyncio
async def test_process_scenario_api_blocked():
    job = BatchJob(
        batch_id="b4",
        scenarios=[{"name": "sc"}],
        status=BatchStatus.PENDING,
        created_at=datetime.now(),
        prompt_spec_name="spec",
    )
    tracker = BatchProgressTracker(job)
    processor = ScenarioProcessor(DummyWrapper(), tracker)

    conversation_result = {
        "session_id": "s3",
        "status": "failed_api_blocked",
        "error": "geo",
        "total_turns": 1,
        "duration_seconds": 1,
        "conversation_history": [],
        "partial_completion": True,
    }

    with (
        patch("src.autogen_conversation_engine.AutogenConversationEngine") as MockEngine,
        patch("src.evaluator.ConversationEvaluator") as MockEval,
    ):
        MockEngine.return_value.run_conversation_with_tools = AsyncMock(return_value=conversation_result)
        result = await processor.process_scenario({"name": "sc"}, 0, "b4", "spec", True)
        MockEval.return_value.evaluate_conversation.assert_not_called()

    assert result["status"] == "failed_api_blocked"
    assert result["score"] == 2
    assert tracker.job.completed_scenarios == 1
    assert tracker.job.failed_scenarios == 0
