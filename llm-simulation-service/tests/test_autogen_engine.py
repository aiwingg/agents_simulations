"""
Test suite for AutoGen conversation engine using pytest
Validates the new implementation against existing test scenarios
"""
import pytest
import json
import os
import sys
from datetime import datetime
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.autogen_conversation_engine import AutoGenConversationEngine
from src.conversation_engine import ConversationEngine
from src.openai_wrapper import OpenAIWrapper
from src.config import Config
from src.logging_utils import get_logger

logger = get_logger()

@pytest.fixture
def openai_wrapper():
    """Fixture to provide OpenAI wrapper instance"""
    if not Config.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY environment variable is required for tests")
    return OpenAIWrapper(api_key=Config.OPENAI_API_KEY)

@pytest.fixture
def autogen_engine(openai_wrapper):
    """Fixture to provide AutoGen conversation engine instance"""
    return AutoGenConversationEngine(openai_wrapper, "multiagent_prompts")

@pytest.fixture
def original_engine(openai_wrapper):
    """Fixture to provide original conversation engine instance"""
    return ConversationEngine(openai_wrapper, "multiagent_prompts")

@pytest.fixture
def test_scenario():
    """Fixture to load test scenario from file"""
    test_scenario_path = os.path.join(os.path.dirname(__file__), '..', 'test_scenario.json')
    with open(test_scenario_path, 'r', encoding='utf-8') as f:
        scenarios = json.load(f)
    return scenarios[0] if scenarios else None

@pytest.fixture
def simple_scenario():
    """Fixture for a simple test scenario"""
    return {
        "name": "Simple test scenario",
        "variables": {
            "CLIENT_NAME": "Test Client",
            "SEED": 123,
            "LOCATION": "Test Location",
            "current_date": "2025-06-24",
            "name": "Test Client",
            "locations": "Test Location",
            "delivery_days": "monday, wednesday, friday",
            "purchase_history": "No previous purchases"
        }
    }

class TestAutoGenEngineInitialization:
    """Test AutoGen engine initialization"""
    
    def test_basic_initialization(self, openai_wrapper):
        """Test basic engine initialization"""
        engine = AutoGenConversationEngine(openai_wrapper, "multiagent_prompts")
        
        assert engine is not None
        assert engine.prompt_specification is not None
        assert engine.prompt_specification.version is not None
        assert len(engine.prompt_specification.agents) > 0
        
        # Check that both agent and client specifications exist
        agents = list(engine.prompt_specification.agents.keys())
        assert 'agent' in agents or any('agent' in agent_name for agent_name in agents)
        assert 'client' in agents
    
    def test_prompt_specification_loading(self, autogen_engine):
        """Test that prompt specification is loaded correctly"""
        assert autogen_engine.prompt_specification is not None
        
        # Should have agent and client specifications
        agent_spec = autogen_engine.prompt_specification.get_agent_prompt('agent')
        client_spec = autogen_engine.prompt_specification.get_agent_prompt('client')
        
        # At least client should exist, agent might be named differently
        assert client_spec is not None
    
    def test_tool_factory_creation(self, autogen_engine):
        """Test that tool factory can be created"""
        from src.autogen_tools import AutogenToolFactory
        
        session_id = "test_session_123"
        tool_factory = AutogenToolFactory(session_id)
        
        assert tool_factory is not None
        assert tool_factory.session_id == session_id

class TestAutoGenEngineConversation:
    """Test AutoGen engine conversation functionality"""
    
    @pytest.mark.asyncio
    async def test_simple_conversation(self, autogen_engine, simple_scenario):
        """Test running a simple conversation"""
        result = await autogen_engine.run_conversation_with_tools(
            scenario=simple_scenario,
            max_turns=2,  # Keep it short for testing
            timeout_sec=30
        )
        
        # Check basic result structure
        assert result is not None
        assert 'status' in result
        assert 'session_id' in result
        assert 'total_turns' in result
        assert 'conversation_history' in result
        assert 'autogen_engine' in result
        assert result['autogen_engine'] is True
    
    @pytest.mark.asyncio
    async def test_conversation_with_test_scenario(self, autogen_engine, test_scenario):
        """Test conversation with the actual test scenario"""
        if test_scenario is None:
            pytest.skip("No test scenario file found")
        
        result = await autogen_engine.run_conversation_with_tools(
            scenario=test_scenario,
            max_turns=3,  # Limit turns for testing
            timeout_sec=60
        )
        
        assert result is not None
        assert result['status'] in ['completed', 'failed']
        assert 'session_id' in result
        assert 'conversation_history' in result
        assert result.get('autogen_engine') is True
        
        # If completed, should have some conversation history
        if result['status'] == 'completed':
            assert len(result['conversation_history']) > 0
    
    @pytest.mark.asyncio
    async def test_conversation_termination(self, autogen_engine, simple_scenario):
        """Test that conversation terminates properly"""
        result = await autogen_engine.run_conversation_with_tools(
            scenario=simple_scenario,
            max_turns=1,  # Force early termination
            timeout_sec=30
        )
        
        assert result is not None
        assert result['total_turns'] <= 1
        assert 'conversation_history' in result

class TestAutoGenEngineCompatibility:
    """Test compatibility with original engine interface"""
    
    def test_interface_compatibility(self, autogen_engine, original_engine):
        """Test that AutoGen engine has same interface as original"""
        # Check that both engines have the same methods
        autogen_methods = [method for method in dir(autogen_engine) if not method.startswith('_')]
        original_methods = [method for method in dir(original_engine) if not method.startswith('_')]
        
        # Key methods should exist in both
        key_methods = ['run_conversation', 'run_conversation_with_tools']
        for method in key_methods:
            assert hasattr(autogen_engine, method), f"AutoGen engine missing {method}"
            assert hasattr(original_engine, method), f"Original engine missing {method}"
    
    @pytest.mark.asyncio
    async def test_result_structure_compatibility(self, autogen_engine, simple_scenario):
        """Test that result structure matches expected format"""
        result = await autogen_engine.run_conversation_with_tools(
            scenario=simple_scenario,
            max_turns=2,
            timeout_sec=30
        )
        
        # Check all required fields are present
        required_fields = [
            'session_id', 'scenario', 'status', 'total_turns',
            'duration_seconds', 'conversation_history', 'start_time',
            'end_time', 'tools_used'
        ]
        
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        # Check conversation history structure
        if result['conversation_history']:
            turn = result['conversation_history'][0]
            expected_turn_fields = ['turn', 'speaker', 'content', 'timestamp']
            for field in expected_turn_fields:
                assert field in turn, f"Missing turn field: {field}"

class TestAutoGenEngineErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_invalid_scenario_handling(self, autogen_engine):
        """Test handling of invalid scenarios"""
        invalid_scenario = {
            "name": "Invalid scenario",
            "variables": {}  # Missing required variables
        }
        
        result = await autogen_engine.run_conversation_with_tools(
            scenario=invalid_scenario,
            max_turns=1,
            timeout_sec=10
        )
        
        # Should handle gracefully, either complete or fail properly
        assert result is not None
        assert 'status' in result
        assert 'error_type' in result or result['status'] == 'completed'
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, autogen_engine, simple_scenario):
        """Test timeout handling"""
        result = await autogen_engine.run_conversation_with_tools(
            scenario=simple_scenario,
            max_turns=10,
            timeout_sec=1  # Very short timeout
        )
        
        assert result is not None
        assert 'status' in result
        # Should either complete quickly or timeout gracefully
    
    @pytest.mark.asyncio
    async def test_max_turns_limit(self, autogen_engine, simple_scenario):
        """Test max turns limit enforcement"""
        max_turns = 2
        result = await autogen_engine.run_conversation_with_tools(
            scenario=simple_scenario,
            max_turns=max_turns,
            timeout_sec=60
        )
        
        assert result is not None
        assert result['total_turns'] <= max_turns

class TestAutoGenEngineDebugFeatures:
    """Test debug and logging features"""
    
    @pytest.mark.asyncio
    async def test_debug_information_capture(self, autogen_engine, simple_scenario):
        """Test that debug information is captured properly"""
        result = await autogen_engine.run_conversation_with_tools(
            scenario=simple_scenario,
            max_turns=2,
            timeout_sec=30
        )
        
        assert result is not None
        
        # Check for debug info in conversation history
        if result['conversation_history']:
            for turn in result['conversation_history']:
                if turn['speaker'] == 'agent':
                    # Agent turns should have swarm_debug info
                    assert 'swarm_debug' in turn
                    debug_info = turn['swarm_debug']
                    assert 'internal_messages' in debug_info
                    assert 'handoffs' in debug_info
                    assert 'tool_executions' in debug_info
    
    def test_logging_integration(self, autogen_engine):
        """Test that logging is properly integrated"""
        # Check that logger is available
        assert autogen_engine.logger is not None
        
        # Logger should have required methods
        assert hasattr(autogen_engine.logger, 'log_info')
        assert hasattr(autogen_engine.logger, 'log_error')
        assert hasattr(autogen_engine.logger, 'log_conversation_turn')

class TestAutoGenEngineTools:
    """Test tool integration"""
    
    def test_tool_name_extraction(self, autogen_engine):
        """Test tool name extraction from agent specifications"""
        # Get an agent specification
        agent_specs = autogen_engine.prompt_specification.agents
        
        if 'agent' in agent_specs:
            agent_spec = agent_specs['agent']
        else:
            # Find first non-client agent
            agent_spec = None
            for name, spec in agent_specs.items():
                if name != 'client':
                    agent_spec = spec
                    break
        
        if agent_spec:
            tool_names = autogen_engine._extract_tool_names_from_agent_spec(agent_spec)
            # Should return a list (might be empty)
            assert isinstance(tool_names, list)
    
    def test_handoff_determination(self, autogen_engine):
        """Test handoff determination from agent specifications"""
        agent_specs = autogen_engine.prompt_specification.agents
        
        if 'agent' in agent_specs:
            agent_spec = agent_specs['agent']
        else:
            # Find first non-client agent
            agent_spec = None
            for name, spec in agent_specs.items():
                if name != 'client':
                    agent_spec = spec
                    break
        
        if agent_spec:
            handoffs = autogen_engine._determine_handoffs_for_agent(agent_spec)
            # Should return a list including 'user'
            assert isinstance(handoffs, list)
            assert 'user' in handoffs

# Integration test marker
@pytest.mark.integration
class TestAutoGenEngineIntegration:
    """Integration tests (may be slower)"""
    
    @pytest.mark.asyncio
    async def test_full_scenario_integration(self, autogen_engine, test_scenario):
        """Run a full scenario integration test"""
        if test_scenario is None:
            pytest.skip("No test scenario file found")
        
        # Run with realistic parameters
        result = await autogen_engine.run_conversation_with_tools(
            scenario=test_scenario,
            max_turns=5,
            timeout_sec=120
        )
        
        assert result is not None
        assert 'status' in result
        assert 'conversation_history' in result
        
        # Log results for manual inspection
        logger.log_info(f"Integration test result", extra_data={
            'status': result['status'],
            'total_turns': result['total_turns'],
            'duration': result['duration_seconds'],
            'conversation_length': len(result.get('conversation_history', []))
        })