from openai import APIError, APITimeoutError, AsyncOpenAI

from app.providers.base import ProviderError, parse_result


class OpenAICompatibleProvider:
    def __init__(self, api_key: str, model: str, base_url: str, mode: str, timeout: float):
        self.model = model
        self.mode = mode
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=1,
        )

    async def generate(self, instructions: str, text: str, schema: dict) -> dict:
        try:
            if self.mode == "deepseek":
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": f"{instructions}\nReturn valid JSON matching this schema: {schema}"},
                        {"role": "user", "content": text},
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=1500,
                )
                raw = response.choices[0].message.content or ""
            else:
                response = await self.client.responses.create(
                    model=self.model,
                    instructions=instructions,
                    input=text,
                    reasoning={"effort": "none"},
                    max_output_tokens=1500,
                    text={"format": {"type": "json_schema", "name": "translation_result", "strict": True, "schema": schema}},
                )
                raw = response.output_text
            return parse_result(raw)
        except (APIError, APITimeoutError, ProviderError) as exc:
            raise ProviderError("OpenAI-compatible provider request failed") from exc

