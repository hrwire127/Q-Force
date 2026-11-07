"""Tests for the exact route optimizer used by app.py."""

import copy
import json
import unittest
from pathlib import Path

from classical_optimizer import (
    analizeaza_planuri,
    analyze_budgets,
    evalueaza_plan,
    evaluate_plan,
    evaluate_qaoa_distribution,
    explain_classical_solution,
    get_alternative_plans,
    get_pareto_plans,
    optimize_routes,
    optimizeaza_clasic,
    profil_bugete,
)


ROUTES = [
    {"nume": "A", "cost": 2, "puncte": 4},
    {"nume": "B", "cost": 3, "puncte": 6},
    {"nume": "C", "cost": 2, "puncte": 5},
    {"nume": "D", "cost": 4, "puncte": 9},
    {"nume": "E", "cost": 4, "puncte": 7},
]


class OptimizeRoutesTests(unittest.TestCase):
    def assert_feasible(self, routes, budget):
        result = optimize_routes(routes, budget)
        self.assertLessEqual(result["cost_total"], budget)
        self.assertEqual(result["buget_ramas"], budget - result["cost_total"])
        self.assertEqual(result["planuri_evaluate"], 2 ** len(routes))
        self.assertEqual(len(result["vector_binar"]), len(routes))
        self.assertEqual(
            result["rute_selectate"],
            [route for route, bit in zip(routes, result["vector_binar"]) if bit],
        )
        return result

    def test_five_routes_budget_seven_and_both_optima(self):
        result = self.assert_feasible(ROUTES, 7)
        self.assertEqual(result["punctaj_total"], 15)
        self.assertEqual(result["cost_total"], 7)
        self.assertEqual(result["vector_binar"], [0, 1, 0, 1, 0])
        self.assertEqual(
            [plan["vector_binar"] for plan in result["solutii_optime"]],
            [[0, 1, 0, 1, 0], [1, 1, 1, 0, 0]],
        )
        self.assertTrue(all(plan["cost_total"] == 7 for plan in result["solutii_optime"]))

    def test_different_budgets_and_empty_routes(self):
        for budget in (0, 1, 2, 4, 7, 15):
            with self.subTest(budget=budget):
                self.assert_feasible(ROUTES, budget)
        self.assertEqual(self.assert_feasible(ROUTES, 0)["vector_binar"], [0] * 5)
        self.assertEqual(self.assert_feasible(ROUTES, 15)["vector_binar"], [1] * 5)
        empty = self.assert_feasible([], 0)
        self.assertEqual(empty["vector_binar"], [])
        self.assertEqual(empty["cost_total"], 0)
        self.assertEqual(empty["punctaj_total"], 0)
        self.assertEqual(empty["planuri_evaluate"], 1)

    def test_blocked_route_and_input_unchanged(self):
        routes = copy.deepcopy(ROUTES)
        routes[3]["blocata"] = True
        original = copy.deepcopy(routes)
        result = self.assert_feasible(routes, 7)
        self.assertEqual(result["vector_binar"], [1, 1, 1, 0, 0])
        self.assertEqual(result["punctaj_total"], 15)
        self.assertEqual(routes, original)
        self.assertFalse(any(plan["vector_binar"][3] for plan in result["solutii_optime"]))

    def test_ties_choose_cheapest_then_stable_order(self):
        routes = [
            {"nume": "A", "cost": 2, "puncte": 5},
            {"nume": "B", "cost": 1, "puncte": 5},
        ]
        result = self.assert_feasible(routes, 2)
        self.assertEqual(result["vector_binar"], [0, 1])
        self.assertEqual(len(result["solutii_optime"]), 2)
        equal_cost = [{"nume": "A", "cost": 1, "puncte": 5},
                      {"nume": "B", "cost": 1, "puncte": 5}]
        self.assertEqual(self.assert_feasible(equal_cost, 1)["vector_binar"], [0, 1])

    def test_zero_cost_positive_route_and_negative_scores(self):
        routes = [{"nume": "Free", "cost": 0, "puncte": 3},
                  {"nume": "Bad", "cost": 0, "puncte": -1}]
        self.assertEqual(self.assert_feasible(routes, 0)["vector_binar"], [1, 0])

    def test_team_adapter_and_qaoa_vector_evaluation(self):
        adapted = optimizeaza_clasic(ROUTES, 7)
        self.assertEqual(adapted["rute_alese"], adapted["rute_selectate"])
        self.assertEqual(adapted["puncte_totale"], 15)
        valid = evalueaza_plan(ROUTES, 7, [1, 1, 1, 0, 0])
        self.assertTrue(valid["este_valid"])
        self.assertEqual((valid["cost_total"], valid["punctaj_total"]), (7, 15))
        over_budget = evalueaza_plan(ROUTES, 7, [1, 0, 1, 1, 0])
        self.assertFalse(over_budget["este_valid"])
        self.assertFalse(over_budget["respecta_bugetul"])
        self.assertEqual((over_budget["cost_total"], over_budget["punctaj_total"]), (8, 18))
        blocked = copy.deepcopy(ROUTES)
        blocked[3]["blocata"] = True
        blocked_plan = evalueaza_plan(blocked, 7, [0, 1, 0, 1, 0])
        self.assertTrue(blocked_plan["respecta_bugetul"])
        self.assertFalse(blocked_plan["respecta_blocajele"])
        self.assertFalse(blocked_plan["este_valid"])

    def test_exact_audit_and_pareto_frontier(self):
        report = analizeaza_planuri(ROUTES, 7)
        self.assertEqual(report["planuri_evaluate"], 32)
        self.assertEqual(report["planuri_cu_rute_blocate"], 0)
        self.assertGreater(report["planuri_valide"], 0)
        self.assertEqual(report["planuri_valide"] + report["planuri_peste_buget"], 32)
        self.assertEqual(report["frontiera_pareto"][-1]["punctaj_total"], 15)
        self.assertTrue(all(plan["cost_total"] <= 7 for plan in report["frontiera_pareto"]))
        self.assertTrue(all(plan["punctaj_total"] < 15 for plan in report["alternative"]))
        self.assertEqual(analizeaza_planuri([], 0)["frontiera_pareto"][0]["vector_binar"], [])

    def test_new_helpers_reject_invalid_vectors_and_limits(self):
        for bits in ([1], [0, 0, 0, 0, 2], [False, 0, 0, 0, 0], "00000"):
            with self.subTest(bits=bits), self.assertRaises(ValueError):
                evalueaza_plan(ROUTES, 7, bits)
        for limit in (-1, 1.5, True):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                analizeaza_planuri(ROUTES, 7, limita_alternative=limit)

    def test_budget_profile_matches_exact_optima(self):
        profile = profil_bugete(ROUTES, [0, 7, 15])
        self.assertEqual([point["punctaj_total"] for point in profile], [0, 15, 31])
        for point in profile:
            with self.subTest(budget=point["buget"]):
                self.assertLessEqual(point["cost_total"], point["buget"])
                self.assertEqual(point["vector_binar"],
                                 optimize_routes(ROUTES, point["buget"])["vector_binar"])
        self.assertEqual(profil_bugete([], []), [])
        with self.assertRaises(ValueError):
            profil_bugete(ROUTES, [-1])

    def test_advanced_budget_analysis_and_blocked_routes(self):
        profile = analyze_budgets(ROUTES, 15)
        self.assertEqual([profile[b]["punctaj_total"] for b in (6, 7, 8)], [14, 15, 18])
        self.assertEqual([profile[b]["castig_marginal"] for b in (6, 7, 8)], [3, 1, 3])
        self.assertTrue(all(a["punctaj_total"] <= b["punctaj_total"]
                            for a, b in zip(profile, profile[1:])))
        for point in profile:
            with self.subTest(budget=point["buget"]):
                self.assertLessEqual(point["cost_total"], point["buget"])
                self.assertEqual(point["buget_ramas"], point["buget"] - point["cost_total"])
                self.assertGreaterEqual(point["numar_solutii_optime"], 1)
        self.assertTrue(profile[2]["este_salt_maxim"])
        original = copy.deepcopy(ROUTES)
        by_index = analyze_budgets(ROUTES, 7, blocked_routes=[3])
        by_name = analyze_budgets(ROUTES, 7, blocked_routes=[ROUTES[3]["nume"]])
        self.assertEqual(by_index[7]["vector_binar"], [1, 1, 1, 0, 0])
        self.assertEqual(by_index, by_name)
        self.assertEqual(ROUTES, original)
        for invalid in (-1, 2.5, True):
            with self.subTest(max_budget=invalid), self.assertRaises(ValueError):
                analyze_budgets(ROUTES, invalid)
        with self.assertRaises(ValueError):
            analyze_budgets(ROUTES, 7, blocked_routes=[99])

    def test_alternative_ranking_and_exact_pareto(self):
        ranked = get_alternative_plans(ROUTES, 7, top_k=3)
        plans = ranked["planuri"]
        self.assertEqual([plan["punctaj_total"] for plan in plans], [15, 15, 14])
        self.assertEqual(len({tuple(plan["vector_binar"]) for plan in plans}), 3)
        self.assertEqual(len(ranked["solutii_optime"]), 2)
        self.assertEqual(plans[2]["cost_total"], 6)
        self.assertEqual(plans[2]["pierdere_punctaj"], 1)
        self.assertEqual(plans[2]["economie_cost"], 1)
        self.assertEqual(ranked["alternativa_mai_ieftina"]["vector_binar"], plans[2]["vector_binar"])
        self.assertTrue(all(plan["cost_total"] <= 7 for plan in plans))
        self.assertEqual(get_alternative_plans(ROUTES, 7, top_k=0)["planuri"], [])
        pareto = get_pareto_plans(ROUTES, 7)
        vectors = [plan["vector_binar"] for plan in pareto]
        self.assertIn([1, 1, 1, 0, 0], vectors)
        self.assertIn([0, 1, 0, 1, 0], vectors)
        self.assertNotIn([1, 0, 0, 0, 0], vectors)  # Same cost, lower score than route 3.
        with self.assertRaises(ValueError):
            get_alternative_plans(ROUTES, 7, top_k=-1)

    def test_explanation_uses_exact_facts(self):
        result = optimize_routes(ROUTES, 7)
        explanation = explain_classical_solution(ROUTES, 7, result)
        self.assertIn("32 de combinații", explanation["rezumat"])
        self.assertIn("2 soluții optime", explanation["rezumat"])
        self.assertIn("economisește 1 unitate", explanation["rezumat"])
        self.assertIn("crește cu 3 puncte", explanation["rezumat"])
        self.assertEqual(explanation["indicatori"]["castig_buget_suplimentar"], 3)
        self.assertEqual(explanation["alternativa_mai_ieftina"]["punctaj_total"], 14)
        with self.assertRaises(ValueError):
            explain_classical_solution(ROUTES, 6, result)

    def test_qaoa_plan_evaluation_recognizes_both_optima(self):
        for bits in ([1, 1, 1, 0, 0], [0, 1, 0, 1, 0]):
            with self.subTest(bits=bits):
                result = evaluate_plan(ROUTES, 7, bits)
                self.assertTrue(result["este_optim_global"])
                self.assertEqual(result["numar_solutii_optime"], 2)
                self.assertEqual(result["diferenta_punctaj_fata_de_optim"], 0)
        invalid = evaluate_plan(ROUTES, 7, [1, 0, 1, 1, 0])
        self.assertFalse(invalid["este_valid"])
        self.assertFalse(invalid["este_optim_global"])
        self.assertEqual(invalid["diferenta_punctaj_fata_de_optim"], 3)
        blocked = evaluate_plan(ROUTES, 7, [0, 1, 0, 1, 0], blocked_routes=[3])
        self.assertTrue(blocked["include_ruta_blocata"])
        self.assertFalse(blocked["este_optim_global"])

    def test_synthetic_qaoa_distributions_and_bit_order(self):
        # Synthetic counts: keys are Qiskit display order, reversed from route order.
        counts = {"00111": 2, "01010": 3, "01110": 5}
        result = evaluate_qaoa_distribution(ROUTES, 7, counts, bit_order="qiskit")
        self.assertEqual(result["format_distributie"], "numarari")
        self.assertEqual(result["total_masurari"], 10)
        self.assertAlmostEqual(result["probabilitate_planuri_valide"], 0.5)
        self.assertAlmostEqual(result["probabilitate_solutii_optime"], 0.5)
        self.assertAlmostEqual(result["punctaj_mediu"], 17.5)
        self.assertAlmostEqual(result["cost_mediu"], 8.0)
        self.assertFalse(result["cel_mai_frecvent_plan"]["este_valid"])
        probabilities = {"11100": 0.2, "01010": 0.3, "01110": 0.5}
        other = evaluate_qaoa_distribution(ROUTES, 7, probabilities, bit_order="route_order")
        self.assertEqual(other["format_distributie"], "probabilitati")
        self.assertIsNone(other["cel_mai_frecvent_plan"])
        self.assertAlmostEqual(other["probabilitate_solutii_optime"], 0.5)
        reversed_key = evaluate_qaoa_distribution(ROUTES, 7, {"00111": 1}, bit_order="qiskit")
        direct_key = evaluate_qaoa_distribution(ROUTES, 7, {"00111": 1}, bit_order="route_order")
        self.assertEqual(reversed_key["probabilitate_solutii_optime"], 1)
        self.assertEqual(direct_key["probabilitate_solutii_optime"], 0)

    def test_existing_qaoa_counts_match_notebook_metrics(self):
        path = Path(__file__).resolve().parents[1] / "railway_results.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        result = evaluate_qaoa_distribution(ROUTES, 7, data["ideal_counts"], bit_order="qiskit")
        self.assertAlmostEqual(result["probabilitate_planuri_valide"],
                               data["metrics"]["Ideal"]["feasible_rate"])
        self.assertAlmostEqual(result["probabilitate_solutii_optime"],
                               data["metrics"]["Ideal"]["optimal_feasible_probability"])
        self.assertAlmostEqual(result["punctaj_mediu"],
                               data["metrics"]["Ideal"]["mean_true_score"])

    def test_invalid_qaoa_distributions(self):
        invalid = [({}, "qiskit"), ({"001": 1}, "qiskit"),
                   ({"00000": -1}, "qiskit"), ({"00000": 0}, "qiskit"),
                   ({"00000": 0.2}, "qiskit"), ({"00000": 1}, "wrong"),
                   ({"00000": 1, "00 000": 2}, "qiskit")]
        for distribution, order in invalid:
            with self.subTest(distribution=distribution, order=order), self.assertRaises(ValueError):
                evaluate_qaoa_distribution(ROUTES, 7, distribution, bit_order=order)

    def test_invalid_inputs(self):
        invalid = [
            (ROUTES, -1),
            (ROUTES, float("nan")),
            (ROUTES, True),
            (None, 7),
            ([{"nume": "A", "cost": -1, "puncte": 2}], 7),
            ([{"nume": "A", "cost": 1}], 7),
            ([{"nume": "", "cost": 1, "puncte": 2}], 7),
            ([{"nume": "A", "cost": float("inf"), "puncte": 2}], 7),
            ([{"nume": "A", "cost": 1, "puncte": "2"}], 7),
            ([{"nume": "A", "cost": 1, "puncte": 2, "blocata": 1}], 7),
        ]
        for routes, budget in invalid:
            with self.subTest(routes=routes, budget=budget):
                with self.assertRaisesRegex(ValueError, ".+"):
                    optimize_routes(routes, budget)


if __name__ == "__main__":
    unittest.main()
