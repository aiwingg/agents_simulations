"""
Tests for AutogenSwarmEngine
"""
import pytest
import jinja2
from unittest.mock import Mock, patch

from src.autogen_swarm_engine import AutogenSwarmEngine, AutogenSwarmFactory
from src.webhook_manager import WebhookManager
from src.config import Config


class TestAutogenSwarmEngine:
    """Test suite for AutogenSwarmEngine"""

    def test_swarm_engine_initialization(self, skip_if_no_api_key):
        """Test that AutogenSwarmEngine initializes correctly"""
        engine = AutogenSwarmEngine(skip_if_no_api_key, "file_based_prompts")
        
        assert engine.openai_api_key == skip_if_no_api_key
        assert engine.model_client is not None
        assert engine.prompt_specification is not None
        assert engine.jinja_env is not None
        assert len(engine.prompt_specification.agents) > 0

    def test_factory_creates_isolated_instances(self, skip_if_no_api_key):
        """Test that factory creates isolated instances"""
        engine1 = AutogenSwarmFactory.create_swarm_engine(skip_if_no_api_key, "file_based_prompts")
        engine2 = AutogenSwarmFactory.create_swarm_engine(skip_if_no_api_key, "file_based_prompts")
        
        assert engine1 is not engine2
        assert id(engine1.agents) != id(engine2.agents)  # Should be separate dict instances

    def test_jinja_prompt_formatting_success(self, skip_if_no_api_key, sample_variables):
        """Test successful prompt formatting with Jinja2"""
        engine = AutogenSwarmEngine(skip_if_no_api_key, "file_based_prompts")
        
        template = "Hello {{name}}, delivery to {{locations}} on {{current_date}}"
        result = engine._format_prompt(template, sample_variables, "test_session")
        
        expected = "Hello Test Company LLC, delivery to Moscow, Saint Petersburg on 2024-12-24"
        assert result == expected

    def test_jinja_prompt_formatting_with_session_id(self, skip_if_no_api_key, sample_variables):
        """Test that session_id is added to variables"""
        engine = AutogenSwarmEngine(skip_if_no_api_key, "file_based_prompts")
        
        template = "Session: {{session_id}}, Client: {{name}}"
        result = engine._format_prompt(template, sample_variables, "test_session_123")
        
        assert "Session: test_session_123" in result
        assert "Client: Test Company LLC" in result

    def test_jinja_prompt_formatting_missing_variable(self, skip_if_no_api_key, incomplete_variables):
        """Test that missing variables raise Jinja2 UndefinedError"""
        engine = AutogenSwarmEngine(skip_if_no_api_key, "file_based_prompts")
        
        template = "Hello {{name}}, delivery to {{missing_location}}"
        
        with pytest.raises(jinja2.UndefinedError):
            engine._format_prompt(template, incomplete_variables, "test_session")

    def test_agent_creation_from_config_success(self, skip_if_no_api_key, sample_variables):
        """Test successful agent creation from configuration"""
        with patch('src.autogen_swarm_engine.AssistantAgent') as mock_agent:
            mock_agent.return_value = Mock()
            
            engine = AutogenSwarmEngine(skip_if_no_api_key, "file_based_prompts")
            agents = engine._create_agents_from_config(sample_variables, "test_session")
            
            # Should create agents excluding client and evaluator
            expected_agents = set(engine.prompt_specification.agents.keys()) - {'client', 'evaluator'}
            assert set(agents.keys()) == expected_agents
            
            # Verify AssistantAgent was called for each agent
            assert mock_agent.call_count == len(expected_agents)

    def test_agent_creation_missing_variables(self, skip_if_no_api_key, incomplete_variables):
        """Test that agent creation fails with missing variables"""
        engine = AutogenSwarmEngine(skip_if_no_api_key, "file_based_prompts")
        
        with pytest.raises(ValueError, match="Missing variable"):
            engine._create_agents_from_config(incomplete_variables, "test_session")

    def test_swarm_creation(self, skip_if_no_api_key, sample_variables):
        """Test swarm creation from agents"""
        with patch('src.autogen_swarm_engine.Swarm') as mock_swarm:
            mock_swarm.return_value = Mock()
            
            engine = AutogenSwarmEngine(skip_if_no_api_key, "file_based_prompts")
            
            # Mock agents
            mock_agents = {
                'agent1': Mock(),
                'agent2': Mock()
            }
            
            swarm = engine._create_swarm(mock_agents)
            
            # Verify Swarm was created with correct parameters
            mock_swarm.assert_called_once()
            call_args = mock_swarm.call_args
            assert 'participants' in call_args.kwargs
            assert 'termination_condition' in call_args.kwargs

    def test_message_history_conversion(self, skip_if_no_api_key):
        """Test conversion of Autogen messages to conversation history"""
        engine = AutogenSwarmEngine(skip_if_no_api_key, "file_based_prompts")
        
        # Mock Autogen messages
        mock_messages = [
            Mock(source='agent1', content='Hello', tool_calls=None),
            Mock(source='client', content='Hi there', tool_calls=[])
        ]
        
        history = engine._convert_autogen_messages_to_history(mock_messages)
        
        assert len(history) == 2
        assert history[0]['speaker'] == 'agent1'
        assert history[0]['content'] == 'Hello'
        assert history[1]['speaker'] == 'client'
        assert history[1]['content'] == 'Hi there'

    @pytest.mark.asyncio
    async def test_variable_enrichment_no_client_id(self, skip_if_no_api_key, sample_variables):
        """Test variable enrichment when no client_id is provided"""
        engine = AutogenSwarmEngine(skip_if_no_api_key, "file_based_prompts")
        
        variables_copy = sample_variables.copy()
        enriched_vars, session_id = await engine._enrich_variables_with_client_data(variables_copy)
        
        # Should return original variables unchanged
        assert enriched_vars == sample_variables
        assert session_id is None

    @pytest.mark.asyncio 
    async def test_variable_enrichment_with_client_id(self, skip_if_no_api_key):
        """Test variable enrichment with client_id"""
        with patch.object(WebhookManager, 'get_client_data') as mock_webhook:
            mock_webhook.return_value = {
                'variables': {'NAME': 'Webhook Company', 'LOCATIONS': 'Moscow'},
                'session_id': 'webhook_session_123'
            }
            
            engine = AutogenSwarmEngine(skip_if_no_api_key, "file_based_prompts")
            
            variables = {'client_id': '123456', 'name': 'Original Company'}
            enriched_vars, session_id = await engine._enrich_variables_with_client_data(variables)
            
            # Should be enriched with webhook data
            assert enriched_vars['NAME'] == 'Webhook Company'
            assert enriched_vars['LOCATIONS'] == 'Moscow'
            assert session_id == 'webhook_session_123'
            assert mock_webhook.called


class TestAutogenSwarmFactory:
    """Test suite for AutogenSwarmFactory"""

    def test_factory_creates_engine(self, skip_if_no_api_key):
        """Test that factory creates AutogenSwarmEngine instances"""
        engine = AutogenSwarmFactory.create_swarm_engine(skip_if_no_api_key, "file_based_prompts")
        
        assert isinstance(engine, AutogenSwarmEngine)
        assert engine.openai_api_key == skip_if_no_api_key

    def test_factory_creates_isolated_instances(self, skip_if_no_api_key):
        """Test that each factory call creates a new isolated instance"""
        engine1 = AutogenSwarmFactory.create_swarm_engine(skip_if_no_api_key, "file_based_prompts")
        engine2 = AutogenSwarmFactory.create_swarm_engine(skip_if_no_api_key, "file_based_prompts")
        
        assert engine1 is not engine2
        assert id(engine1) != id(engine2)