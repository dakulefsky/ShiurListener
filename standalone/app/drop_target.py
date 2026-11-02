"""Native Windows drag-and-drop support for importing audio into the library."""
import ctypes
import os
import pathlib
import shutil
import uuid

from engine import EXTENSIONS


def copy_dropped_audio(paths, recordings_root):
    """Copy supported audio files into the selected library root without clobbering."""
    root = pathlib.Path(recordings_root).resolve()
    if not root.is_dir():
        raise ValueError("The recordings folder is missing or disconnected.")

    imported = []
    skipped = []
    errors = []
    for raw in paths:
        try:
            source = pathlib.Path(raw).expanduser().resolve(strict=True)
            if not source.is_file() or source.suffix.lower() not in EXTENSIONS:
                skipped.append(str(raw))
                continue
            # A recording already anywhere in this library does not need a copy.
            if source.is_relative_to(root):
                skipped.append(str(raw))
                continue

            target = root / source.name
            if target.exists():
                stem, suffix = source.stem, source.suffix
                number = 2
                while (root / f"{stem} ({number}){suffix}").exists():
                    number += 1
                target = root / f"{stem} ({number}){suffix}"

            # Copy to a non-audio temporary name so the folder monitor never
            # indexes a partially copied download.
            temporary = root / f".shiur-import-{uuid.uuid4().hex}.part"
            try:
                shutil.copy2(source, temporary)
                os.rename(temporary, target)
            finally:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
            imported.append(target)
        except (OSError, RuntimeError, ValueError) as error:
            errors.append(f"{raw}: {error}")
    return {"imported": imported, "skipped": skipped, "errors": errors}


class WindowsDropTarget:
    """Receive Explorer WM_DROPFILES on a Tk top-level window."""

    WM_DROPFILES = 0x0233
    GWLP_WNDPROC = -4

    def __init__(self, window, callback):
        if os.name != "nt":
            raise RuntimeError("Windows drag-and-drop is only available on Windows.")
        self.window = window
        self.callback = callback
        self.hwnd = int(window.winfo_id())
        self.user32 = ctypes.windll.user32
        self.shell32 = ctypes.windll.shell32
        self._old_proc = None
        self._callback_ref = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_uint,
            ctypes.c_size_t, ctypes.c_ssize_t
        )(self._window_proc)

        self.user32.CallWindowProcW.restype = ctypes.c_ssize_t
        self.user32.CallWindowProcW.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint,
            ctypes.c_size_t, ctypes.c_ssize_t
        ]
        self.user32.SetWindowLongPtrW.restype = ctypes.c_void_p
        self.user32.SetWindowLongPtrW.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p
        ]
        self.shell32.DragAcceptFiles.argtypes = [ctypes.c_void_p, ctypes.c_bool]
        self.shell32.DragQueryFileW.restype = ctypes.c_uint
        self.shell32.DragQueryFileW.argtypes = [
            ctypes.c_void_p, ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_uint
        ]
        self.shell32.DragFinish.argtypes = [ctypes.c_void_p]

        self._old_proc = self.user32.SetWindowLongPtrW(
            self.hwnd, self.GWLP_WNDPROC,
            ctypes.cast(self._callback_ref, ctypes.c_void_p)
        )
        if not self._old_proc:
            raise ctypes.WinError(ctypes.get_last_error())
        self.shell32.DragAcceptFiles(self.hwnd, True)

    def _window_proc(self, hwnd, message, wparam, lparam):
        if message == self.WM_DROPFILES:
            drop = ctypes.c_void_p(wparam)
            paths = []
            try:
                count = self.shell32.DragQueryFileW(drop, 0xFFFFFFFF, None, 0)
                for index in range(count):
                    length = self.shell32.DragQueryFileW(drop, index, None, 0)
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    self.shell32.DragQueryFileW(drop, index, buffer, len(buffer))
                    paths.append(buffer.value)
            finally:
                self.shell32.DragFinish(drop)
            if paths:
                try:
                    self.window.after_idle(self.callback, paths)
                except Exception:
                    pass
            return 0
        return self.user32.CallWindowProcW(
            self._old_proc, hwnd, message, wparam, lparam
        )

    def close(self):
        if self._old_proc:
            self.shell32.DragAcceptFiles(self.hwnd, False)
            self.user32.SetWindowLongPtrW(
                self.hwnd, self.GWLP_WNDPROC, self._old_proc
            )
            self._old_proc = None
        self._callback_ref = None
