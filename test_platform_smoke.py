"""Run against the API container to check concurrent workspace isolation."""

from concurrent.futures import ThreadPoolExecutor

import requests


URL = "http://127.0.0.1:8000"


def create_private_conversation(number: int) -> tuple[str, dict[str, str]]:
    token = f"load-test-{number:02d}-" + ("x" * 40)
    headers = {"Authorization": f"Bearer {token}"}
    assert requests.post(URL + "/workspaces", json={"token": token}, timeout=5).status_code == 200
    conversation = requests.post(URL + "/conversations", headers=headers, json={}, timeout=5).json()["id"]
    response = requests.post(
        f"{URL}/conversations/{conversation}/messages",
        headers=headers,
        json={"prompt": f"سؤال اختبار {number}", "request_id": f"load-request-{number:02d}"},
        timeout=5,
    )
    assert response.status_code == 200, response.text
    return conversation, headers


with ThreadPoolExecutor(max_workers=10) as executor:
    sessions = list(executor.map(create_private_conversation, range(10)))

first_conversation, first_headers = sessions[0]
_, another_headers = sessions[1]
forbidden = requests.get(
    f"{URL}/conversations/{first_conversation}/messages", headers=another_headers, timeout=5
)
assert forbidden.status_code == 404
owned = requests.get(
    f"{URL}/conversations/{first_conversation}/messages", headers=first_headers, timeout=5
)
assert owned.status_code == 200 and len(owned.json()["messages"]) == 1
print("PASS: 10 concurrent private conversations; cross-session access rejected")
