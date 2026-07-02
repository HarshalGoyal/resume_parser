# Resume Parser — Phased Plan

_Do the phases in order. Each phase is a small, reviewable PR. Do NOT start Phase 1
until the open questions in `02-open-questions.md` are answered — the answers change
scope (especially: portfolio/demo vs. real multi-tenant, and whether the LLM eval is
the next feature)._

## Phase 0 — Stabilize & de-risk (no new features) — HIGHEST PRIORITY

Goal: make the existing working slice correct, safe, and testable.

- [ ] **Fix path traversal** — sanitize/ignore client filename; store under a
      server-generated name (e.g. `original.pdf`) inside the UUID session dir. Keep the
      original name only as metadata. (`file_store.save_file`, `upload.py`)
- [ ] **Fix state fragmentation** — make `SessionRepository` (and its `MemoryStore`) a
      single shared instance injected via FastAPI dependencies; stop building a new
      `ResumeParsingService` per request, or have it accept an injected repository.
- [ ] **Offload blocking I/O** — wrap file/JSON reads/writes in `asyncio.to_thread`
      (or make `FileStore` sync and call it via a threadpool). Decide one convention.
- [ ] **Stream + pre-check upload size** — reject on `Content-Length` / chunked read
      before buffering the whole file into RAM.
- [ ] **Wire the exception hierarchy** — register `@app.exception_handler`s in `main.py`;
      stop swallowing exceptions with generic 500s; log tracebacks (add `logger.exception`).
- [ ] **Remove dead code** — delete/relocate: `nlp/resume_nlp_parser.py`,
      `parsers/nlp_ml_parser.py`, `services/session_service.py`, empty stub files that
      aren't part of the immediate roadmap. Fix `unicorn` → `uvicorn` in requirements.
- [ ] **Fix parser-config** — either wire `get_selected_parser()` into
      `ResumeParsingService` (real strategy selection via `ParserInterface`) OR remove the
      endpoint until it does something. No no-op facades.
- Validation: unit tests for parser + enrichment on sample PDFs; a traversal regression
  test; a concurrency smoke test.
- Rollback: each item is an independent revert.

## Phase 1 — Testing + CI foundation

- [ ] pytest + fixtures with 2-3 sample resume PDFs (good, messy, non-PDF).
- [ ] Unit tests: `PDFParser`, `ResumeEnrichmentService` regexes, `SessionRepository`
      cache-aside, upload validation (size, type, traversal).
- [ ] GitHub Actions: install deps, ruff, mypy, pytest on PRs. Replace the brittle
      `prevent-mainline.yml` author-name check with real branch protection + a real CI gate.

## Phase 2 — Return results + proper API contract

- [ ] Add `GET /resume/{session_id}/{upload_id}` to fetch parsed results (today the parse
      output is computed then discarded).
- [ ] Introduce `schemas/` DTOs so domain models aren't the wire format.
- [ ] Decide sync-in-request vs. background task for parsing (see open questions on scale).

## Phase 3 — LLM evaluation (the actual "AI" feature) — only after Phase 0-2

- [ ] Define `LLMProvider` interface + one concrete impl (provider TBD — org context
      suggests Anthropic/Claude; confirm). Config-driven API key, never hardcoded.
- [ ] Implement `resume_evaluator` + `jd_matcher` behind the interface; version prompts.
- [ ] Add token/cost tracking + timeouts + retries with backoff. Guard against
      prompt injection from resume text (treat resume content as untrusted data).

## Phase 4 — Persistence + scale (only if real multi-user target)

- [ ] Replace file/JSON store with Postgres (metadata) + object storage (files) behind
      the existing repository interface. Add TTL/cleanup job.
- [ ] Background worker (RQ/Celery) for parsing + eval. Observability: metrics, tracing.

## Guardrails for whoever picks this up
- Prefer deleting dead code over "keeping it just in case."
- Every PR: keep it small, add tests, match existing style, no new abstractions without a
  second concrete use.
- Don't build Phase 3/4 infrastructure before the Phase 0 correctness fixes land.
