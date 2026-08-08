# GridPulse Three-Day MVP Roadmap

## Working agreement

Each phase follows the same loop:

1. The AI implements the scoped milestone.
2. Automated checks run locally.
3. The user reviews the visible behavior and approves the milestone.
4. The user creates the suggested Git commit.
5. Work advances to the next phase.

No phase requires paid infrastructure. If a free API is unavailable, saved fixtures keep development and the demo deterministic.

## Day 1 — Foundation, data, and retrieval

### Phase 1: Repository foundation

**AI builds**

- Repository structure and Python package
- Zero-cost architecture decision record
- Environment-variable template with no secrets
- Test and formatting configuration
- Milestone roadmap and acceptance gates

**User provides or reviews**

- Confirm the project name and zero-cost scope
- Confirm that public and synthetic data are acceptable
- Review the repository layout
- Create a GitHub repository when ready to publish

**Exit gate**

- Package imports successfully
- Smoke test passes
- No secrets are tracked
- User approves the roadmap

**Suggested commit**

```text
chore: scaffold GridPulse MVP and delivery roadmap
```

### Phase 2: Domain model, configuration, and fixtures

**AI builds**

- Typed models for incidents, assets, observations, evidence, and hypotheses
- Configuration loader and safe demo mode
- Synthetic assets and incident fixtures
- Initial persistence interfaces and schema
- Unit tests for validation rules

**User provides or reviews**

- Review three example incident scenarios
- Approve the fields displayed in the final incident brief
- Optionally obtain the free EIA and FIRMS keys

**Exit gate**

- Fixtures validate against typed schemas
- Invalid or incomplete incidents fail clearly
- Demo mode works without external credentials

**Suggested commit**

```text
feat: add typed incident domain and demo fixtures
```

### Phase 3: Public hazard APIs and correlation

**AI builds**

- NWS alerts and forecast client
- USGS earthquake-feed client
- Cached API fixtures and retry policies
- Geographic and temporal incident correlation
- Tests for relevant, stale, and unrelated events

**User provides or reviews**

- Choose the primary demo region
- Review one correlated incident timeline
- Confirm that cached public data may be committed as test fixtures

**Exit gate**

- Live clients work when network is available
- Fixture mode is deterministic
- Irrelevant or stale events are rejected

**Suggested commit**

```text
feat: correlate incidents with public hazard feeds
```

### Phase 4: Maintenance-manual RAG

**AI builds**

- Document ingestion and chunk metadata
- Local embeddings and reranking
- Hybrid lexical and semantic retrieval
- Page-level citations
- Retrieval benchmark and Recall@K measurement

**User provides or reviews**

- Approve a public manual or let the AI select one
- Review retrieved passages for two sample questions
- Approve the citation format

**Exit gate**

- Questions retrieve relevant evidence
- Citations resolve to a source and page
- Retrieval evaluation runs locally

**Suggested commit**

```text
feat: implement cited hybrid RAG for maintenance manuals
```

## Day 2 — Multimodal workflow and product experience

### Phase 5: Multimodal processing and LangGraph workflow

**AI builds**

- Image and voice-processing adapters
- Local or free-tier fallbacks
- LangGraph investigation state and nodes
- Cause ranking, evidence verification, and abstention
- Checkpoint-ready human-review interrupt

**User provides or reviews**

- Add free Gemini and Hugging Face credentials locally, if available
- Approve sample image and voice-note inputs
- Review one complete agent trace

**Exit gate**

- A sample incident completes end to end
- Every material claim references evidence
- Weak evidence produces abstention
- Provider failure falls back safely

**Suggested commit**

```text
feat: orchestrate multimodal incident investigation
```

### Phase 6: Streamlit dashboard and approval flow

**AI builds**

- Incident submission and upload interface
- Map and event timeline
- Evidence, hypotheses, citations, and confidence display
- Approve, edit, reject, and request-evidence controls
- Demo scenarios for portfolio reviewers

**User provides or reviews**

- Review layout and terminology
- Choose the strongest default demo scenario
- Approve the final report structure

**Exit gate**

- A new user can complete the demo without instructions
- Approval state persists
- Safety boundary is visible

**Suggested commit**

```text
feat: add incident review dashboard and approval flow
```

## Day 3 — Evaluation, deployment, and portfolio polish

### Phase 7: Evaluation, safety, observability, and CI

**AI builds**

- Versioned evaluation dataset
- Retrieval, citation, abstention, and trajectory evaluators
- Prompt-injection and contradictory-evidence tests
- Optional LangSmith tracing
- GitHub Actions quality and evaluation gates
- Markdown evaluation report with measured results

**User provides or reviews**

- Review a sample of gold labels
- Approve metric thresholds
- Add a free LangSmith key locally if hosted traces are desired

**Exit gate**

- Tests and evaluation gates pass
- Results are measured rather than invented
- Known failures are documented

**Suggested commit**

```text
test: add AI evaluation harness and quality gates
```

### Phase 8: Free deployment and final handoff

**AI builds**

- Streamlit Community Cloud configuration
- Neon-compatible database configuration
- Deployment and rollback instructions
- README screenshots, architecture, limitations, and demo script
- Resume bullets populated only with measured metrics

**User provides or reviews**

- Connect GitHub to Streamlit Community Cloud
- Add secrets through the platform UI
- Create a free Neon project if hosted persistence is desired
- Run the final acceptance demo and approve publication

**Exit gate**

- Public demo URL loads
- Secrets are absent from Git history
- Three demo scenarios work
- README explains design, evaluation, and limitations

**Suggested commit**

```text
docs: publish GridPulse MVP deployment and portfolio results
```

## Scope protection

The following remain post-MVP extensions unless all core gates pass early:

- EIA telemetry ingestion
- NASA FIRMS integration
- TimescaleDB-specific optimizations
- Graph neural networks
- Depth estimation
- Enterprise authentication
- Autonomous dispatch or infrastructure control

