# AI Personalized Medicine

An educational project exploring how intelligent agents and modern diagnostics can enable personalized healthcare — from risk assessment to treatment insights.

> **Disclaimer:** This is a learning project, not a medical device or clinical tool. Nothing here constitutes medical advice. Do not use outputs for real health decisions without consulting a qualified healthcare provider.

---

## What This Project Is About

Personalized medicine tailors prevention, diagnosis, and treatment to an individual's biology, history, and lifestyle — rather than applying one-size-fits-all protocols.

Three forces are making this practical at scale:

1. **Abundant personal health data** — genome scans, lab panels, EHR records, and wearables generate rich, longitudinal signals about each person.
2. **Plummeting diagnostic costs** — genome sequencing has dropped faster than Moore's law; new tests enable earlier detection of disease markers.
3. **Personalized therapies** — mRNA and other delivery vectors make patient-specific treatments increasingly feasible, with regulatory pathways evolving.

**Intelligent agents** sit at the center of this shift. Instead of static dashboards, an agent can:

- Ingest heterogeneous health data (PDF lab reports, VCF genomics files, FHIR EHR exports, CSV wearables)
- Reason over medical literature and structured knowledge bases
- Answer patient-specific questions with citations and uncertainty
- Flag risks, anomalies, and follow-up questions for clinician review

This repository is a **hands-on sandbox** to learn AI by building pieces of that ecosystem — starting simple, growing in complexity.

---

## What We're Building

A modular platform with four core capabilities, implemented incrementally:

| Module | Purpose | Learning focus |
|--------|---------|----------------|
| **Data ingestion** | Parse labs, genomics snippets, wearables CSV | Data engineering, schema design |
| **Knowledge + RAG** | Index guidelines, PubMed abstracts, drug info | Embeddings, retrieval, chunking |
| **Health agent** | Chat over *your* data with tool use | LLM agents, prompt design, safety |
| **Risk & insights** | Simple ML baselines + agent explanations | Classical ML + interpretability |

### High-level architecture

```mermaid
flowchart TB
    subgraph inputs [Health Data Inputs]
        Labs[Labs and diagnostics]
        Genomics[Genomics VCF or summary]
        Wearables[Wearables CSV]
        EHR[EHR FHIR export]
    end

    subgraph backend [Backend]
        Ingest[Ingestion and normalization]
        Store[(PostgreSQL plus object storage)]
        Vector[(Vector store)]
        Agent[AI health agent]
        ML[Risk scoring models]
    end

    subgraph outputs [Outputs]
        Chat[Conversational insights]
        Reports[Structured health summaries]
        Alerts[Risk flags with citations]
    end

    inputs --> Ingest --> Store
    Ingest --> Vector
    Store --> Agent
    Vector --> Agent
    Store --> ML
    Agent --> Chat
    Agent --> Reports
    ML --> Alerts
    Agent --> Alerts
```

---

## Recommended Tech Stack (Learning-Oriented)

Python-first — best ecosystem for AI/ML learning, with a thin web layer for interaction.

### Core

| Layer | Choice | Why |
|-------|--------|-----|
| **Language** | Python 3.11+ | Dominant ML/AI ecosystem |
| **API** | [FastAPI](https://fastapi.tiangolo.com/) | Async, typed, great docs, easy to learn |
| **Agent framework** | [LangGraph](https://langchain-ai.github.io/langgraph/) or [Pydantic AI](https://ai.pydantic.dev/) | Tool-calling agents with explicit control flow |
| **LLM** | OpenAI / Anthropic API (or Ollama locally) | Start with APIs; swap to local models later |
| **Embeddings + RAG** | [ChromaDB](https://www.trychroma.com/) or pgvector | Simple local vector store; pgvector scales with Postgres |
| **Database** | PostgreSQL | Structured patient data, JSONB for flexible records |
| **ML** | scikit-learn, pandas, XGBoost | Classical ML before deep learning |
| **Frontend** | Next.js or Streamlit | Streamlit for fast prototypes; Next.js when you want a real UI |

### Supporting tools

- **uv** or **poetry** — dependency management
- **Docker** — reproducible dev environment
- **pytest** — testing
- **Ruff** — linting and formatting
- **Jupyter** — experiments and EDA

### Data sources (public, for learning)

- [1000 Genomes](https://www.internationalgenome.org/) — genomics
- [MIMIC-IV](https://physionet.org/content/mimiciv/) — de-identified EHR (requires credentialing)
- [OpenSNP](https://opensnp.org/) — consumer genomics
- Synthetic patient generators — safest starting point

---

## Project Structure (Target)

```
ai-personalized-medicine/
├── README.MD
├── pyproject.toml
├── docker-compose.yml
├── backend/
│   ├── api/              # FastAPI routes
│   ├── agents/           # Health agent + tools
│   ├── ingestion/        # Parsers for labs, VCF, CSV
│   ├── ml/               # Risk models
│   ├── rag/              # Document indexing and retrieval
│   └── models/           # Pydantic schemas
├── frontend/             # Streamlit or Next.js app
├── data/
│   ├── synthetic/        # Fake patients for dev
│   └── knowledge/        # Guidelines, sample literature
├── notebooks/            # Exploratory analysis
└── tests/
```

---

## Learning Roadmap

Build in phases. Each phase teaches distinct AI skills.

### Phase 1 — Foundation (Week 1–2)
- [ ] Set up Python project, FastAPI hello-world, Docker Compose
- [ ] Define patient schema (demographics, labs, variants, vitals)
- [ ] Generate 10–50 synthetic patient records
- [ ] Build a simple REST API: upload CSV → store in Postgres

**You learn:** API design, data modeling, SQL

### Phase 2 — RAG over medical knowledge (Week 3–4)
- [ ] Chunk and embed sample guidelines (e.g., CDC, NIH fact sheets)
- [ ] Implement semantic search: "What does elevated LDL mean?"
- [ ] Add citation links in responses

**You learn:** Embeddings, chunking strategies, retrieval quality

### Phase 3 — Health agent (Week 5–7)
- [ ] Agent with tools: `get_patient_labs`, `search_knowledge`, `calculate_bmi`
- [ ] Multi-turn chat grounded in one synthetic patient's data
- [ ] Guardrails: refuse diagnosis, always cite sources, express uncertainty

**You learn:** Tool use, agent orchestration, prompt engineering, safety

### Phase 4 — Risk scoring (Week 8–9)
- [ ] Train a simple classifier (e.g., diabetes risk from labs + demographics)
- [ ] Have the agent *explain* model output in plain language
- [ ] Compare ML prediction vs. agent-only reasoning

**You learn:** Feature engineering, model evaluation, AI + ML hybrid systems

### Phase 5 — Polish (Week 10+)
- [ ] Streamlit or Next.js UI
- [ ] PDF lab report parser
- [ ] Evaluation harness (golden Q&A pairs)
- [ ] Write-up: what worked, what didn't

**You learn:** Full-stack integration, evaluation, product thinking

---

## Getting Started

### Prerequisites

- Python 3.11+
- Docker (optional but recommended)
- An LLM API key (OpenAI, Anthropic) or [Ollama](https://ollama.com/) for local models

### Quick start (once scaffold exists)

```bash
# Clone the repo
git clone https://github.com/KarthikAmaravadi1234/ai-personalized-medicine.git
cd ai-personalized-medicine

# Install dependencies
uv sync   # or: pip install -e .

# Start services
docker compose up -d

# Run the API
uvicorn backend.api.main:app --reload

# Run the UI (Streamlit)
streamlit run frontend/app.py
```

---

## Key Design Principles

1. **Synthetic data first** — never commit real PHI; use fakes until you understand privacy (HIPAA) requirements.
2. **Citations over confidence** — every health claim should trace to a source or patient record field.
3. **Human in the loop** — agents suggest; clinicians (or you, in dev) validate.
4. **Modular agents** — separate ingestion, retrieval, reasoning, and reporting into testable units.
5. **Evaluate continuously** — maintain a small set of question/answer pairs and score retrieval + response quality.

---

## Safety and Ethics

- Do **not** deploy this for real patients without legal, clinical, and security review.
- Be explicit that outputs are **informational**, not diagnostic.
- Log agent reasoning for auditability.
- Understand bias in training data and knowledge bases.
- Read [FDA guidance on AI/ML in SaMD](https://www.fda.gov/medical-devices/software-medical-device-samd/artificial-intelligence-and-machine-learning-software-medical-device) if you go beyond learning.

---

## Inspiration

This project explores the thesis that **abundant personal data + intelligent agents + cheaper diagnostics and therapies** will reshape care delivery — enabling patients to better understand risk and access personalized treatments. The startup ecosystem will span ingestion, interpretation, trial matching, therapy design, and care coordination. This repo is one learner's entry point into that world.

---

## License

TBD — add a license before open-sourcing (MIT recommended for learning projects).

## Contributing

This is primarily a personal learning project. Issues and ideas welcome.
