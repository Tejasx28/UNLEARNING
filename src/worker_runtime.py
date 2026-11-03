"""Lightweight parent supervision without a blocking CRT stdin read on Windows."""
import os
import sys
import threading


def start_parent_watchdog():
    """Exit on parent pipe EOF, without holding Windows' stdin file lock.

    A blocking buffered read on stdin can deadlock NumPy extension loading on
    Windows. PeekNamedPipe observes pipe closure without entering that CRT read.
    """
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        import msvcrt
        handle = msvcrt.get_osfhandle(sys.stdin.fileno())
        peek = ctypes.WinDLL('kernel32', use_last_error=True).PeekNamedPipe
        peek.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                         ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        peek.restype = wintypes.BOOL

        def watch():
            while True:
                if not peek(handle, None, 0, None, None, None):
                    os._exit(2)
                threading.Event().wait(.25)
    else:
        import select

        def watch():
            while True:
                ready, _, _ = select.select([sys.stdin.fileno()], [], [], .25)
                if ready and not os.read(sys.stdin.fileno(), 1):
                    os._exit(2)
    thread = threading.Thread(target=watch, daemon=True, name='parent-watchdog')
    thread.start()
    return thread
