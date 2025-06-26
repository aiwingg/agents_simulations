# ConversationEngine Contract Documentation

## Overview

The `ConversationEngine` is the core component that orchestrates conversations between Agent-LLM and Client-LLM systems with multi-agent support and tool calling capabilities.

## Constructor

```python
ConversationEngine(openai_wrapper: OpenAIWrapper, prompt_spec_name: str = "default_prompts")
```

**Parameters:**
- `openai_wrapper`: OpenAI API wrapper instance
- `prompt_spec_name`: Name of the prompt specification to use (defaults to "default_prompts")

## Public Methods

### 1. `run_conversation`

```python
async def run_conversation(
    scenario: Dict[str, Any], 
    max_turns: Optional[int] = None, 
    timeout_sec: Optional[int] = None
) -> Dict[str, Any]
```

**Purpose:** Run a basic conversation simulation without tools

**Input Contract:**
- `scenario`: Dictionary containing:
  - `name` (str): Scenario identifier
  - `variables` (Dict): Scenario variables including:
    - `SEED` (optional): Random seed for deterministic results
    - `client_id` (optional): Client ID for webhook data enrichment
    - Template variables for prompt formatting

**Output Contract:**
```python
{
    'session_id': str,           # Unique session identifier
    'scenario': str,             # Scenario name
    'status': str,               # 'completed' | 'failed'
    'total_turns': int,          # Number of conversation turns
    'duration_seconds': float,   # Conversation duration
    'conversation_history': List[Dict],  # Turn-by-turn conversation
    'start_time': str,           # ISO timestamp
    'end_time': str,             # ISO timestamp
    'error': str (optional),     # Error message if failed
    'error_type': str (optional) # Error type if failed
}
```

### 2. `run_conversation_with_tools`

```python
async def run_conversation_with_tools(
    scenario: Dict[str, Any], 
    max_turns: Optional[int] = None, 
    timeout_sec: Optional[int] = None
) -> Dict[str, Any]
```

**Purpose:** Run conversation simulation with tool calling and multi-agent handoff support

**Input Contract:** Same as `run_conversation`

**Output Contract:** Same as `run_conversation` plus:
```python
{
    'tools_used': bool,  # Always True for this method
    # Conversation history entries may include:
    'tool_calls': List[Dict],    # Tool calls made during turn
    'tool_results': List[Any]    # Results from tool executions
}
```

## Detailed Data Structures

### conversation_history Structure

The `conversation_history` is a list of turn objects. Each turn has different structures depending on whether tools were used:

#### Basic Turn (no tools)
```python
{
    "turn": int,                    # Turn number (1, 2, 3, etc.)
    "speaker": str,                 # "agent" | "client" | "agent_{agent_name}"
    "content": str,                 # The actual message content
    "timestamp": str                # ISO format timestamp
}
```

#### Turn with Tool Calls
```python
{
    "turn": int,                    # Turn number
    "speaker": str,                 # "agent_{agent_name}" | "client"
    "content": str,                 # Message content (can be empty string)
    "tool_calls": List[Dict],       # List of tool call objects
    "tool_results": List[Any],      # List of parsed tool results (agent only)
    "timestamp": str                # ISO format timestamp
}
```

**Note:** Only agent turns include `tool_results`. Client turns with tool calls (like `end_call`) only have `tool_calls`.

### tool_calls Structure

Each tool call object follows this structure:

```python
{
    "id": str,                      # Unique tool call ID (e.g., "call_VP4wTiwyV1tV2W8xCPnQDhGH")
    "type": "function",             # Always "function"
    "function": {
        "name": str,                # Tool name (e.g., "rag_find_products", "handoff_support")
        "arguments": str            # JSON string of arguments
    }
}
```

#### Example from real data:
```python
{
    "id": "call_VP4wTiwyV1tV2W8xCPnQDhGH",
    "type": "function", 
    "function": {
        "name": "set_current_location",
        "arguments": "{\"location_id\":1,\"execution_message\":\"Хорошо, буду оформлять доставку на Болгарский переулок, дом одиннадцать, строение два Б.\"}"
    }
}
```

### tool_results Structure

Tool results are the parsed responses from tool executions. The structure varies by tool type:

#### Regular Tool Results
```python
# For tools like rag_find_products:
"Найденные товары: - Печень ЦБ мон. охл. Приосколье (Гофра (10 кг)) unknown price [ЦБ-00000931]"

# For tools like set_current_location:
"Адресс изменен на 347881, Ростовская обл, Гуково г, Болгарский пер, дом № 11, стр. 2 Б"
```

#### Handoff Tool Results
```python
{
    "status": "handoff_completed",
    "target_agent": "flow_manager",
    "message": "Successfully handed off conversation to flow_manager"
}
```

#### End Call Tool Results
```python
{
    "status": "call_ended",
    "reason": "conversation completed"
}
```

#### Error Results
```python
{
    "error": "Tool execution failed: <error_message>"
}
```

### Real Example from Conversation History

```python
{
    "turn": 2,
    "speaker": "agent_agent",
    "content": "Отлично, буду оформлять доставку на Болгарский переулок...",
    "tool_calls": [
        {
            "id": "call_VP4wTiwyV1tV2W8xCPnQDhGH",
            "type": "function",
            "function": {
                "name": "set_current_location",
                "arguments": "{\"location_id\":1,\"execution_message\":\"Хорошо, буду оформлять доставку...\"}"
            }
        }
    ],
    "tool_results": [
        "Адресс изменен на 347881, Ростовская обл, Гуково г, Болгарский пер, дом № 11, стр. 2 Б"
    ],
    "timestamp": "2025-06-26T18:07:12.088764"
}
```

## Integration Points

### BatchProcessor Integration

The `BatchProcessor` uses ConversationEngine in the following pattern:

```python
# From batch_processor.py:_process_single_scenario
conversation_engine = ConversationEngine(self.openai_wrapper, job.prompt_spec_name)

if job.use_tools:
    conversation_result = await conversation_engine.run_conversation_with_tools(scenario)
else:
    conversation_result = await conversation_engine.run_conversation(scenario)
```

### Key Features

1. **Multi-Agent Support**: Automatic agent handoff via `handoff_{agent_name}` tools
2. **Variable Enrichment**: Automatic client data fetching via webhooks when `client_id` provided
3. **Tool Execution**: Integration with `ToolEmulator` for tool calling
4. **Prompt Management**: Uses `PromptSpecificationManager` for flexible prompt configurations
5. **Braintrust Tracing**: Decorated with `@traced` for observability

### Error Handling

- Geographic API restrictions: Returns `status: 'failed_api_blocked'` with graceful degradation
- Tool call failures: Logged but don't stop conversation
- Agent handoff failures: Logged with detailed context
- Timeout and turn limit enforcement

### Session Management

- Uses webhook-provided session_id when available
- Falls back to generated session_id
- Maintains agent contexts for handoffs
- Tracks conversation state across agent switches

## Implementation Details

### Speaker Naming
- In basic mode: `"agent"` and `"client"`
- In tools mode: `"agent_{self.current_agent}"` and `"client"`
- Multi-agent context: Speaker field reflects the current active agent (e.g., `"agent_nomenclature_lookup"`)

### Tool Result Parsing
Tool results go through `_safe_parse_tool_result()` which:
- Tries to parse JSON first
- Falls back to raw string if JSON parsing fails
- Always returns something (never fails)

### Content Handling
- Agent content can be empty string when only tool calls are made without additional message
- Client content is always populated
- All content fields are ensured to be non-null strings

### Multi-Agent Handoffs
- Triggered by `handoff_{target_agent}` tool calls
- Context is preserved and transferred between agents
- Conversation history is maintained across handoffs
- Each agent maintains its own message context