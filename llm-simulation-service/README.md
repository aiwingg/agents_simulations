# LLM Simulation & Evaluation Service

A comprehensive service for simulating and evaluating conversations between Agent-LLM and Client-LLM systems, designed for QA teams and prompt engineers to test and optimize conversational AI systems at scale.

## Overview

This service enables reproducible, highly-parallel simulation of phone-order conversations between an Agent-LLM (sales bot) and Client-LLM (scripted customer), followed by automated evaluation using an Evaluator-LLM that provides 3-point scoring and detailed feedback.

### Key Features

- **Scalable Batch Processing**: Run thousands of conversations in parallel with configurable concurrency
- **Deterministic Testing**: Same seed + same prompt set = identical scores for reproducible results
- **Multiple Interfaces**: Both REST API and CLI for different use cases
- **Comprehensive Evaluation**: Automated scoring with detailed comments in Russian
- **Cost Tracking**: Token usage monitoring and cost estimation
- **Multiple Export Formats**: Results available in JSON, CSV, and NDJSON formats
- **Real-time Monitoring**: Progress tracking and status monitoring for batch jobs

## Architecture

The service consists of several key components:

- **Conversation Engine**: Orchestrates conversations between Agent and Client LLMs
- **Evaluator System**: Scores conversations on a 1-3 scale with detailed feedback
- **Batch Processor**: Manages parallel execution of multiple scenarios
- **Result Storage**: Handles export and reporting in multiple formats
- **REST API**: Provides HTTP endpoints for batch management
- **CLI Interface**: Command-line tools for local execution and API interaction

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
  ]
}
```

**Response:**
```json
{
  "batch_id": "uuid-string",
  "status": "launched",
  "total_scenarios": 1
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
  "total_cost_usd": 2.45,
  "total_tokens": 15420,
  "total_requests": 48,
  "average_cost_per_request": 0.051
}
```

#### List All Batches
```http
GET /batches
```

**Response:**
```json
{
  "batches": [
    {
      "batch_id": "uuid-string",
      "status": "completed",
      "total_scenarios": 10,
      "created_at": "2025-06-08T10:00:00"
    }
  ],
  "total_count": 1
}
```

## CLI Reference

### Commands

#### Run Scenarios
```bash
python simulate.py run <scenarios_file> [options]
```

**Options:**
- `--output-dir DIR`: Specify output directory for results
- `--single INDEX`: Run only the scenario at the specified index
- `--no-stream`: Disable real-time output for single scenarios

**Examples:**
```bash
# Run all scenarios in batch mode
python simulate.py run scenarios/sample_scenarios.json

# Run single scenario with streaming
python simulate.py run scenarios/sample_scenarios.json --single 0

# Run batch with custom output directory
python simulate.py run scenarios/sample_scenarios.json --output-dir ./my_results
```

#### Check Batch Status
```bash
python simulate.py status <batch_id> [options]
```

**Options:**
- `--api-url URL`: API base URL (default: http://localhost:5000)

**Example:**
```bash
python simulate.py status 12345678-1234-1234-1234-123456789abc
```

#### Fetch Results
```bash
python simulate.py fetch <batch_id> [options]
```

**Options:**
- `--output FILE`: Output file path
- `--format FORMAT`: Output format (json, csv, ndjson)
- `--api-url URL`: API base URL

**Examples:**
```bash
# Fetch as JSON to stdout
python simulate.py fetch 12345678-1234-1234-1234-123456789abc

# Save as CSV file
python simulate.py fetch 12345678-1234-1234-1234-123456789abc --format csv --output results.csv

# Fetch NDJSON format
python simulate.py fetch 12345678-1234-1234-1234-123456789abc --format ndjson --output results.ndjson
```

### Result Analysis

#### Summarize Results
```bash
python summarise_results.py <results_file> [options]
```

**Options:**
- `--format FORMAT`: Output format for summary (csv, json)
- `--output FILE`: Save summary to file
- `--histogram FILE`: Generate score distribution histogram
- `--quiet`: Suppress console output

**Examples:**
```bash
# Display summary statistics
python summarise_results.py results/batch_12345_20250608_120000.ndjson

# Generate summary with histogram
python summarise_results.py results/batch_12345_20250608_120000.csv --histogram score_dist.png

# Save summary as JSON
python summarise_results.py results/batch_12345_20250608_120000.ndjson --format json --output summary.json
```

## Deployment

### Docker Deployment

1. **Build Docker Image**
   ```bash
   docker build -t llm-simulation-service .
   ```

2. **Run Container**
   ```bash
   docker run -d \
     --name llm-sim-service \
     -p 5000:5000 \
     -e OPENAI_API_KEY=your_api_key_here \
     -e CONCURRENCY=8 \
     -v $(pwd)/results:/app/results \
     -v $(pwd)/logs:/app/logs \
     llm-simulation-service
   ```

3. **Check Health**
   ```bash
   curl http://localhost:5000/api/health
   ```

### Production Considerations

#### Performance Tuning

- **Concurrency**: Adjust `CONCURRENCY` based on your OpenAI rate limits and server capacity
- **Timeout**: Increase `TIMEOUT_SEC` for complex scenarios that may take longer
- **Model Selection**: Use `gpt-4o-mini` for cost efficiency or `gpt-4o` for higher quality

#### Monitoring

- **Logs**: Monitor application logs in the `logs/` directory
- **Health Endpoint**: Use `/api/health` for health checks
- **Cost Tracking**: Review token usage logs for cost monitoring

#### Security

- **API Key**: Never commit API keys to version control
- **Network**: Consider running behind a reverse proxy in production
- **Rate Limiting**: Implement rate limiting if exposing the API publicly

## Troubleshooting

### Common Issues

#### OpenAI API Errors

**Rate Limit Exceeded (429)**
- Reduce `CONCURRENCY` setting
- The service automatically retries with exponential backoff

**Invalid API Key**
- Verify `OPENAI_API_KEY` environment variable is set correctly
- Check API key permissions and billing status

#### Memory Issues

**Out of Memory**
- Reduce `CONCURRENCY` to lower memory usage
- Process smaller batches
- Increase available system memory

#### Conversation Timeouts

**Frequent Timeouts**
- Increase `TIMEOUT_SEC` setting
- Check network connectivity to OpenAI
- Simplify scenario complexity

### Debug Mode

Enable debug mode for detailed logging:
```bash
export DEBUG=True
python src/main.py
```

### Log Analysis

Check different log files for specific issues:
- `logs/app_*.log`: General application logs
- `logs/error_*.log`: Error-specific logs
- `logs/tokens_*.log`: Token usage and cost tracking
- `logs/conversations_*.jsonl`: Detailed conversation logs

## Performance Benchmarks

### Expected Performance

Based on testing with `gpt-4o-mini`:

| Metric | Value |
|--------|-------|
| Conversations per minute | 60-120 (concurrency=4) |
| Average conversation duration | 30-60 seconds |
| Average tokens per conversation | 800-1500 |
| Cost per conversation | $0.02-0.05 |

### Scaling Guidelines

- **Small batches (1-50 scenarios)**: Default settings work well
- **Medium batches (50-500 scenarios)**: Increase concurrency to 8-16
- **Large batches (500+ scenarios)**: Consider distributed deployment

## Contributing

### Development Setup

1. **Install Development Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install pytest black flake8
   ```

2. **Run Tests**
   ```bash
   python test_validation.py
   ```

3. **Code Formatting**
   ```bash
   black src/ *.py
   flake8 src/ *.py
   ```

### Project Structure

```
llm-simulation-service/
├── src/                    # Main application code
│   ├── config.py          # Configuration management
│   ├── main.py            # Flask application entry point
│   ├── openai_wrapper.py  # OpenAI API integration
│   ├── conversation_engine.py  # Core conversation logic
│   ├── evaluator.py       # Conversation evaluation
│   ├── batch_processor.py # Batch processing system
│   ├── result_storage.py  # Result storage and export
│   └── routes/            # API route handlers
├── prompts/               # LLM prompt templates
├── scenarios/             # Sample scenario files
├── logs/                  # Application logs
├── results/               # Generated results
├── simulate.py            # CLI interface
├── summarise_results.py   # Result analysis tool
├── test_validation.py     # Validation tests
├── Dockerfile             # Docker configuration
├── requirements.txt       # Python dependencies
└── README.md             # This documentation
```

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review application logs for error details
3. Ensure all dependencies are correctly installed
4. Verify OpenAI API key and billing status

---

*Built with ❤️ by the Manus AI team*

