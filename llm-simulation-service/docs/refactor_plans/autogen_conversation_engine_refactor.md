# AutogenConversationEngine Refactor Plan

## Overview
Refactor the bloated `AutogenConversationEngine` class by extracting distinct responsibilities into focused service classes, while maintaining the existing public interface and contracts.

## Current Problems
- `run_conversation_with_tools()`: 342 lines doing everything
- `_enrich_variables_with_client_data()`: 79 lines of mixed concerns  
- Duplicate webhook calls between session and enrichment logic
- Complex error handling scattered throughout
- Testing requires 10+ mocks for basic functionality

## New Class Structure

### 1. ScenarioVariableEnricher (NEW)
**File**: `src/scenario_variable_enricher.py`
**Purpose**: Handle variable enrichment and webhook integration
**Methods**:
- `async enrich_scenario_variables(variables: Dict, session_id: str) -> Tuple[Dict, str]`
- `_apply_client_data_overrides(variables: Dict, client_data: Dict) -> Dict`
- `_apply_default_values(variables: Dict) -> Dict`

### 2. ConversationOrchestrator (NEW)  
**File**: `src/conversation_orchestrator.py`
**Purpose**: Manage conversation loop and turn handling
**Methods**:
- `async run_conversation_loop(swarm, user_agent, initial_message: str) -> List[BaseChatMessage]` (~25 lines)
- `async _execute_conversation_turn(swarm, turn_context) -> TurnResult` (~20 lines)
- `async _process_user_response(user_agent, agent_message) -> TextMessage` (~10 lines)
- `_validate_turn_result(task_result, turn_count) -> None` (~10 lines)
- `_should_continue_conversation(turn_count: int, stop_reason: str) -> bool`

### 3. ConversationErrorHandler (NEW)
**File**: `src/conversation_error_handler.py`  
**Purpose**: Centralized error handling with consistent formats
**Methods**:
- `@staticmethod handle_api_blocked_error(...) -> Dict`
- `@staticmethod handle_timeout_error(...) -> Dict`
- `@staticmethod handle_general_error(...) -> Dict`
- `@staticmethod handle_error_by_type(error: Exception, ...) -> Dict`

### 4. AutogenConversationEngine (REFACTORED)
**File**: `src/autogen_conversation_engine.py`
**Purpose**: Simplified orchestration and coordination
**Key Changes**:
- `run_conversation_with_tools()`: 342 → ~50 lines
- Inject new services via constructor
- Share single WebhookManager instance
- Focus on high-level coordination only

## Implementation Steps

### Phase 1: Extract Services
1. Create `ScenarioVariableEnricher` with all enrichment logic
2. Create `ConversationOrchestrator` with conversation loop logic
3. Create `ConversationErrorHandler` with all error handling
4. Update `AutogenConversationEngine` to use new services

### Phase 2: Refactor Tests  
1. Create unit tests for each new service class
2. Update existing integration tests to use dependency injection
3. Simplify mocking (reduce from 10+ mocks to 2-3)
4. Keep one end-to-end test for full workflow validation

### Phase 3: Validation
1. Run existing test suite to ensure no regressions
2. Verify public interface unchanged
3. Validate contract compliance with ConversationAdapter
4. Performance testing to ensure no degradation

## Benefits
- **Single Responsibility**: Each class has one clear purpose
- **Testability**: Each component unit testable independently  
- **Maintainability**: Changes isolated to relevant service
- **Reusability**: Services can be reused in other contexts
- **Readability**: Main method drops from 342 to ~50 lines

## Contract Preservation
- Public interface unchanged (`run_conversation`, `run_conversation_with_tools`)
- Return format identical (uses existing `ConversationAdapter`)
- All existing functionality preserved
- Backward compatibility maintained