import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from windows_client.gui.refresh_policy import RefreshGate


class RefreshGateTests(unittest.TestCase):
    def test_allows_first_refresh_immediately(self) -> None:
        gate = RefreshGate(min_interval_seconds=2.0)

        self.assertTrue(gate.allow_now(now=10.0))
        self.assertEqual(gate.seconds_until_allowed(now=10.0), 0.0)

    def test_blocks_until_interval_has_elapsed(self) -> None:
        gate = RefreshGate(min_interval_seconds=2.0)
        gate.mark(now=10.0)

        self.assertFalse(gate.allow_now(now=11.0))
        self.assertEqual(gate.seconds_until_allowed(now=11.0), 1.0)
        self.assertTrue(gate.allow_now(now=12.0))


if __name__ == "__main__":
    unittest.main()
