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
Coordinates parallel execution of multiple conversation scenarios with comprehensive evaluation:

1. **Job Creation**: Validate input scenarios and initialize batch metadata
2. **Concurrent Execution**: Manage parallel conversation processing with configurable limits
3. **Progress Coordination**: Track completion status across multiple conversations
4. **Result Aggregation**: Collect conversation outputs and organize for evaluation
5. **Quality Assessment**: Coordinate conversation scoring and feedback generation
6. **Final Compilation**: Prepare complete batch results with statistics and summaries

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
**File**: `src/conversation_engine.py`
**Business Logic Coverage**: Multi-agent conversation orchestration, handoff logic, and tool coordination workflows. Manages agent context switching and conversation flow control.

### Autogen Conversation Engine
**File**: `src/autogen_conversation_engine.py`
**Business Logic Coverage**: AutoGen-based implementation of the ConversationEngine contract. Uses Swarm teams, external user simulation, and centralized client/tool factories.

### Batch Processor
**File**: `src/batch_processor.py`  
**Business Logic Coverage**: Batch processing orchestration and result compilation workflows. Coordinates parallel execution and progress tracking across multiple scenarios.

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

## Integration with Infrastructure Layer

### Port Interfaces
The Service Layer communicates with external systems exclusively through Infrastructure Layer port interfaces:

- **LLM Interface**: Conversation generation and evaluation processing
- **Storage Interface**: Batch metadata persistence and result storage
- **Tool Interface**: External tool call execution and response handling
- **Webhook Interface**: Dynamic client data retrieval and session management
- **Logging Interface**: Structured event logging and monitoring