"""Atomic, checksummed storage for extracted documents and private tool results."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


DOCUMENT_SCHEMA = "document-artifact.v1"
DOCUMENT_ROOT = Path(os.getenv("DOCUMENT_ARTIFACT_DIR", "/app/data/document_artifacts"))
RESULT_ROOT = Path(os.getenv("TOOL_RESULT_DIR", "/app/data/tool_results"))
CHECKPOINT_ROOT = Path(os.getenv("TOOL_CHECKPOINT_DIR", "/app/data/tool_checkpoints"))


class ArtifactError(RuntimeError):
    pass


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def checksum(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _safe_child(root: Path, *parts: str) -> Path:
    root = root.resolve()
    candidate = root.joinpath(*parts).resolve()
    if candidate != root and root not in candidate.parents:
        raise ArtifactError("Artifact path is outside its configured storage root")
    return candidate


def _write(path: Path, value: dict[str, Any]) -> tuple[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_bytes(value)
    digest = hashlib.sha256(raw).hexdigest()
    fd, temp_name = tempfile.mkstemp(prefix=".artifact-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            with gzip.GzipFile(fileobj=stream, mode="wb") as archive:
                archive.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
        return digest, path.stat().st_size
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise


def _read(path: Path, expected_checksum: str | None = None) -> dict[str, Any]:
    try:
        with gzip.open(path, "rb") as archive:
            raw = archive.read()
        value = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ArtifactError("Artifact could not be read") from exc
    if not isinstance(value, dict):
        raise ArtifactError("Artifact payload is not an object")
    actual = hashlib.sha256(canonical_bytes(value)).hexdigest()
    if expected_checksum and actual != expected_checksum:
        raise ArtifactError("Artifact checksum does not match")
    return value


def document_path(version_id: str) -> Path:
    return _safe_child(DOCUMENT_ROOT, f"{version_id}.json.gz")


def write_document_artifact(value: dict[str, Any]) -> tuple[str, str, int]:
    if value.get("schema_version") != DOCUMENT_SCHEMA:
        raise ArtifactError("Unexpected document artifact schema")
    version_id = str(value.get("document_version_id") or "")
    full_text = str(value.get("full_text") or "").strip()
    pages = value.get("pages")
    if not version_id or not full_text or not isinstance(pages, list):
        raise ArtifactError("Document artifact is incomplete")
    for number, page in enumerate(pages, 1):
        if not isinstance(page, dict) or page.get("number") != number:
            raise ArtifactError("Document artifact pages are invalid")
        text = str(page.get("text") or "")
        if "has_text" in page and bool(page["has_text"]) != bool(text.strip()):
            raise ArtifactError("Document artifact page text state is invalid")
    expected_text = "\n\n".join(str(page.get("text") or "").strip() for page in pages if str(page.get("text") or "").strip()).strip()
    if full_text != expected_text:
        raise ArtifactError("Document full text does not match its ordered pages")
    if "page_count" in value and int(value["page_count"]) != len(pages):
        raise ArtifactError("Document page count does not match its pages")
    path = document_path(version_id)
    digest, size = _write(path, value)
    return str(path), digest, size


def read_document_artifact(storage_key: str, expected_checksum: str, version_id: str) -> dict[str, Any]:
    expected_path = document_path(version_id)
    if Path(storage_key).resolve() != expected_path:
        raise ArtifactError("Document artifact storage key is invalid")
    value = _read(expected_path, expected_checksum)
    if value.get("schema_version") != DOCUMENT_SCHEMA or value.get("document_version_id") != version_id:
        raise ArtifactError("Document artifact identity is invalid")
    pages = value.get("pages")
    if not isinstance(pages, list) or any(
        not isinstance(page, dict) or page.get("number") != number
        for number, page in enumerate(pages, 1)
    ):
        raise ArtifactError("Document artifact pages are invalid")
    expected_text = "\n\n".join(str(page.get("text") or "").strip() for page in pages if str(page.get("text") or "").strip()).strip()
    if str(value.get("full_text") or "").strip() != expected_text:
        raise ArtifactError("Document full text does not match its ordered pages")
    return value


def write_tool_result(owner_id: str, job_id: str, value: dict[str, Any]) -> tuple[str, str, int]:
    if not owner_id or not job_id or not value.get("schema_version"):
        raise ArtifactError("Tool result is incomplete")
    path = tool_result_path(owner_id, job_id)
    digest, size = _write(path, value)
    return str(path), digest, size


def read_tool_result(owner_id: str, job_id: str, storage_key: str, expected_checksum: str) -> dict[str, Any]:
    expected_path = tool_result_path(owner_id, job_id)
    if Path(storage_key).resolve() != expected_path:
        raise ArtifactError("Tool result storage key is invalid")
    return _read(expected_path, expected_checksum)


def tool_result_path(owner_id: str, job_id: str) -> Path:
    return _safe_child(RESULT_ROOT, owner_id, f"{job_id}.json.gz")


def recover_tool_result(owner_id: str, job_id: str) -> tuple[dict[str, Any], str, int, str] | None:
    """Return a valid orphaned result file so the dispatcher can reconcile it.

    The result path is deterministic and remains constrained to RESULT_ROOT;
    this is only used after a worker interruption between the atomic file write
    and its database pointer commit.
    """
    path = tool_result_path(owner_id, job_id)
    if not path.is_file():
        return None
    value = _read(path)
    return value, checksum(value), path.stat().st_size, str(path)


def tool_checkpoint_path(owner_id: str, job_id: str, stage: str, item: int) -> Path:
    """Return a deterministic private path for one completed provider step."""
    if not stage or not stage.replace("_", "").replace("-", "").isalnum() or item < 0:
        raise ArtifactError("Tool checkpoint identity is invalid")
    return _safe_child(CHECKPOINT_ROOT, owner_id, job_id, f"{stage}-{item}.json.gz")


def write_tool_checkpoint(owner_id: str, job_id: str, stage: str, item: int, value: dict[str, Any]) -> None:
    """Atomically persist a completed bounded step before advancing the job."""
    if not isinstance(value, dict):
        raise ArtifactError("Tool checkpoint payload is invalid")
    _write(tool_checkpoint_path(owner_id, job_id, stage, item), value)


def read_tool_checkpoint(owner_id: str, job_id: str, stage: str, item: int) -> dict[str, Any] | None:
    path = tool_checkpoint_path(owner_id, job_id, stage, item)
    if not path.is_file():
        return None
    return _read(path)


def clear_tool_checkpoints(owner_id: str, job_id: str) -> None:
    """Remove checkpoints after the validated final result is safely stored."""
    directory = _safe_child(CHECKPOINT_ROOT, owner_id, job_id)
    if not directory.is_dir():
        return
    for path in directory.glob("*.json.gz"):
        path.unlink(missing_ok=True)
    try:
        directory.rmdir()
    except OSError:
        pass
