"""Tests for ConversationOrchestrator."""

import pytest
from unittest.mock import AsyncMock, Mock
from autogen_agentchat.messages import TextMessage

from src.conversation_orchestrator import ConversationOrchestrator


@pytest.mark.asyncio
async def test_conversation_loop_terminates_on_stop_reason():
    orchestrator = ConversationOrchestrator()
    swarm = Mock()
    swarm.run = AsyncMock(return_value=Mock(messages=[TextMessage(content="hi", source="agent")], stop_reason="completed"))
    user_agent = Mock()
    user_agent.name = "user"
    user_agent.aask = AsyncMock(return_value=TextMessage(content="ok", source="client"))

    messages = await orchestrator.run_conversation_loop(swarm, user_agent, "hi", max_turns=5, timeout_sec=5)
    assert len(messages) == 1
