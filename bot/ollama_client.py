import logging

import aiohttp

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout_seconds: int):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self.session = aiohttp.ClientSession(timeout=self.timeout)

    async def close(self) -> None:
        if not self.session.closed:
            await self.session.close()

    async def _generate(self, prompt: str, system: str | None = None) -> str | None:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        try:
            async with self.session.post(f"{self.base_url}/api/generate", json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error("Ollama request failed: status=%s body=%s", resp.status, body)
                    return None
                data = await resp.json()
                return (data.get("response") or "").strip()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ollama request exception: %s", exc)
            return None

    async def generate_reply(self, *, system_prompt: str, prompt: str) -> str | None:
        return await self._generate(prompt=prompt, system=system_prompt)

    async def summarize(self, prompt: str) -> str | None:
        return await self._generate(prompt=prompt)
