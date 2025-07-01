"""Scenario processing logic with engine isolation."""

from typing import Any, Dict, Tuple

from src.openai_wrapper import OpenAIWrapper
from src.logging_utils import get_logger


class ScenarioProcessor:
    """Process individual scenarios using isolated engines."""

    def __init__(self, openai_wrapper: OpenAIWrapper, progress_tracker: "BatchProgressTracker"):
        self.openai_wrapper = openai_wrapper
        self.progress_tracker = progress_tracker
        self.logger = get_logger()

    async def process_scenario(
        self,
        scenario: Dict[str, Any],
        scenario_index: int,
        batch_id: str,
        prompt_spec_name: str,
        use_tools: bool,
    ) -> Dict[str, Any]:
        """Run conversation and evaluation for a single scenario."""
        scenario_name = scenario.get("name", f"scenario_{scenario_index}")
        engine, evaluator = self._create_isolated_engines(prompt_spec_name)
        self.logger.log_info(
            f"Processing scenario {scenario_index}: {scenario_name}",
            extra_data={"batch_id": batch_id},
        )
        if use_tools:
            conversation_result = await engine.run_conversation_with_tools(scenario)
        else:
            conversation_result = await engine.run_conversation(scenario)

        evaluation_result = None
        if conversation_result.get("status") in {"completed", "timeout"}:
            evaluation_result = await evaluator.evaluate_conversation(conversation_result)

        result = self._format_scenario_result(
            conversation_result,
            evaluation_result,
            scenario_index,
            scenario_name,
        )

        if result["status"] in {"completed", "failed_api_blocked", "timeout"}:
            await self.progress_tracker.complete_scenario()
        else:
            await self.progress_tracker.fail_scenario()
        return result

    def _create_isolated_engines(
        self, prompt_spec_name: str
    ) -> Tuple["AutogenConversationEngine", "ConversationEvaluator"]:
        """Create fresh conversation engine and evaluator."""
        from src.autogen_conversation_engine import AutogenConversationEngine
        from src.evaluator import ConversationEvaluator

        engine = AutogenConversationEngine(self.openai_wrapper, prompt_spec_name)
        evaluator = ConversationEvaluator(self.openai_wrapper, prompt_spec_name)
        return engine, evaluator

    def _format_scenario_result(
        self,
        conversation_result: Dict[str, Any],
        evaluation_result: Dict[str, Any] | None,
        scenario_index: int,
        scenario_name: str,
    ) -> Dict[str, Any]:
        """Combine conversation and evaluation results."""
        status = conversation_result.get("status")
        if status == "completed":
            return {
                "scenario_index": scenario_index,
                "scenario": scenario_name,
                "session_id": conversation_result.get("session_id"),
                "status": "completed",
                "total_turns": conversation_result.get("total_turns"),
                "duration_seconds": conversation_result.get("duration_seconds"),
                "score": evaluation_result.get("score") if evaluation_result else None,
                "comment": evaluation_result.get("comment") if evaluation_result else None,
                "evaluation_status": evaluation_result.get("evaluation_status") if evaluation_result else None,
                "start_time": conversation_result.get("start_time"),
                "end_time": conversation_result.get("end_time"),
                "conversation_history": conversation_result.get("conversation_history"),
            }
        if status == "failed_api_blocked":
            return {
                "scenario_index": scenario_index,
                "scenario": scenario_name,
                "session_id": conversation_result.get("session_id"),
                "status": "failed_api_blocked",
                "error": conversation_result.get("error"),
                "total_turns": conversation_result.get("total_turns", 0),
                "duration_seconds": conversation_result.get("duration_seconds", 0),
                "score": 2 if conversation_result.get("partial_completion") else 1,
                "comment": f"API заблокирован (географические ограничения). Сделано ходов: {conversation_result.get('total_turns', 0)}",
                "conversation_history": conversation_result.get("conversation_history", []),
                "graceful_degradation": True,
                "partial_completion": conversation_result.get("partial_completion", False),
            }
        if status == "timeout":
            return {
                "scenario_index": scenario_index,
                "scenario": scenario_name,
                "session_id": conversation_result.get("session_id"),
                "status": "timeout",
                "error": conversation_result.get("error"),
                "total_turns": conversation_result.get("total_turns", 0),
                "duration_seconds": conversation_result.get("duration_seconds"),
                "score": evaluation_result.get("score") if evaluation_result else None,
                "comment": evaluation_result.get("comment") if evaluation_result else None,
                "evaluation_status": evaluation_result.get("evaluation_status") if evaluation_result else None,
                "start_time": conversation_result.get("start_time"),
                "end_time": conversation_result.get("end_time"),
                "conversation_history": conversation_result.get("conversation_history", []),
            }
        return {
            "scenario_index": scenario_index,
            "scenario": scenario_name,
            "session_id": conversation_result.get("session_id"),
            "status": "failed",
            "error": conversation_result.get("error"),
            "total_turns": conversation_result.get("total_turns", 0),
            "score": 1,
            "comment": f"Разговор не завершен: {conversation_result.get('error', 'неизвестная ошибка')}",
        }

