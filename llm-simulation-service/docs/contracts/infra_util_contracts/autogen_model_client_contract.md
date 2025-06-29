# AutogenModelClientFactory Contract

Centralized factory for creating AutoGen-compatible OpenAI clients with Braintrust tracing.

## Static Methods
- `create_from_openai_wrapper(openai_wrapper: OpenAIWrapper) -> OpenAIChatCompletionClient`
  - Uses the wrapper's API key and model to instantiate `OpenAIChatCompletionClient`.
  - Wraps the underlying client with `braintrust.wrap_openai` for tracing.
  - Returns the configured client instance.
