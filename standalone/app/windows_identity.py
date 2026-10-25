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
