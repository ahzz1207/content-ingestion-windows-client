from __future__ import annotations

import json
from pathlib import Path


FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "domain_benchmark"
MANIFEST_PATH = FIXTURES_ROOT / "manifest.json"


def test_domain_benchmark_manifest_has_eight_samples() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest["version"] == 1
    assert len(manifest["samples"]) == 8


def test_domain_benchmark_manifest_covers_required_domains() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    domains = {sample["expected_domain_template"] for sample in manifest["samples"]}
    assert {
        "politics_public_issue",
        "macro_business",
        "game_guide",
        "personal_narrative",
    } <= domains


def test_domain_benchmark_manifest_requires_goal_and_domain_expectations() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    for sample in manifest["samples"]:
        assert sample["id"]
        assert sample["public_url"]
        assert sample["expected_reading_goal"]
        assert sample["expected_domain_template"]
        assert sample["snapshot_path"]
        assert sample["notes"]


def test_domain_benchmark_manifest_matches_each_snapshot() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    for sample in manifest["samples"]:
        snapshot_path = Path(sample["snapshot_path"])
        snapshot = json.loads((Path(__file__).resolve().parents[2] / snapshot_path).read_text(encoding="utf-8"))

        assert snapshot["id"] == sample["id"]
        assert snapshot["public_url"] == sample["public_url"]
        assert snapshot["expected_reading_goal"] == sample["expected_reading_goal"]
        assert snapshot["expected_domain_template"] == sample["expected_domain_template"]
        assert snapshot["notes"] == sample["notes"]
