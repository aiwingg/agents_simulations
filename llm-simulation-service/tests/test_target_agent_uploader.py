"""
Unit tests for TargetAgentUploader
"""

import json
import os
import tempfile
import pytest
from unittest.mock import patch, mock_open
from typing import Dict, Any

from src.target_agent_uploader import (
    TargetAgentUploader,
    MappingNotFoundError,
    UploadResult
)
from src.prompt_specification import AgentPromptSpecification, SystemPromptSpecification


class TestTargetAgentUploader:
    """Test cases for TargetAgentUploader"""

    @pytest.fixture
    def sample_tools_mapping(self) -> Dict[str, int]:
        """Sample tools mapping for tests"""
        return {
            "rag_find_products": 606,
            "add_to_cart": 614,
            "get_cart": 616,
            "change_delivery_date": 621
        }

    @pytest.fixture
    def sample_agents_mapping(self) -> Dict[str, int]:
        """Sample agents mapping for tests"""
        return {
            "ENTRY": 710,
            "INTENT_CLASSIFIER": 711,
            "PRODUCT_SELECTOR": 712,
            "GOODBYE": 713
        }

    @pytest.fixture
    def temp_prompts_dir(self, sample_tools_mapping, sample_agents_mapping):
        """Create temporary directory with mapping files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create tools mapping file
            tools_path = os.path.join(temp_dir, "target_tools_mapping.json")
            with open(tools_path, 'w', encoding='utf-8') as f:
                json.dump(sample_tools_mapping, f)

            # Create agents mapping file
            agents_path = os.path.join(temp_dir, "target_agents_mapping.json")
            with open(agents_path, 'w', encoding='utf-8') as f:
                json.dump(sample_agents_mapping, f)

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
            prompt="You are a helpful entry agent. Welcome customers and collect their information.",
            tools=["change_delivery_date", "get_cart"],
            description="Entry agent for customer onboarding",
            handoffs={
                "INTENT_CLASSIFIER": "Transfer after collecting basic info",
                "PRODUCT_SELECTOR": "Transfer when customer wants to browse products"
            }
        )

    def test_load_mappings_success(self, uploader, sample_tools_mapping, sample_agents_mapping):
        """Test successful loading of mapping files"""
        tools_mapping, agents_mapping = uploader.load_mappings()
        
        assert tools_mapping == sample_tools_mapping
        assert agents_mapping == sample_agents_mapping

    def test_load_mappings_missing_tools_file(self):
        """Test exception when tools mapping file is missing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create only agents mapping
            agents_path = os.path.join(temp_dir, "target_agents_mapping.json")
            with open(agents_path, 'w', encoding='utf-8') as f:
                json.dump({}, f)

            with patch('src.target_agent_uploader.get_logger'):
                with pytest.raises(MappingNotFoundError, match="Tools mapping file not found"):
                    TargetAgentUploader(
                        base_url="https://api.test.com",
                        company_id=54,
                        api_key="test_key",
                        prompts_dir=temp_dir
                    )

    def test_load_mappings_missing_agents_file(self):
        """Test exception when agents mapping file is missing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create only tools mapping
            tools_path = os.path.join(temp_dir, "target_tools_mapping.json")
            with open(tools_path, 'w', encoding='utf-8') as f:
                json.dump({}, f)

            with patch('src.target_agent_uploader.get_logger'):
                with pytest.raises(MappingNotFoundError, match="Agents mapping file not found"):
                    TargetAgentUploader(
                        base_url="https://api.test.com",
                        company_id=54,
                        api_key="test_key",
                        prompts_dir=temp_dir
                    )

    def test_load_mappings_invalid_json(self):
        """Test exception when mapping file contains invalid JSON"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create invalid JSON files
            tools_path = os.path.join(temp_dir, "target_tools_mapping.json")
            with open(tools_path, 'w', encoding='utf-8') as f:
                f.write("invalid json content")

            agents_path = os.path.join(temp_dir, "target_agents_mapping.json")
            with open(agents_path, 'w', encoding='utf-8') as f:
                json.dump({}, f)

            with patch('src.target_agent_uploader.get_logger'):
                with pytest.raises(MappingNotFoundError, match="Invalid JSON in mapping file"):
                    TargetAgentUploader(
                        base_url="https://api.test.com",
                        company_id=54,
                        api_key="test_key",
                        prompts_dir=temp_dir
                    )

    def test_build_tool_payload_success(self, uploader):
        """Test successful tool payload building"""
        payload = uploader._build_tool_payload("add_to_cart", "Add item to shopping cart")
        
        expected = {
            "type": "function",
            "name": "add_to_cart",
            "strategy": "latest",
            "id": 614,
            "version": None,
            "calling_condition": "by_choice",
            "description": "Add item to shopping cart",
            "order_number": None
        }
        
        assert payload == expected

    def test_build_tool_payload_missing_tool(self, uploader):
        """Test exception when tool not found in mapping"""
        with pytest.raises(MappingNotFoundError, match="Tool 'unknown_tool' not found in tools mapping"):
            uploader._build_tool_payload("unknown_tool", "Unknown tool")

    def test_build_tool_payload_null_id(self, temp_prompts_dir):
        """Test exception when tool has null ID"""
        # Create mapping with null ID
        tools_mapping = {"test_tool": None}
        tools_path = os.path.join(temp_prompts_dir, "target_tools_mapping.json")
        with open(tools_path, 'w', encoding='utf-8') as f:
            json.dump(tools_mapping, f)

        # Reload the uploader to pick up the new mapping
        with patch('src.target_agent_uploader.get_logger'):
            uploader = TargetAgentUploader(
                base_url="https://api.test.com",
                company_id=54,
                api_key="test_key",
                prompts_dir=temp_prompts_dir
            )

        with pytest.raises(MappingNotFoundError, match="Tool 'test_tool' has null ID in mapping"):
            uploader._build_tool_payload("test_tool", "Test tool")

    def test_build_handoff_payload_success(self, uploader):
        """Test successful handoff payload building"""
        payload = uploader._build_handoff_payload("INTENT_CLASSIFIER", "Transfer to intent classifier")
        
        expected = {
            "type": "agent",
            "name": "INTENT_CLASSIFIER",
            "strategy": "latest",
            "id": 711,
            "version": None,
            "calling_condition": "by_choice",
            "description": "Transfer to intent classifier",
            "order_number": None
        }
        
        assert payload == expected

    def test_build_handoff_payload_missing_agent(self, uploader):
        """Test exception when handoff agent not found in mapping"""
        with pytest.raises(MappingNotFoundError, match="Agent 'UNKNOWN_AGENT' not found in agents mapping"):
            uploader._build_handoff_payload("UNKNOWN_AGENT", "Transfer to unknown agent")

    def test_build_handoff_payload_null_id(self, temp_prompts_dir):
        """Test exception when handoff agent has null ID"""
        # Create mapping with null ID
        agents_mapping = {"TEST_AGENT": None}
        agents_path = os.path.join(temp_prompts_dir, "target_agents_mapping.json")
        with open(agents_path, 'w', encoding='utf-8') as f:
            json.dump(agents_mapping, f)

        # Reload the uploader to pick up the new mapping
        with patch('src.target_agent_uploader.get_logger'):
            uploader = TargetAgentUploader(
                base_url="https://api.test.com",
                company_id=54,
                api_key="test_key",
                prompts_dir=temp_prompts_dir
            )

        with pytest.raises(MappingNotFoundError, match="Agent 'TEST_AGENT' has null ID in mapping"):
            uploader._build_handoff_payload("TEST_AGENT", "Transfer to test agent")

    def test_build_agent_payload_success(self, uploader, sample_agent_spec):
        """Test successful agent payload building"""
        with patch('ftfy.fix_text', return_value=sample_agent_spec.prompt):
            payload = uploader.build_agent_payload(sample_agent_spec, 710)
        
        # Verify basic structure
        assert payload["company_id"] == 54
        assert payload["agent_id"] == 710
        assert payload["version"]["name"] == "ENTRY"
        assert payload["version"]["code_name"] == "entry"
        assert payload["version"]["instruction"] == sample_agent_spec.prompt
        assert payload["version"]["description"] == sample_agent_spec.description
        
        # Verify tools
        tools = payload["version"]["tools"]
        assert len(tools) == 4  # 2 function tools + 2 handoff tools
        
        # Check function tools
        function_tools = [t for t in tools if t["type"] == "function"]
        assert len(function_tools) == 2
        
        tool_names = [t["name"] for t in function_tools]
        assert "change_delivery_date" in tool_names
        assert "get_cart" in tool_names
        
        # Check handoff tools
        agent_tools = [t for t in tools if t["type"] == "agent"]
        assert len(agent_tools) == 2
        
        agent_names = [t["name"] for t in agent_tools]
        assert "INTENT_CLASSIFIER" in agent_names
        assert "PRODUCT_SELECTOR" in agent_names

    def test_build_agent_payload_missing_tool_mapping(self, uploader, sample_agent_spec):
        """Test exception when agent uses unmapped tool"""
        # Create agent spec with unknown tool
        agent_spec = AgentPromptSpecification(
            name="TEST_AGENT",
            prompt="Test prompt",
            tools=["unknown_tool"],
            description="Test agent"
        )
        
        with pytest.raises(MappingNotFoundError, match="Tool 'unknown_tool' not found in tools mapping"):
            uploader.build_agent_payload(agent_spec, 999)

    def test_build_agent_payload_missing_agent_mapping(self, uploader, sample_agent_spec):
        """Test exception when agent has handoff to unmapped agent"""
        # Create agent spec with unknown handoff
        agent_spec = AgentPromptSpecification(
            name="TEST_AGENT",
            prompt="Test prompt",
            tools=[],
            description="Test agent",
            handoffs={"UNKNOWN_AGENT": "Transfer to unknown"}
        )
        
        with pytest.raises(MappingNotFoundError, match="Agent 'UNKNOWN_AGENT' not found in agents mapping"):
            uploader.build_agent_payload(agent_spec, 999)

    def test_upload_all_agents_filters_excluded(self, uploader):
        """Test that client and evaluator agents are excluded from upload"""
        # Create system spec with all types of agents
        agents = {
            "ENTRY": AgentPromptSpecification(
                name="ENTRY",
                prompt="Entry prompt",
                tools=["get_cart"],
                description="Entry agent"
            ),
            "client": AgentPromptSpecification(
                name="client",
                prompt="Client prompt",
                tools=[],
                description="Client agent"
            ),
            "evaluator": AgentPromptSpecification(
                name="evaluator", 
                prompt="Evaluator prompt",
                tools=[],
                description="Evaluator agent"
            )
        }
        
        system_spec = SystemPromptSpecification(
            name="Test System",
            version="1.0.0",
            description="Test system",
            agents=agents
        )
        
        # Mock the upload_single_agent method to avoid actual API calls
        with patch.object(uploader, 'upload_single_agent') as mock_upload:
            mock_upload.return_value = UploadResult(
                agent_name="ENTRY",
                success=True,
                response={"id": 710}
            )
            
            results = uploader.upload_all_agents(system_spec)
        
        # Should only have 1 result (ENTRY), client and evaluator should be excluded
        assert len(results) == 1
        assert results[0].agent_name == "ENTRY"
        assert results[0].success == True
        
        # Verify upload_single_agent was called only once
        mock_upload.assert_called_once()

    def test_upload_all_agents_handles_null_mappings(self, temp_prompts_dir):
        """Test that agents with null IDs are handled gracefully"""
        # Create mapping with null ID
        agents_mapping = {"ENTRY": 710, "NULL_AGENT": None}
        agents_path = os.path.join(temp_prompts_dir, "target_agents_mapping.json")
        with open(agents_path, 'w', encoding='utf-8') as f:
            json.dump(agents_mapping, f)

        # Reload uploader
        with patch('src.target_agent_uploader.get_logger'):
            uploader = TargetAgentUploader(
                base_url="https://api.test.com",
                company_id=54,
                api_key="test_key",
                prompts_dir=temp_prompts_dir
            )

        # Create system spec
        agents = {
            "NULL_AGENT": AgentPromptSpecification(
                name="NULL_AGENT",
                prompt="Null agent prompt",
                tools=[],
                description="Agent with null ID"
            )
        }
        
        system_spec = SystemPromptSpecification(
            name="Test System",
            version="1.0.0", 
            description="Test system",
            agents=agents
        )
        
        results = uploader.upload_all_agents(system_spec)
        
        # Should have 1 result with error
        assert len(results) == 1
        assert results[0].agent_name == "NULL_AGENT"
        assert results[0].success == False
        assert "has null ID in mapping" in results[0].error 