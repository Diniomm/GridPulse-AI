import unittest

from gridpulse.evaluation import render_markdown, run_evaluation


class EvaluationHarnessTest(unittest.TestCase):
    def test_local_evaluation_passes_all_quality_and_safety_gates(self) -> None:
        summary = run_evaluation()
        self.assertTrue(summary.passed, summary.failures)
        self.assertEqual(summary.metrics["retrieval_recall_at_3"], 1.0)
        self.assertEqual(summary.metrics["citation_coverage"], 1.0)
        self.assertEqual(summary.metrics["abstention_accuracy"], 1.0)
        self.assertEqual(summary.metrics["prompt_injection_safety"], 1.0)
        self.assertEqual(summary.metrics["contradictory_evidence_safety"], 1.0)

    def test_report_is_portfolio_readable(self) -> None:
        report = render_markdown(run_evaluation())
        self.assertIn("GridPulse Evaluation Report", report)
        self.assertIn("retrieval_recall_at_3", report)
        self.assertIn("**Overall:** PASS", report)
