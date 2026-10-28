"""Debounced polling monitor for new shiur files in the selected folder."""
import pathlib
import threading
import time

from engine import EXTENSIONS


class FolderMonitor:
    """Rescan after audio files stop changing; never touch the active playback backend."""

    def __init__(self, player, interval=3.0, stable_polls=2):
        self.player = player
        self.interval = max(1.0, float(interval))
        self.stable_polls = max(2, int(stable_polls))
        self.stop_event = threading.Event()
        self.thread = None
        self._applied = None

    def _snapshot(self, root):
        found = {}
        try:
            # Normalize both sides before checking containment. Windows temporary
            # paths and mapped/short path spellings can otherwise compare unequal.
            root = pathlib.Path(root).resolve()
            for path in root.rglob("*"):
                if path.suffix.lower() not in EXTENSIONS:
                    continue
                try:
                    if path.is_file() and path.resolve().is_relative_to(root):
                        stat = path.stat()
                        found[str(path)] = (stat.st_size, stat.st_mtime_ns)
                except (OSError, RuntimeError):
                    continue
        except (OSError, RuntimeError):
            return None
        return found

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, name="shiur-folder-monitor", daemon=True)
        self.thread.start()

    def close(self):
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=self.interval + 1)

    def _run(self):
        previous = None
        stable_count = 0
        while not self.stop_event.wait(self.interval):
            with self.player.lock:
                root = self.player.root
            if root is None or not root.is_dir():
                previous = None
                stable_count = 0
                continue
            current = self._snapshot(root)
            if current is None:
                continue
            if current == previous:
                stable_count += 1
            else:
                previous = current
                stable_count = 0
            if stable_count < self.stable_polls:
                continue
            # Initial observation establishes a baseline without an unnecessary
            # full library refresh. Only stable subsequent changes trigger a scan.
            if self._applied is None:
                self._applied = current
                continue
            if current == self._applied:
                continue
            try:
                self.player.scan(root)
                self._applied = current
            except (OSError, ValueError, RuntimeError):
                # Folder can be disconnected or renamed while the monitor runs.
                # Keep retrying on the next poll; the UI's manual Refresh remains.
                time.sleep(0.1)
