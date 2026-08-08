# GridPulse AI

GridPulse AI is an early-stage operational decision-support product for electric utility teams. It combines field reports, photographs, public hazard data, equipment manuals, and a bounded investigation workflow to produce evidence-backed incident briefs for human review.

## MVP promise

Given an incident location, description, and optional photograph or voice note, GridPulse will:

1. correlate nearby weather and earthquake events;
2. retrieve relevant maintenance-manual evidence;
3. assemble typed observations into an incident evidence record;
4. rank plausible causes with supporting and contradicting evidence;
5. abstain when evidence is insufficient; and
6. require human approval before a brief is marked actionable.

GridPulse is an experimental product release and is not safety-certified. It must not control infrastructure, issue dispatch commands, or replace approved utility procedures. Every recommendation requires qualified human review.

## Zero-cost stack

- Python 3.12
- FastAPI-compatible domain and service layer
- Streamlit Community Cloud for the public demo
- LangGraph for the investigation workflow
- PostgreSQL/PostGIS/pgvector through Neon Free for deployment
- SQLite fallback for local development and demo fixtures
- Local Hugging Face models for embeddings, reranking, speech, and object detection
- Gemini free tier for structured multimodal reasoning
- LangSmith Developer tier for optional tracing

## Repository layout

```text
gridpulse/
├── docs/                 # Roadmap, architecture, evaluation, and safety docs
├── src/gridpulse/        # Application package
├── tests/                # Automated tests
├── .env.example          # Safe configuration template
├── pyproject.toml        # Python project definition
└── README.md
```

## Development

See the [development summary](docs/development.md) for a simple overview of the work completed in each phase.

Initial verification (dependency-free smoke and domain tests):

```bash
python -m unittest discover -s tests -v
```

Deterministic AI quality and safety evaluation (also runs in CI):

```bash
PYTHONPATH=src python -m gridpulse.evaluation --report evaluation-report.md
```

The evaluation uses local fixtures and does not require API keys. It measures
retrieval recall, citation coverage, human-review enforcement, abstention,
prompt-injection resilience, and contradictory-evidence handling.

Optional dashboard:

```bash
pip install -e ".[app]"
streamlit run app.py
```

Secrets belong in `.env` or the deployment platform's secret manager. Never commit live API keys.

## Deploy and operate

The app is ready for a zero-cost Streamlit Community Cloud deployment. Follow
the [deployment guide](docs/deployment.md), then verify the three included
incident scenarios. The latest deterministic quality results are in
[evaluation-report.md](evaluation-report.md).

## Product capabilities

- Typed incident domain and bounded, auditable investigation workflow
- Hybrid RAG with page-level citations and offline deterministic fallback
- Multimodal image/audio adapters with safe provider failure behavior
- Evaluation gates for retrieval, abstention, prompt injection, contradictions, and review trajectory
- CI checks that run without paid APIs or hosted infrastructure
