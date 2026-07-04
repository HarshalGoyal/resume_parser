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
| **Peer benchmarking** | Compare candidates with similar experience, tech stack, and target role (evolving into embedding-driven similarity) |

Longer-term directions: career-trajectory analysis, interview preparation,
GitHub/portfolio analysis, recruiter simulation, personalized learning
roadmaps, salary intelligence.

## 2. Current Status

What is implemented and tested today:

- `POST /resume/upload` — accepts **PDF and DOCX**, validated by **magic
  bytes** (never the client's Content-Type), size-limited before buffering.
- **Structural parsing** — PyMuPDF (PDF) and python-docx (DOCX) parsers emit a
  shared `ParsedDocument` tree (sections → lines, with layout segments), so
  downstream logic is format-agnostic.
- **Deterministic enrichment** — layout/convention-based extraction of contact
  info, skills (category-aware, punctuation-safe), and work experience
  (title/company/dates recovered from visual column gaps).
- **Session storage** — cache-aside repository over per-session JSON + file
  artifacts (`metadata.json`, `document_tree.json`, `resume_extracted.json`).
- `GET /info` — self-describing API index with a curl example per endpoint.
- **Quality gates** — 42 tests (unit, synthetic, end-to-end) plus ruff, mypy,
  and pytest enforced in CI on every PR.

AI evaluation, JD comparison, and benchmarking are **designed but not yet
implemented** (see Roadmap).

## 3. Architecture

```text
Client
  ↓
FastAPI API layer            (routes: upload, info, health)
  ↓
Resume processing pipeline   (structural parse → enrichment)
  ↓
Session repository           (in-memory cache ⇄ file store)
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
```

Configuration is environment-driven (`.env` supported): `STORAGE_PATH`,
`UPLOAD_MAX_SIZE`, `LOG_LEVEL`, `LOG_FILE`, `ALLOWED_HOSTS` — see
`backend/app/core/config.py`.

### Tests & quality gates

```bash
pytest -q            # 42 tests: unit, synthetic, API end-to-end
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
| **2 — Results API + DTOs** | `GET` endpoints for parse results, schema layer separating wire format from domain models | next |
| **3 — AI evaluation** | `LLMProvider` interface, resume evaluator, JD matcher, prompt versioning, token/cost tracking | planned |
| **4 — Persistence + scale** | Postgres + object storage behind existing interfaces, background workers, TTL cleanup, observability | planned |
| **5 — Intelligence** | Embedding-based peer benchmarking, vector search, agentic evaluators (recruiter / ATS / hiring-manager personas) | future |

## 6. Primary Technical Goal

Demonstrate **backend architectural maturity** — scalable AI-system design,
modular service composition, and production-oriented engineering — rather than
merely integrating LLM APIs.

```text
Clean Architecture  >  Maximum Technologies
```
