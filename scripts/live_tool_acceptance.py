"""Exercise every document-tool API against real workers without printing content."""

from __future__ import annotations

import json
import os
import time
import uuid

import requests


BASE_URL = os.getenv("PLATFORM_TEST_URL", "http://api:8000").rstrip("/")
TIMEOUT = int(os.getenv("PLATFORM_TEST_TIMEOUT", "300"))


def submit(headers: dict[str, str], payload: dict) -> str:
    response = requests.post(
        f"{BASE_URL}/tool-jobs", headers=headers,
        json={"request_id": uuid.uuid4().hex, **payload}, timeout=15,
    )
    response.raise_for_status()
    return response.json()["job"]["id"]


def await_result(headers: dict[str, str], job_id: str) -> tuple[dict, float]:
    started = time.perf_counter()
    deadline = time.monotonic() + TIMEOUT
    while time.monotonic() < deadline:
        job_response = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=headers, timeout=10)
        job_response.raise_for_status()
        job = job_response.json()
        if job["status"] in {"failed", "cancelled"}:
            raise AssertionError(f"{job['type']} failed: {job.get('error_code')} / {job.get('message')}")
        if job["status"] == "completed":
            result_response = requests.get(f"{BASE_URL}/tool-jobs/{job_id}/result", headers=headers, timeout=15)
            result_response.raise_for_status()
            result = result_response.json()
            download = requests.get(f"{BASE_URL}/tool-jobs/{job_id}/download", headers=headers, timeout=15)
            download.raise_for_status()
            if not download.content:
                raise AssertionError(f"{job['type']} produced an empty download")
            return result, time.perf_counter() - started
        time.sleep(0.5)
    raise TimeoutError(f"job {job_id} did not finish")


def main() -> None:
    token = f"live-tools-{uuid.uuid4().hex}-{uuid.uuid4().hex}"
    workspace = requests.post(f"{BASE_URL}/workspaces", json={"token": token}, timeout=10)
    workspace.raise_for_status()
    headers = {"Authorization": f"Bearer {token}"}
    docs = requests.get(f"{BASE_URL}/documents", headers=headers, timeout=10).json()["documents"]
    ready = [row for row in docs if row.get("content_status") == "ready"]
    if not ready:
        raise RuntimeError("No ready public document is available for live acceptance")
    document = min(ready, key=lambda row: row.get("char_count") or 10**12)
    version_id = document["version_id"]
    requests_to_run = [
        {"tool_type": "summary", "document_version_id": version_id, "options": {"summary_type": "quick", "length": "short", "include_bullets": True}},
        {"tool_type": "entities", "document_version_id": version_id, "options": {"method": "fast", "entity_types": []}},
        {"tool_type": "translation", "document_version_id": version_id, "options": {"target_language": "en", "style": "academic", "keep_formatting": True, "scope": "page", "page": 1}},
        {"tool_type": "analysis", "document_version_ids": [version_id], "options": {"include_topics": True, "compare": False}},
        {"tool_type": "mindmap", "document_version_id": version_id, "options": {"target_nodes": 8}},
        {"tool_type": "web_search", "input_text": "استرجاع المعلومات العربية", "options": {"category": "academic", "language": "ar", "max_results": 5}},
    ]
    selected_tools = {value.strip() for value in os.getenv("PLATFORM_TEST_TOOLS", "").split(",") if value.strip()}
    if selected_tools:
        prerequisite_tools = selected_tools | ({"web_search"} if "web_analysis" in selected_tools else set())
        requests_to_run = [request for request in requests_to_run if request["tool_type"] in prerequisite_tools]
    evidence = []
    search_job = ""
    for request in requests_to_run:
        job_id = submit(headers, request)
        result, duration = await_result(headers, job_id)
        expected_schema = request["tool_type"].replace("web_search", "web-search") + ".v1"
        if result.get("schema_version") != expected_schema:
            raise AssertionError(f"Unexpected schema for {request['tool_type']}")
        evidence.append({"tool": request["tool_type"], "status": "completed", "seconds": round(duration, 2)})
        if request["tool_type"] == "web_search":
            search_job = job_id
    if search_job and (not selected_tools or "web_analysis" in selected_tools):
        analysis_job = submit(headers, {"tool_type": "web_analysis", "source_job_id": search_job, "options": {"language": "ar"}})
        analysis, duration = await_result(headers, analysis_job)
        if analysis.get("schema_version") != "web-analysis.v1" or not analysis.get("sources"):
            raise AssertionError("Web analysis did not return verified sources")
        evidence.append({"tool": "web_analysis", "status": "completed", "seconds": round(duration, 2)})
    print(json.dumps({"status": "passed", "document_pages": document["page_count"], "tools": evidence}, ensure_ascii=False))


if __name__ == "__main__":
    main()
