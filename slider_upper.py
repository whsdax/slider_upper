# -*- coding: utf-8 -*-
"""
slider_upper.py - 推杆上位机 GUI 主程序 V5.2

功能：通过 CAN-FD 总线控制 LA 系列推杆，提供：
  - 连接/扫描/热插拔检测
  - 位置校准（offset 补偿）
  - 闭环移动到目标位置
  - 力传感器标零、修改设备 ID
  - 实时状态监控（电流、温度、故障码等）

依赖：本地 can 模块（勿 pip install python-can）
线程：CAN 操作在后台线程，GUI 更新通过 root.after 回到主线程
"""

import tkinter as tk
from tkinter import ttk, messagebox
import can  # 本地 can.py
import time
import numpy as np
import threading
import ctypes

# 高 DPI 屏幕适配，避免界面模糊（仅 Windows 有效）
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    pass


class CalibrationApp:
    """推杆校准与控制系统主窗口类"""

    def __init__(self, root):
        self.root = root
        self.root.title("推杆上位机V5.2")
        self.root.geometry("480x480")
        self.root.resizable(False, False)

        # --- 连接与设备状态 ---
        self.device_id = tk.IntVar(value=1)           # 当前选中关节 ID（1~10）
        self.current_position = tk.StringVar(value="--")  # 顶部显示的当前位置 mm
        self.calib_result = tk.StringVar(value="")    # 校准结果文本
        self.move_result = tk.StringVar(value="")     # 移动结果文本
        self.is_calibrating = False                   # 校准/移动进行中标志，防止并发操作
        self.running = True                           # watch 线程运行标志
        self.connected = False                        # CAN 是否已连接
        self.bus = None                               # can.Bus 实例，连接后赋值
        self._watch_thread = None                     # 后台位置监控线程引用
        self.detected_ids = set()                     # 扫描到的在线关节 ID 集合
        self.last_msg_time = time.time()              # 上次收到 CAN 消息时间，用于断连检测
        self.disconnected_reported = False            # 是否已提示过断连，避免重复弹窗

        # 各型号推杆最大行程（mm），用于输入校验
        self.model_stroke = {
            "LA5000": 90.0,
            "LA2000": 40.0,
            "LA400": 35.0
        }
        self.selected_model = tk.StringVar(value="LA5000")

        # 底部状态面板各字段，绑定 StringVar 供 Label 自动刷新
        self.status_vars = {
            "status": tk.StringVar(value="--"),
            "position": tk.StringVar(value="--"),
            "velocity": tk.StringVar(value="--"),
            "torque": tk.StringVar(value="--"),
            "errorcode": tk.StringVar(value="--"),
            "ia": tk.StringVar(value="--"),
            "ib": tk.StringVar(value="--"),
            "ic": tk.StringVar(value="--"),
            "udc": tk.StringVar(value="--"),
            "idc": tk.StringVar(value="--"),
            "id": tk.StringVar(value="--"),
            "iq": tk.StringVar(value="--"),
            "id_ref": tk.StringVar(value="--"),
            "iq_ref": tk.StringVar(value="--"),
            "torq_ref": tk.StringVar(value="--"),
            "mos_temp": tk.StringVar(value="--"),
            "motor_temp": tk.StringVar(value="--"),
        }
        
        self._setup_ui()

    def _setup_ui(self):
        """构建主界面：顶栏连接区、控制区、校准/移动区、状态区"""
        self.root.title("推杆上位机V5.2")
        self.root.geometry("1100x1000")
        self.root.resizable(False, False)
        
        style = ttk.Style()
        style.theme_use("clam")
        
        colors = {
            "bg": "#F5F5F5",
            "frame_bg": "#FFFFFF",
            "primary": "#2196F3",
            "success": "#4CAF50",
            "warning": "#FF9800",
            "danger": "#F44336",
            "text": "#333333",
            "subtext": "#666666",
            "border": "#E0E0E0"
        }
        
        style.configure(".", background=colors["bg"])
        style.configure("TFrame", background=colors["frame_bg"])
        style.configure("TLabelframe", background=colors["frame_bg"], bordercolor=colors["border"])
        style.configure("TLabelframe.Label", background=colors["frame_bg"], foreground=colors["primary"], font=("Segoe UI", 11, "bold"))
        style.configure("TLabel", background=colors["frame_bg"], foreground=colors["text"], font=("Segoe UI", 10))
        style.configure("TEntry", fieldbackground=colors["frame_bg"], bordercolor=colors["border"])
        style.configure("TCombobox", fieldbackground=colors["frame_bg"], bordercolor=colors["border"])
        style.configure("Accent.TButton", background=colors["primary"], foreground="white", font=("Segoe UI", 10, "bold"))
        
        self.root.configure(bg=colors["bg"])
        
        main_frame = ttk.Frame(self.root, padding="12")
        main_frame.configure(style="TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ---------- 顶栏：标题 + 连接按钮 ----------
        header_frame = tk.Frame(main_frame, bg=colors["primary"], height=70)
        header_frame.pack(fill=tk.X, pady=(0, 12))
        header_frame.pack_propagate(False)

        tk.Label(header_frame, text="推杆控制系统 V5.2", bg=colors["primary"], fg="white",
                font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT, padx=20, pady=15)

        self.connect_btn = tk.Button(header_frame, text="连  接", command=self._toggle_connection,
                                     bg="#9E9E9E", fg="white", font=("Segoe UI", 13, "bold"),
                                     relief="raised", bd=3, cursor="hand2", width=10)
        self.connect_btn.pack(side=tk.RIGHT, padx=20, pady=10)

        # ---------- 控制区：关节ID、型号、当前位置、写入新ID ----------
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        control_inner = tk.Frame(control_frame, bg=colors["frame_bg"], relief="solid", bd=1)
        control_inner.pack(fill=tk.X, padx=5, pady=5)

        row1 = tk.Frame(control_inner, bg=colors["frame_bg"])
        row1.pack(fill=tk.X, pady=(8, 4))

        tk.Label(row1, text="关节ID:", bg=colors["frame_bg"], font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(15, 5), pady=8)
        self.id_combo = ttk.Combobox(row1, textvariable=self.device_id, values=[str(i) for i in range(1, 11)],
                                     width=6, state="readonly", font=("Segoe UI", 10))
        self.id_combo.pack(side=tk.LEFT, padx=(0, 15))

        tk.Label(row1, text="推杆型号:", bg=colors["frame_bg"], font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 5), pady=8)
        self.model_combo = ttk.Combobox(row1, textvariable=self.selected_model,
                                        values=list(self.model_stroke.keys()),
                                        width=8, state="readonly", font=("Segoe UI", 10))
        self.model_combo.pack(side=tk.LEFT, padx=(0, 15))

        tk.Label(row1, text="当前位置:", bg=colors["frame_bg"], font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 5), pady=8)
        self.current_pos_label = tk.Label(row1, textvariable=self.current_position,
                                            bg=colors["frame_bg"], font=("Segoe UI", 12, "bold"), foreground=colors["primary"])
        self.current_pos_label.pack(side=tk.LEFT)
        tk.Label(row1, text="mm", bg=colors["frame_bg"], font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 15))

        row2 = tk.Frame(control_inner, bg=colors["frame_bg"])
        row2.pack(fill=tk.X, pady=(4, 4))

        tk.Label(row2, text="新ID:", bg=colors["frame_bg"], font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(15, 5), pady=8)
        self.new_id_var = tk.IntVar(value=1)
        self.new_id_combo = ttk.Combobox(row2, textvariable=self.new_id_var,
                                         values=[str(i) for i in range(1, 11)],
                                         width=4, state="readonly", font=("Segoe UI", 10))
        self.new_id_combo.pack(side=tk.LEFT, padx=(0, 10))

        self.write_id_btn = ttk.Button(row2, text="写入新ID", command=self._write_new_id,
                                        width=10, style="Accent.TButton")
        self.write_id_btn.pack(side=tk.LEFT, padx=(0, 10), pady=6)

        # ---------- 力传感器标零 ----------
        zero_frame = ttk.LabelFrame(main_frame, text="力传感器标零", padding="8")
        zero_frame.pack(fill=tk.X, pady=(0, 10))

        style.configure("Orange.TButton", background=colors["warning"], foreground="white", font=("Segoe UI", 10, "bold"))
        self.zero_calib_btn = ttk.Button(zero_frame, text="力传感器标零", command=self._force_zero_calib,
                                        width=16, style="Orange.TButton")
        self.zero_calib_btn.pack(pady=6)

        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # ---------- 校准控制（左栏） ----------
        calib_frame = ttk.LabelFrame(content_frame, text="校准控制", padding="10")
        calib_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        
        input_frame = tk.Frame(calib_frame, bg=colors["frame_bg"])
        input_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(input_frame, text="目标位置:", bg=colors["frame_bg"], font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(10, 5))
        self.calib_target_entry = ttk.Entry(input_frame, font=("Segoe UI", 11), width=12)
        self.calib_target_entry.pack(side=tk.LEFT, padx=5)
        self.calib_target_entry.insert(0, "0.00")
        tk.Label(input_frame, text="mm", bg=colors["frame_bg"], font=("Segoe UI", 10)).pack(side=tk.LEFT)
        
        self.calib_btn = ttk.Button(calib_frame, text="开始校准", command=self._start_calibration,
                                    style="Accent.TButton")
        self.calib_btn.pack(fill=tk.X, padx=10, pady=(0, 8))
        
        calib_result_frame = tk.Frame(calib_frame, bg=colors["border"], relief="flat", height=40)
        calib_result_frame.pack(fill=tk.X, padx=10)
        calib_result_frame.pack_propagate(False)
        self.calib_result_label = tk.Label(calib_result_frame, textvariable=self.calib_result, 
                                           font=("Segoe UI", 10, "bold"), bg=colors["border"], 
                                           fg=colors["text"], justify=tk.CENTER, anchor=tk.CENTER)
        self.calib_result_label.pack(fill=tk.BOTH, padx=2, pady=2)

        # ---------- 移动控制（右栏） ----------
        move_frame = ttk.LabelFrame(content_frame, text="移动控制", padding="10")
        move_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))
        
        input_frame2 = tk.Frame(move_frame, bg=colors["frame_bg"])
        input_frame2.pack(fill=tk.X, pady=(0, 10))
        tk.Label(input_frame2, text="目标位置:", bg=colors["frame_bg"], font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(10, 5))
        self.move_target_entry = ttk.Entry(input_frame2, font=("Segoe UI", 11), width=12)
        self.move_target_entry.pack(side=tk.LEFT, padx=5)
        self.move_target_entry.insert(0, "0.00")
        tk.Label(input_frame2, text="mm", bg=colors["frame_bg"], font=("Segoe UI", 10)).pack(side=tk.LEFT)
        
        self.move_btn = ttk.Button(move_frame, text="开始移动", command=self._move_to_position,
                                   style="Accent.TButton")
        self.move_btn.pack(fill=tk.X, padx=10, pady=(0, 8))
        
        move_result_frame = tk.Frame(move_frame, bg=colors["border"], relief="flat", height=40)
        move_result_frame.pack(fill=tk.X, padx=10)
        move_result_frame.pack_propagate(False)
        self.move_result_label = tk.Label(move_result_frame, textvariable=self.move_result, 
                                           font=("Segoe UI", 10, "bold"), bg=colors["border"], 
                                           fg=colors["text"], justify=tk.CENTER, anchor=tk.CENTER)
        self.move_result_label.pack(fill=tk.BOTH, padx=2, pady=2)

        # ---------- 推杆状态实时显示 ----------
        status_frame = ttk.LabelFrame(main_frame, text="推杆状态", padding="10")
        status_frame.pack(fill=tk.X)
        
        status_alert_row = ttk.Frame(status_frame)
        status_alert_row.pack(fill=tk.X, pady=(0, 8))
        self._add_alert_status(status_alert_row, "状态", "status", colors)
        self._add_alert_status(status_alert_row, "故障码", "errorcode", colors)

        row_status1 = ttk.Frame(status_frame)
        row_status1.pack(fill=tk.X, pady=3)
        self._add_status_row(row_status1, [("速度", "velocity", "mm/s"), ("力矩", "torque", "N")], colors)
        
        row_status2 = ttk.Frame(status_frame)
        row_status2.pack(fill=tk.X, pady=3)
        self._add_status_row(row_status2, [("Ia", "ia", "A"), ("Ib", "ib", "A"), ("Ic", "ic", "A"), ("母线电压", "udc", "V"), ("母线电流", "idc", "A")], colors)
        
        row_status3 = ttk.Frame(status_frame)
        row_status3.pack(fill=tk.X, pady=3)
        self._add_status_row(row_status3, [("Id", "id", "A"), ("Iq", "iq", "A"), ("Id_Ref", "id_ref", "A"), ("Iq_Ref", "iq_ref", "A"), ("Torq_Ref", "torq_ref", "N")], colors)
        
        row_status4 = ttk.Frame(status_frame)
        row_status4.pack(fill=tk.X, pady=3)
        tk.Label(row_status4, text="MOS温度:", font=("Segoe UI", 10), background=colors["frame_bg"]).pack(side=tk.LEFT, padx=(0, 5))
        tk.Label(row_status4, textvariable=self.status_vars["mos_temp"], font=("Segoe UI", 10, "bold"), foreground=colors["danger"], background=colors["frame_bg"]).pack(side=tk.LEFT, padx=(0, 2))
        tk.Label(row_status4, text="℃", font=("Segoe UI", 10), background=colors["frame_bg"]).pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(row_status4, text="电机温度:", font=("Segoe UI", 10), background=colors["frame_bg"]).pack(side=tk.LEFT, padx=(0, 5))
        tk.Label(row_status4, textvariable=self.status_vars["motor_temp"], font=("Segoe UI", 10, "bold"), foreground=colors["danger"], background=colors["frame_bg"]).pack(side=tk.LEFT, padx=(0, 2))
        tk.Label(row_status4, text="℃", font=("Segoe UI", 10), background=colors["frame_bg"]).pack(side=tk.LEFT)
        
        self.status_label = tk.Label(main_frame, text="就绪", font=("Segoe UI", 9), 
                                      fg=colors["subtext"], anchor=tk.W, bg=colors["bg"])
        self.status_label.pack(fill=tk.X, pady=(8, 0))

    def _add_alert_status(self, parent, label_text, var_key, colors):
        item_frame = tk.Frame(parent, bg=colors["frame_bg"])
        item_frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 20))
        tk.Label(item_frame, text=f"{label_text}:", font=("Segoe UI", 16, "bold"),
                 fg=colors["danger"], bg=colors["frame_bg"]).pack(side=tk.LEFT, padx=(0, 8))
        tk.Label(item_frame, textvariable=self.status_vars[var_key], font=("Segoe UI", 18, "bold"),
                 fg=colors["danger"], bg=colors["frame_bg"]).pack(side=tk.LEFT)
    
    def _add_status_row(self, parent, items, colors):
        for item in items:
            if len(item) == 2:
                label_text, var_key = item
                unit = ""
            else:
                label_text, var_key, unit = item
            
            tk.Label(parent, text=f"{label_text}:", font=("Segoe UI", 10), background=colors["frame_bg"]).pack(side=tk.LEFT, padx=(0, 3))
            tk.Label(parent, textvariable=self.status_vars[var_key], font=("Segoe UI", 10, "bold"), foreground=colors["primary"], background=colors["frame_bg"]).pack(side=tk.LEFT, padx=(0, 3))
            if unit:
                tk.Label(parent, text=unit, font=("Segoe UI", 10), background=colors["frame_bg"]).pack(side=tk.LEFT, padx=(0, 12))
        
    def _init_can(self):
        """
        初始化或复用 CAN 总线连接。

        PCAN 驱动已知 bug：异常 shutdown 会导致 channel 永久损坏。
        策略：优先复用已有 bus；损坏时丢弃引用不调用 shutdown，由 GC 处理。
        """
        if self.bus is not None:
            try:
                self.bus.send(can.Message(arbitration_id=0x000, data=b'\x00'*8,
                                          is_extended_id=False, is_fd=True))
                self._update_status("CAN初始化成功（复用旧连接）")
                return
            except Exception:
                # 旧bus已坏，不调用shutdown，直接丢弃引用
                self.bus = None

        # 第一次连接，或旧bus彻底损坏，创建新bus
        for attempt in range(3):
            try:
                self.bus = can.Bus()
                time.sleep(0.2)
                self.bus.send(can.Message(arbitration_id=0x000, data=b'\x00'*8,
                                          is_extended_id=False, is_fd=True))
                self._update_status("CAN初始化成功")
                return
            except Exception as e:
                if attempt < 2:
                    time.sleep(0.5)
                else:
                    self.bus = None
                    raise Exception(f"CAN初始化失败: {type(e).__name__}: {e}")

    def _scan_devices(self):
        """连接后扫描 1 秒内总线上的报文，从仲裁 ID 低 4 位识别关节 ID"""
        self._update_status("正在扫描设备...")
        self.detected_ids.clear()
        self._clear_queue()
        start_time = time.time()
        while time.time() - start_time < 1.0:
            msg = self.bus.recv(0.05)
            if msg:
                aid = msg.arbitration_id
                # 任意ID=0xABx的报文，低4位为关节ID则视为该关节存在
                joint_id = aid & 0x000F
                if 1 <= joint_id <= 10:
                    self.detected_ids.add(joint_id)
        if self.detected_ids:
            self._update_id_combo()
            self._update_status(f"已检测到关节: {sorted(self.detected_ids)}")
        else:
            self._update_status("CAN链路正常，未检测到设备（可能设备尚未上电）")

    def _update_id_combo(self):
        # 无论是否有检测到的设备，都更新下拉框（热拔场景：清空已断开的ID）
        values = [str(i) for i in sorted(self.detected_ids)] if self.detected_ids else [str(i) for i in range(1, 11)]
        self.id_combo['values'] = values
        # 不要重置当前选中的ID，只在当前值已不在列表中时才更新
        if self.detected_ids:
            current_id = self.device_id.get()
            if current_id not in self.detected_ids:
                self.device_id.set(sorted(self.detected_ids)[0])

    def _join_watch_thread(self, timeout=2.0):
        """等待watch线程安全退出"""
        self.running = False
        if self._watch_thread and self._watch_thread.is_alive():
            self._watch_thread.join(timeout=timeout)
        self._watch_thread = None

    def _start_position_watch(self):
        """启动后台守护线程：热插拔检测、断连判定、周期性读取位置与状态"""
        def watch_loop():
            prev_detected = set()
            while self.running:
                if self.bus is None:
                    time.sleep(0.5)
                    continue
                # 热插拔检测：扫描所有可能的关节ID
                try:
                    self._clear_queue()
                    newly_detected = set()
                    for jid in range(1, 11):
                        self._send_message(0x600, '2B03180520000000')
                        time.sleep(0.05)
                        msg = self.bus.recv(0.02)
                        if msg:
                            aid = msg.arbitration_id
                            joint_id = aid & 0x000F
                            if 1 <= joint_id <= 10:
                                newly_detected.add(joint_id)
                except Exception:
                    pass  # 总线异常时跳过本次检测
                if newly_detected or newly_detected != self.detected_ids:
                    # 检测断开：之前有现在没有的ID（要在替换前计算）
                    removed_ids = self.detected_ids - newly_detected
                    # 直接替换，热拔的设备不再响应自然会被移除
                    self.detected_ids = newly_detected
                    self.last_msg_time = time.time()
                    # 连接从断开恢复到正常，更新按钮状态
                    if self.disconnected_reported:
                        self.disconnected_reported = False
                        self.root.after(0, lambda: self._set_connect_btn(tk.NORMAL, "连接成功", "#4CAF50"))
                        self.root.after(0, lambda: self._update_status(f"CAN链路恢复，已检测到关节: {sorted(self.detected_ids)}"))

                # 超过3秒没收到任何CAN消息，认为CAN链路断开
                if time.time() - self.last_msg_time > 3.0 and not self.disconnected_reported and self.connected:
                    self.disconnected_reported = True
                    self.root.after(0, lambda: self._set_connect_btn(tk.NORMAL, "连接断开", "#F44336"))
                    self.root.after(0, lambda: self._update_status("CAN连接已断开，请检查物理链路"))

                removed_ids = prev_detected - self.detected_ids
                if newly_detected or removed_ids:
                    self.root.after(0, self._update_id_combo)
                    if removed_ids:
                        self.root.after(0, lambda r=removed_ids: self._update_status(f"设备断开: {sorted(r)}"))
                prev_detected = self.detected_ids.copy()

                if not self.is_calibrating:
                    try:
                        device_id = self.device_id.get()
                        self._clear_queue()
                        positions = []
                        for _ in range(3):
                            self._send_message(0x600, '2B03180520000000')
                            time.sleep(0.1)
                            msg = self._receive_message(0.3, [0x480 + device_id])
                            if msg:
                                aid = msg.arbitration_id
                                joint_id = aid & 0x000F
                                if 1 <= joint_id <= 10:
                                    self.detected_ids.add(joint_id)
                                if len(msg.data) >= 4:
                                    pos = int.from_bytes(msg.data[2:4], byteorder='little', signed=True)
                                    if -200000 <= pos <= 200000:
                                        positions.append(pos)
                        if positions:
                            avg_pos = int(np.mean(positions))
                            self.current_position.set(f"{avg_pos/100:.2f}")
                        else:
                            self.current_position.set("--")

                        self._update_status_display(device_id)
                    except Exception as e:
                        self.current_position.set("--")
                time.sleep(1.0)

        self._watch_thread = threading.Thread(target=watch_loop, daemon=True)
        self._watch_thread.start()
    
    def _update_status_display(self, device_id):
        """
        解析 0x480+device_id 的 32 字节状态反馈报文，更新 status_vars。

        字段布局（字节偏移）：
          [0:2] status  [2:4] position  [4:6] velocity  [6:8] torque
          [8:10] error  [10:13] Ia,Ib,Ic  [13:14] udc  [14:16] idc
          [16:24] Id,Iq,Id_ref,Iq_ref  [26:28] torq_ref
          [28:30] mos_temp, motor_temp
        """
        try:
            self._clear_queue()
            self._send_message(0x600, '2B03180520000000')
            time.sleep(0.05)
            msg = self._receive_message(0.3, [0x480 + device_id])
            if msg and len(msg.data) >= 32:
                data = msg.data
                
                status_val = int.from_bytes(data[0:2], byteorder='little', signed=False)
                self.status_vars["status"].set(f"0x{status_val:04X}")
                
                pos_val = int.from_bytes(data[2:4], byteorder='little', signed=True)
                self.status_vars["position"].set(f"{pos_val * 0.00001:.5f}")
                
                vel_val = int.from_bytes(data[4:6], byteorder='little', signed=True)
                self.status_vars["velocity"].set(f"{vel_val * 0.1:.2f}")
                
                torq_val = int.from_bytes(data[6:8], byteorder='little', signed=True)
                self.status_vars["torque"].set(f"{torq_val}")
                
                error_val = int.from_bytes(data[8:10], byteorder='little', signed=False)
                self.status_vars["errorcode"].set(f"0x{error_val:04X}")
                
                ia_val = int.from_bytes(data[10:11], byteorder='little', signed=True)
                self.status_vars["ia"].set(f"{ia_val}")
                
                ib_val = int.from_bytes(data[11:12], byteorder='little', signed=True)
                self.status_vars["ib"].set(f"{ib_val}")
                
                ic_val = int.from_bytes(data[12:13], byteorder='little', signed=True)
                self.status_vars["ic"].set(f"{ic_val}")
                
                udc_val = int.from_bytes(data[13:14], byteorder='little', signed=True)
                self.status_vars["udc"].set(f"{udc_val}")
                
                idc_val = int.from_bytes(data[14:16], byteorder='little', signed=True)
                self.status_vars["idc"].set(f"{idc_val * 0.01:.2f}")
                
                id_val = int.from_bytes(data[16:18], byteorder='little', signed=True)
                self.status_vars["id"].set(f"{id_val * 0.01:.2f}")
                
                iq_val = int.from_bytes(data[18:20], byteorder='little', signed=True)
                self.status_vars["iq"].set(f"{iq_val * 0.01:.2f}")
                
                id_ref_val = int.from_bytes(data[20:22], byteorder='little', signed=True)
                self.status_vars["id_ref"].set(f"{id_ref_val * 0.01:.2f}")
                
                iq_ref_val = int.from_bytes(data[22:24], byteorder='little', signed=True)
                self.status_vars["iq_ref"].set(f"{iq_ref_val * 0.01:.2f}")
                
                torq_ref_val = int.from_bytes(data[26:28], byteorder='little', signed=True)
                self.status_vars["torq_ref"].set(f"{torq_ref_val}")
                
                mos_temp_val = int.from_bytes(data[28:29], byteorder='little', signed=True)
                self.status_vars["mos_temp"].set(f"{mos_temp_val}")
                
                motor_temp_val = int.from_bytes(data[29:30], byteorder='little', signed=True)
                self.status_vars["motor_temp"].set(f"{motor_temp_val}")
        except Exception:
            pass
    
    def _update_status(self, msg):
        self.status_label.config(text=msg)
        self.root.update_idletasks()

    def _set_connect_btn(self, state, text, bg):
        self.connect_btn.config(state=state, text=text, bg=bg, activebackground=bg)

    def _toggle_connection(self):
        """连接/断开 CAN：在后台线程执行，避免阻塞 GUI"""
        if not self.connected:
            # 连接
            self._set_connect_btn(tk.DISABLED, "连接中...", "#9E9E9E")
            self.root.update_idletasks()

            def do_connect():
                try:
                    self._init_can()
                    self.last_msg_time = time.time()
                    self.disconnected_reported = False
                    self.running = True  # 每次连接都确保running=True
                    self._scan_devices()
                    self._start_position_watch()
                    self.connected = True
                    self.root.after(0, lambda: self._set_connect_btn(tk.NORMAL, "连接成功", "#4CAF50"))
                    if self.detected_ids:
                        self.root.after(0, lambda: self._update_status(f"已连接，已检测到关节: {sorted(self.detected_ids)}"))
                    else:
                        self.root.after(0, lambda: self._update_status("已连接，CAN链路正常，等待设备上线..."))
                except Exception as e:
                    self.root.after(0, lambda: self._set_connect_btn(tk.NORMAL, "连接失败", "#F44336"))
                    self.root.after(0, lambda: self._update_status(f"连接失败: {e}"))
                    # 2秒后恢复默认
                    time.sleep(2)
                    self.root.after(0, lambda: self._set_connect_btn(tk.NORMAL, "连  接", "#9E9E9E"))

            threading.Thread(target=do_connect, daemon=True).start()
        else:
            # 断开连接
            self._set_connect_btn(tk.DISABLED, "断开中...", "#9E9E9E")
            self.root.update_idletasks()

            def do_disconnect():
                # 先停止watch线程，等其退出
                self._join_watch_thread(timeout=2.0)
                self.connected = False

                # 尝试发送停止指令，然后直接丢弃bus引用（不调用shutdown，避免PCAN驱动bug）
                if self.bus:
                    try:
                        self._send_message(0x200, '00000000000400')
                    except:
                        pass
                # 保持self.bus引用不变，让GC或下次连接时复用
                # 注意：PCAN驱动shutdown有bug，多次shutdown会导致channel永久损坏

                self.running = True
                self.root.after(0, lambda: self._set_connect_btn(tk.NORMAL, "连  接", "#9E9E9E"))
                self.root.after(0, lambda: self._update_status("已断开连接"))

            threading.Thread(target=do_disconnect, daemon=True).start()

    def _move_to_position(self):
        """
        闭环移动到目标位置（mm）。

        流程：校验行程 → 使能 → 发位置指令(3s) → 轮询反馈
        容差：|diff| < 5（即 0.05mm）视为到达；最多 15 轮重试
        """
        if self.is_calibrating:
            return
        
        try:
            target_mm = float(self.move_target_entry.get())
            model = self.selected_model.get()
            max_stroke = self.model_stroke.get(model, 90.0)
            if target_mm < 0 or target_mm > max_stroke:
                messagebox.showwarning("输入错误", f"指令超行程拒绝执行\n{model}行程范围: 0~{max_stroke}mm")
                return
        except ValueError:
            messagebox.showwarning("输入错误", "请输入有效的目标位置数值")
            return
        
        self.is_calibrating = True
        self.calib_btn.config(state=tk.DISABLED)
        self.move_btn.config(state=tk.DISABLED)
        self.move_result.set("")
        self.move_result_label.config(fg="black")
        
        def do_move():
            try:
                device_id = self.device_id.get()
                target_position = int(target_mm * 100)  # mm 转 0.01mm 整数
                arbi_id = 0x200 + device_id

                self._update_status("正在移动推杆...")

                # 使能：控制字 0x0700
                self.bus.send(can.Message(arbitration_id=arbi_id, data=bytes.fromhex('00000000000700'),
                                         is_extended_id=False, is_fd=True))
                time.sleep(0.3)

                # 位置模式 0x01 + 目标(2B小端) + 时长3000ms + 尾 0F00
                position_bytes = int(target_position).to_bytes(2, byteorder='little', signed=True).hex()
                dur_bytes = int(3000).to_bytes(2, byteorder='little', signed=True).hex()
                move_data = '01' + position_bytes + dur_bytes + '0F00'
                
                self.bus.send(can.Message(arbitration_id=arbi_id, data=bytes.fromhex(move_data), 
                                         is_extended_id=False, is_fd=True))
                
                time.sleep(2.0)
                
                for _ in range(15):
                    positions = []
                    self._clear_queue()
                    for _ in range(5):
                        self._send_message(0x600, '2B03180520000000')
                        time.sleep(0.08)
                        msg = self._receive_message(0.3, [0x480 + device_id])
                        if msg and len(msg.data) >= 4:
                            pos = int.from_bytes(msg.data[2:4], byteorder='little', signed=True)
                            if -200000 <= pos <= 200000:
                                positions.append(pos)
                    
                    if positions:
                        avg_pos = int(np.mean(positions))
                        diff = avg_pos - target_position
                        self._update_status(f"当前位置={avg_pos/100:.2f}mm, 目标={target_mm:.2f}mm, 差={diff/100:.2f}mm")
                        
                        if abs(diff) < 5:  # 5 个 0.01mm = 0.05mm 容差
                            self.bus.send(can.Message(arbitration_id=arbi_id, data=bytes.fromhex('00000000000400'),
                                                     is_extended_id=False, is_fd=True))
                            self.move_result.set(f"已到达 {target_mm:.2f}mm")
                            self.move_result_label.config(fg="green")
                            self._update_status("移动完成")
                            return
                        
                        if abs(diff) >= 5:
                            new_target = target_position
                            position_bytes = int(new_target).to_bytes(2, byteorder='little', signed=True).hex()
                            dur_bytes = int(1000).to_bytes(2, byteorder='little', signed=True).hex()
                            move_data = '01' + position_bytes + dur_bytes + '0F00'
                            self.bus.send(can.Message(arbitration_id=arbi_id, data=bytes.fromhex(move_data), 
                                                     is_extended_id=False, is_fd=True))
                            time.sleep(0.8)
                    
                    time.sleep(0.2)
                
                self.bus.send(can.Message(arbitration_id=arbi_id, data=bytes.fromhex('00000000000400'), 
                                         is_extended_id=False, is_fd=True))
                
                positions_final = []
                self._clear_queue()
                for _ in range(3):
                    self._send_message(0x600, '2B03180520000000')
                    time.sleep(0.1)
                    msg = self._receive_message(0.3, [0x480 + device_id])
                    if msg and len(msg.data) >= 4:
                        pos = int.from_bytes(msg.data[2:4], byteorder='little', signed=True)
                        if -200000 <= pos <= 200000:
                            positions_final.append(pos)
                
                if positions_final:
                    final_pos = int(np.mean(positions_final))
                    self.move_result.set(f"最终位置 {final_pos/100:.2f}mm")
                else:
                    self.move_result.set("移动完成")
                self.move_result_label.config(fg="orange")
                self._update_status("移动完成（未完全到达目标）")
                
            except Exception as e:
                self.move_result.set("移动失败")
                self.move_result_label.config(fg="red")
                self._update_status(f"移动异常: {e}")
            finally:
                self.is_calibrating = False
                self.calib_btn.config(state=tk.NORMAL)
                self.move_btn.config(state=tk.NORMAL)
        
        threading.Thread(target=do_move, daemon=True).start()
    
    def _start_calibration(self):
        """校验输入后在后台线程执行 _calibration_process"""
        if self.is_calibrating:
            return
        
        try:
            target_mm = float(self.calib_target_entry.get())
            model = self.selected_model.get()
            max_stroke = self.model_stroke.get(model, 90.0)
            if target_mm < 0 or target_mm > max_stroke:
                messagebox.showwarning("输入错误", f"指令超行程拒绝执行\n{model}行程范围: 0~{max_stroke}mm")
                return
        except ValueError:
            messagebox.showwarning("输入错误", "请输入有效的目标位置数值")
            return
        
        self.is_calibrating = True
        self.calib_btn.config(state=tk.DISABLED)
        self.move_btn.config(state=tk.DISABLED)
        self.calib_result.set("")
        self.calib_result_label.config(fg="black")
        
        def do_calib():
            try:
                device_id = self.device_id.get()
                target_position = int(target_mm * 100)
                
                self._update_status("开始校准...")
                success = self._calibration_process(device_id, target_position)
                
                if success:
                    result_text = f"ID={device_id} 校准成功 {target_mm:.2f}mm"
                    self.calib_result.set(result_text)
                    self.calib_result_label.config(fg="green")
                    self._update_status("校准成功！")
                else:
                    result_text = f"ID={device_id} 校准失败"
                    self.calib_result.set(result_text)
                    self.calib_result_label.config(fg="red")
                    self._update_status("校准失败，请重试")
                    
            except Exception as e:
                result_text = f"ID={device_id} 校准失败"
                self.calib_result.set(result_text)
                self.calib_result_label.config(fg="red")
                self._update_status(f"校准异常: {e}")
            finally:
                self.is_calibrating = False
                self.calib_btn.config(state=tk.NORMAL)
                self.move_btn.config(state=tk.NORMAL)
        
        threading.Thread(target=do_calib, daemon=True).start()
    
    def _calibration_process(self, device_id, target_position):
        """
        六步位置校准核心逻辑（与 calib_v3 类似，增强采样与验证）。

        target_position 单位：0.01mm
        成功条件：写 offset 后反馈与目标差值 < 5（0.05mm）
        """
        self._update_status("[1/6] 使能设备...")
        self._send_message(0x200, '00000000000700')
        time.sleep(0.2)
        
        self._update_status("[2/6] 清空缓存...")
        self._clear_queue()
        
        self._update_status("[3/6] 发送offset=0...")
        self._send_message(0x600, '2B01200500000000')  # SDO 写 offset=0
        time.sleep(0.1)

        self._update_status("[4/6] 发送standby...")
        self._send_message(0x600, '2B03180520000000')  # 开启状态上报
        time.sleep(0.3)
        
        self._update_status("[5/6] 采样位置数据...")
        positions = []
        for i in range(10):
            msg = self._receive_message(1, [0x480 + device_id])
            if msg and len(msg.data) >= 4:
                pos = int.from_bytes(msg.data[2:4], byteorder='little', signed=True)
                if -200000 <= pos <= 200000:
                    positions.append(pos)
            time.sleep(0.05)
        
        if len(positions) < 3:
            self._update_status("有效采样不足")
            return False
        
        positions_array = np.array(positions)
        mean_pos = int(np.mean(positions_array))
        std_val = np.std(positions_array)
        
        filtered = positions_array[np.abs(positions_array - mean_pos) <= std_val * 2]
        if len(filtered) < 3:
            mean_pos = int(np.mean(filtered))
        
        self._update_status(f"采样完成，当前位置: {mean_pos/100:.2f}mm")

        # 补偿量 = 目标位置 - 当前反馈均值
        offset_position = target_position - mean_pos
        offset_hex = int(offset_position).to_bytes(2, byteorder='little', signed=True).hex()
        data = '2B012005' + offset_hex + '0000'  # SDO 写 offset
        
        self._update_status("[6/6] 发送校准报文并验证...")
        self._send_message(0x200, '00000000000700')
        time.sleep(0.2)
        
        for retry in range(5):
            self._clear_queue()
            self._send_message(0x600, data)
            time.sleep(0.3)
            
            positions = []
            for _ in range(5):
                self._send_message(0x600, '2B03180520000000')
                time.sleep(0.05)
                msg = self._receive_message(0.5, [0x480 + device_id])
                if msg and len(msg.data) >= 4:
                    pos = int.from_bytes(msg.data[2:4], byteorder='little', signed=True)
                    if -200000 <= pos <= 200000:
                        positions.append(pos)
            
            if positions:
                avg_pos = int(np.mean(positions))
                diff = abs(avg_pos - target_position)
                self._update_status(f"验证: 当前位置={avg_pos/100:.2f}mm, 目标={target_position/100:.2f}mm, 差值={diff/100:.2f}mm")
                if diff < 5:
                    self._update_status(f"校准成功! (差值={diff/100:.2f}mm < 0.05mm)")
                    self._send_message(0x200, '00000000000400')
                    return True
            time.sleep(0.2)
        
        self._send_message(0x200, '00000000000400')
        return False
    
    def _force_zero_calib(self):
        """力传感器标零：SDO 2302200100000000"""
        device_id = self.device_id.get()
        self._update_status(f"[力传感器标零] 正在对ID={device_id}标零...")
        self._clear_queue()
        self._send_message(0x600, '2302200100000000')
        time.sleep(0.3)
        messagebox.showinfo("力传感器标零", f"ID={device_id} 推杆力传感器已经校准为0")
        self._update_status(f"[力传感器标零] ID={device_id} 标零完成")

    def _write_new_id(self):
        """将当前关节 ID 修改为 new_id（1~10），需下电重启生效"""
        current_id = self.device_id.get()
        new_id = self.new_id_var.get()
        if current_id == new_id:
            messagebox.showwarning("输入错误", "新ID不能与当前ID相同")
            return
        if new_id < 1 or new_id > 10:
            messagebox.showwarning("输入错误", "新ID需在1~10范围内")
            return
        result = messagebox.askyesno("确认写入ID", f"确定要将ID={current_id}的推杆改为ID={new_id}吗？")
        if not result:
            return
        self._update_status(f"[写入ID] 正在将ID={current_id}改为ID={new_id}...")
        self._clear_queue()
        new_id_hex = f"{new_id:02X}"
        data = '2F012001' + new_id_hex + '000000'  # SDO 写设备 ID
        self._send_message(0x600, data)
        time.sleep(0.3)

        # 等待回复报文，ID=0x58x，x为改之前的ID
        resp_id = 0x580 + current_id
        expected_data = bytes.fromhex('60012001')
        msg = self._receive_message(1.0, [resp_id])
        if msg and msg.data[:4] == expected_data:
            messagebox.showinfo("写入ID成功", f"推杆ID已成功改为{new_id}，请下电重启设备")
            self._update_status(f"[写入ID] 成功: ID={current_id}→{new_id}")
        else:
            messagebox.showerror("写入ID失败", "更改ID失败，请重试")
            self._update_status(f"[写入ID] 失败: ID={current_id}→{new_id}")

    def _send_message(self, control, data):
        """发送 CAN 报文，仲裁 ID = control + 当前 device_id"""
        message = can.Message(
            arbitration_id=control + self.device_id.get(), 
            data=bytes.fromhex(data), 
            is_extended_id=False, 
            is_fd=True
        )
        try:
            self.bus.send(message)
        except can.CanError:
            pass
    
    def _receive_message(self, timeout, abritration_id_list):
        """在 timeout 秒内等待指定仲裁 ID 列表中的任一报文"""
        if isinstance(abritration_id_list, int):
            abritration_id_list = [abritration_id_list]

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                message = self.bus.recv(0.5)
            except Exception:
                return None
            if message and message.arbitration_id in abritration_id_list:
                return message
        return None

    def _clear_queue(self):
        """非阻塞清空接收队列，避免旧报文干扰"""
        try:
            while self.bus.recv(0.001) is not None:
                pass
        except Exception:
            pass
    
    def on_closing(self):
        """窗口关闭：停止 watch 线程 → 失能 → shutdown CAN → 销毁窗口"""
        self._join_watch_thread(timeout=2.0)
        self.connected = False
        if self.bus:
            try:
                self._send_message(0x200, '00000000000400')
            except:
                pass
            try:
                self.bus.shutdown()
            except:
                pass
            self.bus = None
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CalibrationApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)  # 捕获关闭按钮，安全退出
    root.mainloop()
