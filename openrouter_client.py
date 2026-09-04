"""Small OpenRouter client used as the application's single generation boundary."""

import os
import time
from typing import Any, Dict

import requests


DEFAULT_MODEL = "qwen/qwen3-30b-a3b-instruct-2507"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class LLMProviderError(RuntimeError):
    """An error safe to translate into a user-facing AI availability message."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class LLMOutputError(LLMProviderError):
    """The provider returned no usable generated text."""


def validate_llm_output(content: Any, feature: str = "generation") -> str:
    """Reject empty, provider-error, and generic-refusal responses before UI use."""
    if not isinstance(content, str) or not content.strip():
        raise LLMOutputError("لم تُرجع خدمة الذكاء نتيجة صالحة.")

    text = content.strip()
    normalized = text.lower()
    refusal_markers = (
        "sorry, but i can't provide the information you're asking for",
        "sorry, but i cannot provide the information you're asking for",
        "i can't provide the information you're asking for",
        "i cannot provide the information you're asking for",
        "i'm sorry, but i can't",
        "i'm sorry, but i cannot",
        "لا أستطيع تقديم المعلومات التي تطلبها",
        "عذراً، لا أستطيع تقديم",
        "عذرًا، لا أستطيع تقديم",
        "لا يمكنني تقديم المعلومات التي تطلبها",
    )
    if any(marker in normalized for marker in refusal_markers):
        raise LLMOutputError("تعذر إكمال طلب الذكاء الاصطناعي.")

    if feature in {"advanced_analysis", "mindmap"} and len(text) < 20:
        raise LLMOutputError("كانت نتيجة الذكاء الاصطناعي قصيرة جداً لإكمال هذه العملية.")
    return text


class OpenRouterClient:
    """OpenAI-compatible OpenRouter client retaining the legacy ``invoke`` API."""

    def __init__(
        self,
        model: str | None = None,
        timeout_seconds: int | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ):
        self.model = model or os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)
        self.timeout_seconds = timeout_seconds or int(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "60"))
        self.max_tokens = max_tokens or int(os.getenv("OPENROUTER_MAX_TOKENS", "4096"))
        self.temperature = temperature if temperature is not None else float(
            os.getenv("OPENROUTER_TEMPERATURE", "0.1")
        )
        self.max_retries = max(0, min(int(os.getenv("OPENROUTER_MAX_RETRIES", "1")), 2))

    def _headers(self) -> Dict[str, str]:
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise LLMProviderError("لم يتم إعداد مفتاح خدمة الذكاء الاصطناعي.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AI-Conference-Research-Assistant/1.0",
        }
        referer = os.getenv("OPENROUTER_HTTP_REFERER", "").strip()
        title = os.getenv("OPENROUTER_APP_TITLE", "AI Conference Research Assistant").strip()
        if referer:
            headers["HTTP-Referer"] = referer
        if title:
            headers["X-OpenRouter-Title"] = title
        return headers

    @staticmethod
    def _safe_error(status_code: int) -> str:
        messages = {
            400: "تعذر إرسال طلب الذكاء الاصطناعي.",
            401: "تعذر التحقق من خدمة الذكاء الاصطناعي.",
            402: "خدمة الذكاء الاصطناعي غير متاحة حالياً.",
            403: "خدمة الذكاء الاصطناعي غير متاحة حالياً.",
            404: "النموذج المختار غير متاح حالياً.",
            408: "انتهت مهلة خدمة الذكاء الاصطناعي. حاول مرة أخرى.",
            413: "النص المطلوب تحليله كبير جداً لهذه العملية.",
            422: "تعذر معالجة طلب الذكاء الاصطناعي.",
            429: "خدمة الذكاء مشغولة حالياً. حاول بعد لحظات.",
        }
        return messages.get(status_code, "خدمة الذكاء غير متاحة مؤقتاً. حاول مرة أخرى.")

    def invoke(self, prompt: str, feature: str = "generation") -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise LLMOutputError("لا يوجد نص صالح لإرساله إلى خدمة الذكاء الاصطناعي.")

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        retryable_statuses = {408, 429, 500, 502, 503, 504}

        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    OPENROUTER_URL,
                    headers=self._headers(),
                    json=payload,
                    timeout=(10, self.timeout_seconds),
                )
                if response.status_code == 200:
                    try:
                        body = response.json()
                        content = body["choices"][0]["message"]["content"]
                    except (ValueError, KeyError, IndexError, TypeError) as exc:
                        raise LLMOutputError("استجابة خدمة الذكاء الاصطناعي غير صالحة.") from exc
                    return validate_llm_output(content, feature=feature)

                if response.status_code in retryable_statuses and attempt < self.max_retries:
                    time.sleep(1 + attempt)
                    continue
                raise LLMProviderError(self._safe_error(response.status_code), response.status_code)
            except requests.RequestException as exc:
                if attempt < self.max_retries:
                    time.sleep(1 + attempt)
                    continue
                raise LLMProviderError("تعذر الاتصال بخدمة الذكاء الاصطناعي. حاول مرة أخرى.") from exc

        raise LLMProviderError("خدمة الذكاء غير متاحة مؤقتاً. حاول مرة أخرى.")
