from backend.tool_result_contracts import validate_tool_result
from backend.tooling.mindmap import _normalize_graph


def test_large_model_graph_is_pruned_to_a_connected_acyclic_target():
    raw = {
        "central_topic": "بحث",
        "nodes": [
            {"id": str(index), "label": f"عقدة {index}", "page_refs": [1]}
            for index in range(20)
        ],
        "edges": [{"source": str(index), "target": str(index + 1)} for index in range(19)],
    }
    graph = _normalize_graph(raw, 8, {1})
    assert graph is not None
    assert len(graph["nodes"]) == 8
    assert len(graph["edges"]) == 7
    validate_tool_result({
        "schema_version": "mindmap.v1", **graph,
        "coverage": {"processed_pages": 1, "total_pages": 1},
    })


def test_graph_without_page_evidence_is_rejected():
    raw = {"central_topic": "بحث", "nodes": [{"id": "a", "label": "أ", "page_refs": [99]}], "edges": []}
    assert _normalize_graph(raw, 5, {1}) is None
