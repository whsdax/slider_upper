# -*- coding: utf-8 -*-
"""生成 slider_upper 项目 AI 协作与复刻指南 PDF（reportlab）"""

from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Preformatted
)

OUTPUT = Path(__file__).parent / "slider_upper_AI复刻指南.pdf"
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")


def register_font():
    pdfmetrics.registerFont(TTFont("YaHei", str(FONT_PATH)))


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", fontName="YaHei", fontSize=22, leading=30,
            textColor=colors.HexColor("#1e293b"), alignment=1, spaceAfter=12,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", fontName="YaHei", fontSize=11, leading=18,
            textColor=colors.HexColor("#64748b"), alignment=1, spaceAfter=8,
        ),
        "h1": ParagraphStyle(
            "h1", fontName="YaHei", fontSize=16, leading=22,
            textColor=colors.HexColor("#5b21b6"), spaceBefore=14, spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2", fontName="YaHei", fontSize=13, leading=18,
            textColor=colors.HexColor("#334155"), spaceBefore=10, spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "h3", fontName="YaHei", fontSize=11, leading=16,
            textColor=colors.HexColor("#475569"), spaceBefore=8, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body", fontName="YaHei", fontSize=10, leading=16,
            textColor=colors.HexColor("#1e293b"), spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "bullet", fontName="YaHei", fontSize=10, leading=15,
            leftIndent=12, bulletIndent=0, spaceAfter=3,
        ),
        "code": ParagraphStyle(
            "code", fontName="YaHei", fontSize=8.5, leading=13,
            backColor=colors.HexColor("#1e293b"), textColor=colors.HexColor("#e2e8f0"),
            leftIndent=8, rightIndent=8, spaceBefore=4, spaceAfter=8,
        ),
    }


def tbl(data, col_widths):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "YaHei", 8.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def build():
    register_font()
    s = styles()
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=20 * mm, bottomMargin=18 * mm,
    )
    story = []
    W = A4[0] - 36 * mm

    # 封面
    story.append(Spacer(1, 50 * mm))
    story.append(Paragraph("slider_upper V5.2<br/>推杆上位机项目<br/>AI 协作与复刻完整指南", s["title"]))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(
        "整合内容：项目架构 · 两份协议文档区别 · 原作者思维路径<br/>"
        "分阶段开发 · Prompt 模板 · 常见翻车与纠偏<br/>"
        "适用对象：零基础初学者，希望用 AI 从零理解并构建同类项目",
        s["subtitle"],
    ))
    story.append(Spacer(1, 20 * mm))
    story.append(Paragraph("生成日期：2026-06-29", s["subtitle"]))
    story.append(PageBreak())

    # 第一章
    story.append(Paragraph("第一章  项目是什么", s["h1"]))
    story.append(Paragraph(
        "slider_upper V5.2 是一个运行在 Windows 上的 LA 系列电动推杆上位机软件。"
        "通过 PEAK PCAN-USB 适配器，用 CAN-FD 总线与推杆驱动器通信，实现连接扫描、"
        "位置校准、闭环移动、力传感器标零、修改设备 ID、实时状态监控等功能。",
        s["body"],
    ))
    story.append(Paragraph("1.1 技术栈", s["h2"]))
    for item in [
        "语言：Python 3.8+",
        "GUI：Tkinter + ttk",
        "数值：NumPy（校准采样均值/标准差）",
        "并发：threading（GUI 后台 CAN 线程）",
        "硬件：PEAK PCAN-USB + PCAN-Basic 驱动（PCANBasic.dll）",
        "协议：CAN-FD（仲裁 1Mbps / 数据 5Mbps）+ LA 推杆私有协议",
        "打包：PyInstaller",
    ]:
        story.append(Paragraph(f"• {item}", s["bullet"]))

    story.append(Paragraph("1.2 文件结构", s["h2"]))
    story.append(Preformatted(
        "slider_upper_V5.2/\n"
        "├── PCANBasic.py      # PEAK 官方驱动绑定\n"
        "├── can.py            # 本地 CAN 抽象层\n"
        "├── slider_upper.py   # Tkinter GUI 主程序\n"
        "├── position_light.py # 最简位置控制示例\n"
        "├── calib_v3/v4.py    # 命令行校准工具\n"
        "├── main.py           # 命令行全功能调试\n"
        "├── AI-teach.html     # AI 协作指南\n"
        "└── KAI执行器通信32字节协议.xlsx  # 推杆通信协议",
        s["code"],
    ))

    story.append(Paragraph("1.3 分层架构", s["h2"]))
    story.append(Preformatted(
        "应用层 → 协议层(SDO/PDO) → can.py → PCANBasic.py → dll → 硬件",
        s["code"],
    ))
    story.append(PageBreak())

    # 第二章
    story.append(Paragraph("第二章  两份文档的区别（必读）", s["h1"]))
    story.append(Paragraph(
        "初学者常混淆两份协议文档。它们对应不同硬件，用途完全不同。",
        s["body"],
    ))
    story.append(tbl([
        ["对比项", "KAIBOT关节SDO对象字典.docx", "KAI执行器通信32字节协议.xlsx"],
        ["对应硬件", "KAIBOT 关节（旋转执行器）", "KAI LA 推杆（线性执行器）"],
        ["运动单位", "角度 rad、角速度 rad/s", "线性位移 m（0.00001m）"],
        ["文档内容", "CANopen SDO 对象字典", "推杆专用通信协议（字节格式）"],
        ["与本项目", "不直接对应，另一款产品", "本项目的核心协议文档"],
        ["文档作用", "哪个地址存什么参数", "发什么字节、收什么字节"],
    ], [35 * mm, 60 * mm, 67 * mm]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "一句话：docx 是旋转关节的参数字典；xlsx 才是本推杆上位机的通信协议。本项目完全基于 xlsx。",
        s["body"],
    ))

    story.append(Paragraph("2.1 常用协议 ID", s["h2"]))
    story.append(tbl([
        ["仲裁 ID", "方向", "用途"],
        ["0x200 + id", "主机→驱动", "使能/失能、位置/速度/电流控制"],
        ["0x600 + id", "主机→驱动", "SDO 配置（offset、上报、改 ID）"],
        ["0x480 + id", "驱动→主机", "32 字节状态反馈"],
        ["0x580 + id", "驱动→主机", "SDO 响应"],
    ], [40 * mm, 35 * mm, 87 * mm]))
    story.append(PageBreak())

    # 第三章
    story.append(Paragraph("第三章  原作者的思维路径（核心）", s["h1"]))
    story.append(Paragraph(
        "复刻的目标不是复制成品，而是站在原作者处境：理解业务需求 → 思考架构 → 再用 AI 写代码。"
        "AI 是结对工程师，无法代替你提供硬件事实和验收标准。",
        s["body"],
    ))

    story.append(Paragraph("3.1 第一个困惑：怎么用 Python 跟硬件通信？", s["h2"]))
    story.append(tbl([
        ["方案", "做法", "问题"],
        ["A", "用 pip 的 python-can", "配置复杂，import can 冲突"],
        ["B", "直接用 PCANBasic.py", "每次填 TPCANMsgFD 结构体太难"],
        ["C（选中）", "写本地 can.py 包装", "接口干净，不依赖 pip，可控"],
    ], [20 * mm, 55 * mm, 87 * mm]))
    story.append(Paragraph(
        "选 C 的原因：想要 bus.send(message) 这种干净接口，且 import can 自动用本地文件。",
        s["body"],
    ))

    story.append(Paragraph("3.2 第二个困惑：先写什么？", s["h2"]))
    story.append(Paragraph(
        "新手本能是先做 GUI，但这是陷阱。正确问题是：协议理解对了吗？推杆真的会动吗？"
        "所以先写 position_light.py（约 30 行、无 GUI）。工程思维：从最小可验证单元开始。",
        s["body"],
    ))

    story.append(Paragraph("3.3 第三个困惑：推杆位置对不上真实值", s["h2"]))
    story.append(Paragraph(
        "推杆上电后编码器是相对值。需要校准：offset = 真实位置 - 原始读数，写入 SDO 0x2005。"
        "先有 calib_v3（单次采样），再迭代 calib_v4（多次采样、重试）。",
        s["body"],
    ))

    story.append(Paragraph("3.4 第四个困惑：怎么让不懂命令行的人用？", s["h2"]))
    story.append(Paragraph(
        "这时才做 GUI（Tkinter）。碰壁：recv() 阻塞导致界面卡死。"
        "解决：CAN 放后台线程，GUI 用 root.after(0, ...) 回主线程。"
        "还发现 PCAN 多次 shutdown 有 bug → 断开时不 shutdown，复用 bus。",
        s["body"],
    ))

    story.append(Paragraph("3.5 思维路径总览", s["h2"]))
    story.append(Preformatted(
        "有硬件+协议 → 自写can.py → position_light验证\n"
        "→ 位置不准做校准 → GUI+线程 → 长期稳定(不复用shutdown)",
        s["code"],
    ))
    story.append(PageBreak())

    # 第四五章
    story.append(Paragraph("第四章  能否完整复刻？材料清单", s["h1"]))
    story.append(tbl([
        ["材料", "状态", "作用"],
        ["PCANBasic.py", "有", "硬件驱动层"],
        ["KAI执行器通信32字节协议.xlsx", "有", "所有 CAN 报文字节定义"],
        ["KAIBOT关节SDO对象字典.docx", "有但不用", "另一款产品"],
        ["PEAK PCAN-USB + 驱动 + 推杆", "需自备", "真机验收"],
    ], [55 * mm, 25 * mm, 82 * mm]))
    story.append(Paragraph("结论：协议与驱动材料齐全，可以完整复刻。但必须有真机做每阶段验收。", s["body"]))

    story.append(Paragraph("第五章  分阶段迭代路线图", s["h1"]))
    story.append(tbl([
        ["阶段", "产物", "目标", "硬件验收"],
        ["P0", "can.py", "CAN-FD 能收发", "bus 初始化不报错"],
        ["P1", "position_light.py", "使能→移动→失能", "推杆伸出对应长度"],
        ["P2", "calib_v3→v4", "位置校准", "误差 < 0.05mm"],
        ["P3", "slider_upper.py", "GUI+状态监控", "连接/校准/移动正常"],
        ["P4", "文档+spec", "可维护、可打包", "pyinstaller 出 exe"],
    ], [18 * mm, 38 * mm, 50 * mm, 56 * mm]))
    story.append(Paragraph("原则：未通过当前阶段验收，不要进入下一阶段。", s["body"]))
    story.append(PageBreak())

    # 第六章 Prompt
    story.append(Paragraph("第六章  分阶段 Prompt 模板", s["h1"]))
    story.append(Paragraph("P0 — 写 can.py", s["h2"]))
    story.append(Preformatted(
        "我有 PEAK PCAN-USB，推杆用 CAN-FD 通信。\n"
        "请基于 PCANBasic.py，写本地 can.py：\n"
        "- Message、Bus、CanError，接口模仿 python-can\n"
        "- 默认 PCAN_USBBUS1，仲裁1Mbps/数据5Mbps\n"
        "- 不要 pip install python-can",
        s["code"],
    ))
    story.append(Paragraph("P1 — position_light.py", s["h2"]))
    story.append(Preformatted(
        "附件是 KAI 执行器 32 字节通信协议。\n"
        "1. 用户输入关节 ID\n"
        "2. 使能：0x200+id，00000000000700\n"
        "3. 位置：01+pos(2B小端,0.01mm)+时长ms+0F00\n"
        "4. 失能：00000000000400",
        s["code"],
    ))
    story.append(Paragraph("P2 — calib_v3.py", s["h2"]))
    story.append(Preformatted(
        "1. 使能  2. offset=0: 2B01200500000000\n"
        "3. standby: 2B03180520000000\n"
        "4. 读 0x480+id，解析 [2:4] 位置\n"
        "5. offset=实际-反馈  6. 写 offset  7. 失能",
        s["code"],
    ))
    story.append(Paragraph("P3 — slider_upper.py（分两次对话：先 UI 框架，再接入 CAN）", s["h2"]))
    story.append(PageBreak())

    # 第七八九章
    story.append(Paragraph("第七章  好 Prompt vs 坏 Prompt", s["h1"]))
    story.append(Paragraph("坏的：「帮我写个推杆上位机」— 无协议、无验收，AI 会幻觉。", s["body"]))
    story.append(Paragraph("坏的：「pip install python-can」— 与本地 can.py 冲突。", s["body"]))
    story.append(Paragraph(
        "好的：附 xlsx，指定 byte 偏移和单位，先写单函数，验收与抓包一致。",
        s["body"],
    ))
    story.append(Paragraph(
        "好的：描述具体现象，要求在现有代码上最小改动，不要重写。",
        s["body"],
    ))

    story.append(Paragraph("第八章  每次对话应提供的上下文", s["h1"]))
    story.append(tbl([
        ["优先级", "材料", "说明"],
        ["必附", "KAI执行器通信32字节协议.xlsx", "或 Sheet2~3 截图"],
        ["必说", "关节 ID、型号、行程", "如 ID=1，LA5000，0~90mm"],
        ["建议附", "当前 .py 文件", "让 AI 在现有代码上改"],
        ["建议附", "成功报文 hex", "msg.data.hex()"],
        ["建议附", "报错全文+步骤", "比「不能用」有效"],
    ], [22 * mm, 58 * mm, 82 * mm]))

    story.append(Paragraph("第九章  常见翻车与纠偏", s["h1"]))
    story.append(tbl([
        ["现象", "纠偏话术"],
        ["import can 不对", "卸载 python-can，只用本地 can.py"],
        ["位置差100倍", "对照 xlsx 列换算表，统一 int(mm*100)"],
        ["收不到0x480", "先发 2B03180520000000 开上报"],
        ["第二次连接失败", "断开不调 shutdown，复用 bus"],
        ["GUI卡死", "CAN放线程，UI用 root.after"],
    ], [45 * mm, 117 * mm]))
    story.append(PageBreak())

    # 第十十一章
    story.append(Paragraph("第十章  你需要具备的能力", s["h1"]))
    for item in [
        "把业务需求翻译成工程问题（控制推杆 → 发 CAN → 需要 can.py）",
        "知道验收标准（推杆移动到正确位置，不是代码跑起来）",
        "分清自己决策什么（架构、线程），什么交给 AI（结构体填充）",
        "遇到问题能描述清楚现象",
    ]:
        story.append(Paragraph(f"• {item}", s["bullet"]))
    story.append(Paragraph(
        "AI 是工具，但你必须是知道要造什么、为什么造的人。"
        "推杆不知道自己在哪——这是硬件事实，AI 不知道，你必须告诉它。",
        s["body"],
    ))

    story.append(Paragraph("第十一章  项目内学习资源", s["h1"]))
    for item in [
        "AI-teach.html：如何用 AI 从零构建本项目",
        "teach.html：项目写好后如何读懂代码",
        "CAN-guide.md：CAN 协议完整梳理",
        "README.md：功能、环境、快速开始",
    ]:
        story.append(Paragraph(f"• {item}", s["bullet"]))

    story.append(Paragraph("附录：常用 hex 指令", s["h1"]))
    story.append(tbl([
        ["功能", "数据 hex"],
        ["offset 清零", "2B01200500000000"],
        ["开启上报", "2B03180520000000"],
        ["使能", "00000000000700"],
        ["失能", "00000000000400"],
        ["位置模式", "01 + pos(2B) + duration(2B) + 0F00"],
        ["改 ID", "2F012001 + new_id + 000000"],
    ], [45 * mm, 117 * mm]))

    doc.build(story)
    print(f"PDF 已生成: {OUTPUT}")


if __name__ == "__main__":
    build()
