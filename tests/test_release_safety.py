"""Release regressions for safe recommendations, approvals, and audit persistence.

All data and lender operations in these tests are synthetic and local. Run with:
    python3 -m unittest discover -s tests -p 'test_release_safety.py' -v
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ledgerly import financing
from ledgerly.agent import Agent, TOOLS, resolve
from ledgerly.ingest import load_csv
from ledgerly.models import Business
from ledgerly.sandbox import SandboxEnv
from ledgerly.security import AuditLog, Consent, Policy, Tier


class FinancingRecommendationSafety(unittest.TestCase):
    def test_recommendation_is_an_affordable_offer_covering_the_whole_gap(self):
        result = financing.match(880_000, 83, 2_800_000, 77_000)
        offer = result["recommended_offer"]
        self.assertIsNotNone(offer)
        self.assertIn(offer, result["offers"])
        self.assertTrue(offer["affordable"])
        self.assertTrue(offer["covers_need"])
        self.assertGreaterEqual(offer["amount"], result["need"])

    def test_eligible_but_unaffordable_offers_are_visible_and_not_recommended(self):
        result = financing.match(880_000, 83, 2_800_000, 1)
        self.assertEqual(
            {offer["product_id"] for offer in result["offers"]},
            {"FIN-CF", "MFB-GRP", "SUP-NET30", "MM-OD"},
        )
        self.assertTrue(all(not offer["affordable"] for offer in result["offers"]))
        self.assertIsNone(result["recommended_offer"])
        self.assertTrue(result["note"].strip())

    def test_affordable_partial_offers_are_not_recommended(self):
        result = financing.match(10_000_000, 83, 2_800_000, 10_000_000)
        self.assertTrue(result["offers"])
        self.assertTrue(all(offer["affordable"] for offer in result["offers"]))
        self.assertTrue(all(not offer["covers_need"] for offer in result["offers"]))
        self.assertIsNone(result["recommended_offer"])
        self.assertTrue(result["note"].strip())

    def test_cheaper_partial_offer_cannot_displace_a_full_cover_offer(self):
        products = [
            financing.Product("PARTIAL", "Cheap partial", 0, 0, 0, 10, 1, 50_000),
            financing.Product("FULL", "Full cover", 0, 0.10, 0, 10, 1),
        ]
        with patch.object(financing, "CATALOGUE", products):
            result = financing.match(100_000, 80, 1_000_000, 100_000)
        self.assertEqual(len(result["offers"]), 2)
        self.assertEqual(result["recommended_offer"]["product_id"], "FULL")

    def test_affordability_boundary_uses_unrounded_repayment(self):
        product = financing.Product("BOUNDARY", "Boundary loan", 0, 0, 0, 4, 1)
        with patch.object(financing, "CATALOGUE", [product]):
            exact = financing.match(100_000, 80, 1_000_000, 25_000)
            below = financing.match(100_000, 80, 1_000_000, 24_999.99)
        self.assertIsNotNone(exact["recommended_offer"])
        self.assertIsNone(below["recommended_offer"])
        self.assertFalse(below["offers"][0]["affordable"])

    def test_rounding_a_partial_amount_does_not_make_it_full_cover(self):
        product = financing.Product("PARTIAL", "Just short", 0, 0, 0, 4, 1, 99_999.99)
        with patch.object(financing, "CATALOGUE", [product]):
            result = financing.match(100_000, 80, 1_000_000, 100_000)
        self.assertIsNone(result["recommended_offer"])
        self.assertFalse(result["offers"][0]["covers_need"])

    def test_recommendation_covers_rounded_request(self):
        result = financing.match(880_001, 83, 2_800_000, 77_000)
        self.assertEqual(result["need"], 890_000)
        self.assertGreaterEqual(result["recommended_offer"]["amount"], 890_000)

    def test_no_need_or_no_eligible_product_has_no_recommendation(self):
        for need, score in [(0, 90), (100_000, 0)]:
            with self.subTest(need=need, score=score):
                result = financing.match(need, score, 1_000_000, 100_000)
                self.assertEqual(result["offers"], [])
                self.assertIsNone(result["recommended_offer"])
                self.assertTrue(result["note"].strip())

    def test_cost_rate_is_named_for_the_simple_annualized_calculation(self):
        product = financing.Product("RATE", "Illustrative loan", 0, 0.36, 0.02, 12, 1)
        offer = financing.evaluate(product, 100_000, 100_000)
        expected = round(0.36 + 0.02 * 52 / 12, 3)
        self.assertEqual(offer["annualized_cost_rate"], expected)
        self.assertNotIn("effective_apr", offer)

    def test_matching_rejects_nonfinite_and_negative_input_fields(self):
        valid = [100_000, 80, 1_000_000, 100_000]
        for field in range(len(valid)):
            for value in [-1, float("nan"), float("inf"), float("-inf")]:
                with self.subTest(field=field, value=value):
                    values = valid.copy()
                    values[field] = value
                    with self.assertRaises(ValueError):
                        financing.match(*values)

    def test_evaluation_rejects_zero_negative_and_nonfinite_amounts(self):
        product = financing.Product("RATE", "Illustrative loan", 0, 0.36, 0.02, 12, 1)
        for amount in [0, -1, float("nan"), float("inf"), float("-inf")]:
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                financing.evaluate(product, amount, 100_000)


class AgentReleaseSafety(unittest.TestCase):
    APPLY_GOAL = "Apply for the best financing option."
    FUND_GOAL = "Apply for financing and disburse the approved funds in the sandbox."
    OPENING = 650_000

    @classmethod
    def setUpClass(cls):
        cls.txns, _ = load_csv(str(ROOT / "data" / "sample_trader.csv"))

    def agent(self, **kwargs):
        return Agent(
            Business("Release test trader", "retail", "Lagos"),
            kwargs.pop("txns", self.txns),
            kwargs.pop("opening_balance", self.OPENING),
            Consent(frozenset({"credit_assessment", "share_with_lender"})),
            **kwargs,
        )

    def money_ops(self, agent):
        return [op for op in agent.env.ops if op["op"] in {"lender_application", "disbursement"}]

    def test_disbursement_is_a_money_tool_with_submission_dependency(self):
        self.assertIn("disburse", TOOLS)
        tier, dependencies = TOOLS["disburse"]
        self.assertEqual(tier, Tier.ACT_MONEY)
        self.assertIn("submit", dependencies)
        plan = resolve(["disburse"])
        for before, after in [("match", "pack"), ("pack", "submit"), ("submit", "disburse")]:
            self.assertLess(plan.index(before), plan.index(after))

    def test_generic_application_does_not_plan_disbursement(self):
        plan = self.agent().plan(self.APPLY_GOAL)
        self.assertIn("submit", plan)
        self.assertNotIn("disburse", plan)

    def test_explicit_disburse_and_fund_sandbox_goals_plan_disbursement(self):
        for goal in [self.FUND_GOAL, "Fund the approved financing in the sandbox."]:
            with self.subTest(goal=goal):
                plan = self.agent().plan(goal)
                self.assertIn("disburse", plan)
                self.assertLess(plan.index("submit"), plan.index("disburse"))

    def test_approved_application_submits_without_moving_money(self):
        approvals = []

        def approve(tool, preview):
            approvals.append(tool)
            self.assertEqual(preview["tool"], tool)
            self.assertIsNotNone(preview["offer"])
            return True

        agent = self.agent(approver=approve)
        report = agent.run(self.APPLY_GOAL, requested_amount=100_000)
        self.assertEqual(report["status"], "complete")
        self.assertEqual(approvals, ["submit"])
        self.assertEqual(agent.env.balance, self.OPENING)
        self.assertEqual([op["op"] for op in self.money_ops(agent)], ["lender_application"])

    def test_explicit_disbursement_requires_two_independent_approvals(self):
        approvals = []
        agent = self.agent(approver=lambda tool, preview: approvals.append(tool) or True)
        report = agent.run(self.FUND_GOAL, requested_amount=100_000)
        self.assertEqual(report["status"], "complete")
        self.assertEqual(approvals, ["submit", "disburse"])
        self.assertEqual(agent.env.balance, self.OPENING + 100_000)
        self.assertEqual([op["op"] for op in self.money_ops(agent)], ["lender_application", "disbursement"])
        self.assertTrue(report["audit_chain_valid"])

    def test_submission_approval_does_not_authorize_disbursement(self):
        approvals = []

        def approve_submission_only(tool, preview):
            approvals.append(tool)
            return tool == "submit"

        agent = self.agent(approver=approve_submission_only)
        report = agent.run(self.FUND_GOAL, requested_amount=100_000)
        self.assertEqual((report["status"], report["pending"]), ("pending_approval", "disburse"))
        self.assertEqual(approvals, ["submit", "disburse"])
        self.assertEqual(agent.env.balance, self.OPENING)
        self.assertEqual([op["op"] for op in self.money_ops(agent)], ["lender_application"])
        approved = [entry["detail"]["tool"] for entry in agent.audit.entries if entry["action"] == "approved"]
        self.assertEqual(approved, ["submit"])

    def test_custom_policy_cannot_disable_submission_approval(self):
        agent = self.agent(policy=Policy(approval_tiers=()))
        report = agent.run(self.FUND_GOAL, requested_amount=100_000)
        self.assertEqual((report["status"], report["pending"]), ("pending_approval", "submit"))
        self.assertEqual(self.money_ops(agent), [])
        self.assertEqual(agent.env.balance, self.OPENING)

    def test_custom_policy_cannot_disable_separate_disbursement_approval(self):
        approvals = []

        def approve_submission_only(tool, preview):
            approvals.append(tool)
            return tool == "submit"

        agent = self.agent(policy=Policy(approval_tiers=()), approver=approve_submission_only)
        report = agent.run(self.FUND_GOAL, requested_amount=100_000)
        self.assertEqual((report["status"], report["pending"]), ("pending_approval", "disburse"))
        self.assertEqual(approvals, ["submit", "disburse"])
        self.assertEqual(agent.env.balance, self.OPENING)

    def test_llm_disbursement_plan_cannot_skip_application_or_approval(self):
        agent = self.agent(llm_planner=lambda goal, tools: ["disburse", "wire_money"])
        report = agent.run(self.FUND_GOAL, requested_amount=100_000)
        self.assertNotIn("wire_money", report["plan"])
        self.assertLess(report["plan"].index("submit"), report["plan"].index("disburse"))
        self.assertEqual((report["status"], report["pending"]), ("pending_approval", "submit"))
        self.assertEqual(self.money_ops(agent), [])

    def test_repeating_an_approved_funding_run_does_not_pay_twice(self):
        agent = self.agent(approver=lambda tool, preview: True)
        first = agent.run(self.FUND_GOAL, requested_amount=100_000)
        second = agent.run(self.FUND_GOAL, requested_amount=100_000)
        self.assertEqual(first["status"], "complete")
        self.assertEqual(second["status"], "complete")
        self.assertEqual(agent.env.balance, self.OPENING + 100_000)
        self.assertEqual([op["op"] for op in self.money_ops(agent)], ["lender_application", "disbursement"])

    def test_no_suitable_offer_never_enters_a_lender_or_money_operation(self):
        cases = [
            financing.Product("TOO-COSTLY", "Unaffordable loan", 0, 0, 0, 0.1, 1),
            financing.Product("TOO-SMALL", "Partial coverage loan", 0, 0, 0, 24, 1, 50_000),
        ]
        for product in cases:
            with self.subTest(product=product.id), patch.object(financing, "CATALOGUE", [product]):
                approvals = []
                agent = self.agent(approver=lambda tool, preview: approvals.append(tool) or True)
                report = agent.run(self.FUND_GOAL, requested_amount=100_000)
                self.assertTrue(report["match"]["offers"])
                self.assertIsNone(report["match"]["recommended_offer"])
                self.assertIsNone(report["pack"]["request"])
                self.assertEqual(self.money_ops(agent), [])
                self.assertEqual(approvals, [])
                self.assertEqual(agent.env.balance, self.OPENING)
                self.assertTrue(report["match"]["note"].strip())
                self.assertIn(report["match"]["note"], report["summary"])
                self.assertNotIn("Best fit", report["summary"])

    def test_explicit_zero_request_does_not_fall_back_to_forecast_need(self):
        agent = self.agent(approver=lambda tool, preview: True)
        report = agent.run(self.FUND_GOAL, requested_amount=0)
        self.assertGreater(report["forecast"]["downside"]["need"], 0)
        self.assertEqual(report["match"]["need"], 0)
        self.assertIsNone(report["match"]["recommended_offer"])
        self.assertIsNone(report["pack"]["request"])
        self.assertEqual(self.money_ops(agent), [])
        self.assertEqual(agent.env.balance, self.OPENING)

    def test_narration_labels_simple_annualized_cost_without_claiming_apr_or_irr(self):
        report = self.agent().run("Compare financing options", requested_amount=100_000)
        text = report["summary"].lower()
        self.assertIn("simple annualized cost", text)
        self.assertNotIn("effective apr", text)
        self.assertNotIn("effective irr", text)

    def test_invalid_request_is_rejected_before_any_money_operation(self):
        for amount in [-1, float("nan"), float("inf"), float("-inf")]:
            with self.subTest(amount=amount):
                approvals = []
                agent = self.agent(approver=lambda tool, preview: approvals.append(tool) or True)
                with self.assertRaises(ValueError):
                    agent.run(self.FUND_GOAL, requested_amount=amount)
                self.assertEqual(self.money_ops(agent), [])
                self.assertEqual(approvals, [])
                self.assertEqual(agent.env.balance, self.OPENING)

    def test_invalid_opening_balance_is_rejected(self):
        for balance in [-1, float("nan"), float("inf"), float("-inf")]:
            with self.subTest(balance=balance), self.assertRaises(ValueError):
                self.agent(opening_balance=balance).run("Forecast cash flow")

    def test_empty_transaction_history_is_rejected_clearly(self):
        with self.assertRaises(ValueError):
            self.agent(txns=[]).run("Forecast cash flow")

    def test_loss_making_business_gets_a_safe_refusal_instead_of_crashing(self):
        loss_making = [replace(txn, amount=txn.amount * 2 if txn.amount < 0 else txn.amount)
                       for txn in self.txns]
        approvals = []
        agent = self.agent(txns=loss_making,
                           approver=lambda tool, preview: approvals.append(tool) or True)
        report = agent.run(self.FUND_GOAL, requested_amount=100_000)
        self.assertEqual(report["status"], "complete")
        self.assertEqual(report["passport"]["weekly_repayment_capacity"], 0)
        self.assertTrue(report["match"]["offers"])
        self.assertIsNone(report["match"]["recommended_offer"])
        self.assertIsNone(report["pack"]["request"])
        self.assertTrue(report["match"]["note"].strip())
        self.assertIn(report["match"]["note"], report["summary"])
        self.assertEqual(approvals, [])
        self.assertEqual(self.money_ops(agent), [])
        self.assertEqual(agent.env.balance, self.OPENING)
        self.assertTrue(report["audit_chain_valid"])


class SandboxRequestSafety(unittest.TestCase):
    def test_direct_invalid_amounts_cannot_create_a_fundable_application(self):
        for amount in [-1, 0, float("nan"), float("inf"), float("-inf")]:
            with self.subTest(amount=amount):
                env = SandboxEnv(1_000)
                application = env.apply("TEST", amount, 80, 40, key="invalid-amount")
                self.assertEqual(application["status"], "DECLINED")
                disbursement = env.disburse(application["ref"], key="invalid-disbursement")
                self.assertEqual(disbursement["status"], "REFUSED")
                self.assertEqual(env.balance, 1_000)


class AuditPersistenceSafety(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "audit.jsonl"

    def populated_log(self):
        audit = AuditLog(str(self.path))
        audit.record("owner", "goal", {"goal": "Compare financing"})
        audit.record("agent", "tool_ok", {"tool": "match"})
        return audit

    def test_reopening_preserves_disk_bytes_and_extends_existing_chain(self):
        first = self.populated_log()
        original = self.path.read_bytes()
        reopened = AuditLog(str(self.path))
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(reopened.entries, first.entries)
        self.assertTrue(reopened.verify())
        new_entry = reopened.record("owner", "approved", {"tool": "submit"})
        self.assertEqual(new_entry["i"], 2)
        self.assertEqual(new_entry["prev"], first.entries[-1]["hash"])
        self.assertTrue(self.path.read_bytes().startswith(original))
        self.assertTrue(reopened.verify())
        self.assertEqual(len(AuditLog(str(self.path)).entries), 3)

    def test_existing_empty_log_can_be_opened_and_appended(self):
        self.path.write_text("")
        audit = AuditLog(str(self.path))
        self.assertTrue(audit.verify())
        entry = audit.record("agent", "start")
        self.assertEqual((entry["i"], entry["prev"]), (0, "GENESIS"))
        self.assertTrue(audit.verify())

    def test_invalid_disk_chain_is_rejected_without_overwriting_evidence(self):
        self.populated_log()
        rows = self.path.read_text().splitlines()
        altered = json.loads(rows[0])
        altered["detail"]["goal"] = "Approve everything"
        self.path.write_text(json.dumps(altered) + "\n" + rows[1] + "\n")
        original = self.path.read_bytes()
        with self.assertRaises(ValueError):
            AuditLog(str(self.path))
        self.assertEqual(self.path.read_bytes(), original)

    def test_malformed_or_incomplete_disk_entries_raise_value_error(self):
        for contents in ['{"broken":', '{}\n', '[]\n', 'null\n', '"entry"\n', '5\n', 'true\n']:
            with self.subTest(contents=contents):
                self.path.write_text(contents)
                with self.assertRaises(ValueError):
                    AuditLog(str(self.path))
                self.assertEqual(self.path.read_text(), contents)

    def test_verify_detects_disk_edit_even_when_memory_is_untouched(self):
        audit = self.populated_log()
        rows = self.path.read_text().splitlines()
        altered = json.loads(rows[0])
        altered["actor"] = "intruder"
        self.path.write_text(json.dumps(altered) + "\n" + rows[1] + "\n")
        self.assertEqual(audit.entries[0]["actor"], "owner")
        self.assertFalse(audit.verify())

    def test_verify_detects_truncation_to_an_otherwise_valid_prefix(self):
        audit = self.populated_log()
        self.path.write_text(self.path.read_text().splitlines()[0] + "\n")
        self.assertFalse(audit.verify())

    def test_verify_detects_malformed_appended_data(self):
        audit = self.populated_log()
        with self.path.open("a") as handle:
            handle.write("not-json\n")
        self.assertFalse(audit.verify())

    def test_verify_detects_deleted_persistent_log(self):
        audit = self.populated_log()
        self.path.unlink()
        self.assertFalse(audit.verify())

    def test_verify_still_detects_memory_tampering(self):
        audit = self.populated_log()
        audit.entries[0]["detail"]["goal"] = "Tampered in memory"
        self.assertFalse(audit.verify())

    def test_append_refuses_tampered_log_and_preserves_the_evidence(self):
        audit = self.populated_log()
        self.path.write_text(self.path.read_text().splitlines()[0] + "\n")
        tampered_disk = self.path.read_bytes()
        memory_before = list(audit.entries)
        with self.assertRaises(ValueError):
            audit.record("agent", "new_action")
        self.assertEqual(self.path.read_bytes(), tampered_disk)
        self.assertEqual(audit.entries, memory_before)

    def test_stale_writer_cannot_append_to_a_changed_chain(self):
        first = self.populated_log()
        stale = AuditLog(str(self.path))
        first.record("agent", "new_action")
        disk_after_first_writer = self.path.read_bytes()
        with self.assertRaises(ValueError):
            stale.record("agent", "stale_action")
        self.assertEqual(self.path.read_bytes(), disk_after_first_writer)
        self.assertTrue(first.verify())


if __name__ == "__main__":
    unittest.main()
