from __future__ import annotations

import re
import threading
from collections import defaultdict

from .common import ToolContext, ToolFailure, invoke_json, page_chunks

_nlp = None
_nlp_lock = threading.Lock()


def _fast(artifact: dict, progress=None) -> list[dict]:
    global _nlp
    with _nlp_lock:
        if _nlp is None:
            try:
                import spacy
                _nlp = spacy.load("xx_ent_wiki_sm")
            except Exception as exc:
                raise ToolFailure("internal_error", "تعذر تجهيز محلل الكيانات السريع.") from exc
    labels = {"PERSON": "person", "PER": "person", "ORG": "organization", "GPE": "location", "LOC": "location", "DATE": "date"}
    merged = defaultdict(lambda: {"text": "", "normalized": "", "type": "other", "count": 0, "confidence": None, "pages": set()})
    total_pages = len(artifact["pages"])
    for position, page in enumerate(artifact["pages"], 1):
        for entity in _nlp(page["text"]).ents:
            normalized = re.sub(r"\s+", " ", entity.text.strip()).casefold()
            if not normalized:
                continue
            item = merged[(normalized, labels.get(entity.label_, "other"))]
            item.update({"text": entity.text.strip(), "normalized": normalized, "type": labels.get(entity.label_, "other")})
            item["count"] += 1; item["pages"].add(page["number"])
        if progress:
            progress(10 + int(80 * position / max(total_pages, 1)), "processing", f"جارٍ تحليل الصفحة {position}/{total_pages}.")
    return [{**item, "pages": sorted(item["pages"])} for item in merged.values()]


def _merge_llm_items(items: list[dict]) -> list[dict]:
    merged = defaultdict(lambda: {"text": "", "normalized": "", "type": "other", "count": 0, "confidence": None, "pages": set()})
    valid_types = {"person", "organization", "location", "date", "other"}
    for raw in items:
        if not isinstance(raw, dict) or not str(raw.get("text") or "").strip():
            continue
        text = re.sub(r"\s+", " ", str(raw["text"])).strip()
        normalized = text.casefold()
        entity_type = str(raw.get("type") or "other").lower()
        if entity_type not in valid_types:
            entity_type = "other"
        item = merged[(normalized, entity_type)]
        item.update({"text": text, "normalized": normalized, "type": entity_type})
        item["count"] += max(1, int(raw.get("count") or 1))
        confidence = raw.get("confidence")
        if isinstance(confidence, (int, float)):
            confidence = float(confidence)
            if confidence > 1:
                confidence /= 100
            item["confidence"] = max(min(max(confidence, 0.0), 1.0), item["confidence"] or 0.0)
        item["pages"].update(page for page in raw.get("pages", []) if isinstance(page, int) and page > 0)
    return [{**item, "pages": sorted(item["pages"])} for item in merged.values()]


def run(context: ToolContext) -> dict:
    payload, options = context.job.payload, context.job.payload["options"]
    artifact = context.document(payload["document_version_id"])
    context.progress(10, "loading_content", "جارٍ تحميل صفحات المستند.")
    if options["method"] == "fast":
        items = _fast(artifact, context.progress)
        sections = []
    elif options["method"] == "research_sections":
        sections = []
        source_chunks = page_chunks(artifact["pages"])
        for chunk_index, chunk in enumerate(source_chunks):
            parsed = context.checkpoint_json(
                "research_sections", chunk_index,
                "استخرج أقسام البحث كـJSON بالمفتاح sections. كل قسم يحتوي title,summary,confidence,page_refs. "
                f"الصفحات المتاحة {list(chunk.page_refs)}.\n<DOCUMENT_CHUNK>\n{chunk.text}\n</DOCUMENT_CHUNK>",
                "research_sections",
            )
            for section in parsed.get("sections", []):
                if isinstance(section, dict) and section.get("title"):
                    section["page_refs"] = list(chunk.page_refs)
                    section["summary"] = str(section.get("summary") or section["title"]).strip()
                    confidence = section.get("confidence")
                    if isinstance(confidence, (int, float)):
                        confidence = float(confidence) / 100 if float(confidence) > 1 else float(confidence)
                        section["confidence"] = min(max(confidence, 0.0), 1.0)
                    else:
                        section["confidence"] = None
                    sections.append(section)
            context.progress(10 + int(80 * (chunk_index + 1) / max(len(source_chunks), 1)), "processing", f"جارٍ تحليل الجزء {chunk_index + 1}/{len(source_chunks)}.")
        items = []
    else:
        extracted = []
        source_chunks = page_chunks(artifact["pages"])
        for chunk_index, chunk in enumerate(source_chunks):
            parsed = context.checkpoint_json(
                "entities_map", chunk_index,
                "استخرج الكيانات كـJSON بالمفتاح items. كل عنصر text,type,confidence,pages، "
                "والنوع أحد person,organization,location,date,other. "
                f"استخدم فقط الصفحات {list(chunk.page_refs)}.\n<DOCUMENT_CHUNK>\n{chunk.text}\n</DOCUMENT_CHUNK>",
                "ner",
            )
            for item in parsed.get("items", []):
                if isinstance(item, dict):
                    item["pages"] = list(chunk.page_refs)
                    extracted.append(item)
            context.progress(10 + int(80 * (chunk_index + 1) / max(len(source_chunks), 1)), "processing", f"جارٍ تحليل الجزء {chunk_index + 1}/{len(source_chunks)}.")
        items, sections = _merge_llm_items(extracted), []
    requested_types = set(options.get("entity_types") or [])
    if requested_types:
        items = [item for item in items if item.get("type") in requested_types]
    context.progress(95, "validating", "جارٍ تنظيم الكيانات.")
    return {"schema_version": "entities.v1", "method": options["method"], "items": items, "research_sections": sections, "coverage": {"processed_pages": artifact["page_count"], "total_pages": artifact["page_count"]}}
