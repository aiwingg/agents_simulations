# Target AI Agent Upload

This guide explains how to upload multi-agent configurations from the LLM Simulation Service to the Target AI platform.

## Overview

The Target AI agent upload functionality allows you to automatically deploy agent configurations defined in your prompt specifications to the Target AI voice agent infrastructure. This enables seamless integration between your local prompt development and the production voice system.

## Features

- **Automatic Agent Upload**: Upload all agents from a prompt specification in a single command
- **Tool and Handoff Mapping**: Automatically convert local tool names and agent handoffs to Target AI format
- **Text Processing**: Clean up prompt text encoding using ftfy
- **Comprehensive Error Handling**: Detailed error reporting and validation
- **Dry Run Mode**: Validate configurations without performing actual uploads
- **Exclusion Handling**: Automatically excludes client and evaluator agents from upload

## Setup

### 1. Environment Configuration

Set the required environment variables in your `.env` file:

```bash
# Required
TARGET_API_KEY=your_target_ai_api_key_here

# Optional (with defaults)
TARGET_BASE_URL=https://app.targetai.ai
TARGET_COMPANY_ID=54
```

### 2. Tool Mapping Configuration

Create `prompts/target_tools_mapping.json` to map local tool names to Target AI tool IDs:

```json
{
  "rag_find_products": 606,
  "webhook": 610,
  "add_to_cart": 614,
  "remove_from_cart": 615,
  "get_cart": 616,
  "set_current_location": 617,
  "change_delivery_date": 621,
  "end_call": null
}
```

### 3. Agent Mapping Configuration

Create `prompts/target_agents_mapping.json` to map local agent names to Target AI agent IDs:

```json
{
  "ENTRY": 710,
  "INTENT_CLASSIFIER": 711,
  "CONFIRM_PRODUCT_FROM_CART": null,
  "REMOVE_FROM_CART": null,
  "PRODUCT_SELECTOR": null,
  "SEARCH_RAG": null,
  "SELECT_PACKAGING_AND_QUANTITY": null,
  "ADD_TO_CART_STAGE": null,
  "CONFIRMATION_STAGE": null,
  "GOODBYE": null
}
```

**Note**: Set agent IDs to `null` for agents that haven't been created in Target AI yet. You'll need to update these with actual IDs once the agents are created.

### 4. Install Dependencies

Ensure the `ftfy` package is installed for text processing:

```bash
pip install ftfy
```

## Usage

### Command Line Interface

Use the CLI script for uploading agents:

```bash
# Basic usage - upload from default specification
python upload_agents_to_target.py

# Upload from specific prompt specification
python upload_agents_to_target.py --spec-name multiagent_prompts

# Dry run to validate without uploading
python upload_agents_to_target.py --dry-run

# Verbose output for debugging
python upload_agents_to_target.py --verbose

# List available prompt specifications
python upload_agents_to_target.py --list-specs
```

### Programmatic Usage

You can also use the uploader directly in Python code:

```python
from src.target_agent_uploader import TargetAgentUploader
from src.prompt_specification import PromptSpecificationManager
from src.config import Config

# Load prompt specification
manager = PromptSpecificationManager()
prompt_spec = manager.load_specification("file_based_prompts")

# Initialize uploader
uploader = TargetAgentUploader(
    base_url=Config.TARGET_BASE_URL,
    company_id=Config.TARGET_COMPANY_ID,
    api_key=Config.TARGET_API_KEY,
    prompts_dir=Config.PROMPTS_DIR
)

# Upload all agents
results = uploader.upload_all_agents(prompt_spec)

# Process results
for result in results:
    if result.success:
        print(f"✅ {result.agent_name}: {result.response['id']}")
    else:
        print(f"❌ {result.agent_name}: {result.error}")
```

## Upload Process

### 1. Agent Filtering

The system automatically excludes certain agents from upload:

- **client**: User simulation agent (not needed in production)
- **evaluator**: Conversation evaluation agent (not needed in production)

### 2. Tool Conversion

Each tool in an agent's configuration is converted to Target AI format:

```python
# Local format
"tools": ["rag_find_products", "add_to_cart"]

# Converted to Target AI format
"tools": [
    {
        "type": "function",
        "name": "rag_find_products",
        "id": 606,
        "strategy": "latest",
        "calling_condition": "by_choice",
        "description": "Tool: rag_find_products",
        "version": null,
        "order_number": null
    }
]
```

### 3. Handoff Conversion

Agent handoffs are converted to agent-type tools:

```python
# Local format
"handoffs": {
    "INTENT_CLASSIFIER": "Transfer after collecting basic info"
}

# Converted to Target AI format
"tools": [
    {
        "type": "agent",
        "name": "INTENT_CLASSIFIER",
        "id": 711,
        "strategy": "latest",
        "calling_condition": "by_choice",
        "description": "Transfer after collecting basic info",
        "version": null,
        "order_number": null
    }
]
```

### 4. Text Processing

Prompts are processed with ftfy to fix encoding issues:

```python
import ftfy

# Before
prompt = "You are a helpful assistant with café text"

# After
processed_prompt = ftfy.fix_text(prompt)
```

## Configuration Files

### Target Tools Mapping

The `target_tools_mapping.json` file maps local tool names to Target AI tool IDs. You can get these IDs from the Target AI platform's tools section.

Example structure:
```json
{
  "tool_name": tool_id,
  "another_tool": null  // Use null for tools not yet created
}
```

### Target Agents Mapping

The `target_agents_mapping.json` file maps local agent names to Target AI agent IDs. Set to `null` for agents that need to be created first.

Example structure:
```json
{
  "AGENT_NAME": agent_id,
  "PENDING_AGENT": null  // Will be skipped during upload
}
```

## Error Handling

### Common Errors and Solutions

1. **Authentication Failed**
   ```
   ❌ Authentication error: Authentication failed: Invalid API key
   ```
   **Solution**: Check your `TARGET_API_KEY` environment variable

2. **Tool Not Found in Mapping**
   ```
   ❌ Tool 'unknown_tool' not found in tools mapping
   ```
   **Solution**: Add the tool to `target_tools_mapping.json` with its Target AI ID

3. **Agent Has Null ID**
   ```
   ❌ Agent 'NEW_AGENT' has null ID in mapping - needs to be configured
   ```
   **Solution**: Create the agent in Target AI first, then update the mapping with its ID

4. **Mapping File Not Found**
   ```
   ❌ Mapping error: Tools mapping file not found
   ```
   **Solution**: Create the required mapping files in the prompts directory

### Validation

Use dry run mode to validate your configuration:

```bash
python upload_agents_to_target.py --dry-run --verbose
```

This will:
- Check all environment variables
- Validate mapping files exist
- Verify all tools and agents have mappings
- Build payloads without uploading
- Report any configuration issues

## API Integration

### Request Format

The uploader makes HTTP POST requests to:
```
POST {BASE_URL}/api/agents/{COMPANY_ID}
```

With headers:
```
Content-Type: application/json
Accept: application/json
Authorization: Bearer {API_KEY}
```

### Payload Structure

Each agent is uploaded with a complete configuration payload:

```json
{
  "company_id": 54,
  "agent_id": 710,
  "version": {
    "name": "ENTRY",
    "code_name": "entry",
    "instruction": "Processed prompt text",
    "description": "Agent description",
    "arguments": {},
    "stt": {"vendor": "yandex", "language": "auto"},
    "llm": {"model": "gpt-4o-mini", "vendor": "openai"},
    "tts": {"speed": 1.2, "voice": "lera", "vendor": "yandex", "language": "ru-RU"},
    "personality": {"name": "buddy", "base_prompt": "Be friendly and helpful"},
    "background_volume": null,
    "background_id": null,
    "initiator": "agent",
    "frequency": "all",
    "voicemail_detector": "basic",
    "tool_calling_policy": "immediate",
    "chat_timeout_mins": 60,
    "voice_timeout_secs": 30,
    "tools": [/* converted tools and handoffs */],
    "simulations": []
  }
}
```

## Testing

### Unit Tests

Run unit tests for payload building logic:

```bash
pytest tests/test_target_agent_uploader.py -v
```

### Integration Tests

Run integration tests for API communication:

```bash
pytest tests/test_target_agent_uploader_integration.py -v
```

### Test Coverage

The test suite covers:
- Mapping file loading and validation
- Tool and handoff payload building
- Agent filtering (client/evaluator exclusion)
- Error handling for missing mappings
- HTTP request formatting and error responses
- Text processing with ftfy

## Best Practices

1. **Version Control**: Keep mapping files in version control to track agent/tool ID changes

2. **Incremental Updates**: Use null values in mappings for new agents/tools until they're created in Target AI

3. **Dry Run First**: Always run with `--dry-run` before actual uploads to catch configuration issues

4. **Environment Separation**: Use different company IDs for development, staging, and production environments

5. **Error Monitoring**: Check upload results and handle failures appropriately

6. **Backup**: Keep backups of working agent configurations before making changes

## Troubleshooting

### Debug Steps

1. **Check Environment Variables**
   ```bash
   echo $TARGET_API_KEY
   echo $TARGET_COMPANY_ID
   echo $TARGET_BASE_URL
   ```

2. **Validate Mapping Files**
   ```bash
   cat prompts/target_tools_mapping.json | jq .
   cat prompts/target_agents_mapping.json | jq .
   ```

3. **Test with Dry Run**
   ```bash
   python upload_agents_to_target.py --dry-run --verbose
   ```

4. **Check Network Connectivity**
   ```bash
   curl -I https://app.targetai.ai/api/health
   ```

5. **Validate API Key**
   ```bash
   curl -H "Authorization: Bearer $TARGET_API_KEY" \
        https://app.targetai.ai/api/agents/54
   ```

### Common Issues

- **Timeout Errors**: Increase timeout in uploader configuration
- **Rate Limiting**: Add delays between uploads for large agent sets
- **Encoding Issues**: Ensure prompt files are saved in UTF-8 encoding
- **Tool Conflicts**: Check that tool IDs in mapping match Target AI platform

For additional support, check the logs in the `logs/` directory for detailed error information. 