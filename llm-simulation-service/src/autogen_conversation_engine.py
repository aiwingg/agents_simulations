"""
AutogenConversationEngine - Service Layer
Main engine implementing ConversationEngine contract using AutoGen Swarm pattern
Replaces the existing ConversationEngine with multi-agent orchestration capabilities
"""

import asyncio
import time
from typing import Dict, Any, Optional, Tuple

# AutoGen imports
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult

# Existing infrastructure
from src.openai_wrapper import OpenAIWrapper
from src.webhook_manager import WebhookManager
from src.logging_utils import get_logger
from src.prompt_specification import PromptSpecificationManager, SystemPromptSpecification
from src.config import Config

# AutoGen infrastructure
from src.autogen_mas_factory import AutogenMASFactory
from src.conversation_adapter import ConversationAdapter
from src.autogen_tools import AutogenToolFactory
from src.autogen_model_client import AutogenModelClientFactory
from src.scenario_variable_enricher import ScenarioVariableEnricher
from src.conversation_orchestrator import ConversationOrchestrator
from src.conversation_error_handler import ConversationErrorHandler

# Braintrust tracing import
from braintrust import traced


class AutogenConversationEngine:
    """
    Main engine implementing ConversationEngine contract using AutoGen Swarm pattern.
    Maintains exact same interface as existing ConversationEngine while leveraging
    AutoGen's multi-agent coordination, tool calling, and memory management.
    """

    def __init__(
        self,
        openai_wrapper: OpenAIWrapper,
        prompt_spec_name: str = "default_prompts",
        variable_enricher: Optional[ScenarioVariableEnricher] = None,
        orchestrator: Optional[ConversationOrchestrator] = None,
        error_handler: Optional[ConversationErrorHandler] = None,
    ):
        """
        Initialize AutogenConversationEngine with OpenAIWrapper and prompt specification.

        Args:
            openai_wrapper: OpenAI API wrapper instance
            prompt_spec_name: Name of the prompt specification to use (defaults to "default_prompts")
        """
        self.openai = openai_wrapper
        self.webhook_manager = WebhookManager()
        self.logger = get_logger()
        self.prompt_spec_name = prompt_spec_name
        self.variable_enricher = variable_enricher or ScenarioVariableEnricher(self.webhook_manager)
        self.orchestrator = orchestrator or ConversationOrchestrator()
        self.error_handler = error_handler or ConversationErrorHandler()

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
        """Delegate enrichment to :class:`ScenarioVariableEnricher`."""
        return await self.variable_enricher.enrich_scenario_variables(variables, session_id)

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
            f"Running basic conversation via AutoGen Swarm",
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

    def _create_user_agent(self, model_client, formatted_spec: SystemPromptSpecification) -> AssistantAgent:
        """
        Create AssistantAgent for realistic user simulation using client agent from formatted spec.

        Args:
            model_client: OpenAI client for the user simulation agent
            formatted_spec: SystemPromptSpecification with formatted prompts

        Returns:
            Configured AssistantAgent for user simulation
        """
        # Get client agent from formatted specification
        client_agent_spec = formatted_spec.get_agent_prompt("client")
        if not client_agent_spec:
            raise ValueError("No 'client' agent found in formatted specification for user simulation")

        user_agent = AssistantAgent(
            name="user_agent", model_client=model_client, system_message=client_agent_spec.prompt
        )

        return user_agent

    @traced(name="autogen_run_conversation_with_tools")
    async def run_conversation_with_tools(
        self, scenario: Dict[str, Any], max_turns: Optional[int] = None, timeout_sec: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run conversation simulation with tool calling and multi-agent handoff support using AutoGen Swarm.
        Uses external UserProxy for user simulation and proper conversation loop.

        Args:
            scenario: Dictionary containing scenario name and variables
            max_turns: Maximum number of conversation turns (optional)
            timeout_sec: Timeout in seconds (optional)

        Returns:
            Dictionary matching existing ConversationEngine output contract.
            The `conversation_history` value is a list of
            `ConversationHistoryItem` dictionaries. See
            `docs/contracts/dto/conversation_history_item.md` for details.
        """
        max_turns = max_turns or Config.MAX_TURNS
        timeout_sec = timeout_sec or Config.TIMEOUT_SEC

        scenario_name = scenario.get("name", "unknown")
        variables = scenario.get("variables", {})
        seed = variables.get("SEED")

        # Use webhook session_id if available, otherwise initialize a new session
        webhook_session_id = None
        client_id = variables.get("client_id")
        if client_id:
            # Get session_id from webhook if client_id is provided
            client_data = await self.webhook_manager.get_client_data(client_id)
            webhook_session_id = client_data.get("session_id")

        if webhook_session_id:
            session_id = webhook_session_id
            self.logger.log_info(f"Using session_id from webhook: {session_id}")
        else:
            session_id = await self.webhook_manager.initialize_session()
            self.logger.log_info(f"Using generated session_id: {session_id}")

        # Enrich variables with client data and apply defaults
        variables, _ = await self._enrich_variables_with_client_data(variables, session_id)

        # Format prompt specification with variables
        try:
            formatted_spec = self.prompt_specification.format_with_variables(variables)
            self.logger.log_info(
                f"Successfully formatted prompt specification",
                extra_data={"session_id": session_id, "agents_formatted": list(formatted_spec.agents.keys())},
            )
        except Exception as e:
            self.logger.log_error(
                f"Failed to format prompt specification: {e}",
                extra_data={
                    "session_id": session_id,
                    "spec_name": self.prompt_spec_name,
                    "variables_count": len(variables),
                },
            )
            raise

        self.logger.log_info(
            f"Starting AutoGen conversation simulation with tools",
            extra_data={
                "session_id": session_id,
                "scenario": scenario_name,
                "max_turns": max_turns,
                "timeout_sec": timeout_sec,
                "has_client_id": "client_id" in scenario.get("variables", {}),
                "using_webhook_session": bool(webhook_session_id),
                "spec_name": self.prompt_spec_name,
            },
        )

        start_time = time.time()
        try:
            model_client = AutogenModelClientFactory.create_from_openai_wrapper(self.openai)
            user_agent = self._create_user_agent(model_client, formatted_spec)
            tool_factory = AutogenToolFactory(session_id)

            all_tool_names = set()
            for agent_spec in formatted_spec.agents.values():
                all_tool_names.update(agent_spec.tools)
            tools = tool_factory.get_tools_for_agent(list(all_tool_names))

            mas_factory = AutogenMASFactory(session_id)
            swarm = mas_factory.create_swarm_team(
                system_prompt_spec=formatted_spec, tools=tools, model_client=model_client
            )

            initial_task = variables.get("client_greeting") or variables.get("GREETING", "Добрый день!")

            messages = await self.orchestrator.run_conversation_loop(
                swarm,
                user_agent,
                initial_task,
                max_turns,
                timeout_sec,
            )

            duration = time.time() - start_time
            synthetic_result = TaskResult(messages=messages, stop_reason=f"completed_{len(messages)}")
            result = ConversationAdapter.autogen_to_contract_format(
                task_result=synthetic_result,
                session_id=session_id,
                scenario_name=scenario_name,
                duration=duration,
                start_time=start_time,
                prompt_spec=self.prompt_specification,
            )
            self.logger.log_conversation_complete(
                session_id=session_id,
                total_turns=result.get("total_turns", 0),
                status=result.get("status", "completed"),
            )
            return result

        except Exception as e:
            end_time = time.time()
            kwargs = dict(
                session_id=session_id,
                scenario=scenario_name,
                start_time=start_time,
                end_time=end_time,
                turn_count=0,
                timeout_sec=timeout_sec,
                error_context={"scenario": scenario_name},
            )
            self.logger.log_error("Conversation failed", exception=e, extra_data={"session_id": session_id})
            return self.error_handler.handle_error_by_type(e, **kwargs)
