import tempfile
import unittest
from pathlib import Path

from dating_agent.core import (
    Store,
    TrackerError,
    add_event,
    add_funnel_snapshot,
    aggregate_metrics,
    new_case,
    review_case,
    set_status,
    transition_case,
)


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name))
        self.store.initialize()
        new_case(self.store, "Q001")

    def tearDown(self):
        self.temp.cleanup()

    def test_rejects_sensitive_text(self):
        with self.assertRaisesRegex(TrackerError, "手机号"):
            add_event(
                self.store,
                "Q001",
                event_type="message_exchange",
                summary="联系方式是 13812345678",
            )

    def test_date_plan_requires_mutual_yes_and_public_plan(self):
        transition_case(self.store, "Q001", "conversing")
        with self.assertRaisesRegex(TrackerError, "mutual-yes"):
            transition_case(self.store, "Q001", "date_planned")
        case = transition_case(
            self.store,
            "Q001",
            "date_planned",
            mutual_yes=True,
            public_plan=True,
        )
        self.assertEqual(case["stage"], "date_planned")

    def test_dating_requires_completed_date(self):
        transition_case(self.store, "Q001", "conversing")
        transition_case(
            self.store,
            "Q001",
            "date_planned",
            mutual_yes=True,
            public_plan=True,
        )
        with self.assertRaisesRegex(TrackerError, "date_completed"):
            transition_case(self.store, "Q001", "dating")
        add_event(
            self.store,
            "Q001",
            event_type="date_completed",
            summary="公开场所完成短时见面，双方各自返程",
        )
        case = transition_case(self.store, "Q001", "dating")
        self.assertEqual(case["stage"], "dating")

    def test_exclusive_requires_explicit_mutual(self):
        transition_case(self.store, "Q001", "conversing")
        transition_case(
            self.store,
            "Q001",
            "date_planned",
            mutual_yes=True,
            public_plan=True,
        )
        add_event(
            self.store,
            "Q001",
            event_type="date_completed",
            summary="完成见面",
        )
        transition_case(self.store, "Q001", "dating")
        with self.assertRaisesRegex(TrackerError, "explicit-mutual"):
            transition_case(self.store, "Q001", "exclusive")
        case = transition_case(
            self.store, "Q001", "exclusive", explicit_mutual=True
        )
        self.assertEqual(case["stage"], "exclusive")

    def test_high_risk_review_takes_priority(self):
        add_event(
            self.store,
            "Q001",
            event_type="red_flag",
            summary="对方提出投资并要求转账",
            risk="high",
        )
        case = self.store.load()["cases"]["Q001"]
        advice = review_case(case)
        self.assertEqual(len(advice), 1)
        self.assertIn("停止推进", advice[0])

    def test_low_reciprocity_trend_is_flagged(self):
        transition_case(self.store, "Q001", "conversing")
        for _ in range(3):
            add_event(
                self.store,
                "Q001",
                event_type="message_exchange",
                summary="主要由自己发起，对方只做简短回答",
                reciprocity=2,
            )
        case = self.store.load()["cases"]["Q001"]
        self.assertTrue(any("停止单方加力" in item for item in review_case(case)))

    def test_closed_case_rejects_new_event(self):
        set_status(self.store, "Q001", "closed", reason="mutual_end")
        with self.assertRaisesRegex(TrackerError, "已关闭"):
            add_event(
                self.store,
                "Q001",
                event_type="message_exchange",
                summary="不应记录",
            )

    def test_closed_case_cannot_be_reopened(self):
        set_status(self.store, "Q001", "closed", reason="mutual_end")
        with self.assertRaisesRegex(TrackerError, "不能恢复"):
            set_status(self.store, "Q001", "active")

    def test_metrics_are_aggregate_only(self):
        metrics = aggregate_metrics(self.store.load())
        self.assertEqual(metrics["case_count"], 1)
        self.assertEqual(metrics["stages"]["matched"], 1)
        self.assertNotIn("Q001", str(metrics))

    def test_funnel_metrics_include_conversion_and_efficiency(self):
        add_funnel_snapshot(
            self.store,
            "2026-09-27",
            profiles_reviewed=20,
            likes_sent=8,
            notes_sent=2,
            matches=5,
            first_replies=4,
            substantive_chats=3,
            invitations_sent=2,
            first_dates_completed=2,
            mutual_second_date_yes=1,
            minutes_spent=300,
        )
        funnel = aggregate_metrics(self.store.load())["funnel"]
        self.assertEqual(funnel["rates"]["match_rate"], 0.5)
        self.assertEqual(funnel["rates"]["mutual_second_date_rate"], 0.5)
        self.assertEqual(
            funnel["rates"]["mutual_second_dates_per_10_hours"], 2.0
        )

    def test_funnel_rejects_duplicate_date(self):
        add_funnel_snapshot(self.store, "2026-09-27", profiles_reviewed=1)
        with self.assertRaisesRegex(TrackerError, "已存在"):
            add_funnel_snapshot(self.store, "2026-09-27", profiles_reviewed=1)

    def test_funnel_rejects_invalid_date_and_negative_counts(self):
        with self.assertRaisesRegex(TrackerError, "YYYY-MM-DD"):
            add_funnel_snapshot(self.store, "20260927", profiles_reviewed=1)
        with self.assertRaisesRegex(TrackerError, "非负整数"):
            add_funnel_snapshot(self.store, "2026-09-27", profiles_reviewed=-1)

    def test_old_store_without_funnel_is_backward_compatible(self):
        self.store.save({"version": 1, "cases": {}})
        loaded = self.store.load()
        self.assertEqual(loaded["funnel"], [])


if __name__ == "__main__":
    unittest.main()
