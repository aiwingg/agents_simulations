# Part 3: Error Handling

## Overview
Extract and centralize all error handling logic into a focused service. This part consolidates error detection, formatting, and graceful degradation patterns.

## Dependencies
- **Part 1 completed** - Requires ConversationContext
- Can be implemented in **parallel with Part 2**

## Components to Implement

### ConversationErrorHandler Service
**File**: `src/conversation_error_handler.py`
**Purpose**: Centralized error handling with session context
**Dependencies**: `Logger`

**Methods**:
- `__init__(logger: Logger)`
- `handle_error_by_type(error: Exception, context: ConversationContext, scenario_name: str, spec_name: str) -> Dict[str, Any]`
- `handle_api_blocked_error(error: Exception, context: ConversationContext, scenario_name: str) -> Dict[str, Any]`
- `handle_timeout_error(context: ConversationContext, scenario_name: str, timeout_sec: int) -> Dict[str, Any]`
- `handle_general_error(error: Exception, context: ConversationContext, scenario_name: str, spec_name: str) -> Dict[str, Any]`
- `_create_base_error_result(context: ConversationContext, scenario_name: str, status: str, error_msg: str, error_type: str) -> Dict[str, Any]`

### AutogenConversationEngine Integration
**File**: `src/autogen_conversation_engine.py` (partial refactor)
**Changes**:
- Add ConversationErrorHandler to constructor
- Replace scattered error handling with service calls
- Update exception handling in main method

## Testing Strategy

### Unit Tests for ConversationErrorHandler
**File**: `tests/test_conversation_error_handler.py`
**Mock Strategy**: Mock Logger only

**Test Methods**:
- `test_handle_api_blocked_error()` - Test API blocked error creates graceful result
- `test_handle_timeout_error()` - Test timeout error with partial conversation
- `test_handle_general_error()` - Test general error creates proper result
- `test_handle_error_by_type_api_blocked()` - Test error type detection routes correctly
- `test_handle_error_by_type_timeout()` - Test timeout detection routes correctly
- `test_handle_error_by_type_general()` - Test general error routing
- `test_create_base_error_result()` - Test base error result creation

### Integration Tests
**File**: `tests/test_autogen_conversation_engine_part3.py`
**Mock Strategy**: Mock Autogen Swarm to throw errors

**Test Methods**:
- `test_error_handling_integration()` - Test engine uses error handler correctly

## Implementation Steps

1. **Implement ConversationErrorHandler** - Service with all error handling methods
2. **Unit Tests** - Complete test coverage for ConversationErrorHandler
3. **Engine Integration** - Update AutogenConversationEngine to use service
4. **Integration Tests** - Test service integration works correctly
5. **Validation** - Ensure error behavior unchanged

## Files to Create/Modify

### New Files
- `src/conversation_error_handler.py`
- `tests/test_conversation_error_handler.py`
- `tests/test_autogen_conversation_engine_part3.py`

### Modified Files
- `src/autogen_conversation_engine.py`

## Success Criteria
- All existing tests pass
- Error handling behavior unchanged
- ConversationErrorHandler has complete test coverage
- Ready for Part 4 integration