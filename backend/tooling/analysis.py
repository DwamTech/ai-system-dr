from __future__ import annotations

import re

from .common import ToolContext, arabic_terms, invoke_json, page_chunks


def _normalized(value: str) -> str:
    value = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", value.casefold())
    return value.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه"}))


def run(context: ToolContext) -> dict:
    ids, options = context.job.payload["document_version_ids"], context.job.payload["options"]
    documents, term_sets = [], []
    for index, version_id in enumerate(ids, 1):
        artifact = context.document(version_id); text = artifact["full_text"]
        words = re.findall(r"[^\W\d_]+", text, flags=re.UNICODE)
        sentences = [part for part in re.split(r"[.!؟!?]+", text) if part.strip()]
        topics = []
        if options["include_topics"]:
            topic_pages: dict[str, set[int]] = {}
            for chunk_index, chunk in enumerate(page_chunks(artifact["pages"])):
                parsed = context.checkpoint_json(
                    f"topics_{index}", chunk_index,
                    "استخرج أهم الموضوعات كـJSON بالمفتاح topics. كل عنصر يحتوي name فقط. "
                    f"الصفحات {list(chunk.page_refs)}.\n<DOCUMENT_CHUNK>\n{chunk.text}\n</DOCUMENT_CHUNK>",
                    "topics",
                )
                for topic in parsed.get("topics", []):
                    if isinstance(topic, dict) and str(topic.get("name") or "").strip():
                        name = str(topic["name"]).strip()
                        topic_pages.setdefault(name.casefold(), set()).update(chunk.page_refs)
            topics = [
                {"name": name, "page_refs": sorted(pages), "coverage_percent": round(100 * len(pages) / max(artifact["page_count"], 1), 1)}
                for name, pages in topic_pages.items()
            ][:15]
        normalized_pages = [
            (page["number"], _normalized(str(page.get("text") or "")))
            for page in artifact.get("pages", [{"number": 1, "text": text}])
        ]
        frequent_terms = [
            {"term": term, "count": count, "page_refs": [number for number, page_text in normalized_pages if term in page_text]}
            for term, count in arabic_terms(text)
        ]
        term_sets.append({item["term"]: item["count"] for item in frequent_terms})
        documents.append({"document_version_id": version_id, "metrics": {"words": len(words), "characters_without_spaces": len(re.sub(r"\s+", "", text)), "sentences": len(sentences), "average_word_length": round(sum(len(word) for word in words) / max(len(words), 1), 1)}, "frequent_terms": frequent_terms, "topics": topics})
        context.progress(10 + int(80 * index / len(ids)), "processing", f"جارٍ تحليل المستند {index}/{len(ids)}.")
    comparison = {"shared_topics": [], "differences": []}
    if options["compare"]:
        common_terms = set.intersection(*(set(terms) for terms in term_sets))
        comparison["shared_topics"] = [
            {
                "term": term,
                "documents": [
                    {
                        "document_version_id": documents[index]["document_version_id"],
                        "count": term_sets[index][term],
                        "page_refs": next(item["page_refs"] for item in documents[index]["frequent_terms"] if item["term"] == term),
                    }
                    for index in range(len(documents))
                ],
            }
            for term in sorted(common_terms, key=lambda item: sum(terms[item] for terms in term_sets), reverse=True)[:12]
        ]
        comparison["differences"] = [
            {
                "document_version_id": documents[index]["document_version_id"],
                "terms": [
                    {
                        "term": term, "count": count,
                        "page_refs": next(item["page_refs"] for item in documents[index]["frequent_terms"] if item["term"] == term),
                    }
                    for term, count in terms.items() if term not in common_terms
                ][:12],
            }
            for index, terms in enumerate(term_sets)
        ]
    return {"schema_version": "analysis.v1", "documents": documents, "comparison": comparison}
