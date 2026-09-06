"""Single durable execution path for every non-chat document tool."""

from __future__ import annotations

from typing import Callable

from backend.artifacts import ArtifactError, clear_tool_checkpoints, write_tool_result
from backend.models import ToolExecution
from backend.tool_result_contracts import validate_tool_result
from backend.tooling import analysis, entities, mindmap, summary, translation, web_search
from backend.tooling.common import ToolContext, ToolFailure


HANDLERS: dict[str, Callable[[ToolContext], dict]] = {
    "summary": summary.run,
    "entities": entities.run,
    "translation": translation.run,
    "analysis": analysis.run,
    "mindmap": mindmap.run,
    "web_search": web_search.search,
    "web_analysis": web_search.analyze,
}


def run(context_db, job, lease, update, invoke) -> dict:
    execution = context_db.get(ToolExecution, job.id)
    if not execution:
        raise ToolFailure("internal_error", "تعذر العثور على سجل الأداة.")
    tool_type = job.payload.get("tool_type")
    handler = HANDLERS.get(tool_type)
    if not handler:
        raise ToolFailure("invalid_request", "نوع الأداة غير مدعوم.")
    context = ToolContext(
        db=context_db, job=job, execution=execution,
        progress_callback=lambda progress, phase, message: update(progress, phase, message),
        invoke_callback=invoke,
    )
    context.progress(2, "loading_content", "جارٍ تجهيز الطلب.")
    result = handler(context)
    if not isinstance(result, dict) or not result.get("schema_version"):
        raise ToolFailure("invalid_model_output", "تعذر التحقق من نتيجة الأداة.")
    try:
        result = validate_tool_result(result)
    except (TypeError, ValueError) as exc:
        raise ToolFailure("invalid_model_output", "تعذر التحقق من اكتمال نتيجة الأداة.") from exc
    context.progress(97, "saving", "جارٍ حفظ النتيجة.")
    try:
        key, checksum, size = write_tool_result(execution.owner_id, job.id, result)
    except ArtifactError as exc:
        raise ToolFailure("result_storage_failed", "تعذر حفظ النتيجة بصورة آمنة.") from exc
    execution.result_storage_key, execution.result_checksum, execution.result_size_bytes = key, checksum, size
    execution.schema_version = str(result["schema_version"])
    context_db.commit()
    clear_tool_checkpoints(execution.owner_id, job.id)
    return result
