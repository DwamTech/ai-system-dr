# AI-CONFERENCE-UI-REVIEW-010

**Date:** 2026-09-05  
**Branch:** `conference-v1`  
**Verdict:** **READY_FOR_HUMAN_REVIEW**

This pass rebuilds the responsive information architecture without changing the
provider, prompts, RAG, retrieval filters, cache, embeddings, OpenSearch,
Redis, PDF/OCR, SearXNG, Docker, or tool business logic.

# Mobile Information Architecture

The first mobile screen now presents the product header, one compact current
step indicator, and the required document action in the main workspace. A
visitor does not need to discover or open a drawer before starting the primary
flow: upload -> index -> select a document -> ask.

# Main Workflow Relocation

`render_primary_workflow()` is the single main-content presentation of the
existing workflow state and handlers. It uses the existing upload state, the
existing background-indexing handler, the existing active-document selector
key, and the existing job-status renderer.

The panel changes according to the real state:

- No document: a real PDF uploader is immediately visible.
- Files selected: selected-file status and the real **ابدأ الفهرسة** action are
  visible.
- Indexed files with no scoped document: the real active-document selector is
  visible.
- Active document: the compact context card confirms the selected file and
  returns attention to chat.

There is no parallel mobile implementation and no conflicting uploader state.

# Sidebar New Role

The right desktop sidebar and the collapsed mobile drawer are now secondary:
product identity, optional active-document reminder, settings, archive, and
help. Upload, indexing, document selection, and chat do not depend on it.

# RTL Corrections

Main Arabic surfaces use RTL direction and logical alignment. Mixed values such
as a Latin filename, model slug, URL, code, or numeric identifier retain their
natural readable direction; text is not bidi-overridden. Form labels,
selectboxes, workflow cards, chat, source chips, and mobile tool labels were
reviewed in their rendered RTL positions.

# Mobile Stepper

Desktop retains the four-step RTL workflow presentation. At `<=768px` those
four cards are replaced by one compact, readable progress component showing the
current step, `الخطوة n من 4`, and a progress line. It does not compress the
desktop cards into a narrow row.

# Mobile Tools Navigation

At mobile widths the seven tools become a deliberate two-column, wrapped grid.
Each tab remains readable and at least 44 px high. This avoids requiring
horizontal navigation to discover the remaining tools. Desktop and compact
desktop preserve the full RTL tab navigation.

# Mobile Chat

The chat workspace uses the available mobile width with safe horizontal
padding. User messages remain a distinct right-aligned surface; assistant
answers use a neutral, full-readable-width surface. Source chips stack beneath
the answer, and the native composer plus voice affordance retain touch-sized
controls. The composer is part of normal document flow rather than a desktop
overlay.

# Tour Mobile Behavior

The proven action-driven state machine is unchanged. Its targets now point to
the main upload, indexing, selection, composer, and tool controls. Mobile copy
is shortened, and the coach is constrained to a compact top/bottom sheet so its
target remains visible. The indexing and tools steps use a top placement on
narrow screens so their main-content targets are not covered.

# Seven-Tab Responsive Matrix

Every tab was selected at each viewport. The matrix records seven rendered tab
controls, page-level horizontal overflow after each selection, the minimum tab
touch height, and browser page errors.

| Viewport | Tabs selected | Page overflow after tabs 1-7 | Minimum tab height | Page errors |
|---|---:|---|---:|---:|
| 1440 px | 7 | 0 px for each | 46 px | 0 |
| 1024 px | 7 | 0 px for each | 46 px | 0 |
| 768 px | 7 | 0 px for each | 46 px | 0 |
| 430 px | 7 | 0 px for each | 44 px | 0 |
| 390 px | 7 | 0 px for each | 44 px | 0 |
| 375 px | 7 | 0 px for each | 44 px | 0 |

The reviewed tabs were: المحادثة، الملخص، الكيانات، الترجمة، التحليل،
الخريطة الذهنية، والبحث الأكاديمي. The mobile translation, analysis, and web
tabs were additionally captured after selecting an active document.

# Viewports Tested

Playwright drove Chrome against the running local application at `1440`,
`1024`, `768`, `430`, `390`, and `375` px. At 390 px a first visit displayed
the real main uploader without opening the drawer. The real workflow then
uploaded `test.txt.pdf`, started background indexing from the main panel,
completed it, selected the document, and sent a real RAG prompt.

The test indexing job `4e56aecdf11547f589f74b420ec45c37` completed with one
file and one chunk in 140 seconds. During preparation it visibly reported the
embedding/index connection stage; completion reported 100% and exposed the
document-selection state. The RAG answer rendered two chat messages and one
source chip for `test.txt.pdf` at 390 px. The same answer-and-source path was
also rendered at 1440 px. No page errors were captured.

# Screenshots Reviewed

Rendered screenshots were saved locally under
`C:\Users\Copy\AppData\Local\Temp\ai-conference-010` and visually reviewed:

- `fresh-390.png` — first visit, compact header, mobile stepper, and visible
  main uploader.
- `uploaded-390.png` and `index-running-390.png` — selected-file and real
  main indexing states.
- `indexed-select-390.png` and `active-document-390.png` — completed-index and
  main active-document selection state.
- `chat-answer-clean-390.png` — mobile answer, visually distinct user/assistant
  surfaces, stacked source, and full-width composer.
- `tab-7-390.png`, `translation-390.png`, `analysis-390.png`, and `web-390.png`
  — mobile two-column tool navigation and selected tool states.
- `chat-answer-1440.png` — desktop chat answer with the right secondary sidebar.

# Core Smoke

- `py -3 -m py_compile app_optimized.py`: PASS.
- `git diff --check`: PASS.
- Docker Compose services: Streamlit, OpenSearch, Redis, and SearXNG healthy.
- Streamlit health endpoint: PASS.
- Main-workspace upload and background indexing: PASS.
- Completed job reconnect and main active-document selector: PASS.
- Live RAG answer with an isolated displayed source: PASS for `test.txt.pdf`.
- Provider, retrieval, filters, cache, embeddings, persistence, PDF/OCR,
  SearXNG, and seven-tool feature logic: not modified in this pass.

# Demonstrated Remaining Issues

- The native Streamlit uploader still contains its platform-provided English
  internal button and size copy. Replacing it safely requires a custom uploader
  and is outside this UI relocation scope.
- The first embedding-model warm-up can spend time in the explicit preparation
  stage before a time estimate is available. The job remains durable across a
  browser refresh and reports its completed state; this pass does not alter the
  indexing engine or its model-loading behavior.
