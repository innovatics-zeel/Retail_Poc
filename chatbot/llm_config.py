import os

from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI

load_dotenv()


class LLMConfig:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "groq").lower()
        self.temperature = float(os.getenv("LLM_TEMPERATURE", 0))
        self._client = None
        self._model = None

    @property
    def client(self):
        if self._client is None:
            self._client = self._initialize_client()
        return self._client

    @property
    def model(self):
        if self._model is None:
            self._model = self._resolve_model()
        return self._model

    def _initialize_client(self):
        if self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY is missing in .env")
            return OpenAI(api_key=api_key)

        if self.provider == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY is missing in .env")
            return Groq(api_key=api_key)

        raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def _resolve_model(self) -> str:
        if self.provider == "openai":
            return os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        if self.provider == "groq":
            return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

        raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
    ) -> str:
        final_temperature = temperature if temperature is not None else self.temperature

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=final_temperature,
            )
            return response.choices[0].message.content.strip()

        except Exception as exc:
            raise RuntimeError(f"LLM generation failed: {exc}") from exc


llm = LLMConfig()
