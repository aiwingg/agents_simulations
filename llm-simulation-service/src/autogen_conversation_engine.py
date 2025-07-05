"""
AutogenConversationEngine - Service Layer
Main engine implementing ConversationEngine contract using AutoGen Swarm pattern
Replaces the existing ConversationEngine with multi-agent orchestration capabilities
"""

import asyncio
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

# AutoGen imports
from autogen_agentchat.messages import HandoffMessage, TextMessage
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult

# Existing infrastructure
from src.openai_wrapper import OpenAIWrapper
from src.webhook_manager import WebhookManager
from src.logging_utils import get_logger
from src.conversation_context import ConversationContext
from src.conversation_error_handler import ConversationErrorHandler
from src.prompt_specification import PromptSpecificationManager, SystemPromptSpecification
from src.config import Config

# AutoGen infrastructure
from src.autogen_mas_factory import AutogenMASFactory
from src.conversation_adapter import ConversationAdapter
from src.autogen_tools import AutogenToolFactory
from src.autogen_model_client import AutogenModelClientFactory
from src.conversation_turn_manager import ConversationTurnManager
from src.conversation_context import ConversationContext
from src.conversation_loop_orchestrator import ConversationLoopOrchestrator

# Braintrust tracing import
from braintrust import traced


class AutogenConversationEngine:
    """
    Main engine implementing ConversationEngine contract using AutoGen Swarm pattern.
    Maintains exact same interface as existing ConversationEngine while leveraging
    AutoGen's multi-agent coordination, tool calling, and memory management.
    """

    def __init__(self, openai_wrapper: OpenAIWrapper, prompt_spec_name: str = "default_prompts"):
        """
        Initialize AutogenConversationEngine with OpenAIWrapper and prompt specification.

        Args:
            openai_wrapper: OpenAI API wrapper instance
            prompt_spec_name: Name of the prompt specification to use (defaults to "default_prompts")
        """
        self.openai = openai_wrapper
        self.webhook_manager = WebhookManager()
        self.logger = get_logger()
        self.error_handler = ConversationErrorHandler(self.logger)
        self.prompt_spec_name = prompt_spec_name
        self.turn_manager = ConversationTurnManager(self.logger)
        self.loop_orchestrator = ConversationLoopOrchestrator(self.turn_manager, self.logger)

        # Load prompt specification
        self.prompt_manager = PromptSpecificationManager()
        self.prompt_specification = self.prompt_manager.load_specification(prompt_spec_name)

        self.logger.log_info(
            f"AutogenConversationEngine initialized with prompt specification: {prompt_spec_name}",
            extra_data={
                "spec_name": prompt_spec_name,
                "spec_version": self.prompt_specification.version,
                "agents": list(self.prompt_specification.agents.keys()),
                "engine_type": "AutoGen",
            },
        )

    async def _enrich_variables_with_client_data(
        self, variables: Dict[str, Any], session_id: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """Delegate enrichment to the ScenarioVariableEnricher service."""
        from src.scenario_variable_enricher import enrich_scenario_variables

        return await enrich_scenario_variables(
            variables, session_id, self.webhook_manager, self.logger
        )

    @traced(name="autogen_run_conversation")
    async def run_conversation(
        self, scenario: Dict[str, Any], max_turns: Optional[int] = None, timeout_sec: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run a basic conversation simulation without tools.
        Delegates to run_conversation_with_tools() with empty tools for consistency.

        Args:
            scenario: Dictionary containing scenario name and variables
            max_turns: Maximum number of conversation turns (optional)
            timeout_sec: Timeout in seconds (optional)

        Returns:
            Dictionary matching existing ConversationEngine output contract.
            The `conversation_history` value is a list of
            `ConversationHistoryItem` dictionaries as described in
            `docs/contracts/dto/conversation_history_item.md`.
        """
        self.logger.log_info(
            "Running basic conversation via AutoGen Swarm",
            extra_data={
                "scenario": scenario.get("name", "unknown"),
                "max_turns": max_turns,
                "timeout_sec": timeout_sec,
                "tools_enabled": False,
            },
        )

        # Delegate to run_conversation_with_tools() with tools disabled
        result = await self.run_conversation_with_tools(scenario, max_turns, timeout_sec)

        # Ensure tools_used is False for basic conversation
        if "tools_used" in result:
            result["tools_used"] = False

        return result

    def _create_user_agent(self, model_client, formatted_spec: SystemPromptSpecification, session_id: str) -> AssistantAgent:
        """
        Create AssistantAgent for realistic user simulation using client agent from formatted spec.

        Args:
            model_client: OpenAI client for the user simulation agent
            formatted_spec: SystemPromptSpecification with formatted prompts
            session_id: Session ID for tool isolation

        Returns:
            Configured AssistantAgent for user simulation
        """
        # Get client agent from formatted specification
        client_agent_spec = formatted_spec.get_agent_prompt("client")
        if not client_agent_spec:
            raise ValueError("No 'client' agent found in formatted specification for user simulation")

        # Always add end_call tool to user agent for conversation termination
        from src.autogen_tools import AutogenToolFactory
        tool_factory = AutogenToolFactory(session_id)
        user_tools = tool_factory.get_tools_for_agent(["end_call"])

        user_agent = AssistantAgent(
            name="client", 
            model_client=model_client, 
            system_message=client_agent_spec.prompt,
            tools=user_tools,
            reflect_on_tool_use=False
        )

        return user_agent

    @traced(name="autogen_run_conversation_with_tools")
    async def run_conversation_with_tools(
        self, scenario: Dict[str, Any], max_turns: Optional[int] = None, timeout_sec: Optional[int] = None
    ) -> Dict[str, Any]:
        """Run conversation simulation with tools using AutoGen Swarm."""
        max_turns = max_turns or Config.MAX_TURNS
        timeout_sec = timeout_sec or Config.TIMEOUT_SEC

        name = scenario.get("name", "unknown")
        variables = scenario.get("variables", {})
        start = time.time()

        context = ConversationContext(
            session_id=await self.webhook_manager.initialize_session(),
            scenario_name=name,
            max_turns=max_turns,
            timeout_sec=timeout_sec,
            start_time=start,
        )

        variables, webhook_sid = await self._enrich_variables_with_client_data(variables, context.session_id)
        if webhook_sid:
            context.session_id = webhook_sid

        try:
            spec = self.prompt_specification.format_with_variables(variables)
            model = AutogenModelClientFactory.create_from_openai_wrapper(self.openai)
            user_agent = self._create_user_agent(model, spec, context.session_id)
            tool_names = {t for a in spec.agents.values() for t in a.tools}
            tools = AutogenToolFactory(context.session_id).get_tools_for_agent(list(tool_names))
            swarm = AutogenMASFactory(context.session_id).create_swarm_team(spec, tools, model)
            initial = variables.get("client_greeting") or variables.get("GREETING") or "Добрый день!"
            await self.loop_orchestrator.run_conversation_loop(swarm, user_agent, initial, context)
        except TypeError as exc:
            return self._format_non_text_error(exc, context, name, start)
        except Exception as err:
            return self.error_handler.handle_error_by_type(err, context, name, self.prompt_spec_name)

        duration = time.time() - context.start_time
        synthetic = TaskResult(messages=context.all_messages, stop_reason=f"completed_{context.turn_count}_turns")
        result = ConversationAdapter.autogen_to_contract_format(
            task_result=synthetic,
            session_id=context.session_id,
            scenario_name=name,
            duration=duration,
            start_time=context.start_time,
            prompt_spec=self.prompt_specification,
        )
        self.logger.log_conversation_complete(
            session_id=context.session_id,
            total_turns=result.get("total_turns", 0),
            status=result.get("status", "completed"),
        )
        return result

    def _format_non_text_error(
        self, exc: TypeError, context: ConversationContext, scenario_name: str, start: float
    ) -> Dict[str, Any]:
        task_result = getattr(exc, "task_result", None)
        history = ConversationAdapter.extract_conversation_history(
            context.all_messages, self.prompt_specification
        )
        end = time.time()
        return {
            "session_id": context.session_id,
            "scenario": scenario_name,
            "status": "failed",
            "error": str(exc),
            "error_type": "NonTextMessageError",
            "total_turns": context.turn_count,
            "duration_seconds": end - start,
            "tools_used": True,
            "conversation_history": history,
            "start_time": datetime.fromtimestamp(start).isoformat(),
            "end_time": datetime.fromtimestamp(end).isoformat(),
            "mas_stop_reason": getattr(task_result, "stop_reason", None),
            "mas_message_count": len(getattr(task_result, "messages", [])),
        }
