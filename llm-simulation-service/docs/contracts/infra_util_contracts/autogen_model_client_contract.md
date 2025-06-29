# AutogenModelClientFactory Contract

Centralized factory for AutoGen-compatible OpenAI clients with Braintrust tracing.

## Static Methods
- `create_from_openai_wrapper(openai_wrapper: OpenAIWrapper) -> OpenAIChatCompletionClient`
  - Returns a configured client based on the wrapper and wraps it with Braintrust.
