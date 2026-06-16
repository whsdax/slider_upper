import can #不可安装公共库否则冲突
import time
import threading
import numpy as np




target_date = {"position": 0, "speed": 0, "thrust": 0, "current": 0}
current_date = {"status": 0,"position": 0, "speed": 0, "thrust": 0, "current": 0}




Statusword6041 = [
"FOC控制频率太高",	
"过压报警",	
"欠压报警",
"电机内部温度过高",
"控制器温度过高	",
"电机堵转报警",
"位置超出限制范围",
"编码器通信异常",
"编码器故障",
"过流报警",
"驱动器通信异常",
"驱动器故障",
"驱动寄存器复位"    
]


is_record = False

try:
        bus = can.Bus()
except can.CanError as e:
    print("Error setting up CAN bus:", e)
    exit()

data_list = {
    'ts': [],
    'm_ts': [],
    'status': [],
    'thrust': [],
    'pos': [],
    'vel': [],
    'current': [],
    'driver_iqd': [],
    'target_thrust': [],
    'combined_target_thrust': [],
    'kp': [],
    'target_pos': [],
    'kd': [],
    'target_vel': [],
    'target_current': [],
    'error': [],
    'data_idx': [],
    'is_active': [],
    'mos_temp1': [],
    'mos_temp2': [],
    'motor_temp1': [],
    'motor_temp2': [],
}

def add_datalist(ms,m_ts,thrust,target_thrust,combined_target_thrust,position,target_position,speed,target_speed,kd,kp):
    data_list['ts'].append(ms)
    data_list['m_ts'].append(m_ts)
    data_list['thrust'].append(thrust)
    data_list['target_thrust'].append(target_thrust)
    data_list['combined_target_thrust'].append(combined_target_thrust)
    data_list['position'].append(position)
    data_list['target_position'].append(target_position)
    data_list['speed'].append(speed)
    data_list['target_speed'].append(target_speed)
    data_list['kd'].append(kd)
    data_list['kp'].append(kp)

def receive_message(bus, timeout, abritration_id_list):
    if isinstance(abritration_id_list,int):
        abritration_id_list = [abritration_id_list]
    abritration_id_list = [x+device_id for x in abritration_id_list]

    # Set a timeout for the listener
    timeout = timeout  # seconds
    start_time = time.time()

    while True:
        if time.time() - start_time > timeout:
            # print("Timeout: No message received within {} seconds".format(timeout))
            return None

        message = bus.recv(1.0)  # Wait for a message for 1 second
        if message == None:
            continue
        if message.arbitration_id in abritration_id_list:
            return message


def ParseData(message):
    (
        status,
        position,
        speed,
        thrust,
        error,
        ia,
        ib,
        ic,
        driver_board_vol_in,
        driver_board_current_in,
        id,
        iq,
        idd,
        iqd,
        iphase_limit,
        torque_ref,
        mos_temp1,
        mos_temp2,
        mos_temp3,
        motor_temp1,
        motor_temp2,
        index,
    ) = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    # print(message)

    if len(message.data) == 48:
        status = message.data[0:2].hex()
        position = int.from_bytes(message.data[2:4], byteorder='little', signed=True)
        speed = int.from_bytes(message.data[4:6], byteorder='little', signed=True)
        thrust = int.from_bytes(message.data[6:8], byteorder='little', signed=True)
        error = int.from_bytes(message.data[8:10], byteorder='little', signed=False)
        ia = int.from_bytes(message.data[10:12], byteorder='little', signed=True)
        ib = int.from_bytes(message.data[12:14], byteorder='little', signed=True)
        ic = int.from_bytes(message.data[14:16], byteorder='little', signed=True)
        driver_board_vol_in = int.from_bytes(message.data[16:18], byteorder='little', signed=True)
        driver_board_current_in = int.from_bytes(message.data[18:20], byteorder='little', signed=True)
        id = int.from_bytes(message.data[20:22], byteorder='little', signed=True)
        iq = int.from_bytes(message.data[22:24], byteorder='little', signed=True)
        idd = int.from_bytes(message.data[24:26], byteorder='little', signed=True)
        iqd = int.from_bytes(message.data[26:28], byteorder='little', signed=True)
        iphase_limit = int.from_bytes(message.data[28:30], byteorder='little', signed=False)
        torque_ref = int.from_bytes(message.data[30:32], byteorder='little', signed=True)
        mos_temp1 = int.from_bytes(message.data[32:33], byteorder='little', signed=True)
        mos_temp2 = int.from_bytes(message.data[33:34], byteorder='little', signed=True)
        mos_temp3 = int.from_bytes(message.data[34:35], byteorder='little', signed=True)
        motor_temp1 = int.from_bytes(message.data[35:36], byteorder='little', signed=True)
        motor_temp2 = int.from_bytes(message.data[36:37], byteorder='little', signed=True)
        index = int.from_bytes(message.data[37:39], byteorder='little', signed=False)
    elif len(message.data) == 32:
        status = message.data[0:2].hex()
        position = int.from_bytes(message.data[2:4], byteorder='little', signed=True)
        speed = int.from_bytes(message.data[4:6], byteorder='little', signed=True)
        thrust = int.from_bytes(message.data[6:8], byteorder='little', signed=True)
        error = int.from_bytes(message.data[8:10], byteorder='little', signed=False)
        ia = int.from_bytes(message.data[10:11], byteorder='little', signed=True)
        ib = int.from_bytes(message.data[11:12], byteorder='little', signed=True)
        ic = int.from_bytes(message.data[12:13], byteorder='little', signed=True)
        udc = int.from_bytes(message.data[13:14], byteorder='little', signed=True)
        idc = int.from_bytes(message.data[14:16], byteorder='little', signed=True)
        id = int.from_bytes(message.data[16:18], byteorder='little', signed=True)
        iq = int.from_bytes(message.data[18:20], byteorder='little', signed=True)
        IdRef = int.from_bytes(message.data[20:22], byteorder='little', signed=True)
        IqRef = int.from_bytes(message.data[22:24], byteorder='little', signed=True)
        motorIsLimit = int.from_bytes(message.data[24:26], byteorder='little', signed=False)
        TorqRef = int.from_bytes(message.data[26:28], byteorder='little', signed=False)
        mos_temp1 = int.from_bytes(message.data[28:29], byteorder='little', signed=True) 
        motor_temp1 = int.from_bytes(message.data[29:30], byteorder='little', signed=True)   
    else:
        print('The byte length is incorrect!')

    return (
        status,
        position,
        speed,
        thrust,
        error,
        ia,
        ib,
        ic,
        driver_board_vol_in,
        driver_board_current_in,
        id,
        iq,
        idd,
        iqd,
        iphase_limit,
        torque_ref,
        mos_temp1,
        mos_temp2,
        mos_temp3,
        motor_temp1,
        motor_temp2,
        index,
    )




def receive_data():#接受信息并将信息更新到plotjunjjer
    global is_record

    while True:
        msg = receive_message(bus, 2, [0x180,0x280,0x480,0x580])
        if msg == None:
            continue
        if msg.arbitration_id == 0x480 + device_id:
            ##position, speed, thrust, current, ia, ib, iangle, id = parseStatus(msg)
            
            (
            status,
            position,
            speed,
            thrust,
            error,
            ia,
            ib,
            ic,
            driver_board_vol_in,
            driver_board_current_in,
            id,
            iq,
            idd,
            iqd,
            iphase_limit,
            torque_ref,
            mos_temp1,
            mos_temp2,
            mos_temp3,
            motor_temp1,
            motor_temp2,
            index,
        ) = ParseData(msg)



        
            
            # current_date["status"] = status
            current_date["position"] = position
            current_date["thrust"] = thrust
            current_date["current"] = iq
            current_date["speed"] = speed
            
            
            # if is_record == True:
            #     add_datalist(current_time,msg.timestamp,thrust,target_thrust,0,position,target_position,speed,target_speed,0,0)
        if msg.arbitration_id == 0x180 + device_id:
            data = msg.data
            status = data[0] | (data[1]<<8)
            current_date["status"] = status
            if status != 0:
                # print(status)
                status_info = []
                sta_binary = bin(status)[2:].zfill(16)###// [2:]去掉0b// zfill返回指定长度的字符串
                status_info.append(f"状态位6041二进制:{sta_binary}")
                sta_binary_reverse = sta_binary[::-1] # 将二进制字符串排序反过来
                for index,bit in enumerate(sta_binary_reverse):
                    if bit == "1":
                        status_info.append(f"bit {index} 位: {Statusword6041[index]}")
                if status_info:
                    for info in status_info:
                        print(info)        
                        # SendMsg(0x200,sendbuff)#################
            # else:
            #     print("status OK")
        if msg.arbitration_id == 0x580 + device_id:

            data = msg.data
            
            if(len(data) > 4):
                dlen = msg.data[0]
                if dlen==0x80 or (dlen!=0x4F and dlen!=0x4B and dlen!=0x47 and dlen!=0x43):
                    print("失败")
                else:
                    rcv_status = hex(data[0])
                    main_index =hex(data[1] | (data[2]<<8))
                    sub_index = data[3]
                    status = data[4] | (data[5]<<8)
                    print(f"接收状态:{rcv_status}主索引:{main_index}子索引:{sub_index} offset值:{status}")
                    
def send_message(bus, control, data):
    # The data is already a byte array
    byte_data = data
    # print(data)

    message = can.Message(
        arbitration_id=control + device_id, data=bytes.fromhex(byte_data), is_extended_id=False, is_fd=True
    )
    # Send the message.
    try:
        bus.send(message)
        # print("Message sent on {}: {}".format(bus.channel_info, data))
    except can.CanError:
        print("Message NOT sent")


##*******************精确时间混合控制*********胡**#
def sleep_exact(startime,duration):
    evertimeslep = 0.01 * duration
    targetduartion = 0.28 * duration + startime
    #已延时 = 需要延时时间 + 开始时间
    while time.perf_counter()  < targetduartion:
        time.sleep(evertimeslep)
    # precise_delay_microseconds(700)
    targetendtime = duration + startime
    # 使用忙等待精确到最后的几微秒
    while time.perf_counter() < targetendtime:
        pass  # 忙等待直到精确时间到达



##*******************开启上报*********胡**#
def is_report(rid=0):
    if rid == 1:
        hz = 1
        send_message(bus, 0x600, "2B031805" + hz.to_bytes(2, byteorder="little", signed=True).hex() + '0000')
    else:
        hz = 0
        send_message(bus, 0x600, "2B031805" + hz.to_bytes(2, byteorder="little", signed=True).hex() + '0000')


##*******************关闭心跳*********胡**#
def heart(rid=0):
    if rid == 1:
        hz = 1
        send_message(bus, 0x600, "2B171000" + hz.to_bytes(2, byteorder="little", signed=True).hex() + '0000')
    else:
        hz = 0
        send_message(bus, 0x600, "2B171000" + hz.to_bytes(2, byteorder="little", signed=True).hex() + '0000')

def is_enable(sign=0):
    if sign == 1:
        send_message(bus, 0x200, '00000000000700')
    else:
        send_message(bus, 0x200, '00000000000400')#下使能

##*******************速度模式*********胡**#
def speedControl(target_speed, moveDuration):
    # target_current:单位A；  F5000,canfd协议单位是0.01A；F500,canfd协议单位是0.001A
    target_speed = int(target_speed)
    target_date["speed"] = target_speed
    target_speed = target_speed.to_bytes(2, byteorder="little", signed=True).hex()
    moveDuration = int(moveDuration)
    moveDuration = moveDuration.to_bytes(2, byteorder="little", signed=True).hex()
    data = '03' + target_speed + moveDuration + '0F00'
    send_message(bus, 0x200, data)

##*******************位置模式*********胡**#
def positionControl(target_position, moveDuration):
    target_position = int(target_position)
    target_date["position"] = target_position
    target_position = target_position.to_bytes(2, byteorder="little", signed=True).hex()
    moveDuration = int(moveDuration)
    moveDuration = moveDuration.to_bytes(2, byteorder="little", signed=True).hex()
    data = '01' + target_position + moveDuration + '0F00'
    send_message(bus, 0x200, data)
    
##*******************电流模式*********胡**#
def currentControl(target_current, moveDuration):
    # target_current:单位A；  F5000,canfd协议单位是0.01A；F500,canfd协议单位是0.001A
    target_current = int(target_current)
    target_date["current"] = target_current
    target_current = target_current.to_bytes(2, byteorder="little", signed=True).hex()
    moveDuration = int(moveDuration)
    moveDuration = moveDuration.to_bytes(2, byteorder="little", signed=True).hex()
    data = '04' + target_current + moveDuration + '0F00'
    send_message(bus, 0x200, data)
##*******************六步换相********胡**#
def fc(target_current, moveDuration):
    # target_current:单位A；  F5000,canfd协议单位是0.01A；F500,canfd协议单位是0.001A
    target_current = int(target_current)
    target_date["current"] = target_current
    target_current = target_current.to_bytes(2, byteorder="little", signed=True).hex()
    moveDuration = int(moveDuration)
    moveDuration = moveDuration.to_bytes(2, byteorder="little", signed=True).hex()
    data = '06' + target_current + moveDuration + '0F00'
    send_message(bus, 0x200, data)
        

def cosPositionControl(start_position, end_position, hz=1, nums=3):
    amplitude = (end_position - start_position) / 2 # 正弦的振幅
    # print("amplitude",amplitude)
    vertical_shift = start_position + amplitude     # 波谷加二分之模长=中间值
    num_points = int(1000 / hz)
    # print(num_points,"num_point")
    start = 1/num_points
    x = np.linspace(start, 1, num_points)
    # print(x, "x 的值")  # 打印 x 的值
    y = amplitude * np.cos(2 * np.pi * x) + vertical_shift #
    y = np.round(y, 2)

    # 以2S的时间移动到中心点位置
    print(vertical_shift, "垂直位移（中心位置）",hz, "控制频率",
          num_points, "位置点的数量",hz * num_points, "总的时间分割数量")

    positionControl(end_position, 3000)
    time.sleep(5)

    # 以hz的频率正弦运动
    sleep_time = 0.001 #值为常数0.001
    # print(sleep_time)
    delay_times = []

    for i in range(nums):#对应正弦运动的次数
        for i in range(num_points):
            s = time.perf_counter()        
            positionControl(y[i], 0)
            sleep_exact(s,0.001)


        


def test():
    #send_message(bus, 0x200, '00000000000700')
    # send_message(bus, 0x600, '10170010000000')
    heart(0)
    receive_thread = threading.Thread(target=receive_data, daemon=True)
    receive_thread.start()
    
    # temp_thread = threading.Thread(target=send_temp_message, daemon=True)
    # temp_thread.start()

    is_report(1)
    time.sleep(0.5)
    is_report(0)
    

    text = "************************************************** \n \
        以下为控制指令。注：此脚本需要电机上电5s后才可以启动运行  \n \
        p:到达指定位置；\n \
        pcos: 定频cos曲线运动； 此指令需要先使能\n \
        c:到达指定电流；\n \
        s: 到达指定速度\n \
        oy: 上报消息； cr: 停止上报；\n \
        enable : 使能； disable : 失能； q: 退出程序 \n \
*************************************************** \n"
    print(text)


    while True:

        
        print(f"\n/****请输入控制方式:位置:{current_date['position']/ 100} mm "
                f"速度:{current_date['speed']/10} m/s 力:{current_date['thrust']} N"
                f" 电流:{current_date['current']/100} A****/")
        controlmode = input()
        controlmode = controlmode.strip(" ")
        try:
            if controlmode == 'q':
                break
            if controlmode == 'pcos':
                is_report(1)
                print("请输入起始位置(0.01mm)、结束位置(0.01mm)、频率HZ、运行次数:")
                com = input()
                comlist = com.split(" ")
                if len(comlist) == 4:
                    cosPositionControl(float(comlist[0]), float(comlist[1]), float(comlist[2]), int(comlist[3]))
                else:
                    print("pcos控制模式输入格式不正确!") 
###############电流环############电流环###############电流环
            elif controlmode == 'c':
                is_enable(1)
                print("请输入目标电流(0.01A)和时间(0.001s可不填，默认0):")
                com = input()
                comlist = com.split(" ")
                if len(comlist) == 2:
                    currentControl(float(comlist[0]), float(comlist[1]))
                elif len(comlist) == 1:
                    currentControl(float(comlist[0]), 0)
                else:
                    print("c控制模式输入格式不正确!")
                time.sleep(1)
                is_enable(0)
###############速度环############速度环###############速度环
            elif controlmode == 's':

                is_enable(1)
                print("请输入目标速度(0.1 m/s)和时间(0.001s可不填，默认0):")
                com = input()
                comlist = com.split(" ")
                if len(comlist) == 2:
                    speedControl(float(comlist[0]), float(comlist[1]))
                elif len(comlist) == 1:
                    speedControl(float(comlist[0]), 0)
                else:
                    print("c控制模式输入格式不正确!")
                time.sleep(1)
                speedControl(0,0)
                is_enable(0)
###############六步换相############六步换相###############
            elif controlmode == 'fc':
                is_enable(1)
                print("请输入目标PWM(0.01%),占空比和转速(rpm)")
                com = input()
                comlist = com.split(" ")
                if len(comlist) == 2:
                    fc(float(comlist[0]), float(comlist[1]))
                else:
                    print("c控制模式输入格式不正确!")
###############位置环############位置环###############
            elif controlmode == 'p':
                is_enable(1)
                print("请输入目标位置（0.01mm）和运行时长(0.001s可不填，默认1s):")
                com = input()
                comlist = com.split(" ")
                if len(comlist) == 2:
                    positionControl(float(comlist[0]), float(comlist[1]))
                    time.sleep(float(comlist[1])/1000)
                    is_enable(0)
                elif len(comlist) == 1:
                    positionControl(float(comlist[0]), 1000)
                    time.sleep(1.5)
                    is_enable(0)
                else:
                    print("p控制模式输入格式不正确!")

            elif controlmode == 'or':
                is_report(1)
            elif controlmode == 'cr':
                is_report(0)
            elif controlmode == 'enable':
                send_message(bus, 0x200, '00000000000700')
            elif controlmode =='disable':
                send_message(bus, 0x200, '00000000000400')

            elif controlmode == 'help':
                print(text)
            elif controlmode == 'ptp':
                print("输入指令不正确，请重新输入")
            else:
                print("输入指令不正确，请重新输入")
        except Exception as e:
            is_enable(0)
            print(f"发生错误：{e}")
            break
        except KeyboardInterrupt:
            send_message(bus, 0x200, '00000000000400')
            print('[Controller] KeyboardInterrupt!')
            break
    
    
if __name__ == "__main__":
    device_id = 0x1
    
    
    
    test()