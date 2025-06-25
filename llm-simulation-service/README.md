# LLM Simulation & Evaluation Service

A comprehensive service for simulating and evaluating conversations between Agent-LLM and Client-LLM systems, with support for multi-agent conversations and handoffs, designed for QA teams and prompt engineers to test and optimize conversational AI systems at scale.

## Overview

This service enables reproducible, highly-parallel simulation of phone-order conversations between multiple Agent-LLMs (sales bot, support specialist, etc.) and Client-LLM (scripted customer), followed by automated evaluation using an Evaluator-LLM that provides 3-point scoring and detailed feedback.

### Key Features

- **Multi-Agent Conversations**: Support for multiple agents with seamless handoffs during conversation
- **Scalable Batch Processing**: Run thousands of conversations in parallel with configurable concurrency
- **Deterministic Testing**: Same seed + same prompt set = identical scores for reproducible results
- **Multiple Interfaces**: Both REST API and CLI for different use cases
- **Comprehensive Evaluation**: Automated scoring with detailed comments in Russian, including multi-agent coordination assessment
- **Cost Tracking**: Token usage monitoring and cost estimation
- **Multiple Export Formats**: Results available in JSON, CSV, and NDJSON formats
- **Real-time Monitoring**: Progress tracking and status monitoring for batch jobs

## Architecture

The service consists of several key components:

- **Conversation Engine**: Orchestrates conversations between Agent and Client LLMs with multi-agent support
- **Multi-Agent Manager**: Handles agent switching and context management during handoffs
- **Evaluator System**: Scores conversations on a 1-3 scale with detailed feedback, including multi-agent coordination
- **Batch Processor**: Manages parallel execution of multiple scenarios
- **Result Storage**: Handles export and reporting in multiple formats
- **REST API**: Provides HTTP endpoints for batch management
- **CLI Interface**: Command-line tools for local execution and API interaction

## Multi-Agent Functionality

### Overview

The service supports complex multi-agent conversations where different specialized agents can handle specific parts of a conversation. For example, a sales agent can handle initial order processing, then hand off to a support specialist for technical issues, and back to the sales agent to complete the order.

### Agent Handoffs

Agent handoffs are implemented through dynamically generated tools:

1. **Handoff Definition**: Each agent can define which other agents it can hand off to in the prompt specification file
2. **Dynamic Tool Generation**: The system automatically creates `handoff_{target_agent}` tools based on the handoffs configuration
3. **Context Management**: When a handoff occurs, the system maintains conversation context and transfers it to the new agent
4. **Seamless Transitions**: The conversation continues naturally with the new agent taking over

### Configuration

#### Handoffs in Prompt Specifications

Handoffs are configured in the agent specification using the `handoffs` field:

```json
{
  "agents": {
    "agent": {
      "name": "Sales Agent",
      "prompt": "...",
      "tools": ["rag_find_products", "add_to_cart", "handoff_support"],
      "handoffs": {
        "support": "Transfer to support specialist for technical assistance"
      }
    },
    "support": {
      "name": "Support Specialist", 
      "prompt": "...",
      "tools": ["rag_find_products", "handoff_agent"],
      "handoffs": {
        "agent": "Transfer back to sales agent after resolving technical issues"
      }
    }
  }
}
```

#### Generated Handoff Tools

Based on the handoffs configuration, the system automatically generates tools:

- `handoff_support`: Created for the main agent to transfer to support
- `handoff_agent`: Created for the support agent to transfer back to the main agent

These tools have no parameters and execute immediately when called.

### Multi-Agent Conversation Flow

1. **Conversation Start**: Begins with the default agent (usually 'agent')
2. **Normal Operation**: The active agent processes client requests using its available tools
3. **Handoff Trigger**: When the active agent calls a handoff tool (e.g., `handoff_support`)
4. **Context Transfer**: The system:
   - Saves the current agent's conversation context
   - Switches to the target agent
   - Initializes the new agent with its system prompt
   - Provides conversation history for context
5. **Continued Conversation**: The new agent takes over and can use its tools
6. **Return Handoff**: The process can repeat with handoffs back to previous agents

### Example Multi-Agent Scenario

```
Client: "Hello, I need to place an order but I'm having trouble with your website"

Sales Agent (Anna): "Hello! I can help with the order. Let me transfer you to our support specialist for the website issue first."
[Calls handoff_support]

Support Agent (Dmitri): "Hi, I'm Dmitri from technical support. I understand you're having website issues. Can you tell me what specific problem you're experiencing?"

Client: [Describes technical issue]

Support Agent: "I've resolved that issue. Let me transfer you back to Anna to complete your order."
[Calls handoff_agent]

Sales Agent (Anna): "Thank you for waiting! Now let's proceed with your order. What would you like to order today?"
```

### Multi-Agent Evaluation

The evaluator has been enhanced to assess multi-agent coordination:

- **Handoff Appropriateness**: Were handoffs triggered at the right times?
- **Context Continuity**: Did agents maintain conversation context across handoffs?
- **Task Completion**: Was the overall business goal achieved despite agent switches?
- **Smooth Transitions**: Were handoffs executed smoothly without confusing the client?

## Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key
- Docker (optional, for containerized deployment)

### Installation

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd llm-simulation-service
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

3. **Run Validation Tests**
   ```bash
   python test_validation.py
   ```

### Basic Usage

#### CLI Interface

**Run a single scenario with streaming output:**
```bash
python simulate.py run scenarios/sample_scenarios.json --single 0
```

**Run a batch of scenarios:**
```bash
python simulate.py run scenarios/sample_scenarios.json
```

**Manage prompt specifications:**
```bash
# List all prompt specifications
python simulate.py prompts list

# Get specification contents
python simulate.py prompts get default_prompts --output my_spec.json

# Create new specification from file
python simulate.py prompts create my_custom_spec --from-file my_spec.json

# Duplicate existing specification
python simulate.py prompts duplicate default_prompts my_copy --display-name "My Copy" --version "1.1.0"

# Validate specification file
python simulate.py prompts validate my_spec.json

# Delete specification
python simulate.py prompts delete my_custom_spec --force
```

#### REST API

**Start the service:**
```bash
python src/main.py
```

**Launch a batch via API:**
```bash
curl -X POST http://localhost:5000/api/batches \
  -H "Content-Type: application/json" \
  -d @scenarios/sample_scenarios.json
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *required* | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model to use |
| `MAX_TURNS` | `30` | Maximum conversation turns |
| `TIMEOUT_SEC` | `90` | Conversation timeout in seconds |
| `CONCURRENCY` | `4` | Number of parallel conversations |
| `WEBHOOK_URL` | *(optional)* | URL for session initialization |
| `DEBUG` | `True` | Enable debug mode |
| `HOST` | `0.0.0.0` | Server host address |
| `PORT` | `5000` | Server port |

### Prompt Specifications

The service uses a flexible prompt specification system that allows you to define different prompts and tools for each agent in the conversation. Prompts are defined in JSON files located in the `prompts/` directory.

#### Default Prompt Specification

The service comes with a default prompt specification file `prompts/default_prompts.json` that contains the standard agent, client, and evaluator prompts converted from the original txt files.

#### Custom Prompt Specifications

You can create custom prompt specification files to test different prompts, tool configurations, or conversation scenarios.

**Prompt Specification Format:**

```json
{
  "name": "My Custom Prompts",
  "version": "1.0.0",
  "description": "Custom prompt configuration for testing",
  "agents": {
    "agent": {
      "name": "Sales Agent",
      "prompt": "Your agent system prompt here...",
      "tools": [
        "rag_find_products",
        "add_to_cart",
        "remove_from_cart",
        "get_cart",
        "change_delivery_date",
        "set_current_location",
        "call_transfer"
      ],
      "description": "Friendly sales manager"
    },
    "client": {
      "name": "Customer",
      "prompt": "Your client system prompt here...",
      "tools": ["end_call"],
      "description": "Customer calling to place an order"
    },
    "evaluator": {
      "name": "Conversation Evaluator",
      "prompt": "Your evaluator system prompt here...",
      "tools": [],
      "description": "Expert evaluator of conversation quality"
    }
  }
}
```

**Available Tools:**

- **Agent Tools:**
  - `rag_find_products` - Search for products in database
  - `add_to_cart` - Add products to shopping cart
  - `remove_from_cart` - Remove products from cart
  - `get_cart` - View current cart contents
  - `change_delivery_date` - Modify delivery date
  - `set_current_location` - Set delivery address
  - `call_transfer` - Transfer call to human operator

- **Client Tools:**
  - `end_call` - End the conversation

**Using Custom Prompt Specifications:**

1. **Create your JSON file** in the `prompts/` directory (e.g., `prompts/my_custom_prompts.json`)

2. **Via REST API:**
   ```bash
   curl -X POST http://localhost:5000/api/batches \
     -H "Content-Type: application/json" \
     -d '{
       "scenarios": [...],
       "prompt_spec_name": "my_custom_prompts"
     }'
   ```

3. **Via CLI:**
   ```bash
   python simulate.py run scenarios/sample_scenarios.json --prompt-spec my_custom_prompts
   ```

### Scenario Format

Scenarios are defined in JSON format with the following structure:

```json
[
  {
    "name": "calm_reorder",
    "variables": {
      "PERSONALITY": "спокойный",
      "AMB_LEVEL": 0,
      "PATIENCE": 2,
      "ORDER_GOAL": "[{\"name\":\"филе\", \"qty\":2, \"from_history\":true}]",
      "CURRENT_DATE": "2025-06-08 Sunday",
      "client_id": "9525751940",
      "SEED": 12345
    }
  }
]
```

#### Variable Descriptions

- **PERSONALITY**: Customer personality type (спокойный, нетерпеливый, растерянный)
- **AMB_LEVEL**: Ambiguity level (0=clear, 1=somewhat unclear, 2=confusing, 3=very confusing)
- **PATIENCE**: Patience level (0=very impatient, 3=very patient)
- **ORDER_GOAL**: JSON string describing what the customer wants to order
- **CURRENT_DATE**: Current date for the simulation
- **client_id**: Client identifier used to fetch dynamic data (locations, delivery days, purchase history)
- **SEED**: Optional random seed for deterministic results

#### Dynamic Data Retrieval

When a `client_id` is provided in the scenario, the system automatically:

1. Makes a POST request to `https://aiwingg.com/rag/webhook`
2. Sends payload: `{"call_inbound": {"from_number": "client_id"}}`
3. Extracts dynamic variables from `response.call_inbound.dynamic_variables`:
   - `location` → Used as `LOCATIONS` in prompts
   - `delivery_days` → Used as `DELIVERY_DAYS` in prompts
   - `purchase_history` → Used as `PURCHASE_HISTORY` in prompts
   - `session_id` → Used as the session identifier for all subsequent tool calls and logging

If the webhook call fails or `client_id` is not provided, fallback values are used for variables and a new session_id is generated.

#### Legacy Format Support

For backward compatibility, you can still use hardcoded values:

```json
{
  "name": "legacy_scenario",
  "variables": {
    "PERSONALITY": "спокойный",
    "AMB_LEVEL": 0,
    "PATIENCE": 2,
    "ORDER_GOAL": "[{\"name\":\"филе\", \"qty\":2}]",
    "CURRENT_DATE": "2025-06-08 Sunday",
    "LOCATIONS": "Москва, Санкт-Петербург, Екатеринбург",
    "DELIVERY_DAYS": "1-2 рабочих дня",
    "PURCHASE_HISTORY": "Ранее заказывал филе курицы 3 раза",
    "SEED": 12345
  }
}
```

## REST API Reference

### Base URL
```
http://localhost:5000/api
```

### Endpoints

#### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "LLM Simulation Service",
  "version": "1.0.0"
}
```

#### Launch Batch
```http
POST /batches
Content-Type: application/json
```

**Request Body:**
```json
{
  "scenarios": [
    {
      "name": "scenario_name",
      "variables": {
        "PERSONALITY": "спокойный",
        "AMB_LEVEL": 0,
        "PATIENCE": 2,
        "ORDER_GOAL": "[{\"name\":\"филе\", \"qty\":2}]",
        "CURRENT_DATE": "2025-06-08 Sunday"
      }
    }
  ],
  "prompt_spec_name": "default_prompts",
  "prompt_version": "v1.0",
  "use_tools": true,
  "use_autogen": false
}
```

**Optional Parameters:**
- `prompt_spec_name` (string): Name of the prompt specification file to use (default: "default_prompts")
- `prompt_version` (string): Version identifier for tracking (default: "v1.0")
- `use_tools` (boolean): Whether to enable tool calling (default: true)
- `use_autogen` (boolean): Whether to run conversations with the AutoGen library (default: false)

**Response:**
```json
{
  "batch_id": "uuid-string",
  "status": "launched",
  "total_scenarios": 1,
  "prompt_spec_name": "default_prompts",
  "prompt_version": "v1.0",
  "use_tools": true,
  "use_autogen": false
}
```

#### Get Batch Status
```http
GET /batches/{batch_id}
```

**Response:**
```json
{
  "batch_id": "uuid-string",
  "status": "completed",
  "progress": 100.0,
  "total_scenarios": 10,
  "completed_scenarios": 10,
  "failed_scenarios": 0,
  "prompt_spec_name": "default_prompts",
  "prompt_version": "v1.0",
  "use_tools": true,
  "created_at": "2025-06-08T10:00:00",
  "started_at": "2025-06-08T10:00:01",
  "completed_at": "2025-06-08T10:05:30"
}
```

#### Get Batch Results
```http
GET /batches/{batch_id}/results?format={json|csv|ndjson}
```

**JSON Response:**
```json
{
  "batch_id": "uuid-string",
  "results": [
    {
      "session_id": "session-uuid",
      "scenario": "calm_reorder",
      "status": "completed",
      "score": 3,
      "comment": "Отличное обслуживание, заказ оформлен быстро",
      "total_turns": 8,
      "duration_seconds": 45.2
    }
  ],
  "total_results": 1
}
```

#### Get Batch Summary
```http
GET /batches/{batch_id}/summary
```

**Response:**
```json
{
  "batch_id": "uuid-string",
  "total_scenarios": 10,
  "successful_scenarios": 9,
  "failed_scenarios": 1,
  "success_rate": 0.9,
  "score_statistics": {
    "mean": 2.3,
    "median": 2.0,
    "std": 0.7,
    "min": 1,
    "max": 3
  },
  "score_distribution": {
    "score_1": 1,
    "score_2": 5,
    "score_3": 4
  }
}
```

#### Get Cost Estimate
```http
GET /batches/{batch_id}/cost
```

**Response:**
```json
{
  "batch_id": "uuid-string",
  "estimated_cost_usd": 0.45,
  "tokens_used": {
    "input_tokens": 15000,
    "output_tokens": 8000,
    "total_tokens": 23000
  },
  "model": "gpt-4o-mini"
}
```

### Prompt Specification Management

The service provides comprehensive API endpoints for managing prompt specifications, allowing you to programmatically create, read, update, and delete conversation prompts and agent configurations.

#### List All Prompt Specifications
```http
GET /prompt-specs
```

**Response:**
```json
{
  "specifications": [
    {
      "name": "default_prompts",
      "display_name": "Default LLM Simulation Prompts",
      "version": "1.0.0",
      "description": "Default prompt configuration converted from original txt files with multi-agent support",
      "agents": ["agent", "support", "client", "evaluator"],
      "file_size": 12345,
      "last_modified": 1625097600.0
    },
    {
      "name": "custom_prompts",
      "display_name": "My Custom Prompts",
      "version": "2.1.0",
      "description": "Custom prompt configuration for testing",
      "agents": ["agent", "client", "evaluator"],
      "file_size": 8976,
      "last_modified": 1625184000.0
    }
  ],
  "total_count": 2
}
```

#### Get Prompt Specification Contents
```http
GET /prompt-specs/{spec_name}
```

**Response:**
```json
{
  "name": "My Custom Prompts",
  "version": "1.0.0",
  "description": "Custom prompt configuration for testing",
  "agents": {
    "agent": {
      "name": "Sales Agent",
      "prompt": "Your agent system prompt here...",
      "tools": [
        "rag_find_products",
        "add_to_cart",
        "remove_from_cart",
        "get_cart",
        "change_delivery_date",
        "set_current_location",
        "call_transfer"
      ],
      "description": "Friendly sales manager",
      "handoffs": {
        "support": "Transfer to support specialist for technical assistance"
      }
    },
    "client": {
      "name": "Customer",
      "prompt": "Your client system prompt here...",
      "tools": ["end_call"],
      "description": "Customer calling to place an order"
    },
    "evaluator": {
      "name": "Conversation Evaluator",
      "prompt": "Your evaluator system prompt here...",
      "tools": [],
      "description": "Expert evaluator of conversation quality"
    }
  }
}
```

#### Create New Prompt Specification
```http
POST /prompt-specs/{spec_name}
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "My New Prompts",
  "version": "1.0.0",
  "description": "New prompt configuration for specialized testing",
  "agents": {
    "agent": {
      "name": "Specialized Sales Agent",
      "prompt": "You are a specialized sales agent...",
      "tools": ["rag_find_products", "add_to_cart"],
      "description": "Specialized agent for specific products"
    },
    "client": {
      "name": "Customer",
      "prompt": "You are a demanding customer...",
      "tools": ["end_call"],
      "description": "Customer with specific requirements"
    },
    "evaluator": {
      "name": "Strict Evaluator",
      "prompt": "You are a strict evaluator...",
      "tools": [],
      "description": "Evaluator with high standards"
    }
  }
}
```

**Response:**
```json
{
  "message": "Prompt specification created successfully",
  "specification_name": "my_new_prompts",
  "action": "created"
}
```

#### Update Existing Prompt Specification
```http
PUT /prompt-specs/{spec_name}
Content-Type: application/json
```

Uses the same request body format as the create endpoint.

**Response:**
```json
{
  "message": "Prompt specification updated successfully",
  "specification_name": "my_new_prompts"
}
```

#### Delete Prompt Specification
```http
DELETE /prompt-specs/{spec_name}
```

**Response:**
```json
{
  "message": "Prompt specification deleted successfully",
  "specification_name": "my_new_prompts"
}
```

**Note:** The default prompt specification (`default_prompts`) cannot be deleted and will return a 403 error.

#### Validate Prompt Specification
```http
POST /prompt-specs/{spec_name}/validate
Content-Type: application/json
```

Validates a prompt specification without saving it. Uses the same request body format as the create endpoint.

**Response:**
```json
{
  "valid": true,
  "issues": [],
  "specification_name": "test_spec",
  "agents": ["agent", "client", "evaluator"]
}
```

**Response (Invalid):**
```json
{
  "valid": false,
  "issues": [
    "Missing required agent: evaluator",
    "Agent 'agent' references unknown tool: invalid_tool"
  ],
  "specification_name": "test_spec",
  "agents": ["agent", "client"]
}
```

#### Duplicate Prompt Specification
```http
POST /prompt-specs/{spec_name}/duplicate
Content-Type: application/json
```

**Request Body:**
```json
{
  "new_name": "my_duplicated_spec",
  "display_name": "My Duplicated Specification",
  "version": "1.0.0",
  "description": "Duplicated from original specification"
}
```

**Response:**
```json
{
  "message": "Prompt specification duplicated successfully",
  "source_name": "default_prompts",
  "new_name": "my_duplicated_spec"
}
```

### Error Responses

All prompt specification endpoints return consistent error responses:

**400 Bad Request:**
```json
{
  "error": "Validation error: Missing required agent: evaluator"
}
```

**403 Forbidden:**
```json
{
  "error": "Cannot delete the default prompt specification"
}
```

**404 Not Found:**
```json
{
  "error": "Prompt specification not found: non_existent_spec"
}
```

**409 Conflict:**
```json
{
  "error": "Target specification already exists: duplicate_name"
}
```

**500 Internal Server Error:**
```json
{
  "error": "Failed to save specification: disk full"
}
```

## Advanced Usage

### Programmatic Prompt Management

You can now programmatically manage prompt specifications using the API:

**Example: Creating a custom specification programmatically**
```bash
# Create a new specification
curl -X POST http://localhost:5000/api/prompt-specs/my_custom_spec \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Custom Sales Prompts",
    "version": "1.0.0",
    "description": "Optimized prompts for electronics sales",
    "agents": {
      "agent": {
        "name": "Electronics Sales Agent",
        "prompt": "You are an expert electronics sales agent...",
        "tools": ["rag_find_products", "add_to_cart", "get_cart"],
        "description": "Specialized electronics sales agent"
      },
      "client": {
        "name": "Tech Customer",
        "prompt": "You are a tech-savvy customer...",
        "tools": ["end_call"],
        "description": "Customer interested in electronics"
      },
      "evaluator": {
        "name": "Electronics Evaluator",
        "prompt": "Evaluate electronics sales conversations...",
        "tools": [],
        "description": "Specialized evaluator for electronics sales"
      }
    }
  }'

# Use the new specification in a batch
curl -X POST http://localhost:5000/api/batches \
  -H "Content-Type: application/json" \
  -d '{
    "scenarios": [...],
    "prompt_spec_name": "my_custom_spec"
  }'
```

**Example: Duplicating and modifying specifications**
```bash
# Duplicate the default specification
curl -X POST http://localhost:5000/api/prompt-specs/default_prompts/duplicate \
  -H "Content-Type: application/json" \
  -d '{
    "new_name": "modified_default",
    "display_name": "Modified Default Prompts",
    "version": "1.1.0",
    "description": "Modified version of default prompts"
  }'

# Retrieve and modify the duplicated specification
curl -X GET http://localhost:5000/api/prompt-specs/modified_default

# Update with your changes
curl -X PUT http://localhost:5000/api/prompt-specs/modified_default \
  -H "Content-Type: application/json" \
  -d '{...modified specification data...}'
```