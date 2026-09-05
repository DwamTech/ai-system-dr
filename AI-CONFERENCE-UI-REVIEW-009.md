# AI-CONFERENCE-UI-REVIEW-009

**Date:** 2026-09-05  
**Branch:** `conference-v1`  
**Verdict:** **READY_FOR_HUMAN_REVIEW**

This was a focused Arabic-first layout and conversation-workspace pass. It changes only `app_optimized.py` and `style.css`; OpenRouter, RAG, selected-document filtering, cache, embeddings, OpenSearch, Redis, PDF/OCR, SearXNG, prompts, Docker, the guided-tour state machine, and the seven tool implementations were not changed.

## Arabic-first desktop layout

- The native Streamlit sidebar is physically on the **right** at desktop widths, using the rendered Streamlit 1.63 DOM's stable `[data-testid="stAppViewContainer"]` flex container and `[data-testid="stSidebar"]` selector.
- At 1440 px the verified geometry was: main workspace `x=0, width=1140`; sidebar `x=1140, width=300`. No empty left sidebar margin remains.
- The native sidebar's collapse control remains in the rail. In the collapsed Streamlit 1.63 state the actual `[data-testid="stExpandSidebarButton"]` is a visible 42 px control at the upper right; it was clicked in-browser to restore the rail.
- At 768 px, 390 px, and 375 px the desktop reversal is not applied. The existing native collapsible/drawer behavior remains active.
- Main content uses a centered, repeatable shell with consistent inline gutters; header, stepper, context, tab navigation, conversation, and composer align to that grid.
- RTL is normal UI direction. URLs, code, email inputs, filenames/model-like values using `dir="auto"`, and other LTR identifiers retain natural direction. No `unicode-bidi: bidi-override` is used.

## Conversation workspace

- Chat now has a compact header, explanatory line, and a single current-scope treatment: **أنت تسأل عن** followed by the selected document or **كل المستندات**.
- User messages are compact, right-aligned, primary-tinted bubbles with no redundant avatar.
- Assistant messages are wide neutral reading cards with comfortable Arabic line-height. The former green assistant identity border was removed; green remains for success only.
- Mixed Arabic/English answer paragraphs use `unicode-bidi: plaintext`, allowing an English question or answer to read naturally without changing Arabic behavior.
- Document sources are rendered directly in the assistant-card footer as document chips. Scholar links are retained as a separately labelled collapsed **روابط أكاديمية خارجية** section, explicitly distinguished from document evidence.
- The composer has the same width and grid as the conversation. It intentionally remains in normal document flow rather than a fixed overlay: this avoids covering a long answer or its sources while keeping the native safe `st.chat_input` behavior intact.
- Empty chat remains one centered state within the conversation shell. Advanced analysis follows the workspace as a visually secondary expander, separated with a quiet divider rather than a competing chat card.

## Browser review

Microsoft Edge-compatible Chromium was driven with Playwright against `http://127.0.0.1:8502`.

| State / viewport | Result |
|---|---|
| Desktop 1440 — empty workspace | PASS — sidebar right, workflow runs RTL, stable chat grid |
| Desktop 1440 — sidebar collapse/reopen | PASS — collapse and visible 42 px upper-right reopen control |
| Desktop 1440 — active document and RAG answer | PASS — selected `test.txt.pdf`, source chip showed only `test.txt.pdf` |
| Desktop 1440 — user/assistant/source/composer relationship | PASS — compact user bubble, neutral answer card, attached source footer, no source overlap |
| Guided-tour upload state | PASS — coach stayed in main workspace (`x=722..1092`) while the right-side upload target remained separately reachable |
| 768 px | PASS — native drawer behavior, seven tabs present, no page horizontal overflow |
| 390 px | PASS — native drawer behavior, composer within viewport width, no page horizontal overflow |
| 375 px | PASS — native drawer behavior, composer within viewport width, no page horizontal overflow |

Measured document widths had `scrollWidth` equal to each tested viewport width: 1440, 768, 390, and 375 respectively. No browser page errors were captured during responsive or tab-navigation runs.

## Core smoke

- Docker Compose rebuild/recreation: PASS.
- Streamlit health endpoint: PASS.
- OpenSearch, Redis, and SearXNG stayed healthy during validation.
- Safe `test.txt.pdf` upload and background indexing: PASS; the first local embeddings initialization took 156 seconds and completed with one indexed chunk. This existing indexing behavior was not changed.
- Active-document selection: PASS.
- Live RAG question: PASS. The returned document source was `test.txt.pdf` only.
- Seven tabs: PASS — all seven tab controls were clicked successfully with one selected state at a time.
- Guided-tour state machine and production behavior were not modified; its right-rail target positioning was visually verified for the upload step.

## Changed files

- `app_optimized.py` — compact chat-context and source-render helpers; source metadata is retained with the assistant transcript for stable rerenders; Arabic uploader context; external Scholar links are visually separated from document evidence.
- `style.css` — desktop native-sidebar relocation, collapse/reopen treatment, RTL content shell, chat workspace, source footer, composer, secondary advanced-analysis presentation, mixed-direction text handling, and responsive rules.
- `AI-CONFERENCE-UI-REVIEW-009.md` — this browser-review record.

## Demonstrated remaining visual issues

- The native Streamlit uploader retains its built-in English `Upload` and file-size copy. It is now surrounded by Arabic product context; replacing the native control would exceed this layout-only scope.
- The composer is deliberately not fixed over long conversations. This avoids covering answer/source content in Streamlit while preserving the native composer and placing it consistently at the end of the workspace.

The resulting interaction was checked against the intended standard: the desktop page reads as **main workspace | right sidebar**, and the chat reads as one coherent Arabic AI document-conversation workspace rather than disconnected Streamlit blocks.
