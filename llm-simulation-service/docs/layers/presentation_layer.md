# Presentation Layer

The Presentation Layer handles all external interactions with the LLM Simulation Service, providing HTTP APIs for batch management, prompt specification control, and user operations. This layer strictly enforces the separation of concerns by handling only request/response processing, validation, and authentication—no direct business logic or external service calls are permitted.

## Architecture Principles

- **Single Responsibility**: Handle only HTTP request/response cycle
- **No Business Logic**: All complex operations delegated to Service Layer
- **No External Dependencies**: No direct calls to databases, APIs, or file systems
- **Validation Only**: Input validation and sanitization before delegation
- **Stateless**: No session state maintained at this layer

## Core Components

### Main Application Entry Point

**File**: `src/main.py`  
**Purpose**: Flask application initialization and routing configuration  
**Responsibilities**:
- Flask app setup and configuration
- CORS handling for frontend integration
- Global error handling middleware
- Route registration and URL mapping
- Health check endpoint

### HTTP Route Modules

#### Batch Management Routes
**File**: `src/routes/batch_routes.py`  
**Purpose**: Handles all batch simulation operations  

**Key Endpoints**:

- **`POST /api/batches`** - Launch new simulation batches
  - Validates scenarios list and optional parameters
  - Delegates processing to `BatchProcessor` service
  - Starts background processing thread
  - Returns batch ID and launch confirmation

- **`GET /api/batches/<batch_id>`** - Retrieve batch status and progress
  - Returns current status, progress percentage, and timing information
  - Delegates to `BatchProcessor.get_batch_status()`

- **`GET /api/batches`** - List all batch jobs
  - Returns all active batches sorted by creation time
  - Provides overview of batch statuses

- **`GET /api/batches/<batch_id>/results?format={json|csv|ndjson}`** - Export batch results
  - Supports multiple output formats (JSON, CSV, NDJSON)
  - File download for CSV/NDJSON formats
  - JSON response for structured data access

- **`GET /api/batches/<batch_id>/summary`** - Get statistical summaries
  - Provides score distribution and success rate statistics
  - Delegates to `ResultStorage.generate_summary_report()`

- **`GET /api/batches/<batch_id>/cost`** - Retrieve cost estimates
  - Returns token usage and estimated costs
  - Delegates to `ResultStorage.get_cost_estimate()`

- **`GET /api/health`** - Service health check
  - Validates configuration and dependencies
  - Returns service status and version information

#### Prompt Specification Routes
**File**: `src/routes/prompt_spec_routes.py`  
**Purpose**: Manages prompt specifications and agent configurations  

**Key Endpoints**:

- **`GET /api/prompt-specs`** - List all available specifications
  - Returns metadata for all prompt specification files
  - Includes file size and modification timestamps

- **`GET /api/prompt-specs/<spec_name>`** - Retrieve specification contents
  - Returns complete JSON specification structure
  - Validates specification exists before retrieval

- **`POST /api/prompt-specs/<spec_name>`** - Create new specifications
  - Creates new specification or updates existing one
  - Validates JSON structure and required agents
  - Returns creation/update confirmation

- **`PUT /api/prompt-specs/<spec_name>`** - Update existing specifications
  - Requires specification to already exist
  - Validates JSON structure before saving
  - Returns update confirmation

- **`DELETE /api/prompt-specs/<spec_name>`** - Remove specifications
  - Prevents deletion of default_prompts specification
  - Validates specification exists before deletion
  - Returns deletion confirmation

- **`POST /api/prompt-specs/<spec_name>/validate`** - Validate specification format
  - Validates JSON structure without saving
  - Checks for required agents and tool references
  - Returns validation results and issues list

- **`POST /api/prompt-specs/<spec_name>/duplicate`** - Duplicate specifications
  - Creates copy of existing specification with new name
  - Allows modification of metadata (name, version, description)
  - Prevents overwriting existing specifications

#### User Management Routes
**File**: `src/routes/user.py`  
**Purpose**: Handles user-related operations and basic CRUD  

**Key Endpoints**:
- **`GET /api/users`** - List all users
- **`POST /api/users`** - Create new user
- **`GET /api/users/<user_id>`** - Get user details
- **`PUT /api/users/<user_id>`** - Update user information
- **`DELETE /api/users/<user_id>`** - Delete user

## Data Transfer Objects (DTOs)

### Batch Request DTO
```json
{
  "scenarios": [
    {
      "name": "string",
      "variables": {
        "PERSONALITY": "string",
        "AMB_LEVEL": "integer",
        "PATIENCE": "integer",
        "ORDER_GOAL": "string",
        "CURRENT_DATE": "string",
        "client_id": "string (optional)",
        "SEED": "integer (optional)"
      }
    }
  ],
  "prompt_spec_name": "string (optional, default: 'default_prompts')",
  "prompt_version": "string (optional, default: 'v1.0')",
  "use_tools": "boolean (optional, default: true)"
}
```

### Batch Response DTO
```json
{
  "batch_id": "string",
  "status": "string (launched|running|completed|failed)",
  "total_scenarios": "integer",
  "completed_scenarios": "integer",
  "failed_scenarios": "integer",
  "progress": "float",
  "prompt_spec_name": "string",
  "prompt_version": "string",
  "use_tools": "boolean",
  "created_at": "string (ISO datetime)",
  "started_at": "string (ISO datetime, optional)",
  "completed_at": "string (ISO datetime, optional)"
}
```

### Prompt Specification DTO
```json
{
  "name": "string",
  "version": "string",
  "description": "string",
  "agents": {
    "agent": {
      "name": "string",
      "prompt": "string (or file:filename.txt)",
      "tools": ["string"],
      "description": "string",
      "handoffs": {
        "target_agent": "string"
      }
    },
    "client": {
      "name": "string",
      "prompt": "string (or file:filename.txt)",
              "tools": [],
      "description": "string"
    },
    "evaluator": {
      "name": "string",
      "prompt": "string (or file:filename.txt)",
      "tools": [],
      "description": "string"
    }
  }
}
```

### User DTO
```json
{
  "id": "integer",
  "username": "string",
  "email": "string"
}
```

## Request/Response Processing

#### Input Validation
- **JSON Schema Validation**: Request bodies validated for required fields and types
- **Parameter Sanitization**: URL parameters and query strings sanitized
- **File Format Validation**: Prompt specification JSON structure validation
- **Business Rule Validation**: Prevention of default specification deletion

#### Response Formatting
- **Consistent Structure**: Standardized JSON response format across all endpoints
- **Error Handling**: Structured error responses with appropriate HTTP status codes
- **Content Negotiation**: Support for JSON, CSV, and NDJSON response formats for results
- **File Downloads**: Proper MIME types and attachment headers for file exports

#### Authentication & Authorization
- **Basic Validation**: Input parameter validation and sanitization
- **Error Responses**: Consistent error format across all endpoints
- **Service Delegation**: All business logic delegated to appropriate service components

## Error Handling

### HTTP Status Codes
- **200 OK**: Successful operation
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request format or parameters
- **403 Forbidden**: Operation not allowed (e.g., deleting default specification)
- **404 Not Found**: Resource not found
- **409 Conflict**: Resource conflict (e.g., duplicate specification names)
- **500 Internal Server Error**: Server-side errors
- **503 Service Unavailable**: Health check failures

### Error Response Format
```json
{
  "error": "string",
  "current_status": "string (optional)",
  "specification_name": "string (optional)"
}
```

## Integration Points

### Service Layer Dependencies
- **BatchProcessor**: For all batch simulation operations and status management
- **PromptSpecificationManager**: For prompt specification CRUD operations
- **ResultStorage**: For result export and summary generation
- **Config**: For application configuration and environment variables

### External Integrations
- **File System**: JSON file storage for prompt specifications via service layer
- **Background Processing**: Threading for long-running batch operations
- **Logging**: Comprehensive request/response logging via LoggingUtils