# slider_upper 项目 —— 实际使用报文完整对照表

> 本文档只收录**代码里真正会被发送/接收到总线上的报文**（逐个 `grep` 全项目 `.py` 文件核对，没有漏掉任何一种）。每一条都给出：**完整仲裁ID怎么算 → data 每个字节是什么 → 在 `KAI执行器通信32字节协议.xlsx` 里对应哪个 sheet/index/subindex → 代码具体在哪一行发的**。
>
> 协议依据：`KAI执行器通信32字节协议.xlsx`（本项目权威协议文档，不是 `KAIBOT 关节SDO对象字典(1).docx`，两者区别见 `CAN-guide.md` 第0章）
> 涉及代码文件：`can.py`、`calib_v3.py`、`calib_v4.py`、`main.py`、`slider_upper.py`、`position_light.py`

---

## 0. 速查总表

| # | 报文名称 | 方向 | 仲裁ID | data（hex） | xlsx对应 | 是否xlsx有文档 |
|---|---|---|---|---|---|---|
| 1 | 使能 | 发→驱动 | `0x200+id` | `00 00 00 00 00 07 00` | 无（自定义控制字，非标准SDO） | ⚠️自定义 |
| 2 | 失能 | 发→驱动 | `0x200+id` | `00 00 00 00 00 04 00` | 无（自定义控制字） | ⚠️自定义 |
| 3 | 位置控制 | 发→驱动 | `0x200+id` | `01`+目标(2B)+时长(2B)+`0F00` | 无（xlsx描述的位置控制走`0x500`PVT，非此格式） | ⚠️自定义 |
| 4 | 速度控制 | 发→驱动 | `0x200+id` | `03`+目标(2B)+时长(2B)+`0F00` | 同上 | ⚠️自定义 |
| 5 | 电流控制 | 发→驱动 | `0x200+id` | `04`+目标(2B)+时长(2B)+`0F00` | 同上 | ⚠️自定义 |
| 6 | 六步换相 | 发→驱动 | `0x200+id` | `06`+目标(2B)+时长(2B)+`0F00` | 同上 | ⚠️自定义 |
| 7 | 设置心跳周期(含关闭) | 发→驱动 | `0x600+id` | `2B 17 10 00`+周期ms(2B)+`00 00` | "上位机发送"sheet／SDO index`0x1017` sub`0x00` | ✅有 |
| 8 | 借心跳触发读状态 | 发→驱动 | `0x600+id` | `2B 17 10 00 01 00 00 00` | 同上（复用同一对象，用法是代码自己的技巧） | ✅索引有，用法xlsx未写 |
| 9 | 设置周期上报(含关闭) | 发→驱动 | `0x600+id` | `2B 03 18 05`+周期ms(2B)+`00 00` | "上位机发送"sheet／SDO index`0x1803` sub`0x05` | ✅有 |
| 10 | offset清零 | 发→驱动 | `0x600+id` | `2B 01 20 05 00 00 00 00` | "SDO"sheet／index`0x2001` sub`0x05`(PosOffset) | ✅有 |
| 11 | offset写入补偿值 | 发→驱动 | `0x600+id` | `2B 01 20 05`+补偿量(2B)+`00 00` | 同上 | ✅有 |
| 12 | 力/推力传感器标零 | 发→驱动 | `0x600+id` | `23 02 20 01 00 00 00 00` | "SDO"sheet／index`0x2002` sub`0x01`(calibration) | ✅有 |
| 13 | 写入新设备ID | 发→驱动 | `0x600+id` | `2F 01 20 01`+新ID(1B)+`00 00 00` | "SDO"sheet／index`0x2001` sub`0x01`(Device ID) | ✅有 |
| 14 | 状态反馈(TxPDO4) | 驱动→收 | `0x480+id` | 32或48字节定长 | "上位机接收"sheet，逐字节表 | ✅有 |
| 15 | CiA402状态字 | 驱动→收 | `0x180+id` | 2字节+ | "SDO"sheet／`0x6041`位定义 | ✅有 |
| 16 | SDO写响应 | 驱动→收 | `0x580+id` | `60`+index(2B)+sub(1B)+... | 标准CANopen SDO响应格式 | ✅（标准） |
| 17 | SDO读响应 | 驱动→收 | `0x580+id` | `43/47/4B/4F`+index(2B)+sub(1B)+data | 标准CANopen SDO响应格式 | ✅（标准） |
| 18 | SDO失败响应 | 驱动→收 | `0x580+id` | `80`+... | 标准CANopen abort | ✅（标准） |

下面逐条展开字节级细节和代码出处。

---

## 1. 使能

| 项 | 内容 |
|---|---|
| 方向 | 主机 → 驱动 |
| 仲裁ID | `0x200 + 关节ID` |
| DLC/长度 | 7字节 |
| data | `00 00 00 00 00 07 00` |

**字节拆解**（沿用第3~6条共用的"控制帧"格式）：

| 字节 | 含义 | 本条取值 |
|---|---|---|
| [0] | 模式字节 | `00`（本条不带运动目标，纯状态切换） |
| [1:3] | 目标值(2B小端) | `00 00`（未使用） |
| [3:5] | 时长ms(2B小端) | `00 00`（未使用） |
| [5:7] | 控制字(2B小端) | `07 00` → 值=`0x0007` |

**xlsx 对照**：xlsx"上位机发送"sheet 描述的"上伺服"是走 SDO 写 `0x2011:01 = 0x4000`，和这条 `0x200` 控制帧**不是同一套指令**（详见 `CAN-guide.md` 第7章）。这条控制字`0x0007`是项目自定义的、类似 CiA402 Controlword"Switch On"的写法，**xlsx 没有直接文档化**。

**代码位置**：

```57:68:c:\Users\Administrator\Downloads\slider_upper_V5.2\slider_upper_V5.2\calib_v3.py
def is_enable(sign=0):
    if sign == 1:
        send_message(bus, 0x200, '00000000000700')  # 使能
    else:
        send_message(bus, 0x200, '00000000000400')  # 下使能
```

- `calib_v3.py` 第66行、`calib_v4.py` 第31行、`main.py` 第333行（函数`is_enable`）+ 第523行（`test()`里`'enable'`命令）
- `slider_upper.py` 第608行、第752行、第796行（内联`can.Message`，未走`_send_message`封装）
- `position_light.py` 第16行

---

## 2. 失能

| 项 | 内容 |
|---|---|
| 方向 | 主机 → 驱动 |
| 仲裁ID | `0x200 + 关节ID` |
| data | `00 00 00 00 00 04 00` |
| 控制字 | `0x0004` |

字节结构与"1.使能"完全相同，只是控制字取值不同。

**代码位置**：`calib_v3.py`第68行、`calib_v4.py`第33行、`main.py`第335/525/538行、`slider_upper.py`第560/640/658/824/910行、`position_light.py`第18行。

---

## 3. 位置控制

| 项 | 内容 |
|---|---|
| 方向 | 主机 → 驱动 |
| 仲裁ID | `0x200 + 关节ID` |
| data | `01` + 目标位置(2B小端) + 运行时长ms(2B小端) + `0F00` |

**字节拆解**：

| 字节 | 含义 | 单位/换算 |
|---|---|---|
| [0] | 模式字节 = `01` | 固定值，标识"位置模式" |
| [1:3] | 目标位置，int16小端 | 0.01mm整数（如1234=12.34mm） |
| [3:5] | 运行时长，int16小端 | 1ms |
| [5:7] | 控制字 = `0F 00` | `0x000F`，"使能+运行"的固定尾部 |

**举例**：目标12.34mm、耗时2000ms → `01 D2 04 D0 07 0F 00`

**xlsx 对照**：xlsx"上位机发送"sheet 里正规的位置指令是走 `0x500+id` 的 PVT 帧（index`0x1603`，字段`Drivecommand_PosTarget`，还能同时带`VelTarget`/`TorqTarget`/`Kp`/`Kd`做力位混合），本条是项目自定义的简化版单目标格式，**xlsx 未直接文档化这个 `0x200` 格式**。

**代码位置**：

```348:356:c:\Users\Administrator\Downloads\slider_upper_V5.2\slider_upper_V5.2\main.py
def positionControl(target_position, moveDuration):
    target_position = int(target_position)
    target_date["position"] = target_position
    target_position = target_position.to_bytes(2, byteorder="little", signed=True).hex()
    moveDuration = int(moveDuration)
    moveDuration = moveDuration.to_bytes(2, byteorder="little", signed=True).hex()
    data = '01' + target_position + moveDuration + '0F00'
    send_message(bus, 0x200, data)
```

- `main.py` 第348-356行（函数`positionControl`）
- `position_light.py` 第24-28行（内联拼接）
- `slider_upper.py` 第612-618行、第648-653行（GUI移动闭环里反复发送校正）

---

## 4. 速度控制

| 项 | 内容 |
|---|---|
| 方向 | 主机 → 驱动 |
| 仲裁ID | `0x200 + 关节ID` |
| data | `03` + 目标速度(2B小端) + 时长(2B小端) + `0F00` |

字节结构与"位置控制"相同，仅模式字节改为`03`。

**代码位置**：

```338:346:c:\Users\Administrator\Downloads\slider_upper_V5.2\slider_upper_V5.2\main.py
def speedControl(target_speed, moveDuration):
    target_speed = int(target_speed)
    target_date["speed"] = target_speed
    target_speed = target_speed.to_bytes(2, byteorder="little", signed=True).hex()
    moveDuration = int(moveDuration)
    moveDuration = moveDuration.to_bytes(2, byteorder="little", signed=True).hex()
    data = '03' + target_speed + moveDuration + '0F00'
    send_message(bus, 0x200, data)
```

仅 `main.py` 第338-346行（函数`speedControl`），被交互命令`s`调用。

---

## 5. 电流控制

| 项 | 内容 |
|---|---|
| 方向 | 主机 → 驱动 |
| 仲裁ID | `0x200 + 关节ID` |
| data | `04` + 目标电流(2B小端) + 时长(2B小端) + `0F00` |

**代码位置**：

```358:367:c:\Users\Administrator\Downloads\slider_upper_V5.2\slider_upper_V5.2\main.py
def currentControl(target_current, moveDuration):
    target_current = int(target_current)
    target_date["current"] = target_current
    target_current = target_current.to_bytes(2, byteorder="little", signed=True).hex()
    moveDuration = int(moveDuration)
    moveDuration = moveDuration.to_bytes(2, byteorder="little", signed=True).hex()
    data = '04' + target_current + moveDuration + '0F00'
    send_message(bus, 0x200, data)
```

仅 `main.py` 第358-367行（函数`currentControl`），被交互命令`c`调用。

---

## 6. 六步换相（调试用）

| 项 | 内容 |
|---|---|
| 方向 | 主机 → 驱动 |
| 仲裁ID | `0x200 + 关节ID` |
| data | `06` + 参数(2B小端) + 时长(2B小端) + `0F00` |

**代码位置**：`main.py` 第369-377行（函数`fc`），被交互命令`fc`调用。这是唯一没有在 xlsx 任何 sheet 里找到对应说明的模式字节，纯粹是调试/工厂测试用途。

---

## 7. 设置/关闭心跳周期

| 项 | 内容 |
|---|---|
| 方向 | 主机 → 驱动 |
| 仲裁ID | `0x600 + 关节ID` |
| data | `2B 17 10 00` + 周期ms(2B小端) + `00 00` |

**字节拆解（标准CANopen SDO expedited write）**：

| 字节 | 含义 | 取值 |
|---|---|---|
| [0] | 命令字cs | `0x2B`（写2字节） |
| [1:3] | index，小端(byte2<<8\|byte1) | `0x1017` |
| [3] | subindex | `0x00` |
| [4:6] | 数据，2字节小端 | 心跳周期(ms)，0=关闭 |
| [6:8] | 填充 | `00 00` |

**xlsx 对照**："上位机发送"sheet →"关闭心跳"：index`0x1017` sub`0x00`，示例数据`0x00`。索引/子索引/格式**完全一致**。

**代码位置**：

```322:329:c:\Users\Administrator\Downloads\slider_upper_V5.2\slider_upper_V5.2\main.py
def heart(rid=0):
    if rid == 1:
        hz = 1
        send_message(bus, 0x600, "2B171000" + hz.to_bytes(2, byteorder="little", signed=True).hex() + '0000')
    else:
        hz = 0
        send_message(bus, 0x600, "2B171000" + hz.to_bytes(2, byteorder="little", signed=True).hex() + '0000')
```

仅 `main.py` 第322-329行（函数`heart`），`test()`里调用`heart(0)`关闭心跳。

---

## 8. 借心跳周期触发一次状态字读取（`calib_v4.py`专用技巧）

| 项 | 内容 |
|---|---|
| 方向 | 主机 → 驱动（发送）+ 驱动 → 主机（等`0x180`） |
| 仲裁ID | 发`0x600+id`，收`0x180+id` |
| data(发) | `2B 17 10 00 01 00 00 00` |

**说明**：字节结构和"7."完全一样，都是写 `0x1017:00`，只是这里把周期临时设成 `1`（1ms），意图是**逼驱动器几乎立刻在`0x180`上广播一帧状态字**，代码借着这个"副作用"充当了一次"主动读状态"操作，而不是走标准的SDO读请求(`cs=0x40`)。

⚠️ **需要注意的隐患**：函数执行完之后**没有把心跳周期改回0**，如果这个函数被多次调用，驱动器会一直保持1ms心跳输出，可能增加总线负载。xlsx 里没有描述这种"复用"用法，纯粹是代码自己的实现技巧。

**代码位置**：

```57:65:c:\Users\Administrator\Downloads\slider_upper_V5.2\slider_upper_V5.2\calib_v4.py
def read_status(bus):
    clear_queue(bus)
    send_message(bus, 0x600, '2B17100001000000')
    time.sleep(0.05)
    msg = receive_message(bus, 1, [0x180])
    if msg and len(msg.data) >= 2:
        status = int.from_bytes(msg.data[0:2], byteorder='little', signed=False)
        return status
    return None
```

仅 `calib_v4.py` 第57-65行（函数`read_status`），被`wait_for_status_clear`和主流程调用。

---

## 9. 设置/关闭周期状态上报

| 项 | 内容 |
|---|---|
| 方向 | 主机 → 驱动 |
| 仲裁ID | `0x600 + 关节ID` |
| data | `2B 03 18 05` + 周期ms(2B小端) + `00 00` |

**字节拆解**：

| 字节 | 含义 | 取值 |
|---|---|---|
| [0] | cs | `0x2B`（写2字节） |
| [1:3] | index | `0x1803` |
| [3] | subindex | `0x05` |
| [4:6] | 数据(周期,ms,2B小端) | 项目里固定用`0x0020`=32ms；`main.py is_report()`可传1或0 |
| [6:8] | 填充 | `00 00` |

**xlsx 对照**："上位机发送"sheet →"开启上报"：index`0x1803` sub`0x05`，示例"打开2ms PDO4上报周期（500Hz上报）"。**索引/子索引/格式完全一致**，只是项目实际配置周期（32ms或1ms）和xlsx举例的2ms不同——这只是取值不同，不是格式问题。

**代码位置**（这是全项目出现频率最高的一条报文，几乎所有"读位置/读状态前都先发一次"）：

- `calib_v3.py` 第131-138行（固定`'2B03180520000000'`）
- `calib_v4.py` 第118行（固定值，同上）
- `main.py` 第313-319行（函数`is_report`，`hz`参数可变）
- `slider_upper.py` 第373/414/452/626/664行（`_send_message(0x600, '2B03180520000000')`，热插拔检测、位置监控、校准流程等多处复用）

---

## 10. offset清零

| 项 | 内容 |
|---|---|
| 方向 | 主机 → 驱动 |
| 仲裁ID | `0x600 + 关节ID` |
| data | `2B 01 20 05 00 00 00 00` |

**字节拆解**：

| 字节 | 含义 | 取值 |
|---|---|---|
| [0] | cs | `0x2B`（写2字节） |
| [1:3] | index | `0x2001` |
| [3] | subindex | `0x05` |
| [4:6] | 数据 | `00 00` = 0 |
| [6:8] | 填充 | `00 00` |

**xlsx 对照**："SDO"sheet → `0x2001` sub`5` = `PosOffset`，INT16，rw，**单位10um**。**索引/子索引/类型/单位全部一致**。

> ⚠️ 历史遗留笔误提醒：`calib_v3.py` 代码注释第118行写的是"索引0x2005子索引0x01"，这个注释**是反的**，正确应为索引`0x2001`子索引`0x05`（`CAN-guide.md` V2已修正这一处）。

**代码位置**：`calib_v3.py`第117-126行、`calib_v4.py`第114行、`slider_upper.py`第759行。

---

## 11. offset写入补偿值

| 项 | 内容 |
|---|---|
| 方向 | 主机 → 驱动 |
| 仲裁ID | `0x600 + 关节ID` |
| data | `2B 01 20 05` + 补偿量(2B小端,有符号) + `00 00` |

结构和"10."完全一样，只是[4:6]的数据换成实际补偿量（=用户输入的真实位置 − 反馈位置，单位0.01mm，和xlsx定义的"10um"单位一致，因为0.01mm=10um）。

**代码位置**：

```164:168:c:\Users\Administrator\Downloads\slider_upper_V5.2\slider_upper_V5.2\calib_v3.py
offset_position = int(offset_position).to_bytes(2, byteorder='little', signed=True).hex()
data = '2B012005' + offset_position + '0000'

bus.send(can.Message(arbitration_id=arbi_id, data=bytes.fromhex(data), is_extended_id=False, is_fd=True))
```

- `calib_v3.py` 第164-168行
- `calib_v4.py` 第144-150行（增加了失败重试逻辑，重试5次）
- `slider_upper.py` 第792-801行（GUI版，同样带重试）

---

## 12. 力/推力传感器标零

| 项 | 内容 |
|---|---|
| 方向 | 主机 → 驱动 |
| 仲裁ID | `0x600 + 关节ID` |
| data | `23 02 20 01 00 00 00 00` |

**字节拆解**：

| 字节 | 含义 | 取值 |
|---|---|---|
| [0] | cs | `0x23`（写4字节） |
| [1:3] | index | `0x2002` |
| [3] | subindex | `0x01` |
| [4:8] | 数据(4字节) | `00 00 00 00` = 0 |

**xlsx 对照**："SDO"sheet → `0x2002` sub`1` = `calibration`，INT32，rw，**"拉压力校零"**。**完全一致**。

**代码位置**：

```827:834:c:\Users\Administrator\Downloads\slider_upper_V5.2\slider_upper_V5.2\slider_upper.py
    def _force_zero_calib(self):
        """力传感器标零：SDO 2302200100000000"""
        device_id = self.device_id.get()
        self._update_status(f"[力传感器标零] 正在对ID={device_id}标零...")
        self._clear_queue()
        self._send_message(0x600, '2302200100000000')
```

仅 `slider_upper.py` 第827-835行（函数`_force_zero_calib`），是唯一实现这个功能的地方（CLI脚本没有对应功能）。

---

## 13. 写入新设备ID

| 项 | 内容 |
|---|---|
| 方向 | 主机 → 驱动（发） + 驱动 → 主机（等`0x580`确认） |
| 仲裁ID | 发`0x600+当前ID`，收`0x580+当前ID` |
| data(发) | `2F 01 20 01` + 新ID(1B) + `00 00 00` |
| data(期望收到) | 前4字节 = `60 01 20 01` |

**字节拆解（发送）**：

| 字节 | 含义 | 取值 |
|---|---|---|
| [0] | cs | `0x2F`（写1字节） |
| [1:3] | index | `0x2001` |
| [3] | subindex | `0x01` |
| [4] | 数据(1字节) | 新的关节ID(1~10) |
| [5:8] | 填充 | `00 00 00` |

**字节拆解（响应，验证成功）**：

| 字节 | 含义 |
|---|---|
| [0] | `0x60`，写成功 |
| [1:3] | index回显 `0x2001` |
| [3] | subindex回显 `0x01` |

响应的 index/subindex 和发出去的完全一致，这也反向验证了整套 cs/index/subindex 解码规则是对的。

**xlsx 对照**："SDO"sheet → `0x2001` sub`1` = `Device ID`，rw。**完全一致**。

> ⚠️ xlsx 内部矛盾提醒："上位机发送"sheet另有一行"设置ID"写的是`0x2033:04`，与"SDO"sheet的`0x2001:01`不一致，代码采用后者，怀疑`0x2033`是从"关节"产品线文档混入的笔误（详见 `CAN-guide.md` 9.10节）。

**代码位置**：

```850:861:c:\Users\Administrator\Downloads\slider_upper_V5.2\slider_upper_V5.2\slider_upper.py
        new_id_hex = f"{new_id:02X}"
        data = '2F012001' + new_id_hex + '000000'  # SDO 写设备 ID
        self._send_message(0x600, data)
        time.sleep(0.3)

        # 等待回复报文，ID=0x58x，x为改之前的ID
        expected_data = bytes.fromhex('60012001')
        msg = self._receive_message(1.0, [resp_id])
```

仅 `slider_upper.py` 第837-866行（函数`_write_new_id`），CLI脚本没有实现这个功能。

---

## 14. 状态反馈（TxPDO4，接收）

| 项 | 内容 |
|---|---|
| 方向 | 驱动 → 主机 |
| 仲裁ID | `0x480 + 关节ID` |
| 长度 | 32字节（DLC=13）或48字节（DLC=14，个别代码分支兼容） |
| 触发方式 | 驱动器按"9."配置的周期自动发，不需要单独请求 |

**32字节完整字段表**（`main.py ParseData()` 与 xlsx"上位机接收"sheet 逐字节核对一致）：

| 字节偏移 | 字段（xlsx命名） | 类型 | 单位/换算（推杆） |
|---|---|---|---|
| [0:2] | DriveResp_Status | uint16小端 | 状态码 |
| [2:4] | DriveResp_PosReal | int16小端 | ×0.00001 → m |
| [4:6] | DriveResp_VelReal | int16小端 | ×0.0001 → m/s |
| [6:8] | DriveResp_TorqReal | int16小端 | 1N |
| [8:10] | DriveResp_Errorcode | uint16小端 | 查"错误码"sheet |
| [10] | InstantFeedback_Ia | int8 | 1A |
| [11] | InstantFeedback_Ib | int8 | 1A |
| [12] | InstantFeedback_Ic | int8 | 1A |
| [13] | InstantFeedback_Udc | int8 | 1V |
| [14:16] | InstantFeedback_Idc | int16小端 | 0.01A |
| [16:18] | InstantFeedback_Id | int16小端 | 0.01A |
| [18:20] | InstantFeedback_Iq | int16小端 | 0.01A |
| [20:22] | InstantFeedback_IdRef | int16小端 | 0.01A |
| [22:24] | InstantFeedback_IqRef | int16小端 | 0.01A |
| [24:26] | InstantFeedback_motorIsLimit | int16小端 | 0.01A |
| [26:28] | InstantFeedback_TorqRef | int16小端 | 1N |
| [28] | InstantFeedback_MosTemperMax | int8 | ℃ |
| [29] | InstantFeedback_MotorTemperMax | int8 | ℃ |
| [30:32] | DriveResp_DataIndex | uint16小端 | 回显发出去的DataIndex |

**代码位置**：

```126:148:c:\Users\Administrator\Downloads\slider_upper_V5.2\slider_upper_V5.2\main.py
    if len(message.data) == 48:
        ...
    elif len(message.data) == 32:
        status = message.data[0:2].hex()
        position = int.from_bytes(message.data[2:4], byteorder='little', signed=True)
        ...
```

- `main.py` 第99-194行（函数`ParseData`，同时兼容32/48字节两种长度）
- `slider_upper.py` 第440-459行起（函数`_update_status_display`）、以及第416/628/666行等处只取`data[2:4]`位置字段的简化读取
- `calib_v3.py` 第154行、`calib_v4.py` 第75行、只取位置字段
- 大部分代码**只用到了[0:10]这10个字节**（状态/位置/速度/力/错误码），[10:32]的电流/温度细节字段主要在`main.py`的完整解析里用到

---

## 15. CiA402状态字（接收）

| 项 | 内容 |
|---|---|
| 方向 | 驱动 → 主机 |
| 仲裁ID | `0x180 + 关节ID` |
| 长度 | ≥2字节 |

**字节拆解**：

| 字节 | 含义 |
|---|---|
| [0:2] | 状态字，uint16小端（`data[0] \| (data[1]<<8)`） |

**xlsx 对照**："SDO"sheet → `0x6041` Statusword，共31个故障位定义（节选，完整见`CAN-guide.md`9.13节）：

| bit | 含义 |
|---|---|
| 2/3 | 电压过低/过高 |
| 6/7/8 | C/B/A相电流过大 |
| 9/10/11 | C/B/A相电流偏移校准错误 |
| 12/13 | 电机温度点2/1警告 |
| 16/17 | 电机温度点2/1过高 |
| 22/23 | 位置后向/前向超限 |
| 26/27 | 编码器故障/通讯异常 |
| 28/29/30 | 驱动寄存器复位/驱动故障/驱动通信异常 |
| 31 | CANFD PDO中断 |

⚠️ **代码里的解析已过时**：`main.py` 顶部硬编码的 `Statusword6041` 文字列表（13项）和xlsx这31位定义**对不上**（比如代码bit6="位置超出限制范围"，xlsx bit6="C相电流过大"），使用时要小心，不要直接信这份旧列表打印出来的文字。

**代码位置**：

```247:262:c:\Users\Administrator\Downloads\slider_upper_V5.2\slider_upper_V5.2\main.py
        if msg.arbitration_id == 0x180 + device_id:
            data = msg.data
            status = data[0] | (data[1]<<8)
            current_date["status"] = status
```

- `main.py` 第247-265行（`receive_data`函数内）
- `calib_v4.py` 第61-64行（`read_status`函数，只取原始数值，不做位解析）

---

## 16~18. SDO 响应（接收，`0x580+id`）

| 项 | 内容 |
|---|---|
| 方向 | 驱动 → 主机 |
| 仲裁ID | `0x580 + 关节ID` |

**三种响应格式**（标准CANopen SDO响应，字节结构和发送时的SDO请求对称）：

| 类型 | [0]cs | [1:3]index | [3]subindex | [4:8]数据 | 含义 |
|---|---|---|---|---|---|
| 写成功 | `0x60` | 回显 | 回显 | — | 上一条SDO写请求成功 |
| 读成功(1字节) | `0x4F` | 回显 | 回显 | 1字节有效数据 | — |
| 读成功(2字节) | `0x4B` | 回显 | 回显 | 2字节有效数据 | — |
| 读成功(4字节) | `0x43` | 回显 | 回显 | 4字节有效数据 | — |
| 失败 | `0x80` | 回显 | 回显 | abort错误码 | 上一条SDO请求失败 |

**代码位置**：

```266:279:c:\Users\Administrator\Downloads\slider_upper_V5.2\slider_upper_V5.2\main.py
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
```

- `main.py` 第266-279行（`receive_data`函数内，`cs`的取值判断和上表一致）
- `calib_v4.py` 第153-166行（`calib_v4()`函数内，只识别`0x4F`/`0x4B`两种成功码 + 读`data[4:6]`确认状态值）
- `slider_upper.py` 第859-861行（`_write_new_id`函数，只匹配固定前4字节`60012001`判断改ID是否成功）

---

## 附：本文档 vs `CAN-guide.md` 的分工

- **`CAN-guide.md`**：讲原理、讲分层、讲为什么、讲FAQ，适合从头理解整个通信体系。
- **本文档（`CAN-报文对照表.md`）**：只做"报文级"的速查手册，回答"这条报文格式是什么/对应xlsx哪一行/代码在哪发的"，适合写代码时随手翻查、或者对照 xlsx 抓包调试时用。

两份文档互相引用，建议配合着看。
