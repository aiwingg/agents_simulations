# AutogenConversationEngine Refactor Plan

## Overview
Refactor the bloated `AutogenConversationEngine` class by extracting distinct responsibilities into focused service classes, while maintaining the existing public interface and contracts.

## Current Problems
- `run_conversation_with_tools()`: 342 lines doing everything
- `_enrich_variables_with_client_data()`: 79 lines of mixed concerns  
- Duplicate webhook calls between session and enrichment logic
- Complex error handling scattered throughout
- Testing requires 10+ mocks for basic functionality

## Data Structures

### ConversationContext
**File**: `src/conversation_context.py`
**Purpose**: Encapsulate conversation state and configuration
```python
@dataclass
class ConversationContext:
    session_id: str
    scenario_name: str
    max_turns: int
    timeout_sec: int
    start_time: float
    turn_count: int = 0
    all_messages: List[BaseChatMessage] = field(default_factory=list)
```

### TurnResult
**File**: `src/turn_result.py`  
**Purpose**: Encapsulate single conversation turn outcome
```python
@dataclass
class TurnResult:
    task_result: TaskResult
    last_message: BaseChatMessage
    should_continue: bool
    termination_reason: Optional[str] = None
```

## New Class Structure

### 1. ScenarioVariableEnricher (NEW)
**File**: `src/scenario_variable_enricher.py`
**Purpose**: Handle variable enrichment and webhook integration
**Dependencies**: `WebhookManager`, `Logger`
**Methods**:
- `__init__(webhook_manager: WebhookManager, logger: Logger)`
- `async enrich_scenario_variables(variables: Dict[str, Any], session_id: str) -> Tuple[Dict[str, Any], Optional[str]]` (~15 lines)
- `async _fetch_client_data_if_needed(client_id: Optional[str]) -> Tuple[Optional[Dict], Optional[str]]` (~8 lines) 
- `_apply_client_data_overrides(variables: Dict[str, Any], client_data: Dict[str, Any]) -> Dict[str, Any]` (~12 lines)
- `_apply_default_values(variables: Dict[str, Any]) -> Dict[str, Any]` (~15 lines)
- `_create_lowercase_mappings(variables: Dict[str, Any]) -> Dict[str, Any]` (~8 lines)

### 2. ConversationTurnManager (NEW)
**File**: `src/conversation_turn_manager.py`
**Purpose**: Handle individual conversation turns
**Dependencies**: `Logger`
**Methods**:
- `__init__(logger: Logger)`
- `async execute_turn(swarm: Swarm, user_message: str, target_agent: str, context: ConversationContext) -> TurnResult` (~15 lines)
- `async generate_user_response(user_agent: AssistantAgent, agent_message: TextMessage) -> str` (~8 lines)
- `_validate_agent_response(task_result: TaskResult, context: ConversationContext) -> TextMessage` (~12 lines)
- `_determine_continuation(task_result: TaskResult, context: ConversationContext) -> Tuple[bool, Optional[str]]` (~10 lines)

### 3. ConversationLoopOrchestrator (NEW)  
**File**: `src/conversation_loop_orchestrator.py`
**Purpose**: Manage overall conversation flow and timeouts
**Dependencies**: `ConversationTurnManager`, `Logger`
**Methods**:
- `__init__(turn_manager: ConversationTurnManager, logger: Logger)`
- `async run_conversation_loop(swarm: Swarm, user_agent: AssistantAgent, initial_message: str, context: ConversationContext) -> ConversationContext` (~20 lines)
- `_check_conversation_timeout(context: ConversationContext) -> None` (~5 lines)
- `_should_continue_conversation(context: ConversationContext, turn_result: TurnResult) -> bool` (~8 lines)
- `_update_conversation_context(context: ConversationContext, turn_result: TurnResult) -> None` (~6 lines)

### 4. ConversationErrorHandler (NEW)
**File**: `src/conversation_error_handler.py`  
**Purpose**: Centralized error handling with session context
**Dependencies**: `Logger`
**Methods**:
- `__init__(logger: Logger)`
- `handle_error_by_type(error: Exception, context: ConversationContext, scenario_name: str, spec_name: str) -> Dict[str, Any]` (~10 lines)
- `handle_api_blocked_error(error: Exception, context: ConversationContext, scenario_name: str) -> Dict[str, Any]` (~15 lines)  
- `handle_timeout_error(context: ConversationContext, scenario_name: str, timeout_sec: int) -> Dict[str, Any]` (~12 lines)
- `handle_general_error(error: Exception, context: ConversationContext, scenario_name: str, spec_name: str) -> Dict[str, Any]` (~15 lines)
- `_create_base_error_result(context: ConversationContext, scenario_name: str, status: str, error_msg: str, error_type: str) -> Dict[str, Any]` (~12 lines)

### 5. AutogenConversationEngine (REFACTORED)
**File**: `src/autogen_conversation_engine.py`
**Purpose**: Simplified orchestration and coordination
**Key Changes**:
- `run_conversation_with_tools()`: 342 → ~35 lines (orchestration only)
- `_enrich_variables_with_client_data()`: extracted to `ScenarioVariableEnricher`
- Constructor injection of service dependencies
- Focus on high-level workflow coordination

**Refactored Structure**:
```python
class AutogenConversationEngine:
    def __init__(self, openai_wrapper: OpenAIWrapper, prompt_spec_name: str = "default_prompts"):
        # Initialize infrastructure (unchanged)
        self.openai = openai_wrapper
        self.webhook_manager = WebhookManager()
        self.logger = get_logger()
        self.prompt_spec_name = prompt_spec_name
        self.prompt_manager = PromptSpecificationManager()
        self.prompt_specification = self.prompt_manager.load_specification(prompt_spec_name)
        
        # Initialize service dependencies
        self.variable_enricher = ScenarioVariableEnricher(self.webhook_manager, self.logger)
        self.turn_manager = ConversationTurnManager(self.logger)
        self.loop_orchestrator = ConversationLoopOrchestrator(self.turn_manager, self.logger)
        self.error_handler = ConversationErrorHandler(self.logger)
    
    async def run_conversation_with_tools(self, scenario: Dict[str, Any], max_turns: Optional[int] = None, 
                                        timeout_sec: Optional[int] = None) -> Dict[str, Any]:
        """Simplified orchestration (~35 lines)"""
        # 1. Initialize conversation context
        context = self._create_conversation_context(scenario, max_turns, timeout_sec)
        
        # 2. Enrich variables and determine session
        session_id = await self._initialize_session_and_variables(scenario, context)
        
        # 3. Setup AutoGen components
        formatted_spec, swarm, user_agent = await self._setup_autogen_components(context, session_id)
        
        # 4. Execute conversation loop
        try:
            completed_context = await self.loop_orchestrator.run_conversation_loop(
                swarm, user_agent, self._get_initial_message(context), context
            )
            return self._create_success_result(completed_context, formatted_spec)
        except Exception as e:
            return self.error_handler.handle_error_by_type(e, context, scenario["name"], self.prompt_spec_name)
```

## Implementation Steps

### Phase 1: Create Data Structures
1. Create `ConversationContext` dataclass in `src/conversation_context.py`
2. Create `TurnResult` dataclass in `src/turn_result.py`  
3. Update imports in existing files to use new data structures

### Phase 2: Extract Services (Order Matters - Bottom-Up)
1. **Create `ScenarioVariableEnricher`** in `src/scenario_variable_enricher.py`
   - Extract `_enrich_variables_with_client_data()` logic
   - Break into focused methods with clear responsibilities
   - Add constructor dependency injection for WebhookManager and Logger

2. **Create `ConversationTurnManager`** in `src/conversation_turn_manager.py`
   - Extract individual turn handling logic
   - Handle message validation and user response generation
   - Add proper error handling for non-text messages

3. **Create `ConversationLoopOrchestrator`** in `src/conversation_loop_orchestrator.py` 
   - Extract conversation loop logic from main method
   - Handle timeout checking and turn coordination
   - Manage conversation context updates

4. **Create `ConversationErrorHandler`** in `src/conversation_error_handler.py`
   - Extract all error handling patterns
   - Centralize error result formatting
   - Handle different error types with appropriate responses

5. **Refactor `AutogenConversationEngine`**
   - Add service dependencies to constructor
   - Simplify `run_conversation_with_tools()` to orchestration only
   - Add helper methods for setup and result creation
   - Remove extracted logic, delegate to services

### Phase 3: Refactor Tests  

**Current Test Problems**:
- Each test requires 10+ mocks (AutogenModelClientFactory, WebhookManager, PromptSpecificationManager, etc.)
- 20+ lines of mock setup per test method
- Hard to isolate specific functionality
- Tests are fragile and unreadable

**New Test Structure**:

#### Unit Tests for Each Service Class

**ScenarioVariableEnricher Tests**:
```python
class TestScenarioVariableEnricher:
    def test_enrich_variables_no_client_id(self):
        """Test enrichment when no client_id provided - should add defaults and lowercase mappings"""
        
    def test_enrich_variables_with_client_id(self):
        """Test enrichment with client_id - should fetch and apply webhook data"""
        
    def test_webhook_failure_fallback(self):
        """Test graceful fallback when webhook call fails"""
        
    def test_default_value_application(self):
        """Test that all required default values are applied correctly"""
        
    def test_variable_override_priority(self):
        """Test webhook data overrides scenario variables correctly"""
        
    def test_session_id_integration(self):
        """Test session_id is properly added to variables"""
        
    def test_lowercase_mapping_creation(self):
        """Test uppercase variables get lowercase counterparts"""
        
    def test_fetch_client_data_success(self):
        """Test successful client data fetching"""
        
    def test_fetch_client_data_no_client_id(self):
        """Test behavior when client_id is None"""
```

**ConversationTurnManager Tests**:
```python  
class TestConversationTurnManager:
    def test_execute_turn_success(self):
        """Test successful turn execution with valid TextMessage response"""
        
    def test_execute_turn_non_text_message(self):
        """Test handling when agent returns non-TextMessage"""
        
    def test_generate_user_response_success(self):
        """Test user agent generates appropriate response"""
        
    def test_validate_agent_response_text_message(self):
        """Test validation passes for TextMessage"""
        
    def test_validate_agent_response_non_text_message(self):
        """Test validation fails for non-TextMessage"""
        
    def test_determine_continuation_natural_end(self):
        """Test continuation logic for natural conversation termination"""
        
    def test_determine_continuation_max_turns(self):
        """Test continuation logic when max turns reached"""
        
    def test_determine_continuation_ongoing(self):
        """Test continuation logic for ongoing conversation"""
```

**ConversationLoopOrchestrator Tests**:
```python
class TestConversationLoopOrchestrator:
    def test_run_conversation_loop_success(self):
        """Test successful conversation loop completion"""
        
    def test_run_conversation_loop_timeout(self):
        """Test conversation loop timeout handling"""
        
    def test_run_conversation_loop_max_turns(self):
        """Test conversation loop stops at max turns"""
        
    def test_run_conversation_loop_natural_termination(self):
        """Test conversation loop stops on natural termination"""
        
    def test_check_conversation_timeout_within_limit(self):
        """Test timeout check passes when within limit"""
        
    def test_check_conversation_timeout_exceeded(self):
        """Test timeout check raises exception when limit exceeded"""
        
    def test_should_continue_conversation_yes(self):
        """Test continuation decision when conversation should continue"""
        
    def test_should_continue_conversation_no(self):
        """Test continuation decision when conversation should stop"""
        
    def test_update_conversation_context(self):
        """Test context is updated correctly after turn"""
```

**ConversationErrorHandler Tests**:
```python
class TestConversationErrorHandler:
    def test_handle_api_blocked_error(self):
        """Test API blocked error creates proper graceful degradation result"""
        
    def test_handle_timeout_error(self):
        """Test timeout error creates proper result with partial conversation"""
        
    def test_handle_general_error(self):
        """Test general error creates proper error result"""
        
    def test_handle_error_by_type_api_blocked(self):
        """Test error type detection routes to API blocked handler"""
        
    def test_handle_error_by_type_timeout(self):
        """Test error type detection routes to timeout handler"""
        
    def test_handle_error_by_type_general(self):
        """Test error type detection routes to general handler"""
        
    def test_create_base_error_result(self):
        """Test base error result creation with all required fields"""
```

#### Integration Tests

**AutogenConversationEngine Integration Tests**:
```python
class TestAutogenConversationEngineIntegration:
    def test_service_coordination_flow(self):
        """Test services work together correctly with mocked Swarm"""
        # Mock: Autogen Swarm (swarm.run()), WebhookManager, PromptSpecificationManager
        # Test: Variable enrichment -> Loop orchestration -> Result creation
        # Verify: Service method calls, data flow, result format
        
    def test_error_handling_propagation(self):
        """Test errors are handled consistently across services"""
        # Mock: Swarm to throw specific errors (API blocked, timeout, general)
        # Test: Proper error routing to ConversationErrorHandler
        # Verify: Error result format and graceful degradation
        
    def test_public_interface_preservation(self):
        """Test refactored engine maintains exact same public interface"""
        # Mock: Swarm with successful conversation simulation
        # Test: Method signatures, return format, behavior identical
        # Verify: Contract compliance with existing tests
```

**Mock Strategy Refined**:
- **Before**: 10+ mocks per test (AutogenModelClientFactory, WebhookManager, PromptSpecificationManager, AutogenToolFactory, AutogenMASFactory, ConversationAdapter, etc.)
- **After Unit Tests**: 1-2 mocks per test (only injected service dependencies)
- **After Integration Tests**: 3-4 strategic mocks (Autogen Swarm, WebhookManager, PromptSpecificationManager, ConversationAdapter)
- **No End-to-End Tests**: Avoid complex OpenAI API mocking entirely
- **Focus**: Mock at Autogen Swarm boundary (`swarm.run()` method) which is much cleaner and more reliable

### Phase 4: Validation
1. Run existing test suite to ensure no regressions
2. Verify public interface unchanged (`run_conversation`, `run_conversation_with_tools`)
3. Validate contract compliance with ConversationAdapter
4. Performance testing to ensure no degradation (using mocked Swarm)
5. Manual testing with BatchProcessor integration (existing end-to-end tests via batch runs)

## Files to Create/Modify

### New Files
- `src/conversation_context.py` - ConversationContext dataclass
- `src/turn_result.py` - TurnResult dataclass  
- `src/scenario_variable_enricher.py` - Variable enrichment service
- `src/conversation_turn_manager.py` - Turn management service
- `src/conversation_loop_orchestrator.py` - Loop orchestration service
- `src/conversation_error_handler.py` - Error handling service

### New Test Files
- `tests/test_scenario_variable_enricher.py` - Unit tests for variable enricher
- `tests/test_conversation_turn_manager.py` - Unit tests for turn manager
- `tests/test_conversation_loop_orchestrator.py` - Unit tests for loop orchestrator  
- `tests/test_conversation_error_handler.py` - Unit tests for error handler
- `tests/test_autogen_conversation_engine_integration.py` - Integration tests

### Modified Files
- `src/autogen_conversation_engine.py` - Refactored to use services
- `tests/test_autogen_conversation_engine.py` - Updated for new architecture

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