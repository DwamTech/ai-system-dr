from __future__ import annotations

import gzip

import pytest

from backend import artifacts


def document_payload(version_id="version-1"):
    return {
        "schema_version": artifacts.DOCUMENT_SCHEMA,
        "document_version_id": version_id,
        "full_text": "صفحة أولى\n\nصفحة ثالثة",
        "pages": [
            {"number": 1, "text": "صفحة أولى", "has_text": True},
            {"number": 2, "text": "", "has_text": False},
            {"number": 3, "text": "صفحة ثالثة", "has_text": True},
        ],
    }


def test_document_artifact_preserves_blank_original_pages(monkeypatch, tmp_path):
    monkeypatch.setattr(artifacts, "DOCUMENT_ROOT", tmp_path / "documents")
    payload = document_payload()
    key, digest, _ = artifacts.write_document_artifact(payload)
    loaded = artifacts.read_document_artifact(key, digest, "version-1")
    assert [page["number"] for page in loaded["pages"]] == [1, 2, 3]
    assert loaded["pages"][1]["has_text"] is False


def test_corrupt_artifact_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(artifacts, "DOCUMENT_ROOT", tmp_path / "documents")
    key, digest, _ = artifacts.write_document_artifact(document_payload())
    with gzip.open(key, "wb") as stream:
        stream.write(b"not-json")
    with pytest.raises(artifacts.ArtifactError):
        artifacts.read_document_artifact(key, digest, "version-1")


def test_result_recovery_only_reads_its_own_safe_path(monkeypatch, tmp_path):
    monkeypatch.setattr(artifacts, "RESULT_ROOT", tmp_path / "results")
    artifacts.write_tool_result("owner", "job", {"schema_version": "analysis.v1", "documents": []})
    recovered = artifacts.recover_tool_result("owner", "job")
    assert recovered is not None
    value, digest, size, key = recovered
    assert value["schema_version"] == "analysis.v1"
    assert len(digest) == 64 and size > 0 and key.endswith("job.json.gz")


def test_tool_checkpoint_round_trip_and_cleanup(monkeypatch, tmp_path):
    monkeypatch.setattr(artifacts, "CHECKPOINT_ROOT", tmp_path / "checkpoints")
    artifacts.write_tool_checkpoint("owner", "job", "translation_page", 4, {"text": "done"})
    assert artifacts.read_tool_checkpoint("owner", "job", "translation_page", 4) == {"text": "done"}
    artifacts.clear_tool_checkpoints("owner", "job")
    assert artifacts.read_tool_checkpoint("owner", "job", "translation_page", 4) is None


def test_tool_checkpoint_rejects_unsafe_stage(monkeypatch, tmp_path):
    monkeypatch.setattr(artifacts, "CHECKPOINT_ROOT", tmp_path / "checkpoints")
    with pytest.raises(artifacts.ArtifactError):
        artifacts.write_tool_checkpoint("owner", "job", "../escape", 0, {"text": "no"})
