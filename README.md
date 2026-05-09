# AI-Native Career Intelligence Platform

## 1. Vision

The goal of this project is to build an AI-native backend platform capable of evaluating developer resumes, benchmarking candidates against industry peers, and providing intelligent career insights.

This is not intended to be a simple “resume reviewer” application.

<!-- The long-term goal is to design a scalable AI-powered evaluation platform that demonstrates strong capabilities in:

- Backend engineering
- AI orchestration
- Resume intelligence systems
- Agentic workflows
- Data pipelines
- Retrieval systems
- Embedding-based similarity
- Modular AI architectures
- Scalable service design -->

<!-- The project will evolve incrementally from a lightweight in-memory backend into a production-grade extensible AI platform.

---

# 2. Core Functional Requirements

The system should support the following capabilities:

## Resume Upload
Users can upload resumes in PDF format.

## Resume Parsing
The backend extracts:
- raw text
- sections
- skills
- experience
- education
- technologies
- keywords

## AI Evaluation
The system evaluates:
- strengths
- weaknesses
- ATS friendliness
- missing skills
- resume quality
- readability
- career positioning

## JD Comparison
Users can upload a Job Description (JD) and receive:
- match percentage
- missing skills
- role alignment
- improvement suggestions

## Peer Benchmarking
The system compares users against developers with:
- similar YOE
- similar tech stack
- similar target role

This later evolves into embedding-driven similarity systems. -->

---

<!-- # 3. Engineering Philosophy

The project is intentionally designed as:

```text
AI-first backend architecture
```

rather than:

```text
Traditional CRUD application
```

The emphasis is on:
- modular AI pipelines
- extensibility
- replaceable infrastructure
- scalable orchestration
- clean service boundaries
- production-style backend design

The system should demonstrate engineering maturity rather than framework complexity. -->

<!-- --- -->

<!-- # 4. Development Strategy

The platform will be developed in stages.

The goal is to avoid premature complexity and focus first on building a strong AI evaluation pipeline.

--- -->

<!-- # 5. Phase 0 Goals

Phase 0 focuses on validating the core architecture and AI workflow.

The system will:
- run locally
- use in-memory session storage
- avoid databases initially
- avoid frontend development initially
- prioritize backend structure and AI orchestration

The primary objective is to validate the end-to-end resume evaluation pipeline.

--- -->

# 2. Why FastAPI Instead of Django

The backend uses FastAPI because the system is fundamentally:

- API-centric
- async-oriented
- AI-workflow driven
- orchestration-heavy

rather than:
- database-centric
- admin-panel centric
- CRUD-heavy

FastAPI better supports:
- asynchronous processing
- AI SDK integration
- streaming
- concurrent workloads
- lightweight service architecture

The decision is architectural rather than preference-based.

---

# 3. Initial Architecture

The initial architecture intentionally remains lightweight.

```text
Client
   ↓
FastAPI API Layer
   ↓
Resume Processing Pipeline
   ↓
In-Memory Session Store
```

This allows rapid iteration while preserving clean architectural boundaries.

---

<!-- # 4. Architectural Principles

## 4.1 Modular Design -->

Each component should be independently replaceable.

Example:

Today:
```text
InMemorySessionRepository
```

Later:
```text
PostgresSessionRepository
RedisSessionRepository
VectorRepository
```

without modifying core logic.

---

<!-- ## 8.2 Separation of Concerns

The system separates:
- API handling
- business orchestration
- AI logic
- parsing logic
- storage
- domain models

This ensures maintainability and scalability.

--- -->

<!-- ## 8.3 Replaceable AI Providers

LLM providers should be abstracted behind interfaces.

Example:
- OpenAI
- Ollama
- Claude
- Local models

should be swappable without affecting evaluators.

---

## 8.4 Deterministic + AI Hybrid System

The project intentionally avoids relying entirely on LLMs.

Instead:
- deterministic parsers
- regex extractors
- structured analyzers

are combined with AI reasoning.

This improves:
- reliability
- explainability
- scalability
- cost efficiency

---

# 9. Phase 0 Project Structure

```text
backend/
│
├── app/
│   ├── api/
│   ├── core/
│   ├── services/
│   ├── ai/
│   ├── storage/
│   ├── models/
│   ├── schemas/
│   ├── utils/
│   └── tests/
│
├── uploads/
│
├── requirements.txt
├── README.md
└── run.py
```

--- -->

<!-- # 10. AI Pipeline Design

The system initially follows a deterministic pipeline architecture.

```text
Resume Upload
      ↓
PDF Extraction
      ↓
Section Parsing
      ↓
Skill Extraction
      ↓
Resume Analysis
      ↓
JD Matching
      ↓
Feedback Generation
```

This design is:
- debuggable
- extensible
- testable
- production-friendly

---

# 11. Future Evolution

The architecture is intentionally designed for future evolution.

Future additions may include:

## Persistent Storage
- PostgreSQL
- Redis
- S3-compatible storage

## Vector Search
- pgvector
- Pinecone
- Qdrant

## Background Workers
- Celery
- Redis Queue
- Kafka

## Agentic Systems
- recruiter agents
- ATS agents
- hiring-manager evaluators
- career-coach agents

## Observability
- metrics
- tracing
- token tracking
- prompt versioning

## Deployment
- Docker
- Kubernetes
- cloud-native hosting

---

# 12. Long-Term Vision

The long-term vision is to evolve the platform into:

```text
AI-native developer career intelligence infrastructure
```

rather than a standalone resume review tool.

Potential future capabilities include:
- career trajectory analysis
- interview preparation
- GitHub profile analysis
- portfolio evaluation
- recruiter simulation
- personalized learning roadmaps
- salary intelligence
- developer benchmarking systems

---

# 13. Initial MVP Scope

The first MVP should only solve:

1. Resume upload
2. Resume parsing
3. AI evaluation
4. JD comparison
5. Structured feedback generation

Everything else should evolve incrementally.

---

# 14. Primary Technical Goal

The primary technical goal of this project is to demonstrate:

- backend architectural maturity
- scalable AI system design
- modular service composition
- production-oriented engineering thinking
- extensible AI orchestration patterns

rather than simply integrating LLM APIs.

---

# 15. Guiding Principle

The project should prioritize:

```text
Clean Architecture > Maximum Technologies
```

The objective is not to use the largest number of frameworks.

The objective is to build a system that:
- scales cleanly
- evolves naturally
- demonstrates engineering depth
- supports future AI expansion
- remains maintainable -->