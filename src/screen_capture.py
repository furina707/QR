# -*- coding: utf-8 -*-
"""Windows 原生 GDI 高性能屏幕捕获模块 (Screen Capture via GDI)

技术特性与缩写说明：
- GDI: Graphics Device Interface（Windows 图形设备接口），利用底层原生 BitBlt 抓屏，毫秒级响应，零外部驱动。
- DPI: Dots Per Inch，完美支持高分屏多显示器缩放比例，像素级对齐。
- ROI: Region of Interest（感兴趣区域），精准裁切指定矩形区域，最小化资源开销。
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import sys
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

from .utils import enable_dpi_awareness


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class MonitorInfo:
    def __init__(self, index: int, left: int, top: int, right: int, bottom: int, is_primary: bool = False):
        self.index = index
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
        self.width = right - left
        self.height = bottom - top
        self.is_primary = is_primary

    @property
    def name(self) -> str:
        tag = " (主显示器)" if self.is_primary else ""
        return f"显示器 {self.index + 1}: {self.width}x{self.height} (位置: {self.left},{self.top}){tag}"

    def to_dict(self) -> Dict:
        return {
            "index": self.index,
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
            "is_primary": self.is_primary,
            "name": self.name,
        }


def get_monitors() -> List[MonitorInfo]:
    """枚举当前系统连接的所有物理显示器及其坐标信息"""
    enable_dpi_awareness()
    monitors: List[MonitorInfo] = []

    if sys.platform == "win32":
        user32 = ctypes.windll.user32

        def _enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
            r = lprcMonitor.contents
            # 检查是否为主显示器 (0, 0 为主显示器原点)
            is_primary = (r.left == 0 and r.top == 0)
            idx = len(monitors)
            monitors.append(MonitorInfo(idx, r.left, r.top, r.right, r.bottom, is_primary))
            return True

        MONITORENUMPROC = ctypes.WINFUNCTYPE(
            ctypes.c_bool,
            wintypes.HMONITOR,
            wintypes.HDC,
            ctypes.POINTER(wintypes.RECT),
            wintypes.LPARAM,
        )
        proc = MONITORENUMPROC(_enum_proc)
        user32.EnumDisplayMonitors(0, 0, proc, 0)

    # 兜底：若枚举为空，使用主屏幕尺寸
    if not monitors:
        if sys.platform == "win32":
            u = ctypes.windll.user32
            w = u.GetSystemMetrics(0)
            h = u.GetSystemMetrics(1)
            monitors.append(MonitorInfo(0, 0, 0, w, h, True))
        else:
            monitors.append(MonitorInfo(0, 0, 0, 1920, 1080, True))

    return monitors


def get_virtual_screen_bounds() -> Tuple[int, int, int, int]:
    """获取跨所有显示器的完整虚拟屏幕区域 (left, top, width, height)"""
    enable_dpi_awareness()
    if sys.platform == "win32":
        u = ctypes.windll.user32
        SM_XVIRTUALSCREEN = 76
        SM_YVIRTUALSCREEN = 77
        SM_CXVIRTUALSCREEN = 78
        SM_CYVIRTUALSCREEN = 79
        x = u.GetSystemMetrics(SM_XVIRTUALSCREEN)
        y = u.GetSystemMetrics(SM_YVIRTUALSCREEN)
        w = u.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        h = u.GetSystemMetrics(SM_CYVIRTUALSCREEN)
        if w > 0 and h > 0:
            return x, y, w, h

    mons = get_monitors()
    min_x = min(m.left for m in mons)
    min_y = min(m.top for m in mons)
    max_x = max(m.right for m in mons)
    max_y = max(m.bottom for m in mons)
    return min_x, min_y, max_x - min_x, max_y - min_y


def capture_region(x: int, y: int, width: int, height: int) -> Optional[Image.Image]:
    """利用 Windows GDI 原生截取指定屏幕矩形区域 (ROI)

    参数：
        x: 左上角全局 X 坐标
        y: 左上角全局 Y 坐标
        width: 区域宽度 (像素)
        height: 区域高度 (像素)
    返回：
        PIL Image 对象 (RGB 模式) 或 None
    """
    if width <= 0 or height <= 0:
        return None

    enable_dpi_awareness()

    if sys.platform == "win32":
        try:
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32

            hdc_screen = user32.GetDC(0)
            if not hdc_screen:
                return None

            hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
            if not hdc_mem:
                user32.ReleaseDC(0, hdc_screen)
                return None

            hbm = gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
            if not hbm:
                gdi32.DeleteDC(hdc_mem)
                user32.ReleaseDC(0, hdc_screen)
                return None

            old_bmp = gdi32.SelectObject(hdc_mem, hbm)

            SRCCOPY = 0x00CC0020
            CAPTUREBLT = 0x40000000
            # 执行底层位图位块拷贝
            gdi32.BitBlt(hdc_mem, 0, 0, width, height, hdc_screen, x, y, SRCCOPY | CAPTUREBLT)

            bmi = BITMAPINFOHEADER()
            bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.biWidth = width
            bmi.biHeight = -height  # 负高代表从上往下扫描 (Top-down DIB)
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            bmi.biCompression = 0

            buf_size = width * height * 4
            buffer = (ctypes.c_ubyte * buf_size)()
            lines = gdi32.GetDIBits(hdc_mem, hbm, 0, height, ctypes.byref(buffer), ctypes.byref(bmi), 0)

            # 恢复并释放 GDI 对象
            gdi32.SelectObject(hdc_mem, old_bmp)
            gdi32.DeleteObject(hbm)
            gdi32.DeleteDC(hdc_mem)
            user32.ReleaseDC(0, hdc_screen)

            if lines > 0:
                # 内存转为 numpy array: BGRA 格式
                arr = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, 4))
                # 提取 RGB 丢弃 Alpha 通道
                rgb_arr = arr[:, :, [2, 1, 0]]
                return Image.fromarray(rgb_arr, mode="RGB")
        except Exception:
            pass

    # 非 Windows 或 GDI 异常时的备用方案：Pillow ImageGrab
    try:
        from PIL import ImageGrab
        return ImageGrab.grab(bbox=(x, y, x + width, y + height), all_screens=True)
    except Exception:
        return None


def capture_monitor(monitor_index: int = 0) -> Optional[Image.Image]:
    """截取指定索引的显示器全屏画面"""
    mons = get_monitors()
    if 0 <= monitor_index < len(mons):
        m = mons[monitor_index]
        return capture_region(m.left, m.top, m.width, m.height)
    return None


def capture_all_screens() -> Optional[Image.Image]:
    """截取跨所有显示器的完整虚拟屏幕"""
    vx, vy, vw, vh = get_virtual_screen_bounds()
    return capture_region(vx, vy, vw, vh)
