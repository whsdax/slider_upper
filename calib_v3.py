# -*- coding: utf-8 -*-
"""
calib_v3.py - 推杆位置校准脚本（命令行版 v3）

功能：通过 CAN 总线对指定关节推杆进行位置零点/偏移校准。
流程：使能 → 清零 offset → 开启上报 → 读取当前反馈位置 →
      用户输入实际位置 → 计算并写入补偿 offset → 失能。

与 calib_v4 / slider_upper.py 的差异：
  - 单次采样，无标准差过滤
  - 无重试与闭环验证
  - 适合快速手动校准

依赖：本地 can 模块（勿 pip install python-can）
"""

import can  # 本地 can.py，不可安装公共 python-can 库否则冲突
import time
import threading  # 本文件未使用，保留供扩展
import numpy as np  # 本文件未使用，保留供扩展

# ---------- 用户输入关节 ID ----------
print("请输入关节id：1~6整数")
device_id = int(input())  # 关节 ID，后续所有 CAN 仲裁 ID 均在此基础上 +device_id

# ---------- 初始化 CAN 总线 ----------
try:
    bus = can.Bus()  # 打开 PCAN-USB 通道，失败抛 CanError
except can.CanError as e:
    print("Error setting up CAN bus:", e)
    exit()


def send_message(bus, control, data):
    """
    发送一条 CAN-FD 报文。

    参数:
        bus: can.Bus 实例
        control: 基础仲裁 ID（如 0x200 控制、0x600 SDO），实际发送 ID = control + device_id
        data: 十六进制字符串，如 '2B01200500000000'
    """
    byte_data = data

    message = can.Message(
        arbitration_id=control + device_id,  # 加上关节 ID 偏移
        data=bytes.fromhex(byte_data),     # hex 字符串转 bytes
        is_extended_id=False,              # 标准 11 位帧
        is_fd=True                         # CAN-FD 帧
    )
    try:
        bus.send(message)
    except can.CanError:
        print("Message NOT sent")


def is_enable(sign=0):
    """
    推杆使能/失能。

    参数:
        sign: 1=使能（控制字 0x0700），0=失能（控制字 0x0400）
    报文发往 0x200 + device_id
    """
    if sign == 1:
        send_message(bus, 0x200, '00000000000700')  # 使能
    else:
        send_message(bus, 0x200, '00000000000400')  # 下使能


def receive_message(bus, timeout, abritration_id_list):
    """
    在超时时间内等待指定仲裁 ID 的报文。

    参数:
        bus: can.Bus 实例
        timeout: 最长等待秒数
        abritration_id_list: 基础 ID 列表（如 [0x480]），内部自动 +device_id

    返回:
        Message 或 None（超时）
    """
    if isinstance(abritration_id_list, int):
        abritration_id_list = [abritration_id_list]
    # 将基础 ID 转为实际仲裁 ID（加上关节 ID）
    abritration_id_list = [x + device_id for x in abritration_id_list]

    start_time = time.time()

    while True:
        if time.time() - start_time > timeout:
            return None  # 超时未收到目标报文

        message = bus.recv(1.0)  # 单次最多等 1 秒
        if message == None:
            continue
        if message.arbitration_id in abritration_id_list:
            return message


def clear_queue(bus, timeout=0.001):
    """清空 CAN 接收队列中的积压报文，避免读到旧数据"""
    while bus.recv(timeout) is not None:
        pass
    return print("报文缓存已清零")


# ==================== 主校准流程（六步） ====================

# [步骤1] 使能推杆
is_enable(1)
arbi_id = 0x600 + device_id  # SDO 配置通道仲裁 ID

# [步骤2] 清空接收缓存，避免残留旧报文干扰
clear_queue(bus)

# [步骤3] 发送 offset=0，清零位置补偿
# SDO 写：2B=写2字节，01 20=索引0x2005子索引0x01（offset），后4字节=0
bus.send(
    can.Message(
        arbitration_id=arbi_id,
        data=bytes.fromhex('2B01200500000000'),
        is_extended_id=False,
        is_fd=True
    )
)
print("已发送offset=0的报文")

# [步骤4] 发送 standby 上报指令，触发驱动器周期性发送状态
# 2B03180520000000：索引0x1805子索引0x03，0x20=32 可能表示上报频率相关
bus.send(
    can.Message(
        arbitration_id=arbi_id,
        data=bytes.fromhex('2B03180520000000'),
        is_extended_id=False,
        is_fd=True
    )
)
print("已发送standby报文")

# [步骤5] 等待并读取位置反馈报文（0x480 + device_id）
current_msg = receive_message(bus, 2, [0x480])
if current_msg is None:
    raise TimeoutError(
        "等待报文超时：2秒内未收到ID=0x{:03X}的反馈报文。\n"
        "可能原因：\n"
        "1) 设备未上电/未使能/未连接到总线，重新链接PCAN\n"
        "2) 反馈ID不对（代码在receive_message里会自动+device_id）\n".format(0x480 + device_id)
    )

print(f"发送offset=0之后的报文值{current_msg.data.hex(' ').upper()}")

# 从反馈报文字节 [2:4] 解析位置，小端有符号，单位 0.01mm
msg_position = int.from_bytes(current_msg.data[2:4], byteorder='little', signed=True)
print(f"获取当前报文反馈的位置为{msg_position}")

# [步骤6] 用户输入推杆实际推出长度，计算并写入 offset
print("请输入推杆的实际推出长度/0.01mm（如推出12.34mm，则输入1234）：")
real_position = int(input())  # 用户测量的真实位置（0.01mm 为单位）

offset_position = real_position - msg_position  # 补偿量 = 目标实际值 - 当前反馈值
print(f"需要补偿{offset_position}")

# 将 offset 转为 2 字节小端 hex，拼入 SDO 写报文
offset_position = int(offset_position).to_bytes(2, byteorder='little', signed=True).hex()
data = '2B012005' + offset_position + '0000'

bus.send(can.Message(arbitration_id=arbi_id, data=bytes.fromhex(data), is_extended_id=False, is_fd=True))

print("已发送校准报文,校验成功")
is_enable(0)  # 校准完成，失能推杆
