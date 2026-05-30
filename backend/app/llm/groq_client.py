"""
Groq LLM streaming client.
Sends chat messages to Groq's OpenAI-compatible API and yields tokens in real-time.
"""

import json
import httpx
from typing import AsyncGenerator
from app.config import settings


async def stream_groq_chat(messages: list[dict]) -> AsyncGenerator[str, None]:
    """
    Stream a chat completion from Groq's API, yielding tokens as they arrive.

    Args:
        messages: List of chat messages in OpenAI format:
                  [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]

    Yields:
        Individual text tokens as they stream from the model.
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.GROQ_LLM_MODEL,
                "messages": messages,
                "stream": True,
                "temperature": 0.4,
                "max_tokens": 1024,
            },
        ) as response:
            if response.status_code != 200:
                error_body = await response.aread()
                print(f"[LLM] Groq API error {response.status_code}: {error_body.decode()}")
                yield f"\n⚠️ LLM Error: {response.status_code}. Check your Groq API key and rate limits."
                return

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:]  # Strip "data: " prefix
                if payload == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    token = delta.get("content")
                    if token:
                        yield token
                except json.JSONDecodeError:
                    continue
