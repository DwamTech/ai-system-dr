from __future__ import annotations

from .common import ToolContext, ToolFailure, hierarchical_reduce, page_chunks


def run(context: ToolContext) -> dict:
    payload, options = context.job.payload, context.job.payload["options"]
    artifact = context.document(payload["document_version_id"])
    parts = page_chunks(artifact["pages"])
    if not parts:
        raise ToolFailure("content_unavailable", "لا يحتوي المستند على صفحات نصية قابلة للتلخيص.")
    context.progress(10, "processing", "جارٍ تحليل المستند بالكامل.")
    partials = []
    for index, part in enumerate(parts, 1):
        partials.append(context.checkpoint_text("summary_map", index - 1,
            "لخص الجزء التالي من مستند أكاديمي بالعربية مع الحفاظ على الحقائق فقط. "
            f"اذكر أرقام الصفحات الداعمة داخل أقواس. الصفحات: {list(part.page_refs)}.\n"
            f"<DOCUMENT_CHUNK>\n{part.text}\n</DOCUMENT_CHUNK>", "summary_map"
        ))
        context.progress(10 + int(55 * index / len(parts)), "processing", f"جارٍ تحليل الجزء {index}/{len(parts)}.")
    target = {"short": "150-250", "medium": "350-600", "detailed": "800-1200"}[options["length"]]
    reduced = hierarchical_reduce(
        context, partials,
        "ادمج الملخصات الجزئية التالية في ملخص واحد موجز، واحتفظ بمراجع الصفحات ولا تضف حقائق.",
        "summary_reduce",
    )
    bullet_instruction = "اكتب بعد الملخص نقاطًا رئيسية تبدأ كل منها بعلامة -." if options["include_bullets"] else "اكتب فقرات مترابطة فقط من دون قوائم نقطية."
    structured = context.checkpoint_json(
        "summary_final", 0,
        f"اكتب ملخصًا من النوع {options['summary_type']} بالعربية. الطول المستهدف {target} كلمة. "
        f"{bullet_instruction} أعد JSON فقط بالمفاتيح text وbullets وcited_pages. cited_pages قائمة أرقام "
        "الصفحات التي تدعم الملخص، ولا تضف حقائق من خارج النص.\n"
        f"<SUPPORTED_SUMMARY>\n{reduced}\n</SUPPORTED_SUMMARY>",
        "summary_final",
    )
    final = str(structured.get("text") or "").strip()
    bullets = [str(value).strip() for value in structured.get("bullets", []) if str(value).strip()] if options["include_bullets"] else []
    valid_pages = {int(page["number"]): page for page in artifact["pages"] if str(page.get("text") or "").strip()}
    cited_pages = sorted({int(value) for value in structured.get("cited_pages", []) if str(value).isdigit()})
    if not final or not cited_pages or any(page not in valid_pages for page in cited_pages):
        raise ToolFailure("invalid_model_output", "تعذر التحقق من مراجع الملخص.")
    source_words, result_words = artifact["word_count"], len(final.split())
    context.progress(95, "validating", "جارٍ التحقق من النتيجة.")
    return {
        "schema_version": "summary.v1", "text": final, "bullets": bullets,
        "citations": [{"page": page, "excerpt": str(valid_pages[page]["text"])[:240]} for page in cited_pages],
        "metrics": {"source_words": source_words, "result_words": result_words, "compression_percent": max(0, round((1 - result_words / max(source_words, 1)) * 100, 1))},
        "coverage": {"processed_pages": artifact["page_count"], "total_pages": artifact["page_count"]},
    }
