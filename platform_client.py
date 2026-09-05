"""Small, retry-safe client used by Streamlit.

It never stores application state locally; Streamlit only keeps the workspace
token, current job id and conversation id needed to call the platform API.
"""

from __future__ import annotations

import os
from typing import Any

import requests


class PlatformUnavailable(RuntimeError):
    pass


class PlatformClient:
    def __init__(self, token: str = "", base_url: str | None = None):
        self.base_url = (base_url or os.getenv("PLATFORM_API_URL", "")).rstrip("/")
        self.token = token
        if not self.base_url:
            raise PlatformUnavailable("PLATFORM_API_URL is not configured")

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def _request(self, method: str, path: str, **kwargs) -> Any:
        try:
            response = requests.request(
                method, f"{self.base_url}{path}", headers=self.headers, timeout=(3, 20), **kwargs
            )
        except requests.RequestException as exc:
            raise PlatformUnavailable("Platform API is temporarily unavailable") from exc
        if response.status_code >= 400:
            detail = ""
            try:
                detail = response.json().get("detail", "")
            except ValueError:
                pass
            raise PlatformUnavailable(detail or f"Platform API returned {response.status_code}")
        return response.json()

    def ensure_workspace(self) -> dict:
        payload = {"token": self.token} if self.token else {}
        workspace = self._request("POST", "/workspaces", json=payload)
        if workspace.get("token"):
            self.token = workspace["token"]
        return workspace

    def upload(self, file) -> dict:
        data = file.getvalue()
        return self._request(
            "POST", "/uploads", files={"file": (file.name, data, "application/pdf")}
        )

    def create_index_job(self, upload_id: str, force_ocr: bool = False) -> dict:
        return self._request("POST", "/indexing-jobs", json={"upload_id": upload_id, "force_ocr": force_ocr})

    def documents(self, q: str = "", offset: int = 0, limit: int = 100) -> dict:
        return self._request("GET", "/documents", params={"q": q, "offset": offset, "limit": limit})

    def jobs(self) -> list[dict]:
        return self._request("GET", "/jobs").get("jobs", [])

    def conversations(self) -> list[dict]:
        return self._request("GET", "/conversations").get("conversations", [])

    def job(self, job_id: str) -> dict:
        return self._request("GET", f"/jobs/{job_id}")

    def cancel_job(self, job_id: str) -> dict:
        return self._request("POST", f"/jobs/{job_id}/cancel")

    def create_conversation(self) -> dict:
        return self._request("POST", "/conversations", json={})

    def messages(self, conversation_id: str) -> list[dict]:
        return self._request("GET", f"/conversations/{conversation_id}/messages").get("messages", [])

    def send_prompt(self, conversation_id: str, prompt: str, request_id: str,
                    active_version_id: str | None = None) -> dict:
        return self._request(
            "POST", f"/conversations/{conversation_id}/messages",
            json={"prompt": prompt, "request_id": request_id, "active_version_id": active_version_id},
        )
