"""
Integration tests for TargetAgentUploader
"""

import json
import os
import tempfile
import pytest
import requests
from unittest.mock import patch, Mock
from requests.exceptions import RequestException, Timeout

from src.target_agent_uploader import (
    TargetAgentUploader,
    AuthenticationError,
    UploadResult
)
from src.prompt_specification import AgentPromptSpecification


class TestTargetAgentUploaderIntegration:
    """Integration test cases for TargetAgentUploader"""

    @pytest.fixture
    def temp_prompts_dir(self):
        """Create temporary directory with mapping files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create tools mapping file
            tools_mapping = {
                "get_cart": 616,
                "add_to_cart": 614
            }
            tools_path = os.path.join(temp_dir, "target_tools_mapping.json")
            with open(tools_path, 'w', encoding='utf-8') as f:
                json.dump(tools_mapping, f)

            # Create agents mapping file
            agents_mapping = {
                "ENTRY": 710,
                "INTENT_CLASSIFIER": 711
            }
            agents_path = os.path.join(temp_dir, "target_agents_mapping.json")
            with open(agents_path, 'w', encoding='utf-8') as f:
                json.dump(agents_mapping, f)

            yield temp_dir

    @pytest.fixture
    def uploader(self, temp_prompts_dir):
        """Create TargetAgentUploader instance for testing"""
        with patch('src.target_agent_uploader.get_logger'):
            return TargetAgentUploader(
                base_url="https://api.test.com",
                company_id=54,
                api_key="test_api_key",
                prompts_dir=temp_prompts_dir
            )

    @pytest.fixture
    def sample_agent_spec(self) -> AgentPromptSpecification:
        """Sample agent specification for testing"""
        return AgentPromptSpecification(
            name="ENTRY",
            prompt="You are a helpful entry agent.",
            tools=["get_cart"],
            description="Entry agent for customer onboarding",
            handoffs={
                "INTENT_CLASSIFIER": "Transfer after collecting basic info"
            }
        )

    @patch('src.target_agent_uploader.requests.post')
    def test_upload_single_agent_success(self, mock_post, uploader, sample_agent_spec):
        """Test successful agent upload"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 710,
            "status": "created",
            "version": {"id": 100}
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = uploader.upload_single_agent(sample_agent_spec, 710)

        # Verify result
        assert result.success == True
        assert result.agent_name == "ENTRY"
        assert result.response == {"id": 710, "status": "created", "version": {"id": 100}}
        assert result.error is None

        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Check URL (first positional argument)
        assert call_args[0][0] == "https://api.test.com/api/agents/54"
        
        # Check headers
        headers = call_args[1]['headers']
        assert headers["Content-Type"] == "application/json"
        assert headers["accept"] == "application/json"
        assert headers["Authorization"] == "Bearer test_api_key"
        
        # Check payload structure
        payload = call_args[1]['json']
        assert payload["company_id"] == 54
        assert payload["agent_id"] == 710
        assert payload["version"]["name"] == "ENTRY"
        assert payload["version"]["instruction"] == "You are a helpful entry agent."

    @patch('src.target_agent_uploader.requests.post')
    def test_upload_single_agent_auth_failure_401(self, mock_post, uploader, sample_agent_spec):
        """Test authentication failure with 401 status"""
        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Invalid API key"
        mock_post.return_value = mock_response

        with pytest.raises(AuthenticationError, match="Authentication failed: Invalid API key"):
            uploader.upload_single_agent(sample_agent_spec, 710)

    @patch('src.target_agent_uploader.requests.post')
    def test_upload_single_agent_auth_failure_403(self, mock_post, uploader, sample_agent_spec):
        """Test access forbidden with 403 status"""
        # Mock 403 response
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Access forbidden"
        mock_post.return_value = mock_response

        with pytest.raises(AuthenticationError, match="Access forbidden: Access forbidden"):
            uploader.upload_single_agent(sample_agent_spec, 710)

    @patch('src.target_agent_uploader.requests.post')
    def test_upload_single_agent_server_error(self, mock_post, uploader, sample_agent_spec):
        """Test server error response"""
        # Mock server error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_response.raise_for_status.side_effect = RequestException("Server Error")
        mock_post.return_value = mock_response

        result = uploader.upload_single_agent(sample_agent_spec, 710)

        # Should return failed result, not raise exception
        assert result.success == False
        assert result.agent_name == "ENTRY"
        assert result.response is None
        assert "Request failed" in result.error

    @patch('src.target_agent_uploader.requests.post')
    def test_upload_single_agent_timeout(self, mock_post, uploader, sample_agent_spec):
        """Test request timeout"""
        # Mock timeout
        mock_post.side_effect = Timeout("Request timed out")

        result = uploader.upload_single_agent(sample_agent_spec, 710)

        # Should return failed result
        assert result.success == False
        assert result.agent_name == "ENTRY"
        assert result.response is None
        assert "Request failed" in result.error
        assert "timed out" in result.error

    @patch('src.target_agent_uploader.requests.post')
    def test_upload_single_agent_network_error(self, mock_post, uploader, sample_agent_spec):
        """Test network connection error"""
        # Mock connection error
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

        result = uploader.upload_single_agent(sample_agent_spec, 710)

        # Should return failed result
        assert result.success == False
        assert result.agent_name == "ENTRY"
        assert result.response is None
        assert "Request failed" in result.error
        assert "Connection failed" in result.error

    @patch('src.target_agent_uploader.requests.post')
    def test_upload_single_agent_invalid_json_response(self, mock_post, uploader, sample_agent_spec):
        """Test invalid JSON in response"""
        # Mock response with invalid JSON
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = uploader.upload_single_agent(sample_agent_spec, 710)

        # Should return failed result
        assert result.success == False
        assert result.agent_name == "ENTRY"
        assert result.response is None
        assert "Unexpected error" in result.error

    @patch('src.target_agent_uploader.requests.post')
    def test_upload_single_agent_payload_verification(self, mock_post, uploader, sample_agent_spec):
        """Test that the payload contains expected structure"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 710}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        uploader.upload_single_agent(sample_agent_spec, 710)

        # Get the payload that was sent
        payload = mock_post.call_args[1]['json']
        
        # Verify payload structure
        assert payload["company_id"] == 54
        assert payload["agent_id"] == 710
        
        version = payload["version"]
        assert version["name"] == "ENTRY"
        assert version["code_name"] == "entry"
        assert version["instruction"] == "You are a helpful entry agent."
        assert version["description"] == "Entry agent for customer onboarding"
        
        # Verify LLM configuration
        assert version["llm"]["model"] == "gpt-4o-mini"
        assert version["llm"]["vendor"] == "openai"
        
        # Verify TTS configuration
        assert version["tts"]["vendor"] == "yandex"
        assert version["tts"]["language"] == "ru-RU"
        
        # Verify tools
        tools = version["tools"]
        assert len(tools) == 2  # 1 function tool + 1 handoff
        
        # Check function tool
        function_tool = next(t for t in tools if t["type"] == "function")
        assert function_tool["name"] == "get_cart"
        assert function_tool["id"] == 616
        assert function_tool["calling_condition"] == "by_choice"
        
        # Check handoff tool
        agent_tool = next(t for t in tools if t["type"] == "agent")
        assert agent_tool["name"] == "INTENT_CLASSIFIER"
        assert agent_tool["id"] == 711
        assert agent_tool["description"] == "Transfer after collecting basic info"

    @patch('src.target_agent_uploader.requests.post')
    def test_ftfy_text_processing(self, mock_post, uploader):
        """Test that ftfy processes text correctly"""
        # Create agent with problematic text
        agent_spec = AgentPromptSpecification(
            name="TEST_AGENT",
            prompt="You are a helpful assistant with some café and naïve text.",
            tools=[],
            description="Test agent"
        )

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 999}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        with patch('ftfy.fix_text') as mock_ftfy:
            mock_ftfy.return_value = "Fixed text"
            
            uploader.upload_single_agent(agent_spec, 999)
            
            # Verify ftfy was called with the original prompt
            mock_ftfy.assert_called_once_with(agent_spec.prompt)
            
            # Verify the fixed text was used in the payload
            payload = mock_post.call_args[1]['json']
            assert payload["version"]["instruction"] == "Fixed text"

    @patch('src.target_agent_uploader.requests.post')
    def test_multiple_agents_upload(self, mock_post, uploader):
        """Test uploading multiple agents with mixed results"""
        from src.prompt_specification import SystemPromptSpecification
        
        # Create system spec with multiple agents
        agents = {
            "ENTRY": AgentPromptSpecification(
                name="ENTRY",
                prompt="Entry prompt",
                tools=["get_cart"],
                description="Entry agent"
            ),
            "INTENT_CLASSIFIER": AgentPromptSpecification(
                name="INTENT_CLASSIFIER", 
                prompt="Classifier prompt",
                tools=["add_to_cart"],
                description="Intent classifier"
            )
        }
        
        system_spec = SystemPromptSpecification(
            name="Test System",
            version="1.0.0",
            description="Test system",
            agents=agents
        )

        # Mock mixed responses - first success, second failure
        def mock_post_side_effect(*args, **kwargs):
            if "agent_id" in kwargs['json'] and kwargs['json']["agent_id"] == 710:
                # First call (ENTRY) - success
                response = Mock()
                response.status_code = 200
                response.json.return_value = {"id": 710, "status": "created"}
                response.raise_for_status.return_value = None
                return response
            else:
                # Second call (INTENT_CLASSIFIER) - failure
                response = Mock()
                response.status_code = 500
                response.text = "Server error"
                response.raise_for_status.side_effect = RequestException("Server Error")
                return response

        mock_post.side_effect = mock_post_side_effect

        results = uploader.upload_all_agents(system_spec)

        # Verify results
        assert len(results) == 2
        
        # Check successful upload
        success_result = next(r for r in results if r.agent_name == "ENTRY")
        assert success_result.success == True
        assert success_result.response == {"id": 710, "status": "created"}
        
        # Check failed upload
        fail_result = next(r for r in results if r.agent_name == "INTENT_CLASSIFIER")
        assert fail_result.success == False
        assert "Request failed" in fail_result.error 