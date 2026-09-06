"""Concurrent chat and document-tool acceptance for ten private workspaces."""

from __future__ import annotations

import json
import os
import statistics
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import requests


BASE_URL = os.getenv("PLATFORM_TEST_URL", "http://api:8000").rstrip("/")
TIMEOUT = int(os.getenv("PLATFORM_TEST_TIMEOUT", "900"))


def new_workspace() -> dict[str, str]:
    token = f"mixed-{uuid.uuid4().hex}-{uuid.uuid4().hex}"
    requests.post(f"{BASE_URL}/workspaces", json={"token": token}, timeout=10).raise_for_status()
    return {"Authorization": f"Bearer {token}"}


def create_tool(headers: dict[str, str], payload: dict) -> dict:
    response = requests.post(f"{BASE_URL}/tool-jobs", headers=headers, timeout=15, json={
        "request_id": uuid.uuid4().hex, **payload,
    })
    response.raise_for_status()
    return {"kind": "tool", "id": response.json()["job"]["id"], "headers": headers, "tool": payload["tool_type"]}


def create_chat(headers: dict[str, str], version_id: str) -> dict:
    conversation = requests.post(f"{BASE_URL}/conversations", headers=headers, json={}, timeout=10)
    conversation.raise_for_status()
    conversation_id = conversation.json()["id"]
    response = requests.post(
        f"{BASE_URL}/conversations/{conversation_id}/messages", headers=headers, timeout=15,
        json={"prompt": "ما الفكرة الرئيسة للمستند؟", "request_id": uuid.uuid4().hex, "active_version_id": version_id},
    )
    response.raise_for_status()
    return {"kind": "chat", "id": response.json()["job"]["id"], "headers": headers, "conversation_id": conversation_id, "tool": "chat"}


def wait(item: dict) -> dict:
    started = time.perf_counter()
    deadline = time.monotonic() + TIMEOUT
    while time.monotonic() < deadline:
        response = requests.get(f"{BASE_URL}/jobs/{item['id']}", headers=item["headers"], timeout=10)
        response.raise_for_status()
        job = response.json()
        if job["status"] in {"failed", "cancelled"}:
            raise AssertionError(f"{item['tool']} ended {job['status']}: {job.get('error_code')}")
        if job["status"] == "completed":
            if item["kind"] == "tool":
                result = requests.get(f"{BASE_URL}/tool-jobs/{item['id']}/result", headers=item["headers"], timeout=15)
                result.raise_for_status()
                if not result.json().get("schema_version"):
                    raise AssertionError(f"{item['tool']} returned no schema")
            else:
                messages = requests.get(
                    f"{BASE_URL}/conversations/{item['conversation_id']}/messages",
                    headers=item["headers"], timeout=15,
                )
                messages.raise_for_status()
                if not any(row.get("role") == "assistant" and row.get("content") for row in messages.json()["messages"]):
                    raise AssertionError("Chat completed without an assistant response")
            return {"tool": item["tool"], "seconds": round(time.perf_counter() - started, 2)}
        time.sleep(0.5)
    raise TimeoutError(f"{item['tool']} did not finish")


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * fraction))]


def main() -> None:
    sessions = [new_workspace() for _ in range(10)]
    documents = requests.get(f"{BASE_URL}/documents", headers=sessions[0], timeout=10).json()["documents"]
    ready = [row for row in documents if row.get("content_status") == "ready"]
    if not ready:
        raise RuntimeError("The mixed load needs a ready public document")
    version_id = min(ready, key=lambda row: row.get("char_count") or 10**12)["version_id"]
    prepared_search = create_tool(sessions[7], {
        "tool_type": "web_search", "input_text": "استرجاع المعلومات العربية",
        "options": {"category": "academic", "language": "ar", "max_results": 5},
    })
    wait(prepared_search)
    specs = [
        lambda: create_chat(sessions[0], version_id),
        lambda: create_chat(sessions[1], version_id),
        lambda: create_tool(sessions[2], {"tool_type": "summary", "document_version_id": version_id, "options": {"summary_type": "quick", "length": "short", "include_bullets": True}}),
        lambda: create_tool(sessions[3], {"tool_type": "translation", "document_version_id": version_id, "options": {"target_language": "en", "style": "academic", "keep_formatting": True, "scope": "page", "page": 1}}),
        lambda: create_tool(sessions[4], {"tool_type": "entities", "document_version_id": version_id, "options": {"method": "llm", "entity_types": []}}),
        lambda: create_tool(sessions[5], {"tool_type": "analysis", "document_version_ids": [version_id], "options": {"include_topics": True, "compare": False}}),
        lambda: create_tool(sessions[6], {"tool_type": "mindmap", "document_version_id": version_id, "options": {"target_nodes": 8}}),
        lambda: create_tool(sessions[7], {"tool_type": "web_analysis", "source_job_id": prepared_search["id"], "options": {"language": "ar"}}),
        lambda: create_tool(sessions[8], {"tool_type": "entities", "document_version_id": version_id, "options": {"method": "fast", "entity_types": []}}),
        lambda: create_tool(sessions[9], {"tool_type": "web_search", "input_text": "معالجة اللغة العربية", "options": {"category": "academic", "language": "ar", "max_results": 5}}),
    ]
    with ThreadPoolExecutor(max_workers=10) as pool:
        jobs = list(pool.map(lambda action: action(), specs))
        results = list(pool.map(wait, jobs))
    durations = [row["seconds"] for row in results]
    print(json.dumps({
        "status": "passed", "users": 10, "completed": len(results),
        "p50_seconds": round(statistics.median(durations), 2),
        "p95_seconds": round(percentile(durations, 0.95), 2),
        "max_seconds": max(durations), "jobs": results,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
