# AI-Native Career Intelligence Platform

An AI-native backend platform for evaluating developer resumes, benchmarking
candidates against industry peers, and generating intelligent career insights.

This is **not** a simple resume-reviewer application. The goal is
career-intelligence *infrastructure*: a modular, extensible AI evaluation
pipeline that starts as a lightweight local backend and evolves incrementally
into a production-grade platform — without rewrites.

---

## 1. Product Vision

The platform will ultimately support:

| Capability | Description |
|---|---|
| **Resume parsing** | Extract raw text, sections, skills, experience, education, and keywords from uploaded resumes |
| **AI evaluation** | Strengths, weaknesses, ATS-friendliness, readability, resume quality, career positioning |
| **JD comparison** | Match percentage, missing skills, role alignment, improvement suggestions against a job description |
| **Peer benchmarking** | Embedding-driven similarity: compare candidates with similar experience, tech stack, and target role |

Longer-term directions: career-trajectory analysis, interview preparation,
GitHub/portfolio analysis, recruiter simulation, personalized learning
roadmaps, salary intelligence.

## 2. Current Status

What is implemented and tested today:

- `POST /resume/upload` — accepts **PDF and DOCX**, validated by **magic
  bytes** (never the client's Content-Type), size-limited before buffering.
  Parsing runs **in the background**: the response returns immediately with
  result/status links, and clients poll `…/status` (failures are recorded
  there with an error message).
- **Structural parsing** — PyMuPDF (PDF) and python-docx (DOCX) parsers emit a
  shared `ParsedDocument` tree (sections → lines, with layout segments), so
  downstream logic is format-agnostic.
- **Deterministic enrichment** — layout/convention-based extraction of contact
  info, skills (category-aware, punctuation-safe), and work experience
  (title/company/dates recovered from visual column gaps).
- **Session storage** — cache-aside repository over per-session JSON + file
  artifacts (`metadata.json`, `document_tree.json`, `resume_extracted.json`,
  `evaluation.json`).
- **Results API** — `GET /resume/{session_id}/{upload_id}` (extraction) and
  `…/status` (processing stage), with a `schemas/` DTO layer owning the wire
  format; upload responses include ready-to-follow result/status links.
- **AI evaluation & JD matching** — `POST /resume/{…}/{…}/evaluate` and
  `POST /jd/match`, built on a provider-agnostic `LLMProvider` interface with
  versioned prompts, JSON-validated outputs, token tracking, and
  prompt-injection fencing of document text. A concrete provider is selected
  via `LLM_PROVIDER` config (returns 503 until one is configured; a
  deterministic fake provider backs tests and local development).
- `GET /info` — self-describing API index with a curl example per endpoint.
- **Operational hardening** — optional **API-key auth** (`API_KEY` +
  `X-API-Key` header; health/docs exempt), **TTL cleanup** of expired sessions
  (`SESSION_TIMEOUT_MINUTES`, background job), request IDs + access logging,
  and Prometheus **`/metrics`**.
- **Pluggable metadata storage** — JSON file store by default; set
  `DATABASE_URL` (SQLite/Postgres via SQLAlchemy) to keep session metadata in
  a database while file artifacts stay on disk.
- **Peer benchmarking** — `POST /resume/{…}/{…}/index` adds a candidate to the
  vector index (embeddings via `EMBEDDINGS_PROVIDER`: openai/google/bedrock,
  or the offline `fake`); `GET …/similar` returns the most similar indexed
  candidates with shared-skill and skill-gap analysis. The index is
  file-backed behind a protocol seam (pgvector/Qdrant can slot in later).
- **Persona evaluation panel** — `POST /resume/{…}/{…}/panel` runs three
  independent LLM personas (technical recruiter, ATS auditor, hiring manager)
  in parallel over the parsed resume and aggregates their scored verdicts.
- **Quality gates** — 102 tests (unit, synthetic, end-to-end) plus ruff, mypy,
  and pytest enforced in CI on every PR.

Peer benchmarking and a real LLM provider adapter are the main capabilities
**not yet implemented** (see Roadmap).

## 3. Architecture

```text
Client
  ↓
FastAPI API layer            (routes: upload, info, health)
  ↓
Resume processing pipeline   (structural parse → enrichment)
  ↓
Session repository           (file store by default; SQL via DATABASE_URL)
```

```text
backend/
├── app/
│   ├── api/routes/     # HTTP surface (thin; no business logic)
│   ├── core/           # config, logging, exception hierarchy
│   ├── ai/parsers/     # PDFParser, DOCXParser → ParsedDocument
│   ├── ai/llm/         # LLM provider abstraction (planned)
│   ├── ai/evaluators/  # resume evaluator, JD matcher (planned)
│   ├── services/       # orchestration (parsing, enrichment)
│   ├── storage/        # SessionRepository, FileStore, MemoryStore
│   ├── models/         # domain models (Pydantic)
│   ├── schemas/        # API DTOs (planned)
│   └── utils/          # generic text/file helpers
└── tests/              # pytest suite + synthetic fixtures
```

### Design principles

1. **Independently replaceable components.** Storage, parsers, and (soon) LLM
   providers sit behind interfaces so `InMemory…` can become `Postgres…`,
   `Redis…`, or `Vector…` without touching core logic.
2. **Deterministic + AI hybrid.** Structured parsers and rule-based extractors
   handle what they do reliably and cheaply; LLM reasoning is reserved for
   judgment tasks. This keeps the system explainable, testable, and
   cost-efficient — never a single opaque LLM call.
3. **Separation of concerns.** API handling, orchestration, AI logic, parsing,
   storage, and domain models are distinct layers with one-way dependencies.
4. **Clean architecture over maximum technology.** Every addition must earn its
   complexity; the system should evolve naturally, not accrete frameworks.

### Why FastAPI (not Django)

The system is API-centric, async-oriented, and orchestration-heavy — not
database-centric or admin-panel-centric. FastAPI gives first-class async,
lightweight service structure, streaming, and painless AI-SDK integration.
The choice is architectural, not preferential.

## 4. Getting Started

```bash
# 1. Install (Python 3.12+)
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt        # runtime
pip install -r requirements-dev.txt    # + dev/CI tools

# 2. Run the API (http://localhost:3030)
cd backend && python ../run.py         # or: uvicorn app.main:app --port 3030

# 3. Explore
curl http://localhost:3030/info        # lists every endpoint with curl examples
curl -X POST -F 'file=@resume.pdf' http://localhost:3030/resume/upload
# response includes links.result and links.status:
curl http://localhost:3030/resume/<session_id>/<upload_id>          # extraction
curl http://localhost:3030/resume/<session_id>/<upload_id>/status   # stage
curl -X POST http://localhost:3030/resume/<session_id>/<upload_id>/evaluate
curl -X POST http://localhost:3030/resume/<session_id>/<upload_id>/panel
curl -X POST http://localhost:3030/resume/<session_id>/<upload_id>/index
curl http://localhost:3030/resume/<session_id>/<upload_id>/similar?top_k=5
curl -X POST -H 'Content-Type: application/json' \
     -d '{"session_id":"...","upload_id":"...","jd_text":"..."}' \
     http://localhost:3030/jd/match
```

### Enabling the AI endpoints

```bash
cp .env.example .env        # then paste your API key(s) into .env
pip install langchain-anthropic   # or -openai / -google-genai / -aws

# Activate a provider at runtime - no restart needed:
curl -X POST -H 'Content-Type: application/json' \
     -d '{"provider":"anthropic"}' http://localhost:3030/llm/activate
curl http://localhost:3030/llm/providers   # inspect status of all providers
```

Providers: `anthropic`, `openai`, `google`, `bedrock` (AWS credential chain),
`fake` (dev/testing). Pass `"model": "..."` in the activate body to override
the provider's default model. Alternatively set `LLM_PROVIDER` in `.env` as
the startup default. AI endpoints return 503 until a provider is active.

Other settings (see `backend/app/core/config.py` / `.env.example`):
`API_KEY` (enables X-API-Key auth), `DATABASE_URL` (SQL metadata storage),
`SESSION_TIMEOUT_MINUTES` / `CLEANUP_INTERVAL_MINUTES` (retention),
`HOST` / `PORT` / `RELOAD` (server), `STORAGE_PATH`, `UPLOAD_MAX_SIZE`,
`LOG_LEVEL`, `LOG_FILE`, `ALLOWED_HOSTS`.

### Tests & quality gates

```bash
pytest -q            # 58 tests: unit, synthetic, API end-to-end
ruff check backend   # lint (correctness rules)
mypy                 # type-check
```

All three run in CI (`.github/workflows/ci.yml`) on every PR and mainline push.

## 5. Roadmap

Development is staged to avoid premature complexity; each phase lands as
small, reviewable PRs.

| Phase | Scope | Status |
|---|---|---|
| **0 — Stabilize** | Security (traversal, magic bytes, size limits), consistent state, non-blocking I/O, exception wiring | ✅ done |
| **1 — Test + CI** | pytest suite, fixtures, ruff/mypy/pytest gate | ✅ done |
| **2 — Results API + DTOs** | `GET` endpoints for parse results, schema layer separating wire format from domain models | ✅ done |
| **3 — AI evaluation** | `LLMProvider` interface, resume evaluator, JD matcher, prompt versioning, token/cost tracking | ✅ done (real provider adapter pending) |
| **4 — Persistence + scale** | Background parsing, TTL cleanup, API-key auth, SQL metadata storage (SQLite/Postgres), request IDs + metrics | ✅ done |
| **5 — Intelligence** | Embedding-based peer benchmarking, vector search, persona evaluators (recruiter / ATS / hiring-manager) | ✅ done |
| **Future** | Queue-based workers at volume, pgvector/Qdrant index, career-trajectory analysis, interview prep, GitHub/portfolio analysis | ideas |

## 6. Primary Technical Goal

Demonstrate **backend architectural maturity** — scalable AI-system design,
modular service composition, and production-oriented engineering — rather than
merely integrating LLM APIs.

```text
Clean Architecture  >  Maximum Technologies
```
