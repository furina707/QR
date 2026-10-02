# QR 智能工作台 (QR Master)

> **全架构 Python 原生重构版** | 屏幕/图片/剪贴板/摄像头二维码全能识别与生成桌面工具箱

---

## 📌 项目准则合规说明

本项目严格遵循 [`项目准则.md`](file:///c:/Users/cytsh/Desktop/.project/QR/项目准则.md) 的各项规范要求：

1. **唯一启动器**：不使用 `.bat`、`.sh`、`.ps1` 脚本，全工程统一以根目录下的 [`run.py`](file:///c:/Users/cytsh/Desktop/.project/QR/run.py) 作为唯一启动入口。
2. **核心代码组织**：所有核心业务逻辑、解码算法、GUI 界面与底层工具均置于 [`src/`](file:///c:/Users/cytsh/Desktop/.project/QR/src/) 目录内。
3. **旧文件清理**：已彻底移除原 Node.js / Web 相关的冗余文件（`node_modules`、`dist`、`package.json`、旧前端脚本及废弃旧目录）。
4. **技术缩写规范释义**：在本文档、代码注释及软件界面中，均系统性提供了所有缩写的完整中英文名称与技术定义（详见下方 [术语缩写完整释义表](#-术语缩写具体含义介绍-glossary)）。
5. **工作空间目录边界**：
   - 第一层：`.project`（项目工作区）
   - 第二层：项目类别
   - 第三层：本项目自身（`c:\Users\cytsh\Desktop\.project\QR`）
   - 所有改动严格封存于第三层项目本身以内，绝不越界。
6. **依赖自洽与极简**：采用原生 Python 结合主流视觉与图像库，无复杂驱动或繁琐安装。

---

## 📚 术语缩写具体含义介绍 (Glossary)

根据准则第 4 条要求，以下为本项目中涉及的技术缩写的完整中英文定义及其在本项目中的具体技术应用：

| 缩写 | 英文全称 (Full English) | 中文标准名称 | 领域分类 | 具体含义与本项目中的应用 |
| :--- | :--- | :--- | :--- | :--- |
| **QR** | `Quick Response code` | 快速响应矩阵条码（二维码） | 编码与图形识别 | 1994年由日本 Denso Wave 公司发明的一种二维矩阵式条形码。具有超高识读速度（Quick Response）、全方位 360° 可读性、大容量数据存储（可编码数千字符）和强大的 Reed-Solomon 纠错能力。在本工程中代表核心业务：屏幕/图片/摄像头中的二维码识别与生成。 |
| **GUI** | `Graphical User Interface` | 图形用户界面 | 人机交互 | 采用图形方式显示的计算机操作用户界面。相较于纯文本命令行界面（CLI），GUI 提供直观的窗口、标签页、按钮、滑块、画布及实时预览。本项目基于 CustomTkinter / Tkinter 构建现代化原生 GUI 桌面客户端。 |
| **UI** | `User Interface` | 用户界面 | 前端与视觉设计 | 用户与系统之间进行交互与信息传递的媒介与视觉表现层，包含色彩搭配、组件排版、间距、字体及动画效果。 |
| **CLI** | `Command Line Interface` | 命令行接口 | 人机交互 | 通过终端文本命令与程序进行交互的方式。本工程以 `run.py` 统一引导，支持参数分流执行解码与生成，也可直接拉起 GUI 桌面窗口。 |
| **DPI** | `Dots Per Inch` | 每英寸点数（屏幕缩放/分辨率密度） | 显示与系统底层 | 衡量屏幕物理显示精细度与系统缩放比例（如 125%、150%、200%）的核心参数。在 Windows 系统上，如果不开启 DPI-Awareness（DPI 感知），截屏和框选窗口会因系统虚拟缩放而产生坐标偏移与模糊。本项目在启动时立即启用高 DPI 感知以保证像素级精准截图。 |
| **GDI** | `Graphics Device Interface` | Windows 图形设备接口 | 操作系统底层 API | 微软 Windows 操作系统的核心图形子系统，用于与显卡通信并管理设备上下文（HDC）。本项目利用 GDI 中的 `BitBlt`（位块传输）与 `GetDIBits` 原生底层 API，实现无外部第三方驱动依赖、跨多显示器、毫秒级的纯原生超快屏幕捕获。 |
| **ROI** | `Region of Interest` | 感兴趣区域 / 目标检测子区 | 计算机视觉与图像处理 | 图像处理中从完整画面中截取或圈定的特定子区域。本项目中指用户在屏幕上用鼠标框选出来的矩形区域，只针对该区域持续采集并识别，极大节省 CPU/GPU 算力，提升识别帧率。 |
| **ECC** | `Error Correction Code` | 纠错码 / 容错级别 | 信息论与编码算法 | QR 码采用 Reed-Solomon 纠错算法，允许在二维码遭受磨损、污损、遮挡或失真时依然能够正确无损还原数据。分为四个级别：L (Low: 约 7%)、M (Medium: 约 15%)、Q (Quartile: 约 25%)、H (High: 约 30%)。本项目在二维码生成器中提供 ECC 级别的自由选择与配置。 |
| **FPS** | `Frames Per Second` | 每秒传输帧数（帧率/刷新率） | 性能与实时处理 | 屏幕持续抓取或摄像头视频流每秒分析的图像帧数。本项目提供可调扫描频率（30ms - 300ms），在高性能识别与极低能耗间取得最佳平衡。 |
| **URL** | `Uniform Resource Locator` | 统一资源定位符（网络网址） | 网络与通信协议 | 互联网上标准资源的地址格式（如 `https://...`）。QR 码最常见的载荷为 URL，本项目内置协议识别，识别后可一键在默认浏览器中安全打开。 |
| **RGB** | `Red, Green, Blue` | 红绿蓝三原色色彩模式 | 色彩空间与图像格式 | 显示器色彩呈现的加色混合模型。每像素由红、绿、蓝 3 通道组成。OpenCV 默认读写为 BGR 顺序，本项目在引擎间流转时进行了标准化色彩空间转换。 |
| **RGBA** | `Red, Green, Blue, Alpha` | 包含透明度通道的色彩模式 | 色彩空间与图像格式 | 在 RGB 基础上增加 Alpha 透明度通道（32-bit）。在本项目屏幕框选遮罩层（Overlay）及半透明暗化蒙版绘制中广泛使用。 |
| **JSON** | `JavaScript Object Notation` | 轻量级数据交换格式 | 数据持久化与协议 | 人类易读、轻量且与语言无关的结构化文本格式。本项目用于本地永久存储识别历史记录（`data/history.json`）和用户偏好配置。 |
| **OS** | `Operating System` | 操作系统 | 系统平台 | 管理计算机硬件与软件资源的系统软件。本项目专注于 Windows 平台深度优化（DPI、GDI 截图、原生剪贴板），同时核心解码引擎具备良好跨平台兼容性。 |
| **PNG** | `Portable Network Graphics` | 便携式网络图形（无损压缩图像格式） | 多媒体与文件格式 | 支持无损压缩与透明通道的位图文件格式，是保存和导出二维码图像的首选标准格式。 |
| **API** | `Application Programming Interface` | 应用程序编程接口 | 软件工程 | 模块、系统底层库或第三方服务之间约定的通信与调用接口。本项目涵盖了 Win32 系统 API、OpenCV API、Pillow 图像 API 等多层级调用。 |

---

## 🛠️ 项目目录结构

```
QR/
├── run.py                 # 【唯一启动器】支持 GUI 桌面启动与 CLI 命令行调用
├── requirements.txt       # Python 依赖清单 (customtkinter, opencv-python, pillow, qrcode, numpy)
├── README.md              # 完整技术文档与术语释义表
├── 项目准则.md            # 项目规范原始准则
├── data/                  # 本地持久化数据存储
│   └── history.json       # 扫描与生成历史记录 (JSON 格式)
└── src/                   # 【核心代码目录】
    ├── __init__.py        # 代码包导出与版本元信息
    ├── abbreviations.py   # 术语缩写集中词典与格式化助手
    ├── constants.py       # 常量、主题配色与默认参数配置
    ├── pure_decoder.py    # 纯 Python Reed-Solomon QR 兜底解码器
    ├── qr_engine.py       # 多层级容错解码引擎 (Aruco / Standard / Pure) 与生成器
    ├── screen_capture.py  # Windows GDI 底层高性能截屏与多显示器管理
    ├── overlay.py         # 交互式屏幕框选遮罩浮层 (带暗化蒙版与像素标尺)
    ├── camera.py          # 摄像头后台采集线程 (多线程非阻塞)
    ├── history.py         # 历史记录管理器 (增删改查、TXT/CSV/JSON 导出)
    ├── utils.py           # 原生剪贴板读写、URL 检测打开、DPI 感知与音效
    └── app.py             # 现代化 CustomTkinter GUI 桌面应用主界面
```

---

## 🚀 启动与使用指南

### 1. 安装环境依赖

```bash
pip install -r requirements.txt
```

### 2. 启动图形桌面客户端 (GUI)

直接运行唯一启动器即可拉起现代化桌面界面：

```bash
python run.py
```

### 3. 命令行快速使用 (CLI)

启动器亦支持直接在终端中进行快捷解码与生成：

```bash
# 查看帮助信息与版本
python run.py --help
python run.py --version

# 查看完整技术术语缩写词典
python run.py --glossary

# 命令行识别本地图片中的二维码
python run.py --decode my_code.png

# 命令行生成二维码图片 (可选指定纠错级别 L/M/Q/H 及输出文件)
python run.py --generate "https://antigravity.google.com" --out my_qr.png --ecc H
```

---

## 💡 核心功能亮点

1. **🖥️ 屏幕区域截屏扫码 (Screen ROI)**
   - 鼠标自由拖动框选任意屏幕局部区域（支持多显示器、全虚拟桌面）。
   - 全屏快速一键截屏识别。
   - 可调周期的实时持续扫码（30ms ~ 300ms）。
   - 识别成功后支持**自动复制内容**、**自动在浏览器打开网址**、**自动暂停**与**提示音效**。
2. **🖼️ 本地图片与剪贴板图像解码 (Image & Clipboard)**
   - 打开本地任意图片格式（PNG, JPG, BMP, WEBP, TIF 等）。
   - 支持从系统剪贴板一键读取截图（支持 `Ctrl+V` 快捷键，完美契合微信截图与 Win+Shift+S 截图工具）。
3. **📷 摄像头实时视频流扫码 (Webcam Live)**
   - 多摄像头设备自由切换。
   - 独立后台工作线程处理画面帧与解码，保障界面 60 FPS 流畅无卡顿。
   - 自动在视频画面中勾勒二维码绿色识别追踪框。
4. **⚡ 高级二维码生成器 (QR Generator)**
   - 支持任意文本与超长 URL 编码。
   - 四级 ECC 容错算法（L / M / Q / H）自由调节。
   - 预设 7 款高雅配色方案（经典黑白、宝石蓝、深林绿、紫罗兰、暗夜反色等），并支持 Hex 颜色自定义。
   - 一键将生成的二维码位图**直接写入系统原生剪贴板**（可直接在聊天工具与文档中粘贴），或保存为高清 PNG/JPG 文件。
5. **📜 智能历史记录管理 (History Manager)**
   - 分类追踪所有屏幕扫描、图片解码、摄像头识别与生成的二维码。
   - 一键复制、一键跳转打开、逐条删除或批量清空。
   - 支持将历史记录导出为 **CSV 表格**、**TXT 文本** 或 **JSON 结构化文件**。
6. **📖 术语缩写与准则速查 (Built-in Docs)**
   - 界面内置术语速查标签页，随时查阅 QR、DPI、GDI、ROI、ECC 等技术原理解析。
