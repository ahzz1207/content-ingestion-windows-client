import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.app.coverage_stats import compute_coverage


class TestComputeCoverage(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.job_dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_transcript(self, segments: list) -> None:
        path = self.job_dir / "analysis" / "transcript"
        path.mkdir(parents=True)
        (path / "transcript.json").write_text(
            json.dumps({"segments": segments}), encoding="utf-8"
        )

    def _write_request(self, evidence_segments: list) -> None:
        path = self.job_dir / "analysis" / "llm"
        path.mkdir(parents=True)
        (path / "text_request.json").write_text(
            json.dumps({"evidence_segments": evidence_segments}), encoding="utf-8"
        )

    def _make_transcript_segment(self, start: float, end: float) -> dict:
        return {"start": start, "end": end, "text": "segment"}

    def _make_evidence_segment(self, seg_id: str, kind: str = "transcript") -> dict:
        return {"id": seg_id, "text": "excerpt", "kind": kind, "end_ms": 1000}

    def test_returns_none_when_no_transcript_file(self) -> None:
        # Only create the request file, not the transcript
        self._write_request([])
        result = compute_coverage(self.job_dir)
        self.assertIsNone(result)

    def test_returns_none_when_no_request_file(self) -> None:
        # Only create the transcript file, not the request
        self._write_transcript([self._make_transcript_segment(0, 1)])
        result = compute_coverage(self.job_dir)
        self.assertIsNone(result)

    def test_computes_full_coverage(self) -> None:
        segments = [self._make_transcript_segment(i, i + 1) for i in range(10)]
        self._write_transcript(segments)
        evidence = [self._make_evidence_segment(f"seg-{i}") for i in range(10)]
        self._write_request(evidence)

        result = compute_coverage(self.job_dir)
        self.assertIsNotNone(result)
        self.assertEqual(result.total_segments, 10)
        self.assertEqual(result.used_segments, 10)
        self.assertAlmostEqual(result.coverage_ratio, 1.0)
        self.assertFalse(result.input_truncated)

    def test_detects_truncation(self) -> None:
        # 378 total segments, 30 used → 7.9% coverage
        segments = [self._make_transcript_segment(i, i + 1) for i in range(378)]
        self._write_transcript(segments)
        evidence = [self._make_evidence_segment(f"seg-{i}") for i in range(30)]
        self._write_request(evidence)

        result = compute_coverage(self.job_dir)
        self.assertIsNotNone(result)
        self.assertEqual(result.total_segments, 378)
        self.assertEqual(result.used_segments, 30)
        self.assertTrue(result.input_truncated)
        self.assertLess(result.coverage_ratio, 0.85)

    def test_no_truncation_above_threshold(self) -> None:
        segments = [self._make_transcript_segment(i, i + 1) for i in range(100)]
        self._write_transcript(segments)
        evidence = [self._make_evidence_segment(f"seg-{i}") for i in range(90)]
        self._write_request(evidence)

        result = compute_coverage(self.job_dir)
        self.assertIsNotNone(result)
        self.assertFalse(result.input_truncated)
        self.assertGreaterEqual(result.coverage_ratio, 0.85)

    def test_non_transcript_evidence_excluded_from_used_count(self) -> None:
        segments = [self._make_transcript_segment(i, i + 1) for i in range(10)]
        self._write_transcript(segments)
        evidence = [
            self._make_evidence_segment("seg-t", kind="transcript"),
            self._make_evidence_segment("seg-tb", kind="text_block"),
        ]
        self._write_request(evidence)

        result = compute_coverage(self.job_dir)
        self.assertIsNotNone(result)
        # Only the transcript segment counts
        self.assertEqual(result.used_segments, 1)


if __name__ == "__main__":
    unittest.main()
