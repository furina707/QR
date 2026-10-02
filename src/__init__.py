# -*- coding: utf-8 -*-
"""QR 智能工作台 (QR Master) 核心代码包

遵循《项目准则.md》：
1. 核心代码全部组织在 src/ 内部
2. 统一启动器为项目根目录的 run.py
3. 术语与缩写定义详见 src/abbreviations.py
"""

from __future__ import annotations

from .app import QRMasterApp, main
from .qr_engine import engine, QREngine, QRDecodeResult
from .screen_capture import capture_region, capture_monitor, capture_all_screens, get_monitors

__version__ = "2.0.0"
__all__ = [
    "QRMasterApp",
    "main",
    "engine",
    "QREngine",
    "QRDecodeResult",
    "capture_region",
    "capture_monitor",
    "capture_all_screens",
    "get_monitors",
]
