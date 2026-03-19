import json
import logging
from typing import Any

import aiohttp

from bot.prompts import SPAM_CLASSIFICATION_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout_seconds: int):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self.session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

    async def close(self) -> None:
        if self.session is not None and not self.session.closed:
            await self.session.close()

    async def _generate(self, prompt: str, system: str | None = None) -> str | None:
        if self.session is None or self.session.closed:
            await self.start()

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        try:
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error("Ollama request failed: status=%s body=%s", resp.status, body)
                    return None

                data = await resp.json()
                return (data.get("response") or "").strip()

        except Exception as exc:
            logger.exception("Ollama request exception: %s", exc)
            return None

    async def generate_reply(self, *, system_prompt: str, prompt: str) -> str | None:
        return await self._generate(prompt=prompt, system=system_prompt)

    async def summarize(self, prompt: str) -> str | None:
        return await self._generate(prompt=prompt)

    async def classify_message_for_spam(
        self,
        *,
        system_prompt: str,
        message_text: str,
    ) -> dict[str, Any] | None:
        try:
            prompt = SPAM_CLASSIFICATION_PROMPT_TEMPLATE.format(
                system_prompt=system_prompt,
                message_text=message_text,
            )
        except Exception:
            logger.exception("Failed to build spam classification prompt")
            return None

        response = await self._generate(prompt=prompt, system=system_prompt)
        if not response:
            return None

        try:
            payload = json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Spam classification returned non-JSON response: %r", response)
            return None

        if not isinstance(payload, dict):
            logger.warning("Spam classification returned non-object JSON: %r", payload)
            return None

        classification = payload.get("classification")
        confidence = payload.get("confidence")
        reason = payload.get("reason")
        should_warn = payload.get("should_warn")

        if classification not in {"CLEAN", "SUSPICIOUS", "SPAM"}:
            return None
        if not isinstance(confidence, (int, float)):
            return None
        if not isinstance(reason, str):
            return None
        if not isinstance(should_warn, bool):
            return None

        return {
            "classification": classification,
            "confidence": max(0.0, min(1.0, float(confidence))),
            "reason": reason.strip(),
            "should_warn": should_warn,
        }
