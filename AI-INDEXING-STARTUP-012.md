# Indexing startup and concurrency findings — 2026-09-05

The reported job `2c90eab1b6ff488b9b9e764eb67bacab` completed at 100%,
indexing two chunks from `RAG_Test_Arabic_Document.pdf` in 142 seconds.
Its initial 5% stage was loading the embedding model after container recreation;
the cached weights were previously stored only in the container filesystem.
The persisted elapsed counter stayed at zero during the blocking load.

Changes deployed locally:

- Existing complete Hugging Face cache copied to `/app/data/huggingface`;
  Compose now sets `HF_HOME` to that persistent location.
- Running-job elapsed time calculated on status reads, without fake percentage
  advancement. Completed durations remain fixed.
- Model preparation and OpenSearch connection have separate progress stages.
- Completed jobs can lazily reconstruct their engine after service restart.
  New job metadata records the configured model.
- Production file watching disabled to avoid scanning Transformers' lazy
  optional vision modules during every rerun.

Validation: five isolated status/reconnect tests passed; Python compilation and
Docker image build passed. After container recreation, an embedding query with
`HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` loaded the persistent model in
6.83 seconds and produced 384 dimensions. A new live indexing job
`debeb9b8f40a47efb489796de5ec09c1` completed at 100% in seven seconds.
All four local services were healthy.

The browser reconnect probe timed out locating the document option; an actual
post-restart RAG response for the original job was not verified by that probe.
Engine reconstruction is covered by the isolated regression tests.

## Multi-user assessment requested afterward

This fix does not establish concurrent-user readiness. Source review shows:

- `IndexingJobManager.has_running_job()` gates indexing across all users; there
  is one admitted indexing job, with rejection rather than a per-user queue.
- All documents use `knowledge_base_optimized_v2`. Retrieval is global or
  filtered by filename, with no owner/tenant filter. Cache identities similarly
  lack an owner. Browser session separation is not document authorization.
- Each job constructs an engine with its own lazy embedding instance, and
  completed engines remain in `_engines` without eviction. User-triggered
  workspace initialization can create additional instances.
- Indexing executes in daemon threads within the Streamlit process. A process
  failure affects all sessions and interrupts active indexing.
- Upload limits allow 8192 MB per file, while upload payloads are handled in
  memory. No per-user resource quotas or bounded global generation queue exists.
- Provider requests have timeouts and limited retries, but no global concurrency
  controller. A shared provider key alone is not evidence of a failure.

No five-user simultaneous load test was performed. The reported remote-server
outage cannot be attributed to OOM, provider limits, or proxy timeouts without
the server's resource information and logs from the failure interval.

User clarification: the UI stayed available while indexing stalled and answers
failed. A shared archive visible to everybody is an explicit product requirement;
the global document library is therefore intentional, not something to privatize.
Conversations, indexing job ownership/status, pending questions, and errors must
remain independent for each user. Public document access must be preserved while
adding bounded job scheduling, resource reuse, generation admission control, and
concurrent-session validation. Server RAM/CPU specifications remain unknown.
