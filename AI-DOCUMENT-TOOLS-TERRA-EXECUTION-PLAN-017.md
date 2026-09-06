# AI-DOCUMENT-TOOLS-TERRA-EXECUTION-PLAN-017

**التاريخ:** 2026-09-06  
**الفرع المستهدف:** `conference-v1`  
**مرجع التشخيص:** `AI-DOCUMENT-TOOLS-ENGINEERING-REVIEW-016.md`  
**المُنفّذ المستهدف:** Codex Terra  
**الحالة:** **READY_FOR_SEQUENTIAL_IMPLEMENTATION**

## 1. الهدف النهائي الملزم

نقل الأدوات التالية من التنفيذ المحلي القديم داخل Streamlit إلى منصة الوظائف الدائمة نفسها التي تستخدمها المحادثة:

1. الملخص.
2. الكيانات.
3. الترجمة.
4. التحليل.
5. الخريطة الذهنية.
6. البحث الأكاديمي وتحليل نتائجه.

يجب أن تعمل الأدوات على النص الحقيقي الكامل للمستند المؤرشف، وأن تحتفظ بنتائج كل مستخدم بصورة خاصة، وأن تقبل عشرة مستخدمين متزامنين دون تجميد Streamlit أو خلط النتائج أو فقد المهام بعد تحديث الصفحة.

## 2. تعليمات التنفيذ إلى Terra

هذه البنود قواعد تنفيذ وليست اقتراحات:

1. اقرأ هذا الملف و`AI-DOCUMENT-TOOLS-ENGINEERING-REVIEW-016.md` قبل أي تعديل.
2. نفّذ المراحل بالترتيب من 0 إلى 12. لا تبدأ مرحلة قبل اجتياز بوابة المرحلة السابقة.
3. لا تغلق أي مربع `[ ]` إلا بعد تشغيل اختبار القبول المذكور وتسجيل دليله في تقرير التنفيذ النهائي.
4. إذا كشف الاختبار عيبًا، أصلحه داخل المرحلة نفسها ثم أعد الاختبار. لا تؤجل عيبًا يمنع بوابة المرحلة.
5. لا تغيّر المحادثة أو خوارزمية RAG أو embeddings أو OCR أو تصميم الصفحة العام إلا في المواضع المحددة هنا.
6. لا تستبدل الخطأ برسالة نجاح، ولا تستخدم نص placeholder مكان المحتوى تحت أي ظرف.
7. لا تنفذ استدعاء LLM أو spaCy أو معالجة مستند أو طلب SearXNG طويل داخل عملية Streamlit.
8. الأرشيف والمستندات المنشورة عامة لكل الزوار. الوظائف والنتائج وسجل الاستخدام خاصة بصاحب workspace فقط.
9. استخدم `document_version_id` كهوية المحتوى. لا تستخدم اسم الملف كمفتاح كاش أو نتيجة.
10. حافظ على RTL وخط Cairo والثيم الفاتح والهوية الموف الحالية ومكونات التنزيل الحالية بعد تصحيح بياناتها.
11. لا تضف مزود ذكاء جديدًا، قاعدة بيانات جديدة، أو خدمة SaaS جديدة.
12. لا تعرض secrets أو storage paths أو stack traces في الواجهة أو API.
13. بعد كل مرحلة شغّل `git diff --check` وPython compile والاختبارات المحددة، ثم راجع `git diff` للتأكد من عدم خروج النطاق.
14. عند اكتمال جميع المراحل أنشئ `AI-DOCUMENT-TOOLS-IMPLEMENTATION-018.md` بالأدلة الفعلية. لا تعلن الجاهزية اعتمادًا على قراءة الكود فقط.

## 3. قرارات معمارية ثابتة

### 3.1 مصدر محتوى المستند

يحفظ عامل الفهرسة artifact مضغوطًا لكل إصدار داخل volume المشترك `./data` قبل نشر الإصدار. لا يعاد بناء المستند عن طريق جمع مقاطع OpenSearch.

المسار الداخلي:

```text
/app/data/document_artifacts/{document_version_id}.json.gz
```

شكل الملف `document-artifact.v1`:

```json
{
  "schema_version": "document-artifact.v1",
  "document_id": "uuid",
  "document_version_id": "uuid",
  "display_name": "paper.pdf",
  "content_hash": "sha256-of-original-pdf",
  "extraction_method": "direct_extraction|ocr",
  "used_ocr": false,
  "full_text": "ordered complete text",
  "pages": [
    {"number": 1, "text": "page text", "char_count": 1234, "word_count": 210}
  ],
  "page_count": 1,
  "char_count": 1234,
  "word_count": 210,
  "created_at": "ISO-8601 UTC"
}
```

قواعد الحفظ:

- JSON UTF-8 بـ`ensure_ascii=False` ثم gzip.
- checksum هو SHA-256 للـJSON غير المضغوط نفسه.
- الكتابة إلى ملف مؤقت داخل المجلد نفسه ثم `os.replace()`.
- لا يدخل أي اسم يرسله المستخدم في المسار؛ المعرّف UUID من قاعدة البيانات فقط.
- القراءة تتحقق من المسار وschema version وchecksum و`document_version_id`.
- إذا كانت `pages` فارغة و`full_text` صالحًا، ينشأ عنصر صفحة واحدة فقط كـfallback موثق.
- لا ينشر إصدار جديد إن فشل حفظ artifact أو كان `full_text.strip()` فارغًا.

### 3.2 بيانات قاعدة البيانات

أضف إلى `backend/models.py` جدولين جديدين.

`DocumentArtifact`:

| العمود | النوع/القيد |
|---|---|
| `version_id` | PK + FK إلى `document_versions.id` |
| `status` | `pending|ready|failed|unavailable`، مفهرس |
| `storage_key` | String nullable؛ لا يظهر للعميل |
| `checksum` | String(64) nullable |
| `schema_version` | String(64)، القيمة الحالية `document-artifact.v1` |
| `page_count` | Integer default 0 |
| `char_count` | Integer default 0 |
| `word_count` | Integer default 0 |
| `used_ocr` | Boolean default false |
| `error_code` | String(64) nullable |
| `created_at` | DateTime UTC |
| `updated_at` | DateTime UTC مع تحديث |

`ToolExecution`:

| العمود | النوع/القيد |
|---|---|
| `job_id` | PK + FK إلى `jobs.id` |
| `owner_id` | FK إلى `user_sessions.id`، مفهرس |
| `request_id` | String(64) |
| `tool_type` | String(32)، مفهرس |
| `document_version_id` | nullable، مفهرس |
| `input_hash` | String(64) |
| `options_hash` | String(64) |
| `schema_version` | String(64) |
| `result_storage_key` | nullable؛ لا يظهر للعميل |
| `result_checksum` | String(64) nullable |
| `result_size_bytes` | Integer default 0 |
| `created_at` | DateTime UTC |
| `updated_at` | DateTime UTC مع تحديث |

قيد فريد على `(owner_id, request_id)`. إعادة الطلب نفسه بنفس hash تعيد الوظيفة الموجودة. استخدام `request_id` نفسه مع payload مختلف يعيد HTTP 409.

أضف إلى `jobs` عبر آلية الأعمدة الإضافية الحالية في `backend/db.py`:

- `error_code VARCHAR(64)` nullable.
- `error_details JSON` nullable، ويقتصر على بيانات آمنة غير حساسة.

الجداول الجديدة تُنشأ بـ`Base.metadata.create_all()`. لا تحذف أو تعيد تسمية أي جدول أو عمود قائم في هذه المهمة.

### 3.3 ملفات النتائج

تحفظ نتيجة الأداة الخاصة بالمستخدم هنا:

```text
/app/data/tool_results/{owner_id}/{job_id}.json.gz
```

يطبق عليها atomic write وchecksum مثل artifact المستند. لا يوضع النص الطويل في `jobs.result`. يحتوي `jobs.result` فقط:

```json
{
  "result_id": "same-as-job-id",
  "tool_type": "summary",
  "schema_version": "summary.v1"
}
```

### 3.4 أنواع الوظائف والطوابير

- `Job.type`: إحدى القيم `tool_summary`, `tool_entities`, `tool_translation`, `tool_analysis`, `tool_mindmap`, `tool_web_search`, `tool_web_analysis`.
- `Job.queue`: القيمة `tools` لكل هذه الأنواع.
- Celery task واحدة: `backend.tasks.run_tool`، وتفوض التنفيذ إلى handler مسجل حسب `tool_type`.
- أضف `tool-worker` في Compose على queue باسم `tools` وconcurrency يساوي 2.
- يبقى `LLM_MAX_CONCURRENCY=2` حدًا عالميًا افتراضيًا بين المحادثة والأدوات. يمكن رفعه بالنشر فقط بعد اختبار المزود والموارد.
- الحدود الافتراضية: `MAX_TOOL_QUEUE=60` و`MAX_OWNER_TOOL_JOBS=2` و`TOOL_JOB_WAIT_SECONDS=1800`.
- حالات `Job.status` تبقى: `queued`, `running`, `cancel_requested`, `cancelled`, `failed`, `completed`.
- تفاصيل المرحلة توضع في `phase`: `loading_content`, `processing`, `merging`, `validating`, `saving`, ثم `completed`.

### 3.5 الخصوصية

- أي مستخدم صالح يستطيع اختيار أي `Document.current_version_id` منشور ومكتمل وartifact حالته `ready`.
- لا يستطيع المستخدم قراءة أو إلغاء أو تنزيل ToolExecution يملكه مستخدم آخر.
- لا تستخدم `JobSubscription` لمهام الأدوات؛ الاشتراك المشترك يبقى خاصًا بإزالة تكرار الفهرسة فقط.
- لا تعاد نتيجة مستخدم من كاش مستخدم آخر. يمكن إعادة استخدام معالجة مستند حتمية عامة مستقبلًا، لكن ليس ضمن هذه المهمة.

## 4. عقد API الثابت

### 4.1 إنشاء وظيفة

```http
POST /tool-jobs
Authorization: Bearer <workspace-token>
Content-Type: application/json
```

الطلب العام:

```json
{
  "tool_type": "summary",
  "request_id": "uuid-or-random-8-to-64",
  "document_version_id": "uuid-or-null",
  "document_version_ids": [],
  "source_job_id": null,
  "input_text": null,
  "options": {}
}
```

الاستجابة:

```json
{
  "job": {
    "id": "uuid",
    "type": "tool_summary",
    "status": "queued",
    "progress": 0,
    "phase": "queued",
    "message": "تم استلام الطلب.",
    "result": {},
    "error_code": null
  },
  "deduplicated": false
}
```

### 4.2 قراءة النتيجة

```http
GET /tool-jobs/{job_id}/result
```

- 202 إذا لم تنته الوظيفة بعد، مع payload الحالة نفسها.
- 200 مع JSON النتيجة بعد اكتمالها والتحقق من checksum.
- 404 إذا لم تكن الوظيفة موجودة أو لم يملكها المستخدم.
- 409 إذا انتهت بالفشل أو الإلغاء، مع `error_code` ورسالة عربية آمنة.

### 4.3 التنزيل

```http
GET /tool-jobs/{job_id}/download?format=json|txt|md|html
```

الصيغ المسموح بها تختلف حسب الأداة. يرفض format غير مدعوم بـ422. اسم التنزيل sanitized ولا يحتوي مسار التخزين.

### 4.4 قائمة مستندات الأرشيف

وسّع العنصر الحالي في `GET /documents` إلى:

```json
{
  "id": "document-id",
  "version_id": "version-id",
  "name": "paper.pdf",
  "published_at": "ISO-8601",
  "content_status": "ready|pending|failed|unavailable",
  "page_count": 10,
  "char_count": 34000,
  "word_count": 5800,
  "used_ocr": true
}
```

لا يعيد هذا endpoint `full_text`, `pages`, `storage_key`, أو checksum.

### 4.5 التحقق حسب الأداة

| الأداة | مصدر الإدخال | options المقبولة |
|---|---|---|
| `summary` | `document_version_id` مطلوب | `summary_type=executive|analytical|quick`, `length=short|medium|detailed`, `include_bullets=bool` |
| `entities` | `document_version_id` مطلوب | `method=fast|llm|research_sections`, `entity_types[]` whitelist |
| `translation` | واحد فقط من المستند أو `input_text` | `target_language` code whitelist، `style=academic|literal|simple`, `keep_formatting`, `scope=page|range|full`, وأرقام الصفحات |
| `analysis` | `document_version_ids` من 1 إلى 5 | `include_topics=bool`, `compare=bool`؛ `compare=true` يحتاج مستندين على الأقل |
| `mindmap` | واحد فقط من المستند أو `input_text` | `target_nodes` من 5 إلى 30؛ طريقة العرض ليست جزءًا من التوليد |
| `web_search` | query داخل `input_text` | `category=academic|general|news|wikipedia`, `language=auto|ar|en`, `max_results` من 5 إلى 20 |
| `web_analysis` | `source_job_id` لوظيفة بحث مكتملة يملكها المستخدم | لا يقبل مستندًا؛ `language=ar|en` |

حد `input_text` المباشر 120000 حرف بعد `strip()`. الاستعلام 2–500 حرف. يرفض أي key غير معروف داخل options حتى لا تتسلل إعدادات غير مدعومة.

## 5. عقد الأخطاء

استخدم هذه الرموز فقط في `Job.error_code` وAPI:

| الرمز | المعنى |
|---|---|
| `document_not_ready` | الإصدار لم ينشر أو artifact ليست ready |
| `content_unavailable` | الأصل أو artifact غير متاح |
| `invalid_request` | options أو المصدر غير صالح |
| `provider_timeout` | انتهت مهلة OpenRouter |
| `provider_rate_limited` | المزود أعاد 429 أو حد السعة |
| `invalid_model_output` | الناتج لا يطابق schema بعد محاولة repair واحدة |
| `search_unavailable` | SearXNG غير متاح |
| `search_no_results` | بحث ناجح بلا نتائج |
| `result_storage_failed` | فشل حفظ النتيجة أو checksum |
| `cancelled` | ألغى المستخدم المهمة |
| `internal_error` | خطأ غير متوقع؛ التفاصيل في log فقط |

رسائل الواجهة عربية ومحددة. لا تعرض exception نصيًا للمستخدم.

## 6. عقود النتائج

### `summary.v1`

```json
{
  "schema_version": "summary.v1",
  "text": "...",
  "bullets": ["..."],
  "citations": [{"page": 2, "excerpt": "short supporting excerpt"}],
  "metrics": {"source_words": 1000, "result_words": 300, "compression_percent": 70.0},
  "coverage": {"processed_pages": 10, "total_pages": 10}
}
```

### `entities.v1`

```json
{
  "schema_version": "entities.v1",
  "method": "fast",
  "items": [{"text": "...", "normalized": "...", "type": "person", "count": 2, "confidence": null, "pages": [1, 4]}],
  "research_sections": [],
  "coverage": {"processed_pages": 10, "total_pages": 10}
}
```

الأنواع المسموحة: `person`, `organization`, `location`, `date`, `method`, `metric`, `concept`, `other`.

### `translation.v1`

```json
{
  "schema_version": "translation.v1",
  "source_language": "ar",
  "target_language": "en",
  "pages": [{"number": 1, "text": "..."}],
  "text": "...",
  "glossary": [{"source": "...", "target": "..."}],
  "coverage": {"processed_pages": 10, "total_pages": 10}
}
```

### `analysis.v1`

```json
{
  "schema_version": "analysis.v1",
  "documents": [{
    "document_version_id": "uuid",
    "metrics": {"words": 1000, "characters_without_spaces": 5000, "sentences": 50, "average_word_length": 5.0},
    "frequent_terms": [{"term": "...", "count": 12}],
    "topics": [{"name": "...", "coverage_percent": 25, "page_refs": [2, 3]}]
  }],
  "comparison": {"shared_topics": [], "differences": []}
}
```

### `mindmap.v1`

```json
{
  "schema_version": "mindmap.v1",
  "central_topic": "...",
  "nodes": [{"id": "n1", "label": "...", "parent_id": null, "page_refs": [1]}],
  "edges": [{"source": "n1", "target": "n2", "label": ""}],
  "coverage": {"processed_pages": 10, "total_pages": 10}
}
```

كل node id فريد، وكل edge يشير إلى node موجود، وعدد العقد بين `target_nodes` و`target_nodes + 5` متى كان المحتوى يسمح.

### `web-search.v1`

```json
{
  "schema_version": "web-search.v1",
  "query": "...",
  "category": "academic",
  "language": "ar",
  "results": [{"title": "...", "url": "https://...", "snippet": "...", "engine": "google scholar", "authors": [], "doi": null, "published_at": null}],
  "suggestions": [],
  "engines_used": ["google scholar"]
}
```

## 7. هيكل الملفات النهائي

أنشئ الملفات التالية:

```text
backend/artifacts.py
backend/tool_contracts.py
backend/tool_runner.py
backend/tooling/__init__.py
backend/tooling/common.py
backend/tooling/summary.py
backend/tooling/entities.py
backend/tooling/translation.py
backend/tooling/analysis.py
backend/tooling/mindmap.py
backend/tooling/web_search.py
backend/backfill_artifacts.py
tests/test_artifacts.py
tests/test_tool_contracts.py
tests/test_tool_api.py
tests/test_tool_handlers.py
tests/test_tool_security.py
tests/test_tool_recovery.py
tests/test_tool_concurrency.py
tests/e2e/document_tools.spec.js
requirements-dev.txt
Dockerfile.test
package.json
playwright.config.js
```

عدّل فقط عند الحاجة:

```text
backend/models.py
backend/db.py
backend/api.py
backend/tasks.py
backend/celery_app.py
processor_optimized.py
platform_client.py
app_optimized.py
web_search.py
docker-compose.yml
.env.example
requirements.txt
Dockerfile
```

لا تنقل كل التطبيق إلى framework جديد، ولا تعيد كتابة واجهة الصفحة.

بيئة الاختبار ثابتة كذلك:

- `requirements-dev.txt` يثبت إصدارًا محددًا من `pytest`, `pytest-timeout`, و`pytest-xdist`.
- `Dockerfile.test` يبدأ من صورة `mysearchengine-app:latest`، يثبت `requirements-dev.txt`، وينسخ `tests/` فقط.
- أضف خدمة Compose باسم `test-runner` تحت profile باسم `test`، تستخدم `Dockerfile.test` و`platform-env` والشبكة نفسها ولا تعمل مع `docker compose up -d` العادي.
- `package.json` يحتوي `@playwright/test` كـdevDependency بإصدار محدد، ويُحفظ `package-lock.json` في Git.
- لا تضف pytest أو Playwright إلى صورة الإنتاج.

## 8. مراحل التنفيذ المتسلسلة

### المرحلة 0 — baseline وحماية النطاق

**المطلوب:**

- [ ] سجل `git status --short` والفرع الحالي دون حذف تغييرات المستخدم.
- [ ] شغّل `docker compose ps` و`docker compose config --quiet`.
- [ ] شغّل compile للملفات الحالية داخل الحاوية.
- [ ] سجل fixture المستند الحالي وعدد المقاطع وإجمالي أحرف النص دون طباعة النص نفسه.
- [ ] ثبّت أن المحادثة الحالية تعمل باختبار smoke قبل التعديل.

**بوابة المرحلة:** كل الخدمات الحالية healthy، ولا يوجد syntax error، واختبار المحادثة baseline مسجل. إذا فشل baseline، أصلح فقط مانع الاختبار أو سجله كمانع حقيقي قبل متابعة أدوات المستند.

### المرحلة 1 — التخزين الذري وعقود البيانات

**الملفات:** `backend/models.py`, `backend/db.py`, `backend/artifacts.py`, `backend/tool_contracts.py`, واختباراتها.

**المطلوب:**

- [ ] أضف `DocumentArtifact` و`ToolExecution` والقيود المحددة.
- [ ] أضف عمودي الخطأ إلى Job بطريقة additive وآمنة لقاعدة حالية.
- [ ] نفّذ كتابة/قراءة document artifacts وtool results مع gzip وchecksum وatomic replace.
- [ ] نفّذ Pydantic models منفصلة لكل options وvalidator يرفض الحقول الزائدة.
- [ ] نفّذ canonical JSON hashing للطلب والخيارات.
- [ ] اختبر تلف gzip، checksum خاطئ، path traversal، schema غير معروف، وكتابتين متزامنتين.

**بوابة المرحلة:** اختبارات artifact والعقود كلها ناجحة، وإعادة تشغيل API لا تفقد البيانات القديمة ولا تغير counts الحالية.

**يغلق:** DT-P0-02 جزئيًا، وأساس DT-P0-04.

### المرحلة 2 — حفظ artifact أثناء الفهرسة وbackfill

**الملفات:** `backend/tasks.py`, `backend/artifacts.py`, `backend/backfill_artifacts.py`, `processor_optimized.py`, API document payload.

**المطلوب:**

- [ ] استبدل المتغيرات المهملة `_raw`, `_ocr`, `_pages` في `index_document` باستخدام فعلي.
- [ ] حول الصفحات إلى الشكل المحدد واحفظ artifact قبل `publish_staged_version()`.
- [ ] أضف `chunk_index` و`page_number` متى توفر إلى metadata المقاطع الجديدة، من دون الاعتماد عليهما لبناء artifact.
- [ ] لا تنشر الإصدار إذا فشل artifact؛ اضبط حالته وفشل الوظيفة دون حذف الإصدار المنشور السابق.
- [ ] وسع `/documents` ببيانات `content_status` والإحصاءات فقط.
- [ ] نفّذ backfill تسلسليًا للإصدارات المنشورة المفتقدة للـartifact من `Document.storage_key`.
- [ ] لا تشغل backfill تلقائيًا عند startup. الأمر الإداري هو:

```bash
docker compose exec -T index-worker python -m backend.backfill_artifacts --limit 100
```

- [ ] إذا كان الأصل مفقودًا، أنشئ record بحالة `unavailable` ولا تفبرك نصًا من OpenSearch.

**بوابة المرحلة:** المستند الحالي يصبح `content_status=ready` وتطابق `page_count/char_count/word_count` بين artifact وAPI. إعادة تشغيل كل الحاويات ثم قراءة المستند تعطي القيم نفسها. فهرسة fixture جديدة تنشر الفهرس والـartifact معًا أو لا تنشر أيًا منهما.

**يغلق:** DT-P0-01 وDT-P0-02 وTRN-01 وTRN-02 وMAP-01 وANL-01.

### المرحلة 3 — منصة Tool Jobs

**الملفات:** `backend/api.py`, `backend/tasks.py`, `backend/celery_app.py`, `backend/tool_runner.py`, `platform_client.py`, `docker-compose.yml`, `.env.example`.

**المطلوب:**

- [ ] أضف POST `/tool-jobs` وGET result/download بالعقد المحدد.
- [ ] طبّق admission locks وحدود global/owner مثل مهام الفهرسة.
- [ ] تحقق أن الإصدار هو `Document.current_version_id` منشور ومكتمل وartifact ready.
- [ ] طبّق idempotency عبر `ToolExecution` والمعاملة نفسها التي تنشئ Job وOutbox.
- [ ] أضف task route و`tool-worker` وhealthcheck حقيقيًا للعامل.
- [ ] أضف methods إلى `PlatformClient`: `create_tool_job`, `tool_result`, `download_tool_result`.
- [ ] استخدم نظام lease/heartbeat/deadline/cancel الحالي؛ صحح `update_job` لكتابة `error_code/error_details` بأمان.
- [ ] نفّذ handler تجريبي داخلي deterministic لا يصل للمزود لإثبات دورة الوظيفة، ثم احذفه قبل نهاية المرحلة.

**بوابة المرحلة:** إنشاء/استعادة/إلغاء job يعمل بعد refresh؛ request مكرر لا ينشئ وظيفتين؛ payload مختلف بنفس request id يعيد 409؛ مستخدم آخر يحصل على 404؛ قتل tool-worker أثناء handler تجريبي ثم عودته لا يكتب نتيجتين.

**يغلق:** أساس DT-P0-03 وDT-P0-04.

### المرحلة 4 — الملخص

**الملفات:** `backend/tooling/common.py`, `backend/tooling/summary.py`, tests. لا تعدّل UI في هذه المرحلة.

**المطلوب:**

- [ ] اقرأ artifact كاملًا وقسمه حسب الصفحات وبميزانية tokens محافظة.
- [ ] map summaries تحفظ page refs، ثم reduce نهائي لا يضيف معلومة بلا دعم.
- [ ] طبّق الأنواع الثلاثة وأهداف الطول: قصير 150–250، متوسط 350–600، مفصل 800–1200 كلمة تقريبية، مع السماح بمستند أقصر من الهدف.
- [ ] احترم `include_bullets` فعليًا.
- [ ] تحقق من `summary.v1` ومن coverage كامل قبل النجاح.
- [ ] retry للمقطع الفاشل فقط، بحد المزود الحالي؛ repair واحد لإخراج schema ثم `invalid_model_output`.

**بوابة المرحلة:** API test على مستند 2 صفحة ومستند 50 صفحة؛ coverage كامل؛ الخيارات تغير الناتج؛ لا يوجد truncation صامت؛ result يبقى بعد restart.

**يغلق:** SUM-01 إلى SUM-07.

### المرحلة 5 — الكيانات

**الملفات:** `backend/tooling/entities.py`, tests.

**المطلوب:**

- [ ] حمّل spaCy singleton مرة واحدة لكل process داخل tool-worker مع lock.
- [ ] عالج كل صفحة، ثم normalize/deduplicate واجمع count وpages.
- [ ] ترجم labels إلى الأنواع الثابتة في `entities.v1`.
- [ ] في LLM mode استخدم chunks وJSON schema ودمجًا حتميًا.
- [ ] في research sections أعد أقسامًا structured مع confidence وpage refs.
- [ ] إذا فشل spaCy نفّذ fallback المعلن فعليًا أو أعد خطأ صريحًا؛ لا تعرض وعدًا كاذبًا.

**بوابة المرحلة:** fixture عربية ذات كيانات معروفة تحقق baseline موثق، كل الصفحات معالجة، لا duplicate بعد التطبيع، وتحميل النموذج لا يتكرر لكل job.

**يغلق:** ENT-01 إلى ENT-07.

### المرحلة 6 — الترجمة

**الملفات:** `backend/tooling/translation.py`, tests.

**المطلوب:**

- [ ] حدد الصفحات المطلوبة من artifact؛ page/range/full تعمل بأرقام حقيقية.
- [ ] كشف لغة المصدر؛ استخدم language codes وليس عناوين القائمة.
- [ ] قسم الصفحة الطويلة حسب token budget مع overlap سياقي محدود.
- [ ] أنشئ glossary للمصطلحات ومرره للمقاطع لضمان الاتساق.
- [ ] نفّذ `keep_formatting` للعناوين والقوائم والجداول البسيطة.
- [ ] احفظ كل جزء مكتمل في checkpoint خاص بالjob لكي تستأنف retry من الجزء الفاشل.
- [ ] افحص processed pages مقابل total requested قبل success.

**بوابة المرحلة:** ترجمة صفحة ونطاق وكامل PDF مختلط؛ restart للعامل في المنتصف ثم استكمال دون تكرار/فقد؛ الخيار الخاص بالتنسيق يغير النتيجة فعلًا؛ 429 لا يمحو الأجزاء المكتملة.

**يغلق:** TRN-01 إلى TRN-08.

### المرحلة 7 — التحليل والمقارنة

**الملفات:** `backend/tooling/analysis.py`, tests.

**المطلوب:**

- [ ] نفّذ metrics حتمية Unicode-aware خارج LLM.
- [ ] `characters_without_spaces` لا يحسب whitespace، ومتوسط الكلمة يحسب حروف الكلمات فقط.
- [ ] طبّع العربية للـfrequency analysis مع stopwords عربية موثقة داخل الكود واختبارها.
- [ ] حلل الموضوعات على كامل الصفحات map/reduce مع page refs.
- [ ] عند `compare=true` أعد shared topics وdifferences فعلية بين 2–5 إصدارات.
- [ ] لا تحمل النصوص إلى Streamlit ولا تخزنها داخل session state.

**بوابة المرحلة:** corpus صغير معروف العدد يطابق metrics؛ مستندان مختلفان ينتجان مقارنة غير فارغة ومدعمة؛ coverage كامل؛ ذاكرة Streamlit لا تتغير مع حجم PDF.

**يغلق:** ANL-01 إلى ANL-07.

### المرحلة 8 — الخريطة الذهنية

**الملفات:** `backend/tooling/mindmap.py`, tests. العرض داخل UI يؤجل للمرحلة 10.

**المطلوب:**

- [ ] أخرج JSON يطابق `mindmap.v1` بدل parsing Markdown حر.
- [ ] غط كامل المستند map/reduce وأبق page refs.
- [ ] احترم `target_nodes`; repair واحد فقط إذا نقصت/فسدت البنية.
- [ ] تحقق من uniqueness للعقد وصحة edges وعدم وجود cycles غير مقصودة.
- [ ] لا يدخل render mode إلى مفتاح نتيجة التوليد؛ هو اختيار عرض فقط.
- [ ] وحّد المنطق المستخدم وأوقف الاعتماد على المولد المكرر بعد إثبات التكافؤ.

**بوابة المرحلة:** مخطط صالح لثلاثة fixtures، كل edge صالح، عدد العقد ضمن العقد، وناتج invalid من fake provider ينتهي `invalid_model_output` لا نجاحًا فارغًا.

**يغلق:** MAP-01 إلى MAP-04 وMAP-08 وMAP-09.

### المرحلة 9 — البحث الأكاديمي

**الملفات:** `web_search.py`, `backend/tooling/web_search.py`, tests.

**المطلوب:**

- [ ] استخدم `requests.Session` وhealth cache TTL 15 ثانية؛ الفشل يفتح circuit 15 ثانية ثم يسمح بمحاولة استرداد.
- [ ] category ويكيبيديا يحدد محرك ويكيبيديا صراحة أو يعيد `search_unavailable` إذا غير متاح؛ لا يسقط إلى general بصمت.
- [ ] category الأكاديمي يستخدم allowlist من capabilities المتاحة فعليًا ويعيد `engines_used`.
- [ ] كشف اللغة عند `auto` وتمرير ar/en الصحيح.
- [ ] normalize URL وDOI والعنوان، إزالة التكرار، وقبول http/https فقط.
- [ ] success بلا نتائج يتحول إلى `search_no_results` وحالة UI مناسبة.
- [ ] خزّن النتائج كـ`web-search.v1`.
- [ ] `web_analysis` يقرأ فقط نتيجة بحث يملكها المستخدم، يعزل النصوص الخارجية عن تعليمات النظام، ويضع حدودًا للطول والمصادر.
- [ ] أضف timeout وretry/backoff محدودين مع log للengine failures دون بيانات حساسة.

**بوابة المرحلة:** اختبارات fake SearXNG للحالات 200/empty/timeout/500/bad URL/duplicates/recovery، واختبار حي واحد لكل من academic وWikipedia. يجب أن يطابق `engines_used` ما استُخدم فعلًا.

**يغلق:** WEB-01 إلى WEB-10. أصلح WEB-11 في إعدادات proxy عند توفر proxy النشر؛ في Docker المحلي يكفي توثيق trusted direct path وعدم اعتبار خطأ bot-detection نجاحًا وظيفيًا.

### المرحلة 10 — ترحيل واجهة Streamlit

**الملفات:** `app_optimized.py`, `platform_client.py`, `style.css` فقط عند ضرورة حالة مرئية.

**المطلوب المشترك:**

- [ ] في platform mode، استبدل `last_full_text` كقائمة مصادر بـcatalog مستندات من API، keyed by version id.
- [ ] لا تجلب full text إلى الواجهة. ارسل version ids والخيارات فقط.
- [ ] أضف helper واحدًا لإدارة `tool_job_id` لكل تبويب، يستخدم `st.fragment(run_every="2s")` مثل المحادثة والفهرسة.
- [ ] يستعيد helper الوظائف غير النهائية من `/jobs` بعد refresh، ويوقف polling بعد terminal state.
- [ ] يعرض progress حقيقيًا، phase عربية، إلغاء، إعادة محاولة جديدة بـrequest id جديد، والخطأ المحدد.
- [ ] يعرض النتيجة المخزنة والتنزيل فقط بعد اكتمالها وصحة محتواها.
- [ ] امنع الضغط المكرر أثناء وجود job نشط للأداة نفسها.

**المطلوب لكل تبويب:**

- [ ] الملخص: اربط النوع والطول والنقاط؛ أخف زر التنزيل قبل النتيجة؛ metrics من result.
- [ ] الكيانات: اعرض النوع العربي والعدد والثقة والصفحات؛ fallback صادق.
- [ ] الترجمة: اعرض عدد الصفحات الحقيقي؛ احذف separators القابلة للاختيار؛ طبّق scope والتقدم والتنزيل.
- [ ] التحليل: اعرض metrics المنظمة والمقارنة؛ empty state واضح لتوزيع صغير.
- [ ] الخريطة: حوّل `mindmap.v1` داخل UI إلى Markmap/D3/Plotly بثلاثة renderers مستقلة. ثبت حزم العرض محليًا بدل CDN، واستخدم ألوان الثيم الفاتح وfallback نصيًا.
- [ ] البحث: خزّن النتيجة عبر job؛ analysis job منفصلة؛ اعرض no-results وengines المستخدمة.
- [ ] احذف أو اعزل كل استدعاءات LLM/spaCy/SearXNG المباشرة من مسارات التبويبات الست.

**بوابة المرحلة:** اختبار المتصفح لكل تبويب من جلسة جديدة على مستند الأرشيف الحالي. لا يظهر 37 حرفًا/6 كلمات، ولا زر صامت، ولا نتيجة فارغة، ولا page error. بعد refresh أثناء العمل تظهر الوظيفة نفسها ثم النتيجة.

**يغلق:** DT-P0-03 وDT-P0-04 وبقية عيوب العرض MAP-05 إلى MAP-07.

### المرحلة 11 — الاستقرار والعشرة مستخدمين

**الملفات:** tests والضبط فقط؛ لا تغير سلوكًا وظيفيًا دون اختبار regression.

أنشئ provider fake deterministic للاختبارات، ولا تستخدم رصيد OpenRouter في load test الكامل.

**السيناريو الإلزامي:** عشرة workspaces مستقلة تبدأ في اللحظة نفسها:

| المستخدمون | العملية |
|---|---|
| 1–2 | محادثة على مستند محدد |
| 3–4 | ملخصان بخيارات مختلفة |
| 5–6 | ترجمة صفحة ومستند كامل |
| 7 | استخراج كيانات LLM |
| 8 | تحليل مستندين ومقارنة |
| 9 | خريطة ذهنية |
| 10 | بحث أكاديمي ثم تحليل النتائج |

أثناء الاختبار:

- [ ] refresh لثلاث جلسات أثناء queued/running.
- [ ] إلغاء وظيفة واحدة.
- [ ] قتل `tool-worker` أثناء وظيفة ثم تشغيله.
- [ ] حقن provider 429 وtimeout وinvalid JSON.
- [ ] إيقاف SearXNG ثم إعادته.
- [ ] محاولة قراءة نتيجة مستخدم من token مستخدم آخر.
- [ ] التحقق من بقاء المحادثة والفهرسة responsive.

**مقاييس القبول:**

- HTTP قبول الوظيفة p95 أقل من ثانية في البيئة المحلية المستقرة.
- ظهور تغير حالة UI خلال 5 ثوانٍ.
- صفر jobs مقبولة مفقودة، وصفر نتائج مختلطة، وصفر نشر مستند جزئي.
- صفر استدعاء LLM من عملية Streamlit مثبت بالmock/patch والبحث الساكن.
- كل الوظائف غير الملغاة تصل terminal state في حدود المهلة المهيأة.
- لا restart بسبب OOM ولا نمو مستمر في RSS بعد انتهاء الجولة ومرور دورتين إضافيتين.
- لا تتجاوز الاستدعاءات الفعلية حد `LLM_MAX_CONCURRENCY`.
- فشل SearXNG لا يعطل الأدوات الأخرى، وعودته تُكتشف دون restart.

بعد نجاح fake provider، نفّذ smoke محدودًا على OpenRouter الحقيقي: مستخدمان وطلب واحد قصير لكل أداة تعتمد LLM. لا تعتبر load test الحقيقي شرطًا لأن زمن المزود ورصيده خارجيان، لكن سجل زمن كل طلب وأي 429.

**بوابة المرحلة:** السيناريو ينجح مرتين متتاليتين من بيئة بيانات اختبار نظيفة.

### المرحلة 12 — التنظيف والتقرير النهائي

**المطلوب:**

- [ ] احذف المسارات القديمة غير المستخدمة للأدوات فقط بعد إثبات عدم وجود references.
- [ ] لا تحذف fallback المحادثة المحلي إن كان ما زال مقصودًا خارج platform mode.
- [ ] حدّث `.env.example` وREADME بمتغيرات tools وbackfill وطرق التشغيل.
- [ ] شغّل full test suite وbrowser E2E و`docker compose config --quiet` وhealth checks.
- [ ] راجع logs بحثًا عن Traceback/ERROR/timeout/429 غير متوقع.
- [ ] تأكد أن Git لا يحتوي `.env` أو artifacts أو results أو مفاتيح.
- [ ] أنشئ `AI-DOCUMENT-TOOLS-IMPLEMENTATION-018.md` واربط كل ID من التقرير 016 بدليل إغلاق أو سبب بقاء موثق.

**الحكم النهائي المسموح:**

- `READY_FOR_10_USER_REVIEW` فقط بعد نجاح المرحلة 11 مرتين.
- `NOT_READY` إذا بقي أي P0/P1 أو فشل أي اختبار عزل/استعادة/تزامن.

## 9. اختبارات إلزامية بحسب الطبقة

### Unit

- artifact serialization/checksum/atomicity/path safety.
- request validation ورفض extra fields.
- Arabic metrics والتطبيع.
- dedup للكيانات ونتائج البحث.
- mindmap schema/graph validation.
- translation page/range selection وcheckpoint merge.
- health TTL/circuit recovery.

### API/DB contract

- authorization والملكية.
- public document selection.
- idempotency وpayload conflict.
- admission limits.
- job terminal states وerror codes.
- result/download access.
- migration على نسخة DB موجودة، ثم restart ثانٍ دون تكرار أو خطأ.

### Worker integration

- outbox dispatch مرة منطقية رغم redelivery.
- lease expiry وworker restart.
- cancellation بين المقاطع.
- provider retry والـdeadline.
- checksum failure يمنع completed.

### Browser E2E

- Desktop 1440، tablet 768، mobile 390 و375.
- كل تبويب: submit، loading، progress، cancel، success، download، error، refresh restore.
- RTL للنص العربي وLTR للرابط/DOI/اللغة الإنجليزية.
- الخريطة: Markmap وD3 وPlotly كل منها renderer مختلف.
- لا overflow أفقي ولا composer/sidebar regression.

## 10. Fixtures الملزمة

لا تعتمد على ملف واحد:

1. PDF عربي نصي من صفحتين بنتائج متوقعة ثابتة.
2. PDF عربي OCR من صفحتين.
3. PDF إنجليزي.
4. PDF مختلط RTL/LTR.
5. PDF من 50 صفحة.
6. PDF بعناوين وقوائم وجدول.
7. PDF فارغ، تالف، ومحمي.
8. إصداران بالاسم نفسه ومحتوى مختلف.
9. نتائج ويب تحوي URL مكررًا وDOI مكررًا ورابط `javascript:`.
10. نص مستند ونتيجة ويب تحتوي محاولة prompt injection.

ضع fixtures الصغيرة الآمنة تحت `tests/fixtures/`. أنشئ المستند الطويل حتميًا أثناء الاختبار بدل تخزين ملف ضخم في Git.

## 11. أوامر التحقق القياسية

بعد إضافة test dependencies وPlaywright config نفّذ من `F:\docker\files`:

```powershell
git diff --check
docker compose config --quiet
docker compose build
docker compose up -d
docker compose ps
docker compose exec -T api python -m py_compile backend/api.py backend/tasks.py backend/artifacts.py backend/tool_runner.py backend/tool_contracts.py
docker compose exec -T streamlit-app python -m py_compile app_optimized.py platform_client.py web_search.py
docker compose --profile test build test-runner
docker compose --profile test run --rm test-runner python -m pytest -q tests
npm ci
npx playwright test
```

لا تثبت dependencies يدويًا داخل حاوية حية، ولا تشغّل اختبارات Python من صورة الإنتاج.

## 12. منع الخروج عن النطاق

لا تشمل هذه الخطة:

- تغيير نموذج OpenRouter أو prompts المحادثة.
- تغيير خوارزمية retrieval أو ranking للمحادثة.
- تحويل Streamlit إلى React أو Next.js.
- تسجيل دخول بحسابات أو صلاحيات إدارية جديدة.
- جعل الأرشيف خاصًا بكل مستخدم.
- تغيير حد PDF الحالي: 25MB و100 صفحة.
- تغيير الهوية البصرية أو إعادة الجولة التعريفية.
- دمج نتائج الأدوات في المحادثة تلقائيًا.

أي ضرورة جديدة تظهر أثناء التنفيذ تسجل أولًا في تقرير التنفيذ مع السبب والأثر. لا توسع النطاق تلقائيًا إلا إذا كانت الضرورة تمنع معيار قبول واردًا هنا.

## 13. جدول التتبع إلى تقرير 016

| مجموعة التقرير 016 | مرحلة الإغلاق |
|---|---|
| DT-P0-01 وDT-P0-02 | 1–2 |
| DT-P0-03 وDT-P0-04 | 3 و10 |
| SUM-01..07 | 4 و10 |
| ENT-01..07 | 5 و10 |
| TRN-01..08 | 6 و10 |
| ANL-01..07 | 7 و10 |
| MAP-01..09 | 8 و10 |
| WEB-01..11 | 9 و10 وإعداد نشر proxy للبند 11 |
| التزامن والاستعادة | 11 |
| التوثيق وبوابة الجاهزية | 12 |

## 14. Definition of Done

يكتمل هذا العمل فقط عندما:

- [ ] يوجد artifact مرتب وصالح لكل إصدار منشور مستخدم في الاختبار.
- [ ] لا تحتوي `app_optimized.py` لمسارات الأدوات على استدعاء LLM أو spaCy أو SearXNG مباشر.
- [ ] كل الأدوات تعمل من جلسة جديدة على الأرشيف العام.
- [ ] كل نتيجة خاصة بصاحبها، قابلة للاستعادة والتنزيل.
- [ ] كل الخيارات المرئية تؤثر فعليًا أو أزيلت.
- [ ] لا يوجد truncation أو coverage ناقص غير معلن.
- [ ] لا يوجد نجاح بناتج فارغ أو schema غير صالح.
- [ ] اختبار عشرة مستخدمين ينجح مرتين متتاليتين.
- [ ] regression المحادثة والرفع والفهرسة والأرشيف ينجح.
- [ ] التقرير 018 يحتوي الأدلة والأزمنة والنتائج وحالة كل عيب من التقرير 016.

## 15. النص الجاهز لبدء Terra

استخدم الطلب التالي كما هو:

```text
اقرأ AI-DOCUMENT-TOOLS-TERRA-EXECUTION-PLAN-017.md ومرجعه
AI-DOCUMENT-TOOLS-ENGINEERING-REVIEW-016.md، ثم نفذ الخطة كاملة بالترتيب من
المرحلة 0 إلى المرحلة 12. اعتبر القرارات والعقود وحدود النطاق في الخطة ملزمة.
لا تنتقل من مرحلة قبل نجاح بوابتها، ولا تغلق checkbox دون دليل اختبار فعلي.
حافظ على المحادثة والرفع والفهرسة والأرشيف العام والتصميم الحالي. عند الانتهاء
أنشئ AI-DOCUMENT-TOOLS-IMPLEMENTATION-018.md وسجل فيه نتيجة كل اختبار وحالة كل
ID من التقرير 016. لا تعلن READY_FOR_10_USER_REVIEW إلا بعد نجاح اختبار عشرة
مستخدمين مرتين متتاليتين.
```
