from guillotina import app_settings
from typing import Dict
from typing import List
from typing import Optional

import logging
import os


logger = logging.getLogger("guillotina")


class LLMProvider:
    """
    Wrapper around LiteLLM for Guillotina-specific needs.
    Handles configuration, error handling, and provider management.
    """

    def __init__(self):
        self._check_litellm_available()

    @property
    def settings(self):
        return app_settings.get("ai_query", {})

    def _check_litellm_available(self):
        """Check if LiteLLM is available, raise helpful error if not."""
        try:
            import litellm
            self.litellm = litellm
        except ImportError:
            raise ImportError(
                "LiteLLM is required for ai_query. Install it with: pip install litellm"
            )

    def get_model_name(self) -> str:
        """Get the full model name in LiteLLM format."""
        provider = self.settings.get("provider", "openai")
        model = self.settings.get("model", "gpt-4o-mini")

        if "/" in model:
            return model
        return f"{provider}/{model}"

    def get_api_key(self) -> Optional[str]:
        """Get API key from settings or environment."""
        api_key = self.settings.get("api_key")
        if api_key:
            return api_key

        provider = self.settings.get("provider", "openai")

        env_var_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "azure": "AZURE_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "google": "GEMINI_API_KEY",
            "ollama": None,
        }

        env_var = env_var_map.get(provider)
        if env_var:
            return os.getenv(env_var)

        return None

    def _build_completion_kwargs(
        self,
        messages: List[Dict],
        temperature: float = 0.1,
        max_tokens: int = 500,
        timeout: int = 30,
        stream: bool = False,
    ) -> dict:
        """Build kwargs for LiteLLM acompletion."""
        kwargs = {
            "model": self.get_model_name(),
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": timeout,
            "stream": stream,
        }
        api_key = self.get_api_key()
        if api_key:
            kwargs["api_key"] = api_key
        base_url = self.settings.get("base_url")
        if base_url:
            kwargs["api_base"] = base_url
        retry_config = self.settings.get("litellm_settings", {}).get("retry", {})
        if retry_config.get("attempts", 0) > 0:
            kwargs["num_retries"] = retry_config["attempts"]
        return kwargs

    def _handle_completion_error(self, e: Exception) -> None:
        """Map LLM errors to user-facing ValueError."""
        error_msg = str(e).lower()
        if "rate limit" in error_msg or "429" in error_msg:
            logger.error(f"LLM rate limit error: {e}")
            raise ValueError("Rate limit exceeded. Please try again later.")
        if "timeout" in error_msg or "timed out" in error_msg:
            logger.error(f"LLM timeout error: {e}")
            raise ValueError("Request timed out. Please try again.")
        logger.error(f"LLM provider error: {e}", exc_info=True)
        raise ValueError(f"LLM provider error: {str(e)}")

    async def completion(
        self,
        messages: List[Dict],
        temperature: float = 0.1,
        max_tokens: int = 500,
        timeout: int = 30,
    ) -> str:
        """Call LLM provider using LiteLLM unified interface."""
        kwargs = self._build_completion_kwargs(
            messages, temperature, max_tokens, timeout, stream=False
        )
        try:
            response = await self.litellm.acompletion(**kwargs)
            if not response or not response.choices:
                raise ValueError("Empty response from LLM provider")
            return response.choices[0].message.content
        except Exception as e:
            self._handle_completion_error(e)

    async def completion_stream(
        self,
        messages: List[Dict],
        temperature: float = 0.1,
        max_tokens: int = 500,
        timeout: int = 30,
    ):
        """Call LLM provider with stream=True; yields content chunks (str)."""
        kwargs = self._build_completion_kwargs(
            messages, temperature, max_tokens, timeout, stream=True
        )
        try:
            stream = await self.litellm.acompletion(**kwargs)
            if stream is None:
                raise ValueError("Empty stream from LLM provider")
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, "content") and delta.content:
                        yield delta.content
        except Exception as e:
            self._handle_completion_error(e)

    def is_enabled(self) -> bool:
        """Check if AI query is enabled."""
        return self.settings.get("enabled", True)
