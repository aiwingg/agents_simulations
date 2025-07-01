# Part 2: Turn Management

## Overview
Extract individual conversation turn handling logic into a focused service. This part handles the core conversation mechanics - executing turns, validating responses, and determining continuation.

## Dependencies
- **Part 1 completed** - Requires ConversationContext and TurnResult
- Can be implemented in **parallel with Part 3**

## Components to Implement

### ConversationTurnManager Service
**File**: `src/conversation_turn_manager.py`
**Purpose**: Handle individual conversation turns
**Dependencies**: `Logger`

**Methods**:
- `__init__(logger: Logger)`
- `async execute_turn(swarm: Swarm, user_message: str, target_agent: str, context: ConversationContext) -> TurnResult`
- `async generate_user_response(user_agent: AssistantAgent, agent_message: TextMessage) -> str`
- `_validate_agent_response(task_result: TaskResult, context: ConversationContext) -> TextMessage`
- `_determine_continuation(task_result: TaskResult, context: ConversationContext) -> Tuple[bool, Optional[str]]`

### AutogenConversationEngine Integration
**File**: `src/autogen_conversation_engine.py` (partial refactor)
**Changes**:
- Add ConversationTurnManager to constructor
- Extract turn execution logic from main conversation loop
- Update conversation loop to use ConversationTurnManager

## Testing Strategy

### Unit Tests for ConversationTurnManager
**File**: `tests/test_conversation_turn_manager.py`
**Mock Strategy**: Mock Autogen components (Swarm, AssistantAgent)

**Test Methods**:
- `test_execute_turn_success()` - Test successful turn execution
- `test_execute_turn_non_text_message()` - Test handling non-TextMessage responses
- `test_generate_user_response_success()` - Test user response generation
- `test_validate_agent_response_text_message()` - Test validation passes for TextMessage
- `test_validate_agent_response_non_text_message()` - Test validation fails appropriately
- `test_determine_continuation_natural_end()` - Test natural conversation termination
- `test_determine_continuation_max_turns()` - Test max turns termination
- `test_determine_continuation_ongoing()` - Test ongoing conversation logic

### Integration Tests
**File**: `tests/test_autogen_conversation_engine_part2.py`
**Mock Strategy**: Mock Autogen Swarm

**Test Methods**:
- `test_turn_management_integration()` - Test engine uses turn manager correctly

## Implementation Steps

1. **Implement ConversationTurnManager** - Service with all turn handling methods
2. **Unit Tests** - Complete test coverage for ConversationTurnManager
3. **Engine Integration** - Update AutogenConversationEngine to use service
4. **Integration Tests** - Test service integration works correctly
5. **Validation** - Ensure no regressions in existing functionality

## Files to Create/Modify

### New Files
- `src/conversation_turn_manager.py`
- `tests/test_conversation_turn_manager.py`
- `tests/test_autogen_conversation_engine_part2.py`

### Modified Files
- `src/autogen_conversation_engine.py`

## Success Criteria
- All existing tests pass
- Turn execution behavior unchanged
- ConversationTurnManager has complete test coverage
- Ready for Part 4 integration