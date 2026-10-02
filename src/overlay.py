# -*- coding: utf-8 -*-
"""交互式屏幕选区遮罩浮层 (Screen Selection Overlay)

技术特性与缩写说明：
- ROI: Region of Interest（感兴趣区域），允许用户拖拽鼠标框选任意矩形屏幕范围。
- GDI: 利用 GDI 屏幕抓取生成背景冻结视图，配合动态暗化蒙版与高亮选框，提供媲美专业截图工具的交互体验。
- DPI: 保持全屏幕像素级对齐，多显示器坐标自动补偿。
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional, Tuple

from PIL import Image, ImageTk

from .screen_capture import capture_region, get_virtual_screen_bounds


class ScreenSelectorOverlay:
    """全屏框选屏幕区域的交互遮罩层"""

    def __init__(
        self,
        parent: tk.Tk,
        on_selected: Callable[[int, int, int, int], None],
        on_cancel: Optional[Callable[[], None]] = None,
    ):
        self.parent = parent
        self.on_selected = on_selected
        self.on_cancel = on_cancel

        self.start_x = 0
        self.start_y = 0
        self.cur_x = 0
        self.cur_y = 0
        self.is_dragging = False

        # 获取虚拟屏幕总范围
        self.vx, self.vy, self.vw, self.vh = get_virtual_screen_bounds()

        # 捕获当前屏幕作为背景快照
        self.bg_image = capture_region(self.vx, self.vy, self.vw, self.vh)

        # 构建全屏顶层无边框窗口
        self.top = tk.Toplevel(parent)
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)
        self.top.geometry(f"{self.vw}x{self.vh}+{self.vx}+{self.vy}")

        # 鼠标样式
        self.top.config(cursor="cross")

        self.canvas = tk.Canvas(
            self.top,
            width=self.vw,
            height=self.vh,
            highlightthickness=0,
            bg="black",
        )
        self.canvas.pack(fill="both", expand=True)

        # 绘制背景快照与半透明暗色遮罩
        self._bg_photo = None
        if self.bg_image:
            # 制作半透明暗化效果 (暗化 50%)
            darkened = Image.blend(self.bg_image, Image.new("RGB", self.bg_image.size, "black"), 0.55)
            self._bg_photo = ImageTk.PhotoImage(darkened)
            self.canvas.create_image(0, 0, anchor="nw", image=self._bg_photo)

        # 提示横幅
        self.tip_rect = self.canvas.create_rectangle(
            self.vw // 2 - 240, 20, self.vw // 2 + 240, 64,
            fill="#1E1E2E", outline="#3B82F6", width=2
        )
        self.tip_text = self.canvas.create_text(
            self.vw // 2, 42,
            text="拖动鼠标左键框选二维码所在区域  |  按 ESC 或 右键取消",
            fill="#F3F4F6", font=("Microsoft YaHei UI", 11, "bold")
        )

        # 选框图形元素句柄
        self.rect_border = None
        self.rect_inner = None
        self.dim_text = None
        self.dim_bg = None

        # 事件绑定
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.top.bind("<Escape>", lambda e: self._cancel())
        self.canvas.bind("<Button-3>", lambda e: self._cancel())

        # 获得焦点
        self.top.focus_force()

    def _on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.cur_x = event.x
        self.cur_y = event.y
        self.is_dragging = True

    def _on_drag(self, event):
        if not self.is_dragging:
            return
        self.cur_x = event.x
        self.cur_y = event.y
        self._redraw_selection()

    def _redraw_selection(self):
        x1 = min(self.start_x, self.cur_x)
        y1 = min(self.start_y, self.cur_y)
        x2 = max(self.start_x, self.cur_x)
        y2 = max(self.start_y, self.cur_y)
        w = x2 - x1
        h = y2 - y1

        # 清理旧选框
        if self.rect_border:
            self.canvas.delete(self.rect_border)
        if self.dim_bg:
            self.canvas.delete(self.dim_bg)
        if self.dim_text:
            self.canvas.delete(self.dim_text)

        # 绘制主选框边框
        self.rect_border = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline="#3B82F6",
            width=2,
            dash=(6, 4) if w < 30 or h < 30 else ()
        )

        # 尺寸信息标签
        dim_str = f"选区: {w} × {h} px"
        label_y = y2 + 18 if y2 + 25 < self.vh else y1 - 18
        label_x = x1 + 45
        self.dim_bg = self.canvas.create_rectangle(
            label_x - 45, label_y - 12, label_x + 55, label_y + 12,
            fill="#1E1E2E", outline="#60A5FA", width=1
        )
        self.dim_text = self.canvas.create_text(
            label_x + 5, label_y,
            text=dim_str,
            fill="#93C5FD", font=("Segoe UI", 9, "bold")
        )

    def _on_release(self, event):
        if not self.is_dragging:
            return
        self.is_dragging = False

        x1 = min(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        x2 = max(self.start_x, event.x)
        y2 = max(self.start_y, event.y)
        w = x2 - x1
        h = y2 - y1

        self._close()

        # 最小区域过滤（防手抖轻点）
        if w >= 20 and h >= 20:
            # 换算到系统全局坐标系
            global_x = self.vx + x1
            global_y = self.vy + y1
            self.on_selected(global_x, global_y, w, h)
        else:
            if self.on_cancel:
                self.on_cancel()

    def _cancel(self):
        self._close()
        if self.on_cancel:
            self.on_cancel()

    def _close(self):
        try:
            self.top.destroy()
        except Exception:
            pass
        self.parent.focus_force()
