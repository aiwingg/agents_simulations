"""
Target Agent Uploader - Infrastructure layer for uploading agents to Target AI platform
"""

import json
import os
import requests
import ftfy
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from src.prompt_specification import SystemPromptSpecification, AgentPromptSpecification
from src.logging_utils import get_logger


class MappingNotFoundError(Exception):
    """Exception raised when tool or agent mapping is not found"""
    pass


class TargetAPIError(Exception):
    """Exception raised when Target API returns an error"""
    pass


class AuthenticationError(Exception):
    """Exception raised when authentication fails"""
    pass


@dataclass
class UploadResult:
    """Result of uploading a single agent"""
    agent_name: str
    success: bool
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TargetAgentUploader:
    """Handles uploading agent configurations to Target AI platform"""
    
    def __init__(self, base_url: str, company_id: int, api_key: str, prompts_dir: str):
        """
        Initialize the uploader with API credentials and configuration
        
        Args:
            base_url: Target API base URL (e.g., https://app.targetai.ai)
            company_id: Company ID for the Target platform
            api_key: API key for authentication
            prompts_dir: Directory containing prompt files and mappings
        """
        self.base_url = base_url.rstrip('/')
        self.company_id = company_id
        self.api_key = api_key
        self.prompts_dir = prompts_dir
        self.logger = get_logger()
        
        # Load mappings once during initialization
        self.tools_mapping, self.agents_mapping = self.load_mappings()
    
    def load_mappings(self) -> Tuple[Dict[str, int], Dict[str, int]]:
        """
        Load tool and agent mappings from JSON files
        
        Returns:
            Tuple of (tools_mapping, agents_mapping)
            
        Raises:
            MappingNotFoundError: If mapping files are not found or invalid
        """
        tools_mapping_path = os.path.join(self.prompts_dir, "target_tools_mapping.json")
        agents_mapping_path = os.path.join(self.prompts_dir, "target_agents_mapping.json")
        
        try:
            # Load tools mapping
            if not os.path.exists(tools_mapping_path):
                raise MappingNotFoundError(f"Tools mapping file not found: {tools_mapping_path}")
            
            with open(tools_mapping_path, 'r', encoding='utf-8') as f:
                tools_mapping = json.load(f)
            
            # Load agents mapping
            if not os.path.exists(agents_mapping_path):
                raise MappingNotFoundError(f"Agents mapping file not found: {agents_mapping_path}")
            
            with open(agents_mapping_path, 'r', encoding='utf-8') as f:
                agents_mapping = json.load(f)
            
            self.logger.log_info(
                "Loaded Target API mappings",
                extra_data={
                    "tools_count": len(tools_mapping),
                    "agents_count": len(agents_mapping),
                    "tools": list(tools_mapping.keys()),
                    "agents": list(agents_mapping.keys())
                }
            )
            
            return tools_mapping, agents_mapping
            
        except json.JSONDecodeError as e:
            raise MappingNotFoundError(f"Invalid JSON in mapping file: {e}")
        except Exception as e:
            raise MappingNotFoundError(f"Failed to load mappings: {e}")
    
    def _build_tool_payload(self, tool_name: str, description: str) -> Dict[str, Any]:
        """
        Convert local tool name to Target API tool format
        
        Args:
            tool_name: Local tool name (e.g., 'rag_find_products')
            description: Tool description from tools specification
            
        Returns:
            Tool payload dict for Target API
            
        Raises:
            MappingNotFoundError: If tool is not found in mapping
        """
        if tool_name not in self.tools_mapping:
            raise MappingNotFoundError(f"Tool '{tool_name}' not found in tools mapping")
        
        tool_id = self.tools_mapping[tool_name]
        
        if tool_id is None:
            raise MappingNotFoundError(f"Tool '{tool_name}' has null ID in mapping - needs to be configured")
        
        return {
            "type": "function",
            "name": tool_name,
            "strategy": "latest",
            "id": tool_id,
            "version": None,
            "calling_condition": "by_choice",
            "description": description,
            "order_number": None
        }
    
    def _build_handoff_payload(self, agent_name: str, description: str) -> Dict[str, Any]:
        """
        Convert handoff to Target API agent tool format
        
        Args:
            agent_name: Target agent name for handoff
            description: Handoff description
            
        Returns:
            Handoff payload dict for Target API
            
        Raises:
            MappingNotFoundError: If agent is not found in mapping
        """
        if agent_name not in self.agents_mapping:
            raise MappingNotFoundError(f"Agent '{agent_name}' not found in agents mapping")
        
        agent_id = self.agents_mapping[agent_name]
        
        if agent_id is None:
            raise MappingNotFoundError(f"Agent '{agent_name}' has null ID in mapping - needs to be configured")
        
        return {
            "type": "agent",
            "name": agent_name,
            "strategy": "latest",
            "id": agent_id,
            "version": None,
            "calling_condition": "by_choice",
            "description": description,
            "order_number": None
        }
    
    def build_agent_payload(self, agent_spec: AgentPromptSpecification, agent_id: int) -> Dict[str, Any]:
        """
        Build complete Target API payload for single agent
        
        Args:
            agent_spec: Agent specification from prompt system
            agent_id: Target agent ID for this agent
            
        Returns:
            Complete agent payload for Target API
            
        Raises:
            MappingNotFoundError: If tools or handoff agents not found in mappings
        """
        # Process prompt with ftfy to fix encoding issues
        processed_prompt = ftfy.fix_text(agent_spec.prompt)
        
        # Build tools payload
        tools = []
        
        # Add function tools
        for tool_name in agent_spec.tools:
            # Get tool description from tools specification
            # For now, use a placeholder description - this should be enhanced
            # to get actual descriptions from ToolsSpecification
            tool_description = f"Tool: {tool_name}"
            tools.append(self._build_tool_payload(tool_name, tool_description))
        
        # Add handoff tools
        if agent_spec.handoffs:
            for target_agent, handoff_description in agent_spec.handoffs.items():
                tools.append(self._build_handoff_payload(target_agent, handoff_description))
        
        # Build complete payload matching the Target API structure
        payload = {
            "company_id": self.company_id,
            "agent_id": agent_id,
            "version": {
                "name": agent_spec.name,
                "code_name": agent_spec.name.lower(),
                "instruction": processed_prompt,
                "description": agent_spec.description or f"Agent: {agent_spec.name}",
                "arguments": {},
                "stt": {
                    "vendor": "yandex",
                    "language": "auto"
                },
                "llm": {
                    "model": "gpt-4o-mini",
                    "vendor": "openai"
                },
                "tts": {
                    "speed": 1.2,
                    "voice": "lera",
                    "vendor": "yandex",
                    "language": "ru-RU"
                },
                "personality": {
                    "name": "buddy",
                    "base_prompt": "Be friendly and helpful in your responses."
                },
                "background_volume": None,
                "background_id": None,
                "initiator": "agent",
                "frequency": "all",
                "voicemail_detector": "basic",
                "tool_calling_policy": "immediate",
                "chat_timeout_mins": 60,
                "voice_timeout_secs": 30,
                "tools": tools,
                "simulations": []
            }
        }
        
        return payload
    
    def upload_single_agent(self, agent_spec: AgentPromptSpecification, agent_id: int) -> UploadResult:
        """
        Upload a single agent to Target API
        
        Args:
            agent_spec: Agent specification
            agent_id: Target agent ID
            
        Returns:
            UploadResult with success status and response/error details
        """
        try:
            payload = self.build_agent_payload(agent_spec, agent_id)
            
            headers = {
                "Content-Type": "application/json",
                "accept": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            url = f"{self.base_url}/api/agents/{self.company_id}"
            
            self.logger.log_info(
                f"Uploading agent to Target API",
                extra_data={
                    "agent_name": agent_spec.name,
                    "agent_id": agent_id,
                    "url": url,
                    "tools_count": len(payload["version"]["tools"])
                }
            )
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 401:
                raise AuthenticationError(f"Authentication failed: {response.text}")
            elif response.status_code == 403:
                raise AuthenticationError(f"Access forbidden: {response.text}")
            
            response.raise_for_status()
            
            result_data = response.json()
            
            self.logger.log_info(
                f"Successfully uploaded agent: {agent_spec.name}",
                extra_data={
                    "agent_name": agent_spec.name,
                    "agent_id": agent_id,
                    "response": result_data
                }
            )
            
            return UploadResult(
                agent_name=agent_spec.name,
                success=True,
                response=result_data
            )
            
        except (AuthenticationError, MappingNotFoundError) as e:
            # Re-raise these specific errors
            raise
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {e}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f" (Status: {e.response.status_code}, Body: {e.response.text})"
            
            self.logger.log_error(
                f"Failed to upload agent: {agent_spec.name}",
                exception=e,
                extra_data={"agent_name": agent_spec.name, "agent_id": agent_id}
            )
            
            return UploadResult(
                agent_name=agent_spec.name,
                success=False,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            
            self.logger.log_error(
                f"Unexpected error uploading agent: {agent_spec.name}",
                exception=e,
                extra_data={"agent_name": agent_spec.name, "agent_id": agent_id}
            )
            
            return UploadResult(
                agent_name=agent_spec.name,
                success=False,
                error=error_msg
            )
    
    def upload_all_agents(self, prompt_spec: SystemPromptSpecification) -> List[UploadResult]:
        """
        Upload all agents from prompt specification (excluding client and evaluator)
        
        Args:
            prompt_spec: Complete system prompt specification
            
        Returns:
            List of UploadResult objects for each agent
            
        Raises:
            MappingNotFoundError: If any agent is missing from mapping
        """
        results = []
        excluded_agents = {"client", "evaluator"}
        
        for agent_name, agent_spec in prompt_spec.agents.items():
            # Skip client and evaluator agents
            if agent_name in excluded_agents:
                self.logger.log_info(f"Skipping excluded agent: {agent_name}")
                continue
            
            # Check if agent has mapping
            if agent_name not in self.agents_mapping:
                error_msg = f"Agent '{agent_name}' not found in agents mapping"
                results.append(UploadResult(
                    agent_name=agent_name,
                    success=False,
                    error=error_msg
                ))
                continue
            
            agent_id = self.agents_mapping[agent_name]
            
            if agent_id is None:
                error_msg = f"Agent '{agent_name}' has null ID in mapping - needs to be configured"
                results.append(UploadResult(
                    agent_name=agent_name,
                    success=False,
                    error=error_msg
                ))
                continue
            
            # Upload the agent
            result = self.upload_single_agent(agent_spec, agent_id)
            results.append(result)
        
        # Log summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        
        self.logger.log_info(
            f"Agent upload completed",
            extra_data={
                "total_agents": len(results),
                "successful": successful,
                "failed": failed,
                "excluded_agents": list(excluded_agents)
            }
        )
        
        return results 