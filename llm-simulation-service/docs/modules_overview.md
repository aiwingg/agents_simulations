# Modules Overview

This document provides a comprehensive mapping of all source code modules to their architectural layers, giving newcomers a quick navigation map to understand the codebase structure and find relevant documentation.

## Module-to-Layer Mapping

| Module Path | Layer | Purpose | Contract Reference |
|-------------|-------|---------|-------------------|
| **Entry Points** |
| `src/main.py` | Presentation | Flask application entry point and routing configuration | [HTTP API OpenAPI](contracts/http_api_openapi.yaml) |
| **Presentation Layer - HTTP Routes** |
| `src/routes/batch_routes.py` | Presentation | REST endpoints for batch simulation management | [HTTP API OpenAPI](contracts/http_api_openapi.yaml) |
| `src/routes/prompt_spec_routes.py` | Presentation | REST endpoints for prompt specification management | [HTTP API OpenAPI](contracts/http_api_openapi.yaml) |
| `src/routes/user.py` | Presentation | User management and authentication routes | [HTTP API OpenAPI](contracts/http_api_openapi.yaml) |
| **Service Layer - Business Logic** |
| `src/autogen_conversation_engine.py` | Service | Conversation engine based on AutoGen Swarm pattern | [Conversation Engine Contract](contracts/service_layer_contracts/conversation_engine_contract.md) |
| `src/conversation_adapter.py` | Service | Format translation between AutoGen and existing results | [ConversationAdapter Contract](contracts/service_layer_contracts/conversation_adapter_contract.md) |
| `src/autogen_message_parser.py` | Service | Parse AutoGen messages and extract tool info | [AutogenMessageParser Contract](contracts/service_layer_contracts/autogen_message_parser_contract.md) |
| `src/speaker_display_name_resolver.py` | Service | Resolve speaker display names from prompt specs | [SpeakerDisplayNameResolver Contract](contracts/service_layer_contracts/speaker_display_name_resolver_contract.md) |
| `src/tool_flush_state_machine.py` | Service | Match tool calls/results and flush to messages | [ToolFlushStateMachine Contract](contracts/service_layer_contracts/tool_flush_state_machine_contract.md) |
| `src/dtos/parsed_message.py` | Service | DTO representing parsed AutoGen message | [ParsedMessage DTO](contracts/dto/parsed_message_dto.md) |
| `src/batch_processor.py` | Service | Parallel batch processing and workflow coordination | [Batch Processor Contract](contracts/service_layer_contracts/batch_processor_contract.md) |
| `src/evaluator.py` | Service | Conversation scoring and quality assessment logic | [Evaluator Contract](contracts/service_layer_contracts/evaluator_contract.md) |
| `src/prompt_specification.py` | Service | Agent configuration and prompt management logic | [Prompt Specification Contract](contracts/specification_contracts/prompt_specification_contract.md) |
| `src/tools_specification.py` | Service | Tool definition and handoff rule management | [Tools Specification Contract](contracts/specification_contracts/tools_specification_contract.md) |
| **Infrastructure Layer - External Adapters** |
| `src/openai_wrapper.py` | Infrastructure | OpenAI API adapter for LLM interactions | [OpenAI Wrapper Contract](contracts/infra_util_contracts/openai_wrapper_contract.md) |
| `src/autogen_model_client.py` | Infrastructure | Creates AutoGen-compatible clients | [AutogenModelClientFactory Contract](contracts/infra_util_contracts/autogen_model_client_contract.md) |
| `src/autogen_mas_factory.py` | Infrastructure | Builds Swarm teams from specifications | [AutogenMASFactory Contract](contracts/infra_util_contracts/autogen_mas_factory_contract.md) |
| `src/autogen_tools.py` | Infrastructure | Session-aware tool factory and classes | [AutogenToolFactory Contract](contracts/infra_util_contracts/autogen_tool_factory_contract.md) |
| `src/persistent_storage.py` | Infrastructure | File system adapter for batch metadata persistence | [Persistent Storage Contract](contracts/storage_contracts/persistent_storage_contract.md) |
| `src/result_storage.py` | Infrastructure | File system adapter for conversation results export | [Result Storage Contract](contracts/storage_contracts/result_storage_contract.md) |
| `src/tool_emulator.py` | Infrastructure | External tool API adapter for business function simulation | [Tool Emulator Contract](contracts/infra_util_contracts/tool_emulator_contract.md) |
| `src/webhook_manager.py` | Infrastructure | External webhook API adapter for client data retrieval | [Webhook Manager Contract](contracts/infra_util_contracts/webhook_manager_contract.md) |
| `src/logging_utils.py` | Infrastructure | Structured logging and monitoring infrastructure | [Logging Utils Contract](contracts/infra_util_contracts/logging_utils_contract.md) |
| `src/config.py` | Infrastructure | Environment configuration and settings management | [Configuration System](configuration/config_system.md) |

## Layer Summary

### Presentation Layer (3 modules)
**Purpose**: HTTP API endpoints and request/response handling  
**Characteristics**: 
- No business logic or external dependencies
- Input validation and response formatting only
- Delegates all processing to Service Layer

**Key Modules**:
- Route handlers (`batch_routes.py`, `prompt_spec_routes.py`, `user.py`)
- Application entry point (`main.py`)

### Service Layer (10 modules)
**Purpose**: Core business logic and workflow orchestration  
**Characteristics**:
- Pure business logic with no external system access
- Coordinates complex multi-step workflows
- Communicates with Infrastructure Layer through port interfaces

**Key Modules**:
- Conversation engine (`autogen_conversation_engine.py`)
- Conversation adapter (`conversation_adapter.py`)
- Message parsing (`autogen_message_parser.py`)
- Display name resolution (`speaker_display_name_resolver.py`)
- Tool flush state machine (`tool_flush_state_machine.py`)
- Batch processing coordination (`batch_processor.py`)
- Quality assessment (`evaluator.py`)
- Configuration management (`prompt_specification.py`, `tools_specification.py`)

### Infrastructure Layer (10 modules)
**Purpose**: External system integration and technical concerns  
**Characteristics**:
- Adapts external APIs, file systems, and databases
- Provides consistent interfaces for Service Layer consumption
- Handles all cross-cutting technical concerns

**Key Modules**:
- External API adapters (`openai_wrapper.py`, `autogen_model_client.py`, `webhook_manager.py`)
- Swarm team factory (`autogen_mas_factory.py`)
- Tool factory and classes (`autogen_tools.py`)
- Storage adapters (`persistent_storage.py`, `result_storage.py`)
- Technical infrastructure (`logging_utils.py`, `config.py`)
- Tool emulator (`tool_emulator.py`)
- Data models (`models/user.py`)

## Navigation Guide

### For New Developers
1. **Start with README.md** - Understand overall architecture and purpose
2. **Review Layer Documentation** - Read relevant layer documentation:
   - [Presentation Layer](layers/presentation_layer.md)
   - [Service Layer](layers/service_layer.md) 
   - [Infrastructure Layer](layers/infrastructure_layer.md)
3. **Explore Module Contracts** - Dive into specific module contracts for detailed interfaces
4. **Check Configuration** - Review [Configuration System](configuration/config_system.md)

### For API Integration
1. **HTTP API Reference** - [OpenAPI Specification](contracts/http_api_openapi.yaml)
2. **Presentation Layer** - [HTTP endpoint documentation](layers/presentation_layer.md)
3. **Deployment Guide** - [Setup and deployment instructions](deployment/deployment_guide.md)

### For Business Logic Changes
1. **Service Layer Overview** - [Business logic documentation](layers/service_layer.md)
2. **Specific Service Contracts** - Module-specific contract documentation
3. **Configuration Management** - [Prompt and tool specifications](configuration/config_system.md)

### For Infrastructure Changes
1. **Infrastructure Layer** - [External integration documentation](layers/infrastructure_layer.md)
2. **Storage Contracts** - Data persistence and export contracts
3. **Utility Contracts** - Logging, monitoring, and cross-cutting concerns

### Result Formats
Conversation and batch results include a `status` field indicating completion state.
Possible values are `completed`, `failed`, `failed_api_blocked`, and `timeout`.
Timeout conversations still receive a score and comment from the evaluator when processed in a batch.

## Module Dependencies

### Dependency Flow
```
Presentation → Service → Infrastructure → External Systems
```

### Key Dependency Rules
- **Presentation Layer**: Can only depend on Service Layer modules
- **Service Layer**: Can only depend on Infrastructure Layer interfaces (not implementations)
- **Infrastructure Layer**: Can depend on external libraries and systems
- **No Circular Dependencies**: Layers cannot depend on higher layers

### Import Guidelines
- Presentation modules import from `src/batch_processor`, `src/prompt_specification`
- Service modules import from infrastructure interfaces only
- Infrastructure modules import external libraries and lower-level utilities
- Configuration (`src/config.py`) is imported across all layers