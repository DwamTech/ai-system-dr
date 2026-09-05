# RAG-NUMERIC-ACCURACY-DIAGNOSTIC-008

**Date:** 2026-09-05  
**Scope:** Read-only diagnostic for `RAG_Test_Arabic_Document.pdf` and the reported Setting B answer. No provider request was made; no application code, prompt, index mapping, embeddings, or indexed data was changed. API-key values were neither read nor recorded.

## Verdict

**MULTIPLE_CAUSES**

The literal erroneous value `52.0037%` was not found in the original PDF, the application-extracted text, any inspected chunk, or the inspected OpenSearch records. It is present in the cached final answer returned through the provider client. Separately, the application's actual PDF extraction produced a conflicting malformed numeric token, `520037`, in the Setting B content. The evidence therefore establishes two contributing faults:

1. the ingestion extraction path corrupted part of the RTL/table-like numeric content; and
2. the generation result returned `52.0037%` from that ambiguous/corrupted context rather than the document-supported `88.7%`.

There is no evidence of a UI numeric transformation.

## Evidence boundary

The exact historical question, retrieval ranking, assembled prompt, and raw HTTP response body were not persistently logged by the application. Redis stores the cache identity only as an MD5 hash and stores the final `[answer, sources]` value; it does not retain the question, history, retrieved document IDs, prompt, or HTTP JSON. This report does not infer those unavailable artifacts.

The evidence below is therefore divided between direct observations and source-path facts. The application was not restarted and no new model request was sent.

## Stage-by-stage trace

| Stage | Direct observation for the reported numeric value | Result |
|---|---|---|
| Original PDF text, independent read | Two-page extraction contains `Recall: 88.7%`; it contains no `52.0037`. | The source document supports **88.7%**. |
| Actual application extraction (`PyPDFLoader` path) | Raw extracted text contains `88.7` and does **not** contain `52.0037`; it also contains the malformed token `520037` in the Setting B passage. | Extraction has a numeric corruption. |
| Application chunks before storage | Two produced chunks: the 1,898-character chunk contains `520037` but neither `88.7` nor `52.0037`; the 1,520-character chunk contains both `88.7` and `520037`, but not `52.0037`. | Chunking preserved the extraction output; it did not create `52.0037`. |
| OpenSearch records for the selected source | Six records exist, representing three duplicate two-chunk ingestion cycles. Every first-shape chunk (1,898 chars) has `520037`, no `88.7`, no `52.0037`; every second-shape chunk (1,520 chars) has `88.7` and `520037`, no `52.0037`. | Storage faithfully retained the extracted strings; it did not create `52.0037`. |
| Historical retrieved chunks for the exact question | Not persisted, so exact IDs/rank cannot be proven after the request. The selected-document filter restricts candidate documents to this source; `k=7` is requested, while the source currently has the six records listed below. | Exact historical retrieval is **unavailable**, not guessed. |
| Historical final prompt | Not persisted. Source code passes each retrieved `page_content` verbatim into the prompt formatter; it has no numeric conversion. | Exact prompt is **unavailable**; any `520037`/`88.7` in retrieved chunks would be copied unchanged. |
| Provider response | Raw HTTP JSON was not logged. A Redis cache value returned through the provider client contains the exact final answer text `Recall: 52.0037%`. The client reads `choices[0].message.content`, validates it, then only trims surrounding whitespace. | Strong evidence that the provider completion supplied `52.0037%`; byte-for-byte raw HTTP proof is unavailable because it was not logged. |
| Rendered chat answer | The chat UI sends the stored message directly to `st.markdown(msg["content"])`. No numeric formatter, regex replacement, bidi reordering code, or post-generation string transform was found. RTL CSS can affect visual direction but cannot change the underlying characters from `52.0037` to a different number. | The UI rendered the returned value; it did not create or alter it. |

### Targeted extraction evidence

The application extraction's Setting B section includes this minimal relevant excerpt (line breaks preserved as extracted):

```text
... تداخل 120 ... واسترجاع أعلى 5 مقاطع لكل سؤال. وصلت دقة الاسترجاع في هذا الإعداد إلى 091.4؟, بينما بلغ الاستدعاء
520037
```

The same application extraction also has a separate occurrence of `88.7`. Thus, the data supplied to indexing contains both the document-supported recall value and a malformed competing numeric token. The literal `52.0037` is absent before generation.

### OpenSearch records inspected

All six had `metadata.source.keyword = RAG_Test_Arabic_Document.pdf`; no unrelated document text was inspected or reported.

| OpenSearch document ID | Length | Contains `88.7` | Contains `520037` | Contains `52.0037` |
|---|---:|---:|---:|---:|
| `7d964888-b10b-4ddb-b85e-479ecf7d8e29` | 1,898 | No | Yes | No |
| `be71cfcc-dced-4ab6-9546-6dccc7e0d965` | 1,520 | Yes | Yes | No |
| `2bc14aa5-3a9f-46d2-9846-2db8dc413f8e` | 1,898 | No | Yes | No |
| `50e65426-8a8a-42f7-8406-b1266f0866b1` | 1,520 | Yes | Yes | No |
| `f4262b5a-82e3-4004-8646-172329dd4681` | 1,898 | No | Yes | No |
| `77392864-3233-48a7-9be5-dd9b132b04e0` | 1,520 | Yes | Yes | No |

## Answers to the requested questions

1. **Does the extracted PDF text contain 88.7% correctly?** Yes. An independent read of the original PDF contains `88.7%`; the actual application extraction also contains `88.7`.
2. **Does any extracted text contain 52.0037%?** No. Neither the original PDF read nor the actual application extraction contains the literal `52.0037`. The application extraction contains `520037` instead.
3. **Which exact chunk(s) were retrieved for the question?** This cannot be proven retrospectively: the exact retrieval event and ranking were not logged. The only eligible selected-source records are the six IDs listed above.
4. **Does the retrieved context contain 88.7%?** The exact historical context cannot be recovered. Three eligible stored chunks contain `88.7`, and all six contain the malformed `520037`; whether the specific historical result included each record is unlogged.
5. **Does the final prompt sent to OpenRouter contain 88.7%?** The exact historical prompt was not logged and cannot be reproduced safely without the original question/history and a new provider request. The prompt builder would copy any retrieved `88.7` unchanged; it performs no numeric transformation.
6. **Did OpenRouter itself generate 52.0037%?** The raw HTTP body was not retained, so byte-for-byte proof is unavailable. The strongest available evidence is yes: the cached final completion contains `52.0037%`, and the provider adapter takes completion content directly from the response before only validation and whitespace trimming. No upstream stored stage contains that literal.
7. **Is there any RTL/bidi/rendering transformation after generation that could alter numeric display?** No. The app applies RTL presentation CSS but has no code that changes numeric content after generation. CSS bidi layout cannot mutate stored characters into a new number.
8. **Is the number different in raw provider response vs UI rendering?** The raw provider response was not logged, so exact byte comparison is impossible. The provider-client result cached by the application and the UI-reported answer are both `52.0037%`; the UI path has no transformation between them.

## Source-path verification

- `engine_optimized.py:295-304` retrieves once, builds the prompt, then invokes the provider.
- `engine_optimized.py:345-365` uses the selected-document server-side filter `metadata.source.keyword` and asks for up to seven results.
- `engine_optimized.py:367-392` and `:467-473` format retrieved `page_content` into the prompt without numerical formatting.
- `openrouter_client.py:104-130` reads `choices[0].message.content` and returns validation/trimmed output; it has no number replacement logic.
- `app_optimized.py:1272-1277` renders the stored message directly with `st.markdown`.

## Minimum recommendation — not implemented

Correct the RTL/table numeric extraction for this document's ingestion path, then remove only this document's duplicate corrupted chunks and re-index this one document from the corrected extraction. Do not change the prompt, model, embeddings, retrieval architecture, or index mapping as part of that minimum fix.

This targeted repair is necessary because otherwise future retrieval may continue to present both `88.7` and the malformed `520037` as competing source evidence.
