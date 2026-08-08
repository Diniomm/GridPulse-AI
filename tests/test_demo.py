import unittest

from gridpulse.demo import build_demo_workflow, demo_incident_options


class DemoCompositionTest(unittest.TestCase):
    def test_demo_workflow_has_incident_options(self) -> None:
        self.assertGreaterEqual(len(demo_incident_options()), 2)

    def test_demo_workflow_runs_without_external_keys(self) -> None:
        incident = next(iter(demo_incident_options().values()))
        result = build_demo_workflow().run(incident, image_path="storm-pole.jpg")
        self.assertTrue(result.state.report["requires_human_approval"])
        self.assertTrue(result.state.evidence)

