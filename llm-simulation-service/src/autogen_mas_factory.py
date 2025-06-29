"""
AutogenMASFactory - Infrastructure Layer
Creates AutoGen Swarm teams from SystemPromptSpecification with proper configuration
"""
from typing import List, Dict
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import Swarm
from autogen_agentchat.conditions import TextMessageTermination, MaxMessageTermination

from autogen_core.tools import BaseTool

from src.prompt_specification import SystemPromptSpecification, AgentPromptSpecification
from src.logging_utils import get_logger
from src.config import Config


class AutogenMASFactory:
    """
    Lightweight factory for creating configured AutoGen Swarm teams from SystemPromptSpecification
    Converts existing OpenAIWrapper configuration to AutoGen-compatible components
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.logger = get_logger()
        
    def create_swarm_team(
        self, 
        system_prompt_spec: SystemPromptSpecification, 
        tools: List[BaseTool], 
        model_client
    ) -> Swarm:
        """
        Creates AutoGen Swarm team from SystemPromptSpecification and pre-created tools
        
        Args:
            system_prompt_spec: SystemPromptSpecification with agent configurations
            tools: List of pre-created BaseTool instances (from AutogenToolFactory)
            model_client: OpenAIChatCompletionClient for the agents
            
        Returns:
            Configured Swarm instance ready for conversation execution
        """
        # Validate that at least one agent exists
        if not system_prompt_spec.agents:
            raise ValueError("SystemPromptSpecification must contain at least one agent")
        
        self.logger.log_info(f"Creating Swarm team for session {self.session_id}", extra_data={
            'spec_name': system_prompt_spec.name,
            'spec_version': system_prompt_spec.version,
            'agents': list(system_prompt_spec.agents.keys()),
            'tools_count': len(tools)
        })
        
        # Create AssistantAgent instances with handoffs and tools
        agents = self._create_swarm_agents(
            system_prompt_spec.agents, 
            tools, 
            model_client
        )
        
        # Get max internal messages from config and create termination conditions
        max_internal_messages = Config.get_max_internal_messages()
        termination = self._create_termination_conditions(max_internal_messages)
        
        # Create and return Swarm
        swarm = Swarm(participants=agents, termination_condition=termination)
        
        self.logger.log_info(f"Swarm team created successfully for session {self.session_id}", extra_data={
            'agents_count': len(agents),
            'agent_names': [agent.name for agent in agents]
        })
        
        return swarm
    

    
    def _create_swarm_agents(
        self, 
        agents_config: Dict[str, AgentPromptSpecification], 
        tools: List[BaseTool], 
        model_client
    ) -> List[AssistantAgent]:
        """
        Creates AssistantAgent instances with handoffs and tools
        
        Args:
            agents_config: Dictionary of agent name -> AgentPromptSpecification
            tools: List of available tools to distribute among agents
            model_client: OpenAI client for the agents
            
        Returns:
            List of configured AssistantAgent instances
        """
        agents = []
        
        # Setup handoff relationships: agent-to-agent only (no user handoffs)
        handoff_config = self._setup_agent_handoffs(agents_config)
        
        # Create tool mapping for efficient lookup
        tools_by_name = {tool.name: tool for tool in tools}
        
        for agent_name, agent_spec in agents_config.items():
            # Get tools for this agent
            agent_tools = []
            for tool_name in agent_spec.tools:
                if tool_name in tools_by_name:
                    agent_tools.append(tools_by_name[tool_name])
                else:
                    # Skip handoff tools as they're handled by AutoGen's handoff mechanism
                    if not tool_name.startswith('handoff_'):
                        self.logger.log_warning(f"Tool '{tool_name}' not found for agent '{agent_name}'")
            
            # Get handoffs for this agent
            agent_handoffs = handoff_config.get(agent_name, [])
            
            # Create AssistantAgent
            agent = AssistantAgent(
                name=agent_name,
                model_client=model_client,
                handoffs=agent_handoffs,
                tools=agent_tools,
                system_message=agent_spec.prompt,
                description=agent_spec.description or f"Agent {agent_name}"
            )
            
            agents.append(agent)
            
            self.logger.log_info(f"Created agent '{agent_name}' for session {self.session_id}", extra_data={
                'tools_count': len(agent_tools),
                'handoffs': agent_handoffs,
                'session_id': self.session_id
            })
        
        return agents
    
    def _setup_agent_handoffs(
        self, 
        agents_config: Dict[str, AgentPromptSpecification]
    ) -> Dict[str, List[str]]:
        """
        Configures handoff relationships: agent-to-agent only (no user handoffs)
        
        Args:
            agents_config: Dictionary of agent configurations
            
        Returns:
            Dictionary mapping agent_name -> list of handoff targets (agents only)
        """
        handoff_config = {}
        
        for agent_name, agent_spec in agents_config.items():
            handoffs = []
            
            # Add agent-to-agent handoffs from specification
            if agent_spec.handoffs:
                for target_agent in agent_spec.handoffs.keys():
                    if target_agent in agents_config:
                        handoffs.append(target_agent)
                    else:
                        self.logger.log_warning(
                            f"Agent '{agent_name}' has handoff to non-existent agent: '{target_agent}'"
                        )
            
            # NOTE: Removed user handoff target since user is now external to MAS
            handoff_config[agent_name] = handoffs
        
        self.logger.log_info(f"Configured handoffs for session {self.session_id}", extra_data={
            'handoff_config': handoff_config,
            'user_external': True
        })
        
        return handoff_config
    
    def _create_termination_conditions(self, max_internal_messages: int):
        """
        Creates combined termination conditions to limit internal MAS conversations
        
        Args:
            max_internal_messages: Maximum number of internal messages before termination
            
        Returns:
            Combined termination condition for the Swarm
        """
        # Combine TextMessageTermination with MaxMessageTermination to prevent runaway conversations
        text_termination = TextMessageTermination()
        max_msg_termination = MaxMessageTermination(max_messages=max_internal_messages)
        termination = text_termination | max_msg_termination
        
        self.logger.log_info(f"Created termination conditions for session {self.session_id}", extra_data={
            'user_external': True,
            'conditions': ['TextMessageTermination', 'MaxMessageTermination'],
            'max_internal_messages': max_internal_messages
        })
        
        return termination
    
