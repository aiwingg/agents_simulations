# AutoGen Conversational Engine Implementation Plan

## Overview

This document outlines the architecture and implementation plan for creating a new conversational engine based on Microsoft AutoGen's Swarm pattern. This engine will replace the existing ConversationEngine while maintaining the same contract interface and leveraging AutoGen's built-in multi-agent coordination, tool calling, and memory management capabilities.

## Architecture Analysis & Challenges

### Original Proposal vs. Final Architecture

**Initial Concerns Addressed:**
1. **Testing Complexity**: AutoGen's components are already testable. Focus shifted to testing conversation logic rather than agent creation.
2. **Abstraction Overhead**: Avoided unnecessary complexity by leveraging AutoGen's native capabilities.
3. **UserProxy Simulation**: Used AutoGen's Swarm handoff mechanism with configurable user target for client simulation.

**Final Architecture Decision:**
Instead of a 2-layer approach, we adopted a **3-component architecture** that maintains separation of concerns while leveraging AutoGen's Swarm pattern.

## Component Architecture

### 1. AutogenMASFactory (Infrastructure Layer)

**Purpose**: Lightweight factory for creating configured AutoGen Swarm teams

**Contract:**
```python
class AutogenMASFactory:
    def __init__(self, session_id: str):
        self.session_id = session_id
    
    def create_swarm_team(self, system_prompt_spec: SystemPromptSpecification, 
                         tools: List[BaseTool], user_handoff_target: str = "client") -> Swarm:
        """Creates Autogen Swarm team from SystemPromptSpecification and pre-created tools"""
        
    def _create_autogen_client(self, openai_wrapper: OpenAIWrapper) -> OpenAIChatCompletionClient:
        """Creates OpenAIChatCompletionClient from existing OpenAIWrapper config"""
        # Extract model, api_key, base_url etc. from openai_wrapper
        # Return OpenAIChatCompletionClient(model=..., api_key=..., base_url=...)
        
    def _create_swarm_agents(self, agents_config: Dict[str, AgentPromptSpecification], 
                           tools: List[BaseTool], model_client: OpenAIChatCompletionClient,
                           user_handoff_target: str) -> List[AssistantAgent]:
        """Creates AssistantAgent instances with handoffs, tools, and user handoffs"""
        
    def _setup_agent_handoffs(self, agents_config: Dict[str, AgentPromptSpecification],
                             user_handoff_target: str) -> Dict[str, List[str]]:
        """Configures handoff relationships: agent-to-agent + ALL agents can handoff to user_handoff_target"""
        # Each agent gets: handoffs=["other_agent1", "other_agent2", user_handoff_target]
        
    def _create_termination_conditions(self, user_handoff_target: str) -> HandoffTermination | TextMentionTermination:
        """Creates HandoffTermination(target=user_handoff_target) | TextMentionTermination("TERMINATE")"""
```

**Key Features:**
- Converts OpenAIWrapper config to OpenAIChatCompletionClient
- Creates AssistantAgent instances with proper handoff configuration
- Configurable user handoff target (e.g., "client", "user", etc.)
- Sets up termination conditions for Swarm pattern

### 2. AutogenConversationEngine (Service Layer)

**Purpose**: Main engine implementing the ConversationEngine contract using AutoGen Swarm

**Contract:**
```python
class AutogenConversationEngine:
    def __init__(self, openai_wrapper: OpenAIWrapper, prompt_spec_name: str = "default_prompts"):
        self.openai_wrapper = openai_wrapper
        self.prompt_spec_name = prompt_spec_name
        # Note: session_id will be provided per conversation
    
    async def run_conversation(self, scenario: Dict[str, Any], max_turns: Optional[int] = None, 
                              timeout_sec: Optional[int] = None) -> Dict[str, Any]:
        """Basic conversation without tools - creates minimal Swarm setup"""
        
    async def run_conversation_with_tools(self, scenario: Dict[str, Any], max_turns: Optional[int] = None,
                                         timeout_sec: Optional[int] = None) -> Dict[str, Any]:
        """
        Tool-enabled conversation using Swarm pattern:
        1. Extract session_id from scenario/webhook
        2. Create AutogenToolFactory(session_id) for session isolation
        3. Load SystemPromptSpecification from prompt_spec_name
        4. Create tools via tool_factory.get_tools_for_agent()  
        5. Create Swarm via mas_factory.create_swarm_team(spec, tools, "client")
        6. Run conversation with client handoff simulation
        7. Convert result via ConversationAdapter
        """
```

**Implementation Flow:**
1. **Session Setup**: Extract session_id from scenario or generate new one
2. **Tool Creation**: Instantiate AutogenToolFactory with session isolation
3. **Spec Loading**: Load SystemPromptSpecification for agent configuration
4. **Team Creation**: Use AutogenMASFactory to create Swarm with tools
5. **Conversation Execution**: Run Swarm with user handoff simulation
6. **Result Transformation**: Convert AutoGen TaskResult to contract format

### 3. ConversationAdapter (Service Layer)

**Purpose**: Translator between AutoGen's conversation format and existing contract

**Contract:**
```python
class ConversationAdapter:
    @staticmethod
    def autogen_to_contract_format(task_result: TaskResult, session_id: str, 
                                  scenario_name: str, duration: float) -> Dict[str, Any]:
        """Converts Autogen TaskResult to ConversationEngine contract format"""
        
    @staticmethod
    def extract_conversation_history(messages: List[BaseChatMessage]) -> List[Dict]:
        """Converts Autogen messages to conversation_history format with tool_calls/tool_results"""
        
    @staticmethod
    def simulate_client_responses(autogen_messages: List[BaseChatMessage], 
                                user_handoff_target: str = "client") -> List[Dict]:
        """Maps user handoff target messages to 'client' speaker format"""
        
    @staticmethod
    def handle_handoff_messages(messages: List[BaseChatMessage], 
                              user_handoff_target: str = "client") -> List[Dict]:
        """Processes HandoffMessage instances for client simulation"""
```

**Key Responsibilities:**
- Transform AutoGen TaskResult to match existing ConversationEngine output contract
- Convert AutoGen message format to conversation_history structure
- Map HandoffMessage instances to client speaker entries
- Preserve tool_calls and tool_results structure from existing contract

## AutoGen Swarm Pattern Integration

### Key Swarm Features Leveraged:

1. **Agent Handoffs**: `handoffs=["agent1", "agent2", "client"]` for natural delegation
2. **Natural Flow**: Agents decide when to handoff based on context and completion
3. **User Integration**: `HandoffTermination(target="client")` for client simulation
4. **Tool Integration**: Each agent gets specific tools via `tools=[tool1, tool2]`
5. **Memory Management**: AutoGen handles conversation context automatically

### Handoff Configuration:

```python
# Example agent configuration
sales_agent = AssistantAgent(
    "sales_agent",
    model_client=model_client,
    handoffs=["support_agent", "manager_agent", "client"],  # Configurable user target
    tools=[product_search_tool, add_to_cart_tool],
    system_message="You are a sales agent..."
)
```

### Termination Conditions:

```python
termination = (
    HandoffTermination(target="client") |  # When any agent hands off to client
    TextMentionTermination("TERMINATE")    # When any agent says TERMINATE
)
```

## Module Interactions

### Service Layer Flow:
1. **AutogenConversationEngine** receives scenario with variables
2. **Engine** creates session-isolated **AutogenToolFactory** 
3. **Engine** loads **SystemPromptSpecification** from prompt_spec_name
4. **Engine** creates tools via tool factory for each agent
5. **Engine** calls **AutogenMASFactory** with spec, tools, and user target
6. **Factory** creates **OpenAIChatCompletionClient** from OpenAIWrapper
7. **Factory** instantiates **Swarm** with configured agents and termination
8. **Engine** runs conversation via `swarm.run_stream()`
9. **ConversationAdapter** transforms AutoGen result to contract format
10. **Engine** returns formatted result matching existing ConversationEngine

### Layer Separation:
- **Service Layer**: Business logic, tool creation, conversation orchestration
- **Infrastructure Layer**: AutoGen team setup, agent configuration, model client creation
- **Adapter Layer**: Format translation between AutoGen and existing contracts

## Implementation Benefits

### Advantages of AutoGen Swarm:
- **Built-in Memory**: No need to implement conversation context management
- **Native Handoffs**: Sophisticated agent coordination without custom orchestration
- **Tool Integration**: Seamless tool calling with proper session isolation
- **Error Handling**: AutoGen handles LLM API errors and retries
- **Observability**: Built-in tracing and logging capabilities

### Contract Compatibility:
- Maintains exact same input/output contracts as existing ConversationEngine
- Preserves conversation_history structure with tool_calls/tool_results
- Supports both basic and tool-enabled conversation modes
- Compatible with existing BatchProcessor integration

## Configuration Examples

### SystemPromptSpecification for Swarm:
```json
{
  "name": "sales_support_team",
  "version": "1.0",
  "description": "Multi-agent sales and support team",
  "agents": {
    "sales_agent": {
      "name": "sales_agent", 
      "prompt": "You are a sales agent specializing in product recommendations...",
      "tools": ["rag_find_products", "add_to_cart"],
      "description": "Handles product search and sales",
      "handoffs": {
        "support_agent": "For technical support issues",
        "manager_agent": "For escalations"
      }
    },
    "support_agent": {
      "name": "support_agent",
      "prompt": "You are a technical support agent...", 
      "tools": ["get_cart", "change_delivery_date"],
      "description": "Handles technical support and order modifications",
      "handoffs": {
        "sales_agent": "For new purchases",
        "manager_agent": "For complex issues"
      }
    }
  }
}
```

## Error Handling & Edge Cases

### AutoGen Error Management:
- **API Rate Limits**: AutoGen handles with exponential backoff
- **Tool Failures**: Graceful degradation with error context
- **Agent Handoff Loops**: Termination conditions prevent infinite loops
- **Session Isolation**: Tools maintain separate state per session_id

### Contract Compliance:
- **Geographic Restrictions**: Return `status: 'failed_api_blocked'` 
- **Timeout Handling**: Respect max_turns and timeout_sec parameters
- **Tool Result Parsing**: Maintain existing `_safe_parse_tool_result()` logic
- **Speaker Naming**: Map AutoGen agents to contract speaker format

## Testing Strategy

### Component Testing:
1. **AutogenMASFactory**: Test Swarm creation with various configurations
2. **ConversationAdapter**: Test format conversion with real AutoGen outputs  
3. **AutogenConversationEngine**: Integration tests with mock scenarios

### Integration Testing:
1. **Tool Isolation**: Verify session_id separation across conversations
2. **Handoff Flow**: Test agent-to-agent and agent-to-client handoffs
3. **Contract Compliance**: Ensure output matches existing format exactly
4. **Performance**: Compare with existing ConversationEngine benchmarks

## Migration Path

### Phase 1: Implementation
- Create AutogenMASFactory and ConversationAdapter classes
- Implement AutogenConversationEngine with basic functionality
- Add comprehensive unit tests

### Phase 2: Integration
- Integrate with existing BatchProcessor
- Test with real SystemPromptSpecification files
- Validate tool session isolation

### Phase 3: Deployment
- A/B testing against existing ConversationEngine
- Performance monitoring and optimization
- Gradual rollout with fallback capability

## Conclusion

This architecture leverages AutoGen's sophisticated Swarm pattern while maintaining full compatibility with the existing ConversationEngine contract. The design separates concerns appropriately, ensures testability, and provides a clear migration path from the current implementation.

The key advantages are:
- **Reduced Complexity**: AutoGen handles agent coordination, memory, and error handling
- **Production Ready**: Swarm pattern is designed for production multi-agent systems
- **Maintainable**: Clear separation between service logic and infrastructure
- **Flexible**: Configurable user handoff targets and termination conditions
- **Compatible**: Maintains existing API contracts and integration points