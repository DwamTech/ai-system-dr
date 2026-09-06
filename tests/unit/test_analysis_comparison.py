from __future__ import annotations

from types import SimpleNamespace

from backend.tooling.analysis import run


class Context:
    def __init__(self):
        self.job = SimpleNamespace(payload={
            "document_version_ids": ["a", "b"],
            "options": {"include_topics": False, "compare": True},
        })
        self.artifacts = {
            "a": {"full_text": "الذكاء الاصطناعي يحسن البحث العلمي. الذكاء الاصطناعي مفيد.", "page_count": 1},
            "b": {"full_text": "البحث العلمي يعتمد على الذكاء الاصطناعي والتحليل.", "page_count": 1},
        }

    def document(self, version_id):
        return self.artifacts[version_id]

    def progress(self, *_):
        return None

    def invoke(self, *_):
        raise AssertionError("The deterministic comparison must not call the provider")


def test_comparison_returns_actual_shared_and_document_specific_terms():
    result = run(Context())
    shared = {item["term"] for item in result["comparison"]["shared_topics"]}
    assert "الذكاء" in shared or "الاصطناعي" in shared
    assert all("document_version_id" in item for item in result["comparison"]["differences"])
    assert "تحتاج مراجعة" not in str(result["comparison"])
