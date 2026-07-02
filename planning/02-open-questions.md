# Open Questions (answer before writing code)

1. **Intent & audience** — Is this a portfolio/demo to showcase architecture, or a system
   that will serve real (multi-)users? This decides how much to invest in auth, persistence,
   scale, and observability.
2. **Next priority** — Harden the existing parse pipeline (Phase 0), or build the LLM
   evaluation feature that the README advertises but that is entirely empty?
3. **LLM provider** — Which provider for the eval/JD features? (Org context points to
   Anthropic/Claude.) Any budget/latency constraints?
4. **DOCX** — Upload accepts DOCX by content-type but only `PDFParser` exists. Support DOCX
   for real, or restrict to PDF only?
5. **Multi-tenancy / auth** — Is any authentication expected, or is this open/local-only?
6. **Deployment target** — Local only, or Docker/K8s/cloud? Affects config, logging paths,
   and the `run.py` reload/host settings.
7. **Scale targets** — Expected concurrent uploads and resume volume? Determines whether
   parsing must move to a background worker and whether the file store must become a DB.

## Recommendation if answers are unavailable
Treat as a portfolio-grade Phase-0 backend: do Phase 0 (stabilize) + Phase 1 (tests/CI)
first — these are unambiguously correct regardless of the answers — then reassess.

---
## ANSWERS (2026-07-02)
1. Intent: **combination** — build as if it could become a real multi-user product, but no premature infra. Interfaces must allow persistence/workers to slot in later.
2. Priority: **Both, in order** — Phase 0 stabilize + Phase 1 tests/CI first, then LLM eval.
3. LLM provider: **Decide later** — design `LLMProvider` interface only, no concrete impl yet.
4. File types: **PDF + DOCX** — implement a real DOCX parser path; validate by magic bytes.
