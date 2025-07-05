"""
System prompt specification for conversation simulation
Defines prompts and tools for different agents in the conversation
"""

import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from src.config import Config
from src.tools_specification import ToolsSpecification
from src.logging_utils import get_logger


@dataclass
class AgentPromptSpecification:
    """Specification for a single agent's prompt and tools"""

    name: str
    prompt: str
    tools: List[str]  # List of tool names
    description: Optional[str] = None
    handoffs: Optional[Dict[str, str]] = None  # Dict of agent_name -> handoff_description

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get the actual tool schemas for this agent"""
        # Start with explicitly defined tools
        tool_names = self.tools.copy()

        # Automatically add handoff tools based on handoffs configuration
        if self.handoffs:
            for agent_name in self.handoffs.keys():
                handoff_tool_name = f"handoff_{agent_name}"
                if handoff_tool_name not in tool_names:
                    tool_names.append(handoff_tool_name)

        return ToolsSpecification.get_tools_by_names(tool_names, self.handoffs or {})

    def format_with_variables(self, variables: Dict[str, Any]) -> "AgentPromptSpecification":
        """
        Create a new AgentPromptSpecification instance with formatted prompt using Jinja2.

        Args:
            variables: Dictionary of variables to substitute in the prompt template

        Returns:
            New AgentPromptSpecification instance with formatted prompt

        Raises:
            Exception: If formatting fails due to missing variables or template errors
        """
        from jinja2 import Environment, BaseLoader, Template, StrictUndefined, UndefinedError

        try:
            # Create Jinja2 environment with strict undefined handling
            jinja_env = Environment(loader=BaseLoader(), undefined=StrictUndefined)

            # Use Jinja2 to render the template with proper variable handling
            jinja_template = jinja_env.from_string(self.prompt)
            formatted_prompt = jinja_template.render(**variables)

            # Create new instance with formatted prompt
            return AgentPromptSpecification(
                name=self.name,
                prompt=formatted_prompt,
                tools=self.tools.copy(),
                description=self.description,
                handoffs=self.handoffs.copy() if self.handoffs else None,
            )

        except UndefinedError as e:
            raise ValueError(f"Missing variable in prompt template for agent '{self.name}': {e}")
        except Exception as e:
            raise ValueError(f"Template formatting failed for agent '{self.name}': {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        # Remove None values to keep JSON clean
        return {k: v for k, v in result.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any], prompts_dir: str = None) -> "AgentPromptSpecification":
        """Create instance from dictionary, resolving file references if needed"""
        # Create a copy to avoid modifying the original data
        data_copy = data.copy()

        # Resolve file reference in prompt if present
        if prompts_dir and "prompt" in data_copy:
            data_copy["prompt"] = cls._resolve_file_reference(data_copy["prompt"], prompts_dir)

        return cls(**data_copy)

    @staticmethod
    def _resolve_file_reference(prompt: str, prompts_dir: str) -> str:
        """Resolve file reference in prompt string"""
        if isinstance(prompt, str) and prompt.startswith("file:"):
            filename = prompt[5:]  # Remove 'file:' prefix
            filepath = os.path.join(prompts_dir, filename)

            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        return f.read().strip()
                except Exception as e:
                    return f"[ERROR: Could not read {filename}: {str(e)}]"
            else:
                return f"[ERROR: File not found: {filename}]"

        return prompt


@dataclass
class SystemPromptSpecification:
    """Complete system specification with all agents and their configurations"""

    name: str
    version: str
    description: Optional[str]
    agents: Dict[str, AgentPromptSpecification]

    def get_agent_prompt(self, agent_name: str) -> Optional[AgentPromptSpecification]:
        """Get prompt specification for a specific agent"""
        return self.agents.get(agent_name)

    def get_agent_tools(self, agent_name: str) -> List[Dict[str, Any]]:
        """Get tool schemas for a specific agent"""
        agent = self.get_agent_prompt(agent_name)
        if agent:
            return agent.get_tool_schemas()
        return []

    def format_with_variables(self, variables: Dict[str, Any]) -> "SystemPromptSpecification":
        """
        Create a new SystemPromptSpecification instance with all agent prompts formatted using Jinja2.

        Args:
            variables: Dictionary of variables to substitute in prompt templates

        Returns:
            New SystemPromptSpecification instance with all prompts formatted

        Raises:
            ValueError: If 'client' agent is missing or formatting fails for any agent
        """
        # Validate that 'client' agent exists (required for user simulation)
        if "client" not in self.agents:
            raise ValueError("SystemPromptSpecification must contain a 'client' agent for user simulation")

        # Format all agent prompts
        formatted_agents = {}
        for agent_name, agent_spec in self.agents.items():
            try:
                formatted_agents[agent_name] = agent_spec.format_with_variables(variables)
            except Exception as e:
                raise ValueError(f"Failed to format prompt for agent '{agent_name}': {e}")

        # Create new instance with formatted agents
        return SystemPromptSpecification(
            name=self.name, version=self.version, description=self.description, agents=formatted_agents
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "agents": {name: agent.to_dict() for name, agent in self.agents.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], prompts_dir: str = None) -> "SystemPromptSpecification":
        """Create instance from dictionary, resolving file references if needed"""
        agents = {
            name: AgentPromptSpecification.from_dict(agent_data, prompts_dir)
            for name, agent_data in data["agents"].items()
        }

        return cls(name=data["name"], version=data["version"], description=data.get("description"), agents=agents)

    def save_to_file(self, filepath: str) -> None:
        """Save specification to JSON file"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str) -> "SystemPromptSpecification":
        """Load specification from JSON file"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Prompt specification file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Pass the prompts directory for file reference resolution
        prompts_dir = os.path.dirname(filepath)
        return cls.from_dict(data, prompts_dir)


class PromptSpecificationManager:
    """Manager for loading and handling prompt specifications"""

    def __init__(self):
        self.logger = get_logger()
        self.prompts_dir = Config.PROMPTS_DIR
        self._cache: Dict[str, SystemPromptSpecification] = {}

    def get_specification_path(self, spec_name: str) -> str:
        """Get full path to a prompt specification file"""
        if not spec_name.endswith(".json"):
            spec_name += ".json"
        return os.path.join(self.prompts_dir, spec_name)

    def load_specification(self, spec_name: str) -> SystemPromptSpecification:
        """Load prompt specification from file with caching"""
        if spec_name in self._cache:
            return self._cache[spec_name]

        spec_path = self.get_specification_path(spec_name)

        try:
            specification = SystemPromptSpecification.load_from_file(spec_path)
            self._cache[spec_name] = specification

            self.logger.log_info(
                f"Loaded prompt specification: {spec_name}",
                extra_data={
                    "spec_name": spec_name,
                    "spec_path": spec_path,
                    "agents": list(specification.agents.keys()),
                    "version": specification.version,
                },
            )

            return specification

        except Exception as e:
            self.logger.log_error(
                f"Failed to load prompt specification: {spec_name}",
                exception=e,
                extra_data={"spec_name": spec_name, "spec_path": spec_path},
            )
            raise

    def get_specification_contents(self, spec_name: str) -> Dict[str, Any]:
        """Get the contents of a prompt specification as a dictionary"""
        try:
            specification = self.load_specification(spec_name)
            return specification.to_dict()
        except Exception as e:
            self.logger.log_error(f"Failed to get specification contents: {spec_name}", exception=e)
            raise

    def save_specification(self, spec_name: str, spec_data: Dict[str, Any]) -> None:
        """Save provided data as a new JSON specification"""
        try:
            # Validate the specification data
            specification = SystemPromptSpecification.from_dict(spec_data, self.prompts_dir)

            # Validate the specification
            issues = self.validate_specification(specification)
            if issues:
                raise ValueError(f"Specification validation failed: {'; '.join(issues)}")

            # Save to file
            spec_path = self.get_specification_path(spec_name)
            specification.save_to_file(spec_path)

            # Clear cache for this specification in case it existed before
            if spec_name in self._cache:
                del self._cache[spec_name]

            self.logger.log_info(
                f"Saved prompt specification: {spec_name}",
                extra_data={
                    "spec_name": spec_name,
                    "spec_path": spec_path,
                    "agents": list(specification.agents.keys()),
                    "version": specification.version,
                },
            )

        except Exception as e:
            self.logger.log_error(f"Failed to save prompt specification: {spec_name}", exception=e)
            raise

    def list_available_specifications(self) -> List[Dict[str, Any]]:
        """List all available prompt specifications in the prompts directory"""
        specifications = []

        try:
            if not os.path.exists(self.prompts_dir):
                return specifications

            for filename in os.listdir(self.prompts_dir):
                if filename.endswith(".json"):
                    spec_name = filename[:-5]  # Remove .json extension

                    try:
                        spec_path = os.path.join(self.prompts_dir, filename)

                        # Get file metadata
                        stat = os.stat(spec_path)

                        # Try to load basic info without full parsing
                        with open(spec_path, "r", encoding="utf-8") as f:
                            spec_data = json.load(f)

                        specifications.append(
                            {
                                "name": spec_name,
                                "display_name": spec_data.get("name", spec_name),
                                "version": spec_data.get("version", "unknown"),
                                "description": spec_data.get("description", ""),
                                "agents": list(spec_data.get("agents", {}).keys()),
                                "file_size": stat.st_size,
                                "last_modified": stat.st_mtime,
                            }
                        )
                    except Exception as e:
                        # Skip files that can't be parsed, but log the error
                        self.logger.log_error(f"Failed to parse specification file: {filename}", exception=e)
                        continue

            # Sort by name
            specifications.sort(key=lambda x: x["name"])

        except Exception as e:
            self.logger.log_error("Failed to list available specifications", exception=e)
            raise

        return specifications

    def delete_specification(self, spec_name: str) -> None:
        """Delete a prompt specification file"""
        # Prevent deletion of default specification
        if spec_name == "default_prompts":
            raise ValueError("Cannot delete the default prompt specification")

        spec_path = self.get_specification_path(spec_name)

        if not os.path.exists(spec_path):
            raise FileNotFoundError(f"Prompt specification file not found: {spec_name}")

        try:
            os.remove(spec_path)

            # Clear from cache if present
            if spec_name in self._cache:
                del self._cache[spec_name]

            self.logger.log_info(
                f"Deleted prompt specification: {spec_name}",
                extra_data={"spec_name": spec_name, "spec_path": spec_path},
            )

        except Exception as e:
            self.logger.log_error(f"Failed to delete prompt specification: {spec_name}", exception=e)
            raise

    def specification_exists(self, spec_name: str) -> bool:
        """Check if a prompt specification exists"""
        spec_path = self.get_specification_path(spec_name)
        return os.path.exists(spec_path)

    def get_default_specification(self) -> SystemPromptSpecification:
        """Get the default prompt specification"""
        return self.load_specification("default_prompts")

    def clear_cache(self) -> None:
        """Clear the specification cache"""
        self._cache.clear()

    def validate_specification(self, specification: SystemPromptSpecification) -> List[str]:
        """Validate a prompt specification and return list of issues"""
        issues = []

        # Check that required agents exist
        required_agents = ["agent", "client", "evaluator"]
        for agent_name in required_agents:
            if agent_name not in specification.agents:
                issues.append(f"Missing required agent: {agent_name}")

        # Validate tools for each agent
        available_tools = ToolsSpecification.get_available_tool_names()

        for agent_name, agent_spec in specification.agents.items():
            for tool_name in agent_spec.tools:
                # Skip handoff tools as they are dynamically generated
                if tool_name.startswith("handoff_"):
                    continue
                if tool_name not in available_tools:
                    issues.append(f"Agent '{agent_name}' references unknown tool: {tool_name}")

            # Validate handoffs if present
            if agent_spec.handoffs:
                for target_agent in agent_spec.handoffs.keys():
                    if target_agent not in specification.agents:
                        issues.append(f"Agent '{agent_name}' has handoff to non-existent agent: {target_agent}")

        return issues

    def create_default_specification_file(self) -> None:
        """Create the default specification file from current txt files"""
        # Read current txt files
        agent_prompt = self._read_txt_file("agent_system.txt")
        client_prompt = self._read_txt_file("client_system.txt")
        evaluator_prompt = self._read_txt_file("evaluator_system.txt")

        # Create specification
        specification = SystemPromptSpecification(
            name="Default LLM Simulation Prompts",
            version="1.0.0",
            description="Default prompt configuration converted from original txt files",
            agents={
                "agent": AgentPromptSpecification(
                    name="Sales Agent",
                    prompt=agent_prompt,
                    tools=[
                        "rag_find_products",
                        "add_to_cart",
                        "remove_from_cart",
                        "get_cart",
                        "change_delivery_date",
                        "set_current_location",
                        "call_transfer",
                    ],
                    description="Friendly sales manager Anna for food supply company",
                ),
                "client": AgentPromptSpecification(
                    name="Customer",
                    prompt=client_prompt,
                    tools=["end_call"],
                    description="Customer calling to place an order",
                ),
                "evaluator": AgentPromptSpecification(
                    name="Conversation Evaluator",
                    prompt=evaluator_prompt,
                    tools=[],
                    description="Expert evaluator of conversation quality",
                ),
            },
        )

        # Save to file
        spec_path = self.get_specification_path("default_prompts.json")
        specification.save_to_file(spec_path)

        self.logger.log_info(f"Created default specification file: {spec_path}")

    def _read_txt_file(self, filename: str) -> str:
        """Read content from a txt file in prompts directory"""
        filepath = os.path.join(self.prompts_dir, filename)

        if not os.path.exists(filepath):
            self.logger.log_error(f"Prompt file not found: {filepath}")
            return f"[ERROR: Could not load {filename}]"

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self.logger.log_error(f"Failed to read prompt file: {filepath}", exception=e)
            return f"[ERROR: Could not read {filename}]"
