# GridPulse AI

GridPulse is a zero-cost, portfolio-grade MVP for multimodal infrastructure-incident triage. It combines field reports, photographs, public hazard data, equipment manuals, and a bounded agent workflow to produce evidence-backed incident briefs for human review.

## MVP promise

Given an incident location, description, and optional photograph or voice note, GridPulse will:

1. correlate nearby weather and earthquake events;
2. retrieve relevant maintenance-manual evidence;
3. assemble typed observations into an incident evidence record;
4. rank plausible causes with supporting and contradicting evidence;
5. abstain when evidence is insufficient; and
6. require human approval before a brief is marked actionable.

GridPulse is a portfolio demonstration. It is not a safety-certified system and must not control infrastructure or replace approved utility procedures.

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

The detailed phase plan and review gates live in [docs/roadmap.md](docs/roadmap.md).

Initial verification (dependency-free smoke and domain tests):

```bash
python -m unittest discover -s tests -v
```

Optional dashboard:

```bash
pip install -e ".[app]"
streamlit run app.py
```

Secrets belong in `.env` or the deployment platform's secret manager. Never commit live API keys.
