"""Win32-only host for attaching the real native renderer to developer UI."""
from __future__ import annotations

import ctypes
import os
from ctypes import wintypes


RENDERER_WINDOW_CLASS = 'OesEyeballNativeRenderer'
GWL_STYLE = -16
WS_CHILD = 0x40000000
WS_POPUP = 0x80000000
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040


class _Rect(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                ('right', ctypes.c_long), ('bottom', ctypes.c_long)]


class Win32PreviewApi:
    """Narrow injectable boundary around the Win32 calls required for SetParent."""

    def __init__(self):
        if os.name != 'nt':
            raise OSError('Native renderer preview hosting requires Windows')
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        self.user32.FindWindowW.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR)
        self.user32.FindWindowW.restype = wintypes.HWND
        self.user32.GetParent.argtypes = (wintypes.HWND,)
        self.user32.GetParent.restype = wintypes.HWND
        self.user32.GetWindowLongW.argtypes = (wintypes.HWND, ctypes.c_int)
        self.user32.GetWindowLongW.restype = ctypes.c_long
        self.user32.SetWindowLongW.argtypes = (wintypes.HWND, ctypes.c_int, ctypes.c_long)
        self.user32.SetWindowLongW.restype = ctypes.c_long
        self.user32.SetParent.argtypes = (wintypes.HWND, wintypes.HWND)
        self.user32.SetParent.restype = wintypes.HWND
        self.user32.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(_Rect))
        self.user32.GetWindowRect.restype = wintypes.BOOL
        self.user32.SetWindowPos.argtypes = (
            wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, ctypes.c_int, wintypes.UINT)
        self.user32.SetWindowPos.restype = wintypes.BOOL
        self.user32.InvalidateRect.argtypes = (wintypes.HWND, ctypes.c_void_p, wintypes.BOOL)
        self.user32.InvalidateRect.restype = wintypes.BOOL
        self.user32.UpdateWindow.argtypes = (wintypes.HWND,)
        self.user32.UpdateWindow.restype = wintypes.BOOL

    def find_renderer(self):
        return self.user32.FindWindowW(RENDERER_WINDOW_CLASS, None)

    def parent(self, hwnd):
        return self.user32.GetParent(hwnd)

    def style(self, hwnd):
        return self.user32.GetWindowLongW(hwnd, GWL_STYLE)

    def rect(self, hwnd):
        value = _Rect()
        if not self.user32.GetWindowRect(hwnd, ctypes.byref(value)):
            raise OSError('Renderer window bounds are unavailable')
        return value.left, value.top, value.right - value.left, value.bottom - value.top

    def set_style(self, hwnd, style):
        ctypes.set_last_error(0)
        previous = self.user32.SetWindowLongW(hwnd, GWL_STYLE, style)
        if not previous and ctypes.get_last_error():
            raise OSError('Renderer window style could not be changed')

    def set_parent(self, hwnd, parent):
        ctypes.set_last_error(0)
        previous = self.user32.SetParent(hwnd, parent)
        if not previous and ctypes.get_last_error():
            raise OSError('Renderer window could not be attached')

    def position(self, hwnd, x, y, width, height):
        flags = SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_SHOWWINDOW
        if not self.user32.SetWindowPos(hwnd, 0, int(x), int(y), int(width), int(height), flags):
            raise OSError('Renderer window could not be positioned')

    def invalidate(self, hwnd):
        self.user32.InvalidateRect(hwnd, None, True)
        self.user32.UpdateWindow(hwnd)


class NativePreviewHost:
    """Temporarily parents the native renderer into a developer preview surface."""

    def __init__(self, api=None):
        self.api = api or Win32PreviewApi()
        self.hwnd = None
        self._original_parent = None
        self._original_style = None
        self._original_rect = None
        self._host_hwnd = None

    @property
    def attached(self):
        return self.hwnd is not None

    def attach(self, parent_hwnd):
        if self.attached:
            return True
        hwnd = self.api.find_renderer()
        if not hwnd:
            return False
        original_parent = self.api.parent(hwnd)
        original_style = self.api.style(hwnd)
        original_rect = self.api.rect(hwnd)
        child_style = (original_style & ~WS_POPUP) | WS_CHILD
        try:
            self.api.set_style(hwnd, child_style)
            self.api.set_parent(hwnd, parent_hwnd)
        except OSError:
            try:
                self.api.set_parent(hwnd, original_parent)
                self.api.set_style(hwnd, original_style)
            except OSError:
                pass
            return False
        self.hwnd = hwnd
        self._original_parent = original_parent
        self._original_style = original_style
        self._original_rect = original_rect
        self._host_hwnd = parent_hwnd
        return True

    def place(self, host_width, host_height, surface_width, surface_height):
        if not self.attached:
            return False
        x = max(0, (int(host_width) - int(surface_width)) // 2)
        y = max(0, (int(host_height) - int(surface_height)) // 2)
        self.api.position(self.hwnd, x, y, surface_width, surface_height)
        self.api.invalidate(self._host_hwnd)
        return True

    def detach(self):
        if not self.attached:
            return False
        hwnd = self.hwnd
        parent, style = self._original_parent, self._original_style
        x, y, width, height = self._original_rect
        host_hwnd = self._host_hwnd
        try:
            self.api.set_parent(hwnd, parent)
            self.api.set_style(hwnd, style)
            self.api.position(hwnd, x, y, width, height)
        finally:
            self.hwnd = None
            self._original_parent = None
            self._original_style = None
            self._original_rect = None
            self._host_hwnd = None
            self.api.invalidate(host_hwnd)
        return True
