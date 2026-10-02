# -*- coding: utf-8 -*-
"""多引擎二维码解码与生成核心 (QR Engine: Multi-Tier Decoder & Encoder)

技术特性与缩写说明：
- QR: Quick Response code，快速响应矩阵条码。
- ECC: Error Correction Code，容错级别（L/M/Q/H 四级）。
- 多层级容错解码架构：
  1. OpenCV Aruco 增强型解码器（速度极快，抗形变倾斜能力强）
  2. OpenCV 经典解码器（兼容性强）
  3. 纯 Python Reed-Solomon 解码器（纯原生无二进制扩展兜底）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image
import qrcode
from qrcode.constants import (
    ERROR_CORRECT_L,
    ERROR_CORRECT_M,
    ERROR_CORRECT_Q,
    ERROR_CORRECT_H,
)

from .utils import is_url

# 纯 Python 解码器
try:
    from . import pure_decoder
    _HAS_PURE_DECODER = True
except Exception:
    _HAS_PURE_DECODER = False


@dataclass
class QRDecodeResult:
    """二维码解码结果结构体"""
    text: str                                           # 解码出的文本或链接内容
    points: Optional[List[Tuple[float, float]]] = None  # 四边形顶点坐标 [(x1,y1), (x2,y2), ...]
    engine: str = "opencv"                             # 解码所用引擎标识
    is_url: bool = False                               # 是否为可访问的网络链接


class QREngine:
    """统一二维码解码与编码服务单例类"""

    def __init__(self):
        # 初始化 OpenCV 识别器
        self._detector_aruco = None
        self._detector_std = None

        try:
            self._detector_aruco = cv2.QRCodeDetectorAruco()
        except Exception:
            pass

        try:
            self._detector_std = cv2.QRCodeDetector()
        except Exception:
            pass

    @staticmethod
    def to_bgr_array(image_input: Union[Image.Image, np.ndarray, str]) -> Optional[np.ndarray]:
        """将任意输入格式 (PIL Image / 文件路径 / ndarray) 标准化为 OpenCV BGR 图像矩阵"""
        if isinstance(image_input, str):
            try:
                # 兼容中文路径的读取
                img_array = np.fromfile(image_input, dtype=np.uint8)
                return cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            except Exception:
                return None

        if isinstance(image_input, Image.Image):
            rgb_im = image_input.convert("RGB")
            rgb_array = np.array(rgb_im)
            return cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)

        if isinstance(image_input, np.ndarray):
            if len(image_input.shape) == 2:
                return cv2.cvtColor(image_input, cv2.COLOR_GRAY2BGR)
            if image_input.shape[2] == 4:
                return cv2.cvtColor(image_input, cv2.COLOR_RGBA2BGR)
            if image_input.shape[2] == 3:
                return image_input

        return None

    def decode(self, image_input: Union[Image.Image, np.ndarray, str]) -> Optional[QRDecodeResult]:
        """多层级综合识别二维码

        依次尝试：
        1. OpenCV Aruco 增强检测器
        2. OpenCV 经典检测器
        3. 灰度增强与自适应二值化后再次检测
        4. 纯 Python Reed-Solomon 兜底解码器
        """
        bgr = self.to_bgr_array(image_input)
        if bgr is None or bgr.size == 0:
            return None

        # Tier 1: OpenCV Aruco 检测器
        if self._detector_aruco is not None:
            try:
                res = self._detector_aruco.detectAndDecode(bgr)
                # OpenCV 5.0+ 返回 3 项: (decoded_info, points, straight_qrcode)
                # 某些版本可能返回 2 项: (decoded_info, points)
                text = res[0]
                points = res[1] if len(res) > 1 else None
                if text and len(text.strip()) > 0:
                    pts_list = self._format_points(points)
                    return QRDecodeResult(
                        text=text.strip(),
                        points=pts_list,
                        engine="OpenCV Aruco",
                        is_url=is_url(text.strip()),
                    )
            except Exception:
                pass

        # Tier 2: OpenCV 经典检测器
        if self._detector_std is not None:
            try:
                res = self._detector_std.detectAndDecode(bgr)
                text = res[0]
                points = res[1] if len(res) > 1 else None
                if text and len(text.strip()) > 0:
                    pts_list = self._format_points(points)
                    return QRDecodeResult(
                        text=text.strip(),
                        points=pts_list,
                        engine="OpenCV Standard",
                        is_url=is_url(text.strip()),
                    )
            except Exception:
                pass

        # Tier 2.5: 灰度增强预处理后重试 (应对微弱光照、模糊或低对比度)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)

        if self._detector_aruco is not None:
            try:
                res = self._detector_aruco.detectAndDecode(enhanced_bgr)
                text = res[0]
                points = res[1] if len(res) > 1 else None
                if text and len(text.strip()) > 0:
                    return QRDecodeResult(
                        text=text.strip(),
                        points=self._format_points(points),
                        engine="OpenCV CLAHE Enhanced",
                        is_url=is_url(text.strip()),
                    )
            except Exception:
                pass

        # Tier 3: 纯 Python Reed-Solomon 解码器 (兜底)
        if _HAS_PURE_DECODER:
            try:
                # 转换灰度列表为 bytes 序列
                h, w = gray.shape
                gray_rows = [bytes(gray[row_idx, :]) for row_idx in range(h)]
                pure_text = pure_decoder.decode_gray(gray_rows)
                if pure_text and len(pure_text.strip()) > 0:
                    return QRDecodeResult(
                        text=pure_text.strip(),
                        points=None,
                        engine="Pure-Python Reed-Solomon",
                        is_url=is_url(pure_text.strip()),
                    )
            except Exception:
                pass

        return None

    @staticmethod
    def _format_points(points) -> Optional[List[Tuple[float, float]]]:
        """格式化 OpenCV 检测返回的四边形角点坐标"""
        if points is None:
            return None
        try:
            arr = np.array(points).reshape(-1, 2)
            return [(float(pt[0]), float(pt[1])) for pt in arr]
        except Exception:
            return None

    @staticmethod
    def generate(
        text: str,
        ecc_level: str = "M",
        box_size: int = 10,
        border: int = 2,
        fill_color: str = "#000000",
        back_color: str = "#FFFFFF",
    ) -> Optional[Image.Image]:
        """生成指定样式的二维码 PIL 图像

        参数：
            text: 载荷内容 (文本或网址)
            ecc_level: 容错等级 (L: 7%, M: 15%, Q: 25%, H: 30%)
            box_size: 每个二维码模块的像素尺寸
            border: 外边距格数
            fill_color: 前景颜色 (Hex 格式如 #000000)
            back_color: 背景颜色 (Hex 格式如 #FFFFFF)
        """
        if not text:
            return None

        ecc_map = {
            "L": ERROR_CORRECT_L,
            "M": ERROR_CORRECT_M,
            "Q": ERROR_CORRECT_Q,
            "H": ERROR_CORRECT_H,
        }
        level = ecc_map.get(ecc_level.upper(), ERROR_CORRECT_M)

        try:
            qr = qrcode.QRCode(
                version=None,
                error_correction=level,
                box_size=max(2, box_size),
                border=max(1, border),
            )
            qr.add_data(text)
            qr.make(fit=True)
            img = qr.make_image(fill_color=fill_color, back_color=back_color)
            return img.convert("RGB")
        except Exception:
            return None


# 全局单例
engine = QREngine()
