# -*- coding: utf-8 -*-
"""QR 智能工作台主界面 (Main Graphical User Interface)

技术特性与缩写说明：
- GUI: Graphical User Interface（基于 CustomTkinter 构建的高质感原生图形界面）。
- DPI: 高分屏像素自适应缩放。
- ROI: 屏幕框选与实时扫描管道集成。
- 多功能一体化：屏幕框选、全屏快扫、本地图片/剪贴板图像解码、摄像头实时扫码、专业级二维码生成、历史管理与术语速查。
"""

from __future__ import annotations

from datetime import datetime
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter as ctk
import numpy as np
from PIL import Image, ImageTk

from .abbreviations import get_abbreviations_list
from .camera import CameraScannerThread, get_available_cameras
from .constants import (
    APP_NAME,
    APP_SUBTITLE,
    APP_VERSION,
    COLOR_THEME,
    DEFAULT_SCAN_INTERVAL_MS,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    ECC_LEVELS,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    QR_COLOR_PRESETS,
    THEME_MODE,
)
from .history import history_manager
from .overlay import ScreenSelectorOverlay
from .qr_engine import engine, QRDecodeResult
from .screen_capture import (
    capture_all_screens,
    capture_monitor,
    capture_region,
    get_monitors,
)
from .utils import (
    copy_image_to_clipboard,
    copy_text_to_clipboard,
    is_url,
    open_url_in_browser,
    play_success_sound,
    read_image_from_clipboard,
)

# 初始化 CustomTkinter 外观主题
ctk.set_appearance_mode(THEME_MODE)
ctk.set_default_color_theme(COLOR_THEME)


class QRMasterApp(ctk.CTk):
    """QR 智能工作台主窗口应用程序"""

    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} v{APP_VERSION} - {APP_SUBTITLE}")
        self.geometry(f"{DEFAULT_WINDOW_WIDTH}x{DEFAULT_WINDOW_HEIGHT}")
        self.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

        # 核心扫描状态变量
        self.screen_roi: Optional[tuple[int, int, int, int]] = None
        self.is_screen_scanning: bool = False
        self.screen_after_id = None
        self.last_screen_hash = None

        # 摄像头线程状态
        self.camera_thread: Optional[CameraScannerThread] = None

        # 当前生成缓存
        self.current_generated_img: Optional[Image.Image] = None

        # 历史记录最新缓存
        self.last_decoded_text: str = ""

        # 构建主界面结构
        self._build_header()
        self._build_tabview()

        # 窗口关闭事件钩子
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_header(self):
        """构建顶部导航与状态条"""
        self.header_frame = ctk.CTkFrame(self, height=54, corner_radius=0, fg_color=("gray90", "#181825"))
        self.header_frame.pack(fill="x", side="top", padx=0, pady=0)

        # 品牌 LOGO 与主标题
        title_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=16, pady=8)

        logo_label = ctk.CTkLabel(
            title_box,
            text="⚡ " + APP_NAME,
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=18, weight="bold"),
            text_color=("#1D4ED8", "#60A5FA"),
        )
        logo_label.pack(side="left")

        ver_label = ctk.CTkLabel(
            title_box,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        ver_label.pack(side="left", padx=(8, 0))

        # 顶部右侧：主题切换与状态指示
        right_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        right_box.pack(side="right", padx=16, pady=8)

        self.status_chip = ctk.CTkLabel(
            right_box,
            text="● 就绪",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=12),
            text_color="#10B981",
        )
        self.status_chip.pack(side="left", padx=(0, 16))

        self.theme_switch = ctk.CTkSwitch(
            right_box,
            text="暗夜模式",
            command=self._toggle_theme,
            onvalue="dark",
            offvalue="light",
        )
        self.theme_switch.select()
        self.theme_switch.pack(side="left")

    def _build_tabview(self):
        """构建功能选项卡容器"""
        self.tabview = ctk.CTkTabview(self, corner_radius=8)
        self.tabview.pack(fill="both", expand=True, padx=12, pady=(6, 12))

        # 添加 6 大核心功能标签页
        self.tab_screen = self.tabview.add("🖥️ 屏幕扫码")
        self.tab_image = self.tabview.add("🖼️ 图片/剪贴板")
        self.tab_camera = self.tabview.add("📷 摄像头扫码")
        self.tab_gen = self.tabview.add("⚡ 二维码生成")
        self.tab_history = self.tabview.add("📜 历史记录")
        self.tab_about = self.tabview.add("📖 术语缩写与准则")

        # 逐页布局
        self._init_screen_tab()
        self._init_image_tab()
        self._init_camera_tab()
        self._init_history_tab()
        self._init_generator_tab()
        self._init_about_tab()

    # =========================================================================
    # Tab 1: 屏幕扫码 (Screen Scan)
    # =========================================================================
    def _init_screen_tab(self):
        tab = self.tab_screen

        # 左侧控制面板，右侧实时选区预览与结果
        split_frame = ctk.CTkFrame(tab, fg_color="transparent")
        split_frame.pack(fill="both", expand=True, padx=8, pady=8)

        left_panel = ctk.CTkFrame(split_frame, width=320, fg_color=("gray95", "#1E1E2E"))
        left_panel.pack(side="left", fill="y", padx=(0, 8), pady=0)
        left_panel.pack_propagate(False)

        right_panel = ctk.CTkFrame(split_frame, fg_color="transparent")
        right_panel.pack(side="right", fill="both", expand=True)

        # --- 控制区 ---
        ctk.CTkLabel(
            left_panel,
            text="屏幕捕获控制",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=15, weight="bold"),
        ).pack(anchor="w", padx=14, pady=(14, 8))

        # 显示器选择
        ctk.CTkLabel(left_panel, text="目标显示器:", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=14, pady=(4, 2))
        monitors = get_monitors()
        monitor_options = ["全虚拟屏 (跨多显示器)"] + [m.name for m in monitors]
        self.monitor_combo = ctk.CTkComboBox(left_panel, values=monitor_options, width=280)
        self.monitor_combo.set(monitor_options[0])
        self.monitor_combo.pack(padx=14, pady=(0, 10))

        # 核心触发按钮
        self.btn_select_roi = ctk.CTkButton(
            left_panel,
            text="🎯 框选屏幕区域并扫码",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=13, weight="bold"),
            height=38,
            command=self._start_screen_selection,
        )
        self.btn_select_roi.pack(fill="x", padx=14, pady=(4, 6))

        self.btn_fullscreen_scan = ctk.CTkButton(
            left_panel,
            text="⚡ 全屏一键扫码",
            height=34,
            fg_color=("#2563EB", "#1D4ED8"),
            command=self._scan_fullscreen_once,
        )
        self.btn_fullscreen_scan.pack(fill="x", padx=14, pady=4)

        self.btn_toggle_continuous = ctk.CTkButton(
            left_panel,
            text="▶ 开始实时持续扫码",
            height=34,
            fg_color=("#059669", "#047857"),
            hover_color=("#10B981", "#059669"),
            command=self._toggle_screen_scanning,
        )
        self.btn_toggle_continuous.pack(fill="x", padx=14, pady=4)

        # 扫描设置
        ctk.CTkLabel(
            left_panel,
            text="扫描参数与自动化",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=13, weight="bold"),
        ).pack(anchor="w", padx=14, pady=(16, 6))

        # 扫描间隔滑块
        self.slider_label = ctk.CTkLabel(left_panel, text=f"扫描周期: {DEFAULT_SCAN_INTERVAL_MS} ms", font=ctk.CTkFont(size=12))
        self.slider_label.pack(anchor="w", padx=14)

        self.interval_slider = ctk.CTkSlider(
            left_panel,
            from_=30,
            to=300,
            number_of_steps=27,
            command=self._on_interval_slider_change,
        )
        self.interval_slider.set(DEFAULT_SCAN_INTERVAL_MS)
        self.interval_slider.pack(fill="x", padx=14, pady=(0, 10))

        # 自动化选项
        self.chk_auto_copy = ctk.CTkCheckBox(left_panel, text="识别成功自动复制到剪贴板", font=ctk.CTkFont(size=12))
        self.chk_auto_copy.select()
        self.chk_auto_copy.pack(anchor="w", padx=14, pady=4)

        self.chk_auto_open = ctk.CTkCheckBox(left_panel, text="若为网址则自动在浏览器打开", font=ctk.CTkFont(size=12))
        self.chk_auto_open.pack(anchor="w", padx=14, pady=4)

        self.chk_beep = ctk.CTkCheckBox(left_panel, text="识别成功播放提示音效", font=ctk.CTkFont(size=12))
        self.chk_beep.select()
        self.chk_beep.pack(anchor="w", padx=14, pady=4)

        self.chk_auto_pause = ctk.CTkCheckBox(left_panel, text="识别成功后自动暂停持续扫码", font=ctk.CTkFont(size=12))
        self.chk_auto_pause.select()
        self.chk_auto_pause.pack(anchor="w", padx=14, pady=4)

        # --- 右侧：选区缩略图与识别结果 ---
        # 实时预览区域
        preview_box = ctk.CTkFrame(right_panel, height=220, fg_color=("gray90", "#181825"))
        preview_box.pack(fill="x", padx=4, pady=(0, 8))
        preview_box.pack_propagate(False)

        self.screen_preview_label = ctk.CTkLabel(
            preview_box,
            text="未设定屏幕选区\n点击左侧【框选屏幕区域】或【全屏一键扫码】",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        )
        self.screen_preview_label.pack(fill="both", expand=True, padx=8, pady=8)

        # 结果展示卡片
        res_card = ctk.CTkFrame(right_panel, fg_color=("gray95", "#1E1E2E"))
        res_card.pack(fill="both", expand=True, padx=4, pady=0)

        res_header = ctk.CTkFrame(res_card, fg_color="transparent")
        res_header.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            res_header,
            text="识别结果",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=14, weight="bold"),
        ).pack(side="left")

        self.screen_engine_badge = ctk.CTkLabel(
            res_header,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#60A5FA",
        )
        self.screen_engine_badge.pack(side="right")

        # 结果文本框
        self.screen_result_text = ctk.CTkTextbox(
            res_card,
            height=120,
            font=ctk.CTkFont(family="Consolas, Microsoft YaHei UI", size=13),
            wrap="word",
        )
        self.screen_result_text.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        # 动作工具栏
        btn_bar = ctk.CTkFrame(res_card, fg_color="transparent")
        btn_bar.pack(fill="x", padx=12, pady=(0, 12))

        self.btn_screen_copy = ctk.CTkButton(
            btn_bar,
            text="📋 复制内容",
            width=110,
            command=lambda: self._copy_text(self.screen_result_text.get("1.0", "end-1c")),
        )
        self.btn_screen_copy.pack(side="left", padx=(0, 8))

        self.btn_screen_open = ctk.CTkButton(
            btn_bar,
            text="🌐 打开链接",
            width=110,
            fg_color=("#059669", "#047857"),
            hover_color=("#10B981", "#059669"),
            command=lambda: self._open_text_url(self.screen_result_text.get("1.0", "end-1c")),
        )
        self.btn_screen_open.pack(side="left", padx=(0, 8))

        self.btn_screen_clear = ctk.CTkButton(
            btn_bar,
            text="清空",
            width=70,
            fg_color=("gray75", "gray30"),
            hover_color=("gray65", "gray40"),
            command=lambda: self.screen_result_text.delete("1.0", "end"),
        )
        self.btn_screen_clear.pack(side="right")

    def _on_interval_slider_change(self, value):
        val_int = int(value)
        self.slider_label.configure(text=f"扫描周期: {val_int} ms")

    def _start_screen_selection(self):
        """拉起交互式屏幕选区浮层"""
        self.withdraw()  # 暂时隐藏主窗口，方便框选
        self.after(200, self._open_overlay)

    def _open_overlay(self):
        ScreenSelectorOverlay(
            parent=self,
            on_selected=self._on_roi_selected,
            on_cancel=self._on_roi_cancel,
        )

    def _on_roi_selected(self, x: int, y: int, w: int, h: int):
        self.deiconify()
        self.screen_roi = (x, y, w, h)
        self.screen_preview_label.configure(text=f"选区已锁定: X={x}, Y={y}, 宽度={w}px, 高度={h}px\n正在执行识别...")
        # 立即扫描一次
        self._execute_screen_scan_step()
        # 若未启动持续扫码，自动启动持续扫码
        if not self.is_screen_scanning:
            self._toggle_screen_scanning()

    def _on_roi_cancel(self):
        self.deiconify()

    def _scan_fullscreen_once(self):
        """全屏快速单次扫描"""
        sel_idx = self.monitor_combo.get()
        im = None
        if "全虚拟屏" in sel_idx:
            im = capture_all_screens()
        else:
            # 解析显示器索引
            for m in get_monitors():
                if m.name in sel_idx:
                    im = capture_monitor(m.index)
                    break
            if im is None:
                im = capture_all_screens()

        if im:
            self._process_screen_image(im)
        else:
            messagebox.showwarning(APP_NAME, "无法截取屏幕画面，请检查权限。")

    def _toggle_screen_scanning(self):
        """开启或停止持续屏幕扫描"""
        if self.is_screen_scanning:
            self.is_screen_scanning = False
            self.btn_toggle_continuous.configure(
                text="▶ 开始实时持续扫码",
                fg_color=("#059669", "#047857"),
                hover_color=("#10B981", "#059669"),
            )
            self.status_chip.configure(text="● 待机", text_color="#9CA3AF")
            if self.screen_after_id:
                self.after_cancel(self.screen_after_id)
                self.screen_after_id = None
        else:
            if not self.screen_roi:
                # 若尚未选择选区，提示用户先框选
                self._start_screen_selection()
                return

            self.is_screen_scanning = True
            self.btn_toggle_continuous.configure(
                text="⏹ 停止持续扫码",
                fg_color=("#DC2626", "#B91C1C"),
                hover_color=("#EF4444", "#DC2626"),
            )
            self.status_chip.configure(text="● 正在屏幕扫码...", text_color="#3B82F6")
            self._continuous_screen_loop()

    def _continuous_screen_loop(self):
        """持续扫描循环体"""
        if not self.is_screen_scanning:
            return

        self._execute_screen_scan_step()

        interval = int(self.interval_slider.get())
        self.screen_after_id = self.after(interval, self._continuous_screen_loop)

    def _execute_screen_scan_step(self):
        """截取当前选区并执行解码"""
        if not self.screen_roi:
            return

        x, y, w, h = self.screen_roi
        im = capture_region(x, y, w, h)
        if im is None:
            return

        self._process_screen_image(im)

    def _process_screen_image(self, im: Image.Image):
        """处理截取的屏幕图像并更新界面"""
        # 显示缩略图预览
        preview_im = im.copy()
        preview_im.thumbnail((420, 180))
        photo = ctk.CTkImage(light_image=preview_im, dark_image=preview_im, size=preview_im.size)
        self.screen_preview_label.configure(image=photo, text="")
        self.screen_preview_label.image = photo

        # 解码检测
        res = engine.decode(im)
        if res and res.text:
            text = res.text
            if text != self.last_decoded_text:
                self.last_decoded_text = text
                self.screen_result_text.delete("1.0", "end")
                self.screen_result_text.insert("1.0", text)
                self.screen_engine_badge.configure(text=f"引擎: {res.engine}")

                # 记录到历史记录
                history_manager.add_record("屏幕扫描", text, res.engine)
                self._refresh_history_list()

                # 音效
                if self.chk_beep.get():
                    play_success_sound()

                # 自动复制
                if self.chk_auto_copy.get():
                    copy_text_to_clipboard(text)

                # 自动打开网址
                if self.chk_auto_open.get() and res.is_url:
                    open_url_in_browser(text)

                # 自动暂停持续扫码
                if self.chk_auto_pause.get() and self.is_screen_scanning:
                    self._toggle_screen_scanning()

    # =========================================================================
    # Tab 2: 图片与剪贴板 (Image & Clipboard)
    # =========================================================================
    def _init_image_tab(self):
        tab = self.tab_image

        layout = ctk.CTkFrame(tab, fg_color="transparent")
        layout.pack(fill="both", expand=True, padx=8, pady=8)

        # 操作栏
        toolbar = ctk.CTkFrame(layout, fg_color=("gray95", "#1E1E2E"), height=54)
        toolbar.pack(fill="x", padx=4, pady=(0, 8))

        btn_open_file = ctk.CTkButton(
            toolbar,
            text="📂 选择本地图片文件",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=13, weight="bold"),
            command=self._open_local_image_file,
        )
        btn_open_file.pack(side="left", padx=12, pady=10)

        btn_paste_clip = ctk.CTkButton(
            toolbar,
            text="📋 从剪贴板粘贴截图 (Ctrl+V)",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=13, weight="bold"),
            fg_color=("#2563EB", "#1D4ED8"),
            command=self._decode_from_clipboard,
        )
        btn_paste_clip.pack(side="left", padx=(0, 12), pady=10)

        # 快捷键支持
        self.bind("<Control-v>", lambda e: self._decode_from_clipboard())

        # 主内容区
        content_frame = ctk.CTkFrame(layout, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=4)

        # 左侧预览
        left_preview = ctk.CTkFrame(content_frame, fg_color=("gray90", "#181825"))
        left_preview.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.img_preview_label = ctk.CTkLabel(
            left_preview,
            text="暂无图片\n点击上方【选择本地图片】或直接粘贴剪贴板截图",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        )
        self.img_preview_label.pack(fill="both", expand=True, padx=12, pady=12)

        # 右侧解码结果
        right_res = ctk.CTkFrame(content_frame, width=340, fg_color=("gray95", "#1E1E2E"))
        right_res.pack(side="right", fill="both", padx=(6, 0))
        right_res.pack_propagate(False)

        res_head = ctk.CTkFrame(right_res, fg_color="transparent")
        res_head.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(res_head, text="图像解码结果", font=ctk.CTkFont(family="Microsoft YaHei UI", size=14, weight="bold")).pack(side="left")
        self.img_engine_badge = ctk.CTkLabel(res_head, text="", font=ctk.CTkFont(size=11), text_color="#60A5FA")
        self.img_engine_badge.pack(side="right")

        self.img_result_text = ctk.CTkTextbox(
            right_res,
            font=ctk.CTkFont(family="Consolas, Microsoft YaHei UI", size=13),
            wrap="word",
        )
        self.img_result_text.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        img_btn_bar = ctk.CTkFrame(right_res, fg_color="transparent")
        img_btn_bar.pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkButton(
            img_btn_bar,
            text="📋 复制",
            width=90,
            command=lambda: self._copy_text(self.img_result_text.get("1.0", "end-1c")),
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            img_btn_bar,
            text="🌐 打开",
            width=90,
            fg_color=("#059669", "#047857"),
            command=lambda: self._open_text_url(self.img_result_text.get("1.0", "end-1c")),
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            img_btn_bar,
            text="清空",
            width=60,
            fg_color=("gray75", "gray30"),
            command=lambda: self.img_result_text.delete("1.0", "end"),
        ).pack(side="right")

    def _open_local_image_file(self):
        """选择本地图片文件"""
        path = filedialog.askopenfilename(
            title="选择包含二维码的图片",
            filetypes=[
                ("常用图片格式", "*.png;*.jpg;*.jpeg;*.bmp;*.webp;*.tif"),
                ("PNG 图像", "*.png"),
                ("JPEG 图像", "*.jpg;*.jpeg"),
                ("所有文件", "*.*"),
            ],
        )
        if not path:
            return
        try:
            im = Image.open(path)
            self._process_static_image(im, source_tag="图片识别")
        except Exception as e:
            messagebox.showerror(APP_NAME, f"无法打开图片: {e}")

    def _decode_from_clipboard(self):
        """从剪贴板读取图像并解码"""
        im = read_image_from_clipboard()
        if im is None:
            messagebox.showinfo(APP_NAME, "当前系统剪贴板中没有图像数据。\n请先使用截屏工具截图或复制一张图片后再试。")
            return
        self._process_static_image(im, source_tag="剪贴板")

    def _process_static_image(self, im: Image.Image, source_tag: str):
        """统一处理静态图片解码"""
        # 显示图片预览
        preview_im = im.copy()
        preview_im.thumbnail((460, 380))
        photo = ctk.CTkImage(light_image=preview_im, dark_image=preview_im, size=preview_im.size)
        self.img_preview_label.configure(image=photo, text="")
        self.img_preview_label.image = photo

        # 执行多引擎解码
        res = engine.decode(im)
        if res and res.text:
            self.img_result_text.delete("1.0", "end")
            self.img_result_text.insert("1.0", res.text)
            self.img_engine_badge.configure(text=f"引擎: {res.engine}")
            history_manager.add_record(source_tag, res.text, res.engine)
            self._refresh_history_list()
            play_success_sound()
            copy_text_to_clipboard(res.text)
            messagebox.showinfo(APP_NAME, f"识别成功！内容已自动复制到剪贴板。\n\n引擎: {res.engine}\n内容: {res.text[:80]}...")
        else:
            self.img_result_text.delete("1.0", "end")
            self.img_engine_badge.configure(text="未检测到二维码")
            messagebox.showwarning(APP_NAME, "在选定图像中未检测到有效二维码。")

    # =========================================================================
    # Tab 3: 摄像头扫码 (Webcam Live)
    # =========================================================================
    def _init_camera_tab(self):
        tab = self.tab_camera

        layout = ctk.CTkFrame(tab, fg_color="transparent")
        layout.pack(fill="both", expand=True, padx=8, pady=8)

        # 顶部操作行
        top_row = ctk.CTkFrame(layout, fg_color=("gray95", "#1E1E2E"), height=54)
        top_row.pack(fill="x", padx=4, pady=(0, 8))

        ctk.CTkLabel(top_row, text="选择摄像头:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(14, 6))

        cameras = get_available_cameras()
        cam_options = [f"摄像头设备 #{i}" for i in cameras] if cameras else ["未检测到物理摄像头"]
        self.cam_combo = ctk.CTkComboBox(top_row, values=cam_options, width=180)
        self.cam_combo.set(cam_options[0])
        self.cam_combo.pack(side="left", padx=(0, 10))

        self.btn_cam_toggle = ctk.CTkButton(
            top_row,
            text="▶ 开启摄像头",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=13, weight="bold"),
            fg_color=("#059669", "#047857"),
            hover_color=("#10B981", "#059669"),
            command=self._toggle_camera,
        )
        self.btn_cam_toggle.pack(side="left", padx=(0, 10))

        # 主视频与结果分栏
        split_box = ctk.CTkFrame(layout, fg_color="transparent")
        split_box.pack(fill="both", expand=True, padx=4)

        # 视频展示画布
        video_frame = ctk.CTkFrame(split_box, fg_color=("gray90", "#181825"))
        video_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.cam_video_label = ctk.CTkLabel(
            video_frame,
            text="摄像头已关闭\n请点击上方【开启摄像头】开始实时扫描",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        )
        self.cam_video_label.pack(fill="both", expand=True, padx=12, pady=12)

        # 右侧结果
        cam_res_card = ctk.CTkFrame(split_box, width=320, fg_color=("gray95", "#1E1E2E"))
        cam_res_card.pack(side="right", fill="both", padx=(6, 0))
        cam_res_card.pack_propagate(False)

        ctk.CTkLabel(
            cam_res_card,
            text="摄像头扫描结果",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=14, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(12, 6))

        self.cam_result_text = ctk.CTkTextbox(
            cam_res_card,
            font=ctk.CTkFont(family="Consolas, Microsoft YaHei UI", size=13),
            wrap="word",
        )
        self.cam_result_text.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        cam_btn_bar = ctk.CTkFrame(cam_res_card, fg_color="transparent")
        cam_btn_bar.pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkButton(
            cam_btn_bar,
            text="📋 复制",
            width=90,
            command=lambda: self._copy_text(self.cam_result_text.get("1.0", "end-1c")),
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            cam_btn_bar,
            text="🌐 打开",
            width=90,
            fg_color=("#059669", "#047857"),
            command=lambda: self._open_text_url(self.cam_result_text.get("1.0", "end-1c")),
        ).pack(side="left", padx=(0, 6))

    def _toggle_camera(self):
        """开启或关闭摄像头视频流"""
        if self.camera_thread and self.camera_thread.running:
            self.camera_thread.stop()
            self.camera_thread = None
            self.btn_cam_toggle.configure(
                text="▶ 开启摄像头",
                fg_color=("#059669", "#047857"),
                hover_color=("#10B981", "#059669"),
            )
            self.cam_video_label.configure(image="", text="摄像头已关闭")
        else:
            sel_str = self.cam_combo.get()
            cam_idx = 0
            if "#" in sel_str:
                try:
                    cam_idx = int(sel_str.split("#")[-1])
                except Exception:
                    cam_idx = 0

            self.camera_thread = CameraScannerThread(
                camera_index=cam_idx,
                on_frame=self._on_camera_frame,
                on_error=lambda err: self.after(0, lambda: messagebox.showerror(APP_NAME, err)),
            )
            self.camera_thread.start()
            self.btn_cam_toggle.configure(
                text="⏹ 停止摄像头",
                fg_color=("#DC2626", "#B91C1C"),
                hover_color=("#EF4444", "#DC2626"),
            )

    def _on_camera_frame(self, pil_img: Image.Image, qr_res: Optional[QRDecodeResult]):
        """摄像头子线程回调：在 UI 线程调度刷新"""
        self.after(0, self._render_camera_frame, pil_img, qr_res)

    def _render_camera_frame(self, pil_img: Image.Image, qr_res: Optional[QRDecodeResult]):
        preview = pil_img.copy()
        preview.thumbnail((500, 380))
        photo = ctk.CTkImage(light_image=preview, dark_image=preview, size=preview.size)
        self.cam_video_label.configure(image=photo, text="")
        self.cam_video_label.image = photo

        if qr_res and qr_res.text:
            text = qr_res.text
            if text != self.last_decoded_text:
                self.last_decoded_text = text
                self.cam_result_text.delete("1.0", "end")
                self.cam_result_text.insert("1.0", text)
                history_manager.add_record("摄像头", text, qr_res.engine)
                self._refresh_history_list()
                play_success_sound()
                copy_text_to_clipboard(text)

    # =========================================================================
    # Tab 4: 二维码生成 (QR Generator)
    # =========================================================================
    def _init_generator_tab(self):
        tab = self.tab_gen

        layout = ctk.CTkFrame(tab, fg_color="transparent")
        layout.pack(fill="both", expand=True, padx=8, pady=8)

        # 左侧输入与样式控制
        left_ctrl = ctk.CTkFrame(layout, width=380, fg_color=("gray95", "#1E1E2E"))
        left_ctrl.pack(side="left", fill="y", padx=(0, 8))
        left_ctrl.pack_propagate(False)

        ctk.CTkLabel(
            left_ctrl,
            text="生成参数配置",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=15, weight="bold"),
        ).pack(anchor="w", padx=14, pady=(14, 8))

        ctk.CTkLabel(left_ctrl, text="输入文本或网址内容:", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=14, pady=(2, 2))
        self.gen_text_input = ctk.CTkTextbox(
            left_ctrl,
            height=110,
            font=ctk.CTkFont(family="Consolas, Microsoft YaHei UI", size=13),
            wrap="word",
        )
        self.gen_text_input.insert("1.0", "https://antigravity.google.com")
        self.gen_text_input.pack(fill="x", padx=14, pady=(0, 10))

        # ECC 容错级别
        ctk.CTkLabel(left_ctrl, text="容错等级 (ECC):", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=14, pady=(2, 2))
        self.gen_ecc_combo = ctk.CTkComboBox(left_ctrl, values=list(ECC_LEVELS.keys()), width=350)
        self.gen_ecc_combo.set(list(ECC_LEVELS.keys())[1])  # 默认 M
        self.gen_ecc_combo.pack(padx=14, pady=(0, 10))

        # 配色方案预设
        ctk.CTkLabel(left_ctrl, text="配色方案预设:", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=14, pady=(2, 2))
        preset_names = [p[2] for p in QR_COLOR_PRESETS]
        self.gen_color_combo = ctk.CTkComboBox(left_ctrl, values=preset_names, width=350, command=self._on_color_preset_select)
        self.gen_color_combo.set(preset_names[0])
        self.gen_color_combo.pack(padx=14, pady=(0, 10))

        # 自定义颜色色值
        color_row = ctk.CTkFrame(left_ctrl, fg_color="transparent")
        color_row.pack(fill="x", padx=14, pady=(0, 12))

        ctk.CTkLabel(color_row, text="前景色:", font=ctk.CTkFont(size=12)).pack(side="left")
        self.gen_fg_entry = ctk.CTkEntry(color_row, width=80)
        self.gen_fg_entry.insert(0, "#000000")
        self.gen_fg_entry.pack(side="left", padx=(6, 14))

        ctk.CTkLabel(color_row, text="背景色:", font=ctk.CTkFont(size=12)).pack(side="left")
        self.gen_bg_entry = ctk.CTkEntry(color_row, width=80)
        self.gen_bg_entry.insert(0, "#FFFFFF")
        self.gen_bg_entry.pack(side="left", padx=(6, 0))

        # 尺寸与边框滑块
        self.gen_size_label = ctk.CTkLabel(left_ctrl, text="模块大小: 10 px", font=ctk.CTkFont(size=12))
        self.gen_size_label.pack(anchor="w", padx=14)
        self.gen_size_slider = ctk.CTkSlider(
            left_ctrl, from_=4, to=20, number_of_steps=16,
            command=lambda v: self.gen_size_label.configure(text=f"模块大小: {int(v)} px"),
        )
        self.gen_size_slider.set(10)
        self.gen_size_slider.pack(fill="x", padx=14, pady=(0, 12))

        # 生成按钮
        self.btn_generate = ctk.CTkButton(
            left_ctrl,
            text="⚡ 立即生成二维码",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=14, weight="bold"),
            height=40,
            command=self._generate_qr_code,
        )
        self.btn_generate.pack(fill="x", padx=14, pady=(4, 10))

        # 右侧预览与导出卡片
        right_preview = ctk.CTkFrame(layout, fg_color=("gray90", "#181825"))
        right_preview.pack(side="right", fill="both", expand=True)

        self.gen_preview_label = ctk.CTkLabel(right_preview, text="", text_color="gray")
        self.gen_preview_label.pack(fill="both", expand=True, padx=20, pady=(20, 10))

        # 导出工具条
        export_bar = ctk.CTkFrame(right_preview, fg_color=("gray95", "#1E1E2E"), height=54)
        export_bar.pack(fill="x", padx=12, pady=(0, 12))

        self.btn_copy_qr_img = ctk.CTkButton(
            export_bar,
            text="📋 复制二维码图片到剪贴板",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=13, weight="bold"),
            command=self._copy_generated_image,
        )
        self.btn_copy_qr_img.pack(side="left", padx=12, pady=10)

        self.btn_save_qr_img = ctk.CTkButton(
            export_bar,
            text="💾 保存为图片文件 (PNG/JPG)",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=13, weight="bold"),
            fg_color=("#059669", "#047857"),
            hover_color=("#10B981", "#059669"),
            command=self._save_generated_image,
        )
        self.btn_save_qr_img.pack(side="left", padx=(0, 12), pady=10)

        # 初始自动渲染一次默认二维码 (不写入历史)
        self._generate_qr_code(save_history=False)

    def _on_color_preset_select(self, preset_name: str):
        for fg, bg, name in QR_COLOR_PRESETS:
            if name == preset_name:
                self.gen_fg_entry.delete(0, "end")
                self.gen_fg_entry.insert(0, fg)
                self.gen_bg_entry.delete(0, "end")
                self.gen_bg_entry.insert(0, bg)
                break
        self._generate_qr_code(save_history=False)

    def _generate_qr_code(self, save_history: bool = True):
        """生成并展示二维码"""
        text = self.gen_text_input.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showwarning(APP_NAME, "请输入要编码的文本或网址内容！")
            return

        ecc_choice = self.gen_ecc_combo.get()
        ecc_level = ECC_LEVELS.get(ecc_choice, "M")
        box_size = int(self.gen_size_slider.get())
        fg_col = self.gen_fg_entry.get().strip() or "#000000"
        bg_col = self.gen_bg_entry.get().strip() or "#FFFFFF"

        img = engine.generate(
            text=text,
            ecc_level=ecc_level,
            box_size=box_size,
            border=2,
            fill_color=fg_col,
            back_color=bg_col,
        )

        if img:
            self.current_generated_img = img
            # 缩放至预览区域大小
            preview_im = img.copy()
            preview_im.thumbnail((360, 360))
            photo = ctk.CTkImage(light_image=preview_im, dark_image=preview_im, size=preview_im.size)
            self.gen_preview_label.configure(image=photo, text="")
            self.gen_preview_label.image = photo

            # 存入历史记录
            if save_history:
                history_manager.add_record("二维码生成", text, "QRCode Engine")
                self._refresh_history_list()
        else:
            messagebox.showerror(APP_NAME, "二维码生成失败，请检查输入内容及颜色格式！")

    def _copy_generated_image(self):
        """将生成的二维码图片直接写入系统原生剪贴板"""
        if not self.current_generated_img:
            messagebox.showwarning(APP_NAME, "尚未生成二维码图片！")
            return
        if copy_image_to_clipboard(self.current_generated_img):
            messagebox.showinfo(APP_NAME, "二维码图像已成功复制到系统剪贴板！\n您可直接在微信、文档或画图中 Ctrl+V 粘贴。")
        else:
            messagebox.showerror(APP_NAME, "写入系统剪贴板失败。")

    def _save_generated_image(self):
        """保存生成的二维码为文件"""
        if not self.current_generated_img:
            messagebox.showwarning(APP_NAME, "尚未生成二维码图片！")
            return

        path = filedialog.asksaveasfilename(
            title="保存二维码图片",
            defaultextension=".png",
            filetypes=[
                ("PNG 高清无损图像", "*.png"),
                ("JPEG 图像", "*.jpg"),
                ("所有文件", "*.*"),
            ],
            initialfile=f"qrcode_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
        )
        if path:
            try:
                self.current_generated_img.save(path)
                messagebox.showinfo(APP_NAME, f"二维码已成功保存至：\n{path}")
            except Exception as e:
                messagebox.showerror(APP_NAME, f"保存失败: {e}")

    # =========================================================================
    # Tab 5: 历史记录 (History)
    # =========================================================================
    def _init_history_tab(self):
        tab = self.tab_history

        layout = ctk.CTkFrame(tab, fg_color="transparent")
        layout.pack(fill="both", expand=True, padx=8, pady=8)

        # 顶部过滤与导出条
        filter_bar = ctk.CTkFrame(layout, fg_color=("gray95", "#1E1E2E"), height=50)
        filter_bar.pack(fill="x", padx=4, pady=(0, 8))

        ctk.CTkLabel(filter_bar, text="分类筛选:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(14, 6))
        self.history_filter_combo = ctk.CTkComboBox(
            filter_bar,
            values=["全部", "屏幕扫描", "图片识别", "剪贴板", "摄像头", "二维码生成"],
            width=130,
            command=lambda v: self._refresh_history_list(),
        )
        self.history_filter_combo.set("全部")
        self.history_filter_combo.pack(side="left", padx=(0, 14))

        ctk.CTkButton(
            filter_bar,
            text="📤 导出为 CSV 表格",
            width=120,
            command=self._export_history_csv,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            filter_bar,
            text="📤 导出为 TXT 文本",
            width=120,
            command=self._export_history_txt,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            filter_bar,
            text="🗑️ 清空所有记录",
            width=110,
            fg_color=("#DC2626", "#B91C1C"),
            hover_color=("#EF4444", "#DC2626"),
            command=self._clear_all_history,
        ).pack(side="right", padx=14)

        # 可滚动的历史卡片列表
        self.history_scroll = ctk.CTkScrollableFrame(layout, fg_color=("gray90", "#181825"))
        self.history_scroll.pack(fill="both", expand=True, padx=4)

        self._refresh_history_list()

    def _refresh_history_list(self):
        """重新绘制历史记录列表"""
        if not hasattr(self, "history_scroll") or self.history_scroll is None:
            return

        # 清除现有卡片
        for widget in self.history_scroll.winfo_children():
            widget.destroy()

        filt = self.history_filter_combo.get() if hasattr(self, "history_filter_combo") else "全部"
        records = history_manager.get_records(filt)

        if not records:
            empty_lbl = ctk.CTkLabel(
                self.history_scroll,
                text="暂无历史记录",
                font=ctk.CTkFont(size=14),
                text_color="gray",
            )
            empty_lbl.pack(pady=40)
            return

        for rec in records:
            card = ctk.CTkFrame(self.history_scroll, fg_color=("gray95", "#1E1E2E"), corner_radius=6)
            card.pack(fill="x", padx=6, pady=4)

            # 顶部信息行
            top_line = ctk.CTkFrame(card, fg_color="transparent")
            top_line.pack(fill="x", padx=10, pady=(6, 2))

            source_color = {
                "屏幕扫描": "#3B82F6",
                "图片识别": "#8B5CF6",
                "剪贴板": "#EC4899",
                "摄像头": "#10B981",
                "二维码生成": "#F59E0B",
            }.get(rec.source, "#6B7280")

            badge = ctk.CTkLabel(
                top_line,
                text=f"[{rec.source}]",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=source_color,
            )
            badge.pack(side="left")

            time_lbl = ctk.CTkLabel(top_line, text=rec.timestamp, font=ctk.CTkFont(size=11), text_color="gray")
            time_lbl.pack(side="left", padx=8)

            if rec.engine:
                eng_lbl = ctk.CTkLabel(top_line, text=f"({rec.engine})", font=ctk.CTkFont(size=11), text_color="gray")
                eng_lbl.pack(side="left")

            # 右侧操作按钮
            del_btn = ctk.CTkButton(
                top_line,
                text="✕",
                width=24,
                height=22,
                fg_color="transparent",
                hover_color=("#FCA5A5", "#7F1D1D"),
                text_color="gray",
                command=lambda r_id=rec.record_id: self._delete_history_item(r_id),
            )
            del_btn.pack(side="right")

            copy_btn = ctk.CTkButton(
                top_line,
                text="复制",
                width=50,
                height=22,
                font=ctk.CTkFont(size=11),
                command=lambda c=rec.content: self._copy_text(c),
            )
            copy_btn.pack(side="right", padx=4)

            if rec.is_url:
                open_btn = ctk.CTkButton(
                    top_line,
                    text="打开",
                    width=50,
                    height=22,
                    font=ctk.CTkFont(size=11),
                    fg_color=("#059669", "#047857"),
                    command=lambda u=rec.content: self._open_text_url(u),
                )
                open_btn.pack(side="right", padx=4)

            # 内容文字展示
            content_lbl = ctk.CTkLabel(
                card,
                text=rec.content,
                font=ctk.CTkFont(family="Consolas, Microsoft YaHei UI", size=12),
                anchor="w",
                justify="left",
                wraplength=760,
            )
            content_lbl.pack(fill="x", padx=10, pady=(0, 8))

    def _delete_history_item(self, record_id: str):
        history_manager.delete_record(record_id)
        self._refresh_history_list()

    def _clear_all_history(self):
        if messagebox.askyesno(APP_NAME, "确定要清空所有历史记录吗？此操作不可恢复。"):
            history_manager.clear()
            self._refresh_history_list()

    def _export_history_csv(self):
        path = filedialog.asksaveasfilename(
            title="导出历史记录为 CSV",
            defaultextension=".csv",
            filetypes=[("CSV 表格", "*.csv")],
            initialfile=f"qr_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )
        if path:
            if history_manager.export_to_csv(path):
                messagebox.showinfo(APP_NAME, f"成功导出历史记录至：\n{path}")
            else:
                messagebox.showerror(APP_NAME, "导出失败。")

    def _export_history_txt(self):
        path = filedialog.asksaveasfilename(
            title="导出历史记录为 TXT",
            defaultextension=".txt",
            filetypes=[("纯文本文件", "*.txt")],
            initialfile=f"qr_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        if path:
            if history_manager.export_to_txt(path):
                messagebox.showinfo(APP_NAME, f"成功导出历史记录至：\n{path}")
            else:
                messagebox.showerror(APP_NAME, "导出失败。")

    # =========================================================================
    # Tab 6: 术语缩写与项目准则 (Glossary & Project Rules)
    # =========================================================================
    def _init_about_tab(self):
        tab = self.tab_about

        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=8, pady=8)

        # 顶端：项目准则说明卡片
        rules_card = ctk.CTkFrame(scroll, fg_color=("gray95", "#1E1E2E"), corner_radius=8)
        rules_card.pack(fill="x", padx=4, pady=(0, 10))

        ctk.CTkLabel(
            rules_card,
            text="📌 《项目准则.md》合规实现声明",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=15, weight="bold"),
            text_color=("#1D4ED8", "#60A5FA"),
        ).pack(anchor="w", padx=14, pady=(12, 6))

        rules_desc = (
            "1. 【唯一启动器】：不使用 bat/sh/ps1，统一使用根目录下唯一的 run.py 作为启动引导器。\n"
            "2. 【代码布局】：所有核心算法与功能组件全部封装在 src 文件夹内。\n"
            "3. 【旧文件清理】：彻底清除历史冗余文件（node_modules、dist、desktop 等旧脚本与配置）。\n"
            "4. 【缩写释义规范】：项目内所有技术缩写均提供详尽的中英文对照与技术原理释义（见下方词典）。\n"
            "5. 【目录安全边界】：所有改动严格限制在本工程第三层目录内，绝不越界。\n"
            "6. 【依赖自洽】：使用原生 Python 标准库与成熟图像扩展，零外部驱动依赖。"
        )
        ctk.CTkLabel(
            rules_card,
            text=rules_desc,
            font=ctk.CTkFont(size=12),
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=14, pady=(0, 12))

        # 术语缩写词典卡片
        ctk.CTkLabel(
            scroll,
            text="📚 项目专业术语与技术缩写释义词典 (Glossary)",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=15, weight="bold"),
        ).pack(anchor="w", padx=4, pady=(6, 8))

        abbr_list = get_abbreviations_list()
        for item in abbr_list:
            item_card = ctk.CTkFrame(scroll, fg_color=("gray95", "#1E1E2E"), corner_radius=6)
            item_card.pack(fill="x", padx=4, pady=4)

            header_row = ctk.CTkFrame(item_card, fg_color="transparent")
            header_row.pack(fill="x", padx=12, pady=(10, 4))

            ctk.CTkLabel(
                header_row,
                text=item["abbr"],
                font=ctk.CTkFont(family="Consolas, Microsoft YaHei UI", size=15, weight="bold"),
                text_color=("#2563EB", "#60A5FA"),
            ).pack(side="left")

            ctk.CTkLabel(
                header_row,
                text=f"—  {item['full_zh']} ({item['full_en']})",
                font=ctk.CTkFont(size=13, weight="bold"),
            ).pack(side="left", padx=8)

            category_badge = ctk.CTkLabel(
                header_row,
                text=f"[{item['category']}]",
                font=ctk.CTkFont(size=11),
                text_color="gray",
            )
            category_badge.pack(side="right")

            ctk.CTkLabel(
                item_card,
                text=item["description"],
                font=ctk.CTkFont(size=12),
                justify="left",
                anchor="w",
                wraplength=820,
            ).pack(fill="x", padx=12, pady=(0, 10))

    # =========================================================================
    # 通用动作辅助函数
    # =========================================================================
    def _copy_text(self, text: str):
        if not text or not text.strip():
            return
        if copy_text_to_clipboard(text.strip()):
            messagebox.showinfo(APP_NAME, "文本已成功复制到系统剪贴板！")

    def _open_text_url(self, text: str):
        if not text or not text.strip():
            return
        url = text.strip()
        if is_url(url):
            open_url_in_browser(url)
        else:
            if messagebox.askyesno(APP_NAME, "当前内容看起来不是标准的 URL 链接，是否仍要在浏览器中搜索/打开？"):
                open_url_in_browser(f"https://www.google.com/search?q={url}")

    def _toggle_theme(self):
        new_mode = self.theme_switch.get()
        ctk.set_appearance_mode(new_mode)

    def _on_close(self):
        """窗口关闭清理资源"""
        if self.camera_thread and self.camera_thread.running:
            self.camera_thread.stop()
        if self.screen_after_id:
            self.after_cancel(self.screen_after_id)
        self.destroy()


def main():
    """GUI 桌面程序主入口"""
    app = QRMasterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
