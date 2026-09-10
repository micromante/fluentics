import httpx

from app.providers.base import ProviderError, parse_result


class GeminiProvider:
    def __init__(self, api_key: str, model: str, timeout: float):
        self.api_key = api_key
        self.model = model.removeprefix("models/")
        self.timeout = timeout

    async def generate(self, instructions: str, text: str, schema: dict) -> dict:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        body = {
            "systemInstruction": {"parts": [{"text": instructions}]},
            "contents": [{"role": "user", "parts": [{"text": text}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": schema, "maxOutputTokens": 1500},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, params={"key": self.api_key}, json=body)
                response.raise_for_status()
                raw = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            return parse_result(raw)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ProviderError) as exc:
            raise ProviderError("Gemini provider request failed") from exc

