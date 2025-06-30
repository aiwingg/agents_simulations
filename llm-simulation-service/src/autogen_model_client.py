"""
AutogenModelClient - Infrastructure Layer
Single entry point for creating OpenAI completion clients for AutoGen usage
"""

import os
from autogen_ext.models.openai import OpenAIChatCompletionClient
from src.openai_wrapper import OpenAIWrapper
from src.logging_utils import get_logger
from braintrust import wrap_openai


class AutogenModelClientFactory:
    """
    Factory for creating OpenAI completion clients compatible with AutoGen.
    Centralizes client creation logic to avoid duplication across modules.
    """

    @staticmethod
    def create_from_openai_wrapper(openai_wrapper: OpenAIWrapper) -> OpenAIChatCompletionClient:
        """
        Creates OpenAIChatCompletionClient from existing OpenAIWrapper config.

        Args:
            openai_wrapper: Existing OpenAIWrapper instance

        Returns:
            Configured OpenAIChatCompletionClient for AutoGen usage
        """
        logger = get_logger()

        # Extract configuration from OpenAIWrapper
        api_key = openai_wrapper.client.api_key
        model = openai_wrapper.model

        # Create AutoGen-compatible client
        client = OpenAIChatCompletionClient(model=model, api_key=api_key)

        # Only enable Braintrust tracing if BRAINTRUST_API_KEY is provided
        if os.getenv("BRAINTRUST_API_KEY"):
            client._client = wrap_openai(client._client)
            logger.log_info(
                f"Created AutoGen client with Braintrust tracing enabled",
                extra_data={"model": model, "engine_type": "AutoGen", "tracing_enabled": True},
            )
        else:
            logger.log_info(
                f"Created AutoGen client without tracing",
                extra_data={"model": model, "engine_type": "AutoGen", "tracing_enabled": False},
            )

        return client
