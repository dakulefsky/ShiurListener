"""Stable Windows taskbar identity, independent of the bundled interpreter."""
import ctypes
import sys

APP_ID = 'ShiurPlayer.Standalone'


def configure_taskbar():
    """Call before creating any windows; match the installer shortcut's AppID."""
    if sys.platform != 'win32':
        return
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    set_id = shell.SetCurrentProcessExplicitAppUserModelID
    set_id.argtypes = [ctypes.c_wchar_p]
    set_id.restype = ctypes.c_int32
    result = set_id(APP_ID)
    if result < 0:
        raise OSError(f'Could not set Shiur Player taskbar identity (0x{result & 0xffffffff:08x}).')


class InstanceHandle:
    def __init__(self, kernel, handle):
        self.kernel = kernel
        self.handle = handle

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def acquire_instance():
    """Prevent two simultaneous launches from writing the same listening profile."""
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateMutexW
    create.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    create.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.restype = ctypes.c_int
    ctypes.set_last_error(0)
    handle = create(None, False, 'Local\\ShiurPlayerStandalone')
    error = ctypes.get_last_error()
    if not handle:
        raise OSError(error, 'Could not protect the player listening profile.')
    if error == 183:  # ERROR_ALREADY_EXISTS: the first process is starting or running.
        kernel.CloseHandle(handle)
        user = ctypes.WinDLL('user32', use_last_error=True)
        user.FindWindowW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
        user.FindWindowW.restype = ctypes.c_void_p
        user.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
        user.SetForegroundWindow.argtypes = [ctypes.c_void_p]
        window = user.FindWindowW(None, 'Shiur Player')
        if window:
            user.ShowWindow(window, 9)
            user.SetForegroundWindow(window)
        return None
    return InstanceHandle(kernel, handle)
