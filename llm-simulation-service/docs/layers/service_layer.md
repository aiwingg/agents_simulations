# Service Layer

The Service Layer contains the core business logic for multi-agent conversation simulation and evaluation. This layer orchestrates complex workflows, manages conversation state, and coordinates between different agents while maintaining pure business logic. **No external API calls, database access, or filesystem operations are performed at this layer** - all external interactions are delegated to Infrastructure Layer adapters through well-defined port interfaces.

## Architecture Principles

- **Pure Business Logic**: Contains only domain-specific rules and workflows
- **No External Dependencies**: All external calls delegated to Infrastructure Layer
- **Port Interfaces**: External interactions only through infrastructure adapters
- **Workflow Orchestration**: Manages complex multi-step business processes
- **State Coordination**: Handles in-memory state and business rule enforcement

## Business Logic Workflows

### Multi-Agent Conversation Orchestration
The core business logic for managing conversations between multiple specialized agents with seamless handoffs:

1. **Agent Initialization**: Start conversations with default agent configuration
2. **Turn-Based Processing**: Execute agent responses with tool calling capability
3. **Handoff Logic**: Detect handoff requests and validate target agents
4. **Context Preservation**: Maintain conversation history across agent switches
5. **Tool Coordination**: Process tool calls and integrate responses into conversation flow
6. **Completion Detection**: Identify conversation end conditions and finalize results

### Batch Processing Orchestration
Coordinates parallel execution of multiple conversation scenarios with comprehensive evaluation through specialized service components:

1. **Job Management**: Validate input scenarios and initialize batch metadata
2. **Resource Management**: Control concurrent execution with configurable semaphore limits
3. **Scenario Processing**: Handle individual scenario execution with engine isolation
4. **Progress Tracking**: Monitor completion status with simplified percentage calculations
5. **Execution Orchestration**: Coordinate concurrent task creation and result aggregation
6. **Result Compilation**: Prepare complete batch results with statistics and summaries

### Conversation Evaluation Logic
Automated quality assessment workflow for conversation scoring and analysis:

1. **Conversation Analysis**: Examine dialogue structure and content quality
2. **Multi-Agent Assessment**: Evaluate handoff appropriateness and context continuity
3. **Scoring Logic**: Apply business rules for 1-3 scale scoring with detailed feedback
4. **Statistical Compilation**: Generate score distributions and success rate metrics
5. **Quality Metrics**: Calculate performance indicators across conversation batches

### Prompt and Configuration Management
Business logic for managing agent specifications and conversation configurations:

1. **Specification Validation**: Ensure agent configurations meet business requirements
2. **Agent Definition Logic**: Manage tool assignments and capability mappings
3. **Handoff Rule Enforcement**: Validate and apply agent-to-agent transfer rules
4. **Dynamic Configuration**: Support runtime specification switching for testing scenarios

## Core Components

### Conversation Engine
**File**: `src/autogen_conversation_engine.py`
**Business Logic Coverage**: Implements the ConversationEngine contract using AutoGen's Swarm pattern with external user simulation and centralized client/tool factories. Delegates variable enrichment to ScenarioVariableEnricher service for separation of concerns.

### Scenario Variable Enricher
**File**: `src/scenario_variable_enricher.py`
**Business Logic Coverage**: Handles scenario variable enrichment by integrating with the `WebhookManager`. It passes scenario-specific data (like purchase history) to the webhook for enrichment and applies default values. This component provides pure functions for these tasks, ensuring no direct external dependencies.

### Conversation Turn Manager
**File**: `src/conversation_turn_manager.py`
**Business Logic Coverage**: Executes individual conversation turns, validates agent responses and determines if the conversation should continue.

### Conversation Error Handler
**File**: `src/conversation_error_handler.py`
**Business Logic Coverage**: Centralizes formatting for timeout, API blocked and general errors, logging context-aware information.

### Conversation Loop Orchestrator
**File**: `src/conversation_loop_orchestrator.py`
**Business Logic Coverage**: Orchestrates the overall conversation loop, enforcing max turn and timeout constraints using the turn manager.

### Batch Processor
**File**: `src/batch_processor.py`  
**Business Logic Coverage**: Simplified batch job lifecycle management and coordination. Delegates complex orchestration logic to specialized service components while maintaining the public interface contract.

### Batch Orchestrator
**File**: `src/batch_orchestrator.py`
**Business Logic Coverage**: High-level batch execution coordination and concurrent task management. Creates scenario tasks, processes results with exception handling, and builds final batch summaries.

### Scenario Processor
**File**: `src/scenario_processor.py`
**Business Logic Coverage**: Individual scenario processing with complete engine isolation. Handles conversation execution, evaluation coordination, and result formatting with proper error handling for different failure modes (timeout, API blocked, general failures).

### Batch Progress Tracker
**File**: `src/batch_progress_tracker.py`
**Business Logic Coverage**: Simplified progress calculation and batch status updates. Tracks scenario completion with straightforward percentage-based progress reporting without complex sub-progress mechanisms.

### Batch Resource Manager
**File**: `src/batch_resource_manager.py`
**Business Logic Coverage**: Concurrency control through asyncio semaphore management. Provides simple, thread-safe resource allocation for scenario processing limits without complex lazy initialization.

### Conversation Evaluator
**File**: `src/evaluator.py`  
**Business Logic Coverage**: Conversation evaluation logic and quality assessment workflows. Implements scoring algorithms and statistical analysis for conversation quality.

### Prompt Specification Manager
**File**: `src/prompt_specification.py`  
**Business Logic Coverage**: Prompt and configuration management workflows. Handles agent specification validation and configuration rule enforcement.

### Tools Specification Manager
**File**: `src/tools_specification.py`
**Business Logic Coverage**: Tool definition and handoff rule management. Manages dynamic tool generation and validation logic for agent capabilities.

### Conversation Adapter
**File**: `src/conversation_adapter.py`
**Business Logic Coverage**: Translates AutoGen messages and task results to the existing conversation result format for evaluator and batch processor consumption.

### Autogen Message Parser
**File**: `src/autogen_message_parser.py`
**Business Logic Coverage**: Parses individual AutoGen messages, skipping system events and extracting tool call and result details.

### Speaker Display Name Resolver
**File**: `src/speaker_display_name_resolver.py`
**Business Logic Coverage**: Resolves human friendly display names for agents using the prompt specification.

### Tool Flush State Machine
**File**: `src/tool_flush_state_machine.py`
**Business Logic Coverage**: Matches tool call requests to execution events by ID and flushes them to text messages, handling orphaned tool events.

### Parsed Message DTO
**File**: `src/dtos/parsed_message.py`
**Business Logic Coverage**: Data transfer object returned by `AutogenMessageParser` representing a normalized message structure.

## Integration with Infrastructure Layer

### Port Interfaces
The Service Layer communicates with external systems exclusively through Infrastructure Layer port interfaces:

- **LLM Interface**: Conversation generation and evaluation processing
- **Storage Interface**: Batch metadata persistence and result storage
- **Tool Interface**: External tool call execution and response handling
- **Webhook Interface**: Dynamic client data retrieval and session management
- **Logging Interface**: Structured event logging and monitoring