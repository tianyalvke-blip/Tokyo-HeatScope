from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    interventions = json.loads((root / "knowledge/interventions/tokyo_heat_interventions.json").read_text(encoding="utf-8"))["interventions"]
    scenarios = json.loads((root / "knowledge/interventions/tokyo_heat_scenarios.json").read_text(encoding="utf-8"))["scenarios"]
    chunks = [json.loads(line) for line in (root / "knowledge/chunks/tokyo_summer_heat_guideline.jsonl").read_text(encoding="utf-8").splitlines() if line]
    errors = json.loads((root / "knowledge/documents/policy_extraction_errors.json").read_text(encoding="utf-8"))["validation_errors"]
    by_i = {item["intervention_id"]: item for item in interventions}
    by_s = {item["scenario_id"]: item for item in scenarios}
    assertions = [
        (not errors, "schema/cross-reference validation has no errors"),
        (len(scenarios) == 9 and len(by_s) == 9, "nine unique benchmark scenarios"),
        (len(interventions) == 19 and len(by_i) == 19, "nineteen unique extracted interventions"),
        (len(chunks) == 44 and len({item['chunk_id'] for item in chunks}) == 44, "44 unique semantic chunks"),
        (all(key in by_s for key in ["urban_block", "road"]), "requested scenario samples exist"),
        (all(key in by_i for key in ["water_retentive_surface", "green_roof", "building_configuration"]), "requested intervention samples exist"),
        ("roof_heat_shielding" not in by_s["road"]["recommended_interventions"], "road does not inherit roof-only treatment"),
        (by_i["water_retentive_surface"]["policy_logic"] == {"dasanai": False, "tamenai": True, "morawanai": True}, "water-retentive logic matches the three-viewpoint matrix"),
        (by_i["building_configuration"]["maintenance"] == [], "unstated building-form maintenance remains empty"),
        (all(item["evidence_type"] == "policy" for item in interventions + scenarios + chunks), "all benchmark evidence is typed as policy"),
        (all(item["source_evidence"] for item in interventions + scenarios), "all structured records have source evidence"),
    ]
    failures = [label for passed, label in assertions if not passed]
    for passed, label in assertions:
        print(("PASS" if passed else "FAIL") + ": " + label)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

