# -*- coding: utf-8 -*-
"""本项目涉及的所有术语缩写具体含义介绍 (Glossary of Abbreviations)

严格遵循《项目准则.md》第 4 条：“需要缩写的具体含义介绍”。
在此模块中集中定义并系统性阐释本项目所涉及的全部技术缩写，
供应用界面、帮助文档、控制台输出及代码注释中统一引用。
"""

from __future__ import annotations

from typing import Dict, List, TypedDict


class AbbreviationInfo(TypedDict):
    abbr: str          # 缩写名称 (Abbreviation)
    full_en: str       # 英文全称 (Full English Term)
    full_zh: str       # 中文名称 (Full Chinese Term)
    category: str      # 技术领域分类 (Category)
    description: str   # 详细定义与本项目中的具体应用 (Detailed Description & Usage)


# 术语缩写完整映射词典
ABBREVIATIONS: Dict[str, AbbreviationInfo] = {
    "QR": {
        "abbr": "QR",
        "full_en": "Quick Response code",
        "full_zh": "快速响应矩阵条码（二维码）",
        "category": "编码与图形识别",
        "description": (
            "1994年由日本 Denso Wave 公司发明的一种二维矩阵式条形码。"
            "具有超高识读速度（Quick Response）、全方位 360° 可读性、"
            "大容量数据存储（可编码数千字符）和强大的 Reed-Solomon 纠错能力。"
            "在本工程中代表核心业务：屏幕/图片/摄像头中的二维码识别与生成。"
        ),
    },
    "GUI": {
        "abbr": "GUI",
        "full_en": "Graphical User Interface",
        "full_zh": "图形用户界面",
        "category": "人机交互",
        "description": (
            "采用图形方式显示的计算机操作用户界面。相较于纯文本命令行界面（CLI），"
            "GUI 提供直观的窗口、标签页、按钮、滑块、画布及实时预览。"
            "本项目基于 CustomTkinter / Tkinter 构建现代化原生 GUI 桌面客户端。"
        ),
    },
    "UI": {
        "abbr": "UI",
        "full_en": "User Interface",
        "full_zh": "用户界面",
        "category": "前端与人机交互",
        "description": (
            "用户与系统之间进行交互与信息传递的媒介与视觉表现层，"
            "包含色彩搭配、组件排版、间距、字体及动画效果。"
        ),
    },
    "CLI": {
        "abbr": "CLI",
        "full_en": "Command Line Interface",
        "full_zh": "命令行接口",
        "category": "人机交互",
        "description": (
            "通过终端文本命令与程序进行交互的方式。本工程以 run.py 统一引导，"
            "支持传参启动或直接拉起 GUI 桌面窗口。"
        ),
    },
    "DPI": {
        "abbr": "DPI",
        "full_en": "Dots Per Inch",
        "full_zh": "每英寸点数（屏幕缩放/分辨率密度）",
        "category": "显示与系统底层",
        "description": (
            "衡量屏幕物理显示精细度与系统缩放比例（如 125%、150%、200%）的核心参数。"
            "在 Windows 系统上，如果不开启 DPI-Awareness（DPI 感知），"
            "截屏和框选窗口会因系统虚拟缩放而产生坐标偏移与模糊。"
            "本项目在启动时立即启用高 DPI 感知以保证像素级精准截图。"
        ),
    },
    "GDI": {
        "abbr": "GDI",
        "full_en": "Graphics Device Interface",
        "full_zh": "Windows 图形设备接口",
        "category": "操作系统底层 API",
        "description": (
            "微软 Windows 操作系统的核心图形子系统，用于与显卡通信并管理设备上下文（HDC）。"
            "本项目利用 GDI 中的 BitBlt（位块传输）与 GetDIBits 原生底层 API，"
            "实现无外部第三方驱动依赖、跨多显示器、毫秒级的纯原生超快屏幕捕获。"
        ),
    },
    "ROI": {
        "abbr": "ROI",
        "full_en": "Region of Interest",
        "full_zh": "感兴趣区域 / 目标检测子区",
        "category": "计算机视觉与图像处理",
        "description": (
            "图像处理中从完整画面中截取或圈定的特定子区域。"
            "本项目中指用户在屏幕上用鼠标框选出来的矩形区域，"
            "只针对该区域持续采集并识别，极大节省 CPU/GPU 算力，提升识别帧率。"
        ),
    },
    "ECC": {
        "abbr": "ECC",
        "full_en": "Error Correction Code",
        "full_zh": "纠错码 / 容错级别",
        "category": "信息论与编码算法",
        "description": (
            "QR 码采用 Reed-Solomon 纠错算法，允许在二维码遭受磨损、污损、遮挡或失真时"
            "依然能够正确无损还原数据。分为四个级别："
            "L (Low: 约可纠错 7%)、M (Medium: 约 15%)、"
            "Q (Quartile: 约 25%)、H (High: 约 30%)。"
            "本项目在二维码生成器中提供 ECC 级别的自由选择与配置。"
        ),
    },
    "FPS": {
        "abbr": "FPS",
        "full_en": "Frames Per Second",
        "full_zh": "每秒传输帧数（帧率/刷新率）",
        "category": "性能与实时处理",
        "description": (
            "屏幕持续抓取或摄像头视频流每秒分析的图像帧数。"
            "本项目提供可调扫描频率（如 50ms - 500ms），在高性能识别与极低能耗间取得最佳平衡。"
        ),
    },
    "URL": {
        "abbr": "URL",
        "full_en": "Uniform Resource Locator",
        "full_zh": "统一资源定位符（网络网址）",
        "category": "网络与协议",
        "description": (
            "互联网上标准资源的地址格式（如 https://...）。"
            "QR 码最常见的载荷为 URL，本项目内置协议识别，识别后可一键在默认浏览器中安全打开。"
        ),
    },
    "RGB": {
        "abbr": "RGB",
        "full_en": "Red, Green, Blue",
        "full_zh": "红绿蓝三原色色彩模式",
        "category": "色彩空间与图像格式",
        "description": (
            "显示器色彩呈现的加色混合模型。每像素由红、绿、蓝 3 通道组成（常见 8-bit 每通道，共 24-bit）。"
            "OpenCV 默认读写为 BGR 顺序，本项目在引擎间流转时进行了标准化色彩空间转换。"
        ),
    },
    "RGBA": {
        "abbr": "RGBA",
        "full_en": "Red, Green, Blue, Alpha",
        "full_zh": "包含透明度通道的红绿蓝色彩模式",
        "category": "色彩空间与图像格式",
        "description": (
            "在 RGB 基础上增加 Alpha 透明度通道（8-bit，共 32-bit）。"
            "在本项目屏幕框选遮罩层（Overlay）及半透明取色/边框绘制中广泛使用。"
        ),
    },
    "JSON": {
        "abbr": "JSON",
        "full_en": "JavaScript Object Notation",
        "full_zh": "轻量级数据交换格式",
        "category": "数据持久化与协议",
        "description": (
            "人类易读、轻量且与语言无关的结构化文本格式。"
            "本项目用于本地永久存储识别历史记录（history.json）和用户偏好配置。"
        ),
    },
    "OS": {
        "abbr": "OS",
        "full_en": "Operating System",
        "full_zh": "操作系统",
        "category": "系统平台",
        "description": (
            "管理计算机硬件与软件资源的系统软件。本项目专注于 Windows 平台优化"
            "（DPI、GDI 截图、原生剪贴板），同时核心解码引擎具备良好跨平台兼容性。"
        ),
    },
    "PNG": {
        "abbr": "PNG",
        "full_en": "Portable Network Graphics",
        "full_zh": "便携式网络图形（无损压缩图像格式）",
        "category": "多媒体与文件格式",
        "description": (
            "支持无损压缩与透明通道的位图文件格式，是保存和导出二维码图像的首选标准格式。"
        ),
    },
    "API": {
        "abbr": "API",
        "full_en": "Application Programming Interface",
        "full_zh": "应用程序编程接口",
        "category": "软件工程",
        "description": (
            "模块、系统底层库或第三方服务之间约定的通信与调用接口。"
            "本项目涵盖了 Win32 系统 API、OpenCV API、Pillow 图像 API 等多层级调用。"
        ),
    },
}


def get_abbreviations_list() -> List[AbbreviationInfo]:
    """返回所有术语缩写的有序列表"""
    return list(ABBREVIATIONS.values())


def get_abbreviation(abbr: str) -> AbbreviationInfo | None:
    """根据缩写词检索具体释义"""
    return ABBREVIATIONS.get(abbr.upper())


def format_markdown_table() -> str:
    """生成术语缩写对照表的 Markdown 格式文本，可直接嵌入文档"""
    lines = [
        "| 缩写 | 英文全称 (Full English) | 中文名称 | 领域分类 | 具体含义与本项目中的应用 |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for item in ABBREVIATIONS.values():
        desc = item["description"].replace("\n", " ")
        lines.append(
            f"| **{item['abbr']}** | `{item['full_en']}` | {item['full_zh']} | {item['category']} | {desc} |"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_markdown_table())
