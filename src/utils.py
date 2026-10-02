# -*- coding: utf-8 -*-
"""通用实用工具模块 (Utilities)

包含：
- Windows DPI (Dots Per Inch) 高分辨率缩放适配
- 系统剪贴板交互（文本复制、图片写入 Windows CF_DIB 原生剪贴板）
- URL 判定与系统默认浏览器快速打开
- 成功解码音效与震鸣提示
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import io
import re
import sys
import webbrowser
from typing import Optional

from PIL import Image


def enable_dpi_awareness() -> bool:
    """开启 Windows 系统的进程级 DPI (Dots Per Inch) 缩放感知

    防止高分屏下屏幕截图坐标错位及界面文字模糊。
    返回 True 表示设置成功。
    """
    if sys.platform != "win32":
        return False
    try:
        # PROCESS_PER_MONITOR_DPI_AWARE = 2
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return True
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
            return True
        except Exception:
            return False


def copy_text_to_clipboard(text: str) -> bool:
    """将文本复制到 Windows 系统剪贴板"""
    if not text:
        return False
    if sys.platform == "win32":
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        CF_UNICODETEXT = 13
        GMEM_MOVEABLE = 0x0002

        kernel32.GlobalAlloc.restype = ctypes.c_void_p
        kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]

        user32.OpenClipboard.argtypes = [wintypes.HWND]
        user32.SetClipboardData.restype = ctypes.c_void_p
        user32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]

        encoded = text.encode("utf-16le") + b"\x00\x00"
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
        if not h_mem:
            return False

        ptr = kernel32.GlobalLock(h_mem)
        if ptr:
            ctypes.memmove(ptr, encoded, len(encoded))
            kernel32.GlobalUnlock(h_mem)

            if user32.OpenClipboard(0):
                user32.EmptyClipboard()
                user32.SetClipboardData(CF_UNICODETEXT, h_mem)
                user32.CloseClipboard()
                return True
    return False


def copy_image_to_clipboard(image: Image.Image) -> bool:
    """将 PIL Image 图像复制到 Windows 系统剪贴板 (CF_DIB 格式)"""
    if sys.platform != "win32" or image is None:
        return False

    try:
        output = io.BytesIO()
        image.convert("RGB").save(output, "BMP")
        # BMP 文件前 14 字节为 BITMAPFILEHEADER，DIB 数据从第 14 字节开始
        dib_data = output.getvalue()[14:]
        output.close()

        GMEM_MOVEABLE = 0x0002
        CF_DIB = 8

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        kernel32.GlobalAlloc.restype = ctypes.c_void_p
        kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]

        user32.OpenClipboard.argtypes = [wintypes.HWND]
        user32.SetClipboardData.restype = ctypes.c_void_p
        user32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]

        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(dib_data))
        if not h_mem:
            return False

        mem_ptr = kernel32.GlobalLock(h_mem)
        if not mem_ptr:
            return False

        ctypes.memmove(mem_ptr, dib_data, len(dib_data))
        kernel32.GlobalUnlock(h_mem)

        if user32.OpenClipboard(0):
            user32.EmptyClipboard()
            user32.SetClipboardData(CF_DIB, h_mem)
            user32.CloseClipboard()
            return True
    except Exception:
        pass
    return False


def read_image_from_clipboard() -> Optional[Image.Image]:
    """从系统剪贴板读取位图图像"""
    try:
        from PIL import ImageGrab
        im = ImageGrab.grabclipboard()
        if isinstance(im, Image.Image):
            return im
    except Exception:
        pass
    return None


_URL_REGEX = re.compile(
    r"^(?:(?:https?|ftp)://|www\.)[^\s/$.?#].[^\s]*$",
    re.IGNORECASE,
)


def is_url(text: str) -> bool:
    """判断字符串是否为合法 URL"""
    if not text:
        return False
    text = text.strip()
    return bool(_URL_REGEX.match(text))


def open_url_in_browser(url: str) -> bool:
    """在系统默认浏览器中打开指定链接"""
    if not url:
        return False
    clean_url = url.strip()
    if clean_url.startswith("www."):
        clean_url = "https://" + clean_url
    try:
        webbrowser.open(clean_url)
        return True
    except Exception:
        return False


def play_success_sound() -> None:
    """播放解码成功系统提示音效"""
    if sys.platform == "win32":
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass
