# Infrastructure Layer

The Infrastructure Layer provides all external system integrations and technical capabilities required by the Service Layer. This layer implements adapter patterns to isolate external dependencies and provides consistent interfaces for databases, APIs, file systems, and other infrastructure concerns. All components in this layer are focused on technical implementation details rather than business logic.

## Architecture Principles

- **Adapter Pattern**: Wraps external dependencies with consistent internal interfaces
- **Technical Focus**: Handles only infrastructure and external system concerns
- **Service Isolation**: Provides clean interfaces for Service Layer consumption
- **Dependency Management**: Manages all external API clients and connections
- **Cross-Cutting Concerns**: Implements logging, monitoring, and configuration

## Core Components

### OpenAI Wrapper
**File**: `src/openai_wrapper.py`  
**Adapts**: OpenAI API for LLM conversations and evaluations  
**Infrastructure Concerns**:
- OpenAI API client management and authentication
- Request/response formatting and error handling
- Rate limiting and retry logic implementation
- Token usage tracking and cost calculation
- Model configuration and parameter management

### Persistent Storage
**File**: `src/persistent_storage.py`  
**Adapts**: File system for batch metadata and job state persistence  
**Infrastructure Concerns**:
- File system operations for batch metadata storage
- JSON serialization and deserialization
- Directory management and file organization
- Data consistency and atomic write operations
- Storage error handling and recovery

### Result Storage
**File**: `src/result_storage.py`  
**Adapts**: File system for conversation results export and format conversion  
**Infrastructure Concerns**:
- Multi-format result export (JSON, CSV, NDJSON)
- File system operations for result persistence
- Statistical calculation and summary generation
- Cost estimation and token usage aggregation
- Result file management and cleanup

### Tool Emulator
**File**: `src/tool_emulator.py`  
**Adapts**: External tool APIs (aiwingg.com/rag) for business function simulation  
**Infrastructure Concerns**:
- HTTP client management for external tool APIs
- Request formatting and response parsing
- API authentication and session management
- Tool-specific protocol handling
- Error handling and fallback responses

### Webhook Manager
**File**: `src/webhook_manager.py`  
**Adapts**: External webhook APIs for client data retrieval and session management  
**Infrastructure Concerns**:
- HTTP client configuration and connection management
- External webhook API integration, with support for injecting scenario-specific data
- Session ID generation and tracking
- Client data transformation and mapping
- Network error handling and timeouts

### Logging Utils
**File**: `src/logging_utils.py`
**Adapts**: File system for structured logging and monitoring  
**Infrastructure Concerns**:
- Log file management and rotation
- Structured logging format implementation
- Multiple log stream management (app, conversation, API)
- Log level configuration and filtering
- Performance monitoring and metrics collection

### Autogen Model Client Factory
**File**: `src/autogen_model_client.py`
**Adapts**: OpenAIWrapper configuration into AutoGen-compatible clients
**Infrastructure Concerns**:
- Centralized OpenAI client creation
- Automatic Braintrust wrapping for observability

### Autogen MAS Factory
**File**: `src/autogen_mas_factory.py`
**Adapts**: AutoGen Swarm team creation
**Infrastructure Concerns**:
- Builds `AssistantAgent` objects from prompt specifications
- Configures agent handoffs (user external)
- Applies combined termination conditions for cost control

### Autogen Tool Factory
**File**: `src/autogen_tools.py`
**Adapts**: Tool specification into AutoGen tools with session isolation
**Infrastructure Concerns**:
- Creates tool instances bound to a conversation session
- Maps specification names to concrete `BaseTool` classes

## Configuration Management

### Environment Configuration
**File**: `src/config.py`  
**Purpose**: Centralized configuration and environment variable management  
**Infrastructure Concerns**:
- Environment variable parsing and validation
- Default value management and fallback configuration
- Configuration schema enforcement
- Directory structure initialization
- Runtime configuration validation

### Configuration Categories
- **API Configuration**: OpenAI API keys, model settings, timeout values
- **Processing Configuration**: Concurrency limits, batch sizes, retry parameters
- **Storage Configuration**: File paths, directory structures, retention policies
- **Integration Configuration**: External API endpoints, webhook URLs, authentication

## Cross-Cutting Concerns

### Error Handling Infrastructure
- **Retry Logic**: Configurable retry mechanisms for external API calls
- **Circuit Breakers**: Failure detection and recovery for external dependencies
- **Graceful Degradation**: Fallback responses when external systems are unavailable
- **Error Categorization**: Structured error classification for monitoring and debugging

### Performance Infrastructure
- **Connection Pooling**: Efficient HTTP connection management for external APIs
- **Caching Strategies**: Response caching for frequently accessed external data
- **Resource Management**: Memory and file handle management for long-running processes
- **Monitoring Integration**: Performance metrics collection and exposure

### Security Infrastructure
- **API Key Management**: Secure storage and rotation of external API credentials
- **Request Validation**: Input sanitization and validation before external API calls
- **Response Sanitization**: Output cleaning and validation from external sources
- **Audit Logging**: Security event tracking and compliance logging