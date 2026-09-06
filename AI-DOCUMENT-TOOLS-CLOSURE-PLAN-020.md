# AI-DOCUMENT-TOOLS-CLOSURE-PLAN-020

**التاريخ:** 2026-09-06  
**يعتمد على:** `AI-DOCUMENT-TOOLS-TERRA-REVIEW-019.md` و`AI-DOCUMENT-TOOLS-ENGINEERING-REVIEW-016.md`  
**الهدف:** إغلاق الأدوات الست وتشغيلها باستقرار مع عشرة مستخدمين متزامنين، مع بقاء الأرشيف عامًا والنتائج والمحادثات خاصة بكل مستخدم  
**طريقة التنفيذ:** مراحل متسلسلة ببوابة قبول؛ لا توجد تقديرات أيام، ولا يُعلن الإغلاق وفق الانطباع البصري

## 1. ثوابت النطاق

- لا تغير منطق المحادثة أو RAG أو التحديد بالمستند إلا عند إصلاح regression مثبت باختبار.
- لا تغير كون الأرشيف عامًا لكل المستخدمين.
- تبقى المحادثات، وظائف الأدوات، النتائج، والتنزيلات خاصة بصاحب workspace token.
- Streamlit طبقة عرض فقط في platform mode؛ لا يدخل إليها full text ولا spaCy ولا استدعاء LLM أو SearXNG.
- لا تعرض نجاحًا إذا كان الناتج فارغًا أو schema غير صالح أو التغطية ناقصة دون تصريح.
- لا تحذف fallback المحلي قبل إثبات أن وضع المنصة لا يعتمد عليه؛ اعزله في دالة/وحدة واضحة بدل الاعتماد على `st.stop()` كحد معماري.
- لا تطبع أسرارًا أو محتوى مستندات في logs أو تقارير الاختبار.

## 2. تعريف الإغلاق

يُعد العمل مغلقًا فقط عندما تتحقق الشروط كلها:

- كل IDs في التقرير 016 لها `CLOSED` ودليل اختبار، أو قرار حذف خيار غير منفذ من المنتج.
- كل خيار ظاهر للمستخدم يؤثر فعليًا في النتيجة.
- كل وظيفة تستعاد بعد refresh، وتُنهي الإلغاء والتعطل بحالة نهائية صحيحة.
- ملفات 100 صفحة ضمن الحد تعمل بتغطية معلنة من غير تمرير النص كاملًا إلى طلب نموذج واحد.
- نتائج الملخص والموضوعات والخريطة مرتبطة بصفحات PDF الأصلية.
- عشرة مستخدمين ينفذون الحمل المختلط مرتين متتاليتين دون تسرب أو Job عالق أو تجميد للمحادثة.
- Unit وAPI/DB وworker integration وBrowser E2E وchaos tests موجودة داخل المستودع وتنجح من بيئة نظيفة.
- تقرير التنفيذ النهائي `AI-DOCUMENT-TOOLS-IMPLEMENTATION-021.md` يحتوي الأوامر والنتائج والمقاييس وربط كل عيب.

## 3. الترتيب التنفيذي الملزم

### المرحلة 0 — تثبيت baseline وبنية الاختبارات

**الهدف:** جعل كل ادعاء لاحق قابلًا للتكرار.

- [ ] أنشئ `tests/unit`, `tests/contracts`, `tests/integration`, `tests/load`, و`tests/e2e`.
- [ ] أضف dependencies اختبار منفصلة وrunner داخل Docker؛ لا تعتمد على برامج مثبتة يدويًا على جهاز المطور.
- [ ] أنشئ fixtures آمنة: عربي نصي، عربي OCR، إنجليزي، RTL/LTR مختلط، جداول وقوائم، 50+ صفحة، صفحة فارغة وسط الملف، تالف، محمي، ونسختان لهما الاسم نفسه ومحتوى مختلف.
- [ ] سجل baseline للمحادثة والرفع والفهرسة والأرشيف مع لقطة metrics دون محتوى خام.
- [ ] أضف command واحدًا يشغل lint/compile/unit/contracts، وcommand مستقلًا لـE2E/load/chaos.
- [ ] ألغ مفتاح المزود المكشوف سابقًا وأصدر مفتاحًا جديدًا قبل أي اختبار مزود أو نشر.

**البوابة G0:** الاختبارات الحالية تبدأ وتنتج تقارير JUnit/JSON، وsmoke المحادثة والفهرسة ينجح قبل تعديل السلوك.

### المرحلة 1 — إصلاح دورة حياة Job والتعافي

**الهدف:** لا تبقى وظيفة عالقة، ولا يعاد حساب نتيجة مكتملة عند restart.

**الملفات الأساسية:** `backend/tasks.py`, `backend/dispatcher.py`, `backend/models.py`, `backend/db.py`, `backend/tool_runner.py`, `backend/api.py`.

- [ ] استبدل `update_job()` بانتقالات حالة صريحة ومشروطة في قاعدة البيانات، تسمح فقط بالانتقالات القانونية وتسمح `cancel_requested -> cancelled`.
- [ ] أضف finalizer واحدًا ذريًا يكتب `status`, `phase`, `message`, `error_code`, `error_details`, `finished_at`, وresult pointer في معاملة واضحة.
- [ ] أضف recovery sweeper دوريًا للوظائف `queued/running/cancel_requested` ذات lease المنتهي.
- [ ] عند worker loss: إذا النتيجة المحفوظة checksum-valid، أغلق Job كـcompleted؛ وإلا أعد نشره بمحاولة محدودة.
- [ ] اجعل إعادة التشغيل idempotent على مستوى checkpoint/result، ولا تعيد provider call لجزء مكتمل.
- [ ] أضف `attempt`, `max_attempts`, وسبب الاستعادة إلى logs/metrics دون بيانات حساسة.
- [ ] اختبر الانقطاع في ثلاث نقاط: قبل كتابة النتيجة، بعد كتابة الملف قبل DB، وبعد DB قبل اكتمال Job.
- [ ] اجعل healthcheck لكل Celery worker يستهدف hostname والـqueue المحددين، لا أي `pong`.

**اختبارات إلزامية:** running cancel، queued cancel، hard kill، soft timeout، lease expiry، broker redelivery، result reconciliation، duplicate delivery.

**البوابة G1:** صفر Job يبقى active بعد نافذة التعافي، والإلغاء ينتهي `cancelled`، وإعادة العامل لا تضاعف provider calls للمقاطع المكتملة.

### المرحلة 2 — migrations والعقود الصارمة

**الهدف:** رفض الخطأ عند API وإغلاق النجاح الشكلي.

**الملفات الأساسية:** migrations جديدة، `backend/models.py`, `backend/tool_contracts.py`, `backend/api.py`, وملف `backend/tool_result_contracts.py` جديد.

- [ ] أضف migration versioned للجداول والأعمدة والفهارس والقيود؛ اختبر upgrade من نسخة قاعدة ما قبل Terra على نسخة احتياطية.
- [ ] اجعل IDs من نوع UUID في العقود أو تحقق صياغتها صراحة.
- [ ] أنشئ Options model مستقلًا لكل أداة مع `extra=forbid` بدل `dict[str, Any]` العام.
- [ ] الترجمة: `page` مطلوب وموجب مع scope page، و`start_page/end_page` مطلوبان ومرتّبان مع range، وتُراجع الحدود مقابل artifact قبل إنشاء Job.
- [ ] التحليل: 1–5 version IDs فريدة؛ المقارنة تحتاج 2–5 مستندات مختلفة.
- [ ] الكيانات: allowlist موحدة لـentity types، ورفض الأنواع غير المدعومة.
- [ ] امنع خلط المصادر: summary/entities تقبل إصدارًا واحدًا فقط؛ translation/mindmap تقبل مصدرًا واحدًا فقط؛ web analysis يقبل search result مملوكًا ومكتملًا فقط.
- [ ] أنشئ Pydantic result model لكل `summary.v1`, `entities.v1`, `translation.v1`, `analysis.v1`, `mindmap.v1`, `web-search.v1`, و`web-analysis.v1`.
- [ ] لا يحفظ `tool_runner` نتيجة قبل نجاح model validation وفحص non-empty/coverage.
- [ ] وحّد mapping الأخطاء إلى 422/409 وحالات Job المعلنة؛ لا يتحول خطأ مستخدم إلى `internal_error`.
- [ ] عند سباق idempotency، اقرأ السجل الفائز وأعده إذا تطابق hash بدل 409 عام.
- [ ] أضف `tool_revision`, `model_revision`, وresult cache identity صريحًا حتى لا تُعاد نتيجة قديمة بعد تغيير الخوارزمية.

**البوابة G2:** contract matrix لكل أداة ينجح، وكل payload غير صالح يُرفض قبل Outbox، وكل result غير صالح ينتهي `invalid_model_output` بلا ملف نهائي.

### المرحلة 3 — صحة artifact والصفحات

**الهدف:** page refs تعني أرقام PDF الأصلية دائمًا.

**الملفات الأساسية:** `processor_optimized.py`, `backend/artifacts.py`, `backend/tasks.py`, `backend/backfill_artifacts.py`.

- [ ] احتفظ بسجل لكل صفحة أصلية ورقمها حتى إن كانت فارغة؛ استخدم `has_text` أو status بدل حذف الصفحة وإعادة الترقيم.
- [ ] اربط كل chunk بـ`page_number` الأصلي و`chunk_index` الحتمي.
- [ ] عرّف الفرق بين `pdf_page_count`, `processed_pages`, `text_pages`, و`coverage` في schema.
- [ ] تحقق أن `full_text` مشتق حتميًا من الصفحات وأن checksum يعاد بنفس النتيجة.
- [ ] انقل `StoredFile` إلى وحدة مشتركة خفيفة؛ لا يستورد backfill ملف workers الكامل.
- [ ] اكتب timestamp ISO صحيحًا دائمًا، وسجل unavailable/failed بسبب محدد.
- [ ] اجعل backfill قابلًا للاستئناف ويطبع counts فقط، ووثق أمر dry-run وأمر التنفيذ.
- [ ] اختبر gzip فاسد، checksum خاطئ، path traversal، كتابة متزامنة، صفحة فارغة، OCR، وإصدار قديم بلا أصل.

**البوابة G3:** كل fixture منشور يعيد نفس عدد صفحات PDF ونفس ترتيبها بعد جلسة جديدة وbackfill، ولا يمكن قراءة artifact خارج root.

### المرحلة 4 — pipeline مشترك للنماذج

**الهدف:** كل أداة تغطي المستند كاملًا ضمن حدود المزود.

**الملفات الأساسية:** وحدة جديدة مثل `backend/tooling/pipeline.py` و`backend/tooling/common.py`.

- [ ] استخدم token counter مناسبًا للنموذج مع headroom ثابت للـprompt والإخراج؛ لا تستخدم عدد الحروف كحد وحيد.
- [ ] قسّم وفق الصفحات والعناوين، مع overlap صغير فقط عند الحاجة وpage refs لكل جزء.
- [ ] طبق map/reduce متعدد المستويات حتى لا يتجاوز reduce النهائي الميزانية مهما كان عدد الصفحات.
- [ ] احفظ checkpoint لكل جزء: input hash، status، attempts، output، page refs.
- [ ] retry/backoff للجزء الفاشل فقط ضمن حد واضح، ثم repair واحد للإخراج البنيوي.
- [ ] افصل system instructions عن document/web content بعلامات وبنية ثابتة، واختبر prompt injection.
- [ ] سجل provider latency/calls/retries والتغطية دون prompts أو نصوص.
- [ ] ضع budget أقصى للمكالمات والمقاطع، وأعد خطأ مفهومًا قبل التنفيذ إذا استحال الطلب ضمن السياسة.

**البوابة G4:** fixture من 50+ صفحة يمر في كل pipeline من دون طلب يتجاوز الميزانية، ويمكن استكماله بعد فشل جزء واحد.

### المرحلة 5 — إكمال صحة الأدوات الخمس المعتمدة على المستند

#### 5.1 الملخص

- [ ] مرر `summary_type`, `length`, و`include_bullets` إلى prompt/schema واجعل أثر كل خيار مثبتًا باختبار.
- [ ] اربط كل فكرة أو نقطة بـpage refs اختارها map stage، ولا تولد citations من أول الصفحات بصورة آلية.
- [ ] طبق أهداف الطول مع سماح موثق للمستند الأقصر، ثم تحقق بعد التوليد.
- [ ] احسب coverage من الصفحات المعالجة فعليًا ونسبة الضغط بالكلمات.

#### 5.2 الكيانات

- [ ] أبق spaCy singleton، وأضف health/warmup للعامل.
- [ ] طبق entity type filter فعليًا.
- [ ] طبّع العربية والإنجليزية، deduplicate، واجمع count/pages/confidence بقواعد حتمية.
- [ ] عالج LLM/research sections بالمقاطع وschema، مع دمج حتمي ومراجع صفحات.
- [ ] نفذ fallback معلنًا ومختبرًا أو احذف الوعد من الواجهة.
- [ ] أنشئ fixture عربية موسومة وbaseline Precision/Recall/F1؛ وثق الحد المقبول.

#### 5.3 الترجمة

- [ ] نفذ full/page/range على أرقام الصفحات الأصلية.
- [ ] اكتشف لغة المصدر وأرجع code وثقة أو `unknown`.
- [ ] أنشئ glossary للمصطلحات قبل ترجمة المقاطع واستخدمه في كل جزء.
- [ ] طبق `keep_formatting` للعناوين والقوائم والجداول البسيطة، أو احذف الخيار إذا لم يتحقق.
- [ ] استأنف من checkpoint ولا تعيد الأجزاء الناجحة.
- [ ] تحقق أن جميع الصفحات المطلوبة ممثلة في result والتنزيل.

#### 5.4 التحليل والمقارنة

- [ ] طبق normalization عربي: إزالة التشكيل والتطويل، توحيد الألف والياء/الألف المقصورة وفق سياسة موثقة، punctuation، وstopwords مختبرة.
- [ ] حسّن sentence segmentation للنص العربي/الإنجليزي المختلط.
- [ ] نفذ topics map/reduce مع coverage وpage refs.
- [ ] استبدل placeholder المقارنة بخوارزمية فعلية تعيد shared topics وdifferences لكل مستند مع أدلة صفحات.
- [ ] ارفض مقارنة الإصدار بنفسه.

#### 5.5 الخريطة الذهنية

- [ ] ولد central topic/nodes/edges عبر pipeline كامل المستند.
- [ ] تحقق من عدد العقد ضمن tolerance معلن لـ`target_nodes`.
- [ ] تحقق من IDs الفريدة، parent IDs، edges، connectivity، وعدم cycles غير المقصودة.
- [ ] repair مرة واحدة ثم `invalid_model_output` بدل `internal_error`.
- [ ] احتفظ بـpage refs لكل عقدة مشتقة من المستند.

**البوابة G5:** كل أداة تنجح على fixtures القصير وOCR والمختلط والطويل، وتفشل برسالة صحيحة على الفارغ/التالف، وكل خيار له test يثبت أثره.

### المرحلة 6 — البحث الأكاديمي وتحليل نتائجه

**الملفات الأساسية:** `web_search.py`, `backend/tooling/web_search.py`, إعداد SearXNG/proxy.

- [ ] استخدم `requests.Session` مع timeouts منفصلة وretry/backoff محدود للاتصال و5xx فقط.
- [ ] نفذ circuit breaker بحالات closed/open/half-open وTTL 15 ثانية مع اختبار توقف وعودة SearXNG.
- [ ] اكتشف المحركات المتاحة، ثم طبق allowlist حسب general/news/academic/wikipedia؛ لا تسقط إلى تصنيف آخر بصمت.
- [ ] طبّع DOI وURL canonical والعنوان قبل deduplication.
- [ ] طبق ranking موثق يجمع صلة النتيجة ونوع المصدر والتاريخ مع بقاء score الخام.
- [ ] أضف pagination/cursor أو احذف أي وعد pagination من الواجهة والعقد.
- [ ] اجعل `web_analysis` يقتبس فقط source indices موجودة، ويقيد عدد المصادر وطول كل مصدر وإجمالي tokens.
- [ ] اختبر نتائج تحاول تغيير تعليمات النظام أو حقن روابط/HTML.
- [ ] اضبط trusted proxy و`X-Forwarded-For`/`X-Real-IP` في بيئة النشر، وأزل خطأ SearXNG الحالي.

**البوابة G6:** التصنيفات الأربعة تعيد `engines_used` صحيحة أو خطأ صريحًا، no-results حالة مستقلة، والتحليل لا يستشهد بمصدر غير موجود.

### المرحلة 7 — واجهة Streamlit النهائية

**الملفات الأساسية:** `platform_tools_ui.py`, `platform_client.py`, `app_optimized.py`, `style.css`.

- [ ] أضف Tool Job controller مشتركًا لكل تبويب: submit، active، polling، terminal، cancel، retry، restore، clear/new run.
- [ ] عند بدء جلسة أو refresh، اقرأ `/jobs` واستعد أحدث Job لكل tool من payload/result metadata، ثم أوقف polling عند terminal.
- [ ] امنع زر الإرسال أثناء Job نشط للأداة نفسها، مع نص queue/running واضح.
- [ ] اعرض phase عربية مترجمة و`error_code` المحدد وزر إعادة المحاولة بـrequest ID جديد.
- [ ] افصل تنزيل binary/text عن `_request().json()`، واستخدم endpoint الخادم مع filename وmime الصحيحين.
- [ ] الملخص: بطاقات النص والنقاط والمقاييس والمراجع، ولا تنزيل قبل النتيجة.
- [ ] الكيانات: فلاتر الأنواع، تسميات عربية، count/confidence/pages، empty state صادق.
- [ ] الترجمة: source، اللغة، الأسلوب، full/page/range، keep formatting، تقدير الصفحات، progress، وتنزيل TXT/Markdown.
- [ ] التحليل: metrics وfrequencies وtopics والمقارنة في مكونات مفهومة بدل JSON الخام.
- [ ] الخريطة: renderer محلي واحد أساسي موثوق مع fallback نصي، ثم renderer إضافي فقط إذا كان له test؛ لا CDN.
- [ ] البحث: cards، المحرك، التاريخ/DOI، no-results، pagination إن نُفذت، وزر تحليل النتائج كـJob مستقل.
- [ ] اعزل legacy tools في function/module خاص بوضع local؛ أزل التكرار و`st.stop()` الحدّي بعد اختبار أن dashboard/cookie/footer تعمل مرة واحدة.
- [ ] اختبر RTL/LTR والهواتف 390 و375 واللوحي 768 والديسكتوب 1440، مع keyboard focus وloading/disabled states.

**البوابة G7:** Browser E2E لكل تبويب ينجح بعد refresh وفي جلسة جديدة، ولا يوجد JSON خام كواجهة نهائية أو زر يعمل مرتين أو تنزيل فارغ.

### المرحلة 8 — السعة والمراقبة والنشر الذري

- [ ] أضف metrics حسب tool: queue wait، execution time، completion/failure/cancel، retries، provider calls، token estimate، artifact/result errors.
- [ ] أضف correlation IDs: workspace hash آمن، job ID، tool، attempt؛ من دون token أو document text.
- [ ] امنع starvation: افصل أو أعط أولوية لمسارات deterministic/search عن LLM الطويلة، مع بقاء LLM gate مركزيًا.
- [ ] اختبر وأثبت قيم queue/concurrency على موارد السيرفر المستهدف؛ لا تثبت رقمًا اعتمادًا على جهاز التطوير فقط.
- [ ] ابنِ image واحدة immutable tag/digest وشغل API وStreamlit والworkers منها في النشر نفسه.
- [ ] أضف readiness يثبت اتصال كل worker بالـqueue المطلوبة، ومساحة القرص للartifacts، وقابلية قراءة قاعدة البيانات وRedis.
- [ ] أضف تنبيهًا لـstuck jobs، oldest queue age، provider 429/timeout، disk usage، worker restarts، وfailure rate.
- [ ] وثق backup/restore لـPostgres و`data/document_artifacts` و`data/tool_results` مع اختبار استعادة.
- [ ] حدّث `.env.example` وREADME لأوامر migrations/backfill/tests/load/rollback والتشغيل الإنتاجي.

**البوابة G8:** كل الخدمات تعمل من digest واحد، dashboard التشغيل يكشف العطل المتعمد، وbackup restore يعيد artifact ونتيجة قابلة للتحقق.

### المرحلة 9 — اختبار القبول النهائي

#### سيناريو عشرة مستخدمين المختلط

شغّل السيناريو مرتين متتاليتين من بيئة نظيفة:

| المستخدمون | العمل المتزامن |
|---:|---|
| 2 | رفع وفهرسة ملفين مختلفين |
| 2 | محادثة RAG مع مستند محدد |
| 1 | ملخص detailed لمستند 50+ صفحة |
| 1 | ترجمة range ثم refresh واستعادة |
| 1 | كيانات LLM أو research sections |
| 1 | تحليل ومقارنة مستندين |
| 1 | خريطة ذهنية |
| 1 | بحث أكاديمي ثم web analysis |

تحقق في الجولتين من:

- [ ] لا 5xx غير محقون عمدًا، ولا Job عالق، ولا نتيجة فارغة ناجحة.
- [ ] المحادثة والواجهة تبقيان responsive أثناء المهام الطويلة.
- [ ] الأرشيف الجديد يظهر للجميع، بينما كل conversation/job/result خاص بصاحبه.
- [ ] refresh لثلاث جلسات يستعيد الوظائف والنتائج.
- [ ] إلغاء وظيفة عاملة ينتهي `cancelled`.
- [ ] قتل tool-worker وإعادته يؤدي إلى استكمال/إعادة محدودة ثم terminal state.
- [ ] 429 وtimeout وinvalid model JSON تنتج الأكواد الصحيحة ولا تسقط التطبيق.
- [ ] توقف SearXNG وعودته يفتح ويغلق circuit كما هو متوقع.
- [ ] RSS لكل حاوية يبقى تحت limit ولا يوجد نمو مستمر بعد الجولة الثانية.
- [ ] تسجل p50/p95 للqueue wait والتنفيذ لكل أداة وعدد provider calls/retries.

#### Regression نهائي

- [ ] رفع تلقائي → فهرسة → جاهز للمحادثة.
- [ ] تحديد مستند وعزل مصادر RAG.
- [ ] الأرشيف العام من متصفحات جديدة.
- [ ] المحادثة النصية والصوتية إن كانت مفعلة.
- [ ] التنزيلات JSON/TXT/Markdown/الخريطة غير فارغة وتطابق النتيجة المحفوظة.
- [ ] لا page errors أو console errors على 1440/768/390/375.
- [ ] `docker compose config --quiet`, compile, full tests, و`git diff --check` ناجحة.
- [ ] logs خالية من Traceback/ERROR غير متوقع وأسرار أو محتوى خام.

**البوابة G9:** كل البنود تنجح مرتين متتاليتين؛ أي فشل يعيد التنفيذ إلى المرحلة المالكة للعيب ثم يعيد G9 كاملًا.

## 4. ترتيب commits المقترح

1. `test: add document tools fixtures and baseline harness`
2. `fix: make tool jobs cancellable and recoverable`
3. `feat: enforce typed tool request and result contracts`
4. `fix: preserve original PDF page identity in artifacts`
5. `feat: add resumable page-aware model pipeline`
6. `fix: complete summary entities translation analysis and mindmap`
7. `fix: harden academic search and web analysis`
8. `feat: restore and render durable tool jobs in Streamlit`
9. `ops: add tool metrics atomic deployment and recovery docs`
10. `test: prove mixed ten-user acceptance and regressions`

كل commit يجب أن يجتاز اختبارات طبقته، ولا يخلط refactor بصريًا واسعًا مع إصلاحات worker أو العقود.

## 5. التقرير النهائي المطلوب

أنشئ `AI-DOCUMENT-TOOLS-IMPLEMENTATION-021.md` فقط بعد G9، ويحتوي:

- commit hashes والملفات المعدلة.
- جدول كل ID من 016 وحالته `CLOSED` ودليل الاختبار.
- نتائج G0–G9 والأوامر وexit codes.
- fixtures وأحجامها من دون محتوى حساس.
- نتائج جولتي العشرة مستخدمين: p50/p95، queue wait، provider calls، retries، CPU/RSS، والحالات النهائية.
- اختبارات العزل وrefresh/cancel/worker kill/SearXNG/provider faults.
- لقطات desktop/mobile للتبويبات الست.
- أي limitation حقيقية متبقية؛ لا تستخدم `READY` إذا بقي P0/P1 أو اختبار مطلوب غير منفذ.

## 6. أمر التنفيذ الجاهز للنموذج التالي

> نفذ `AI-DOCUMENT-TOOLS-CLOSURE-PLAN-020.md` بالترتيب من المرحلة 0 إلى 9. لا تتجاوز بوابة مرحلة فاشلة، ولا تغيّر ثوابت النطاق. نفذ الكود والاختبارات والتشغيل الحي، وحدّث checkboxes بعد وجود دليل فقط. عند اكتمال G9 مرتين أنشئ `AI-DOCUMENT-TOOLS-IMPLEMENTATION-021.md` واربط كل عيب من التقرير 016 بدليل إغلاق. لا تعلن الجاهزية قبل تحقق Definition of Closure كاملًا.
