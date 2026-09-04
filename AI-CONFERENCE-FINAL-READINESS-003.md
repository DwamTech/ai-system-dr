# AI-CONFERENCE-FINAL-READINESS-003

**النطاق:** تدقيق ما قبل التنفيذ فقط في `F:\docker\files` بتاريخ 2026-09-04. لم يُشغّل Docker أو OpenSearch أو Ollama، ولم تقرأ قيم `.env`، ولم يُعدّل كود التطبيق أو بياناته. هذا تقرير minimum-change يحافظ على Streamlit، OpenSearch، Redis، PDF/OCR، نموذج embeddings الحالي، وكل الميزات والتبويبات السبعة.

## القرار التنفيذي

يمكن إنجاز نسخة مؤتمر محلية محسنة الليلة **من دون إعادة كتابة**، بشرط تنفيذ تغييرات مركزة في provider boundary وRAG selected-file filter ومعالجة أخطاء/واجهة. توجد ثلاثة عيوب وظيفية مؤكدة يجب أن تكون ضمن تمريرة التنفيذ: (1) لا توجد عزلة مستند في chat رغم المتطلب، (2) cache لا يتضمن المستند أو محتوى history، (3) التحليل المتقدم يقبل أي نص من المزود—including refusal—as success ويتيح تنزيله.

---

## 1. العزلة على ملف محدد: الدليل الكامل

### ما الموجود الآن

| السؤال | الدليل والنتيجة |
|---|---|
| ما قيمة الملف المختار؟ | لا توجد قيمة `selected_document` أو `active_document` لمسار chat. أسماء الملفات المفهرسة موجودة في `st.session_state.indexed_files`، والنصوص الحديثة في `last_full_text` (`app_optimized.py:134-147,158-187`). |
| أين يتم الاختيار فعلاً؟ | `selected_analysis_file` خاص بالتحليل المتقدم فقط (`app_optimized.py:1082-1086`)، و`selected_file` في summary/NER، وselectors منفصلة للترجمة/التحليل/الخريطة. لا واحدة منها تستدعي chat. |
| ما الذي يصل إلى RAG chat؟ | `prompt` و`chat_history` فقط: `query_with_cache(prompt, chat_history=chat_history)` في `app_optimized.py:1016-1018`. |
| هل يصل اسم ملف إلى engine/retriever؟ | لا. signatures هي `query_with_cache(query, chat_history=None)` و`_execute_query(query, chat_history=None)` و`get_optimized_chain()` في `engine_optimized.py:268,300,361`. |
| هل OpenSearch مفلتر؟ | لا. ينشأ retriever بـ `as_retriever(search_kwargs={"k": 7})` فقط (`engine_optimized.py:362`) ويستدعى في chain (`:420`) ومرة ثانية للمصادر (`:313`). لا يوجد filter/boolean_filter/pre_filter/document id. |
| هل الاختيار الحالي يوهم المستخدم بعزل chat؟ | **نعم.** يمكن للمستخدم اختيار ملف للتحليل المتقدم والملخص وغيرها، لكن سؤال chat في tab 1 يبحث عالمياً في جميع chunks في index. |
| ما metadata المتاح؟ | processor يضع `metadata["source"] = uploaded_file.name` لكل PDF (`processor_optimized.py:55-61,66-78`). ويثبت engine أن الحقل مفهرس/usable كـ`metadata.source.keyword` عند قائمة الملفات واسترجاع النص (`engine_optimized.py:465-492`). |
| هل يوجد `document_id`؟ | لا. لا ينشأ document ID في processor أو app. قد يولد LangChain/OpenSearch IDs داخلية للـchunks، لكنها ليست هوية document يتعامل معها التطبيق ولا تصل UI. |

### أقل إصلاح آمن الليلة

1. أضف state واحداً `active_document` في `app_optimized.py`، مع selector واحد ظاهر في رحلة العمل: بعد الفهرسة/الأرشيف وقبل chat. مصدر الخيارات هو نفس القائمة الحالية `get_indexed_files()`، مع خيار واضح **«كل المستندات»** حتى لا تزال القدرة الحالية للبحث الكلي مخفية أو محذوفة.
2. مرر `active_document` صراحة من `app_optimized.py:1018` إلى `query_with_cache` ثم `_execute_query` و`get_optimized_chain` في `engine_optimized.py`.
3. طبق فلتر OpenSearch على **exact term** `metadata.source.keyword: active_document` في كل retrieval. لا تغيّر embeddings أو index أو تعِد الفهرسة؛ هذا الحقل موجود بالفعل في البيانات الحالية.
4. اجعل `active_document` جزءاً من مفتاح cache (وانظر القسم 5)، واعرض اسم الملف النشط فوق chat وفي المصادر.
5. اختبر أن كل chunk مسترجع يحمل `metadata.source == active_document` قبل إرسال السياق إلى LLM. في حال لا توجد chunks، اعرض حالة «لم تُفهرس وثيقة صالحة/لا توجد نتائج لهذه الوثيقة»، لا fallback عالمي صامت.

**ملاحظة توافق مهمة:** filename آمن كحل توافق فوري لأنه metadata الوحيد المثبت في corpus الحالي ويستعمله code حالياً. لكنه ليس هوية طويلة الأجل: قد يتكرر الاسم في رفعين مختلفين، ولا يوجد sanitization قبل حفظه metadata. لا تضف أو تستبدل mapping/ID الآن؛ يجب أن يبقى نطاق الليلة filter exact على `metadata.source.keyword` مع تنبيه داخلي لاحتمال collision. آلية filter الدقيقة (`boolean_filter` مع approximate k-NN في إصدار LangChain/OpenSearch الحالي) يجب اختبارها على index الحالي قبل اعتمادها؛ لا تستخدم filtering Python بعد global top-k لأنه لا يضمن سبع نتائج من الملف المختار.

---

## 2. Web Search: السلوك الحالي مقابل المطلوب

### ما يثبته المصدر

- `WebSearchEngine.search()` يرسل طلب SearXNG JSON إلى `/search` (`web_search.py:45-148`). عند الفئة الأكاديمية يحاول تحديد engines: `google scholar,arxiv,semantic scholar,pubmed` (`:81-84`). إذن **Google Scholar مطلوب في الطلب البرمجي**.
- لا يوجد مجلد `searxng/` في workspace رغم أن Compose يركب `./searxng:/etc/searxng:rw`. لا يوجد `settings.yml` يثبت أن SearXNG image فعّل محرك Google Scholar أو أن اسم المحرك مطابق لتثبيت الصورة. لذلك لا يمكن إثبات أنه يعمل فعلياً؛ بل configuration المحلية الناقصة blocker محتمل.
- UI tab 7 يأخذ `web_query` من `st.text_input` ويستدعي `web_search_engine.search(web_query, category=web_category, ...)` فقط (`app_optimized.py:2173-2195`). لا يوجد selector للـPDF، ولا filename/title integration، ولا استدعاء `get_scholar_link_cached` في هذا التبويب.
- روابط Google Scholar بجانب المصادر في chat والأرشيف هي links فقط مبنية من filename (`utils.py:37-81`, `app_optimized.py:645,1038-1044`)؛ ليست نتيجة بحث ولا تدخل إلى RAG.
- بحث الويب مستقل تماماً عن normal document RAG. لا تخزن نتائجه في OpenSearch، ولا تضيفها إلى index، ولا يقرأ normal chat `web_search_engine`. زر «تحليل نتائج الويب بالذكاء» يلخص أول خمس snippets في عملية مستقلة (`app_optimized.py:2226-2235`) ولا يمررها إلى chat/index.

### النتيجة والحد الأدنى المطلوب

1. أبقِ tab 7 والبحث اليدوي والفئات كما هي.
2. أضف action اختياري واضح: **«ابحث عن الورقة/الملف النشط أكاديمياً»** يستخدم `active_document` بعد إزالة `.pdf`؛ لا تجعل web content يختلط في RAG chat.
3. أظهر engine الفعلي في كل نتيجة (موجود)، وحالة واضحة عند عدم عودة Google Scholar/عند عدم عمل SearXNG؛ لا تدّعِ أن Scholar عمل ما لم يرجع response `engine` المناسب.
4. وفّر/تحقق من SearXNG `settings.yml` فقط إذا كان مطلوباً لتشغيل الحاوية؛ لا تغيّر محرك RAG أو index.

**المكسور/غير المثبت حالياً:** folder config SearXNG غائب؛ healthcheck قد ينجح أو يفشل حسب defaults image/volume، لكن Google Scholar غير مثبت runtime. كذلك `is_available` يخزن أول فشل في `_available=False` طوال عمر instance، فيبقى unavailable بعد أن تبدأ الخدمة حتى rerun جديد. messages الخام من exceptions قد تعرض للمستخدم (`web_search.py:141-148`).

---

## 3. خلل التحليل المتقدم/اللغوي

### trace للسيناريو المبلغ عنه

1. في tab 1، selector `advanced_analysis_file_tab1` يعطي `selected_analysis_file` (`app_optimized.py:1075-1086`).
2. `get_file_content_safe()` يجلب النص من session أو OpenSearch (`:175-187`). لذلك رقم 3263 كلمة/20733 حرفاً منطقي ومقاس عبر `len(txt.split())` و`len(txt)` (`:1117-1142`).
3. Arabic detection هي نسبة Unicode Arabic characters إلى `isalpha`; threshold 0.3 (`:1122-1125`). instruction اللغة باللغة الإنجليزية صراحة، وتطلب Arabic only حين الاختيار/auto Arabic (`:1127-1139`).
4. deep linguistic prompt يبنى في `app_optimized.py:1198-1229`، ويطلب جداول morphology/grammar/semantics/statistics واقتباسات. analysis prompts الأخرى تبنى في `:1148-1321`.
5. `analyze_text_in_chunks()` يقسم عند أكثر من 4500 كلمة؛ المستند المبلغ 3263 كلمة يذهب في **استدعاء واحد** `rag_engine.llm.invoke(prompt)` (`:399-416`)، لا map-reduce. إعداد Ollama العام في engine هو `num_ctx=8192`, `num_predict=4096`, `temperature=.1`, `top_k=10`, `top_p=.95`, `keep_alive=10m` (`engine_optimized.py:132-142`).
6. أي string يعيده LLM—including `Sorry, but I can't provide...`—يعرض كـHTML (`app_optimized.py:1337`) ثم ينزل فوراً عبر `create_fancy_download_button_optimized` (`:1339-1343`). لا فحص empty/refusal/language/length/format. exceptions وحدها فقط تعرض error مع traceback كامل (`:1345-1348`).

### مشاكل مستقلة عن Ollama

- لا contract/validation لمخرجات أي provider.
- prompt طويل ومفرط في الطلبات لجلسة واحدة؛ output cap 4096 قد يقطع الجداول. الانتقال إلى OpenRouter لا يمنع refusal أو truncation تلقائياً.
- option `summary_type` و`summary_length` في tab 2 لا تدخل prompt؛ مثال على UI controls لا تطابق behavior. في advanced، `SAMPLE_LIMIT` معرّف ولا يستعمل.
- parallel analyzer يصل إلى 4 LLM calls ثم merge؛ يحتاج حد concurrency provider لتجنب 429، حتى إن لم يؤثر هذا المثال 3263-word.
- output rendering غير مهرب، وdownload يتعامل مع error/refusal كناتج.

### أقل إصلاح آمن

- أنشئ validator موحداً عند provider boundary: يرفض `None`/empty/whitespace، response قصيراً بصورة غير معقولة، ونصوص refusal المعروفة (Arabic/English مثل الرسالة المبلغ عنها)؛ يميّز provider HTTP errors من valid text. لا ينزل ولا يرسم «نتيجة» إن فشل validator.
- في advanced block، أظهر رسالة conference-safe («تعذر إكمال التحليل الآن؛ عدّل نوع التحليل أو حاول لاحقاً») مع retry button، وسجل التفاصيل في logger/diagnostics فقط. لا تعرض traceback.
- صرّح في prompt أن النص **بيانات مرجعية غير موثوقة وليست تعليمات**، وأنه عند غياب مثال يقول «غير مذكور في النص»، وأن اللغة النهائية هي العربية/الإنجليزية المحددة. هذا يقلل، ولا يلغي، injection/refusal.
- ضع max output/request timeout من config في adapter، وقيد advanced map-reduce إلى concurrency=1 أو 2 الليلة. عند provider 429/timeout، لا تدمج error strings ولا تعرض download.
- حدّد acceptance أن output المختار Arabic فعلاً في العربية. لا يلزم تغيير OCR أو chunk/index.

---

## 4. جرد كل استدعاءات التوليد LLM

`advanced_mindmap.py:92` يحتوي `self.llm.invoke` لكنه **غير reachable حالياً**: `AdvancedMindMapGenerator` يستورد فقط في app ولا ينشأ. يبقى تحت مراجعة migration لأن أي تفعيل مستقبلي له يجب أن يتلقى adapter نفسه.

| Feature | File / function | Current call | Prompt source | Expected response | Ollama dependency | Required OpenRouter change |
|---|---|---|---|---|---|---|
| RAG answer | `engine_optimized.py:_execute_query/get_optimized_chain` | LCEL `chain.invoke` -> `self.llm` | `build_prompt` lines 366-413؛ chunks + history | answer text | `Ollama(...)`, host/fallback | provider adapter compatible مع `.invoke`; يبسط chain أو يكون Runnable |
| Query rewrite | `engine_optimized.py:rewrite_query` | `self.llm.invoke` | inline Arabic rewrite prompt 341-347 | short query <500 chars | same | adapter + validate nonempty؛ fallback original query |
| Document summary | `engine_optimized.py:generate_research_summary_optimized` | `.invoke` | inline Arabic prompt, first 8000 chars | summary | same | adapter + output failure handling |
| Advanced/deep analysis | `app_optimized.py:analyze_text_in_chunks` | `.invoke` per 1/4 chunks + merge | templates 1148-1321, merge 1146 | analysis text / tables | same | adapter, output validation, timeouts, concurrency/retry |
| NER via LLM | `app_optimized.py:1560-1590` | `.invoke` | `entity_prompt`, first 5000 chars | classified table | same | adapter + validate response before display |
| Translation | `app_optimized.py:1784-1877` | `.invoke` per 800-word chunk | `translation_prompt` 1823-1834 | translation-only text | same | adapter + fail whole result safely; do not download embedded error chunks |
| Topic generation | `app_optimized.py:1938-1965` | `.invoke` | `topic_prompt`, smart 2000 words | topic analysis | same | adapter + validate |
| Mind map (used) | `app_optimized.py:create_mindmap_from_text` | `.invoke` | inline Arabic Markdown hierarchy, first 6000 chars | hierarchy Markdown | same | adapter + validate expected `#` structure / safe fallback |
| Mind map (unused class) | `advanced_mindmap.py:generate_mindmap` | `.invoke` per <=7000-char chunk | `IntelligentPromptsLibrary` | JSON mind-map | generic injected `llm`, but current provider would be Ollama | ensure any instantiation gets same adapter |
| Web result summary | `app_optimized.py:2226-2235` | `.invoke` | inline Arabic prompt, first 4000 chars of web snippets | web-only summary | same | adapter + labeled external-data output |
| Analysis helper direct | `app_optimized.py:416,431,454` | `.invoke` | advanced templates / merge | same as advanced | same | covered by common adapter |

spaCy NER and rule-based research-section extraction do **not** call an LLM and must remain unchanged.

---

## 5. OpenRouter minimum-change integration

### مقارنة الخيارات المتاحة الليلة

| الخيار | الملاءمة لهذا repository | الأثر | القرار |
|---|---|---|---|
| A. `langchain-openai` / `ChatOpenAI` على OpenRouter OpenAI-compatible base URL | ممكن، لكن requirements مثبتة حد أدنى قديم (`langchain>=0.1.12`, `langchain-community>=0.0.28`) ولا يوجد `langchain-openai`/`openai` حالياً. Chat model يعيد AIMessage بينما أغلب app يتوقع `str`; LCEL compatibility تحتاج تعديل/اختبار دقيق. | dependencies/version risk الليلة | ليس الخيار الأكثر أماناً |
| B. `requests` OpenRouter client صغير خلف `invoke(prompt)->str` | `requests>=2.31.0` موجود بالفعل؛ 9 من call sites تستخدم `.invoke` النصي. يحتاج adapter واحد وخفض اعتماد RAG chain على pipe أو جعله يدعو adapter بعد retrieval. | ملف/provider boundary واحد + تعديلات engine مركزة | **موصى به** |
| C. SDK/package OpenRouter أو `ChatOpenRouter` | حديث ويتطلب dependency/compatibility validation؛ dedicated LangChain package موصوف كـbeta وغير backward-compatible مع LangChain القديم. | أعلى risk/version churn | لا تستخدمه الليلة |

OpenRouter يوفّر endpoint OpenAI-compatible `/api/v1/chat/completions` مع Bearer API key، وتعود الرسالة في `choices[0].message.content`; docs تسجل أخطاء 400/401/402/403/404/408/413/422/429/5xx. [Quickstart الرسمي](https://openrouter.ai/docs/quickstart)، [مرجع chat completion](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request?explorer=true). النموذج المقترح **`qwen/qwen3-30b-a3b-instruct-2507` موجود حالياً** في catalog، text-to-text، context 262144، وحد provider المعروض 128000/max completion 32000؛ لا تعتمد هذه الحدود في code، فاجعلها config/guardrail. [OpenRouter models API](https://openrouter.ai/api/v1/models).

### تصميم التغيير الأدنى

- أضف `openrouter_client.py` صغيراً (أو class في `engine_optimized.py` لتقليل الملفات) بواجهة `invoke(prompt: str) -> str`. يستخدم `requests.post`, `Authorization: Bearer $OPENROUTER_API_KEY`, JSON messages، model/config، ويفك `choices[0].message.content` فقط.
- استعمل `OPENROUTER_API_KEY` (مطلوب، لا يطبع)، `OPENROUTER_MODEL` (default candidate)، `OPENROUTER_TIMEOUT_SECONDS`، `OPENROUTER_MAX_TOKENS`، `OPENROUTER_TEMPERATURE`، والخيارين غير السريين `OPENROUTER_HTTP_REFERER`/`OPENROUTER_APP_TITLE`. تبقى `.env` غير tracked؛ لا hardcode key أو model في call sites.
- timeout connect/read محدد، مثلاً tuple requests؛ retry واحد أو اثنان فقط لأخطاء transient 408/429/5xx باستخدام `tenacity` الموجود، مع backoff قصير. لا retry 401/402/403/413/422. حوّل الخطأ إلى typed/provider exception؛ UI يترجمه إلى رسالة آمنة.
- model selector يمرر model إلى `OptimizedRAGEngine` ثم adapter، لا إلى URLs Ollama.
- أزل usage imports/dependency `ollama` فقط بعد التأكد أن لا file يستعمله؛ أبقِ embeddings/`sentence-transformers` وOpenSearch دون تغيير.

**حد chain:** الـRAG الحالي يصنع `RunnableLambda | self.llm | StrOutputParser`. adapter النصي الصغير ليس Runnable. أقل تغيير آمن هو تعديل `get_optimized_chain/_execute_query` ليجلب docs مرة واحدة ويبني prompt ثم `self.llm.invoke(prompt)` مباشرة، بدلاً من محاولة جعل HTTP wrapper يحاكي LangChain internals. هذا كذلك يصلح double retrieval (القسم 6). لا يعد هذا redesign للـRAG؛ يحافظ على prompt/retrieval/model interface.

### model selector

- حالياً sidebar `st.selectbox` في `app_optimized.py:471-476` يحتوي Ollama names `[qwen2:1.5b, phi3, llama3, llama3.1, mistral]`. القيمة تمرر إلى `OptimizedRAGEngine(model_name=model)` عند button activation (`:499-515`) ثم إلى `Ollama(model=self.model_name)` (`engine_optimized.py:116-143`). كل LLM feature تعتمد engine session نفسه.
- حافظ على feature: selector صغير curated من OpenRouter slugs، primary candidate أولاً، وoptional approved fallback واحد/اثنان فقط من config—not a free-text provider list. ضع selector في **«إعدادات الذكاء المتقدمة» collapsed expander**؛ headline يعرض النموذج النشط وprovider OpenRouter. لا تحذف model selection.

---

## 6. صحة cache وكفاءة retrieval

### cache

الدليل الحرفي: `cache_key = f"{query}_{history_len}"` ثم MD5 في `engine_optimized.py:268-272`. لا يتضمن `selected document` (غير موجود)، ولا محتوى/roles/history نفسه، ولا model/provider/index/version.

النتيجة: سؤال واحد مع history مختلف بطول واحد أو أي ملف مختلف يمكن أن يعيد cached response/sources من سياق آخر. هذا breach وظيفي وخصوصي.

**إصلاح صغير:** بعد إضافة `active_document`, استخدم canonical JSON/hash لـ`{query, active_document or "__all__", last N history messages(role/content), model_name, index_name}`. لا تخزن raw question/history في Redis key؛ hash فقط. امسح cache مرة واحدة عند release لأن key semantics تتغير. cache TTL/Redis يبقيان كما هما.

### retrieval مرتين

مؤكد: chain يستدعي `retriever.invoke(search_query)` في `engine_optimized.py:420` ثم `_execute_query` يستدعيه ثانية عند `:313` فقط لبناء source list. **إصلاح صغير:** retrieve مرة واحدة في `_execute_query`, ابن prompt من نفس `docs`, invoke LLM، واستخرج unique sources من نفس list. هذا مطلوب أيضاً لتطبيق selected-file filter مرة واحدة بشكل موثوق.

---

## 7. Upload behavior (دون تغيير limit)

| بند | الحقيقة من المصدر |
|---|---|
| per-file limit | `STREAMLIT_SERVER_MAX_UPLOAD_SIZE=8192` في Compose: 8192 MB لكل ملف بحسب Streamlit config |
| aggregate limit | لا يوجد |
| files | `accept_multiple_files=True`; لا حد لعدد الملفات (`app_optimized.py:662-667`) |
| parallelism | اختيار serial أو parallel؛ parallel حتى 4 ملفات (`:674-680`; `processor_optimized.py:138-154`) |
| validation | UI `type=["pdf"]` فقط. `utils.validate_pdf_file()` يفحص extension/signature/size لكنه **لا يستدعى** |
| failure UX | processor يرجع chunks فارغة ويعرض raw exception في `st.warning/st.error`; app ما زال يرسل `all_results` إلى ingest ثم يقول «تمت الفهرسة X ملف» (`app_optimized.py:733-786`)؛ لا per-file success/fail summary موثوق |

الحد الحالي large multi-file يبقى. التغيير الليلي فقط هو استدعاء validation الموجود قبل processing، وإظهار قائمة نجاح/فشل وإلغاء success العام عند إخفاق كل الملفات؛ لا تغيير OCR أو limit.

---

## 8. UI/UX: خطة مؤتمر كبيرة داخل Streamlit

### المبدأ

حافظ على tabs السبعة وكل الوظائف، لكن اجعل **رحلة العمل المرئية** ثابتة: **1 ارفع -> 2 فهرس -> 3 اختر الوثيقة -> 4 اختر الأداة -> 5 اسأل/حلل -> 6 راجع/نزّل**. لا تضف animation أو décor لا يخدم هذه الرحلة.

### الترتيب المقترح القابل للتنفيذ الليلة

| المنطقة | التغيير الدقيق |
|---|---|
| Header / identity | hero قصير وهادئ: الاسم، سطر «حلّل مستنداتك بأمان»، وstepper من 6 خطوات. أزل claims غير مثبتة مثل «70% أسرع». |
| Sidebar | اجعله sections: **المستندات** (رفع + active file)، **الذكاء** (model/advanced)، **النظام** (health/diagnostics)، **secondary** (archive/support). لا تضع file uploader وdestructive actions مختلطين. |
| Engine/settings | زر واحد واضح «اتصال OpenRouter وOpenSearch» مع state badge؛ model selector وchunk/batch/cache في expander. لا تعرض host/internal ports للمستخدم العام. |
| Uploaded files / active document | بطاقة لكل ملف: الاسم، status (جاهز/فشل/قيد المعالجة)، pages/chunks إن متاح. selector مركزي `active_document` مع «كل المستندات». استخدمه contextually في كل tab ولا تكرر selectors إلا حيث multiple-file comparison مطلوب. |
| Indexing/progress | group upload settings تحت uploader؛ progress حقيقي لكل ملف + final success/failure summary، بدون `st.balloons()` الذي لا يضيف clarity. |
| Tabs | احتفظ بالسبعة، لكن أسماء قصيرة متسقة وأيقونات ثابتة؛ tab 1 chat أولاً وadvanced analysis داخل expander/card ثانوي تحت chat بدلاً من منافسة البحث. |
| Chat | heading «اسأل عن: [active document]»، bubble آمن markdown، input كبير وbutton primary واحد، clear conversation secondary. اعرض spinner نصياً لا typewriter decorative. |
| Sources/results/downloads | source chips باسم ملف/page إن توفر؛ «تنزيل» secondary action بعد successful validated response فقط. كل analysis result card يوحد title/model/document/status. |
| states | Empty: يرشد للخطوة التالية. Loading: اسم العملية والملف. Success: ما تم فعلاً. Warning: action needed. Error: رسالة عربية بسيطة + retry، technical detail في diagnostics فقط. |
| RTL / typography | `dir=rtl` و`text-align:right` للمحتوى العربي دون `unicode-bidi:bidi-override` لأنه يفسد النص المخلوط/code. font stack محلي/system fallback، line-height ومسافات موحدة. |
| colors/buttons/forms | palette واحدة (navy/teal/neutral)، لون تحذير/error محجوز، primary واحد لكل section، secondary outline للتحميل/إعادة المحاولة؛ labels مرئية لا emojis فقط. |
| mobile/narrow | containers بعرض كامل، لا columns حرجة لـ chat/upload عند narrow، CSS media query لتكديس cards وأزرار؛ اختبر 375px و768px. |

### ما ينقل ولا يختفي

- **Advanced settings collapsed:** model, chunk size, overlap, batch, cache؛ لا تدفن active document.
- **Sidebar secondary/system:** health check، archive search، cache clear، support. **Database clear** يبقى feature لكن تحت confirmation expander شديد الوضوح، وليس بجوار upload.
- **Contextual controls:** summary/NER/translation/text analysis/mindmap تعرض إعداداتها داخل tab بعد اختيار active file؛ web search يبقى مستقل ويضاف له action الوثيقة الاختياري.

### `unsafe_allow_html` وrendering الآمن الليلة

يجب إبقاء HTML الثابت فقط: CSS في `local_css` (`app_optimized.py:90-121`)، hero ثابت (`:866-872`)، placeholders الثابتة، وHTML export المقصود للـmindmap بعد serialization.

يجب عدم تمرير untrusted strings إلى HTML wrapper:

- LLM: RAG `:1024`، advanced `:1337`، summary `:1406`، LLM NER `:1584`، translation `:1861`، topics `:1963`، web summary `:2235`، mindmap text `:2110`.
- PDF/user text والكيانات: spaCy badges/`highlighted_text` (`:1528-1545`)، وfilename يظهر داخل Markdown/HTML contexts.
- web result `title/content/url` يظهر عبر `st.write/st.markdown` (`:2200-2217`) ويحتاج safe display/link validation.

الحد الأدنى: استخدم `st.markdown(result)`/`st.write` للمخرجات النصية بدلاً من HTML wrapper، أو escape user/model content قبل إدخاله في div؛ للNER استعمل Streamlit native chips/tables أو escape `ent.text` وsource text قبل إضافة `<mark>`. لا تجعل filenames جزءاً من HTML غير مهرب.

### error experience: أعلى الإصلاحات قيمة

| مكان | الخطأ الحالي | message آمنة مطلوبة |
|---|---|---|
| provider/RAG | engine يحول exception إلى `حدث خطأ: {str(e)}` (`engine_optimized.py:287-292`) | «خدمة الذكاء غير متاحة مؤقتاً. حاول مرة أخرى.» |
| advanced | traceback للمستخدم (`app_optimized.py:1345-1348`) | «تعذر إكمال التحليل» + retry؛ diagnostics فقط للتفاصيل |
| PDF/OCR | raw exception مع filename (`processor_optimized.py:62-80,132-133`) | «تعذر معالجة هذا الملف» + per-file state |
| activation/OpenSearch | raw exception (`app_optimized.py:521-523`, `engine_optimized.py:224-227`) | «تعذر الاتصال بخدمة الفهرسة» |
| translation | يدمج `[خطأ ...]` مع output وينزله (`app_optimized.py:1852-1877`) | لا download حين فشل أي chunk؛ retry/partial state واضح |
| voice | service/traceback raw (`app_optimized.py:967-977`) | «تعذر تحويل الصوت إلى نص»؛ technical detail مخفي |
| SearXNG | raw `{str(e)}` داخل result (`web_search.py:141-148`) | «البحث الخارجي غير متاح مؤقتاً» |

---

## 9. مصفوفة المحافظة على الوظائف / acceptance

| Feature | Current location | Status from source | Dependency | Preserve | Migration/UI risk | Required regression test |
|---|---|---|---|---|---|---|
| Multi-PDF upload | sidebar `app_optimized.py:659-799` | موجود | Streamlit/PDF processor | نعم | Medium | 2+ PDFs accepted and reported |
| PDF extraction | `processor_optimized.py:55-64` | موجود | PyPDFLoader | نعم | Low | Arabic/English digital PDFs |
| OCR | `processor_optimized.py:66-128` | موجود | Poppler/Tesseract | نعم | Low | scanned Arabic PDF |
| Indexing | `engine_optimized.py:230-248` | موجود | MiniLM/OpenSearch | نعم | Medium | chunks count and retrievable |
| Active file isolation | غير موجود في chat | **defect** | OpenSearch metadata | نعم/يضاف | High functional priority | same question returns only selected source |
| RAG chat | tab1 `:981-1050` | موجود/global | provider/OS/Redis | نعم | High | Arabic+English answer, source/page |
| Summary | tab2 `:1355-1435` | موجود | LLM | نعم | Medium | selected PDF summary |
| Rule-based research sections | tab3 `:1456-1483` | موجود | `research_extractor` | نعم | Low | report generated |
| spaCy NER | tab3 `:1485-1557` | موجود if model | spaCy model | نعم | Low | entities / graceful unavailable |
| LLM NER | tab3 `:1560-1590` | موجود | LLM | نعم | Medium | valid table/error state |
| Translation | tab4 `:1595-1881` | موجود | LLM | نعم | Medium | Arabic<->English, no error download |
| Text stats/topics | tab5 `:1884-1967` | موجود | Python/LLM | نعم | Medium | stats + topic output |
| Advanced/deep analysis | tab1 `:1071-1352` | exists but defect | LLM | نعم | High | Arabic validated result; refusal handling |
| Mind map | tab6 `:1970-2160` | موجود | LLM/Plotly/CDN | نعم | Medium | map + exports |
| Web academic search | tab7 `:2162-2242` | exists; runtime config uncertain | SearXNG | نعم | Medium | manual + active-file query, no RAG mixing |
| Voice | tab1 `:894-977` | implemented, external | Google/ffmpeg | نعم | Medium | audio -> text / safe fail |
| Downloads | `utils.py`, all tabs | موجود | Streamlit | نعم | Medium | successful results only |
| Archive/history | sidebar/chat history | موجود | OpenSearch/session | نعم | Medium | indexed filenames/history retain behavior |
| Diagnostics | sidebar | موجود, Ollama-specific | services | نعم, provider-aware | Medium | OS/Redis/OpenRouter health |
| Redis cache | `redis_cache.py`, engine | موجود but incorrect key | Redis | نعم | High correctness | no cross-file/context cache hit |

---

## 10. Local run readiness after removing local generation

### Current startup blockers

- Dockerfile hardcodes `OLLAMA_URL` and starts Streamlit with CORS/XSRF disabled (`Dockerfile:56-76`).
- Compose makes `streamlit-app` depend on `ollama: condition: service_healthy` and declares `OLLAMA_URL`; it also defines `ollama` service and exposed port (`docker-compose.yml:18-76`). If Ollama service is simply omitted without changing these, Compose validation/startup will fail because dependency is undefined.
- `requirements.txt` includes `ollama>=0.1.7`; source import is `from langchain_community.llms import Ollama` (`engine_optimized.py:12`). Both must be removed/replaced in the same migration pass, otherwise app import fails.
- `searxng/` config directory is absent. Web Search must be verified before conference, not assumed.
- no `.streamlit/config.toml`; configuration is CLI/env/Compose only. `.env` exists but its values were not inspected.

### Safest local conference runtime target

Keep services **streamlit-app + opensearch + redis + searxng**; remove Ollama service, port, volume, health dependency, and env reference only after code imports no Ollama. Keep `opensearch_data` untouched and MiniLM embedding dependency/image build. Add OpenRouter variables via `.env`/Compose `environment` without printing them. Ngrok should be disabled/not started for local acceptance unless deliberately required for the conference QR; it is not needed to prove local functionality and expands exposure.

Do not modify `opensearch_data`, `ollama_data` archive, or existing corpus. Existing vectors remain compatible because embedding model/index are unchanged. Build/start exactly through the edited Compose profile/config once code migration is done; do not attempt today’s old README `docker-compose up --build` sequence until the Ollama dependency removal is included.

---

## 11. Short E2E smoke plan for tonight

1. Build/start the local non-Ollama Compose; Streamlit health endpoint and OpenSearch/Redis/SearXNG health visible.
2. Confirm OpenRouter valid key/model with one controlled Arabic and English `.invoke`; confirm missing/invalid key gets safe UI error.
3. Ingest one Arabic digital PDF; verify source name, chunks, and retrieval.
4. Ingest one English PDF and one scanned/OCR PDF; verify per-file status.
5. Upload multiple PDFs in both serial and parallel mode; verify no false global success when a file fails.
6. Select PDF A, ask a distinctive question, assert every returned source/chunk is A.
7. Select PDF B with same question; assert no cache reuse/answer/source from A. Repeat with different same-length histories.
8. Select «كل المستندات» and verify intentional global behavior remains available.
9. Test RAG answer, summary, spaCy NER, LLM NER, translation, topics, advanced/deep analysis, and mind map—Arabic and English where applicable.
10. For advanced analysis, simulate/refuse/empty/provider failure if possible; assert no result card/download and safe retry message.
11. Test web academic manual query and active-file title query; inspect returned `engine`; confirm web snippets never appear in normal RAG chat.
12. Download a successful answer/summary/translation/mindmap; verify failed output has no download.
13. Verify Redis second identical same-context request caches, but different document/history/model does not.
14. Test OpenSearch unavailable and OpenRouter 401/429/timeout paths; no traceback/key/internal URL in public UI.
15. Use browser responsive emulation at 375px and 768px; verify workflow controls, tabs, selector, and primary actions remain usable.

---

# A. VERIFIED BLOCKERS BEFORE IMPLEMENTATION

1. **Selected-PDF RAG is absent:** current chat is global and fails the confirmed user workflow.
2. **Cache key crosses contexts/documents:** exact key is question plus history length only.
3. **Ollama removal requires coordinated code + Compose changes:** otherwise imports and `depends_on` block startup.
4. **Advanced analysis accepts refusal/errors as successful downloadable output.**
5. **SearXNG configuration is missing from workspace; Google Scholar runtime behavior is unverified.**
6. **No usable Python interpreter exists on this host for non-Docker test execution.** Docker build/runtime validation remains necessary after the one pass.

# B. EXACT FILES TO CHANGE TONIGHT

| File | Why / intended changes | Risk |
|---|---|---|
| `engine_optimized.py` | replace Ollama construction with one OpenRouter `invoke` boundary; provider-safe errors; retrieve once; selected-file filter; cache key including document/history/model; provider-aware health | High—central logic; preserve embedding/index exactly |
| `app_optimized.py` | active document selector/state and pass to chat; curated OpenRouter selector; provider-safe states; output validation/display/download gating; error UX; conference UI hierarchy; web active-file query action | High—large UI file; regression checklist mandatory |
| `docker-compose.yml` | remove Ollama service/dependency/port/volume/env; add OpenRouter nonsecret config wiring; keep OpenSearch/Redis/SearXNG | Medium—Compose must still validate/start |
| `Dockerfile` | remove Ollama env/import assumptions; avoid insecure/dead settings where safely possible; preserve PDF/OCR packages and entrypoint | Medium—build risk |
| `requirements.txt` | remove unused Ollama package; no new dependency if `requests` adapter selected; preserve LangChain/community for OpenSearch | Low—verify build |
| `style.css` | cohesive Streamlit-safe visual system, RTL/mixed text, responsive media rules, consistent states; remove fragile bidi override behavior | Medium—visual regression only |
| `web_search.py` | safe errors, refreshable health availability, optional filename-title query helper if kept outside app | Low—web feature isolated |
| `processor_optimized.py` | call existing PDF validation from app or return structured per-file outcome; replace raw error presentation with safe messages | Medium—ingestion preservation |
| `README.md` | update local startup/env/model instructions after verification | Low—documentation only |
| `.env` | add key/config values locally only; never print/commit secret | Medium—secret handling |
| `searxng/settings.yml` (new only if needed) | make intended engines/config explicit for local web feature | Medium—validate against image before relying on Scholar |

# C. FILES THAT MUST NOT BE TOUCHED

- `opensearch_data` volume/archive and all node/index files: existing embeddings/corpus must remain intact.
- `ollama_data.tar.gz`: historical backup; not needed by conference runtime but do not delete/overwrite.
- embedding choice in `engine_optimized.py`: retain `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` exactly.
- `processor_optimized.py` OCR algorithm/DPI/process strategy: no OCR-quality scope expansion.
- PDF samples, user data, backup/restore scripts, and `DockerDesktopWSL` runtime data.
- Do not reindex, delete `knowledge_base_optimized_v2`, alter mapping, or introduce document IDs tonight.

# D. ONE-PASS IMPLEMENTATION ORDER

1. Snapshot/check current source and data paths; never touch volumes. Add config placeholders without exposing secrets.
2. Implement and unit-smoke the small OpenRouter adapter/error type; make `OptimizedRAGEngine.llm.invoke` the sole generation boundary.
3. Refactor engine query execution minimally: retrieve once, filter active file, build same prompt, invoke adapter; fix cache key.
4. Add active document state/selector and wire it only into chat/RAG; expose explicit all-documents option.
5. Wire all current LLM features through the common adapter; add output validation and no-download-on-failure.
6. Change Compose/Dockerfile/requirements in the same patch to remove Ollama startup/import dependency while preserving OS/Redis/SearXNG/PDF/OCR.
7. Apply UI/CSS hierarchy and safe rendering; retain all seven tabs and actions.
8. Harden WebSearch error/active filename action and add/validate SearXNG config if necessary.
9. Update README, build local image, then execute the E2E smoke plan in section 11. Fix only demonstrated regressions.

# E. ACCEPTANCE CHECKLIST

- [ ] Local Compose starts with no Ollama container or dependency.
- [ ] OpenRouter key/model are read only from environment and never shown in UI/log output.
- [ ] All LLM features in the inventory use OpenRouter successfully or fail safely.
- [ ] Arabic and English PDF ingestion work; OCR workflow remains available.
- [ ] Multiple files retain per-file success/failure status.
- [ ] A selected PDF is passed into retrieval and results are filtered to it.
- [ ] «كل المستندات» is explicit and intentional.
- [ ] Cache key includes selected document and actual relevant conversation content.
- [ ] RAG retrieves once per uncached request.
- [ ] Refusal/empty/provider error is not displayed or downloadable as a successful analysis.
- [ ] Summary, NER, translation, topics, deep analysis, mindmap, voice, downloads, archive, diagnostics, and all 7 tabs remain reachable.
- [ ] Web search remains separate from normal document RAG and file-name academic search is available.
- [ ] No untrusted LLM/PDF/web/filename string enters `unsafe_allow_html=True` unescaped.
- [ ] Public-facing errors are conference-safe; technical details stay in diagnostics/logs.
- [ ] Narrow-screen workflow is usable.

# F. ESTIMATED RISK

| Change | Risk | Why |
|---|---|---|
| OpenRouter migration | MEDIUM | adapter is small, but every generation feature and Compose dependency must migrate together |
| RAG selected-file isolation | HIGH | critical behavior and exact OpenSearch filter semantics must be proven on existing index |
| Analysis bug | MEDIUM | clear code fixes, but provider refusal/response validation needs real acceptance tests |
| UI redesign | MEDIUM | achievable CSS/Streamlit reorganization but `app_optimized.py` is a large monolith |
| Overall regression risk | HIGH | one-pass time constraint plus no local Python test runner; mitigate with the exact smoke checklist |
