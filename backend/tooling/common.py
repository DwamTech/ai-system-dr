from __future__ import annotations

import json
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from backend.artifacts import (
    ArtifactError, read_document_artifact, read_tool_checkpoint, write_tool_checkpoint,
)
from backend.models import DocumentArtifact


class ToolFailure(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


MAX_INPUT_CHARS = max(2000, int(os.getenv("TOOL_MODEL_INPUT_CHARS", "9000")))
MODEL_CONTENT_CHARS = max(1000, MAX_INPUT_CHARS - 1200)


@dataclass(frozen=True)
class TextChunk:
    text: str
    page_refs: tuple[int, ...]


def chunks(text: str, maximum: int | None = None) -> list[str]:
    maximum = maximum or MODEL_CONTENT_CHARS
    words = text.split()
    result, current, size = [], [], 0
    for word in words:
        next_size = size + len(word) + 1
        if current and next_size > maximum:
            result.append(" ".join(current)); current, size = [], 0
        current.append(word); size += len(word) + 1
    if current:
        result.append(" ".join(current))
    return result or [text]


def page_chunks(pages: Iterable[dict[str, Any]], maximum: int | None = None) -> list[TextChunk]:
    """Build bounded chunks without losing original PDF page references."""
    maximum = maximum or MODEL_CONTENT_CHARS
    result: list[TextChunk] = []
    for page in pages:
        page_number = int(page["number"])
        text = str(page.get("text") or "").strip()
        if not text:
            continue
        result.extend(TextChunk(part, (page_number,)) for part in chunks(text, maximum))
    return result


def extract_json(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for position, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[position:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ToolFailure("invalid_model_output", "تعذر التحقق من صيغة نتيجة النموذج.")


def invoke_json(context: "ToolContext", prompt: str, feature: str) -> dict[str, Any]:
    """Request structured output and allow exactly one bounded repair."""
    raw = context.invoke(prompt, feature)
    try:
        return extract_json(raw)
    except ToolFailure:
        repair = (
            "حوّل الناتج التالي إلى JSON صالح فقط، من دون شرح أو Markdown. "
            "لا تضف حقائق جديدة.\n<UNTRUSTED_OUTPUT>\n"
            + raw[:max(1000, MAX_INPUT_CHARS - 500)]
            + "\n</UNTRUSTED_OUTPUT>"
        )
        return extract_json(context.invoke(repair, f"{feature}_repair"))


def hierarchical_reduce(context: "ToolContext", values: list[str], instruction: str, feature: str) -> str:
    """Reduce an arbitrary number of model outputs without exceeding input bounds."""
    current = [value.strip() for value in values if value and value.strip()]
    if not current:
        raise ToolFailure("invalid_model_output", "لم ينتج النموذج محتوى صالحًا.")
    for level in range(8):
        if len(current) == 1:
            return current[0]
        groups: list[list[str]] = []
        group: list[str] = []
        size = 0
        group_budget = max(1000, MAX_INPUT_CHARS - len(instruction) - 500)
        for value in current:
            if group and size + len(value) > group_budget:
                groups.append(group)
                group, size = [], 0
            group.append(value[:group_budget])
            size += len(group[-1])
        if group:
            groups.append(group)
        reduced: list[str] = []
        for group_index, group in enumerate(groups):
            prompt = instruction + "\n<UNTRUSTED_PARTIALS>\n" + "\n\n".join(group) + "\n</UNTRUSTED_PARTIALS>"
            saved = context.checkpoint(
                feature, level * 1000 + group_index,
                lambda prompt=prompt: {"text": context.invoke(prompt, feature).strip()},
            )
            reduced.append(str(saved.get("text") or "").strip())
        current = reduced
    raise ToolFailure("invalid_model_output", "تعذر دمج أجزاء النتيجة ضمن حدود النموذج.")


def arabic_terms(text: str) -> list[tuple[str, int]]:
    normalized = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", text.casefold())
    normalized = normalized.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه"}))
    tokens = re.findall(r"[\u0621-\u064Aa-zA-Z]{3,}", normalized)
    stop = {
        "هذا", "هذه", "ذلك", "تلك", "التي", "الذي", "الذين", "على", "من", "في", "الى", "عن",
        "كان", "كانت", "كما", "قد", "تم", "the", "and", "with", "for", "from", "that", "this",
    }
    return [(term, count) for term, count in Counter(token for token in tokens if token not in stop).most_common(20)]


@dataclass
class ToolContext:
    db: Any
    job: Any
    execution: Any
    progress_callback: Callable[[int, str, str], bool]
    invoke_callback: Callable[[str, str], str]
    _last_progress: int = field(default=2, init=False)

    def progress(self, value: int, phase: str, message: str) -> None:
        self._last_progress = value
        if not self.progress_callback(value, phase, message):
            raise ToolFailure("cancelled", "تم إلغاء الطلب.")

    def invoke(self, prompt: str, feature: str) -> str:
        if not self.progress_callback(
            self._last_progress, "provider", "جارٍ معالجة الجزء الحالي بالذكاء الاصطناعي."
        ):
            raise ToolFailure("cancelled", "تم إلغاء الطلب.")
        try:
            return self.invoke_callback(prompt, feature)
        except TimeoutError as exc:
            raise ToolFailure("provider_timeout", "انتهت مهلة مزود الذكاء الاصطناعي.") from exc
        except Exception as exc:
            message = str(exc).lower()
            if "429" in message or "rate" in message:
                raise ToolFailure("provider_rate_limited", "مزود الذكاء الاصطناعي مشغول؛ أعد المحاولة لاحقًا.") from exc
            status_code = getattr(exc, "status_code", None)
            if status_code in {408, 504} or "timeout" in message or "مهلة" in message:
                raise ToolFailure("provider_timeout", "انتهت مهلة مزود الذكاء الاصطناعي.") from exc
            if status_code is not None or exc.__class__.__name__.startswith("LLM"):
                raise ToolFailure("provider_unavailable", "خدمة الذكاء الاصطناعي غير متاحة مؤقتًا.") from exc
            raise ToolFailure("internal_error", "تعذر تنفيذ الأداة الآن.") from exc

    def checkpoint(self, stage: str, item: int, compute: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        """Return a saved provider step or compute and atomically save it once.

        A recovered job keeps its id, so a worker restart resumes at the first
        missing step instead of paying for provider calls that already finished.
        """
        try:
            saved = read_tool_checkpoint(self.execution.owner_id, self.job.id, stage, item)
            if saved is not None:
                return saved
            value = compute()
            if not isinstance(value, dict):
                raise ToolFailure("invalid_model_output", "تعذر التحقق من ناتج مرحلة الأداة.")
            write_tool_checkpoint(self.execution.owner_id, self.job.id, stage, item, value)
            return value
        except ArtifactError as exc:
            raise ToolFailure("result_storage_failed", "تعذر حفظ تقدم الأداة بصورة آمنة.") from exc

    def checkpoint_text(self, stage: str, item: int, prompt: str, feature: str) -> str:
        value = self.checkpoint(stage, item, lambda: {"text": self.invoke(prompt, feature).strip()})
        text = str(value.get("text") or "").strip()
        if not text:
            raise ToolFailure("invalid_model_output", "أعاد مزود الذكاء الاصطناعي نتيجة فارغة.")
        return text

    def checkpoint_json(self, stage: str, item: int, prompt: str, feature: str) -> dict[str, Any]:
        return self.checkpoint(stage, item, lambda: invoke_json(self, prompt, feature))

    def document(self, version_id: str) -> dict[str, Any]:
        artifact = self.db.get(DocumentArtifact, version_id)
        if not artifact or artifact.status != "ready" or not artifact.storage_key or not artifact.checksum:
            raise ToolFailure("document_not_ready", "محتوى المستند ما زال قيد التجهيز.")
        try:
            return read_document_artifact(artifact.storage_key, artifact.checksum, version_id)
        except ArtifactError as exc:
            raise ToolFailure("content_unavailable", "تعذر قراءة محتوى المستند المحفوظ.") from exc
