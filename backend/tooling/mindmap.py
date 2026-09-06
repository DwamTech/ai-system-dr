from __future__ import annotations

import json

from .common import MODEL_CONTENT_CHARS, ToolContext, ToolFailure, hierarchical_reduce, page_chunks


def _normalize_graph(raw: dict, target: int, allowed_pages: set[int]) -> dict | None:
    """Select a connected, acyclic evidence-backed view from a model graph."""
    central = str(raw.get("central_topic") or "").strip()
    source_nodes = raw.get("nodes")
    if not central or not isinstance(source_nodes, list):
        return None
    nodes: dict[str, dict] = {}
    for value in source_nodes:
        if not isinstance(value, dict):
            continue
        node_id, label = str(value.get("id") or "").strip(), str(value.get("label") or "").strip()
        refs = sorted({int(page) for page in value.get("page_refs", []) if str(page).isdigit() and int(page) in allowed_pages})
        if node_id and label and node_id not in nodes and refs:
            nodes[node_id] = {"id": node_id, "label": label, "parent_id": None, "page_refs": refs}
    minimum = max(2, target - 3)
    if len(nodes) < minimum:
        return None
    adjacency = {node_id: set() for node_id in nodes}
    for edge in raw.get("edges", []):
        if not isinstance(edge, dict):
            continue
        source, destination = str(edge.get("source") or ""), str(edge.get("target") or "")
        if source in nodes and destination in nodes and source != destination:
            adjacency[source].add(destination); adjacency[destination].add(source)
    for value in source_nodes:
        node_id, parent_id = str(value.get("id") or ""), str(value.get("parent_id") or "")
        if node_id in nodes and parent_id in nodes and node_id != parent_id:
            adjacency[parent_id].add(node_id); adjacency[node_id].add(parent_id)
    root = max(nodes, key=lambda node_id: len(adjacency[node_id]))
    chosen: list[str] = []
    parent: dict[str, str | None] = {root: None}
    pending = [root]
    while pending and len(chosen) < target:
        current = pending.pop(0)
        if current in chosen:
            continue
        chosen.append(current)
        for neighbor in sorted(adjacency[current], key=lambda item: (-len(adjacency[item]), item)):
            if neighbor not in parent:
                parent[neighbor] = current
                pending.append(neighbor)
    if len(chosen) < minimum:
        return None
    output_nodes, output_edges = [], []
    for node_id in chosen:
        node = dict(nodes[node_id])
        node["parent_id"] = parent[node_id]
        output_nodes.append(node)
        if parent[node_id]:
            output_edges.append({"source": parent[node_id], "target": node_id})
    return {"central_topic": central, "nodes": output_nodes, "edges": output_edges}


def run(context: ToolContext) -> dict:
    payload, options = context.job.payload, context.job.payload["options"]
    if payload.get("document_version_id"):
        artifact = context.document(payload["document_version_id"])
        pages = artifact["pages"]
        total_pages = artifact["page_count"]
    else:
        pages = [{"number": 1, "text": payload["input_text"]}]
        total_pages = 1
    source_chunks = page_chunks(pages)
    if not source_chunks:
        raise ToolFailure("invalid_request", "النص لا يحتوي على محتوى يصلح للخريطة الذهنية.")

    candidates = []
    for index, chunk in enumerate(source_chunks, 1):
        parsed = context.checkpoint_json(
            "mindmap_map", index - 1,
            "استخرج مفاهيم وعلاقات الجزء التالي كـJSON بالمفتاح concepts. كل مفهوم يحتوي label وpage_refs، "
            f"ولا تستخدم صفحات غير {list(chunk.page_refs)}.\n<DOCUMENT_CHUNK>\n{chunk.text}\n</DOCUMENT_CHUNK>",
            "mindmap_map",
        )
        candidates.append(json.dumps(parsed, ensure_ascii=False))
        context.progress(10 + int(55 * index / len(source_chunks)), "processing", f"جارٍ تحليل جزء الخريطة {index}/{len(source_chunks)}.")

    reduced = hierarchical_reduce(
        context, candidates,
        "ادمج المفاهيم المكررة والعلاقات التالية في قائمة موجزة، واحتفظ بمراجع الصفحات. لا تضف معلومات.",
        "mindmap_reduce",
    )
    target = options["target_nodes"]
    result = context.checkpoint_json(
        "mindmap_final", 0,
        "أنشئ JSON فقط بالمفاتيح central_topic,nodes,edges. كل node يحتوي id,label,parent_id,page_refs، "
        "وكل edge يحتوي source,target. استخدم IDs فريدة، واجعل الرسم متصلًا بلا دورات. "
        f"عدد العقد المستهدف {target} مع سماح ثلاث عقد زيادة أو نقص.\n<SUPPORTED_CONCEPTS>\n{reduced}\n</SUPPORTED_CONCEPTS>",
        "mindmap_final",
    )
    allowed_pages = {int(page["number"]) for page in pages if str(page.get("text") or "").strip()}
    graph = _normalize_graph(result, target, allowed_pages)
    if graph is None:
        repaired = context.checkpoint_json(
            "mindmap_semantic_repair", 0,
            "صحح الخريطة التالية وأعد JSON فقط بالمفاتيح central_topic,nodes,edges. يجب أن تكون متصلة "
            "وبلا دورات، ولكل عقدة page_refs من الصفحات المسموح بها، مع IDs فريدة. "
            f"عدد العقد المستهدف {target}، والصفحات المسموح بها {sorted(allowed_pages)}.\n"
            f"<INVALID_GRAPH>\n{json.dumps(result, ensure_ascii=False)[:MODEL_CONTENT_CHARS]}\n</INVALID_GRAPH>",
            "mindmap_semantic_repair",
        )
        graph = _normalize_graph(repaired, target, allowed_pages)
    if graph is None:
        raise ToolFailure("invalid_model_output", "تعذر بناء خريطة ذهنية متصلة ومدعومة بمراجع الصفحات.")
    return {
        "schema_version": "mindmap.v1", **graph,
        "coverage": {"processed_pages": total_pages, "total_pages": total_pages},
    }
