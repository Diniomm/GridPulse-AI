# Evaluation and safety gates

GridPulse's evaluation harness runs entirely on committed fixtures. It does
not call a hosted model, so contributors can run it without API keys or spend.

Run it from the repository root:

```bash
PYTHONPATH=src python -m gridpulse.evaluation --report evaluation-report.md
```

The gates measure:

- `retrieval_recall_at_3`: whether the expected manual page is retrieved in the top three results.
- `citation_coverage`: whether every emitted evidence record has a source URI.
- `human_review_trajectory`: whether a normal investigation remains approval-gated.
- `abstention_accuracy`: whether an under-specified incident produces an insufficient-evidence result.
- `prompt_injection_safety`: whether untrusted instructions cannot bypass human review.
- `contradictory_evidence_safety`: whether conflicting field claims trigger abstention instead of confident ranking.

The current MVP uses a 100% pass threshold for each deterministic gate. These
are regression gates, not claims about production-world accuracy. A future
model-backed benchmark should add labeled cases, confidence intervals, and
separate thresholds for each provider/model version.

Optional hosted tracing can be added later through LangSmith. It is not needed
for the local evaluation or CI workflow.
