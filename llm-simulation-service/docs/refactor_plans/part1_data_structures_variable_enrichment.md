# Part 1: Data Structures & Variable Enrichment

## Overview
This is the **foundation part** that creates the core data structures and extracts variable enrichment logic. It establishes the base types and services needed by all subsequent parts.

## Dependencies
- **None** - Can be implemented immediately
- All other parts depend on this foundation

## Components to Implement

### 1. ConversationContext Dataclass
**File**: `src/conversation_context.py`
**Purpose**: Encapsulate conversation state and configuration

**Fields**:
- `session_id: str`
- `scenario_name: str` 
- `max_turns: int`
- `timeout_sec: int`
- `start_time: float`
- `turn_count: int = 0`
- `all_messages: List[BaseChatMessage] = field(default_factory=list)`

**Methods**:
- `increment_turn() -> None`
- `add_message(message: BaseChatMessage) -> None`
- `get_elapsed_time() -> float`

### 2. TurnResult Dataclass
**File**: `src/turn_result.py`
**Purpose**: Encapsulate single conversation turn outcome

**Fields**:
- `task_result: TaskResult`
- `last_message: BaseChatMessage`
- `should_continue: bool`
- `termination_reason: Optional[str] = None`

**Properties**:
- `is_successful -> bool`

### 3. ScenarioVariableEnricher Service
**File**: `src/scenario_variable_enricher.py`
**Purpose**: Handle variable enrichment and webhook integration
**Dependencies**: `WebhookManager`, `Logger`

**Methods**:
- `__init__(webhook_manager: WebhookManager, logger: Logger)`
- `async enrich_scenario_variables(variables: Dict[str, Any], session_id: str) -> Tuple[Dict[str, Any], Optional[str]]`
- `async _fetch_client_data_if_needed(client_id: Optional[str]) -> Tuple[Optional[Dict], Optional[str]]`
- `_apply_client_data_overrides(variables: Dict[str, Any], client_data: Dict[str, Any]) -> Dict[str, Any]`
- `_apply_default_values(variables: Dict[str, Any]) -> Dict[str, Any]`
- `_create_lowercase_mappings(variables: Dict[str, Any]) -> Dict[str, Any]`

### 4. AutogenConversationEngine Integration
**File**: `src/autogen_conversation_engine.py` (partial refactor)
**Changes**:
- Add ScenarioVariableEnricher to constructor
- Replace `_enrich_variables_with_client_data()` implementation with service delegation
- Update imports

## Testing Strategy

### Unit Tests for ScenarioVariableEnricher
**File**: `tests/test_scenario_variable_enricher.py`
**Mock Strategy**: Mock only `WebhookManager` and `Logger`

**Test Methods**:
- `test_enrich_variables_no_client_id()` - Test enrichment without client_id
- `test_enrich_variables_with_client_id()` - Test enrichment with webhook data
- `test_webhook_failure_fallback()` - Test graceful webhook failure handling
- `test_default_value_application()` - Test default values applied correctly
- `test_variable_override_priority()` - Test webhook data overrides variables
- `test_session_id_integration()` - Test session_id properly added
- `test_lowercase_mapping_creation()` - Test uppercase→lowercase mappings
- `test_fetch_client_data_success()` - Test successful client data fetch
- `test_fetch_client_data_no_client_id()` - Test behavior when client_id is None

### Integration Tests
**File**: `tests/test_autogen_conversation_engine_part1.py`
**Mock Strategy**: Mock WebhookManager only

**Test Methods**:
- `test_variable_enrichment_integration()` - Test engine uses enricher correctly

## Implementation Steps

1. **Create Data Structures** - ConversationContext and TurnResult dataclasses
2. **Implement ScenarioVariableEnricher** - Service with all enrichment methods
3. **Unit Tests** - Complete test coverage for ScenarioVariableEnricher
4. **Engine Integration** - Update AutogenConversationEngine to use service
5. **Integration Tests** - Test service integration works correctly
6. **Validation** - Ensure no regressions in existing functionality

## Files to Create/Modify

### New Files
- `src/conversation_context.py`
- `src/turn_result.py` 
- `src/scenario_variable_enricher.py`
- `tests/test_scenario_variable_enricher.py`
- `tests/test_autogen_conversation_engine_part1.py`

### Modified Files
- `src/autogen_conversation_engine.py`

## Success Criteria
- All existing tests pass
- Variable enrichment behavior unchanged
- ScenarioVariableEnricher has complete test coverage
- Foundation data structures ready for Parts 2-4