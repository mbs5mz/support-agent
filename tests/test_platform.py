import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_workspace import AOPS, duet_assist, platform_summary, select_aop


class PlatformDemoTests(unittest.TestCase):
    def test_catalog_has_runnable_bookly_workflows(self):
        summary = platform_summary()
        self.assertEqual(len(summary["aops"]), 4)
        self.assertTrue(all(aop["steps"] and aop["entry_conditions"] for aop in AOPS))
        self.assertEqual(summary["watchtower"]["metrics"][0]["label"], "Deflection rate")
        self.assertEqual(len(summary["resources"]["tools"]), 4)

    def test_trace_selects_refund_aop_from_tool_call(self):
        trace = select_aop(
            [{"role": "user", "content": "yes"}],
            [{"tool": "create_refund_request", "result": {"status": "Submitted"}}],
        )
        self.assertEqual(trace["aop_id"], "refund-review")
        self.assertIn("Called create_refund_request", trace["events"][1]["label"])

    def test_duet_returns_reviewable_simulation_artifact(self):
        result = duet_assist("Test this workflow for edge cases", "book-return")
        self.assertEqual(result["artifact"]["kind"], "Simulation suite")
        self.assertEqual(len(result["artifact"]["items"]), 4)

    def test_watchtower_periods_show_recent_improvement(self):
        periods = platform_summary()["watchtower"]["periods"]
        self.assertGreaterEqual(float(periods["90"]["metrics"][0]["value"].rstrip("%")), 85)
        self.assertLessEqual(float(periods["7"]["metrics"][0]["value"].rstrip("%")), 95)
        self.assertGreater(float(periods["7"]["metrics"][0]["value"].rstrip("%")), float(periods["30"]["metrics"][0]["value"].rstrip("%")))
        self.assertGreater(float(periods["30"]["metrics"][0]["value"].rstrip("%")), float(periods["90"]["metrics"][0]["value"].rstrip("%")))
        self.assertGreater(float(periods["7"]["metrics"][1]["value"].rstrip("%")), float(periods["90"]["metrics"][1]["value"].rstrip("%")))
        self.assertLess(float(periods["7"]["metrics"][3]["value"].rstrip("%")), float(periods["90"]["metrics"][3]["value"].rstrip("%")))

    def test_watchtower_headlines_are_period_averages_and_windows_roll_up(self):
        periods = platform_summary()["watchtower"]["periods"]
        for key in ("7", "30", "90"):
            for metric_index, field in ((0, "deflection"), (1, "resolution")):
                headline = float(periods[key]["metrics"][metric_index]["value"].rstrip("%"))
                plotted_average = sum(point[field] for point in periods[key]["trend"]) / len(periods[key]["trend"])
                self.assertEqual(headline, plotted_average)
        self.assertEqual(periods["30"]["trend"][-1]["deflection"], 94)
        self.assertEqual(periods["30"]["trend"][-1]["resolution"], 96)
        self.assertEqual(periods["90"]["trend"][-1]["deflection"], 90)
        self.assertEqual(periods["90"]["trend"][-1]["resolution"], 92)


if __name__ == "__main__":
    unittest.main()
