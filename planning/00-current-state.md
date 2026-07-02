# Resume Parser — Current State Assessment

_Last updated: 2026-07-02. Source of truth: `mainline`._

## What the README claims vs. what exists

The README describes an "AI-Native Career Intelligence Platform" (resume eval, JD
matching, peer benchmarking, embeddings, agents). **Almost all of that is
aspirational and commented out.** What actually ships today is a Phase-0 skeleton:

```
Client → POST /resume/upload → PDF structural parse (PyMuPDF) →
regex enrichment (contact/skills/experience) → JSON files on disk
```

## What actually works (live code path)

- `POST /resume/upload` — validates content-type, reads file into memory, size-checks,
  creates a session, persists file + `metadata.json`, then **synchronously** runs the
  parse pipeline and returns a status (NOT the parsed data).
- `PDFParser` (`ai/parsers/pdf_parser.py`, ~143 LOC) — real PyMuPDF structural parser:
  font/bold heuristics → headers → sections. Linear complexity. The one solid module.
- `ResumeEnrichmentService` (~149 LOC) — regex extraction of contact info, skills
  (section-heading based, no taxonomy), work experience (bold+date state machine).
- `SessionRepository` + `FileStore` + `MemoryStore` — cache-aside over JSON files.
- `GET /health/`, parser-config endpoints (see "broken" below).

## What is empty / stubbed / dead (0-byte or unused)

- **All LLM/AI eval code**: `ai/llm/client.py`, `ai/llm/provider.py`,
  `ai/evaluators/*.py`, `ai/prompts/*.txt`, `ai/parsers/section_parser.py`,
  `ai/parsers/skill_extractor.py` — all empty.
- **JD + Evaluation features**: `services/evaluation_service.py`, `services/jd_service.py`,
  `models/evaluation.py`, `models/jd.py`, `api/routes/evaluation.py`, `api/routes/jd.py`,
  `api/routes/session.py` (contains a model, no router) — empty or not mounted.
- **Schemas layer**: `schemas/*.py` all empty → domain models are used directly as API
  responses (no DTO boundary).
- **utils**: `utils/file_utils.py`, `utils/text_utils.py` — empty.
- **Dead parsers**: `nlp/resume_nlp_parser.py` + `parsers/nlp_ml_parser.py` — two
  duplicate spaCy/sklearn parsers, unused, ML "trained" on 6 hardcoded examples. Pull in
  heavy deps (spacy, sklearn, pdfplumber) that aren't even in requirements.txt.
- **Broken**: `services/session_service.py` imports `app.model` (nonexistent) — would
  ModuleNotFoundError if imported; currently unreferenced.
- `core/exceptions.py` — rich exception hierarchy, never wired into the app.

## Confirmed high-severity issues

1. **Path traversal / arbitrary file write** — `file_store.save_file` joins the
   unsanitized client `file.filename` onto the storage path (`file_store.py:85`).
   `../../evil` escapes the session dir.
2. **Parser-config API is a no-op** — `set_selected_parser` changes a global that
   nothing reads; `ResumeParsingService` always uses `PDFParser`. Misleads consumers.
3. **Fragmented state** — `upload.py` holds a module-level `SessionRepository`, but each
   request also builds a fresh `ResumeParsingService` → a *second* `SessionRepository` +
   `MemoryStore`. The two caches never share; stage updates land in a throwaway cache.
4. **Global mutable parser config** — shared across all requests/users, no locking.
5. **Blocking file I/O in async handlers** — all `open()`/`json` calls are sync inside
   `async def`; they block the event loop under concurrency.
6. **Size check after full read** — `await file.read()` buffers the whole upload into RAM
   before the size limit is applied → memory-exhaustion DoS.
7. **Content-type-only file validation** — spoofable; no magic-byte sniffing.
8. **No cleanup / no TTL** — `session_timeout_minutes` is defined but never enforced;
   disk + (if repo becomes a singleton) memory grow unbounded.

## Cross-cutting gaps

- No tests, no linting, no type-checking in CI. Only CI is `prevent-mainline.yml`, whose
  guard has a bash syntax bug (`[ ... || ... ]`) and relies on a spoofable author-name string.
- No CORS, no auth, no global exception handlers, no request IDs / structured logging,
  no metrics/tracing, no log rotation (hardcoded `backend_app.log`).
- `requirements.txt` pins `unicorn==2.1.4` (CPU emulator) — almost certainly a typo for
  the already-present `uvicorn`. Supply-chain smell; remove.
- Module-level logging side effects on import in every model file.
- `run.py` hardcodes `reload=True`, `host="localhost"`, `port=3030` — no env switch.
