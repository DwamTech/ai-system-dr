from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.tool_contracts import ToolJobRequest, validated_options


def request(**changes):
    value = {
        "tool_type": "translation", "request_id": "a" * 16,
        "document_version_id": "11111111-1111-1111-1111-111111111111",
        "options": {"target_language": "en", "scope": "full"},
    }
    value.update(changes)
    return ToolJobRequest(**value)


def test_unknown_options_are_rejected():
    with pytest.raises(ValueError):
        validated_options(request(options={"target_language": "en", "scope": "full", "unexpected": True}))


def test_blank_direct_text_is_rejected():
    with pytest.raises(ValidationError):
        ToolJobRequest(tool_type="mindmap", request_id="b" * 16, input_text="   ")


def test_page_scope_requires_a_page_before_a_job_is_created():
    with pytest.raises(ValueError, match="page number"):
        validated_options(request(options={"target_language": "en", "scope": "page"}))


def test_duplicate_analysis_documents_are_rejected():
    version_id = "11111111-1111-1111-1111-111111111111"
    with pytest.raises(ValidationError, match="unique"):
        ToolJobRequest(
            tool_type="analysis", request_id="c" * 16,
            document_version_ids=[version_id, version_id], options={"compare": True},
        )
