# core/usb_monitor.py

import ctypes
import ctypes.wintypes as wintypes
from PyQt5.QtCore import QThread, pyqtSignal

WM_DEVICECHANGE          = 0x0219
DBT_DEVICEARRIVAL        = 0x8000
DBT_DEVICEREMOVECOMPLETE = 0x8004
DBT_DEVTYP_VOLUME        = 0x00000002
CS_VREDRAW               = 0x0001
CS_HREDRAW               = 0x0002

WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_long,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style",         wintypes.UINT),
        ("lpfnWndProc",   WNDPROC),
        ("cbClsExtra",    ctypes.c_int),
        ("cbWndExtra",    ctypes.c_int),
        ("hInstance",     wintypes.HINSTANCE),
        ("hIcon",         wintypes.HICON),
        ("hCursor",       wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName",  wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class DEV_BROADCAST_HDR(ctypes.Structure):
    _fields_ = [
        ("dbch_size",       wintypes.DWORD),
        ("dbch_devicetype", wintypes.DWORD),
        ("dbch_reserved",   wintypes.DWORD),
    ]


class DEV_BROADCAST_VOLUME(ctypes.Structure):
    _fields_ = [
        ("dbcv_size",       wintypes.DWORD),
        ("dbcv_devicetype", wintypes.DWORD),
        ("dbcv_reserved",   wintypes.DWORD),
        ("dbcv_unitmask",   wintypes.DWORD),
        ("dbcv_flags",      wintypes.WORD),
    ]


class USBMonitor(QThread):
    device_connected    = pyqtSignal(str)
    device_disconnected = pyqtSignal(str)

    _CLASS_NAME = "DLP_USB_Monitor_Wnd"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hwnd        = None
        self._running     = False
        self._wndproc_ref = None

    def stop(self):
        self._running = False
        if self._hwnd:
            ctypes.windll.user32.PostMessageW(self._hwnd, 0x0012, 0, 0)
        self.wait(3000)

    def run(self):
        user32   = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        self._wndproc_ref = WNDPROC(self._wnd_proc)

        # Получаем hInstance и сразу приводим к HINSTANCE
        hinstance = wintypes.HINSTANCE(kernel32.GetModuleHandleW(None))

        wc               = WNDCLASSW()
        wc.style         = CS_VREDRAW | CS_HREDRAW
        wc.lpfnWndProc   = self._wndproc_ref
        wc.hInstance     = hinstance
        wc.lpszClassName = self._CLASS_NAME

        if not user32.RegisterClassW(ctypes.byref(wc)):
            err = kernel32.GetLastError()
            if err != 1410:  # 1410 = уже зарегистрирован — ок
                print(f"[USB] RegisterClassW error: {err}")
                return

        # Передаём hinstance через ctypes.c_void_p чтобы избежать OverflowError
        self._hwnd = user32.CreateWindowExW(
            0,
            self._CLASS_NAME,
            "DLP USB Monitor",
            0,           # WS_OVERLAPPED
            0, 0, 0, 0,
            None,
            None,
            hinstance,
            None
        )

        if not self._hwnd:
            print(f"[USB] CreateWindowExW error: {kernel32.GetLastError()}")
            user32.UnregisterClassW(self._CLASS_NAME, hinstance)
            return

        self._running = True
        print("[USB] USB monitoring started.")

        msg = wintypes.MSG()
        while self._running:
            if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                if msg.message == 0x0012:  # WM_QUIT
                    break
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            else:
                self.msleep(50)

        user32.DestroyWindow(self._hwnd)
        user32.UnregisterClassW(self._CLASS_NAME, hinstance)
        self._hwnd = None
        print("[USB] USB monitoring stopped.")

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_DEVICECHANGE:
            if wparam in (DBT_DEVICEARRIVAL, DBT_DEVICEREMOVECOMPLETE):
                drive = self._parse_drive(lparam)
                if wparam == DBT_DEVICEARRIVAL:
                    print(f"[USB ALERT] Connected: {drive or 'unknown'}")
                    self.device_connected.emit(drive)
                else:
                    print(f"[USB] Disconnected: {drive or 'unknown'}")
                    self.device_disconnected.emit(drive)
        return ctypes.windll.user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    @staticmethod
    def _parse_drive(lparam):
        if not lparam:
            return ""
        try:
            hdr = DEV_BROADCAST_HDR.from_address(lparam)
            if hdr.dbch_devicetype != DBT_DEVTYP_VOLUME:
                return ""
            vol = DEV_BROADCAST_VOLUME.from_address(lparam)
            for i in range(26):
                if vol.dbcv_unitmask & (1 << i):
                    return chr(65 + i) + ":\\"
        except Exception as e:
            print(f"[USB] Drive parse error: {e}")
        return ""