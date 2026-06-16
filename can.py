# -*- coding: utf-8 -*-
"""
can.py - 本地 CAN 总线抽象层

本模块模仿 python-can 库的 Message / Bus / CanError 接口，
底层通过 PCANBasic.py 调用 PEAK PCANBasic.dll 驱动。

重要：请勿 pip install python-can，否则会与本模块命名冲突。
项目内所有 import can 均指导入本文件。
"""

from PCANBasic import *  # 导入 PEAK 驱动全部符号（句柄、错误码、结构体、PCANBasic 类）
import time              # perf_counter 用于 recv 超时计时；sleep 用于轮询让步


class Message:
    """
    CAN-FD 报文封装类，兼容 python-can 的 Message 接口。

    两种构造方式：
    1. 发送：传入 arbitration_id + data，自动填充 TPCANMsgFD 结构体
    2. 接收：传入 msgFD（ReadFD 返回值）+ timestamp，还原为 Python 对象
  """
    arbitration_id = 0           # 仲裁 ID（11 位标准帧，本项目不使用扩展帧）
    data = None                  # Python bytes 形式的数据载荷
    msgCanMessageFD = TPCANMsgFD()  # 底层 C 结构体，供 Bus.send → WriteFD 使用
    timestamp = 0                # 接收时间戳（微秒）

    def __init__(self, arbitration_id=None, data=None, is_extended_id=False, is_fd=True, msgFD=None, timestamp=0):
        # 接收路径：从硬件 ReadFD 结果构造
        if msgFD != None:
            self.__init_msgFD(msgFD, timestamp)
            return
        # 发送路径：从 Python 参数构造
        self.data = data
        self.arbitration_id = arbitration_id
        dlen = len(data)
        self.msgCanMessageFD.ID = arbitration_id
        # CAN-FD DLC 编码：DLC 值与实际字节数非线性映射（CiA 规范）
        if dlen <= 8:
            self.msgCanMessageFD.DLC = dlen       # DLC 0~8 对应 0~8 字节
        elif dlen <= 12:
            self.msgCanMessageFD.DLC = 9          # DLC 9 对应 12 字节
        elif dlen <= 16:
            self.msgCanMessageFD.DLC = 10         # DLC 10 对应 16 字节
        elif dlen <= 20:
            self.msgCanMessageFD.DLC = 11
        elif dlen <= 24:
            self.msgCanMessageFD.DLC = 12
        elif dlen <= 32:
            self.msgCanMessageFD.DLC = 13         # 推杆 32 字节状态报文走此档
        elif dlen <= 48:
            self.msgCanMessageFD.DLC = 14         # 推杆 48 字节状态报文走此档
        else:
            self.msgCanMessageFD.DLC = 15         # 最大 64 字节
        if dlen > 64:
            dlen = 64                             # 超出 64 字节则截断
        if is_fd:
            # FD 帧 + 比特率切换（BRS）：数据段以更高波特率传输，推杆通信必需
            self.msgCanMessageFD.MSGTYPE = PCAN_MESSAGE_FD.value | PCAN_MESSAGE_BRS.value
        if is_extended_id:
            # 29 位扩展帧（本项目默认 is_extended_id=False）
            self.msgCanMessageFD.MSGTYPE = PCAN_MESSAGE_EXTENDED.value
        # 逐字节拷贝到 C 定长数组 DATA[64]
        for i in range(dlen):
            self.msgCanMessageFD.DATA[i] = data[i]

    def __init_msgFD(self, msgFD, timestamp):
        """从 ReadFD 返回的 TPCANMsgFD 结构体还原为 Python Message 对象"""
        self.msgCanMessageFD = msgFD
        data = None
        dlc = msgFD.DLC
        # 按 DLC 反查实际数据长度（与上方编码规则对称）
        if dlc <= 8:
            data = msgFD.DATA[0:dlc]
        elif dlc == 9:
            data = msgFD.DATA[0:12]
        elif dlc == 10:
            data = msgFD.DATA[0:16]
        elif dlc == 11:
            data = msgFD.DATA[0:20]
        elif dlc == 12:
            data = msgFD.DATA[0:24]
        elif dlc == 13:
            data = msgFD.DATA[0:32]
        elif dlc == 14:
            data = msgFD.DATA[0:48]
        elif dlc == 15:
            data = msgFD.DATA[0:64]
        self.data = bytes(data)                   # 转为不可变 bytes 供上层解析
        self.arbitration_id = msgFD.ID
        self.timestamp = timestamp.value          # c_ulonglong 需 .value 取 Python int


class CanError(Exception):
    """CAN 总线异常类，接口兼容 python-can.CanError，供上层 try/except 捕获"""
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class Bus:
    """
    CAN 总线类，封装 PCAN-USB 通道的初始化、收发、关闭。

    默认使用 PCAN_USBBUS1（USB 通道 1），CAN-FD 波特率：
    仲裁段 1Mbps，数据段 5Mbps（80MHz 时钟配置）。
    """
    PcanHandle = PCAN_USBBUS1  # 默认 PCAN-USB 第 1 通道（句柄 0x51）
    # CAN-FD 波特率字符串：f_clock_mhz=80 表示 80MHz 时钟
    # nom_* 为仲裁段参数（1Mbps），data_* 为数据段参数（5Mbps）
    BitrateFD = b'f_clock_mhz=80, nom_brp=2, nom_tseg1=29, nom_tseg2=10, nom_sjw=10, data_brp=1, data_tseg1=11, data_tseg2=4, data_sjw=4'
    m_DLLFound = False         # 标记 PCANBasic.dll 是否加载成功

    def __init__(self):
        # 加载 PCANBasic.dll 并初始化 FD 通道；失败则抛出 CanError
        try:
            self.m_objPCANBasic = PCANBasic()  # 实例化驱动，内部 LoadLibrary
            self.m_DLLFound = True
        except Exception as e:
            self.m_DLLFound = False
            raise CanError(e)                  # DLL 未安装或路径不对
        stsResult = self.m_objPCANBasic.InitializeFD(self.PcanHandle, self.BitrateFD)
        if stsResult != PCAN_ERROR_OK:
            errstr = self.GetFormattedError(stsResult)
            raise CanError(errstr)             # 通道被占用、硬件未连接等

    def GetFormattedError(self, error):
        """
        将 PCAN 错误码翻译为可读文本（英文）

        Parameters:
            error: TPCANStatus 错误码

        Returns:
            错误描述字符串
        """
        stsReturn = self.m_objPCANBasic.GetErrorText(error, 0x09)  # 0x09=英语
        if stsReturn[0] != PCAN_ERROR_OK:
            return "An error occurred. Error-code's text ({0:X}h) couldn't be retrieved".format(error)
        else:
            message = str(stsReturn[1])
            return message.replace("'", "", 2).replace("b", "", 1)

    def send(self, message):
        """发送一条 CAN-FD 报文；message 须为含 msgCanMessageFD 的 Message 实例"""
        try:
            return self.m_objPCANBasic.WriteFD(self.PcanHandle, message.msgCanMessageFD)
        except Exception as e:
            raise CanError(e)

    def recv(self, waittime):
        """
        阻塞接收一条 CAN-FD 报文，最长等待 waittime 秒。

        Parameters:
            waittime: 最大等待时间（秒），超时返回 None

        Returns:
            Message 实例，或 None（超时/无报文）
        """
        start_time = time.perf_counter()
        stsResult, msg, timestamp = self.m_objPCANBasic.ReadFD(self.PcanHandle)
        # 队列为空时持续轮询，直到超时
        while stsResult == PCAN_ERROR_QRCVEMPTY:
            stsResult, msg, timestamp = self.m_objPCANBasic.ReadFD(self.PcanHandle)
            end_time = time.perf_counter()
            if end_time - start_time >= waittime:
                break
            time.sleep(0.00001)  # 10μs 让步，避免 CPU 占满

        if stsResult != PCAN_ERROR_OK:
            return None

        return Message(msgFD=msg, timestamp=timestamp)

    def shutdown(self):
        """释放 PCAN 通道；注意：多次调用可能导致驱动 bug，GUI 中需谨慎使用"""
        self.m_objPCANBasic.CAN_Uninitialize(self.PcanHandle)
