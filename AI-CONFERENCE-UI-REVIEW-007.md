# AI-CONFERENCE-UI-REVIEW-007

**Date:** 2026-09-05
**Branch:** `conference-v1`
**Verdict:** **READY_FOR_HUMAN_REVIEW**

The guided tour is now a stateful, action-driven walkthrough of the real Streamlit application. It remains present across normal reruns, advances only when the corresponding production action completes, and keeps the actual control bright and usable. The approved application design and all provider, RAG, filtering, cache, embedding, persistence, PDF/OCR, search, and seven-tool behavior were preserved.

## State machine and rerun persistence

- Session-only state is explicit: `tour_active`, `tour_step`, `tour_completed`, `tour_manual_restart`, `tour_last_completed_step`, indexing/error/confirmation state, and a guarded pending chat prompt.
- Every key is initialized only when absent; file upload, indexing, selection, chat submission, widget changes, and Streamlit reruns do not reset the walkthrough.
- `sync_tour_with_actions()` advances at most one action-driven step per normal rerun. Manual Previous/Next sets a one-rerun hold so real state cannot immediately undo the requested navigation.
- The permanent four-stage workflow derives its display from the active tour step while onboarding is running, and from real application state afterward. A Help restart was verified to return both displays to Step 1.
- Finish sets `tour_active=False` and `tour_completed=True`. Skip uses a pre-rerun callback to stop all remaining onboarding. Neither reopens automatically in the same session; Help retains **إعادة الجولة التعريفية**.

## Action completion rules

| Tour step | Real target | Completion rule | Result |
|---|---|---|---|
| 1 — رفع المستندات | Native PDF uploader | At least one uploaded file exists | Automatically advanced to Step 2 after selecting `test.txt.pdf` |
| 2 — الفهرسة | Existing indexing button and flow | Existing ingestion completes successfully | Automatically advanced to Step 3; failure remains on Step 2 with a contextual note |
| 3 — المستند النشط | Existing active-document selector | A specific document is selected | `runtime-alpha.pdf` automatically advanced to Step 4; manual Next remains available for deliberate all-document use |
| 4 — ابدأ المحادثة | Native `st.chat_input` | A real typed or voice prompt is submitted | Prompt is preserved across an immediate rerun and Step 5 appears before waiting for OpenRouter |
| 5 — أدوات المستند | Existing seven-tool tab navigation | No real action required | **إنهاء الجولة** completes onboarding |

Small in-card confirmations report file selection, successful indexing, selected-document scope, and submitted chat without adding toast noise.

## Spotlight and target interaction

- The tour is a fixed native Streamlit coach container rather than a blocking `st.dialog`; Settings remains unchanged.
- Stable target keys identify the uploader, indexing action, active-document selector, chat composer, and seven-tool navigation. No fragile `nth-child` targeting is used.
- The active target is raised above a `rgba(4, 8, 14, .70)` large-shadow surround, leaving the target itself undimmed and clickable.
- A 3 px primary ring, 7 px restrained halo, elevated surface, and lower shadow make focus obvious without flashing or neon animation.
- The real highlighted widget is the primary action. Action-required Next buttons remain disabled until the real prerequisite is complete; Previous, Skip, and Help restart remain available.
- Skip is the close semantic. The tour does not create a modal or keyboard trap.
- A focused stale-widget guard prevents Streamlit's prior control row from appearing during a long provider rerun; the live Step 4→5 transition showed one coach, one Step 5 marker, and exactly three visible controls.

## Coach-card positioning

| Step | Desktop coach placement | Measured coach / target relationship at 1440 px |
|---|---|---|
| Upload | upper center-right | Coach `x=710, y=88`; uploader `x=27, y=287`; no overlap |
| Index | middle center-right | Coach `x=710, y=240`; index action `x=27, y=474`; no overlap |
| Document | lower right | Coach `x=1022, y=384`; selector `x=27, y=246`; no overlap |
| Chat | upper right | Coach `x=1022, y=88`; composer `x=380, y=644`; no overlap |
| Tools | lower right | Coach `x=1022, y=551`; tabs `x=380, y=417`; no overlap |

At 768 px and below, the coach changes to a safe-margin bottom sheet; the chat step uses a top placement so it does not cover the composer. Sidebar steps add an explicit phone instruction to open the document menu.

## Complete live walkthrough

Microsoft Edge was driven through Playwright against `http://127.0.0.1:8502`:

1. Fresh session displayed Step 1 with one bright, clickable native uploader.
2. Uploading the safe repository PDF survived the rerun and displayed Step 2.
3. Running the real ingestion flow survived initialization/indexing reruns and displayed Step 3.
4. Selecting `runtime-alpha.pdf` displayed Step 4.
5. Submitting `What is the unique alpha marker?` displayed Step 5 before the provider response completed.
6. The response contained `ALPHA-771`; `runtime-alpha.pdf` was present as the source and `runtime-beta.pdf` was absent.
7. Finish removed the tour. Help → **إعادة الجولة التعريفية** restored Step 1 and the matching workflow state.
8. Previous then Next was exercised after real document selection, and Skip was exercised after restart; both preserved correct state and Skip ended the whole tour.

No browser page errors were captured.

## Responsive browser validation

| Viewport | Coach inside viewport | Page overflow | Sidebar target usable | Index target visible | Skip/tap control |
|---|---|---|---|---|---|
| 1440 px | PASS | none | PASS | PASS | PASS |
| 768 px | PASS | none | PASS | PASS | PASS — 42 px |
| 390 px | PASS | none | PASS | PASS | PASS — 42 px |
| 375 px | PASS | none | PASS | PASS | PASS — 42 px |

The mobile uploader was operated while the tour was active, and Skip was clicked successfully in separate fresh sessions at all three responsive widths.

## Core smoke test

- Streamlit health endpoint: PASS.
- Docker Compose services: Streamlit, OpenSearch, Redis, and SearXNG healthy during validation.
- Safe PDF upload and real indexing: PASS.
- Active-document selection: PASS.
- OpenRouter generation through the existing RAG path: PASS.
- Selected-document source isolation: PASS for `runtime-alpha.pdf`; Beta was not returned.
- Seven tool tabs reachable: PASS — seven tab roles detected.
- Provider, retrieval, filter, cache, embeddings, OpenSearch, Redis, PDF/OCR algorithm, SearXNG, and tool feature logic: not modified.

## Files changed

- `app_optimized.py` — persistent tour state machine, real-action completion, guarded chat hand-off, smart controls, workflow-step agreement, restart/skip semantics, and stable tour target keys.
- `style.css` — target-aware coach positions, true non-blocking spotlight, visible focus ring, stale-widget guard, and responsive bottom-sheet behavior.
- `AI-CONFERENCE-UI-REVIEW-007.md` — this implementation and browser-acceptance record.

## Remaining demonstrated issues

None within the interactive-tour scope. The native Streamlit uploader's existing English internal copy remains the previously documented platform limitation and was not changed by this onboarding surgery.
