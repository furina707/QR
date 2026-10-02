# -*- coding: utf-8 -*-
"""摄像头实时二维码扫描模块 (Webcam QR Scanner)

采用独立后台工作线程 (Worker Thread) 进行摄像头画面采集与解码计算，
避免耗时计算阻塞 GUI 主事件循环，保障界面丝滑流畅。
"""

from __future__ import annotations

import os
import sys
import threading
import time
from typing import Callable, List, Optional

import cv2
import numpy as np
from PIL import Image

from .qr_engine import engine, QRDecodeResult

# 静音 OpenCV 内部的调试输出与错误告警
try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
except Exception:
    pass


def get_available_cameras(max_test: int = 2) -> List[int]:
    """探测系统中可用的物理摄像头设备索引"""
    available = []
    for idx in range(max_test):
        try:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                available.append(idx)
                cap.release()
        except Exception:
            pass
    return available


class CameraScannerThread(threading.Thread):
    """摄像头后台采集与扫描线程"""

    def __init__(
        self,
        camera_index: int = 0,
        on_frame: Optional[Callable[[Image.Image, Optional[QRDecodeResult]], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(daemon=True)
        self.camera_index = camera_index
        self.on_frame = on_frame
        self.on_error = on_error
        self.running = False
        self.pause_scanning = False

    def run(self):
        try:
            cap = cv2.VideoCapture(self.camera_index)
            if not cap.isOpened():
                if self.on_error:
                    self.on_error(f"无法打开索引为 {self.camera_index} 的摄像头设备，请检查是否被占用或驱动异常。")
                return

            self.running = True
            frame_counter = 0

            while self.running:
                ret, frame = cap.read()
                if not ret or frame is None:
                    time.sleep(0.05)
                    continue

                frame_counter += 1
                result: Optional[QRDecodeResult] = None

                # 每 2 帧执行一次 QR 解码，降低 CPU 负载并提升画面的流畅度
                if not self.pause_scanning and frame_counter % 2 == 0:
                    result = engine.decode(frame)

                # 在画面上标出二维码位置 (若检测到角点)
                if result and result.points:
                    pts = np.array(result.points, dtype=np.int32).reshape((-1, 1, 2))
                    cv2.polylines(frame, [pts], isClosed=True, color=(0, 255, 0), thickness=3)

                # 将 BGR 转换为 PIL Image 供 UI 渲染
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_frame)

                if self.on_frame:
                    self.on_frame(pil_img, result)

                time.sleep(0.03)  # 控制采集帧率约为 30 FPS

            cap.release()
        except Exception as e:
            if self.on_error:
                self.on_error(f"摄像头运行出错: {e}")

    def stop(self):
        self.running = False
