#这段“精简版”代码我验证过了，可以用
import can,time

print("输入ID：1~7整数")
device_id = int(input())
arbi_id = device_id + 0x200

try:
        bus = can.Bus()
except can.CanError as e:
    print("Error setting up CAN bus:", e)
    exit()

def is_enable(sign=0):
    if sign == 1:
        bus.send(can.Message(arbitration_id=arbi_id,data=bytes.fromhex('00000000000700'), is_extended_id=False, is_fd=True))
    else:
        bus.send(can.Message(arbitration_id=arbi_id,data=bytes.fromhex('00000000000400'), is_extended_id=False, is_fd=True))


if __name__ =="__main__":
    is_enable(1)
    print("你想让推杆伸出多长/0.01mm?")
    position=int(input())  #改这个值就可以改变推杆伸出长度
    position=int(position).to_bytes(2,byteorder='little',signed=True).hex()  #推杆长度，单位0.01mm
    dur = int(2000).to_bytes(2,byteorder='little',signed=True).hex()  #运动时间，单位1ms
    send_msg='01'+position+dur+'0F00'
    bus.send(can.Message(arbitration_id=arbi_id,data=bytes.fromhex(send_msg), is_extended_id=False, is_fd=True))
    time.sleep(1.5)
    is_enable(0)

