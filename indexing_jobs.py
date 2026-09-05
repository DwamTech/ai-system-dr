"""Durable, observable background jobs for document indexing.

The Streamlit session is deliberately not used to hold job state: a browser
refresh creates a new session, while an indexing job must continue to run and
remain inspectable.  Job metadata is stored in the application data volume;
the worker itself is intentionally in-process because this deployment has no
queue worker service.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from engine_optimized import OptimizedRAGEngine
from processor_optimized import OptimizedDocumentProcessor


logger = logging.getLogger("IndexingJobs")
JOBS_DIR = Path(os.getenv("INDEXING_JOBS_DIR", "/app/data/indexing_jobs"))
ACTIVE_STATES = {"queued", "running"}


class StoredPDF:
    """Minimal UploadedFile-compatible wrapper backed by a temporary job file."""

    def __init__(self, path: Path, name: str):
        self.path = path
        self.name = name

    def getvalue(self) -> bytes:
        return self.path.read_bytes()


class IndexingJobManager:
    def __init__(self, jobs_dir: Path = JOBS_DIR):
        self.jobs_dir = jobs_dir
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._threads: dict[str, threading.Thread] = {}
        self._engines: dict[str, OptimizedRAGEngine] = {}
        self._recover_orphaned_jobs()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _job_dir(self, job_id: str) -> Path:
        return self.jobs_dir / job_id

    def _status_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "status.json"

    def _write_status(self, job_id: str, status: dict[str, Any]) -> None:
        path = self._status_path(job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        status["updated_at"] = self._now()
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(status, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, path)

    def get_status(self, job_id: str | None) -> dict[str, Any] | None:
        if not job_id:
            return None
        path = self._status_path(job_id)
        try:
            status = json.loads(path.read_text(encoding="utf-8"))
            # Long blocking model downloads emit no progress callbacks. Compute
            # elapsed time at read time, without inventing percentage progress.
            if status.get("state") in ACTIVE_STATES:
                try:
                    started = datetime.fromisoformat(status["started_at"])
                    status["elapsed_seconds"] = max(
                        status.get("elapsed_seconds", 0),
                        int((datetime.now(timezone.utc) - started).total_seconds()),
                    )
                except (KeyError, ValueError, TypeError):
                    pass
            return status
        except (OSError, json.JSONDecodeError):
            return None

    def get_engine(self, job_id: str | None) -> OptimizedRAGEngine | None:
        if not job_id:
            return None
        with self._lock:
            engine = self._engines.get(job_id)
            if engine is None:
                status = self.get_status(job_id)
                if status and status.get("state") == "completed":
                    # Documents survive a container restart; reconnect lazily
                    # rather than requiring the user to index them again.
                    engine = OptimizedRAGEngine(
                        model_name=status.get("model_name"), report_errors=False
                    )
                    self._engines[job_id] = engine
            return engine

    def _update(self, job_id: str, **changes: Any) -> dict[str, Any]:
        with self._lock:
            status = self.get_status(job_id) or {"id": job_id}
            status.update(changes)
            status["heartbeat_at"] = self._now()
            self._write_status(job_id, status)
            return status

    def _recover_orphaned_jobs(self) -> None:
        """Never show a dead worker as running after a container restart."""
        for path in self.jobs_dir.glob("*/status.json"):
            try:
                status = json.loads(path.read_text(encoding="utf-8"))
                if status.get("state") in ACTIVE_STATES:
                    status.update({
                        "state": "interrupted",
                        "phase": "توقفت المهمة بعد إعادة تشغيل الخدمة",
                        "message": "لم يكتمل العمل لأن خدمة الفهرسة أعيد تشغيلها. أعد رفع الملف وابدأ مهمة جديدة.",
                    })
                    self._write_status(status["id"], status)
            except (OSError, json.JSONDecodeError, KeyError):
                logger.warning("Ignoring unreadable indexing-job state: %s", path)

    def has_running_job(self) -> bool:
        for path in self.jobs_dir.glob("*/status.json"):
            try:
                if json.loads(path.read_text(encoding="utf-8")).get("state") in ACTIVE_STATES:
                    return True
            except (OSError, json.JSONDecodeError):
                continue
        return False

    def start_job(
        self,
        files: list[tuple[str, bytes]],
        *,
        chunk_size: int,
        chunk_overlap: int,
        batch_size: int,
        force_ocr: bool,
        parallel: bool,
        model_name: str,
    ) -> str:
        if not files:
            raise ValueError("No files were supplied for indexing")
        with self._lock:
            if self.has_running_job():
                raise RuntimeError("An indexing job is already running")
            job_id = uuid.uuid4().hex
            status = {
                "id": job_id,
                "model_name": model_name,
                "state": "queued",
                "progress": 1,
                "phase": "وضع المهمة في الطابور",
                "message": "يجري تجهيز مهمة الفهرسة في الخلفية.",
                "active_file": "",
                "completed_files": 0,
                "total_files": len(files),
                "indexed_chunks": 0,
                "total_chunks": 0,
                "files": [name for name, _ in files],
                "indexed_files": [],
                "failed_files": [],
                "started_at": self._now(),
                "heartbeat_at": self._now(),
                "elapsed_seconds": 0,
                "eta_seconds": None,
            }
            self._write_status(job_id, status)
            thread = threading.Thread(
                target=self._run_job,
                args=(job_id, files),
                kwargs={
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "batch_size": batch_size,
                    "force_ocr": force_ocr,
                    "parallel": parallel,
                    "model_name": model_name,
                },
                name=f"indexing-{job_id[:8]}",
                daemon=True,
            )
            self._threads[job_id] = thread
            thread.start()
            return job_id

    @staticmethod
    def _estimate(progress: int, started: float) -> tuple[int, int | None]:
        elapsed = max(0, int(time.monotonic() - started))
        if progress < 8:
            return elapsed, None
        remaining = max(0, int(elapsed * (100 - progress) / progress))
        return elapsed, remaining

    def _set_progress(self, job_id: str, started: float, progress: int, **changes: Any) -> None:
        elapsed, eta = self._estimate(progress, started)
        self._update(
            job_id,
            progress=max(0, min(100, int(progress))),
            elapsed_seconds=elapsed,
            eta_seconds=eta,
            **changes,
        )

    def _save_inputs(self, job_id: str, files: list[tuple[str, bytes]], started: float) -> list[StoredPDF]:
        input_dir = self._job_dir(job_id) / "input"
        input_dir.mkdir(parents=True, exist_ok=True)
        stored: list[StoredPDF] = []
        total_bytes = sum(len(content) for _, content in files)
        copied = 0
        for index, (name, content) in enumerate(files, 1):
            safe_name = Path(name).name or f"document-{index}.pdf"
            target = input_dir / f"{index:03d}-{safe_name}"
            self._set_progress(
                job_id, started, 2,
                state="running", phase="حفظ نسخة العمل المؤقتة",
                message=f"يجري حفظ «{safe_name}» ليبقى العمل مستمراً إذا حدّثت الصفحة.",
                active_file=safe_name,
            )
            with target.open("wb") as output:
                for offset in range(0, len(content), 1024 * 1024):
                    block = content[offset:offset + 1024 * 1024]
                    output.write(block)
                    copied += len(block)
                    progress = 2 + int(3 * copied / max(total_bytes, 1))
                    self._set_progress(
                        job_id, started, progress,
                        state="running", phase="حفظ نسخة العمل المؤقتة",
                        message=f"يجري حفظ «{safe_name}» قبل بدء المعالجة.",
                        active_file=safe_name,
                    )
            stored.append(StoredPDF(target, safe_name))
        return stored

    def _run_job(self, job_id: str, payloads: list[tuple[str, bytes]], **config: Any) -> None:
        started = time.monotonic()
        try:
            stored_files = self._save_inputs(job_id, payloads, started)
            self._set_progress(
                job_id, started, 5,
                state="running", phase="تجهيز نموذج الفهرسة",
                message="يجري تحميل نموذج الفهرسة من النسخة المحلية، أو تنزيله في أول تشغيل فقط. نسبة هذه المرحلة لا تتغير حتى يجهز النموذج؛ الوقت المنقضي يُحدّث تلقائياً.",
                active_file="",
            )
            engine = OptimizedRAGEngine(model_name=config["model_name"], report_errors=False)
            # Separate model readiness from the search connection in the UI.
            _ = engine.embeddings
            self._set_progress(
                job_id, started, 8,
                state="running", phase="الاتصال بمحرك البحث",
                message="نموذج الفهرسة جاهز. يجري تجهيز الاتصال بمحرك البحث قبل قراءة الملفات.",
            )
            engine.get_vectorstore()
            processor = OptimizedDocumentProcessor(
                chunk_size=config["chunk_size"],
                chunk_overlap=config["chunk_overlap"],
                reporter=lambda level, message: logger.warning("%s: %s", level, message),
            )
            total_files = len(stored_files)
            progress_by_file = [0.0] * total_files
            results: list[tuple[list[Any], str, list[str], str]] = [([], "", [], "") for _ in stored_files]

            def update_file_progress(index: int, file_name: str, stage: str, completed: int, total: int) -> None:
                fraction = min(1.0, max(0.0, completed / max(total, 1)))
                progress_by_file[index] = max(progress_by_file[index], fraction)
                processing_progress = 10 + int(45 * sum(progress_by_file) / total_files)
                stage_label = "استخراج النص" if stage == "extract" else "التعرّف الضوئي OCR"
                self._set_progress(
                    job_id, started, processing_progress,
                    state="running", phase=stage_label,
                    message=f"{stage_label}: «{file_name}» ({completed}/{total})",
                    active_file=file_name,
                    completed_files=sum(1 for value in progress_by_file if value >= 1),
                    total_files=total_files,
                )

            def process_one(index: int, stored: StoredPDF) -> tuple[int, list[Any], str, list[str], str]:
                self._set_progress(
                    job_id, started, 10 + int(45 * sum(progress_by_file) / total_files),
                    state="running", phase="فحص المستند",
                    message=f"يجري فحص «{stored.name}» قبل استخراج المحتوى.",
                    active_file=stored.name,
                )
                chunks, raw_text, _used_ocr, pages = processor.process_single_pdf(
                    stored,
                    force_ocr=config["force_ocr"],
                    progress_callback=lambda stage, done, total: update_file_progress(index, stored.name, stage, done, total),
                )
                progress_by_file[index] = 1.0
                return index, chunks, raw_text, pages, stored.name

            if config["parallel"] and total_files > 1:
                with ThreadPoolExecutor(max_workers=min(4, total_files)) as executor:
                    futures = [executor.submit(process_one, index, stored) for index, stored in enumerate(stored_files)]
                    for future in as_completed(futures):
                        index, chunks, raw_text, pages, name = future.result()
                        results[index] = (chunks, raw_text, pages, name)
            else:
                for index, stored in enumerate(stored_files):
                    result_index, chunks, raw_text, pages, name = process_one(index, stored)
                    results[result_index] = (chunks, raw_text, pages, name)

            all_chunks = [chunks for chunks, _text, _pages, _name in results if chunks]
            indexed_files = [name for chunks, _text, _pages, name in results if chunks]
            failed_files = [name for chunks, _text, _pages, name in results if not chunks]
            if not all_chunks:
                raise RuntimeError("No readable text was produced from the submitted documents")

            total_chunks = sum(len(chunks) for chunks in all_chunks)
            self._set_progress(
                job_id, started, 56,
                state="running", phase="تقسيم المحتوى وتجهيز المتجهات",
                message=f"تم استخراج {total_chunks} مقطعاً. يجري الآن إنشاء المتجهات وفهرستها.",
                active_file="",
                completed_files=len(indexed_files), total_files=total_files,
                total_chunks=total_chunks, indexed_chunks=0,
                indexed_files=indexed_files, failed_files=failed_files,
            )

            def update_indexing_progress(done: int, total: int) -> None:
                progress = 56 + int(43 * done / max(total, 1))
                self._set_progress(
                    job_id, started, progress,
                    state="running", phase="فهرسة المتجهات",
                    message=f"تُفهرس دفعات المحتوى: {done}/{total} مقطعاً.",
                    active_file="", indexed_chunks=done, total_chunks=total,
                    indexed_files=indexed_files, failed_files=failed_files,
                )

            if not engine.ingest_documents_bulk(all_chunks, batch_size=config["batch_size"], progress_callback=update_indexing_progress):
                raise RuntimeError("OpenSearch indexing did not complete")
            self._engines[job_id] = engine
            self._set_progress(
                job_id, started, 100,
                state="completed", phase="اكتملت الفهرسة",
                message=f"تمت فهرسة {len(indexed_files)} ملف بنجاح. يمكنك الآن بدء المحادثة.",
                active_file="", completed_files=len(indexed_files), total_files=total_files,
                indexed_chunks=total_chunks, total_chunks=total_chunks,
                indexed_files=indexed_files, failed_files=failed_files,
            )
        except Exception:
            logger.exception("Indexing job %s failed", job_id)
            self._set_progress(
                job_id, started, (self.get_status(job_id) or {}).get("progress", 0),
                state="failed", phase="تعذّر إكمال الفهرسة",
                message="توقفت المهمة قبل اكتمالها. لم يُعرض نجاح غير مؤكد؛ راجع صحة الملف واتصال خدمة الفهرسة ثم حاول مرة أخرى.",
            )
        finally:
            # Raw inputs are needed only while the background job is active.
            shutil.rmtree(self._job_dir(job_id) / "input", ignore_errors=True)
            with self._lock:
                self._threads.pop(job_id, None)


indexing_jobs = IndexingJobManager()
