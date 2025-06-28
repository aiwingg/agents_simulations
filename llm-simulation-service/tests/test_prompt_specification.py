"""
Tests for prompt specification formatting functionality
"""
import pytest
from src.prompt_specification import AgentPromptSpecification, SystemPromptSpecification


class TestAgentPromptSpecificationFormatting:
    """Test AgentPromptSpecification formatting functionality"""
    
    def test_format_with_variables_basic(self):
        """Test basic variable substitution in agent prompt"""
        agent_spec = AgentPromptSpecification(
            name="test_agent",
            prompt="Hello {{name}}, you are located in {{location}}",
            tools=["tool1", "tool2"]
        )
        
        variables = {
            "name": "John",
            "location": "New York"
        }
        
        formatted_spec = agent_spec.format_with_variables(variables)
        
        assert formatted_spec.name == "test_agent"
        assert formatted_spec.prompt == "Hello John, you are located in New York"
        assert formatted_spec.tools == ["tool1", "tool2"]
        assert formatted_spec.description == agent_spec.description
        assert formatted_spec.handoffs == agent_spec.handoffs
    
    def test_format_with_variables_immutable(self):
        """Test that formatting creates a new instance without modifying original"""
        original_prompt = "Hello {{name}}"
        agent_spec = AgentPromptSpecification(
            name="test_agent",
            prompt=original_prompt,
            tools=["tool1"]
        )
        
        variables = {"name": "John"}
        formatted_spec = agent_spec.format_with_variables(variables)
        
        # Original should be unchanged
        assert agent_spec.prompt == original_prompt
        # New instance should be formatted
        assert formatted_spec.prompt == "Hello John"
        # Should be different instances
        assert agent_spec is not formatted_spec
    
    def test_format_with_variables_missing_variable(self):
        """Test that missing variables raise ValueError"""
        agent_spec = AgentPromptSpecification(
            name="test_agent",
            prompt="Hello {{name}}, you live in {{location}}",
            tools=[]
        )
        
        variables = {"name": "John"}  # Missing 'location'
        
        with pytest.raises(ValueError) as exc_info:
            agent_spec.format_with_variables(variables)
        
        assert "Missing variable in prompt template for agent 'test_agent'" in str(exc_info.value)
    
    def test_format_with_variables_no_template(self):
        """Test formatting prompt without any variables"""
        agent_spec = AgentPromptSpecification(
            name="test_agent",
            prompt="This is a static prompt with no variables",
            tools=[]
        )
        
        variables = {"unused": "value"}
        formatted_spec = agent_spec.format_with_variables(variables)
        
        assert formatted_spec.prompt == "This is a static prompt with no variables"
    
    def test_format_with_variables_complex_template(self):
        """Test formatting with complex Jinja2 template features"""
        agent_spec = AgentPromptSpecification(
            name="test_agent",
            prompt="Hello {{name}}{% if location %}, you are in {{location}}{% endif %}. Your items: {% for item in items %}{{item}}{% if not loop.last %}, {% endif %}{% endfor %}",
            tools=[]
        )
        
        variables = {
            "name": "John",
            "location": "NYC",
            "items": ["apple", "banana", "cherry"]
        }
        
        formatted_spec = agent_spec.format_with_variables(variables)
        expected = "Hello John, you are in NYC. Your items: apple, banana, cherry"
        assert formatted_spec.prompt == expected


class TestSystemPromptSpecificationFormatting:
    """Test SystemPromptSpecification formatting functionality"""
    
    def test_format_with_variables_basic(self):
        """Test basic formatting of system specification"""
        agents = {
            "agent1": AgentPromptSpecification(
                name="agent1",
                prompt="Hello {{name}}, I'm agent1",
                tools=["tool1"]
            ),
            "client": AgentPromptSpecification(
                name="client",
                prompt="Hi, I'm {{name}} from {{location}}",
                tools=[]
            )
        }
        
        system_spec = SystemPromptSpecification(
            name="test_system",
            version="1.0",
            description="Test system",
            agents=agents
        )
        
        variables = {
            "name": "John",
            "location": "NYC"
        }
        
        formatted_spec = system_spec.format_with_variables(variables)
        
        assert formatted_spec.name == "test_system"
        assert formatted_spec.version == "1.0"
        assert formatted_spec.description == "Test system"
        assert len(formatted_spec.agents) == 2
        assert formatted_spec.agents["agent1"].prompt == "Hello John, I'm agent1"
        assert formatted_spec.agents["client"].prompt == "Hi, I'm John from NYC"
    
    def test_format_with_variables_missing_client_agent(self):
        """Test that missing client agent raises ValueError"""
        agents = {
            "agent1": AgentPromptSpecification(
                name="agent1",
                prompt="Hello {{name}}",
                tools=[]
            )
        }
        
        system_spec = SystemPromptSpecification(
            name="test_system",
            version="1.0",
            description="Test system",
            agents=agents
        )
        
        variables = {"name": "John"}
        
        with pytest.raises(ValueError) as exc_info:
            system_spec.format_with_variables(variables)
        
        assert "SystemPromptSpecification must contain a 'client' agent for user simulation" in str(exc_info.value)
    
    def test_format_with_variables_agent_formatting_failure(self):
        """Test that agent formatting failure is propagated with context"""
        agents = {
            "agent1": AgentPromptSpecification(
                name="agent1",
                prompt="Hello {{missing_var}}",  # Missing variable
                tools=[]
            ),
            "client": AgentPromptSpecification(
                name="client",
                prompt="Hi there",
                tools=[]
            )
        }
        
        system_spec = SystemPromptSpecification(
            name="test_system",
            version="1.0",
            description="Test system",
            agents=agents
        )
        
        variables = {"name": "John"}
        
        with pytest.raises(ValueError) as exc_info:
            system_spec.format_with_variables(variables)
        
        assert "Failed to format prompt for agent 'agent1'" in str(exc_info.value)
    
    def test_format_with_variables_immutable(self):
        """Test that formatting creates new instances without modifying originals"""
        original_agent_prompt = "Hello {{name}}"
        agents = {
            "agent1": AgentPromptSpecification(
                name="agent1",
                prompt=original_agent_prompt,
                tools=[]
            ),
            "client": AgentPromptSpecification(
                name="client",
                prompt="Client prompt",
                tools=[]
            )
        }
        
        system_spec = SystemPromptSpecification(
            name="test_system",
            version="1.0",
            description="Test system",
            agents=agents
        )
        
        variables = {"name": "John"}
        formatted_spec = system_spec.format_with_variables(variables)
        
        # Original should be unchanged
        assert system_spec.agents["agent1"].prompt == original_agent_prompt
        # New instance should be formatted
        assert formatted_spec.agents["agent1"].prompt == "Hello John"
        # Should be different instances
        assert system_spec is not formatted_spec
        assert system_spec.agents["agent1"] is not formatted_spec.agents["agent1"]
    
    def test_format_with_variables_preserves_handoffs(self):
        """Test that handoffs are preserved during formatting"""
        agents = {
            "agent1": AgentPromptSpecification(
                name="agent1",
                prompt="Hello {{name}}",
                tools=["tool1"],
                handoffs={"agent2": "For advanced queries"}
            ),
            "agent2": AgentPromptSpecification(
                name="agent2", 
                prompt="Advanced agent",
                tools=["tool2"]
            ),
            "client": AgentPromptSpecification(
                name="client",
                prompt="Client prompt",
                tools=[]
            )
        }
        
        system_spec = SystemPromptSpecification(
            name="test_system",
            version="1.0",
            description="Test system",
            agents=agents
        )
        
        variables = {"name": "John"}
        formatted_spec = system_spec.format_with_variables(variables)
        
        assert formatted_spec.agents["agent1"].handoffs == {"agent2": "For advanced queries"}
        assert formatted_spec.agents["agent2"].handoffs is None 