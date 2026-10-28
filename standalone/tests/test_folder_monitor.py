"""Deterministic tests for debounced folder monitoring."""
import pathlib
import sys
import threading
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "app"))
from folder_monitor import FolderMonitor


class FakePlayer:
    def __init__(self, root):
        self.root = root
        self.lock = threading.RLock()
        self.scans = []

    def scan(self, root):
        self.scans.append(pathlib.Path(root))


class SequenceEvent:
    def __init__(self, results):
        self.results = iter(results)

    def wait(self, _interval):
        return next(self.results, True)

    def set(self):
        pass


class FolderMonitorTests(unittest.TestCase):
    def test_snapshot_only_tracks_supported_audio_files(self):
        with __import__("tempfile").TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "shiur.mp3").write_bytes(b"audio")
            (root / "notes.txt").write_text("not audio")
            nested = root / "subfolder"
            nested.mkdir()
            (nested / "recording.WAV").write_bytes(b"wav")
            monitor = FolderMonitor(FakePlayer(root))
            snapshot = monitor._snapshot(root)
            self.assertEqual({pathlib.Path(path).name for path in snapshot}, {"shiur.mp3", "recording.WAV"})

    def test_initial_snapshot_does_not_rescan_but_stable_change_does(self):
        with __import__("tempfile").TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            player = FakePlayer(root)
            monitor = FolderMonitor(player, interval=1, stable_polls=2)
            before = {"one.mp3": (100, 1)}
            after = {"one.mp3": (100, 1), "two.mp3": (200, 2)}
            snapshots = iter([before, before, before, before, after, after, after, after])
            monitor._snapshot = mock.Mock(side_effect=lambda _root: next(snapshots))
            monitor.stop_event = SequenceEvent([False] * 8 + [True])
            monitor._run()
            self.assertEqual(player.scans, [root])

    def test_growing_file_is_not_scanned_until_size_and_mtime_stabilize(self):
        with __import__("tempfile").TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            player = FakePlayer(root)
            monitor = FolderMonitor(player, interval=1, stable_polls=2)
            baseline = {"shiur.mp3": (100, 1)}
            growing = {"shiur.mp3": (200, 2)}
            finished = {"shiur.mp3": (9000, 9)}
            # Establish the initial baseline, then simulate a copy growing in
            # two steps. A scan is allowed only after the final snapshot repeats.
            snapshots = iter(
                [baseline, baseline, baseline, baseline,
                 growing, finished, finished, finished, finished]
            )
            monitor._snapshot = mock.Mock(side_effect=lambda _root: next(snapshots))
            monitor.stop_event = SequenceEvent([False] * 9 + [True])
            monitor._run()
            self.assertEqual(player.scans, [root])
            self.assertEqual(monitor._applied, finished)

    def test_missing_root_does_not_crash_monitor(self):
        player = FakePlayer(None)
        monitor = FolderMonitor(player, interval=1)
        monitor.stop_event = SequenceEvent([False, True])
        monitor._run()
        self.assertEqual(player.scans, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
