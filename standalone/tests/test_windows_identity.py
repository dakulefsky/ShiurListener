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

    def test_new_instance_holds_handle_and_closes_it_once(self):
        kernel = Mock();kernel.CreateMutexW.return_value=123
        with patch.object(ctypes,'WinDLL',return_value=kernel,create=True),patch.object(ctypes,'set_last_error',create=True),patch.object(ctypes,'get_last_error',return_value=0,create=True):
            handle=windows_identity.acquire_instance()
        kernel.CloseHandle.assert_not_called()
        handle.close();handle.close();kernel.CloseHandle.assert_called_once_with(123)

    def test_second_launch_focuses_existing_window_without_a_second_profile(self):
        kernel=Mock();kernel.CreateMutexW.return_value=123
        user=Mock();user.FindWindowW.return_value=456
        with patch.object(ctypes,'WinDLL',side_effect=lambda name,**kw:kernel if name=='kernel32' else user,create=True),patch.object(ctypes,'set_last_error',create=True),patch.object(ctypes,'get_last_error',return_value=183,create=True):
            self.assertIsNone(windows_identity.acquire_instance())
        kernel.CloseHandle.assert_called_once_with(123)
        user.ShowWindow.assert_called_once_with(456,9)

    def test_failed_audio_startup_releases_instance_handle(self):
        import main
        instance=Mock()
        with patch.object(main.sys,'platform','win32'),patch.object(main.sys,'argv',['Shiur Player']),patch.object(main,'configure_taskbar'),patch.object(main,'acquire_instance',return_value=instance),patch.object(main,'VLC',side_effect=RuntimeError('Audio missing')):
            with self.assertRaisesRegex(RuntimeError,'Audio missing'):main.main()
        instance.close.assert_called_once()
