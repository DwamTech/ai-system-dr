from __future__ import annotations

import pytest

from backend.tool_result_contracts import validate_tool_result


def test_rejects_partial_coverage_before_result_storage():
    with pytest.raises(ValueError, match="coverage"):
        validate_tool_result({
            "schema_version": "summary.v1", "text": "ملخص", "bullets": [], "citations": [],
            "metrics": {}, "coverage": {"processed_pages": 1, "total_pages": 2},
        })


def test_rejects_a_mindmap_edge_to_an_unknown_node():
    with pytest.raises(ValueError, match="edge"):
        validate_tool_result({
            "schema_version": "mindmap.v1", "central_topic": "موضوع",
            "nodes": [{"id": "a", "label": "أ"}],
            "edges": [{"source": "a", "target": "missing"}],
            "coverage": {"processed_pages": 1, "total_pages": 1},
        })
