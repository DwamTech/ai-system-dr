"""Create durable text artifacts for public versions indexed before tool jobs existed."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from sqlalchemy import select

from backend.artifacts import DOCUMENT_SCHEMA, write_document_artifact
from backend.db import SessionLocal, init_db
from backend.models import Document, DocumentArtifact, DocumentVersion
from backend.stored_file import StoredFile
from processor_optimized import OptimizedDocumentProcessor


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("platform.backfill_artifacts")


def backfill(limit: int, dry_run: bool = False) -> tuple[int, int]:
    db = SessionLocal()
    ready = failed = 0
    try:
        rows = db.execute(
            select(Document, DocumentVersion).join(
                DocumentVersion, Document.current_version_id == DocumentVersion.id
            ).where(Document.published.is_(True), DocumentVersion.status == "completed").limit(limit)
        ).all()
        for document, version in rows:
            current = db.get(DocumentArtifact, version.id)
            if current and current.status == "ready":
                continue
            if dry_run:
                if Path(document.storage_key).is_file():
                    ready += 1
                else:
                    failed += 1
                continue
            artifact = current or DocumentArtifact(version_id=version.id, status="pending")
            if current is None:
                db.add(artifact)
                db.flush()
            if not Path(document.storage_key).is_file():
                artifact.status, artifact.error_code = "unavailable", "content_unavailable"
                db.commit(); failed += 1
                continue
            try:
                processor = OptimizedDocumentProcessor(reporter=lambda level, message: logger.info("%s: %s", level, message))
                chunks, raw_text, used_ocr, pages = processor.process_single_pdf(StoredFile(document.storage_key, document.display_name))
                normalized_pages = [str(page).strip() for page in pages] or ([raw_text.strip()] if raw_text.strip() else [])
                if not chunks or not any(normalized_pages):
                    raise RuntimeError("No readable ordered text")
                full_text = "\n\n".join(page for page in normalized_pages if page)
                payload = {
                    "schema_version": DOCUMENT_SCHEMA, "document_id": document.id, "document_version_id": version.id,
                    "display_name": document.display_name, "content_hash": document.content_hash,
                    "extraction_method": "ocr" if used_ocr else "direct_extraction", "used_ocr": bool(used_ocr),
                    "full_text": full_text,
                    "pages": [{"number": i, "text": page, "has_text": bool(page), "char_count": len(page), "word_count": len(page.split())} for i, page in enumerate(normalized_pages, 1)],
                    "page_count": len(normalized_pages), "text_page_count": sum(1 for page in normalized_pages if page), "char_count": len(full_text), "word_count": len(full_text.split()),
                    "created_at": version.published_at.isoformat() if version.published_at else "",
                }
                key, digest, _ = write_document_artifact(payload)
                artifact.status, artifact.storage_key, artifact.checksum = "ready", key, digest
                artifact.schema_version, artifact.page_count = DOCUMENT_SCHEMA, len(normalized_pages)
                artifact.char_count, artifact.word_count, artifact.used_ocr, artifact.error_code = len(full_text), len(full_text.split()), bool(used_ocr), None
                db.commit(); ready += 1
            except Exception:
                logger.exception("Could not backfill artifact for version %s", version.id)
                artifact.status, artifact.error_code = "failed", "content_unavailable"
                db.commit(); failed += 1
        return ready, failed
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    init_db()
    ready, failed = backfill(max(1, args.limit), dry_run=args.dry_run)
    print({"dry_run": args.dry_run, "ready_or_eligible": ready, "failed_or_unavailable": failed})


if __name__ == "__main__":
    main()
