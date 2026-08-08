import unittest

from gridpulse.rag import HybridIndex, ManualIngestor


MANUAL = """# Manual

## Page 1

Scene safety requires a safe perimeter. Treat a downed conductor as energized until qualified personnel verify isolation.

## Page 2

For a leaning wooden pole, inspect the foundation, guy wires, crossarm attachment points, insulators, conductor clearance, and nearby vegetation.

## Page 3

For a split crossarm after high winds, keep the line out of service until a qualified crew evaluates conductor tension and hardware.
"""


class RagTest(unittest.TestCase):
    def setUp(self) -> None:
        chunks = ManualIngestor(max_chars=500).ingest_text(
            MANUAL,
            document_id="manual",
            title="Storm Manual",
            source_uri="storm-manual.md",
        )
        self.index = HybridIndex()
        self.index.add(chunks)

    def test_ingestor_preserves_page_metadata(self) -> None:
        results = self.index.retrieve("crossarm high winds", top_k=1)
        self.assertEqual(results[0].chunk.page, 3)
        self.assertEqual(results[0].chunk.source_uri, "storm-manual.md")

    def test_retrieval_returns_citation(self) -> None:
        result = self.index.retrieve("safe perimeter downed conductor", top_k=1)[0]
        self.assertIn("Storm Manual, p. 1", result.citation())
        self.assertGreater(result.score, 0)

    def test_context_contains_source_and_text(self) -> None:
        context = self.index.context("inspect pole foundation", top_k=1)
        self.assertIn("foundation", context)
        self.assertIn("Source:", context)

    def test_empty_query_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.index.retrieve("   ")

    def test_metadata_filter_can_narrow_results(self) -> None:
        chunks = ManualIngestor().ingest_text(
            "## Page 4\n\nOnly the fourth page.",
            document_id="other",
            title="Other Manual",
            source_uri="other.md",
        )
        self.index.add(chunks)
        results = self.index.retrieve("page", metadata={"section": "missing"})
        self.assertEqual(results, ())

