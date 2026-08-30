from __future__ import annotations

import unittest
from pathlib import Path

from server.policy_retrieval import PolicyKnowledgeStore


ROOT = Path(__file__).resolve().parents[1]


class PolicyRetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = PolicyKnowledgeStore(ROOT)

    def test_metadata_counts(self):
        metadata = self.store.metadata()
        self.assertEqual(metadata["chunks"], 44)
        self.assertEqual(metadata["interventions"], 19)
        self.assertEqual(metadata["scenarios"], 9)
        self.assertEqual(metadata["evidence_type"], "policy")

    def test_japanese_search_returns_road_evidence(self):
        result = self.store.search("道路 保水化", top_k=5)
        self.assertGreater(result["result_count"], 0)
        self.assertTrue(any("road" in row["scenario"] or "water_retentive_surface" in row["interventions"] for row in result["results"]))
        self.assertTrue(all(row["chunk_id"] and row["source_file"] for row in result["results"]))

    def test_english_search_uses_bilingual_retrieval_text(self):
        result = self.store.search("water retentive road surface", top_k=5)
        ids = {item for row in result["results"] for item in row["interventions"]}
        self.assertIn("water_retentive_surface", ids)

    def test_structured_road_filter(self):
        result = self.store.filter_interventions(scenario="road", min_confidence="high")
        ids = {row["intervention_id"] for row in result["interventions"]}
        self.assertIn("water_retentive_surface", ids)
        self.assertIn("ground_greening", ids)
        self.assertNotIn("roof_heat_shielding", ids)

    def test_logic_and_status_filters(self):
        result = self.store.filter_interventions(
            policy_logic=["tamenai", "morawanai"],
            document_status="historical_reference",
        )
        self.assertGreater(result["match_count"], 0)
        for row in result["interventions"]:
            self.assertTrue(row["policy_logic"]["tamenai"])
            self.assertTrue(row["policy_logic"]["morawanai"])

    def test_full_evidence_has_printed_and_pdf_pages(self):
        result = self.store.get_evidence("tokyo_summer_heat_guideline_2019-p036-water_retentive_surface")
        self.assertEqual(result["citation"]["pdf_pages"], [36, 36])
        self.assertEqual(result["citation"]["printed_pages"], [34, 34])
        self.assertEqual(result["evidence_type"], "policy")

    def test_unknown_filter_is_rejected(self):
        with self.assertRaises(ValueError):
            self.store.filter_interventions(scenario="invented_scenario")

    def test_policy_results_do_not_claim_model_evidence(self):
        result = self.store.search("建物形状の工夫", top_k=3)
        self.assertTrue(all(row["evidence_type"] == "policy" for row in result["results"]))
        self.assertNotIn("model", result["note"].lower())


if __name__ == "__main__":
    unittest.main()
