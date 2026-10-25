import ctypes
import pathlib
import sys
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'app'))
import windows_identity


class Tests(unittest.TestCase):
    def test_assigns_stable_app_identity_before_gui(self):
        shell = Mock()
        shell.SetCurrentProcessExplicitAppUserModelID.return_value = 0
        with patch.object(windows_identity.sys, 'platform', 'win32'), patch.object(ctypes, 'WinDLL', return_value=shell, create=True):
            windows_identity.configure_taskbar()
        shell.SetCurrentProcessExplicitAppUserModelID.assert_called_once_with('ShiurPlayer.Standalone')
        self.assertEqual(shell.SetCurrentProcessExplicitAppUserModelID.restype, ctypes.c_int32)

    def test_reports_failed_windows_identity_assignment(self):
        shell = Mock()
        shell.SetCurrentProcessExplicitAppUserModelID.return_value = -2147024809
        with patch.object(windows_identity.sys, 'platform', 'win32'), patch.object(ctypes, 'WinDLL', return_value=shell, create=True):
            with self.assertRaisesRegex(OSError, 'taskbar identity'):
                windows_identity.configure_taskbar()

    def test_does_not_load_windows_libraries_elsewhere(self):
        with patch.object(windows_identity.sys, 'platform', 'linux'), patch.object(ctypes, 'WinDLL', create=True) as load:
            windows_identity.configure_taskbar()
        load.assert_not_called()
