# -*- coding: utf-8 -*-
"""应用常量与配置参数 (Constants and Configurations)

集中管理整个二维码桌面工具箱所用到的全局常量、配色规范与默认路径。
"""

from __future__ import annotations

import os
import sys

# 应用程序元信息
APP_NAME = "QR 智能工作台"
APP_SUBTITLE = "桌面二维码全功能工具箱 (QR Master)"
APP_VERSION = "2.0.0"
APP_AUTHOR = "Google DeepMind Pair-Programming"

# 路径常量
# 定位本工程根目录 (即 C:\Users\cytsh\Desktop\.project\QR)
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SRC_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")

# 确保数据存储目录存在
os.makedirs(DATA_DIR, exist_ok=True)

# 默认扫描参数
DEFAULT_SCAN_INTERVAL_MS = 60          # 持续扫码轮询间隔 (毫秒)
MIN_SCAN_INTERVAL_MS = 30              # 最小扫描间隔
MAX_SCAN_INTERVAL_MS = 500             # 最大扫描间隔
SCREEN_CHANGE_THRESHOLD = 0.8          # 画面变动检测阈值 (降低无意义解码开销)

# 容错等级映射 (ECC: Error Correction Code)
# 对应 qrcode 库的 constants
ECC_LEVELS = {
    "L (低 - 容错约 7%)": "L",
    "M (中 - 容错约 15% 推荐)": "M",
    "Q (高 - 容错约 25%)": "Q",
    "H (极高 - 容错约 30%)": "H",
}

# 预设二维码配色方案 (前景色, 背景色, 显示名称)
QR_COLOR_PRESETS = [
    ("#000000", "#FFFFFF", "经典黑白 (Classic)"),
    ("#0F52BA", "#FFFFFF", "商务宝石蓝 (Sapphire Blue)"),
    ("#1B4D3E", "#FFFFFF", "森林深绿 (Forest Green)"),
    ("#5B2C6F", "#FFFFFF", "优雅紫罗兰 (Deep Purple)"),
    ("#B03A2E", "#FFFFFF", "赤红烈火 (Crimson)"),
    ("#E67E22", "#FFFFFF", "活力暖橙 (Warm Orange)"),
    ("#FFFFFF", "#1E1E2E", "极客反色暗夜 (Dark Mode)"),
]

# UI 视觉规范 (CustomTkinter 现代配色)
THEME_MODE = "dark"                   # "dark" / "light" / "system"
COLOR_THEME = "blue"                  # 内置预设主题

# 窗口初始尺寸
DEFAULT_WINDOW_WIDTH = 960
DEFAULT_WINDOW_HEIGHT = 700
MIN_WINDOW_WIDTH = 840
MIN_WINDOW_HEIGHT = 600
