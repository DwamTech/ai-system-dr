from __future__ import annotations

from .common import MODEL_CONTENT_CHARS, ToolContext, ToolFailure, chunks


def _detect_language(text: str) -> str:
    letters = [character for character in text if character.isalpha()]
    if not letters:
        return "unknown"
    arabic = sum("\u0600" <= character <= "\u06ff" for character in letters)
    return "ar" if arabic / len(letters) >= 0.35 else "en"


def run(context: ToolContext) -> dict:
    payload, options = context.job.payload, context.job.payload["options"]
    if payload.get("document_version_id"):
        artifact = context.document(payload["document_version_id"])
        pages = artifact["pages"]
        if options["scope"] == "page":
            pages = [page for page in pages if page["number"] == options.get("page")]
        elif options["scope"] == "range":
            pages = [page for page in pages if options.get("start_page", 1) <= page["number"] <= options.get("end_page", 0)]
        if not pages:
            raise ToolFailure("invalid_request", "نطاق الصفحات المحدد غير متاح.")
        total_pages = len(pages)
    else:
        pages, total_pages = [{"number": 1, "text": payload["input_text"]}], 1
    source_text = "\n".join(page["text"] for page in pages if page.get("text"))
    if not source_text.strip():
        raise ToolFailure("content_unavailable", "لا يحتوي النطاق المحدد على نص قابل للترجمة.")
    source_language = _detect_language(source_text)
    sample = source_text[:MODEL_CONTENT_CHARS]
    glossary = []
    if sample:
        parsed = context.checkpoint_json(
            "translation_glossary", 0,
            "استخرج أهم المصطلحات التي يجب توحيد ترجمتها كـJSON بالمفتاح glossary. "
            "كل عنصر يحتوي source,target، ولا تتجاوز 15 عنصرًا. "
            f"اللغة الهدف {options['target_language']}.\n<SOURCE_SAMPLE>\n{sample}\n</SOURCE_SAMPLE>",
            "translation_glossary",
        )
        glossary = [item for item in parsed.get("glossary", []) if isinstance(item, dict) and item.get("source") and item.get("target")][:15]
    glossary_text = "\n".join(f"{item['source']} => {item['target']}" for item in glossary)
    translated = []
    context.progress(10, "processing", "جارٍ بدء الترجمة.")
    chunk_checkpoint = 0
    for position, page in enumerate(pages, 1):
        if not str(page.get("text") or "").strip():
            translated.append({"number": page["number"], "text": "", "has_text": False})
            context.progress(10 + int(80 * position / total_pages), "processing", f"جارٍ ترجمة الصفحة {position}/{total_pages}.")
            continue
        results = []
        for part in chunks(page["text"]):
            formatting = "Preserve headings, lists and simple table structure." if options["keep_formatting"] else "Use plain paragraphs."
            prompt = (
                f"Translate to {options['target_language']}. Style: {options['style']}. {formatting} "
                "Use the glossary consistently and output translation only.\n"
                f"<GLOSSARY>\n{glossary_text}\n</GLOSSARY>\n<SOURCE_TEXT>\n{part}\n</SOURCE_TEXT>"
            )
            results.append(context.checkpoint_text("translation_page", chunk_checkpoint, prompt, "translation"))
            chunk_checkpoint += 1
        translated.append({"number": page["number"], "text": "\n\n".join(results), "has_text": True})
        context.progress(10 + int(80 * position / total_pages), "processing", f"جارٍ ترجمة الصفحة {position}/{total_pages}.")
    output = "\n\n".join(item["text"] for item in translated)
    return {"schema_version": "translation.v1", "source_language": source_language, "target_language": options["target_language"], "pages": translated, "text": output, "glossary": glossary, "coverage": {"processed_pages": total_pages, "total_pages": total_pages}}
