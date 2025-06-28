# Configuration System

`config.py` centralizes environment variables and default values for the service.

## Key Variables
- `OPENAI_API_KEY` *(required)* – API token for OpenAI.
- `OPENAI_MODEL` – model name, defaults to `gpt-4o-mini`.
- `MAX_TURNS` – conversation turn limit (default `30`).
- `TIMEOUT_SEC` – timeout per conversation (default `90`).
- `CONCURRENCY` – number of parallel scenarios (default `4`).
- `MAX_INTERNAL_MESSAGES` – limits the number of internal agent-to-agent messages before termination (default `10`). A warning is logged when the variable isn’t set.
- `WEBHOOK_URL` – optional URL for session initialization.
- `RESULTS_DIR` – directory for exported results (default `results`).
- `LOGS_DIR` – directory for log files (default `logs`).
- `HOST` / `PORT` – Flask binding settings.
- `DEBUG` – enable debug mode.

## Behavior
- `Config.validate()` ensures `OPENAI_API_KEY` is provided.
- `Config.ensure_directories()` creates `RESULTS_DIR` and `LOGS_DIR` at startup.
- `Config.get_prompt_path(name)` resolves prompt files under `prompts/`.

Directory structure is created automatically under the repository root.
