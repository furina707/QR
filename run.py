#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QR 智能工作台 (QR Master) 唯一统一启动器

严格遵循《项目准则.md》：
1. 不使用 bat，sh，ps1 这种文件，统一使用唯一的 run.py 作为启动器。
2. 核心代码都放在 "src" 文件夹里面。
3. 术语与缩写定义详见 src/abbreviations.py 与 README.md。

支持两种启动模式：
- 默认无参运行：直接拉起现代化原生 GUI 桌面客户端窗口。
- 命令行 CLI 模式：
    python run.py --help                查看帮助与术语说明
    python run.py --version             查看版本与架构信息
    python run.py --glossary            打印全部技术缩写词典
    python run.py --decode <image_path> 快速解码指定图像文件
    python run.py --generate <text>     快速生成二维码并保存
"""

from __future__ import annotations

import argparse
import os
import sys

# 1. 确保 Windows 控制台具备完整的 UTF-8 编解码能力，防止中文输出乱码
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 2. 定位项目路径，确保可直接导入 src 模块
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def check_dependencies() -> bool:
    """依赖环境检查与友好提示"""
    missing = []
    for mod in ["customtkinter", "cv2", "PIL", "qrcode", "numpy"]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)

    if missing:
        print("[错误] 检测到当前 Python 环境缺失关键依赖模块：")
        for m in missing:
            print(f"  - {m}")
        print("\n请在终端运行以下命令一键安装完整依赖：")
        print("  pip install -r requirements.txt\n")
        return False
    return True


def run_cli(args: argparse.Namespace) -> int:
    """命令行 CLI 模式分流处理"""
    if args.version:
        from src.constants import APP_NAME, APP_VERSION, APP_SUBTITLE
        print(f"{APP_NAME} v{APP_VERSION} - {APP_SUBTITLE}")
        print("遵循《项目准则.md》全架构 Python 原生重构版。")
        return 0

    if args.glossary:
        from src.abbreviations import format_markdown_table
        print("\n" + format_markdown_table() + "\n")
        return 0

    if args.decode:
        from src.qr_engine import engine
        img_path = args.decode
        if not os.path.exists(img_path):
            print(f"[错误] 目标图片文件不存在: {img_path}")
            return 1
        print(f"[*] 正在分析图片: {img_path} ...")
        res = engine.decode(img_path)
        if res and res.text:
            print("\n[√] 二维码识别成功！")
            print(f"  - 解码引擎: {res.engine}")
            print(f"  - 是否网址: {'是' if res.is_url else '否'}")
            print(f"  - 识别内容:\n{res.text}\n")
            return 0
        else:
            print("[×] 未在图片中检测到有效二维码。")
            return 2

    if args.generate:
        from src.qr_engine import engine
        text = args.generate
        out_path = args.out or "generated_qr.png"
        ecc = args.ecc or "M"
        print(f"[*] 正在生成二维码 (ECC: {ecc}) ...")
        img = engine.generate(text=text, ecc_level=ecc)
        if img:
            img.save(out_path)
            print(f"[√] 二维码已成功保存至: {os.path.abspath(out_path)}")
            return 0
        else:
            print("[×] 二维码生成失败。")
            return 1

    return 0


def main():
    """主启动流程"""
    parser = argparse.ArgumentParser(
        prog="python run.py",
        description="QR 智能工作台 - 桌面二维码全功能工具箱 (遵循项目准则.md 唯一启动器)",
    )
    parser.add_argument("-v", "--version", action="store_true", help="显示程序版本信息")
    parser.add_argument("-g", "--glossary", action="store_true", help="显示所有技术缩写与术语释义词典")
    parser.add_argument("-d", "--decode", metavar="IMAGE_PATH", help="命令行直接解码指定图片")
    parser.add_argument("-gen", "--generate", metavar="TEXT", help="命令行直接生成二维码图片")
    parser.add_argument("-o", "--out", metavar="OUT_PATH", help="指定生成的二维码图片保存路径 (默认为 generated_qr.png)")
    parser.add_argument("-e", "--ecc", choices=["L", "M", "Q", "H"], default="M", help="二维码纠错容错级别 (默认 M)")

    args = parser.parse_args()

    # 如果有特定命令行选项，进入 CLI 处理
    if args.version or args.glossary or args.decode or args.generate:
        if not check_dependencies():
            sys.exit(1)
        sys.exit(run_cli(args))

    # 默认无参：启动现代化 GUI 桌面程序
    if not check_dependencies():
        sys.exit(1)

    from src.utils import enable_dpi_awareness
    enable_dpi_awareness()

    from src.app import main as gui_main
    gui_main()


if __name__ == "__main__":
    main()
