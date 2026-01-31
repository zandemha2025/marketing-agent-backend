"""
OpenRouter integration for LLM access.

We always use the highest quality model (Claude Opus) for everything.
This is a premium agency-level platform - quality is non-negotiable.
"""
import json
from typing import Optional, Dict, Any, List
import httpx
import logging

logger = logging.getLogger(__name__)

API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Default model - always the best
DEFAULT_MODEL = "anthropic/claude-3-opus"


class OpenRouterService:
    """
    Service for interacting with Claude Opus via OpenRouter.

    Usage:
        service = OpenRouterService(api_key="...")

        # Simple prompt
        response = await service.complete("Write a tagline for a coffee shop")

        # With system prompt
        response = await service.complete(
            prompt="Write a tagline",
            system="You are a world-class creative director at a top agency"
        )

        # Get structured JSON response
        data = await service.complete_json(
            prompt="Analyze the competitive landscape",
            system="You are a McKinsey-level strategy consultant"
        )
    """

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self.api_key = api_key
        self.model = model
        self.client = httpx.AsyncClient(timeout=180.0)  # Longer timeout for quality responses

    async def complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_mode: bool = False
    ) -> str:
        """
        Generate a completion from Claude Opus.

        Args:
            prompt: The user prompt
            system: Optional system prompt
            temperature: Creativity (0.0-1.0)
            max_tokens: Maximum response length
            json_mode: Request JSON response format

        Returns:
            The generated text
        """
        # Build messages
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # Build request body
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens:
            body["max_tokens"] = max_tokens

        if json_mode:
            body["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://marketing-agent.app",
            "X-Title": "Marketing Agent",
        }

        try:
            response = await self.client.post(
                API_URL,
                headers=headers,
                json=body
            )
            response.raise_for_status()
            data = response.json()

            return data["choices"][0]["message"]["content"]

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"OpenRouter request failed: {e}")
            raise

    async def complete_json(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3  # Lower temp for structured output
    ) -> Dict[str, Any]:
        """
        Generate a JSON response from Claude Opus.

        Args:
            prompt: The user prompt
            system: Optional system prompt (should mention JSON format)
            temperature: Creativity level

        Returns:
            Parsed JSON dictionary
        """
        # Ensure system prompt mentions JSON if not already
        if system and "json" not in system.lower():
            system = f"{system}\n\nRespond only with valid JSON."
        elif not system:
            system = "Respond only with valid JSON."

        raw = await self.complete(
            prompt=prompt,
            system=system,
            temperature=temperature,
            json_mode=True
        )

        # Clean up response (remove markdown fences if present)
        text = raw.strip()
        if text.startswith("```"):
            # Remove opening fence
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            # Remove closing fence
            if text.endswith("```"):
                text = text[:-3]

        return json.loads(text.strip())

    async def stream(
        self,
        prompt: str,
        system: str = "",
        history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ):
        """
        Stream a completion from Claude Opus.

        Args:
            prompt: The user prompt
            system: Optional system prompt
            history: Optional conversation history
            temperature: Creativity (0.0-1.0)
            max_tokens: Maximum response length

        Yields:
            Text chunks as they arrive
        """
        # Build messages
        messages = []
        if system:
            messages.append({"role": "system", "content": system})

        # Add history
        if history:
            messages.extend(history)

        messages.append({"role": "user", "content": prompt})

        # Build request body
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        if max_tokens:
            body["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://marketing-agent.app",
            "X-Title": "Marketing Agent",
        }

        try:
            async with self.client.stream(
                "POST",
                API_URL,
                headers=headers,
                json=body
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API error: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"OpenRouter streaming failed: {e}")
            raise

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Multi-turn conversation with Claude Opus.

        Args:
            messages: List of {"role": "user/assistant/system", "content": "..."}
            temperature: Creativity level
            max_tokens: Maximum response length

        Returns:
            The assistant's response
        """
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens:
            body["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://marketing-agent.app",
            "X-Title": "Marketing Agent",
        }

        response = await self.client.post(
            API_URL,
            headers=headers,
            json=body
        )
        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"]

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Convenience functions for simple usage
_service: Optional[OpenRouterService] = None


def _get_service() -> OpenRouterService:
    """Get or create the global service instance."""
    global _service
    if _service is None:
        from ...core.config import get_settings
        settings = get_settings()
        _service = OpenRouterService(api_key=settings.openrouter_api_key)
    return _service


async def llm(
    prompt: str,
    system: str = "",
    json_mode: bool = False
) -> str:
    """
    Quick LLM call using Claude Opus.

    Args:
        prompt: User prompt
        system: System prompt
        json_mode: Request JSON format

    Returns:
        Generated text
    """
    service = _get_service()
    return await service.complete(
        prompt=prompt,
        system=system,
        json_mode=json_mode
    )


async def llm_json(
    prompt: str,
    system: str = ""
) -> Dict[str, Any]:
    """
    Quick JSON LLM call using Claude Opus.

    Args:
        prompt: User prompt
        system: System prompt

    Returns:
        Parsed JSON dict
    """
    service = _get_service()
    return await service.complete_json(
        prompt=prompt,
        system=system
    )
