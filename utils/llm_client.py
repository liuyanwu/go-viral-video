"""
OpenAI-compatible LLM client adapter.
Supports: OpenAI, Claude (via proxy), Qwen, DeepSeek, Ollama, and any
OpenAI-compatible API endpoint.
"""

import json
import time
from typing import Optional, Type, TypeVar

from openai import OpenAI, APIConnectionError, APITimeoutError, RateLimitError, APIStatusError
from pydantic import BaseModel

from config import get_config, LLMConfig
from utils.logger import setup_logger
from utils.rate_limiter import RetryHandler

logger = setup_logger("LLMClient")

T = TypeVar("T", bound=BaseModel)

_RETRYABLE_STATUS_CODES = {429, 502, 503, 504}


def _is_retryable(exc: Exception) -> bool:
    """Return True if the exception is a transient/retryable error."""
    if isinstance(exc, (APIConnectionError, APITimeoutError)):
        return True
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, APIStatusError) and exc.status_code in _RETRYABLE_STATUS_CODES:
        return True
    return False


class LLMClient:
    """
    Provider-agnostic LLM client using the OpenAI SDK.

    Supports structured JSON output via Pydantic models.
    """

    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
    ):
        cfg = config or get_config().llm
        self.model = cfg.model
        self.max_tokens = cfg.max_tokens
        self.temperature = cfg.temperature
        self._timeout = timeout
        self._max_retries = max_retries

        self.client = OpenAI(
            api_key=cfg.api_key,
            base_url=cfg.base_url,
            timeout=timeout,
        )
        self._retry_handler = RetryHandler(max_retries=max_retries)

    def _call_with_retry(self, func, *args, **kwargs):
        """Execute an API call with retry on transient errors."""
        last_exception = None
        for attempt in range(self._max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if _is_retryable(e) and attempt < self._max_retries:
                    delay = self._retry_handler.get_delay(attempt)
                    logger.warning(
                        "LLM call failed (attempt %d/%d): %s — retrying in %.1fs",
                        attempt + 1,
                        self._max_retries + 1,
                        e,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    raise
        raise last_exception

    def chat(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Send a chat completion request and return the text response.

        Args:
            prompt: User message.
            system: System message.
            temperature: Override default temperature.
            max_tokens: Override default max_tokens.

        Returns:
            Assistant's response text.
        """
        def _call():
            return self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
            )

        response = self._call_with_retry(_call)
        return response.choices[0].message.content.strip()

    def chat_json(
        self,
        prompt: str,
        system: str = "You are a helpful assistant. Always respond in valid JSON.",
        temperature: Optional[float] = None,
    ) -> dict:
        """
        Send a chat request expecting JSON response.

        Returns:
            Parsed JSON dict.
        """
        def _call():
            return self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature or self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
            )

        response = self._call_with_retry(_call)
        text = response.choices[0].message.content.strip()
        return json.loads(text)

    def chat_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system: str = "You are a helpful assistant. Always respond in valid JSON matching the schema.",
        temperature: Optional[float] = None,
        max_retries: int = 2,
    ) -> T:
        """
        Send a chat request and parse response into a Pydantic model.

        Args:
            prompt: User message (should include schema description).
            response_model: Pydantic model class to parse response into.
            system: System message.
            temperature: Override temperature.
            max_retries: Number of retries on validation failure.

        Returns:
            Parsed Pydantic model instance.
        """
        schema_json = json.dumps(
            response_model.model_json_schema(),
            indent=2,
            ensure_ascii=False,
        )
        full_prompt = (
            f"{prompt}\n\n"
            f"Respond in JSON matching this schema:\n"
            f"```json\n{schema_json}\n```"
        )

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                data = self.chat_json(full_prompt, system=system, temperature=temperature)
                return response_model.model_validate(data)
            except Exception as e:
                last_error = e
                logger.warning(f"chat_structured attempt {attempt+1} failed: {e}")
                if attempt < max_retries:
                    full_prompt += f"\n\nPrevious response was invalid. Please retry with exact schema."

        raise last_error


# Singleton
_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create the global LLM client singleton."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
