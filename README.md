# slider_upper — 推杆上位机 V5.2

LA 系列电动推杆 **CAN-FD** 上位机软件：位置校准、闭环移动、力传感器标零、设备 ID 配置、实时状态监控。

仓库地址：[https://github.com/whsdax/slider_upper](https://github.com/whsdax/slider_upper)

## 功能特性

- **GUI 主程序**（`slider_upper.py`）：连接 PCAN、扫描关节、校准/移动、状态面板、热插拔检测
- **CLI 校准**（`calib_v3.py` / `calib_v4.py`）：命令行位置 offset 校准（v4 含多次采样与重试）
- **CLI 全功能**（`main.py`）：位置/速度/电流/余弦轨迹等调试命令
- **最小示例**（`position_light.py`）：使能 → 移动 → 失能，验证 CAN 链路

## 环境要求

| 项目 | 说明 |
|------|------|
| 系统 | Windows（GUI 使用 Tkinter + PCAN 驱动） |
| Python | 3.8+ |
| 硬件 | PEAK PCAN-USB 适配器、LA 推杆（LA5000 / LA2000 / LA400） |
| 驱动 | [PEAK PCAN-Basic](https://www.peak-system.com/)，`PCANBasic.dll` 需在 PATH 或同目录 |
| Python 包 | `numpy`（校准采样） |

**重要：请勿** `pip install python-can`。本项目使用本地 [`can.py`](can.py)，安装公共库会导致 `import can` 冲突。

## 协议文档（需自备，不在本仓库）

开发与 AI 协作时，请向设备厂商索取：

**`KAI执行器通信32字节协议.xlsx`**

内含 SDO 指令（`0x600+id`）、TxPDO4 反馈 32 字节（`0x480+id`）、故障码定义。无此文件难以正确解析报文字段。

## 快速开始

```bash
# 安装依赖（仅 numpy，勿装 python-can）
pip install numpy

# 启动 GUI
python slider_upper.py

# CLI 校准
python calib_v3.py
python calib_v4.py

# 最小位置控制测试
python position_light.py

# 打包 exe（需 pyinstaller）
pyinstaller slider_upper.spec
```

## 项目结构

| 文件 | 说明 |
|------|------|
| `slider_upper.py` | GUI 主程序 V5.2 |
| `can.py` | 本地 CAN 抽象层（模仿 python-can） |
| `PCANBasic.py` | PEAK 官方 PCAN-Basic Python 绑定 |
| `main.py` | CLI 交互式全功能控制 |
| `calib_v3.py` | 命令行校准 v3（单次采样） |
| `calib_v4.py` | 命令行校准 v4（多次采样 + 重试） |
| `position_light.py` | 最简位置控制示例 |
| `slider_upper.spec` | PyInstaller 打包配置 |
| `teach.html` | 代码阅读教学文档（四段式讲解） |
| `AI-teach.html` | **如何用 AI 从零构建本项目**（新手对话指南） |

## 教学文档

本地用浏览器打开：

- [`teach.html`](teach.html) — 读懂现有代码：架构、协议、逐文件说明
- [`AI-teach.html`](AI-teach.html) — 用 AI 从零做出本项目：迭代路线、Prompt 模板、协议 Excel 用法

推荐顺序：先读 `AI-teach.html` → 开发与 AI 协作 → 再读 `teach.html` 深入理解。

## CAN 协议速查

| 仲裁 ID | 方向 | 用途 |
|---------|------|------|
| `0x200 + id` | 主机 → 驱动 | 使能/失能、位置/速度/电流控制 |
| `0x600 + id` | 主机 → 驱动 | SDO 配置（offset、上报、改 ID） |
| `0x480 + id` | 驱动 → 主机 | 状态反馈（32 字节） |
| `0x180 + id` | 驱动 → 主机 | 状态字 |
| `0x580 + id` | 驱动 → 主机 | SDO 响应 |

使能：`00000000000700` · 失能：`00000000000400` · 位置模式：`01` + 目标(2B小端) + 时长ms(2B) + `0F00`

## 致谢

- [`PCANBasic.py`](PCANBasic.py) 版权归 [PEAK-System Technik GmbH](https://www.peak-system.com/)
