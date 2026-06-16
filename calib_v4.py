
import can
import time
import numpy as np

print("请输入关节id：1~6整数")
device_id = int(input())

MAX_RETRIES = 5
SAMPLE_COUNT = 10
VALID_POSITION_RANGE = (-200000, 200000)

try:
    bus = can.Bus()
except can.CanError as e:
    print("Error setting up CAN bus:", e)
    exit()

def send_message(bus, control, data):
    byte_data = data
    message = can.Message(
        arbitration_id=control + device_id, data=bytes.fromhex(byte_data), is_extended_id=False, is_fd=True
    )
    try:
        bus.send(message)
    except can.CanError:
        print("Message NOT sent")

def is_enable(sign=0):
    if sign == 1:
        send_message(bus, 0x200, '00000000000700')
    else:
        send_message(bus, 0x200, '00000000000400')

def receive_message(bus, timeout, abritration_id_list):
    if isinstance(abritration_id_list, int):
        abritration_id_list = [abritration_id_list]
    abritration_id_list = [x + device_id for x in abritration_id_list]

    timeout = timeout
    start_time = time.time()

    while True:
        if time.time() - start_time > timeout:
            return None

        message = bus.recv(0.5)
        if message == None:
            continue
        if message.arbitration_id in abritration_id_list:
            return message

def clear_queue(bus, timeout=0.001):
    while bus.recv(timeout) is not None:
        pass

def read_status(bus):
    clear_queue(bus)
    send_message(bus, 0x600, '2B17100001000000')
    time.sleep(0.05)
    msg = receive_message(bus, 1, [0x180])
    if msg and len(msg.data) >= 2:
        status = int.from_bytes(msg.data[0:2], byteorder='little', signed=False)
        return status
    return None

def read_position_with_validation(bus, sample_count=SAMPLE_COUNT):
    positions = []
    clear_queue(bus)
    time.sleep(0.05)
    
    for i in range(sample_count):
        msg = receive_message(bus, 1, [0x480])
        if msg and len(msg.data) >= 4:
            pos = int.from_bytes(msg.data[2:4], byteorder='little', signed=True)
            if VALID_POSITION_RANGE[0] <= pos <= VALID_POSITION_RANGE[1]:
                positions.append(pos)
        time.sleep(0.02)
    
    if len(positions) < 3:
        return None, f"有效采样不足，仅获取{len(positions)}个有效位置"
    
    positions_array = np.array(positions)
    mean_pos = int(np.mean(positions_array))
    std_val = np.std(positions_array)
    
    filtered = positions_array[np.abs(positions_array - mean_pos) <= std_val * 2]
    if len(filtered) < 3:
        return None, f"数据离散度太大，std={std_val:.2f}"
    
    final_pos = int(np.mean(filtered))
    return final_pos, f"采样{len(positions)}次,std={std_val:.2f},最终取{len(filtered)}次平均={final_pos}"

def wait_for_status_clear(bus, timeout=3.0):
    start = time.time()
    while time.time() - start < timeout:
        status = read_status(bus)
        if status is not None and status == 0:
            return True
        time.sleep(0.1)
    return False

def calib_v4():
    print(f"\n========== 推杆位置校准 V4 (device_id={device_id}) ==========")
    
    is_enable(1)
    print("[1/6] 设备使能成功")
    time.sleep(0.2)
    
    clear_queue(bus)
    print("[2/6] CAN缓存已清零")
    
    print("[3/6] 发送offset=0的报文...")
    send_message(bus, 0x600, '2B01200500000000')
    time.sleep(0.1)
    
    print("[4/6] 发送standby报文...")
    send_message(bus, 0x600, '2B03180520000000')
    time.sleep(0.3)
    
    status = read_status(bus)
    if status is None:
        raise TimeoutError("无法读取设备状态，请检查连接")
    print(f"     设备状态字: 0x{status:04X}")
    if status != 0:
        print(f"     警告: 设备状态异常 (0x{status:04X}), 正在等待清除...")
        if not wait_for_status_clear(bus):
            raise RuntimeError(f"设备状态无法清除，当前状态: 0x{status:04X}")
        print("     状态已清除")
    
    print("[5/6] 多次采样获取位置数据...")
    position, msg = read_position_with_validation(bus, SAMPLE_COUNT)
    if position is None:
        raise TimeoutError(f"位置读取失败: {msg}")
    print(f"     {msg}")
    
    print("[6/6] 请输入推杆的实际推出长度/0.01mm（如推出12.34mm，则输入1234）：")
    real_position = int(input())
    
    offset_position = real_position - position
    print(f"     当前位置反馈: {position}, 实际位置: {real_position}")
    print(f"     补偿offset: {offset_position}")
    
    offset_hex = int(offset_position).to_bytes(2, byteorder='little', signed=True).hex()
    data = '2B012005' + offset_hex + '0000'
    
    for retry in range(MAX_RETRIES):
        print(f"\n--- 发送校准报文 (第{retry+1}次/{MAX_RETRIES}) ---")
        clear_queue(bus)
        send_message(bus, 0x600, data)
        time.sleep(0.1)
        
        confirm_msg = receive_message(bus, 2, [0x580])
        if confirm_msg and len(confirm_msg.data) >= 6:
            dlen = confirm_msg.data[0]
            if dlen == 0x4F or dlen == 0x4B:
                status_code = int.from_bytes(confirm_msg.data[4:6], byteorder='little', signed=False)
                if status_code == 0:
                    print(f"     设备确认: 校准成功 (status=0x{status_code:04X})")
                    is_enable(0)
                    print("\n========== 校准完成 ==========")
                    return True
                else:
                    print(f"     设备确认: 状态码=0x{status_code:04X}, 等待重试...")
            else:
                print(f"     收到异常响应: dlen=0x{dlen:02X}, 等待重试...")
        else:
            print(f"     未收到有效确认报文, 等待重试...")
        
        time.sleep(0.5)
        
        if retry < MAX_RETRIES - 1:
            print("     重新采样位置数据验证...")
            new_pos, new_msg = read_position_with_validation(bus, 5)
            if new_pos is not None:
                print(f"     当前采样位置: {new_pos} {new_msg}")
    
    raise RuntimeError(f"校准失败，已重试{MAX_RETRIES}次仍无法确认成功")

if __name__ == "__main__":
    try:
        calib_v4()
    except Exception as e:
        print(f"\n校准异常: {e}")
        is_enable(0)
