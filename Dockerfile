# ════════════════════════════════════════════════════════
#  MySearchEngine – Dockerfile (محسّن للبناء السريع)
# ════════════════════════════════════════════════════════
FROM python:3.11-slim

# ── 1. تثبيت أدوات النظام ────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-ara \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    gcc \
    g++ \
    curl \
    wget \
 && rm -rf /var/lib/apt/lists/*

# ── 2. مجلد العمل ────────────────────────────────────
WORKDIR /app

# ── 3. نسخ requirements أولاً (cache layer) ──────────
COPY requirements.txt .

# ── 4. تحديث pip وتثبيت PyTorch CPU ──────────────────
RUN pip install --upgrade pip --no-cache-dir

RUN pip install --no-cache-dir torch \
    --index-url https://download.pytorch.org/whl/cpu

# ── 5. تثبيت باقي المكتبات ───────────────────────────
RUN pip install --no-cache-dir -r requirements.txt

# ── 6. تحميل نموذج spaCy ─────────────────────────────
RUN python -m spacy download xx_ent_wiki_sm

# ── 7. نسخ ملفات المشروع ─────────────────────────────
COPY processor_optimized.py .
COPY engine_optimized.py .
COPY openrouter_client.py .
COPY research_extractor.py .
COPY utils.py .
COPY app_optimized.py .
COPY style.css .
COPY redis_cache.py .
COPY web_search.py .

# تحقق من وجود ملفات اختيارية قبل النسخ
COPY arabic_text_processor.py* ./
COPY intelligent_prompts_library.py* ./
COPY advanced_mindmap.py* ./

# ── 8. المتغيرات البيئية ──────────────────────────────
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV OPENSEARCH_URL=http://opensearch:9200
ENV REDIS_URL=redis://redis:6379/0
ENV SEARXNG_URL=http://searxng:8080
ENV TESSERACT_CMD=/usr/bin/tesseract

# ── 9. إنشاء مجلد البيانات ────────────────────────────
RUN mkdir -p /app/data

# ── 10. فتح المنفذ وتشغيل التطبيق ────────────────────
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app_optimized.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
