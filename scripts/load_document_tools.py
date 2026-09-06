"""Two-round, ten-workspace acceptance load for the durable tool platform."""

from __future__ import annotations

import json
import os
import statistics
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import requests


BASE_URL = os.getenv("PLATFORM_TEST_URL", "http://api:8000").rstrip("/")
USERS = int(os.getenv("PLATFORM_TEST_USERS", "10"))
TIMEOUT = int(os.getenv("PLATFORM_TEST_TIMEOUT", "90"))


def workspace(number: int) -> tuple[str, dict[str, str]]:
    token = f"acceptance-{number}-{uuid.uuid4().hex}-{uuid.uuid4().hex}"
    response = requests.post(f"{BASE_URL}/workspaces", json={"token": token}, timeout=10)
    response.raise_for_status()
    return response.json()["workspace_id"], {"Authorization": f"Bearer {token}"}


def submit(headers: dict[str, str], version_id: str) -> tuple[str, float]:
    started = time.perf_counter()
    response = requests.post(
        f"{BASE_URL}/tool-jobs", headers=headers, timeout=10,
        json={
            "tool_type": "analysis", "request_id": uuid.uuid4().hex,
            "document_version_ids": [version_id],
            "options": {"include_topics": False, "compare": False},
        },
    )
    response.raise_for_status()
    return response.json()["job"]["id"], started


def wait(headers: dict[str, str], job_id: str, started: float) -> dict:
    deadline = time.monotonic() + TIMEOUT
    while time.monotonic() < deadline:
        job = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=headers, timeout=10).json()
        if job["status"] in {"completed", "failed", "cancelled"}:
            if job["status"] != "completed":
                raise AssertionError(f"job {job_id} ended as {job['status']}: {job.get('error_code')}")
            result_response = requests.get(f"{BASE_URL}/tool-jobs/{job_id}/result", headers=headers, timeout=10)
            result_response.raise_for_status()
            result = result_response.json()
            if not result.get("documents"):
                raise AssertionError(f"job {job_id} returned an empty successful result")
            return {"seconds": time.perf_counter() - started, "job_id": job_id}
        time.sleep(0.2)
    raise TimeoutError(f"job {job_id} did not reach a terminal state")


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round((len(ordered) - 1) * fraction)))]


def main() -> None:
    response = requests.get(f"{BASE_URL}/health", timeout=10)
    response.raise_for_status()
    sessions = [workspace(number) for number in range(USERS)]
    document_sets = [requests.get(f"{BASE_URL}/documents", headers=headers, timeout=10).json()["documents"] for _, headers in sessions]
    if not document_sets[0]:
        raise RuntimeError("The acceptance load needs one ready document in the public archive")
    visible_version = document_sets[0][0]["version_id"]
    if any(visible_version not in {row["version_id"] for row in rows} for rows in document_sets):
        raise AssertionError("The public archive is not consistent across workspaces")
    rounds = []
    for round_number in (1, 2):
        with ThreadPoolExecutor(max_workers=USERS) as pool:
            submitted = list(pool.map(lambda item: submit(item[1], visible_version), sessions))
            completed = list(pool.map(lambda args: wait(args[0][1], args[1][0], args[1][1]), zip(sessions, submitted)))
        durations = [item["seconds"] for item in completed]
        rounds.append({
            "round": round_number, "users": USERS, "completed": len(completed),
            "p50_seconds": round(statistics.median(durations), 3),
            "p95_seconds": round(percentile(durations, 0.95), 3),
            "max_seconds": round(max(durations), 3),
        })
        owner_headers, other_headers = sessions[0][1], sessions[1][1]
        private_job = completed[0]["job_id"]
        if requests.get(f"{BASE_URL}/tool-jobs/{private_job}/result", headers=other_headers, timeout=10).status_code != 404:
            raise AssertionError("A private tool result was visible to another workspace")
        assert requests.get(f"{BASE_URL}/tool-jobs/{private_job}/result", headers=owner_headers, timeout=10).status_code == 200
    print(json.dumps({"status": "passed", "rounds": rounds}, ensure_ascii=False))


if __name__ == "__main__":
    main()
