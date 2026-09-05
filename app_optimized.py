# app_optimized.py
import streamlit as st
import time
import os
from datetime import datetime
import uuid
import struct
import wave

import json
import networkx as nx
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from collections import Counter
import io
import requests
import html

if "current_text" not in st.session_state:
    st.session_state.current_text = ""

# محرك البحث على الإنترنت
try:
    from web_search import WebSearchEngine
    web_search_engine = WebSearchEngine()
    WEB_SEARCH_AVAILABLE = True
except ImportError:
    WEB_SEARCH_AVAILABLE = False
    web_search_engine = None

from processor_optimized import OptimizedDocumentProcessor
from engine_optimized import OptimizedRAGEngine
from indexing_jobs import indexing_jobs
from utils import (
    get_scholar_link_cached,
    save_support_ticket_optimized,
    create_fancy_download_button_optimized,
    format_file_size,
    validate_pdf_file,
)

# مكتبات NLP الذكية
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

# مستخرج أقسام البحث العلمي
from research_extractor import get_research_report, extract_research_sections

# ═══════════════════════════════════════════════════════════════
# المكتبات الجديدة للتحليل المتقدم
# ═══════════════════════════════════════════════════════════════

# معالج النص العربي
try:
    from arabic_text_processor import ArabicTextProcessor, reshape_arabic, normalize_arabic
    arabic_processor = ArabicTextProcessor()
    ARABIC_PROCESSOR_AVAILABLE = True
except ImportError:
    ARABIC_PROCESSOR_AVAILABLE = False
    arabic_processor = None

# مولد الخرائط الذهنية المتقدم
try:
    from advanced_mindmap import AdvancedMindMapGenerator
    ADVANCED_MINDMAP_AVAILABLE = True
except ImportError:
    ADVANCED_MINDMAP_AVAILABLE = False

# مكتبة Prompts الذكية
try:
    from intelligent_prompts_library import IntelligentPromptsLibrary, AnalysisType
    prompts_library = IntelligentPromptsLibrary(language="ar")
    PROMPTS_LIBRARY_AVAILABLE = True
except ImportError:
    PROMPTS_LIBRARY_AVAILABLE = False
    prompts_library = None


# ==========================================
# 0. إعداد الصفحة والتصميم
# ==========================================
st.set_page_config(
    page_title="مساحة البحث الأكاديمي الذكية",
    layout="wide",
    page_icon="◈",
    initial_sidebar_state="auto"
)
st.set_option("client.toolbarMode", "viewer")

# تحميل الـ CSS
def local_css(file_name):
    try:
        with open(file_name, encoding='utf-8') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except:
        # CSS افتراضي إذا لم يوجد ملف
        st.markdown("""
        <style>
        .paper-container {
            background: linear-gradient(180deg, #f9f9f9 0%, #ffffff 100%);
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 0;
            font-family: 'Arial', sans-serif;
            line-height: 1.6;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .performance-metric {
            background: white;
            padding: 10px;
            border-radius: 5px;
            margin: 5px 0;
            border-left: 4px solid #4CAF50;
        }
        .stProgress > div > div > div > div {
            background-color: #4CAF50;
        }
        </style>
        """, unsafe_allow_html=True)

local_css("style.css")

# عناصر HTML للديكور
typewriter_html = """<div class="typewriter"><div class="slide"><i></i></div><div class="paper"></div><div class="keyboard"></div></div>"""
pencil_html = """<div class="pencil"><div class="pencil__body1"></div><div class="pencil__body2"></div><div class="pencil__body3"></div><div class="pencil__eraser"></div><div class="pencil__eraser-skew"></div><div class="pencil__point"></div><div class="pencil__rotate"></div><div class="pencil__stroke"></div></div>"""

# ==========================================
# 1. تهيئة Session State
# ==========================================
if "rag_engine" not in st.session_state:
    st.session_state.rag_engine = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_full_text" not in st.session_state:
    st.session_state.last_full_text = {}
if "last_file_pages" not in st.session_state:
    st.session_state.last_file_pages = {}
if "performance_data" not in st.session_state:
    st.session_state.performance_data = {}
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "processing_queue" not in st.session_state:
    st.session_state.processing_queue = []
if "mindmaps" not in st.session_state:
    st.session_state.mindmaps = {}
if "indexed_files" not in st.session_state:
    st.session_state.indexed_files = []
if "db_files_loaded" not in st.session_state:
    st.session_state.db_files_loaded = False
if "voice_text" not in st.session_state:
    st.session_state.voice_text = ""
if "active_document" not in st.session_state:
    st.session_state.active_document = None
# القيم الافتراضية للإعدادات المتقدمة
if "chunk_size" not in st.session_state:
    st.session_state.chunk_size = 2000
if "chunk_overlap" not in st.session_state:
    st.session_state.chunk_overlap = 300
if "selected_model" not in st.session_state:
    st.session_state.selected_model = os.getenv(
        "OPENROUTER_MODEL", "qwen/qwen3-30b-a3b-instruct-2507"
    )
if "batch_size" not in st.session_state:
    st.session_state.batch_size = 500
if "enable_cache" not in st.session_state:
    st.session_state.enable_cache = True
if "processing_mode" not in st.session_state:
    st.session_state.processing_mode = "تلقائي"
if "force_ocr" not in st.session_state:
    st.session_state.force_ocr = False
if "tour_active" not in st.session_state:
    st.session_state.tour_active = True
if "tour_step" not in st.session_state:
    st.session_state.tour_step = 1
if "tour_completed" not in st.session_state:
    st.session_state.tour_completed = False
if "tour_manual_restart" not in st.session_state:
    st.session_state.tour_manual_restart = False
if "tour_last_completed_step" not in st.session_state:
    st.session_state.tour_last_completed_step = 0
if "tour_index_completed" not in st.session_state:
    st.session_state.tour_index_completed = False
if "tour_index_error" not in st.session_state:
    st.session_state.tour_index_error = False
if "tour_confirmation" not in st.session_state:
    st.session_state.tour_confirmation = ""
if "tour_hold_step_once" not in st.session_state:
    st.session_state.tour_hold_step_once = False
if "tour_pending_prompt" not in st.session_state:
    st.session_state.tour_pending_prompt = ""
if "indexing_job_id" not in st.session_state:
    query_job_id = st.query_params.get("index_job", "")
    st.session_state.indexing_job_id = query_job_id if isinstance(query_job_id, str) else ""

def load_indexed_files_from_db():
    """تحميل قائمة الملفات المفهرسة من قاعدة البيانات"""
    if st.session_state.rag_engine and not st.session_state.db_files_loaded:
        try:
            indexed_files = st.session_state.rag_engine.get_indexed_files()
            if indexed_files:
                st.session_state.indexed_files = indexed_files
                # إضافة placeholder للملفات المفهرسة
                for f in indexed_files:
                    if f not in st.session_state.last_full_text:
                        st.session_state.last_full_text[f] = "[ملف مفهرس سابقاً - اضغط لتحميل المحتوى]"
                st.session_state.db_files_loaded = True
                return True
        except Exception as e:
            pass
    return False    

def get_file_content_safe(filename: str) -> str:
    """استرجاع محتوى الملف بأمان (من الذاكرة أو قاعدة البيانات إذا لم يكن متاحاً)"""
    txt = st.session_state.last_full_text.get(filename, "")
    if not txt or txt.startswith("[ملف مفهرس"):
        if st.session_state.rag_engine and hasattr(st.session_state.rag_engine, 'get_document_text_from_db'):
            with st.spinner(f"جاري جلب محتوى الملف {filename} من قاعدة البيانات..."):
                fetched_txt = st.session_state.rag_engine.get_document_text_from_db(filename)
                if fetched_txt:
                    st.session_state.last_full_text[filename] = fetched_txt
                    txt = fetched_txt
                else:
                    return ""
    return txt

# ==========================================
# 2. الوظائف المساعدة
# ==========================================
def display_performance_metrics():
    """عرض مقاييس الأداء"""
    if st.session_state.rag_engine and hasattr(st.session_state.rag_engine, 'get_system_stats'):
        stats = st.session_state.rag_engine.get_system_stats()
        
        with st.expander("إحصائيات النظام", expanded=False, icon=":material/monitoring:"):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("إجمالي الاستعلامات", stats['total_queries'])
            
            with col2:
                st.metric("المستندات المفهرسة", stats['index_size'])
            
            with col3:
                st.metric("ضربات الـ Cache", stats['cache_hits'])
            
            with col4:
                st.metric("نسبة الـ Cache", f"{stats['cache_hit_rate']:.1f}%")
            
            # عرض مقترحات التحسين
            if hasattr(st.session_state.rag_engine, 'monitor'):
                suggestions = st.session_state.rag_engine.monitor.get_suggestions()
                if suggestions:
                    st.warning("مقترحات تحسين:")
                    for suggestion in suggestions:
                        st.write(f"- {suggestion}")

def create_mindmap_from_text(text, max_concepts=20):
    """إنشاء خريطة ذهنية هرمية من النص - نسخة سريعة وواضحة"""
    try:
        if not st.session_state.rag_engine:
            return None

        # برومبت مبسط وسريع: يطلب Markdown هرمي مباشر
        mindmap_prompt = f"""أنت خبير في تلخيص الأوراق العلمية.

اقرأ النص التالي ثم أنشئ خريطة ذهنية هرمية واضحة باللغة العربية.
استخدم هذا التنسيق بالضبط (Markdown هرمي):

# الموضوع الرئيسي للورقة
## 1. الفكرة/القسم الأول
### تفصيل أ
### تفصيل ب
## 2. الفكرة/القسم الثاني
### تفصيل أ
### تفصيل ب
## 3. المنهجية
### خطوة 1
### خطوة 2
## 4. النتائج الرئيسية
### نتيجة 1
### نتيجة 2
## 5. الاستنتاجات والتوصيات
### استنتاج 1
### استنتاج 2

قواعد مهمة:
- لا تكتب أي نص خارج الهيكل الهرمي
- استخدم # و## و### فقط
- كل سطر يبدأ بـ # أو ## أو ###
- لا تضع نقاط أو أرقام قبل العناوين
- اجعل الخريطة شاملة ومفيدة (7-12 فرع رئيسي)

النص:
{text[:6000]}"""

        response = st.session_state.rag_engine.llm.invoke(mindmap_prompt, feature="mindmap")

        # استخراج الـ Markdown الهرمي من الاستجابة
        import re
        lines = response.strip().split('\n')
        md_lines = [l for l in lines if l.strip().startswith('#')]
        clean_md = '\n'.join(md_lines) if md_lines else response

        # تحويل الـ Markdown إلى بنية JSON متوافقة مع الكود الحالي
        central_topic = "الخريطة الذهنية"
        main_concepts = []
        current_main = None

        for line in md_lines:
            stripped = line.strip()
            if stripped.startswith('### '):
                sub = stripped[4:].strip()
                if current_main is not None:
                    current_main["sub_concepts"].append(sub)
            elif stripped.startswith('## '):
                title = stripped[3:].strip()
                # إزالة الأرقام من البداية إن وجدت
                title = re.sub(r'^\d+\.\s*', '', title)
                current_main = {"concept": title, "weight": 1.0, "sub_concepts": [], "related_concepts": []}
                main_concepts.append(current_main)
            elif stripped.startswith('# '):
                central_topic = stripped[2:].strip()

        mindmap_data = {
            "central_topic": central_topic,
            "main_concepts": main_concepts[:max_concepts],
            "keywords": [],
            "relationships": [],
            "_markdown": clean_md  # نحتفظ بالـ Markdown للعرض المباشر
        }
        return mindmap_data

    except Exception:
        st.error("تعذر إنشاء الخريطة الذهنية الآن. تحقق من النص وحاول مرة أخرى.")
        return None

def extract_simple_mindmap(text):
    """استخراج خريطة ذهنية مبسطة من النص"""
    words = [word for word in text.split() if len(word) > 3]
    word_freq = Counter(words)
    top_keywords = [word for word, freq in word_freq.most_common(10)]
    return {
        "central_topic": "الموضوع المستخلص",
        "main_concepts": [
            {"concept": keyword, "weight": 1.0, "sub_concepts": [], "related_concepts": []} 
            for keyword in top_keywords[:5]
        ],
        "keywords": top_keywords,
        "relationships": []
    }

def visualize_mindmap_interactive(mindmap_data):
    """تصور الخريطة الذهنية بشكل تفاعلي"""
    if not mindmap_data: return None
    G = nx.Graph()
    central_topic = mindmap_data.get("central_topic", "الموضوع الرئيسي")
    G.add_node(central_topic, size=30, color='#FF6B6B', type='central')
    
    for concept in mindmap_data.get("main_concepts", []):
        concept_name = concept.get("concept", "")
        if concept_name:
            G.add_node(concept_name, size=20, color='#4ECDC4', type='main')
            G.add_edge(central_topic, concept_name, weight=concept.get("weight", 1))
            for sub in concept.get("sub_concepts", [])[:3]:
                if sub:
                    G.add_node(sub, size=10, color='#FFD166', type='sub')
                    G.add_edge(concept_name, sub, weight=0.5)
    
    for rel in mindmap_data.get("relationships", [])[:10]:
        source, target = rel.get("source", ""), rel.get("target", "")
        if source and target and source in G.nodes() and target in G.nodes():
            G.add_edge(source, target, weight=rel.get("strength", 1))
            
    if len(G.nodes()) == 0: return None
    
    pos = nx.spring_layout(G, seed=42)
    node_x, node_y, node_text, node_size, node_color = [], [], [], [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x); node_y.append(y); node_text.append(node)
        attrs = G.nodes[node]
        if attrs.get('type') == 'central': s, c = 30, '#FF6B6B'
        elif attrs.get('type') == 'main': s, c = 20, '#4ECDC4'
        else: s, c = 10, '#FFD166'
        node_size.append(s); node_color.append(c)
        
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]; x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
        
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#888'), hoverinfo='none', mode='lines'))
    fig.add_trace(go.Scatter(x=node_x, y=node_y, mode='markers+text', text=node_text, textposition="top center", marker=dict(color=node_color, size=node_size, line=dict(width=2, color='white'))))
    fig.update_layout(showlegend=False, hovermode='closest', margin=dict(b=0,l=0,r=0,t=40), xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False), plot_bgcolor='white', height=500)
    return fig

def create_text_mindmap(mindmap_data):
    """إنشاء تمثيل نصي للخريطة الذهنية"""
    if not mindmap_data: return "لا توجد بيانات"
    output = f"# الخريطة الذهنية: {mindmap_data.get('central_topic')}\n\n"
    output += "## المفاهيم الرئيسية\n"
    for i, c in enumerate(mindmap_data.get("main_concepts", []), 1):
        output += f"{i}. **{c.get('concept')}**\n"
        if c.get("sub_concepts"): output += "   - " + " | ".join([f"`{sc}`" for sc in c.get("sub_concepts")[:5]]) + "\n"
    return output

def get_text_by_words(text, max_words=2000, strategy="smart"):
    """
    استخراج نص بالكلمات بدل الحروف - للحصول على تحليل أشمل
    
    Args:
        text: النص الكامل
        max_words: الحد الأقصى للكلمات
        strategy: 
            "first" - أول max_words كلمة
            "smart" - أول 70% + آخر 30% (لتغطية المقدمة والنتائج)
            "full" - النص كاملاً (بدون قطع)
    """
    words = text.split()
    total_words = len(words)
    
    if total_words <= max_words:
        return text, total_words
    
    if strategy == "first":
        return " ".join(words[:max_words]), total_words
    elif strategy == "smart":
        first_part = int(max_words * 0.7)
        last_part = max_words - first_part
        result = " ".join(words[:first_part]) + "\n\n[...]\n\n" + " ".join(words[-last_part:])
        return result, total_words
    else:
        return text, total_words

def analyze_text_in_chunks(text, prompt_template, rag_engine, max_words_per_chunk=1500, merge_prompt=None):
    """
    تحليل نص كبير عن طريق تقسيمه لأجزاء وتحليل كل جزء ثم دمج النتائج
    
    Args:
        text: النص الكامل
        prompt_template: قالب البرومبت (يحتوي على {text} كمتغير)
        rag_engine: محرك RAG
        max_words_per_chunk: حد الكلمات لكل جزء
        merge_prompt: برومبت لدمج النتائج (اختياري)
    """
    words = text.split()
    total_words = len(words)
    
    # لو النص صغير كفاية، حلله مباشرة
    if total_words <= max_words_per_chunk:
        prompt = prompt_template.replace("{text}", text)
        return rag_engine.llm.invoke(prompt, feature="advanced_analysis")
    
    # تقسيم النص لأجزاء
    chunks = []
    for i in range(0, total_words, max_words_per_chunk):
        chunk_words = words[i:i + max_words_per_chunk]
        chunks.append(" ".join(chunk_words))
    
    # المعالجة المتوازية لتسريع التحليل (حتى 4 عمليات متزامنة)
    from concurrent.futures import ThreadPoolExecutor, as_completed
    results_dict = {}
    
    def process_chunk(index, chunk):
        chunk_prompt = prompt_template.replace("{text}", chunk)
        chunk_prompt = f"[الجزء {index+1} من {len(chunks)}]\n\n" + chunk_prompt
        result = rag_engine.llm.invoke(chunk_prompt, feature="advanced_analysis")
        return index, f"### 📄 الجزء {index+1} (كلمات {index*max_words_per_chunk+1} إلى {min((index+1)*max_words_per_chunk, total_words)}):\n{result}"
        
    with ThreadPoolExecutor(max_workers=min(4, len(chunks))) as executor:
        future_to_index = {executor.submit(process_chunk, i, chunk): i for i, chunk in enumerate(chunks)}
        for future in as_completed(future_to_index):
            i = future_to_index[future]
            try:
                index, result = future.result()
                results_dict[index] = result
            except Exception as exc:
                raise RuntimeError("تعذر تحليل أحد أجزاء المستند.") from exc
    
    # ترتيب النتائج بناءً على الفهرس
    results = [results_dict[i] for i in range(len(chunks))]
    
    # دمج النتائج
    combined = "\n\n---\n\n".join(results)
    
    if merge_prompt and len(chunks) > 1:
        # دمج ذكي بالنموذج
        merge_text = merge_prompt.replace("{results}", combined[:6000])
        try:
            merged = rag_engine.llm.invoke(merge_text, feature="advanced_analysis")
            return f"## 📋 الملخص المدمج:\n{merged}\n\n---\n\n## 📑 التفاصيل بالأجزاء:\n{combined}"
        except Exception as exc:
            raise RuntimeError("تعذر دمج نتائج التحليل.") from exc
    
    return combined
                     

# ==========================================
# 3. الواجهة الرئيسية
# ==========================================

# --- UI helpers ---
MODEL_LABELS = {
    "qwen/qwen3-30b-a3b-instruct-2507": "Qwen 3 — متوازن",
}


def initialize_workspace():
    """تهيئة المحرك من الواجهة دون تغيير سلوكه أو إعدادات الاسترجاع."""
    try:
        engine = OptimizedRAGEngine(model_name=st.session_state.selected_model)
        engine.get_vectorstore()
        st.session_state.rag_engine = engine
        st.session_state.db_files_loaded = False
        load_indexed_files_from_db()
        return True
    except Exception:
        st.session_state.rag_engine = None
        return False


def _format_duration(seconds):
    if seconds is None:
        return "يُحسب بعد بدء مرحلة المعالجة"
    seconds = max(0, int(seconds))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours} س {minutes} د"
    if minutes:
        return f"{minutes} د {seconds} ث"
    return f"{seconds} ث"


def _attach_completed_indexing_job(status):
    """Reconnect a refreshed browser session to its completed background job."""
    if status.get("state") != "completed":
        return
    engine = indexing_jobs.get_engine(status.get("id"))
    if engine is not None:
        st.session_state.rag_engine = engine
    indexed_names = status.get("indexed_files", [])
    if indexed_names:
        st.session_state.indexed_files = list(dict.fromkeys(
            st.session_state.indexed_files + indexed_names
        ))
        for name in indexed_names:
            st.session_state.last_full_text.setdefault(
                name, "[ملف مفهرس سابقاً - اضغط لتحميل المحتوى]"
            )
    st.session_state.tour_index_completed = True
    st.session_state.tour_index_error = False


def render_indexing_job_status():
    """Show durable job state and poll it without rerunning the whole app."""
    job_id = st.session_state.get("indexing_job_id", "")
    if not job_id:
        return

    def draw_status():
        status = indexing_jobs.get_status(job_id)
        if not status:
            st.warning("لم تعد حالة مهمة الفهرسة متاحة. يمكنك بدء مهمة جديدة من الملفات المرفوعة.")
            return
        state = status.get("state", "queued")
        progress = int(status.get("progress", 0))
        if state in {"queued", "running"}:
            st.progress(progress, text=f"{progress}% — {status.get('phase', 'جاري التحضير')}")
            st.caption(status.get("message", "تعمل المهمة في الخلفية."))
            details = [f"الوقت المنقضي: {_format_duration(status.get('elapsed_seconds'))}"]
            if status.get("eta_seconds") is not None:
                details.append(f"المتبقي التقريبي: {_format_duration(status.get('eta_seconds'))}")
            active_file = status.get("active_file")
            if active_file:
                details.append(f"الملف الحالي: {active_file}")
            completed = status.get("completed_files", 0)
            total = status.get("total_files", 0)
            if total:
                details.append(f"الملفات المكتملة: {completed}/{total}")
            st.caption(" · ".join(details))
            st.info("الفهرسة مستمرة حتى عند تحديث الصفحة. لا تغلق خدمة التطبيق أثناء التنفيذ.")
        elif state == "completed":
            _attach_completed_indexing_job(status)
            st.success(status.get("message", "اكتملت الفهرسة بنجاح."))
            if status.get("failed_files"):
                st.warning("لم تُفهرس بعض الملفات: " + "، ".join(status["failed_files"]))
        elif state == "interrupted":
            st.warning(status.get("message", "توقفت مهمة الفهرسة."))
        else:
            st.error(status.get("message", "تعذر إكمال الفهرسة."))
            st.session_state.tour_index_error = True

        # A fragment rerun updates only this status card. When a job reaches a
        # terminal state, refresh the whole sidebar once so the primary button
        # cannot remain labelled "running" beside a completed-job message.
        if state not in {"queued", "running"} and st.session_state.get("indexing_terminal_sync") != job_id:
            st.session_state.indexing_terminal_sync = job_id
            st.rerun(scope="app")

    if hasattr(st, "fragment"):
        @st.fragment(run_every="2s")
        def live_status_fragment():
            draw_status()
        live_status_fragment()
    else:
        draw_status()


def start_background_indexing(uploaded_files):
    valid_files = []
    rejected_files = []
    for uploaded_file in uploaded_files:
        is_valid, validation_message = validate_pdf_file(uploaded_file)
        if is_valid:
            valid_files.append((uploaded_file.name, uploaded_file.getvalue()))
        else:
            rejected_files.append(f"{uploaded_file.name}: {validation_message}")
    if not valid_files:
        st.session_state.tour_index_error = True
        st.error("لم يوجد ملف PDF صالح للفهرسة. تحقق من الملفات ثم حاول مرة أخرى.")
        return
    if rejected_files:
        st.warning("لم تُقبل بعض الملفات: " + "، ".join(rejected_files))
    configured_mode = st.session_state.processing_mode
    parallel = configured_mode == "متوازي" or (
        configured_mode == "تلقائي" and len(valid_files) > 1
    )
    try:
        job_id = indexing_jobs.start_job(
            valid_files,
            chunk_size=st.session_state.chunk_size,
            chunk_overlap=st.session_state.chunk_overlap,
            batch_size=st.session_state.batch_size,
            force_ocr=st.session_state.force_ocr,
            parallel=parallel,
            model_name=st.session_state.selected_model,
        )
    except RuntimeError:
        st.info("هناك مهمة فهرسة أخرى تعمل الآن. تابع نسبة التقدم الظاهرة قبل بدء مهمة جديدة.")
        return
    st.session_state.indexing_job_id = job_id
    st.session_state.indexing_terminal_sync = ""
    st.session_state.tour_index_error = False
    st.session_state.tour_index_completed = False
    st.query_params["index_job"] = job_id
    st.rerun()


def render_product_header():
    st.markdown(
        """
        <section class="product-header" dir="rtl">
            <div class="product-kicker">مساحة بحث مدعومة بالذكاء الاصطناعي</div>
            <h1>محرك البحث الأكاديمي الذكي</h1>
            <p>ابحث، حلّل، ولخّص مستنداتك بوضوح وفي مكان واحد.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def derive_workflow_step(uploaded_files):
    """Return the permanent product step from the same facts used by onboarding."""
    if st.session_state.tour_active:
        return max(1, min(5, st.session_state.tour_step))
    if st.session_state.messages:
        return 5
    if st.session_state.active_document:
        return 4
    if st.session_state.tour_index_completed or st.session_state.indexed_files:
        return 3
    if uploaded_files:
        return 2
    return 1


def render_workflow_steps(uploaded_files):
    current_step = derive_workflow_step(uploaded_files)
    labels = ["رفع المستند", "الفهرسة", "اختيار النطاق", "استخدام الأدوات"]
    steps = []
    for number, label in enumerate(labels, 1):
        is_complete = number < current_step
        state = "is-complete" if is_complete else "is-active" if number == current_step else ""
        marker = '<i class="material-symbols-rounded">check</i>' if is_complete else str(number)
        steps.append(
            f'<div class="workflow-step {state}"><span>{marker}</span><small>{label}</small></div>'
        )
    st.markdown(
        f'<div class="workflow-steps" dir="rtl">{"".join(steps)}</div>',
        unsafe_allow_html=True,
    )


def render_document_context():
    active_label = html.escape(st.session_state.active_document or "كل المستندات")
    is_global = st.session_state.active_document is None
    heading = "نطاق البحث" if is_global else "المستند النشط"
    icon_name = "library_books" if is_global else "task"
    state_label = "جاهز للتحليل" if st.session_state.rag_engine else "جاهز بعد الفهرسة"
    st.markdown(
        f"""
        <div class="document-context" dir="rtl">
            <div class="document-context__identity">
                <span class="material-symbols-rounded" aria-hidden="true">{icon_name}</span>
                <div><small>{heading}</small><strong>{active_label}</strong></div>
            </div>
            <b><span class="status-dot"></span>{state_label}</b>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(icon_name, title, body):
    st.markdown(
        f"""
        <div class="empty-state" dir="rtl">
            <span class="material-symbols-rounded" aria-hidden="true">{icon_name}</span>
            <div><strong>{title}</strong><p>{body}</p></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_chat_header():
    """Render the compact, persistent context for the conversation workspace."""
    active_document = st.session_state.active_document
    scope = html.escape(active_document or "كل المستندات")
    scope_icon = "description" if active_document else "library_books"
    st.markdown(
        f"""
        <section class="chat-workspace__header" dir="rtl">
            <div>
                <h2>المحادثة</h2>
                <p>اسأل عن المحتوى، وستظهر الإجابة ومصادرها هنا.</p>
            </div>
            <div class="chat-workspace__scope">
                <span class="material-symbols-rounded" aria-hidden="true">{scope_icon}</span>
                <span><small>أنت تسأل عن</small><b dir="auto">{scope}</b></span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_chat_sources(sources, include_scholar_links=False, instance_key=""):
    """Keep document provenance visually attached to its assistant response."""
    if not sources:
        return
    chips = "".join(
        (
            '<span class="chat-source-chip" dir="auto">'
            '<span class="material-symbols-rounded" aria-hidden="true">description</span>'
            f'<span>{html.escape(str(source))}</span>'
            '</span>'
        )
        for source in sources[:5]
    )
    st.markdown(
        f"""
        <footer class="chat-sources" dir="rtl">
            <span class="chat-sources__label">المصادر</span>
            <div class="chat-sources__list">{chips}</div>
        </footer>
        """,
        unsafe_allow_html=True,
    )
    if len(sources) > 5:
        st.caption(f"و {len(sources) - 5} مصادر أخرى...")
    if include_scholar_links:
        with st.expander("روابط أكاديمية خارجية", expanded=False, icon=":material/open_in_new:"):
            st.caption("هذه روابط بحث خارجية وليست من أدلة المستند المستخدم في الإجابة.")
            for index, source in enumerate(sources[:5]):
                st.link_button(
                    f"البحث عن {source} في Scholar",
                    get_scholar_link_cached(source),
                    icon=":material/open_in_new:",
                    key=f"chat_scholar_{instance_key}_{index}",
                    use_container_width=True,
                )


def render_result_card(icon_name, title, content, context=None):
    """Render generated output in one consistent, safe product surface."""
    safe_title = html.escape(title)
    safe_context = html.escape(str(context)) if context else ""
    context_html = f"<small>{safe_context}</small>" if safe_context else ""
    with st.container(border=True):
        st.markdown(
            f"""
            <div class="result-card__header" dir="rtl">
                <span class="material-symbols-rounded" aria-hidden="true">{icon_name}</span>
                <div><strong>{safe_title}</strong>{context_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(content)


TOUR_STEPS = {
    1: ("رفع المستندات", "ابدأ برفع ملف PDF أو أكثر. سننتقل تلقائيًا للخطوة التالية بعد اختيار الملفات."),
    2: ("فهرسة المستند", "الملفات جاهزة. ابدأ الفهرسة حتى يستطيع النظام البحث داخل محتواها."),
    3: ("المستند النشط", "اختر المستند الذي تريد العمل عليه. ستكون الإجابات والتحليلات مرتبطة بالمستند المحدد."),
    4: ("ابدأ المحادثة", "اسأل الآن أي سؤال عن المستند المحدد. سيستخدم النظام محتوى هذا المستند للإجابة."),
    5: ("أدوات المستند", "أصبح المستند جاهزًا. يمكنك الآن استخدام التلخيص، الكيانات، الترجمة، التحليل، الخريطة الذهنية، والبحث الأكاديمي."),
}


def end_tour(completed=False):
    st.session_state.tour_active = False
    st.session_state.tour_completed = completed
    st.session_state.tour_manual_restart = False
    if completed:
        st.session_state.tour_last_completed_step = 5


def restart_tour():
    st.session_state.tour_active = True
    st.session_state.tour_step = 1
    st.session_state.tour_completed = False
    st.session_state.tour_manual_restart = True
    st.session_state.tour_last_completed_step = 0
    st.session_state.tour_index_completed = False
    st.session_state.tour_index_error = False
    st.session_state.tour_confirmation = ""
    st.session_state.tour_hold_step_once = True


def sync_tour_with_actions(uploaded_files):
    """Advance at most one action-driven step during a normal Streamlit rerun."""
    if not st.session_state.tour_active:
        return
    if st.session_state.tour_hold_step_once:
        st.session_state.tour_hold_step_once = False
        return
    step = st.session_state.tour_step
    if step == 1 and uploaded_files:
        st.session_state.tour_last_completed_step = 1
        st.session_state.tour_step = 2
        st.session_state.tour_confirmation = "تم اختيار الملفات."
    elif step == 2 and st.session_state.tour_index_completed:
        st.session_state.tour_last_completed_step = 2
        st.session_state.tour_step = 3
        st.session_state.tour_confirmation = "تمت الفهرسة بنجاح."
    elif step == 3 and st.session_state.active_document:
        st.session_state.tour_last_completed_step = 3
        st.session_state.tour_step = 4
        st.session_state.tour_confirmation = "تم تحديد المستند النشط."


def render_guided_tour():
    """Render a non-modal floating coach card; the real highlighted control stays primary."""
    if not st.session_state.tour_active:
        with st.container(key="tour_coach"):
            st.markdown('<span class="tour-inactive"></span>', unsafe_allow_html=True)
        return
    step = max(1, min(5, st.session_state.tour_step))
    title, description = TOUR_STEPS[step]
    # Share widget identity only across the chat→tools hand-off. That transition
    # happens before a potentially slow provider call, so the old controls must
    # be replaced immediately; other steps retain independent navigation state.
    control_key = "chat_tools" if step in (4, 5) else str(step)
    with st.container(key="tour_coach", border=True):
        st.markdown(f'<span class="tour-marker tour-step-{step}"></span>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="tour-card" dir="rtl">
                <div class="tour-card__eyebrow"><span>جولة تعريفية</span><b>الخطوة {step} من 5</b></div>
                <div class="tour-progress"><b style="width:{step * 20}%"></b></div>
                <h3>{title}</h3><p>{description}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.session_state.tour_confirmation:
            st.caption(st.session_state.tour_confirmation)
            st.session_state.tour_confirmation = ""
        if step == 2 and st.session_state.tour_index_error:
            st.caption("لم تكتمل الفهرسة. راجع رسالة الحالة ثم حاول مرة أخرى.")
        if step < 5:
            st.caption("نفّذ الخطوة المضاءة للمتابعة تلقائيًا.")
        previous_col, skip_col, next_col = st.columns([1, 1.3, 1])
        with previous_col:
            if st.button("السابق", disabled=step == 1, use_container_width=True, key=f"tour_previous_{control_key}"):
                st.session_state.tour_step = step - 1
                st.session_state.tour_hold_step_once = True
                st.rerun()
        with skip_col:
            st.button(
                "تخطي الجولة",
                type="tertiary",
                use_container_width=True,
                key=f"tour_skip_{control_key}",
                on_click=end_tour,
                args=(False,),
            )
        with next_col:
            label = "إنهاء الجولة" if step == 5 else "التالي"
            completed_real_action = (
                (step == 1 and bool(st.session_state.get("tour_target_upload")))
                or (step == 2 and st.session_state.tour_index_completed)
            )
            manual_next_allowed = step >= 3 or completed_real_action
            if st.button(label, type="primary" if step == 5 else "secondary", disabled=not manual_next_allowed, use_container_width=True, key=f"tour_next_{control_key}"):
                if step == 5:
                    end_tour(True)
                else:
                    st.session_state.tour_step = step + 1
                    st.session_state.tour_hold_step_once = True
                st.rerun()


@st.dialog("الإعدادات", width="large", icon=":material/settings:")
def show_settings_dialog():
    st.markdown("### نموذج الذكاء الاصطناعي")
    configured_model = os.getenv("OPENROUTER_MODEL", "qwen/qwen3-30b-a3b-instruct-2507")
    model_options = list(dict.fromkeys([st.session_state.selected_model, configured_model]))
    st.selectbox(
        "النموذج النشط",
        model_options,
        key="selected_model",
        format_func=lambda slug: MODEL_LABELS.get(slug, slug),
        help="يظهر الاسم التقني هنا فقط لأغراض الإعداد.",
    )

    st.markdown("### معالجة المستندات")
    setting_col1, setting_col2 = st.columns(2)
    with setting_col1:
        processing_mode = st.selectbox(
            "طريقة المعالجة",
            ["تلقائي", "متسلسل", "متوازي"],
            index=["تلقائي", "متسلسل", "متوازي"].index(st.session_state.processing_mode),
        )
        chunk_size = st.slider(
            "حجم الجزء النصي", 800, 2000, value=st.session_state.chunk_size, step=100
        )
        chunk_overlap = st.slider(
            "تداخل الأجزاء", 50, 300, value=st.session_state.chunk_overlap, step=10
        )
    with setting_col2:
        batch_size = st.slider(
            "حجم دفعة الفهرسة", 100, 500, value=st.session_state.batch_size, step=50
        )
        force_ocr = st.toggle("استخدام OCR إجبارياً", value=st.session_state.force_ocr)
        enable_cache = st.toggle("تفعيل التخزين المؤقت", value=st.session_state.enable_cache)

    st.markdown("### النظام")
    status_col, action_col = st.columns([2, 1])
    with status_col:
        state = "جاهزة" if st.session_state.rag_engine else "غير مهيأة"
        st.write(f"حالة مساحة العمل: **{state}**")
    with action_col:
        if st.button("تهيئة الآن", icon=":material/power_settings_new:", use_container_width=True):
            with st.spinner("جاري تجهيز مساحة العمل..."):
                if initialize_workspace():
                    st.success("مساحة العمل جاهزة.")
                    st.rerun()
                else:
                    st.error("تعذر تجهيز مساحة العمل. حاول مرة أخرى.")

    with st.expander("تشخيص الخدمات"):
        if st.button("تشغيل الفحص", icon=":material/health_and_safety:", use_container_width=True):
            if not st.session_state.rag_engine:
                st.warning("هيّئ مساحة العمل أولاً.")
            else:
                health = st.session_state.rag_engine.check_services_health()
                st.write("OpenRouter", "متصل" if health["provider"]["status"] else "غير متصل")
                st.write("OpenSearch", "متصل" if health["opensearch"]["status"] else "غير متصل")
                st.write("Redis", health["redis"]["message"])
                try:
                    sx_resp = requests.get("http://searxng:8080/healthz", timeout=3)
                    sx_ok = sx_resp.status_code == 200
                except Exception:
                    sx_ok = False
                st.write("SearXNG", "متصل" if sx_ok else "غير متصل")

    with st.expander("خيارات متقدمة وخطرة"):
        if st.button("مسح الذاكرة المؤقتة", icon=":material/cleaning_services:", use_container_width=True):
            if st.session_state.rag_engine:
                st.session_state.rag_engine._query_cache.clear()
                st.session_state.rag_engine._metadata_cache.clear()
                st.success("تم مسح الذاكرة المؤقتة.")
        confirm_clear = st.checkbox("أفهم أن مسح الفهرس لا يمكن التراجع عنه")
        if st.button("مسح فهرس المستندات", type="primary", icon=":material/delete_forever:", disabled=not confirm_clear, use_container_width=True, key="clear_index_danger"):
            if st.session_state.rag_engine and st.session_state.rag_engine.clear_database():
                st.session_state.indexed_files = []
                st.session_state.active_document = None
                st.success("تم مسح الفهرس.")
        if st.button("عرض تقرير الأداء", icon=":material/monitoring:", use_container_width=True):
            if st.session_state.rag_engine and hasattr(st.session_state.rag_engine, "monitor"):
                st.markdown(st.session_state.rag_engine.monitor.get_performance_report())

    if st.button("حفظ وإغلاق", type="primary", icon=":material/check:", use_container_width=True):
        st.session_state.processing_mode = processing_mode
        st.session_state.chunk_size = chunk_size
        st.session_state.chunk_overlap = chunk_overlap
        st.session_state.batch_size = batch_size
        st.session_state.force_ocr = force_ocr
        st.session_state.enable_cache = enable_cache
        st.rerun()


@st.dialog("الأرشيف", icon=":material/archive:")
def show_archive_dialog():
    if not st.session_state.rag_engine:
        st.info("هيّئ مساحة العمل لعرض المستندات المحفوظة.")
        return
    files = st.session_state.rag_engine.get_indexed_files()
    if not files:
        st.info("لا توجد مستندات مفهرسة بعد.")
        return
    search_term = st.text_input("ابحث باسم المستند", placeholder="اسم المستند...")
    filtered_files = [f for f in files if search_term.lower() in f.lower()]
    st.caption(f"{len(filtered_files)} مستند")
    for filename in filtered_files[:20]:
        st.write(filename)


@st.dialog("المساعدة والدعم", icon=":material/help:")
def show_support_dialog():
    st.markdown("ارفع ملفات PDF، ابدأ الفهرسة، اختر نطاق العمل، ثم استخدم المحادثة أو إحدى الأدوات.")
    if st.button("إعادة الجولة التعريفية", icon=":material/replay:", use_container_width=True):
        restart_tour()
        st.rerun()
    with st.form("support_form_optimized"):
        rating = st.select_slider("تقييم التجربة", options=[1, 2, 3, 4, 5], value=5)
        name = st.text_input("الاسم (اختياري)")
        email = st.text_input("البريد الإلكتروني (اختياري)")
        query_type = st.selectbox("نوع الرسالة", ["تقييم عام", "مشكلة تقنية", "اقتراح تحسين", "استفسار آخر"])
        msg = st.text_area("رسالتك", height=100)
        if st.form_submit_button("إرسال", use_container_width=True):
            save_support_ticket_optimized(name, email, query_type, msg, rating)
            st.success("شكراً لك. تم حفظ رسالتك.")


# --- Sidebar ---
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand" dir="rtl">
            <span class="material-symbols-rounded" aria-hidden="true">school</span>
            <div><strong>باحث</strong><small>مساحة أكاديمية ذكية</small></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.session_state.rag_engine:
        st.caption("● مساحة العمل جاهزة")
    else:
        st.caption("○ ستُجهّز مساحة العمل عند الفهرسة")

    with st.container(key="indexing_job_status"):
        render_indexing_job_status()
    
    # --- رفع الملفات ---
    st.markdown("### المستندات")
    
    available_documents = list(dict.fromkeys(
        list(st.session_state.indexed_files) + list(st.session_state.last_full_text.keys())
    ))
    if available_documents:
        document_options = ["كل المستندات"] + available_documents
        current_option = st.session_state.active_document or "كل المستندات"
        if current_option not in document_options:
            current_option = "كل المستندات"
        selected_document = st.selectbox(
            "المستند النشط للبحث والتحليل",
            document_options,
            index=document_options.index(current_option),
            help="اختر ملفاً لعزل إجابات البحث عليه، أو اختر كل المستندات للبحث العام.",
            key="active_document_selector",
        )
        st.session_state.active_document = (
            None if selected_document == "كل المستندات" else selected_document
        )
        if st.session_state.active_document:
            st.caption(f"جاهز للتحليل: {st.session_state.active_document}")
    else:
        st.caption("ابدأ برفع ملف PDF أو أكثر.")

    st.markdown(
        """
        <div class="sidebar-upload-context" dir="rtl">
            <strong>رفع المستندات</strong>
            <span>اسحب ملفات PDF هنا أو اخترها من جهازك</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    uploaded_files = st.file_uploader(
        "ارفع المستندات",
        type=["pdf"],
        accept_multiple_files=True,
        help="يمكنك رفع عدة ملفات PDF مرة واحدة",
        key="tour_target_upload",
    )
    
    if uploaded_files:
        # معلومات الملفات
        total_size = sum(f.size for f in uploaded_files)
        st.caption(f"{len(uploaded_files)} ملف | الحجم الإجمالي: {format_file_size(total_size)}")
        
        configured_mode = st.session_state.processing_mode
        if configured_mode == "متسلسل":
            process_method = "متسلسل (مناسب لملفات كبيرة)"
        elif configured_mode == "متوازي":
            process_method = "متوازي (مناسب لملفات متعددة)"
        else:
            process_method = (
                "متسلسل (مناسب لملفات كبيرة)"
                if len(uploaded_files) == 1
                else "متوازي (مناسب لملفات متعددة)"
            )
        force_ocr = st.session_state.force_ocr
    
    indexing_is_running = indexing_jobs.has_running_job()
    if uploaded_files and st.button(
        "الفهرسة جارية في الخلفية" if indexing_is_running else "بدء الفهرسة",
        type="primary",
        icon=":material/hourglass_top:" if indexing_is_running else ":material/auto_awesome_motion:",
        use_container_width=True,
        key="tour_target_index_background",
        disabled=indexing_is_running,
    ):
        start_background_indexing(uploaded_files)

    # Emergency compatibility fallback, deliberately disabled in the normal
    # deployment. The durable background path above is the supported flow.
    if os.getenv("ENABLE_LEGACY_SYNCHRONOUS_INDEXING") == "1":
        st.session_state.tour_index_error = False
        if not st.session_state.rag_engine:
            with st.spinner("جاري تجهيز مساحة العمل..."):
                initialize_workspace()
        if st.session_state.rag_engine:
            valid_files = []
            rejected_files = []
            for uploaded_file in uploaded_files:
                is_valid, validation_message = validate_pdf_file(uploaded_file)
                if is_valid:
                    valid_files.append(uploaded_file)
                else:
                    rejected_files.append(uploaded_file.name)
                    st.warning(f"تعذر قبول الملف «{uploaded_file.name}»: {validation_message}")

            if not valid_files:
                st.error("لم يوجد ملف PDF صالح للفهرسة. تحقق من الملفات ثم حاول مرة أخرى.")
                st.session_state.tour_index_error = True
                render_guided_tour()
                st.stop()

            uploaded_files = valid_files
            # إنشاء معالج المستندات
            processor = OptimizedDocumentProcessor(
                chunk_size=st.session_state.get('chunk_size', 2000),
                chunk_overlap=st.session_state.get('chunk_overlap', 300)
            )
            
            # عرض حاوية التقدم
            progress_container = st.container()
            with progress_container:
                st.markdown("### جاري معالجة الملفات...")
                
                # شريط تقدم رئيسي
                main_progress_bar = st.progress(0, text="إعداد النظام...")
                st.session_state.progress_bar = main_progress_bar
                
                # منطقة المعلومات
                info_placeholder = st.empty()
                time_placeholder = st.empty()
                
                # عناصر الديكور
                placeholder = st.empty()
                placeholder.markdown(typewriter_html, unsafe_allow_html=True)
            
            # بدء قياس الوقت
            start_time = time.time()
            
            try:
                # معالجة الملفات
                all_results = []
                
                if process_method == "متوازي (مناسب لملفات متعددة)":
                    # معالجة متوازية
                    def update_progress(completed, total, filename):
                        progress = completed / total
                        main_progress_bar.progress(
                            progress,
                            text=f"معالجة {filename} ({completed}/{total})"
                        )
                        info_placeholder.info(f"جاري معالجة: {filename}")
                        
                        # حساب الوقت المتبقي
                        elapsed = time.time() - start_time
                        if completed > 0:
                            remaining = (elapsed / completed) * (total - completed)
                            time_placeholder.caption(f"⏱️ الوقت المتبقي: ~{int(remaining)} ثانية")
                    
                    results = processor.process_batch_pdfs(uploaded_files, update_progress, force_ocr=force_ocr)
                    successful_results = [r for r in results if r.get('chunks')]
                    failed_results = [r for r in results if not r.get('chunks')]
                    all_results = [r['chunks'] for r in successful_results]
                    # تخزين النصوص الكاملة والصفحات من المعالجة المتوازية أيضاً
                    for r in successful_results:
                        if 'raw_text' in r and r.get('file'):
                            fname = r['file'] if isinstance(r['file'], str) else r['file'].name
                            st.session_state.last_full_text[fname] = r['raw_text']
                            if r.get('pages'):
                                st.session_state.last_file_pages[fname] = r['pages']
                    
                else:
                    # معالجة متسلسلة
                    for i, file in enumerate(uploaded_files):
                        # تحديث التقدم
                        progress = (i + 1) / len(uploaded_files)
                        main_progress_bar.progress(
                            progress,
                            text=f"معالجة {file.name} ({i+1}/{len(uploaded_files)})"
                        )
                        
                        info_placeholder.info(f"جاري معالجة: {file.name}")
                        
                        # معالجة الملف
                        chunks, full_txt, used_ocr, pages = processor.process_single_pdf(file, force_ocr=force_ocr)
                        
                        # Add only successfully extracted documents to the index batch.
                        if chunks:
                            all_results.append(chunks)
                            st.session_state.last_full_text[file.name] = full_txt
                            if pages:
                                st.session_state.last_file_pages[file.name] = pages
                        else:
                            rejected_files.append(file.name)
                            st.warning(f"تعذر معالجة الملف «{file.name}». تحقق من سلامة ملف PDF ثم حاول مرة أخرى.")
                        
                        # تحديث الوقت المتبقي
                        elapsed = time.time() - start_time
                        if i > 0:
                            remaining = (elapsed / (i + 1)) * (len(uploaded_files) - i - 1)
                            time_placeholder.caption(f"⏱️ الوقت المتبقي: ~{int(remaining)} ثانية")
                
                if not all_results:
                    raise RuntimeError("لم تنتج الملفات الصالحة أي نص قابل للفهرسة.")

                # فهرسة جميع النتائج معاً
                info_placeholder.info("جاري فهرسة النتائج...")
                indexing_succeeded = st.session_state.rag_engine.ingest_documents_bulk(
                    all_results, batch_size=st.session_state.batch_size
                )
                if not indexing_succeeded:
                    raise RuntimeError("Indexing did not complete")
                
                # حساب الوقت الإجمالي
                total_time = time.time() - start_time
                
                # إخفاء عناصر التقدم
                placeholder.empty()
                info_placeholder.empty()
                time_placeholder.empty()
                main_progress_bar.empty()
                
                # عرض النتائج
                indexed_count = len(all_results)
                indexed_names = [getattr(file, "name", str(file)) for file in uploaded_files]
                st.session_state.indexed_files = list(dict.fromkeys(st.session_state.indexed_files + indexed_names))
                st.session_state.tour_index_completed = True
                st.success(f"تمت فهرسة {indexed_count} ملف بنجاح.")
                if process_method == "متوازي (مناسب لملفات متعددة)":
                    for result in failed_results:
                        failed_name = result.get('file')
                        failed_name = failed_name if isinstance(failed_name, str) else getattr(failed_name, 'name', 'ملف')
                        rejected_files.append(failed_name)
                if rejected_files:
                    failed_names = "، ".join(dict.fromkeys(rejected_files))
                    st.warning(f"لم تتم فهرسة بعض الملفات: {failed_names}")
                
                # عرض إحصائيات الأداء
                if hasattr(st.session_state.rag_engine, 'monitor'):
                    indexing_time = st.session_state.rag_engine.monitor.metrics.get('indexing_time', [])
                    if indexing_time:
                        last_time = indexing_time[-1]['value']
                        st.metric("⏱️ وقت الفهرسة الإجمالي", f"{total_time:.1f} ثانية")
                        st.metric("⚡ متوسط الوقت لكل ملف", f"{total_time/indexed_count:.1f} ثانية")
                
                # مهلة قصيرة لتأكيد النجاح قبل متابعة الجولة.
                time.sleep(0.8)
                st.rerun()
                
            except Exception:
                st.session_state.tour_index_error = True
                st.error("تعذر إكمال الفهرسة. تحقق من اتصال خدمة الفهرسة ومن صحة ملفات PDF ثم حاول مرة أخرى.")
                placeholder.empty()
    
    st.markdown('<div class="sidebar-spacer"></div>', unsafe_allow_html=True)
    if st.button("الإعدادات", icon=":material/settings:", use_container_width=True):
        show_settings_dialog()
    if st.button("الأرشيف", icon=":material/archive:", use_container_width=True):
        show_archive_dialog()
    if st.button("المساعدة", icon=":material/help:", use_container_width=True):
        show_support_dialog()

# ==========================================
# 4. المحتوى الرئيسي
# ==========================================

sync_tour_with_actions(uploaded_files)
render_product_header()
render_workflow_steps(uploaded_files)
render_document_context()
render_guided_tour()

# تبويبات الواجهة
with st.container(key="tour_target_tools"):
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        ":material/chat: المحادثة",
        ":material/summarize: الملخص",
        ":material/label: الكيانات",
        ":material/translate: الترجمة",
        ":material/analytics: التحليل",
        ":material/hub: الخريطة الذهنية",
        ":material/menu_book: البحث الأكاديمي"
    ])

# --- TAB 1: البحث الذكي ---
with tab1:
    with st.container(key="chat_workspace"):
        render_chat_header()

        # Keep the transcript ahead of the composer in the document flow. Writing
        # new messages back into this container lets the answer appear above the
        # input instead of pushing the conversation below it after a rerun.
        chat_feed = st.container(key="chat_transcript")
        with chat_feed:
            if st.session_state.messages:
                for msg in st.session_state.messages[-5:]:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
                        if msg.get("role") == "assistant":
                            render_chat_sources(msg.get("sources", []))
            elif not st.session_state.rag_engine:
                render_empty_state("upload_file", "ابدأ بمستند", "ارفع مستنداً أو اختر مستنداً جاهزاً للبدء.")
            else:
                render_empty_state("chat", "ابدأ المحادثة", "ابدأ بسؤال عن المستند المحدد، مثل فكرته الرئيسية أو نتائجه.")
    
    with st.expander("استخدام الإدخال الصوتي", icon=":material/mic:"):
        # استخدام st.audio_input المدمج في Streamlit بدلاً من المكون الخارجي
        audio = st.audio_input("اضغط للتسجيل")
        
        # معالجة الصوت إذا تم التسجيل
        if audio is not None:
            with st.spinner("جاري تحويل الصوت إلى نص..."):
                try:
                    import speech_recognition as sr
                    import subprocess
                    import tempfile
                    import os
                    
                    # إنشاء recognizer
                    r = sr.Recognizer()
                    r.energy_threshold = 200  # حساسية أعلى
                    r.dynamic_energy_threshold = True
                    r.pause_threshold = 0.8
                    
                    # قراءة bytes الصوت (يأتي من Streamlit كـ WAV أو WebM)
                    audio_bytes = audio.read()
                    
                    # محاولة قراءة الصوت مباشرة أولاً
                    wav_buffer = io.BytesIO(audio_bytes)
                    wav_buffer.seek(0)
                    
                    audio_data = None
                    try:
                        # محاولة قراءة WAV مباشرة
                        with sr.AudioFile(wav_buffer) as source:
                            audio_data = r.record(source)
                    except Exception:
                        # إذا فشل WAV، حاول تحويل الصوت باستخدام ffmpeg
                        try:
                            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp_in:
                                tmp_in.write(audio_bytes)
                                tmp_in_path = tmp_in.name
                            tmp_out_path = tmp_in_path.replace('.webm', '.wav')
                            
                            # تحويل باستخدام ffmpeg
                            result = subprocess.run(
                                ['ffmpeg', '-y', '-i', tmp_in_path, '-ar', '16000', '-ac', '1', tmp_out_path],
                                capture_output=True, timeout=15
                            )
                            
                            if result.returncode == 0 and os.path.exists(tmp_out_path):
                                with sr.AudioFile(tmp_out_path) as source:
                                    audio_data = r.record(source)
                            
                            # تنظيف الملفات المؤقتة
                            for p in [tmp_in_path, tmp_out_path]:
                                try: os.unlink(p)
                                except: pass
                        except Exception as conv_err:
                            st.warning(f"تعذّر تحويل الصوت: {conv_err}")
                    
                    if audio_data is None:
                        st.error("تعذّر قراءة ملف الصوت. حاول مرة أخرى.")
                    else:
                        # التعرف على الكلام - محاولة العربية أولاً ثم الإنجليزية
                        recognized = None
                        try:
                            recognized = r.recognize_google(audio_data, language="ar-EG")
                            st.session_state.voice_text = recognized
                            st.success(f"تم التعرف: {recognized}")
                        except sr.UnknownValueError:
                            try:
                                recognized = r.recognize_google(audio_data, language="en-US")
                                st.session_state.voice_text = recognized
                                st.success(f"تم التعرف: {recognized}")
                            except sr.UnknownValueError:
                                st.error("لم أتمكن من فهم الصوت. تأكد من وضوح التسجيل.")
                            except sr.RequestError as e:
                                st.error(f"خطأ في خدمة التعرف على الصوت: {e}")
                        except sr.RequestError as e:
                            st.error(f"خطأ في خدمة التعرف على الصوت: {e}")
                            
                except ImportError:
                    st.error("الإدخال الصوتي غير متاح الآن.")
                except Exception:
                    st.error("تعذر تحويل الصوت إلى نص. جرّب تسجيل الصوت مرة أخرى أو اكتب السؤال.")
    
    voice_prompt = None
    if st.session_state.voice_text:
        st.caption(f"النص الصوتي: {st.session_state.voice_text}")
        if st.button("إرسال النص الصوتي", icon=":material/arrow_upward:"):
            voice_prompt = st.session_state.voice_text

    typed_prompt = st.chat_input("اسأل أي سؤال عن المستند المحدد...", key="tour_target_chat")
    new_prompt = typed_prompt or voice_prompt
    pending_prompt = st.session_state.tour_pending_prompt

    # First persist the user's real message, then rerun. The next pass draws it
    # in the transcript above the sticky composer before the provider starts.
    if new_prompt and not pending_prompt:
        st.session_state.messages.append({"role": "user", "content": new_prompt})
        st.session_state.tour_pending_prompt = new_prompt
        if st.session_state.voice_text:
            st.session_state.voice_text = ""
        if st.session_state.tour_active and st.session_state.tour_step == 4:
            st.session_state.tour_last_completed_step = 4
            st.session_state.tour_step = 5
            st.session_state.tour_confirmation = "تم إرسال سؤالك."
        st.rerun()

    prompt = pending_prompt
    if pending_prompt:
        st.session_state.tour_pending_prompt = ""
    
    # معالجة الاستعلام
    if prompt:
        with chat_feed:
            with st.chat_message("assistant"):
                if st.session_state.rag_engine:
                    # عرض مؤشر التحميل
                    with st.spinner("جاري البحث في المستندات..."):
                        thinking_ph = st.empty()
                        thinking_ph.markdown(typewriter_html, unsafe_allow_html=True)

                        # تنفيذ الاستعلام مع caching وتاريخ المحادثة
                        chat_history = st.session_state.messages[:-1] if len(st.session_state.messages) > 1 else []
                        response, sources = st.session_state.rag_engine.query_with_cache(
                            prompt,
                            chat_history=chat_history,
                            active_document=st.session_state.active_document,
                        )

                        # إخفاء مؤشر التحميل
                        thinking_ph.empty()
                        
                        # عرض الإجابة داخل واجهة محسنة
                        st.markdown(response)
                        
                        # زر تحميل النتيجة
                        filename = create_fancy_download_button_optimized(
                            response,
                            "search_result",
                            "تحميل الإجابة"
                        )

                        render_chat_sources(
                            sources,
                            include_scholar_links=True,
                            instance_key=f"live_{len(st.session_state.messages)}",
                        )

                        # إضافة الإجابة إلى سجل المحادثة
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response,
                            "sources": sources,
                        })

                else:
                    st.error("مساحة العمل غير جاهزة. ارفع مستنداً للفهرسة أو افتح الإعدادات لتهيئتها.")
    
    # قسم التحليل المتقدم (مدمج في البحث الذكي)
    st.markdown('<div class="advanced-analysis-divider" aria-hidden="true"></div>', unsafe_allow_html=True)
    advanced_panel = st.expander("تحليل متقدم", expanded=False, icon=":material/science:")
    advanced_panel.__enter__()
    st.caption("أداة ثانوية للتحليل المتخصص عند الحاجة.")
    
    # دمج الملفات المفهرسة مع الملفات المرفوعة
    all_available_files = list(st.session_state.last_full_text.keys()) + [
        f for f in st.session_state.indexed_files 
        if f not in st.session_state.last_full_text
    ]
    
    if all_available_files:
        selected_analysis_file = st.selectbox(
            "اختر الملف للتحليل:",
            all_available_files,
            key="advanced_analysis_file_tab1"
        )
        
        col_atype, col_lang = st.columns([2, 1])
        with col_atype:
            analysis_type = st.selectbox(
                "نوع التحليل:",
                [
                    "تحليل الورقة العلمية",
                    "تحليل الشعر والبلاغة",
                    "التحليل اللغوي العميق",
                    "تحليل مقارن",
                    "اكتشاف الفجوات البحثية",
                    "استخراج الأرقام والإحصائيات"
                ],
                key="analysis_type_tab1"
            )
        with col_lang:
            output_lang = st.selectbox(
                "لغة الإخراج:",
                ["تلقائي (حسب المستند)", "عربي دائماً", "إنجليزي دائماً"],
                key="analysis_output_lang"
            )
        
        # حدود النص الذكية — مضبوطة حسب النموذج
        # context window لـ llama3/qwen2.5 = 8192 token ≈ 5000-6000 كلمة عربية
        FAST_LIMIT    = 4500   # حد التحليل المباشر (كلمة)
        SAMPLE_LIMIT  = 4500   # حد العينة الذكية (كلمة)
        
        if st.button("بدء التحليل المتقدم", type="primary", icon=":material/science:", use_container_width=True):
            if st.session_state.rag_engine and selected_analysis_file:
                with st.spinner("جاري التحليل المتقدم..."):
                    txt = get_file_content_safe(selected_analysis_file)
                    total_words = len(txt.split())
                    total_chars = len(txt)
                    
                    # ── كشف لغة المستند ──────────────────────────────────
                    arabic_chars = sum(1 for c in txt if '\u0600' <= c <= '\u06FF')
                    alpha_chars  = sum(1 for c in txt if c.isalpha())
                    arabic_ratio = arabic_chars / alpha_chars if alpha_chars > 0 else 0
                    doc_is_arabic = arabic_ratio >= 0.3   # أكثر من 30% حروف عربية
                    
                    if output_lang == "عربي دائماً":
                        lang_instruction = "IMPORTANT: You MUST write your ENTIRE response in Arabic only. Do not use English at all.\n\n"
                        lang_label = "🇸🇦 عربي"
                    elif output_lang == "إنجليزي دائماً":
                        lang_instruction = "IMPORTANT: You MUST write your ENTIRE response in English only. Do not use Arabic at all.\n\n"
                        lang_label = "🇬🇧 إنجليزي"
                    else:  # تلقائي
                        if doc_is_arabic:
                            lang_instruction = "IMPORTANT: You MUST write your ENTIRE response in Arabic only, since the document is in Arabic. Do not use English.\n\n"
                            lang_label = f"🔄 تلقائي → عربي ({arabic_ratio*100:.0f}% عربي)"
                        else:
                            lang_instruction = "IMPORTANT: You MUST write your ENTIRE response in English only, since the document is in English. Do not use Arabic.\n\n"
                            lang_label = f"🔄 تلقائي → إنجليزي ({(1-arabic_ratio)*100:.0f}% إنجليزي)"
                    
                    # عرض معلومات النص
                    st.info(f"📊 حجم النص: {total_words:,} كلمة | {total_chars:,} حرف | لغة الإخراج: {lang_label}")
                    
                    # ── التحليل بالكتل (Map-Reduce) ─────────────────────────
                    prompt_template = ""
                    merge_prompt = f"{lang_instruction}قم بدمج وتلخيص النتائج التالية في تقرير متماسك وشامل دون تكرار:\n\n{{results}}"
                    
                    if analysis_type == "تحليل الورقة العلمية":
                        prompt_template = f"""{lang_instruction}أنت محلل أبحاث علمية خبير. حلل الورقة العلمية التالية تحليلاً فعلياً مفصلاً.

مطلوب منك:
1. **العنوان والموضوع**: استخرج العنوان الفعلي من النص
2. **الأهداف والفرضيات**: اقتبس الأهداف مباشرة من النص (ضع الاقتباس بين علامتي تنصيص)
3. **المنهجية**: اذكر المنهج البحثي المستخدم فعلياً (مثلاً: تجريبي، وصفي، تحليلي) مع التفاصيل
4. **حجم العينة والمجتمع**: اذكر الأرقام الفعلية (مثلاً: "العينة 200 طالب من جامعة كذا")
5. **النتائج الرقمية**: استخرج كل الأرقام والنسب المئوية الموجودة فعلياً في النص (مثلاً: "نسبة الموافقة 78.5%")
6. **أدوات البحث**: اذكر الأدوات الفعلية (استبيان، مقابلات، اختبارات...)
7. **نقاط القوة**: 3 نقاط محددة بناءً على ما قرأته فعلياً
8. **نقاط الضعف**: 3 نقاط محددة بناءً على ما قرأته فعلياً
9. **الإسهام العلمي**: ما الجديد الذي أضافه هذا البحث؟

⚠️ مهم جداً: لا تكتب وصفاً عاماً! اقتبس من النص مباشرة. إذا لم تجد معلومة محددة، اكتب "غير مذكور في النص".

النص:
{{text}}"""

                    elif analysis_type == "تحليل الشعر والبلاغة":
                        prompt_template = f"""{lang_instruction}أنت خبير في البلاغة العربية والنقد الأدبي. حلل النص التالي تحليلاً بلاغياً فعلياً ومفصلاً.

مطلوب منك استخراج وتحليل كل مما يلي مع ذكر الاقتباس المباشر من النص:

**أولاً: التشبيهات** (اذكر كل تشبيه مع نوعه):
- اقتبس الجملة → حدد المشبه والمشبه به ووجه الشبه وأداة التشبيه → نوع التشبيه (مرسل/مؤكد/بليغ/تمثيلي)

**ثانياً: الاستعارات**:
- اقتبس الجملة → حدد نوعها (تصريحية/مكنية) → اشرح المعنى الحقيقي والمجازي

**ثالثاً: الكناية**:
- اقتبس الجملة → ما المعنى الظاهر؟ → ما المعنى المقصود؟

**رابعاً: المحسنات البديعية**:
- طباق: اقتبس أمثلة مع تحديد الكلمتين المتضادتين
- جناس: اقتبس أمثلة مع تحديد نوعه (تام/ناقص)
- سجع: اقتبس أمثلة
- تورية: اقتبس أمثلة

**خامساً: الأساليب** (خبري/إنشائي):
- اقتبس 3-5 جمل → حدد نوع كل أسلوب → غرضه البلاغي

**سادساً: الصور الشعرية والتصوير الفني**:
- الصور البصرية والسمعية والحركية مع اقتباسات

⚠️ مهم جداً: لا تكتب "النص يحتوي على استعارات" بشكل عام! يجب أن تقتبس كل مثال فعلي من النص. إذا لم تجد نوعاً معيناً، اكتب "لم يُعثر على أمثلة في النص".

النص:
{{text}}"""

                    elif analysis_type == "التحليل اللغوي العميق":
                        prompt_template = f"""{lang_instruction}أنت عالم لغويات متخصص. حلل النص التالي تحليلاً لغوياً فعلياً ومفصلاً.

مطلوب منك:

**1. التحليل الصرفي** (اختر 15-20 كلمة مهمة من النص):
| الكلمة | الجذر | الوزن الصرفي | نوعها | الاشتقاقات |
|--------|-------|-------------|-------|-------------|
(املأ الجدول بكلمات فعلية من النص)

**2. التحليل النحوي** (حلل 5 جمل رئيسية من النص):
- اقتبس الجملة → حدد نوعها (اسمية/فعلية) → أعرب الأركان الأساسية

**3. التحليل الدلالي**:
- الحقول الدلالية المهيمنة: اذكر 3-5 حقول مع أمثلة فعلية من النص
- الكلمات متعددة المعاني: اقتبس كلمات لها أكثر من معنى في السياق
- المترادفات في النص: اذكر أزواج المترادفات الفعلية

**4. المصطلحات المتخصصة**:
| المصطلح | المجال | التكرار في النص | المعنى |
|---------|--------|----------------|--------|
(استخرج المصطلحات الفعلية من النص)

**5. إحصائيات لغوية**:
- نسبة الأسماء / الأفعال / الحروف (تقريبياً)
- متوسط طول الجملة
- مستوى التعقيد اللغوي (1-10)

⚠️ مهم جداً: كل مثال يجب أن يكون مقتبساً فعلياً من النص. لا تخترع أمثلة!

النص:
{{text}}"""

                    elif analysis_type == "تحليل مقارن":
                        prompt_template = f"""{lang_instruction}أنت خبير في التحليل المقارن للأبحاث. حلل النص التالي تحليلاً مقارناً فعلياً.

مطلوب منك:

**1. النقاط الرئيسية في النص** (استخرج 5-8 نقاط مع اقتباسات):
- النقطة + الاقتباس الداعم من النص

**2. المقارنات الموجودة في النص نفسه**:
- هل يقارن الباحث بين مفاهيم/نتائج/نظريات؟ اقتبس المقارنات فعلياً
- اعرضها في جدول: | العنصر الأول | العنصر الثاني | وجه المقارنة | النتيجة |

**3. نقاط القوة** (بناءً على محتوى النص الفعلي):
- 3-5 نقاط مع شرح مبني على اقتباسات

**4. نقاط الضعف والقيود**:
- هل ذكر الباحث قيوداً؟ اقتبسها
- قيود تلاحظها أنت مع التبرير

**5. موقع البحث من الأدبيات**:
- المراجع والدراسات المذكورة في النص (اقتبس أسماءها)
- كيف يتموضع هذا البحث بالنسبة لها؟

⚠️ كل نقطة يجب أن تكون مدعومة باقتباس أو إشارة محددة من النص.

النص:
{{text}}"""

                    elif analysis_type == "اكتشاف الفجوات البحثية":
                        prompt_template = f"""{lang_instruction}أنت خبير في تحديد الفجوات البحثية. حلل النص التالي لاكتشاف الفجوات.

مطلوب منك:

**1. ما غطاه البحث فعلياً** (اقتبس من النص):
- الموضوعات المعالجة مع اقتباسات

**2. ما لم يغطه البحث**:
- بناءً على ما ذُكر في المقدمة أو الأهداف ولم يظهر في النتائج
- موضوعات ذكرها الباحث كقيود أو توصيات مستقبلية (اقتبسها)

**3. الأسئلة المفتوحة**:
- أسئلة أثارها البحث ولم يجب عليها

**4. الفجوات المنهجية**:
- هل هناك ضعف في حجم العينة أو الأدوات؟ (اذكر الأرقام الفعلية)
- هل هناك متغيرات لم تُدرس؟

**5. اقتراحات بحثية مستقبلية**:
- ما ذكره الباحث نفسه (اقتبس) + اقتراحاتك

النص:
{{text}}"""

                    else:  # استخراج الأرقام والإحصائيات
                        prompt_template = f"""{lang_instruction}أنت محلل بيانات خبير. استخرج جميع الأرقام والإحصائيات الموجودة فعلياً في النص التالي.

مطلوب منك استخراج كل رقم وإحصائية في جداول منظمة:

**1. النسب المئوية والأرقام**:
| الرقم/النسبة | السياق (اقتبس الجملة) | الصفحة/الموقع |
|-------------|----------------------|---------------|
(استخرج كل نسبة ورقم مذكور فعلياً)

**2. حجم العينة والمجتمع**:
| البيان | القيمة | التفاصيل |
|--------|--------|----------|
(مثلاً: حجم العينة، المجتمع، عدد المشاركين...)

**3. التواريخ والفترات الزمنية**:
| التاريخ/الفترة | السياق |
|---------------|--------|
(كل تاريخ مذكور في النص)

**4. المقاييس والمعايير الإحصائية**:
| المقياس | القيمة | الدلالة |
|---------|--------|---------|
(مثلاً: المتوسط الحسابي، الانحراف المعياري، معامل الارتباط، مستوى الدلالة...)

**5. النتائج الكمية**:
| النتيجة | القيمة | التفسير |
|---------|--------|---------|
(كل نتيجة رقمية مع تفسيرها)

**6. ملخص إحصائي**:
- إجمالي الأرقام المستخرجة
- أهم 5 أرقام في البحث مع أهميتها

⚠️ مهم جداً: استخرج الأرقام الموجودة فعلياً في النص فقط. لا تخترع أرقاماً! إذا لم توجد إحصائيات في قسم معين، اكتب "لا توجد بيانات رقمية".

النص:
{{text}}"""
                        
                    try:
                        # ── تنفيذ التحليل — استدعاء ذكي وموزع ───────────
                        progress_ph = st.empty()
                        progress_ph.info(f"جاري التحليل الشامل لجميع الأجزاء... ({total_words:,} كلمة)")
                        
                        result = analyze_text_in_chunks(
                            text=txt,
                            prompt_template=prompt_template,
                            rag_engine=st.session_state.rag_engine,
                            max_words_per_chunk=FAST_LIMIT,
                            merge_prompt=merge_prompt
                        )
                        
                        progress_ph.empty()
                        render_result_card("science", "نتيجة التحليل", result, selected_analysis_file)
                        
                        create_fancy_download_button_optimized(
                            result,
                            f"advanced_analysis_{selected_analysis_file[:20]}",
                            "تحميل نتيجة التحليل"
                        )
                        
                    except Exception:
                        st.error("تعذر إكمال التحليل الآن. حاول مرة أخرى أو اختر نوع تحليل أبسط.")
            else:
                st.warning("يرجى تهيئة مساحة العمل واختيار ملف.")
    else:
        render_empty_state("science", "التحليل المتقدم", "ارفع مستنداً أو اختر مستنداً جاهزاً لتفعيل التحليل المتقدم.")
    advanced_panel.__exit__(None, None, None)

# --- TAB 2: الملخص التلقائي ---
with tab2:
    st.header("تلخيص المستند")
    st.caption("حوّل المستند إلى ملخص واضح بالطول والأسلوب المناسبين.")
    
    if st.session_state.last_full_text:
        # اختيار الملف
        selected_file = st.selectbox(
            "اختر الملف:",
            list(st.session_state.last_full_text.keys()),
            help="الملفات التي تمت معالجتها مؤخراً"
        )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            summary_type = st.selectbox(
                "نوع الملخص:",
                ["ملخص تنفيذي", "ملخص تحليلي", "ملخص سريع"]
            )
        
        with col2:
            summary_length = st.select_slider(
                "طول الملخص:",
                options=["قصير", "متوسط", "مفصل"],
                value="متوسط"
            )
        
        with col3:
            include_bullets = st.toggle("تضمين نقاط", value=True)
        
        if st.button("توليد الملخص", type="primary", icon=":material/summarize:", use_container_width=True):
            if st.session_state.rag_engine and selected_file:
                with st.spinner("جاري تحليل النص وتوليد الملخص..."):
                    # عرض مؤشر التحميل
                    pencil_ph = st.empty()
                    pencil_ph.markdown(pencil_html, unsafe_allow_html=True)
                    
                    # الحصول على النص
                    txt = get_file_content_safe(selected_file)
                    
                    # توليد الملخص
                    summary = st.session_state.rag_engine.generate_research_summary_optimized(txt)
                    
                    # إخفاء مؤشر التحميل
                    pencil_ph.empty()
                    
                    # تحسين تنسيق الملخص
                    if include_bullets and "•" not in summary and "-" not in summary:
                        summary = summary.replace("\n", "\n• ")
                        summary = "• " + summary
                    
                    # عرض الملخص
                    render_result_card("summarize", "الملخص", summary, selected_file)
        txt = get_file_content_safe(selected_file)
        summary = summary if 'summary' in locals() else ""

        # ===============================
        # إحصائيات الملخص
        # ===============================
        if summary:
            col_stats1, col_stats2, col_stats3 = st.columns(3)

            with col_stats1:
                st.metric("كلمات النص الأصلي", len(txt.split()))

            with col_stats2:
                st.metric("كلمات الملخص", len(summary.split()))

            with col_stats3:
                compression_rate = (1 - (len(summary) / len(txt))) * 100 if len(txt) else 0
                st.metric("نسبة الضغط", f"{compression_rate:.1f}%")

        # ===============================
        # تحميل الملخص
        # ===============================
        create_fancy_download_button_optimized(
            summary,
            f"summary_{selected_file}",
            "تحميل الملخص"
        )
    else:
        render_empty_state("summarize", "لا يوجد مستند للتلخيص", "اختر المستند الذي تريد تلخيصه.")

# --- TAB 3: استخراج الكيانات ---
with tab3:
    st.header("استخراج الكيانات")
    st.caption("استخرج الأسماء والمواقع والمصطلحات وأقسام البحث.")
    
    if st.session_state.last_full_text:
        selected_file = st.selectbox(
            "اختر الملف لتحليله:",
            list(st.session_state.last_full_text.keys()),
            key="ner_file_select"
        )
        
        # اختيار طريقة الاستخراج
        extraction_method = st.radio(
            "طريقة الاستخراج:",
            ["سريع (spaCy)", "متقدم (LLM)", "أقسام البحث العلمي"],
            horizontal=True,
            help="spaCy أسرع 10x، LLM أدق، أقسام البحث تستخرج الأهداف والنتائج"
        )
        
        if extraction_method == "أقسام البحث العلمي":
            # استخراج أقسام البحث العلمي
            if st.button("استخراج أقسام البحث", type="primary", icon=":material/article:"):
                if selected_file:
                    with st.spinner("📖 جاري استخراج أقسام البحث العلمي..."):
                        txt = get_file_content_safe(selected_file)
                        
                        # استخدام مستخرج أقسام البحث
                        report = get_research_report(txt)
                        sections = extract_research_sections(txt)
                        
                        # عرض التقرير
                        render_result_card("article", "أقسام البحث", report, selected_file)
                        
                        # إحصائيات
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("عدد الأقسام المستخرجة", len(sections))
                        with col2:
                            avg_conf = sum(s.confidence for s in sections.values()) / len(sections) if sections else 0
                            st.metric("متوسط الثقة", f"{avg_conf*100:.0f}%")
                        
                        # زر التحميل
                        create_fancy_download_button_optimized(
                            report,
                            f"research_sections_{selected_file}",
                            "تحميل التقرير"
                        )
        
        elif extraction_method == "سريع (spaCy)":
            # استخدام spaCy للاستخراج السريع
            if st.button("استخراج الكيانات (سريع)", type="primary", icon=":material/label:"):
                if selected_file:
                    with st.spinner("⚡ جاري استخراج الكيانات بـ spaCy..."):
                        txt = get_file_content_safe(selected_file)
                        
                        if SPACY_AVAILABLE:
                            try:
                                # تحميل نموذج spaCy
                                nlp = spacy.load("xx_ent_wiki_sm")
                                doc = nlp(txt[:10000])  # أول 10000 حرف
                                
                                # تجميع الكيانات مع مواقعها
                                entities_by_type = {}
                                entity_positions = []
                                for ent in doc.ents:
                                    ent_type = ent.label_
                                    if ent_type not in entities_by_type:
                                        entities_by_type[ent_type] = []
                                    if ent.text not in entities_by_type[ent_type]:
                                        entities_by_type[ent_type].append(ent.text)
                                    entity_positions.append((ent.start_char, ent.end_char, ent.label_, ent.text))
                                
                                # ألوان مختلفة لكل نوع كيان
                                entity_colors = {
                                    "PER": "#FF6B6B",  # أحمر - أشخاص
                                    "ORG": "#4ECDC4",  # أخضر فاتح - مؤسسات
                                    "LOC": "#45B7D1",  # أزرق - أماكن
                                    "GPE": "#96CEB4",  # أخضر - دول
                                    "DATE": "#FFEAA7",  # أصفر - تواريخ
                                    "MISC": "#DDA0DD",  # بنفسجي - متنوع
                                }
                                
                                # عرض النتائج مع Highlight
                                st.markdown("### 🧬 الكيانات المستخرجة")
                                
                                if entities_by_type:
                                    # عرض الكيانات بألوان مميزة
                                    for ent_type, entities in entities_by_type.items():
                                        color = entity_colors.get(ent_type, "#E0E0E0")
                                        with st.expander(f"**{ent_type}** ({len(entities)} كيان)", expanded=True):
                                            st.write(" • ".join(entities[:25]))
                                    
                                    # Display original PDF text natively; do not inject it into HTML.
                                    st.markdown("### 📝 النص مع الكيانات المحددة")
                                    st.text_area("مقتطف من النص", txt[:3000], height=300, disabled=True)
                                    
                                    # إحصائيات
                                    total_entities = sum(len(e) for e in entities_by_type.values())
                                    st.metric("إجمالي الكيانات", total_entities)
                                else:
                                    st.warning("لم يتم العثور على كيانات في النص")
                                    
                            except Exception as e:
                                st.error(f"خطأ في spaCy: {e}")
                                st.info("جاري استخدام الطريقة البديلة...")
                        else:
                            st.warning("⚠️ spaCy غير متوفر، استخدم الطريقة المتقدمة")
        
        else:
            # الطريقة الأصلية باستخدام LLM
            entity_types = st.multiselect(
                "اختر أنواع الكيانات:",
                ["الأشخاص", "المؤسسات", "المواقع", "التواريخ", "المصطلحات التقنية", "الأبحاث"],
                default=["الأشخاص", "المؤسسات", "المصطلحات التقنية"]
            )
            
            if st.button("استخراج الكيانات (متقدم)", type="primary", icon=":material/label:"):
                if selected_file and st.session_state.rag_engine:
                    with st.spinner("🧪 جاري تحليل النص واستخراج الكيانات..."):
                        txt = get_file_content_safe(selected_file)
                        
                        entity_prompt = f"""
                        قم باستخراج الكيانات المسماة من النص البحثي التالي.
                        أنواع الكيانات المطلوبة: {', '.join(entity_types)}
                        
                        قدم النتائج في جدول منظم مع التصنيف.
                        
                        النص:
                        {txt[:5000]}
                        """
                        
                        try:
                            entities_result = st.session_state.rag_engine.llm.invoke(entity_prompt, feature="ner")
                            render_result_card("label", "الكيانات المستخرجة", entities_result, selected_file)
                            
                            lines = entities_result.count('\n')
                            st.metric("عدد الكيانات المستخرجة", lines - 2 if lines > 2 else 0)
                            
                        except Exception:
                            st.error("تعذر استخراج الكيانات بالذكاء الاصطناعي الآن. حاول مرة أخرى.")
    else:
        render_empty_state("label", "لا يوجد مستند جاهز", "ارفع مستنداً أو اختر مستنداً جاهزاً لاستخراج الكيانات.")

# --- TAB 4: الترجمة العلمية ---
with tab4:
    st.header("الترجمة العلمية")
    st.caption("ترجم النصوص والمستندات مع الحفاظ على المعنى والمصطلحات.")
    
    # اختيار مصدر النص للترجمة
    translation_source = st.radio(
        "اختر مصدر النص:",
        ["إدخال يدوي", "من ملف محمّل"],
        horizontal=True
    )
    
    src_text = ""
    
    if translation_source == "إدخال يدوي":
        src_text = st.text_area(
            "النص المصدر:",
            height=200,
            placeholder="الصق النص العلمي هنا للترجمة...",
            help="يدعم النصوص بالعربية والإنجليزية"
        )
    
    else:  # من ملف محمّل
        if st.session_state.last_full_text:
            selected_trans_file = st.selectbox(
                "📂 اختر الملف:",
                list(st.session_state.last_full_text.keys()),
                key="translation_file_select"
            )
            
            if selected_trans_file:
                full_text = get_file_content_safe(selected_trans_file)
                
                # التحقق من وجود صفحات حقيقية
                real_pages = st.session_state.last_file_pages.get(selected_trans_file, [])
                has_real_pages = len(real_pages) > 0
                
                if has_real_pages:
                    total_pages = len(real_pages)
                    total_chars = len(full_text)
                    st.success(f"📊 المستند يحتوي على **{total_pages}** صفحة حقيقية ({total_chars:,} حرف)")
                else:
                    # Fallback للملفات القديمة
                    page_size = 3000
                    total_chars = len(full_text)
                    total_pages = max(1, (total_chars // page_size) + (1 if total_chars % page_size > 0 else 0))
                    st.info(f"📊 المستند يحتوي على حوالي **{total_pages}** صفحة تقريبية ({total_chars:,} حرف)")
                    st.caption("💡 أعد رفع الملف للحصول على صفحات حقيقية من الـ PDF")
                
                # اختيار نطاق الترجمة
                translation_scope = st.radio(
                    "ماذا تريد أن تترجم؟",
                    ["صفحة واحدة", "نطاق صفحات", "المستند كاملاً"],
                    horizontal=True
                )
                
                if translation_scope == "صفحة واحدة":
                    page_num = st.number_input(
                        "رقم الصفحة:",
                        min_value=1,
                        max_value=total_pages,
                        value=1
                    )
                    if has_real_pages:
                        src_text = real_pages[page_num - 1]
                    else:
                        start_idx = (page_num - 1) * page_size
                        end_idx = min(page_num * page_size, total_chars)
                        src_text = full_text[start_idx:end_idx]
                    
                    # عرض محتوى الصفحة
                    preview = src_text[:500] + ("..." if len(src_text) > 500 else "")
                    st.text_area(f"محتوى الصفحة {page_num}:", preview, height=120, disabled=True)
                    st.caption(f"📏 حجم الصفحة: {len(src_text):,} حرف | {len(src_text.split()):,} كلمة")
                    
                elif translation_scope == "نطاق صفحات":
                    col_from, col_to = st.columns(2)
                    with col_from:
                        from_page = st.number_input("من صفحة:", min_value=1, max_value=total_pages, value=1, key="trans_from_page")
                    with col_to:
                        default_to = min(from_page + 4, total_pages)
                        to_page = st.number_input("إلى صفحة:", min_value=from_page, max_value=total_pages, value=default_to, key="trans_to_page")
                    
                    if has_real_pages:
                        selected_pages = real_pages[from_page - 1:to_page]
                        src_text = "\n\n".join(selected_pages)
                    else:
                        start_idx = (from_page - 1) * page_size
                        end_idx = min(to_page * page_size, total_chars)
                        src_text = full_text[start_idx:end_idx]
                    
                    st.info(f"سيتم ترجمة {to_page - from_page + 1} صفحات ({len(src_text):,} حرف | {len(src_text.split()):,} كلمة)")
                    
                else:  # المستند كاملاً
                    src_text = full_text
                    st.warning(f"⚠️ سيتم ترجمة المستند كاملاً ({total_chars:,} حرف | {len(full_text.split()):,} كلمة). قد يستغرق وقتاً طويلاً!")
        else:
            render_empty_state("translate", "لا يوجد مستند للترجمة", "ارفع مستنداً أو الصق النص الذي تريد ترجمته.")
    
    st.divider()
    
    # خريطة اللغات (لضمان استخدام الاسم الصحيح في البرومبت)
    LANG_MAP = {
        "الإنجليزية": "English", "العربية": "Arabic", "الفرنسية": "French",
        "الألمانية": "German", "الإسبانية": "Spanish", "الإيطالية": "Italian",
        "البرتغالية": "Portuguese", "الصينية": "Chinese (Simplified)", "اليابانية": "Japanese",
        "الكورية": "Korean", "الهندية": "Hindi", "التركية": "Turkish",
        "الإندونيسية": "Indonesian", "الفيتنامية": "Vietnamese", "التايلاندية": "Thai",
        "الروسية": "Russian", "البولندية": "Polish", "الهولندية": "Dutch",
        "السويدية": "Swedish", "اليونانية": "Greek", "العبرية": "Hebrew",
        "الفارسية": "Persian (Farsi)", "الأوردية": "Urdu",
    }

    # إعدادات الترجمة المحسنة
    st.subheader("إعدادات الترجمة")
    
    col_lang1, col_lang2 = st.columns(2)
    
    with col_lang1:
        target_lang = st.selectbox(
            "الترجمة إلى:",
            [
                "--- اللغات الرئيسية ---",
                "الإنجليزية", "العربية", "الفرنسية", "الألمانية",
                "الإسبانية", "الإيطالية", "البرتغالية",
                "--- اللغات الآسيوية ---",
                "الصينية", "اليابانية", "الكورية", "الهندية", "التركية",
                "الإندونيسية", "الفيتنامية", "التايلاندية",
                "--- لغات أخرى ---",
                "الروسية", "البولندية", "الهولندية", "السويدية", "اليونانية",
                "العبرية", "الفارسية", "الأوردية"
            ],
            index=1
        )
    
    with col_lang2:
        translation_style = st.selectbox(
            "أسلوب الترجمة:",
            [
                "أكاديمي رسمي", "صحفي إعلامي", "أدبي سلس",
                "تجاري مهني", "تقني متخصص", "تعليمي مبسط"
            ]
        )
    
    # إعدادات متقدمة
    with st.expander("إعدادات متقدمة", icon=":material/tune:"):
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            preserve_terms = st.toggle("الحفاظ على المصطلحات التقنية", value=True)
            include_notes = st.toggle("إضافة هوامش تفسيرية", value=False)
        with col_opt2:
            formal_style = st.toggle("أسلوب رسمي", value=True)
            keep_formatting = st.toggle("الحفاظ على التنسيق", value=True)
    
    # زر الترجمة
    if st.button("بدء الترجمة", type="primary", icon=":material/translate:", use_container_width=True):
        if src_text and st.session_state.rag_engine:
            # استخدام خريطة اللغات للحصول على الاسم الإنجليزي الصحيح
            clean_lang = LANG_MAP.get(target_lang, None)
            if clean_lang is None or target_lang.startswith("---"):
                st.warning("⚠️ يرجى اختيار لغة صحيحة")
            else:
                # تقسيم النص بالكلمات بدل الحروف
                words = src_text.split()
                max_words_per_chunk = 800  # 800 كلمة لكل جزء (مناسب للنموذج)
                
                # إنشاء الأجزاء بالكلمات
                text_chunks = []
                for i in range(0, len(words), max_words_per_chunk):
                    chunk_words = words[i:i + max_words_per_chunk]
                    text_chunks.append(" ".join(chunk_words))
                
                all_translations = []
                progress_bar = st.progress(0)
                status_container = st.container()
                
                # استخراج اسم الأسلوب بشكل نظيف
                style_name = translation_style
                
                for i, chunk in enumerate(text_chunks):
                    with status_container:
                        st.caption(f"جاري ترجمة الجزء {i+1}/{len(text_chunks)} ({len(chunk.split())} كلمة)...")
                    
                    # بناء تعليمات الأسلوب
                    style_instructions = []
                    if preserve_terms:
                        style_instructions.append("Keep technical terms in their original language and add the translation in parentheses.")
                    if include_notes:
                        style_instructions.append("Add explanatory footnotes for difficult concepts.")
                    if formal_style:
                        style_instructions.append("Use formal academic language.")
                    
                    style_text = " ".join(style_instructions) if style_instructions else ""
                    
                    translation_prompt = f"""Translate the following text to {clean_lang}. Translation style: {style_name}.
{style_text}

IMPORTANT RULES:
1. Output ONLY the translated text. Do NOT add any comments, explanations, or notes before or after the translation.
2. Do NOT say "Here is the translation" or anything similar.
3. Translate the ENTIRE text completely. Do not skip or summarize any part.
4. Maintain the original paragraph structure and formatting.
5. Start directly with the translated text.

Text to translate:
{chunk}"""
                    
                    try:
                        chunk_translation = st.session_state.rag_engine.llm.invoke(
                            translation_prompt, feature="translation"
                        )
                        
                        # تنظيف الناتج من أي مقدمات غير مرغوبة
                        cleaned = chunk_translation.strip()
                        # إزالة عبارات شائعة يضيفها النموذج
                        unwanted_prefixes = [
                            "Here is the translation:", "Here's the translation:", 
                            "Translation:", "الترجمة:", "هذه هي الترجمة:",
                            "Here is the translated text:", "Translated text:"
                        ]
                        for prefix in unwanted_prefixes:
                            if cleaned.lower().startswith(prefix.lower()):
                                cleaned = cleaned[len(prefix):].strip()
                        if not cleaned:
                            raise ValueError("Empty translated content")
                        all_translations.append(cleaned)
                    except Exception:
                        progress_bar.empty()
                        st.error("تعذر إكمال الترجمة. لم تُنشأ نتيجة أو ملف تنزيل غير مكتمل.")
                        st.stop()
                    
                    progress_bar.progress((i + 1) / len(text_chunks))
                
                # دمج كل الترجمات
                translation = "\n\n".join(all_translations)
                
                # عرض النتيجة
                translation_context = selected_trans_file if translation_source != "إدخال يدوي" else "نص مباشر"
                render_result_card("translate", "الترجمة", translation, translation_context)
                
                # إحصائيات الترجمة
                col_t1, col_t2, col_t3 = st.columns(3)
                with col_t1:
                    st.metric("كلمات النص الأصلي", len(src_text.split()))
                with col_t2:
                    st.metric("كلمات النص المترجم", len(translation.split()))
                with col_t3:
                    st.metric("عدد الأجزاء", len(text_chunks))
                
                # زر تحميل الترجمة
                create_fancy_download_button_optimized(
                    translation,
                    f"translation_{target_lang}",
                    "تحميل الترجمة"
                )
        elif not src_text:
            st.warning("⚠️ يرجى إدخال نص أو اختيار ملف للترجمة")
        else:
            st.error("⚠️ يرجى تفعيل المحرك أولاً")

# --- TAB 5: تحليل النصوص ---
with tab5:
    st.header("تحليل النصوص")
    st.caption("استكشف البنية والإحصاءات والموضوعات الرئيسية.")
    
    if st.session_state.last_full_text:
        selected_files = st.multiselect(
            "اختر الملفات للتحليل:",
            list(st.session_state.last_full_text.keys()),
            help="يمكنك اختيار عدة ملفات للمقارنة"
        )
        
        if selected_files:
            # إنشاء علامات تبويب للملفات المختارة
            analysis_tabs = st.tabs(selected_files)
            
            for i, file in enumerate(selected_files):
                with analysis_tabs[i]:
                    txt = get_file_content_safe(file)
                    
                    # التحليل الإحصائي
                    col_a1, col_a2, col_a3, col_a4 = st.columns(4)
                    
                    with col_a1:
                        word_count = len(txt.split())

                        st.metric("عدد الكلمات", word_count)
                    
                    with col_a2:
                        char_count = len(txt)
                        st.metric("عدد الحروف", char_count)
                    
                    with col_a3:
                        sentence_count = txt.count('.') + txt.count('؟') + txt.count('!')
                        st.metric("عدد الجمل", sentence_count)
                    
                    with col_a4:
                        if word_count > 0:
                            avg_word_length = char_count / word_count
                            st.metric("متوسط طول الكلمة", f"{avg_word_length:.1f}")
                    
                    # توزيع الكلمات
                    with st.expander("📈 توزيع الكلمات", expanded=False):
                        words = txt.split()
                        if len(words) > 100:
                            # عرض الكلمات الأكثر تكراراً
                            from collections import Counter
                            word_freq = Counter(words)
                            common_words = word_freq.most_common(20)
                            
                            # عرض في جدول
                            import pandas as pd
                            df = pd.DataFrame(common_words, columns=["الكلمة", "التكرار"])
                            st.dataframe(df, use_container_width=True)
                        
                    # تحليل الموضوعات (محسن)
                    if st.button(f"تحليل موضوعات {file}", icon=":material/analytics:", key=f"topic_{i}"):
                        with st.spinner("جاري تحليل الموضوعات..."):
                            analysis_text, total_w = get_text_by_words(txt, max_words=2000, strategy="smart")
                            topic_prompt = f"""أنت محلل محتوى خبير. حلل النص التالي واستخرج الموضوعات الرئيسية.

مطلوب منك:

**1. الموضوعات الرئيسية** (رتبها حسب الأهمية):
| # | الموضوع | نسبة التغطية التقريبية | اقتباس داعم من النص |
|---|---------|----------------------|-------------------|
(استخرج 5-10 موضوعات فعلية)

**2. الكلمات المفتاحية**: أهم 10-15 كلمة مفتاحية مع عدد تكرارها التقريبي

**3. المجال العلمي**: حدد المجال الرئيسي والفرعي

**4. ملخص الموضوع في 3 جمل**

⚠️ اقتبس من النص الفعلي ولا تكتب وصفاً عاماً.

النص ({total_w} كلمة):
{analysis_text}"""
                            
                            try:
                                topics = st.session_state.rag_engine.llm.invoke(topic_prompt, feature="topics")
                                render_result_card("analytics", "تحليل الموضوعات", topics, file)
                            except Exception:
                                st.error("تعذر تحليل الموضوعات بالذكاء الاصطناعي الآن. حاول مرة أخرى.")
    else:
        render_empty_state("analytics", "لا يوجد مستند للتحليل", "ارفع مستنداً أو اختر مستنداً جاهزاً لبدء التحليل.")

# --- TAB 6: الخرائط الذهنية ---
with tab6:
    st.header("الخريطة الذهنية")
    st.caption("حوّل الأفكار والعلاقات إلى خريطة سهلة الاستكشاف.")
    st.markdown("""
    <div class="capability-note" dir="rtl">
        <span class="material-symbols-rounded" aria-hidden="true">hub</span>
        <div><strong>عرض تفاعلي</strong><small>تكبير، طي الفروع، وتصدير HTML تفاعلي.</small></div>
    </div>
    """, unsafe_allow_html=True)
    
    col_src, col_cfg = st.columns([3, 1])

    with col_cfg:
        with st.expander("إعدادات الخريطة", expanded=True, icon=":material/tune:"):
            viz_mode = st.radio(
                "طريقة العرض:",
                ["markmap (الأفضل)", "D3.js دائري", "Plotly شبكي"],
                index=0,
                help="markmap: خريطة تفاعلية كاملة\nD3: شجرة دائرية احترافية\nPlotly: تقليدي"
            )
            min_nodes = st.slider("الحد الأدنى للعقد", 5, 30, 15)
            map_height = st.slider("ارتفاع العرض (px)", 400, 900, 580)

    with col_src:
        input_mode = st.radio(
            "مصدر النص:",
            ["من ملف مرفوع", "إدخال نص مباشر"],
            horizontal=True
        )

        src_text_mm = ""
        selected_mm_file = None

        if input_mode == "من ملف مرفوع":
            if st.session_state.last_full_text:
                selected_mm_file = st.selectbox(
                    "اختر الملف:",
                    list(st.session_state.last_full_text.keys()),
                    key="mindmap_file_select_v2"
                )
            else:
                render_empty_state("hub", "لا يوجد مستند للخريطة", "ارفع مستنداً أو أدخل نصاً لبناء خريطة ذهنية.")
        else:
            src_text_mm = st.text_area(
                "أدخل النص:",
                height=120,
                placeholder="اكتب أو الصق النص هنا...",
                key="mindmap_direct_text_v2"
            )

    # تحديد render_mode
    if "markmap" in viz_mode:
        render_mode = "markmap"
    elif "D3" in viz_mode:
        render_mode = "d3"
    else:
        render_mode = "plotly"

    generate_btn = st.button(
        "توليد الخريطة الذهنية",
        type="primary",
        icon=":material/hub:",
        use_container_width=True,
        key="generate_mindmap_v2"
    )

    if generate_btn:
        if selected_mm_file:
            src_text_mm = get_file_content_safe(selected_mm_file)
        if not src_text_mm or len(src_text_mm.strip()) < 50:
            st.warning("النص قصير جداً أو فارغ.")
        elif not st.session_state.rag_engine:
            st.error("مساحة العمل غير جاهزة. هيّئها أولاً.")
        else:
            with st.spinner("🔄 جاري تحليل النص وبناء الخريطة الذهنية..."):
                key_name = selected_mm_file or "direct_input"
                mindmap_data = create_mindmap_from_text(src_text_mm, min_nodes)
                if mindmap_data:
                    st.session_state.mindmaps[key_name] = {"data": mindmap_data, "mode": render_mode, "height": map_height}
                    st.success("تم توليد الخريطة الذهنية بنجاح.")
                    st.rerun()

    # عرض الخريطة إذا وجدت
    key_name = selected_mm_file or "direct_input"
    if key_name in st.session_state.mindmaps:
        saved = st.session_state.mindmaps[key_name]
        mindmap_data = saved["data"]
        viz_tab1, viz_tab2, viz_tab3 = st.tabs(["الخريطة التفاعلية", "المخطط النصي", "التصدير"])

        with viz_tab1:
            # استخدام الـ Markdown الهرمي المحفوظ مباشرة مع markmap.js (أسرع وأوضح)
            raw_md = mindmap_data.get("_markdown", "")
            if raw_md and render_mode in ("markmap", "d3"):
                import streamlit.components.v1 as components
                st.caption("💡 **markmap.js** – اضغط الدوائر لطي/توسيع الفروع؛ عجلة الماوس للتكبير")
                import json as _json
                escaped_md = _json.dumps(raw_md)
                markmap_html = f"""<!DOCTYPE html>
<html dir="rtl">
<head>
<meta charset="UTF-8">
<style>
  body {{ margin: 0; background: #0f1117; }}
  #mm {{ width: 100%; height: {map_height}px; }}
</style>
</head>
<body>
<svg id="mm"></svg>
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script src="https://cdn.jsdelivr.net/npm/markmap-view@0.17"></script>
<script src="https://cdn.jsdelivr.net/npm/markmap-lib@0.17"></script>
<script>
const {{ Transformer, Markmap }} = window.markmap;
const t = new Transformer();
const md = {escaped_md};
const {{ root }} = t.transform(md);
const mm = Markmap.create('#mm', {{
    initialExpandLevel: 3,
    fitRatio: 0.95,
    colorFreezeLevel: 2
}});
mm.setData(root);
setTimeout(() => mm.fit(), 400);
</script>
</body>
</html>"""
                components.html(markmap_html, height=map_height + 20)
            elif render_mode == "plotly" or not raw_md:
                fig = visualize_mindmap_interactive(mindmap_data)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

        with viz_tab2:
            # عرض الخريطة النصية الهرمية
            raw_md = mindmap_data.get("_markdown", "")
            if raw_md:
                st.markdown("### 🗂️ الخريطة الهرمية النصية")
                st.code(raw_md, language="markdown")
            text_mindmap = create_text_mindmap(mindmap_data)
            render_result_card("hub", "الخريطة النصية", text_mindmap, key_name)

        with viz_tab3:
            st.markdown("### 📥 تصدير الخريطة")
            export_col1, export_col2, export_col3 = st.columns(3)
            with export_col1:
                json_data = json.dumps(mindmap_data, ensure_ascii=False, indent=2)
                st.download_button("📦 JSON", data=json_data, file_name=f"mindmap_{key_name}.json",
                                   mime="application/json", use_container_width=True)
            with export_col2:
                raw_md_export = mindmap_data.get("_markdown", "")
                if raw_md_export:
                    escaped_md_export = json.dumps(raw_md_export)
                    html_export = f"""<!DOCTYPE html>
<html dir="rtl">
<head><meta charset="UTF-8">
<style>body{{margin:0;background:#0f1117}} #mm{{width:100vw;height:100vh}}</style>
</head>
<body>
<svg id="mm"></svg>
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script src="https://cdn.jsdelivr.net/npm/markmap-view@0.17"></script>
<script src="https://cdn.jsdelivr.net/npm/markmap-lib@0.17"></script>
<script>
const{{Transformer,Markmap}}=window.markmap;
const t=new Transformer();
const md={escaped_md_export};
const{{root}}=t.transform(md);
const mm=Markmap.create('#mm',{{initialExpandLevel:3,fitRatio:0.95,colorFreezeLevel:2}});
mm.setData(root);setTimeout(()=>mm.fit(),300);
</script>
</body></html>"""
                    st.download_button("🌐 HTML تفاعلي", data=html_export,
                                       file_name=f"mindmap_{key_name}.html",
                                       mime="text/html", use_container_width=True)
                else:
                    st.button("🌐 HTML (غير متاح)", disabled=True, use_container_width=True)
            with export_col3:
                text_outline = create_text_mindmap(mindmap_data)
                st.download_button("📝 نص هرمي", data=text_outline,
                                   file_name=f"mindmap_{key_name}.txt",
                                   mime="text/plain", use_container_width=True)
    else:
        st.markdown("""
        <div style="text-align:center; padding:40px; color:#a0aec0;">
            <h2>🧠</h2>
            <h3>ابدأ بتوليد خريطتك الذهنية</h3>
            <p>اختر ملفاً أو أدخل نصاً، ثم اضغط <b>✨ توليد الخريطة الذهنية</b></p>
        </div>
        """, unsafe_allow_html=True)

# --- TAB 7: بحث الويب الأكاديمي ---
with tab7:
    st.header("البحث الأكاديمي")
    st.caption("ابحث خارج المستندات عند الحاجة، ثم راجع النتائج منفصلة عن مصادر المحادثة.")
    st.markdown("""
    > ابحث مباشرة في الإنترنت عبر محركات بحث أكاديمية (Google Scholar, arXiv, PubMed, Semantic Scholar)
    > ⚠️ هذه الميزة تتطلب اتصال بالإنترنت
    """)
    
    if WEB_SEARCH_AVAILABLE:
        web_col1, web_col2 = st.columns([3, 1])
        
        with web_col1:
            web_query = st.text_input(
                "موضوع البحث",
                placeholder="اكتب موضوع البحث الأكاديمي...",
                key="web_search_input"
            )
        
        with web_col2:
            web_category = st.selectbox(
                "التصنيف",
                ["أكاديمي", "عام", "أخبار", "ويكيبيديا"],
                key="web_search_category"
            )
        
        web_max_results = st.slider("عدد النتائج:", 5, 20, 10, key="web_max_results")
        
        if st.button("بحث", type="primary", icon=":material/search:", use_container_width=True, key="web_search_btn"):
            if web_query:
                with st.spinner("جاري البحث في المصادر الأكاديمية..."):
                    results = web_search_engine.search(
                        web_query,
                        category=web_category,
                        max_results=web_max_results
                    )
                    
                    if results["success"]:
                        st.success(f"تم العثور على {results['total']} نتيجة.")
                        
                        for i, result in enumerate(results["results"], 1):
                            with st.expander(f"{i}. {result['title']}", expanded=(i <= 3)):
                                if result.get("content"):
                                    st.write(result["content"])
                                
                                info_cols = st.columns(3)
                                with info_cols[0]:
                                    st.markdown(f"🔗 [فتح الرابط]({result['url']})")
                                with info_cols[1]:
                                    st.caption(f"المحرك: {result['engine']}")
                                with info_cols[2]:
                                    if result.get("publishedDate"):
                                        st.caption(f"📅 {result['publishedDate']}")
                                
                                if result.get("authors"):
                                    st.caption(f"👥 {', '.join(result['authors'][:3])}")
                                if result.get("doi"):
                                    st.caption(f"📄 DOI: {result['doi']}")
                        
                        # اقتراحات
                        if results.get("suggestions"):
                            st.markdown("---")
                            st.markdown("💡 **اقتراحات بحث:**")
                            for s in results["suggestions"][:5]:
                                st.write(f"- {s}")
                        
                        # دمج مع RAG
                        if st.session_state.rag_engine and results["results"]:
                            st.markdown("---")
                            if st.button("تحليل النتائج بالذكاء الاصطناعي", icon=":material/auto_awesome:", key="analyze_web_results"):
                                combined_text = "\n\n".join([f"{r['title']}: {r.get('content', '')}" for r in results["results"][:5]])
                                with st.spinner("جاري التحليل..."):
                                    try:
                                        summary = st.session_state.rag_engine.llm.invoke(
                                            f"لخص وحلل النتائج التالية من بحث الإنترنت حول '{web_query}' باللغة العربية:\n\n{combined_text[:4000]}",
                                            feature="web_summary",
                                        )
                                        render_result_card("auto_awesome", "تحليل نتائج الويب", summary, web_query)
                                    except Exception:
                                        st.error("تعذر تلخيص نتائج الويب بالذكاء الاصطناعي الآن.")
                    else:
                        st.error(results['error'])
            else:
                st.warning("اكتب نص البحث أولاً")
    else:
        st.warning("⚠️ محرك البحث على الإنترنت غير متاح. تأكد من تشغيل حاوية SearXNG.")
        st.code("docker compose up searxng -d", language="bash")

# تذييل هادئ بلا تفاصيل تشغيلية.
st.caption("مساحة البحث الأكاديمي الذكية")
