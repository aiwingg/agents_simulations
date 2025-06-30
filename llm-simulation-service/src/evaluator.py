"""
Evaluator system for scoring conversations
"""

import json
from typing import Dict, List, Any, Tuple, Optional
from src.config import Config
from src.openai_wrapper import OpenAIWrapper
from src.logging_utils import get_logger
from src.prompt_specification import PromptSpecificationManager


class ConversationEvaluator:
    """Evaluates conversations and provides scores with comments"""

    def __init__(self, openai_wrapper: OpenAIWrapper, prompt_spec_name: str = "default_prompts"):
        self.openai = openai_wrapper
        self.logger = get_logger()

        # Load evaluator prompt from specification
        self.prompt_manager = PromptSpecificationManager()
        self.prompt_specification = self.prompt_manager.load_specification(prompt_spec_name)

        evaluator_spec = self.prompt_specification.get_agent_prompt("evaluator")
        if evaluator_spec:
            self.evaluator_prompt = evaluator_spec.prompt
        else:
            self.logger.log_error("No evaluator specification found, using fallback prompt")
            self.evaluator_prompt = """You are an expert evaluator of customer service conversations. 
            Evaluate the conversation and respond with JSON: {"score": [1,2,3], "comment": "explanation"}"""

        self.logger.log_info(f"ConversationEvaluator initialized with prompt specification: {prompt_spec_name}")

    def _format_conversation_for_evaluation(self, conversation_history: List[Dict[str, Any]]) -> str:
        """Format conversation history for evaluation"""
        formatted_conversation = "=== РАЗГОВОР ДЛЯ ОЦЕНКИ ===\n\n"

        for entry in conversation_history:
            raw_speaker = entry.get("speaker", "")
            if raw_speaker == "client":
                speaker = "client"
            elif raw_speaker.startswith("agent_"):
                speaker = raw_speaker.replace("agent_", "")
            else:
                speaker = raw_speaker or "agent"

            content = entry.get("content", "")
            turn = entry.get("turn")

            formatted_conversation += f"Ход {turn} - {speaker}: {content}\n\n"

        formatted_conversation += "=== КОНЕЦ РАЗГОВОРА ==="
        return formatted_conversation

    async def evaluate_conversation(self, conversation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a conversation and return score with comment"""

        session_id = conversation_data.get("session_id", "unknown")
        conversation_history = conversation_data.get("conversation_history", [])
        scenario = conversation_data.get("scenario", "unknown")

        self.logger.log_info(
            f"Evaluating conversation",
            extra_data={
                "session_id": session_id,
                "scenario": scenario,
                "total_turns": len(conversation_history),
            },
        )

        try:
            # Format conversation for evaluation
            formatted_conversation = self._format_conversation_for_evaluation(conversation_history)

            # Prepare messages for evaluator
            messages = [
                {"role": "system", "content": self.evaluator_prompt},
                {"role": "user", "content": formatted_conversation},
            ]

            # Get evaluation from LLM with JSON format
            evaluation_response, usage = await self.openai.json_completion(
                messages=messages,
                session_id=session_id,
                temperature=0.3,  # Lower temperature for more consistent evaluation
            )

            # Parse and validate evaluation
            score, comment = self._parse_evaluation_response(evaluation_response, session_id)

            evaluation_result = {
                "session_id": session_id,
                "scenario": scenario,
                "score": score,
                "comment": comment,
                "evaluation_status": "success",
                "raw_response": evaluation_response,
            }

            self.logger.log_info(
                f"Conversation evaluation completed",
                extra_data={
                    "session_id": session_id,
                    "score": score,
                    "comment_length": len(comment) if comment else 0,
                },
            )

            return evaluation_result

        except Exception as e:
            self.logger.log_error(
                f"Failed to evaluate conversation",
                exception=e,
                extra_data={"session_id": session_id, "scenario": scenario},
            )

            return {
                "session_id": session_id,
                "scenario": scenario,
                "score": 1,
                "comment": f"Ошибка оценки разговора: {str(e)}",
                "evaluation_status": "failed",
                "error": str(e),
            }

    def _parse_evaluation_response(self, response: Dict[str, Any], session_id: str) -> Tuple[int, str]:
        """Parse and validate evaluation response"""
        try:
            score = response.get("score", 1)
            comment = response.get("comment", "Комментарий отсутствует")

            # Validate score
            if not isinstance(score, int) or score not in [1, 2, 3]:
                self.logger.log_error(
                    f"Invalid score in evaluation response: {score}",
                    extra_data={"session_id": session_id},
                )
                score = 1

            # Validate comment
            if not isinstance(comment, str):
                comment = str(comment) if comment else "Комментарий отсутствует"

            return score, comment

        except Exception as e:
            self.logger.log_error(
                f"Failed to parse evaluation response",
                exception=e,
                extra_data={"session_id": session_id, "response": response},
            )
            return 1, f"Ошибка парсинга оценки: {str(e)}"

    async def batch_evaluate_conversations(self, conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluate multiple conversations"""

        self.logger.log_info(f"Starting batch evaluation of {len(conversations)} conversations")

        evaluations = []

        for i, conversation in enumerate(conversations):
            try:
                evaluation = await self.evaluate_conversation(conversation)
                evaluations.append(evaluation)

                self.logger.log_info(
                    f"Completed evaluation {i + 1}/{len(conversations)}",
                    extra_data={
                        "session_id": evaluation.get("session_id"),
                        "score": evaluation.get("score"),
                    },
                )

            except Exception as e:
                self.logger.log_error(f"Failed to evaluate conversation {i + 1}", exception=e)

                # Add failed evaluation
                evaluations.append(
                    {
                        "session_id": conversation.get("session_id", f"unknown_{i}"),
                        "scenario": conversation.get("scenario", "unknown"),
                        "score": 1,
                        "comment": f"Ошибка оценки: {str(e)}",
                        "evaluation_status": "failed",
                        "error": str(e),
                    }
                )

        self.logger.log_info(f"Completed batch evaluation: {len(evaluations)} evaluations")
        return evaluations

    def get_evaluation_summary(self, evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for evaluations"""

        if not evaluations:
            return {
                "total_evaluations": 0,
                "average_score": 0,
                "score_distribution": {1: 0, 2: 0, 3: 0},
                "success_rate": 0,
            }

        scores = [eval_data.get("score", 1) for eval_data in evaluations]
        successful_evaluations = [e for e in evaluations if e.get("evaluation_status") == "success"]

        score_distribution = {1: 0, 2: 0, 3: 0}
        for score in scores:
            if score in score_distribution:
                score_distribution[score] += 1

        return {
            "total_evaluations": len(evaluations),
            "successful_evaluations": len(successful_evaluations),
            "average_score": sum(scores) / len(scores) if scores else 0,
            "score_distribution": score_distribution,
            "success_rate": (len(successful_evaluations) / len(evaluations) if evaluations else 0),
        }
