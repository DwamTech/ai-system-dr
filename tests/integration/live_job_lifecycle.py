"""Live cancellation and invalid-request checks against a running platform."""

from __future__ import annotations

import json
import os
import time
import uuid

import requests


BASE_URL = os.getenv("PLATFORM_TEST_URL", "http://api:8000").rstrip("/")


def main() -> None:
    token = f"lifecycle-{uuid.uuid4().hex}-{uuid.uuid4().hex}"
    requests.post(f"{BASE_URL}/workspaces", json={"token": token}, timeout=10).raise_for_status()
    headers = {"Authorization": f"Bearer {token}"}
    request_id = uuid.uuid4().hex
    payload = {
        "tool_type": "mindmap", "request_id": request_id,
        "input_text": "البحث العلمي يجمع الأدلة ويحلل النتائج ويعرض الاستنتاجات بوضوح. " * 10,
        "options": {"target_nodes": 8},
    }
    created = requests.post(f"{BASE_URL}/tool-jobs", headers=headers, json=payload, timeout=10)
    created.raise_for_status()
    job_id = created.json()["job"]["id"]
    duplicate = requests.post(f"{BASE_URL}/tool-jobs", headers=headers, json=payload, timeout=10)
    duplicate.raise_for_status()
    if duplicate.json()["job"]["id"] != job_id or not duplicate.json().get("deduplicated"):
        raise AssertionError("Idempotent request did not return the original job")
    requests.post(f"{BASE_URL}/jobs/{job_id}/cancel", headers=headers, timeout=10).raise_for_status()
    deadline = time.monotonic() + 20
    terminal = None
    while time.monotonic() < deadline:
        terminal = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=headers, timeout=10).json()
        if terminal["status"] in {"cancelled", "completed", "failed"}:
            break
        time.sleep(0.25)
    if not terminal or terminal["status"] != "cancelled":
        raise AssertionError(f"Cancellation did not finish correctly: {terminal}")
    documents = requests.get(f"{BASE_URL}/documents", headers=headers, timeout=10).json()["documents"]
    if documents:
        invalid = requests.post(f"{BASE_URL}/tool-jobs", headers=headers, timeout=10, json={
            "tool_type": "translation", "request_id": uuid.uuid4().hex,
            "document_version_id": documents[0]["version_id"],
            "options": {"target_language": "en", "style": "academic", "keep_formatting": True, "scope": "page", "page": documents[0]["page_count"] + 1},
        })
        if invalid.status_code != 422:
            raise AssertionError(f"Out-of-range translation page returned {invalid.status_code}")
    print(json.dumps({"status": "passed", "cancelled_job": True, "idempotency": True, "invalid_page": 422}))


if __name__ == "__main__":
    main()
