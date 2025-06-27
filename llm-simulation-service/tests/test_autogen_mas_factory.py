"""
Tests for AutogenMASFactory
"""
import pytest
from unittest.mock import Mock, patch
from src.autogen_mas_factory import AutogenMASFactory
from src.prompt_specification import SystemPromptSpecification, AgentPromptSpecification
from src.openai_wrapper import OpenAIWrapper


class TestAutogenMASFactory:
    """Test AutogenMASFactory functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.session_id = "test_session_123"
        self.factory = AutogenMASFactory(self.session_id)
        
    def test_initialization(self):
        """Test AutogenMASFactory initialization"""
        assert self.factory.session_id == self.session_id
        assert self.factory.logger is not None
        
    def test_setup_agent_handoffs(self):
        """Test handoff configuration setup"""
        # Create test agent configurations
        agents_config = {
            'sales_agent': AgentPromptSpecification(
                name='sales_agent',
                prompt='You are a sales agent',
                tools=['rag_find_products'],
                handoffs={'support_agent': 'For technical support'}
            ),
            'support_agent': AgentPromptSpecification(
                name='support_agent', 
                prompt='You are a support agent',
                tools=['get_cart'],
                handoffs={'sales_agent': 'For sales questions'}
            )
        }
        
        user_handoff_target = "client"
        
        # Test handoff setup
        handoff_config = self.factory._setup_agent_handoffs(agents_config, user_handoff_target)
        
        # Verify handoff configuration
        assert 'sales_agent' in handoff_config
        assert 'support_agent' in handoff_config
        
        # Each agent should have handoffs to other agents only (no client - user is external)
        assert 'support_agent' in handoff_config['sales_agent']
        assert 'client' not in handoff_config['sales_agent']  # User is external now
        assert 'sales_agent' in handoff_config['support_agent'] 
        assert 'client' not in handoff_config['support_agent']  # User is external now
        
    def test_create_termination_conditions(self):
        """Test termination conditions creation"""
        user_handoff_target = "client"
        
        termination = self.factory._create_termination_conditions(user_handoff_target)
        
        # Should create combined termination condition
        assert termination is not None
        
    @patch('src.autogen_mas_factory.OpenAIChatCompletionClient')
    def test_create_autogen_client(self, mock_client_class):
        """Test OpenAI client creation from wrapper"""
        # Mock OpenAIWrapper
        mock_wrapper = Mock()
        mock_wrapper.client = Mock()
        mock_wrapper.client.api_key = "test_api_key"
        mock_wrapper.model = "gpt-4o-mini"
        
        # Mock client instance
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance
        
        # Test client creation
        client = self.factory._create_autogen_client(mock_wrapper)
        
        # Verify client was created with correct parameters
        mock_client_class.assert_called_once_with(
            model="gpt-4o-mini",
            api_key="test_api_key"
        )
        assert client == mock_client_instance
        
    @patch('src.autogen_mas_factory.AssistantAgent')
    @patch('src.autogen_mas_factory.OpenAIChatCompletionClient')
    def test_create_swarm_agents(self, mock_client_class, mock_agent_class):
        """Test swarm agents creation"""
        # Create test configuration
        agents_config = {
            'test_agent': AgentPromptSpecification(
                name='test_agent',
                prompt='You are a test agent',
                tools=['rag_find_products'],
                description='Test agent description'
            )
        }
        
        # Mock tools
        mock_tool = Mock()
        mock_tool.name = 'rag_find_products'
        tools = [mock_tool]
        
        # Mock model client
        mock_model_client = Mock()
        
        # Mock agent instance
        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance
        
        # Test agent creation
        agents = self.factory._create_swarm_agents(
            agents_config, 
            tools, 
            mock_model_client, 
            "client"
        )
        
        # Verify agent was created
        assert len(agents) == 1
        assert agents[0] == mock_agent_instance
        
        # Verify AssistantAgent was called with correct parameters
        mock_agent_class.assert_called_once_with(
            name='test_agent',
            model_client=mock_model_client,
            handoffs=[],  # No handoffs since no other agents and user is external
            tools=[mock_tool],
            system_message='You are a test agent',
            description='Test agent description'
        )
        
    @patch('src.autogen_mas_factory.Swarm')
    @patch('src.autogen_mas_factory.AutogenToolFactory')
    def test_create_swarm_team_with_openai_wrapper(self, mock_tool_factory_class, mock_swarm_class):
        """Test full swarm team creation with OpenAIWrapper"""
        # Create test specification
        system_prompt_spec = SystemPromptSpecification(
            name="Test Spec",
            version="1.0",
            description="Test specification",
            agents={
                'test_agent': AgentPromptSpecification(
                    name='test_agent',
                    prompt='You are a test agent',
                    tools=['rag_find_products']
                )
            }
        )
        
        # Mock OpenAIWrapper
        mock_wrapper = Mock()
        mock_wrapper.client = Mock()
        mock_wrapper.client.api_key = "test_api_key"
        mock_wrapper.model = "gpt-4o-mini"
        
        # Mock tool factory
        mock_tool_factory = Mock()
        mock_tool = Mock()
        mock_tool.name = 'rag_find_products'
        mock_tool_factory.get_tools_for_agent.return_value = [mock_tool]
        mock_tool_factory_class.return_value = mock_tool_factory
        
        # Mock swarm
        mock_swarm = Mock()
        mock_agent = Mock()
        mock_swarm.participants = [mock_agent]
        mock_swarm_class.return_value = mock_swarm
        
        # Test swarm creation
        with patch.object(self.factory, '_create_autogen_client') as mock_create_client, \
             patch.object(self.factory, 'create_swarm_team') as mock_create_swarm:
            mock_client = Mock()
            mock_create_client.return_value = mock_client
            mock_create_swarm.return_value = mock_swarm
            
            result = self.factory.create_swarm_team_with_openai_wrapper(
                system_prompt_spec,
                mock_wrapper,
                "client"
            )
        
        # Verify tool factory was created with correct session_id
        mock_tool_factory_class.assert_called_once_with(self.session_id)
        
        # Verify tools were requested
        mock_tool_factory.get_tools_for_agent.assert_called_once_with(['rag_find_products'])
        
        # Verify create_swarm_team was called with correct parameters
        mock_create_swarm.assert_called_once_with(
            system_prompt_spec,
            [mock_tool],
            mock_client,
            "client"
        )
        
        # Verify result
        assert result == mock_swarm