import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.app.evidence_resolver import (
    EvidenceSnippet,
    load_evidence_index,
    resolve_evidence_for_item,
)


class TestLoadEvidenceIndex(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.job_dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_load_empty_when_no_file(self) -> None:
        result = load_evidence_index(self.job_dir)
        self.assertEqual(result, {})

    def _write_request(self, segments: list) -> None:
        path = self.job_dir / "analysis" / "llm"
        path.mkdir(parents=True)
        (path / "text_request.json").write_text(
            json.dumps({"evidence_segments": segments}), encoding="utf-8"
        )

    def test_load_parses_segments_correctly(self) -> None:
        self._write_request(
            [
                {"id": "seg-1", "text": "Hello world", "start_ms": 1000, "end_ms": 2000, "kind": "transcript"},
                {"id": "seg-2", "text": "Second segment", "start_ms": None, "end_ms": None, "kind": "text_block"},
            ]
        )
        index = load_evidence_index(self.job_dir)

        self.assertIn("seg-1", index)
        self.assertEqual(index["seg-1"].text, "Hello world")
        self.assertEqual(index["seg-1"].start_ms, 1000)
        self.assertEqual(index["seg-1"].end_ms, 2000)
        self.assertEqual(index["seg-1"].kind, "transcript")

        self.assertIn("seg-2", index)
        self.assertIsNone(index["seg-2"].start_ms)
        self.assertEqual(index["seg-2"].kind, "text_block")

    def test_load_skips_entries_without_id(self) -> None:
        self._write_request([{"text": "no id here", "kind": "transcript"}])
        index = load_evidence_index(self.job_dir)
        self.assertEqual(index, {})

    def test_load_returns_empty_on_invalid_json(self) -> None:
        path = self.job_dir / "analysis" / "llm"
        path.mkdir(parents=True)
        (path / "text_request.json").write_text("not json", encoding="utf-8")
        result = load_evidence_index(self.job_dir)
        self.assertEqual(result, {})


class TestResolveEvidenceForItem(unittest.TestCase):
    def setUp(self) -> None:
        self.index = {
            "seg-1": EvidenceSnippet("seg-1", "First excerpt", 0, 1000, "transcript"),
            "seg-2": EvidenceSnippet("seg-2", "Second excerpt", 1000, 2000, "transcript"),
        }

    def test_resolve_maps_ids_to_snippets(self) -> None:
        item = {"evidence_segment_ids": ["seg-1", "seg-2"]}
        result = resolve_evidence_for_item(item, self.index)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].segment_id, "seg-1")
        self.assertEqual(result[1].segment_id, "seg-2")

    def test_resolve_skips_missing_ids(self) -> None:
        item = {"evidence_segment_ids": ["seg-1", "seg-99", "seg-2"]}
        result = resolve_evidence_for_item(item, self.index)
        self.assertEqual(len(result), 2)
        ids = [s.segment_id for s in result]
        self.assertNotIn("seg-99", ids)

    def test_resolve_returns_empty_when_no_ids(self) -> None:
        result = resolve_evidence_for_item({}, self.index)
        self.assertEqual(result, [])

    def test_resolve_returns_empty_on_empty_ids(self) -> None:
        result = resolve_evidence_for_item({"evidence_segment_ids": []}, self.index)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
