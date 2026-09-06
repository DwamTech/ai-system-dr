"""Streamlit presentation for durable non-chat tool jobs in platform mode."""

from __future__ import annotations

import json
import uuid
from typing import Any

import streamlit as st

from platform_client import PlatformClient, PlatformUnavailable


TOOL_LABELS = {
    "summary": "الملخص", "entities": "الكيانات", "translation": "الترجمة",
    "analysis": "التحليل", "mindmap": "الخريطة الذهنية", "web_search": "البحث الأكاديمي",
    "web_analysis": "تحليل نتائج البحث",
}
ENTITY_LABELS = {"person": "شخص", "organization": "منظمة", "location": "مكان", "date": "تاريخ", "other": "أخرى"}


def _state() -> dict[str, str]:
    return st.session_state.setdefault("platform_tool_jobs", {})


ACTIVE_STATUSES = {"queued", "preparing", "extracting", "indexing", "running", "cancel_requested"}
PHASE_LABELS = {
    "queued": "في انتظار الدور", "recovering": "جارٍ استعادة المهمة", "loading_content": "جارٍ تحميل المحتوى",
    "processing": "جارٍ المعالجة", "provider": "جارٍ الاتصال بخدمة الذكاء الاصطناعي",
    "validating": "جارٍ التحقق من النتيجة", "saving": "جارٍ حفظ النتيجة",
    "completed": "اكتملت المهمة", "cancelled": "أُلغيت المهمة",
}


def _restore_jobs(client: PlatformClient) -> None:
    """Restore the newest durable job for each tab after a browser refresh."""
    if st.session_state.get("platform_tool_jobs_restored"):
        return
    restored = _state()
    for job in client.jobs():
        tool = str(job.get("type", "")).removeprefix("tool_")
        if tool in TOOL_LABELS and tool not in restored:
            restored[tool] = job["id"]
    st.session_state.platform_tool_jobs_restored = True


def _active_job(client: PlatformClient, tool: str) -> bool:
    job_id = _state().get(tool)
    if not job_id:
        return False
    try:
        return client.job(job_id).get("status") in ACTIVE_STATUSES
    except PlatformUnavailable:
        # Keep submission locked until the durable job can be checked again;
        # an API outage must not produce duplicate work from repeated clicks.
        return True


def _ready_documents(client: PlatformClient) -> list[dict[str, Any]]:
    return [row for row in client.documents().get("documents", []) if row.get("content_status") == "ready"]


def _select_document(label: str, docs: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    if not docs:
        st.info("لا يوجد مستند مكتمل التجهيز بعد. ارفع مستندًا وانتظر اكتمال الفهرسة.")
        return None
    return st.selectbox(label, docs, format_func=lambda row: f"{row['name']} — {row['page_count']} صفحة", key=key)


def _submit(client: PlatformClient, tool: str, payload: dict[str, Any]) -> None:
    try:
        st.session_state[f"platform_tool_payload_{tool}"] = payload
        response = client.create_tool_job({"tool_type": tool, "request_id": uuid.uuid4().hex, **payload})
        _state()[tool] = response["job"]["id"]
        st.rerun()
    except PlatformUnavailable as exc:
        st.error(f"تعذر بدء {TOOL_LABELS[tool]}: {exc}")


def _result_view(client: PlatformClient, tool: str) -> bool:
    job_id = _state().get(tool)
    if not job_id:
        return False
    def draw() -> None:
        try:
            job = client.job(job_id)
        except PlatformUnavailable as exc:
            st.error(f"تعذر قراءة حالة المهمة: {exc}")
            return
        if job["status"] in ACTIVE_STATUSES:
            phase = PHASE_LABELS.get(job.get("phase"), job.get("message", "جارٍ التنفيذ."))
            st.progress(job.get("progress", 0), text=phase)
            if job.get("message") and job.get("message") != phase:
                st.caption(job["message"])
            if st.button("إلغاء", key=f"cancel_{tool}_{job_id}"):
                try:
                    client.cancel_job(job_id)
                    st.rerun()
                except PlatformUnavailable as exc:
                    st.error(f"تعذر إلغاء المهمة: {exc}")
            return
        if job["status"] != "completed":
            error_code = job.get("error_code") or job.get("phase")
            st.error(f"{job.get('message', 'تعذر تنفيذ الأداة.')} ({error_code})")
            retry_payload = st.session_state.get(f"platform_tool_payload_{tool}")
            if retry_payload and st.button("إعادة المحاولة", key=f"retry_{tool}_{job_id}"):
                _submit(client, tool, retry_payload)
            if st.button("مسح الحالة", key=f"clear_failed_{tool}_{job_id}"):
                _state().pop(tool, None)
                st.rerun()
            return
        try:
            result = client.tool_result(job_id)
        except PlatformUnavailable as exc:
            st.error(f"تعذر جلب النتيجة: {exc}")
            return
        _render_result(client, tool, result, job_id)
        if st.button("بدء نتيجة جديدة", key=f"clear_completed_{tool}_{job_id}"):
            _state().pop(tool, None)
            st.rerun()
    try:
        if hasattr(st, "fragment"):
            @st.fragment(run_every="2s")
            def fragment():
                draw()
            fragment()
        else:
            draw()
    except PlatformUnavailable as exc:
        st.error(str(exc))
    return True


def _render_result(client: PlatformClient, tool: str, result: dict[str, Any], job_id: str) -> None:
    text = result.get("text")
    if isinstance(text, str):
        st.markdown(text)
    if tool == "summary":
        metrics = result.get("metrics", {})
        cols = st.columns(3)
        cols[0].metric("كلمات المصدر", metrics.get("source_words", 0))
        cols[1].metric("كلمات الملخص", metrics.get("result_words", 0))
        cols[2].metric("نسبة الاختصار", f"{metrics.get('compression_percent', 0)}%")
        if result.get("bullets"):
            with st.expander("النقاط الرئيسية", expanded=True):
                for bullet in result["bullets"]:
                    st.markdown(f"- {bullet}")
        if result.get("citations"):
            with st.expander("مراجع الصفحات"):
                for citation in result["citations"]:
                    st.caption(f"صفحة {citation.get('page')}: {citation.get('excerpt', '')}")
    elif tool == "entities":
        rows = [{**item, "type": ENTITY_LABELS.get(item.get("type"), item.get("type")), "pages": ", ".join(map(str, item.get("pages", [])))} for item in result.get("items", [])]
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        for section in result.get("research_sections", []):
            with st.expander(f"{section.get('title', 'قسم')} — الصفحات {', '.join(map(str, section.get('page_refs', [])))}"):
                st.write(section.get("summary", ""))
                if section.get("confidence") is not None:
                    st.caption(f"درجة الثقة: {round(float(section['confidence']) * 100)}%")
        if not rows and not result.get("research_sections"):
            st.info("لم تُكتشف كيانات مطابقة للأنواع المحددة في هذا المستند.")
    elif tool == "analysis":
        for document in result.get("documents", []):
            metrics = document.get("metrics", {})
            cols = st.columns(4)
            cols[0].metric("الكلمات", metrics.get("words", 0))
            cols[1].metric("الجمل", metrics.get("sentences", 0))
            cols[2].metric("الحروف", metrics.get("characters_without_spaces", 0))
            cols[3].metric("متوسط الكلمة", metrics.get("average_word_length", 0))
            terms = document.get("frequent_terms", [])
            if terms:
                st.bar_chart({item["term"]: item["count"] for item in terms})
        comparison = result.get("comparison", {})
        if comparison.get("shared_topics") or comparison.get("differences"):
            with st.expander("نتيجة المقارنة", expanded=True):
                if comparison.get("shared_topics"):
                    st.markdown("#### المصطلحات المشتركة")
                    for topic in comparison["shared_topics"]:
                        counts = "، ".join(str(item.get("count", 0)) for item in topic.get("documents", []))
                        st.markdown(f"- **{topic.get('term', '')}** — مرات الظهور: {counts}")
                if comparison.get("differences"):
                    st.markdown("#### ما يميز كل مستند")
                    names = {row["version_id"]: row["name"] for row in _ready_documents(client)}
                    for difference in comparison["differences"]:
                        st.markdown(f"**{names.get(difference.get('document_version_id'), 'مستند')}**")
                        st.write("، ".join(item.get("term", "") for item in difference.get("terms", [])) or "لا توجد فروق بارزة.")
    elif tool == "mindmap":
        st.subheader(result.get("central_topic", "الخريطة الذهنية"))
        nodes = {str(node.get("id")): str(node.get("label", "")) for node in result.get("nodes", [])}
        lines = ["digraph G {", 'rankdir="RL";', 'node [shape=box, style="rounded,filled", fillcolor="#F2EBFA", color="#7651A8"];']
        for node_id, label in nodes.items():
            lines.append(f'"{node_id}" [label="{label.replace(chr(34), chr(39))}"];')
        for edge in result.get("edges", []):
            source_id, target_id = edge.get("source"), edge.get("target")
            lines.append(f'"{source_id}" -> "{target_id}";')
        lines.append("}")
        st.graphviz_chart("\n".join(lines), use_container_width=True)
    elif tool == "translation":
        coverage = result.get("coverage", {})
        st.caption(f"تمت معالجة {coverage.get('processed_pages', 0)} من {coverage.get('total_pages', 0)} صفحة — لغة المصدر: {result.get('source_language', 'unknown')}")
    elif tool == "web_search":
        for item in result.get("results", []):
            st.markdown(f"### [{item['title']}]({item['url']})")
            metadata = [item.get("engine", "")]
            if item.get("published_at"):
                metadata.append(str(item["published_at"]))
            if item.get("doi"):
                metadata.append(f"DOI: {item['doi']}")
            st.caption(" — ".join(value for value in metadata if value))
            st.write(item.get("snippet", ""))
    elif tool == "web_analysis":
        if result.get("sources"):
            st.caption("المصادر المستخدمة في التحليل")
            for source in result["sources"]:
                st.markdown(f"- [{source.get('index')}]({source.get('url')})")
    try:
        data, filename, mime = client.download_tool_result(job_id, "json")
        st.download_button("تنزيل النتيجة", data=data, file_name=filename, mime=mime, key=f"download_{job_id}")
        if isinstance(text, str):
            text_data, text_filename, text_mime = client.download_tool_result(job_id, "txt")
            st.download_button("تنزيل النص", data=text_data, file_name=text_filename, mime=text_mime, key=f"download_text_{job_id}")
    except PlatformUnavailable as exc:
        st.caption(f"تعذر تجهيز التنزيل: {exc}")


def render_platform_tools(tab2, tab3, tab4, tab5, tab6, tab7, client: PlatformClient) -> None:
    _restore_jobs(client)
    docs = _ready_documents(client)
    with tab2:
        st.header("تلخيص المستند")
        selected = _select_document("اختر الملف", docs, "platform_summary_file")
        left, middle, right = st.columns(3)
        kind = left.selectbox("نوع الملخص", ["executive", "analytical", "quick"], format_func=lambda x: {"executive": "تنفيذي", "analytical": "تحليلي", "quick": "سريع"}[x])
        length = middle.selectbox("طول الملخص", ["short", "medium", "detailed"], index=1, format_func=lambda x: {"short": "قصير", "medium": "متوسط", "detailed": "مفصل"}[x])
        bullets = right.toggle("تضمين نقاط", value=True)
        if st.button("توليد الملخص", type="primary", use_container_width=True, disabled=selected is None or _active_job(client, "summary")):
            _submit(client, "summary", {"document_version_id": selected["version_id"], "options": {"summary_type": kind, "length": length, "include_bullets": bullets}})
        _result_view(client, "summary")
    with tab3:
        st.header("استخراج الكيانات")
        selected = _select_document("اختر الملف", docs, "platform_entities_file")
        method = st.radio("طريقة الاستخراج", ["fast", "llm", "research_sections"], format_func=lambda x: {"fast": "سريع", "llm": "متقدم", "research_sections": "أقسام البحث"}[x], horizontal=True)
        entity_types = st.multiselect("أنواع الكيانات", list(ENTITY_LABELS), format_func=lambda value: ENTITY_LABELS[value], key="platform_entity_types")
        if st.button("استخراج الكيانات", type="primary", disabled=selected is None or _active_job(client, "entities")):
            _submit(client, "entities", {"document_version_id": selected["version_id"], "options": {"method": method, "entity_types": entity_types}})
        _result_view(client, "entities")
    with tab4:
        st.header("الترجمة العلمية")
        source = st.radio("مصدر النص", ["document", "direct"], format_func=lambda x: "من ملف مرفوع" if x == "document" else "إدخال يدوي", horizontal=True)
        selected = _select_document("اختر الملف", docs, "platform_translation_file") if source == "document" else None
        direct = st.text_area("النص المصدر", key="platform_translation_text") if source == "direct" else ""
        left, middle, right = st.columns(3)
        target = left.selectbox("الترجمة إلى", ["en", "ar", "fr", "de", "es", "tr"])
        style = middle.selectbox("الأسلوب", ["academic", "literal", "simple"], format_func=lambda value: {"academic": "أكاديمي", "literal": "حرفي", "simple": "مبسط"}[value])
        scope = right.selectbox("النطاق", ["full", "page", "range"], format_func=lambda value: {"full": "المستند كاملًا", "page": "صفحة", "range": "نطاق صفحات"}[value], disabled=source == "direct")
        page = st.number_input("رقم الصفحة", min_value=1, max_value=max(1, selected["page_count"] if selected else 1), value=1) if source == "document" and scope == "page" else None
        page_count = max(1, selected["page_count"] if selected else 1)
        if source == "document" and scope == "range" and page_count > 1:
            range_values = st.slider("نطاق الصفحات", 1, page_count, (1, page_count))
        elif source == "document" and scope == "range":
            range_values = (1, 1)
        else:
            range_values = None
        keep_formatting = st.toggle("الحفاظ على العناوين والقوائم والجداول", value=True)
        if st.button("بدء الترجمة", type="primary", disabled=(selected is None and not direct.strip()) or _active_job(client, "translation")):
            effective_scope = scope if source == "document" else "full"
            options = {"target_language": target, "style": style, "keep_formatting": keep_formatting, "scope": effective_scope}
            if page is not None:
                options["page"] = int(page)
            if range_values is not None:
                options["start_page"], options["end_page"] = map(int, range_values)
            payload = {"options": options}
            payload["document_version_id" if selected else "input_text"] = selected["version_id"] if selected else direct
            _submit(client, "translation", payload)
        _result_view(client, "translation")
    with tab5:
        st.header("تحليل النصوص")
        selected = st.multiselect("اختر الملفات للتحليل", docs, format_func=lambda row: row["name"], key="platform_analysis_files")
        include_topics = st.toggle("تحليل الموضوعات", value=True)
        compare = st.toggle("مقارنة الملفات", value=False, disabled=len(selected) < 2)
        if st.button("بدء التحليل", type="primary", disabled=not selected or _active_job(client, "analysis")):
            _submit(client, "analysis", {"document_version_ids": [row["version_id"] for row in selected], "options": {"include_topics": include_topics, "compare": compare}})
        _result_view(client, "analysis")
    with tab6:
        st.header("الخريطة الذهنية")
        source = st.radio("مصدر النص", ["document", "direct"], format_func=lambda x: "من ملف مرفوع" if x == "document" else "إدخال نص مباشر", horizontal=True, key="platform_mindmap_source")
        selected = _select_document("اختر الملف", docs, "platform_mindmap_file") if source == "document" else None
        direct = st.text_area("النص", key="platform_mindmap_text") if source == "direct" else ""
        nodes = st.slider("عدد العقد المستهدف", 5, 30, 15)
        if st.button("توليد الخريطة الذهنية", type="primary", disabled=(selected is None and not direct.strip()) or _active_job(client, "mindmap")):
            payload = {"options": {"target_nodes": nodes}}
            payload["document_version_id" if selected else "input_text"] = selected["version_id"] if selected else direct
            _submit(client, "mindmap", payload)
        _result_view(client, "mindmap")
    with tab7:
        st.header("البحث الأكاديمي")
        query = st.text_input("موضوع البحث", key="platform_web_query")
        category = st.selectbox("التصنيف", ["academic", "general", "news", "wikipedia"], format_func=lambda x: {"academic": "أكاديمي", "general": "عام", "news": "أخبار", "wikipedia": "ويكيبيديا"}[x])
        language = st.selectbox("لغة البحث", ["auto", "ar", "en"], format_func=lambda x: {"auto": "تلقائي", "ar": "العربية", "en": "الإنجليزية"}[x])
        if st.button("بحث", type="primary", disabled=len(query.strip()) < 2 or _active_job(client, "web_search")):
            _submit(client, "web_search", {"input_text": query, "options": {"category": category, "language": language, "max_results": 10}})
        _result_view(client, "web_search")
        search_job = _state().get("web_search")
        if search_job:
            try:
                search_state = client.job(search_job)
                if search_state.get("status") == "completed" and st.button("تحليل نتائج البحث", disabled=_active_job(client, "web_analysis")):
                    _submit(client, "web_analysis", {"source_job_id": search_job, "options": {"language": "ar"}})
            except PlatformUnavailable:
                pass
        _result_view(client, "web_analysis")
