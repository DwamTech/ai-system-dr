from __future__ import annotations

from unittest.mock import Mock, patch

from platform_client import PlatformClient


def test_download_keeps_binary_or_text_response_instead_of_forcing_json():
    response = Mock(status_code=200, content=b"translated text")
    response.headers = {
        "content-disposition": 'attachment; filename="translation-job.txt"',
        "content-type": "text/plain; charset=utf-8",
    }
    with patch("platform_client.requests.request", return_value=response):
        client = PlatformClient(token="x" * 32, base_url="http://api")
        content, filename, mime = client.download_tool_result("job", "txt")
    assert content == b"translated text"
    assert filename == "translation-job.txt"
    assert mime.startswith("text/plain")
