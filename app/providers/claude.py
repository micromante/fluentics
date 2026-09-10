import httpx

from app.providers.base import ProviderError, parse_result


class ClaudeProvider:
    def __init__(self, api_key: str, model: str, timeout: float):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    async def generate(self, instructions: str, text: str, schema: dict) -> dict:
        body = {
            "model": self.model,
            "max_tokens": 1500,
            "system": f"{instructions}\nReturn valid JSON matching this schema: {schema}",
            "messages": [{"role": "user", "content": text}],
        }
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=body)
                response.raise_for_status()
                raw = response.json()["content"][0]["text"]
            return parse_result(raw)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ProviderError) as exc:
            raise ProviderError("Claude provider request failed") from exc

