import sys
from pathlib import Path
import unittest

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from data_contract import RouteScenario, UserPreferenceProfile, DecisionResponse
from engine.decision_engine import DecisionEngine


class TestDecisionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = DecisionEngine(tau_cutoff=9.0, lambda_ari=0.6, sigma_0_sq=1.0)
        self.scenarios = self.engine.get_benchmark_scenarios()

    def test_bayesian_uncertainty(self):
        u0 = self.engine.compute_bayesian_uncertainty(0)
        self.assertAlmostEqual(u0, 1.0, places=3)

        u3 = self.engine.compute_bayesian_uncertainty(3)
        self.assertAlmostEqual(u3, 0.5, places=3)

        u100 = self.engine.compute_bayesian_uncertainty(100)
        self.assertLess(u100, u3)

    def test_hard_safety_constraint(self):
        valid, filtered = self.engine.filter_hard_safety_constraints(self.scenarios, tau_cutoff=9.0)
        filtered_ids = [f["route_id"] for f in filtered]
        self.assertIn("ROUTE_E", filtered_ids)
        self.assertNotIn("ROUTE_E", [s.route_id for s in valid])

        valid_ids = [s.route_id for s in valid]
        self.assertIn("ROUTE_A", valid_ids)
        self.assertIn("ROUTE_B", valid_ids)
        self.assertIn("ROUTE_C", valid_ids)
        self.assertIn("ROUTE_D", valid_ids)

    def test_pareto_frontier(self):
        valid, _ = self.engine.filter_hard_safety_constraints(self.scenarios)
        pareto = self.engine.filter_pareto_frontier(valid)
        pareto_ids = [s.route_id for s in pareto]
        self.assertIn("ROUTE_A", pareto_ids)
        self.assertIn("ROUTE_B", pareto_ids)
        self.assertIn("ROUTE_C", pareto_ids)
        self.assertNotIn("ROUTE_D", pareto_ids)

    def test_mcda_profiles(self):
        res_safe = self.engine.evaluate(self.scenarios, UserPreferenceProfile.safe_first())
        self.assertIn(res_safe.recommended_scenario.route_id, ["ROUTE_B", "ROUTE_C"])

        res_fast = self.engine.evaluate(self.scenarios, UserPreferenceProfile.fast_first())
        self.assertEqual(res_fast.recommended_scenario.route_id, "ROUTE_A")

        res_bal = self.engine.evaluate(self.scenarios, UserPreferenceProfile.balanced())
        self.assertEqual(res_bal.recommended_scenario.route_id, "ROUTE_B")

    def test_xai_explanation_generation(self):
        res = self.engine.evaluate(self.scenarios, UserPreferenceProfile.balanced())
        xai = res.recommended_scenario.xai_explanation
        self.assertTrue(len(xai) > 10)
        self.assertIn("ROUTE_B", res.tradeoff_metadata.get("recommended_route_id", ""))
        self.assertGreater(res.tradeoff_metadata.get("ari_reduction_pct", 0), 0)

    def test_serialization(self):
        res = self.engine.evaluate(self.scenarios, UserPreferenceProfile.balanced())
        res_dict = res.to_dict()
        self.assertIsInstance(res_dict, dict)
        self.assertIn("pareto_scenarios", res_dict)
        self.assertIn("recommended_scenario", res_dict)
        self.assertIn("tradeoff_metadata", res_dict)


if __name__ == "__main__":
    unittest.main(verbosity=2)
