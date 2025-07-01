"""
AutogenConversationEngine - Service Layer
Main engine implementing ConversationEngine contract using AutoGen Swarm pattern
Replaces the existing ConversationEngine with multi-agent orchestration capabilities
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# AutoGen imports
from autogen_agentchat.teams import Swarm
from autogen_agentchat.messages import HandoffMessage, TextMessage
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
        self.prompt_spec_name = prompt_spec_name

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
        all_messages = []  # Track all conversation messages
        turn_count = 0

        try:
            # Create AutoGen model client from OpenAIWrapper
            model_client = AutogenModelClientFactory.create_from_openai_wrapper(self.openai)

            # Create user simulation agent using formatted spec
            user_agent = self._create_user_agent(model_client, formatted_spec)

            # Create session-isolated tool factory
            tool_factory = AutogenToolFactory(session_id)

            # Collect all unique tool names from all agents in formatted spec
            all_tool_names = set()
            for agent_spec in formatted_spec.agents.values():
                all_tool_names.update(agent_spec.tools)

            # Create tools for all agents (session-isolated)
            tools = tool_factory.get_tools_for_agent(list(all_tool_names))

            # Create AutoGen Swarm team using formatted spec (without user as participant)
            mas_factory = AutogenMASFactory(session_id)
            swarm = mas_factory.create_swarm_team(
                system_prompt_spec=formatted_spec, tools=tools, model_client=model_client
            )

            # Prepare initial task based on system prompt spec
            initial_task = "Добрый день!"  # Default greeting

            # If there's a specific client prompt or greeting in variables, use that
            if "client_greeting" in variables:
                initial_task = variables["client_greeting"]
            elif "GREETING" in variables:
                initial_task = variables["GREETING"]

            self.logger.log_info(
                f"Starting AutoGen conversation loop",
                extra_data={
                    "session_id": session_id,
                    "initial_task": initial_task,
                    "agents_count": len(self.prompt_specification.agents),
                    "tools_count": len(tools),
                    "max_turns": max_turns,
                },
            )

            # Conversation loop with timeout for entire conversation
            try:
                # Start timeout for entire conversation
                conversation_start = time.time()
                current_user_message = initial_task
                last_active_agent = "agent"  # Default first agent

                while turn_count < max_turns:
                    # Check timeout for entire conversation
                    if time.time() - conversation_start > timeout_sec:
                        raise asyncio.TimeoutError(f"Conversation timeout after {timeout_sec} seconds")

                    turn_count += 1

                    self.logger.log_info(
                        f"Turn {turn_count}: User -> {last_active_agent}",
                        extra_data={
                            "session_id": session_id,
                            "user_message": current_user_message[:100],
                            "target_agent": last_active_agent,
                        },
                    )

                    # Run swarm with current user message
                    task_result = await swarm.run(
                        task=HandoffMessage(source="client", target=last_active_agent, content=current_user_message)
                    )

                    # Add all swarm messages to conversation history
                    all_messages.extend(task_result.messages)

                    # Get last message from MAS (should be TextMessage)
                    last_message = task_result.messages[-1]
                    if not isinstance(last_message, TextMessage):
                        self.logger.log_error(
                            f"MAS terminated with non-text message - cannot pass to user simulation. "
                            f"Expected TextMessage, got {type(last_message).__name__}",
                            extra_data={
                                "session_id": session_id,
                                "turn_count": turn_count,
                                "message_type": type(last_message).__name__,
                                "stop_reason": task_result.stop_reason,
                                "total_mas_messages": len(task_result.messages),
                                "scenario": scenario_name,
                            },
                        )
                        # Stop conversation gracefully - create error result
                        end_time = time.time()
                        duration = end_time - start_time

                        return {
                            "session_id": session_id,
                            "scenario": scenario_name,
                            "status": "failed",
                            "error": f"MAS terminated with non-text message ({type(last_message).__name__})",
                            "error_type": "NonTextMessageError",
                            "total_turns": turn_count,
                            "duration_seconds": duration,
                            "tools_used": True,
                            "conversation_history": ConversationAdapter.extract_conversation_history(
                                all_messages, self.prompt_specification
                            ),
                            "start_time": datetime.fromtimestamp(start_time).isoformat(),
                            "end_time": datetime.fromtimestamp(end_time).isoformat(),
                            "mas_stop_reason": task_result.stop_reason,
                            "mas_message_count": len(task_result.messages),
                        }

                    # Update last active agent for next iteration
                    last_active_agent = last_message.source

                    self.logger.log_info(
                        f"Turn {turn_count}: {last_active_agent} -> User",
                        extra_data={
                            "session_id": session_id,
                            "agent_response": last_message.content[:100],
                            "stop_reason": task_result.stop_reason,
                        },
                    )

                    # Check if conversation naturally ended (only on actual termination conditions)
                    # TODO: this is a hack to check if the conversation ended naturally, think how to refactor this to normal behavior.
                    if task_result.stop_reason and any(
                        term in task_result.stop_reason.lower()
                        for term in ["terminate", "end", "finished", "completed"]
                    ):
                        self.logger.log_info(f"Conversation ended naturally: {task_result.stop_reason}")
                        break

                    # If we've reached max turns, break
                    if turn_count >= max_turns:
                        self.logger.log_info(f"Reached max_turns ({max_turns})")
                        break

                    # Get user response via user simulation agent
                    user_response = await user_agent.on_messages([last_message], None)
                    current_user_message = user_response.chat_message.content

                    # Add user response to conversation history as a client message
                    user_message = TextMessage(content=current_user_message, source="client")
                    all_messages.append(user_message)

                    self.logger.log_info(
                        f"User simulation agent generated response",
                        extra_data={"session_id": session_id, "user_response": current_user_message[:100]},
                    )

                end_time = time.time()
                duration = end_time - start_time

                self.logger.log_info(
                    f"AutoGen conversation loop completed",
                    extra_data={
                        "session_id": session_id,
                        "duration": duration,
                        "total_turns": turn_count,
                        "messages_count": len(all_messages),
                    },
                )

                # Create a synthetic TaskResult for ConversationAdapter
                synthetic_result = TaskResult(messages=all_messages, stop_reason=f"completed_{turn_count}_turns")

                # Convert to contract format using ConversationAdapter
                result = ConversationAdapter.autogen_to_contract_format(
                    task_result=synthetic_result,
                    session_id=session_id,
                    scenario_name=scenario_name,
                    duration=duration,
                    start_time=start_time,
                    prompt_spec=self.prompt_specification,
                )

                # Log conversation completion
                self.logger.log_conversation_complete(
                    session_id=session_id,
                    total_turns=result.get("total_turns", 0),
                    status=result.get("status", "completed"),
                )

                return result

            except asyncio.TimeoutError:
                end_time = time.time()
                duration = end_time - start_time

                self.logger.log_error(
                    f"AutoGen conversation timeout after {timeout_sec} seconds",
                    extra_data={
                        "session_id": session_id,
                        "timeout_sec": timeout_sec,
                        "actual_duration": duration,
                        "scenario_name": scenario_name,
                        "completed_turns": turn_count,
                    },
                )

                history = ConversationAdapter.extract_conversation_history(all_messages, self.prompt_specification)

                # Return timeout result in contract format
                return {
                    "session_id": session_id,
                    "scenario": scenario_name,
                    "status": "timeout",
                    "error": f"Conversation timeout after {timeout_sec} seconds",
                    "error_type": "TimeoutError",
                    "total_turns": turn_count,
                    "duration_seconds": duration,
                    "conversation_history": history,
                    "start_time": datetime.fromtimestamp(start_time).isoformat(),
                    "end_time": datetime.fromtimestamp(end_time).isoformat(),
                    "tools_used": True,
                }

        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time

            # Enhanced error logging with more context
            error_context = {
                "session_id": session_id,
                "scenario_name": scenario_name,
                "duration_so_far": duration,
                "max_turns": max_turns,
                "timeout_sec": timeout_sec,
                "completed_turns": turn_count,
                "error_type": type(e).__name__,
                "spec_name": self.prompt_spec_name,
            }

            # Check if this is a geographic restriction or persistent OpenAI API failure
            error_message = str(e).lower()
            is_api_blocked = (
                "geographic restriction" in error_message
                or "unsupported_country_region_territory" in error_message
                or "blocked due to geographic" in error_message
            )

            if is_api_blocked:
                self.logger.log_error(
                    f"OpenAI API blocked in AutoGen engine - attempting graceful degradation: {str(e)}",
                    exception=e,
                    extra_data=error_context,
                )

                # Return a graceful failure with some useful information
                return {
                    "session_id": session_id,
                    "scenario": scenario_name,
                    "status": "failed_api_blocked",
                    "error": "OpenAI API blocked due to geographic restrictions",
                    "error_type": "APIBlockedError",
                    "total_turns": turn_count,
                    "duration_seconds": duration,
                    "tools_used": True,
                    "conversation_history": [],
                    "start_time": datetime.fromtimestamp(start_time).isoformat(),
                    "end_time": datetime.fromtimestamp(end_time).isoformat(),
                    "graceful_degradation": True,
                    "partial_completion": turn_count > 0,
                }
            else:
                self.logger.log_error(
                    f"AutoGen conversation with tools failed: {str(e)}", exception=e, extra_data=error_context
                )

            return {
                "session_id": session_id,
                "scenario": scenario_name,
                "status": "failed",
                "error": str(e),
                "error_type": type(e).__name__,
                "total_turns": turn_count,
                "duration_seconds": duration,
                "tools_used": True,
                "conversation_history": [],
                "start_time": datetime.fromtimestamp(start_time).isoformat(),
                "end_time": datetime.fromtimestamp(end_time).isoformat(),
                "error_context": error_context,
            }
