# delivery_robot 工程详解文档（README_A）

> 面向第一次接触本项目的同学：读完本文件，你应当能够理解**整体架构、每个节点职责、topic/service/parameter/launch 的联动关系**，并且可以直接完成构建、运行、调试与演示。

---

## 1. 项目定位与目标

`delivery_robot` 是一个基于 **ROS2 Humble + turtlesim + Python(rclpy)** 的课程级仿真工程。

它模拟了一个“酒店送餐机器人”流程：
- 在 turtlesim 中画出简化酒店地图（走廊、房间、门口、起点）；
- 接收送餐目标房间；
- 按预定义路径分段移动（非直线、非自动规划）；
- 在终端实时展示任务状态与路径进度；
- 到达后可自动回起点；
- 支持开始、取消、查询、复位四类服务操作。

本工程重点展示 ROS2 四大基础能力：
1. Topic 通信
2. Service 通信
3. Parameter 参数系统
4. Launch 一键启动

---

## 2. 工程目录与模块说明

工程核心目录（包路径）：`src/delivery_robot`

- `CMakeLists.txt`  
  负责 ament/rosidl 构建逻辑，自定义 `srv` 接口生成。

- `package.xml`  
  声明依赖（`rclpy`、`turtlesim`、`std_msgs`、`geometry_msgs`、`rosidl` 等）。

- `setup.py` / `setup.cfg` / `resource/delivery_robot`  
  Python 包安装与入口点配置（四个节点脚本的可执行入口）。

- `srv/`  
  自定义服务接口：
  - `StartDelivery.srv`
  - `CancelDelivery.srv`
  - `GetDeliveryStatus.srv`
  - `ResetRobot.srv`

- `config/hotel_params.yaml`  
  参数配置中心：起点、房间坐标、控制参数、调试参数等。

- `launch/hotel_delivery.launch.py`  
  一键启动：`turtlesim_node` + 地图节点 + 管理节点 + 运动节点 + 状态监视节点。

- `delivery_robot_nodes/common.py`  
  公共常量与工具：状态常量、坐标数据结构、路径构建、编码解码、角度工具。

- `delivery_robot_nodes/hotel_map_node.py`  
  地图绘制节点：通过 turtlesim 服务生成绘图海龟并绘制地图。

- `delivery_robot_nodes/delivery_manager_node.py`  
  任务管理节点：服务入口、状态机管理、路径下发、到达/回程控制。

- `delivery_robot_nodes/path_motion_node.py`  
  路径跟踪节点：订阅姿态、执行路径、发布位置/进度/到达标志。

- `delivery_robot_nodes/status_monitor_node.py`  
  终端看板节点：将关键状态集中打印，方便演示与调试。

---

## 3. 系统运行时架构（节点协作）

### 3.1 节点列表

1. `turtlesim_node`（官方）
2. `hotel_map_node`
3. `delivery_manager_node`
4. `path_motion_node`
5. `status_monitor_node`

### 3.2 启动时序（简化）

1. 启动 `turtlesim_node`。
2. 启动 `hotel_map_node`，等待 turtlesim 服务就绪后绘图。
3. 延时启动 `delivery_manager_node`、`path_motion_node`、`status_monitor_node`。
4. 系统进入 `idle`，等待 `/start_delivery`。

---

## 4. Topic 设计与数据流（非常关键）

> 下表是“谁发布、谁订阅、用于什么”的总览。

### 4.1 机器人控制与姿态

1. `/turtle1/cmd_vel`（`geometry_msgs/msg/Twist`）
- 发布者：`path_motion_node`（在取消/复位场景，`delivery_manager_node` 也会发零速度停止）
- 订阅者：`turtlesim_node`
- 作用：驱动机器人线速度/角速度。

2. `/turtle1/pose`（`turtlesim/msg/Pose`）
- 发布者：`turtlesim_node`
- 订阅者：`path_motion_node`
- 作用：闭环控制输入（当前 `x,y,theta`）。

### 4.2 任务状态相关

3. `/delivery_status`（`std_msgs/msg/String`）
- 发布者：`delivery_manager_node`
- 订阅者：`status_monitor_node`
- 作用：广播状态机当前状态（idle/planning/...）。

4. `/current_target_room`（`std_msgs/msg/String`）
- 发布者：`delivery_manager_node`
- 订阅者：`status_monitor_node`
- 作用：当前任务目标房间。

### 4.3 路径执行与可视化调试

5. `/delivery_path`（`std_msgs/msg/String`）
- 发布者：`delivery_manager_node`
- 订阅者：`path_motion_node`
- 作用：传递整条路径点序列（编码字符串）。
- 编码形式示例：`0.800,0.900;0.800,5.500;7.800,5.500;7.800,8.100`

6. `/robot_position`（`geometry_msgs/msg/Point`）
- 发布者：`path_motion_node`
- 订阅者：`status_monitor_node`
- 作用：输出当前机器人坐标用于看板展示。

7. `/path_progress`（`std_msgs/msg/String`）
- 发布者：`path_motion_node`
- 订阅者：`status_monitor_node`、`delivery_manager_node`
- 作用：显示“当前段/总段、目标点、误差”等调试信息；管理节点据此切换阶段状态。

8. `/arrival_flag`（`std_msgs/msg/Bool`）
- 发布者：`path_motion_node`
- 订阅者：`delivery_manager_node`
- 作用：路径全部执行完成时发 `True`，触发到达逻辑（停留、回程、结束）。

---

## 5. Service 设计与使用方式

### 5.1 `/start_delivery`（`StartDelivery.srv`）

请求：
- `string room_name`

响应：
- `bool success`
- `string message`

行为：
1. 校验当前是否忙碌。
2. 校验房间名是否合法（必须在 `room_names` 中）。
3. 构建路径并发布 `/delivery_path`。
4. 切换状态到执行阶段。

命令：
```bash
ros2 service call /start_delivery delivery_robot/srv/StartDelivery "{room_name: 'room_102'}"
```

### 5.2 `/cancel_delivery`（`CancelDelivery.srv`）

请求：空  
响应：`success/message`

行为：
- 若有任务：切换 `cancelled`、发停止速度、清空路径、清理计时器。
- 若无任务：返回失败并提示。

命令：
```bash
ros2 service call /cancel_delivery delivery_robot/srv/CancelDelivery "{}"
```

### 5.3 `/get_delivery_status`（`GetDeliveryStatus.srv`）

请求：空  
响应：
- `string status`
- `string current_room`
- `bool has_task`

命令：
```bash
ros2 service call /get_delivery_status delivery_robot/srv/GetDeliveryStatus "{}"
```

### 5.4 `/reset_robot_to_start`（`ResetRobot.srv`）

请求：空  
响应：`success/message`

行为：
- 停止机器人；
- 通过 `/turtle1/teleport_absolute` 把机器人传送回起点；
- 清空任务并置 `idle`。

命令：
```bash
ros2 service call /reset_robot_to_start delivery_robot/srv/ResetRobot "{}"
```

---

## 6. 参数系统（Parameter）详解

参数来源：`config/hotel_params.yaml`

> 参数会在节点启动时读取；你改了参数后需重新 launch（一般建议重新 build + source 以避免旧环境影响）。

### 6.1 起点参数

- `start_x` / `start_y`  
  机器人起点坐标。用于：
  - 地图节点将 `turtle1` 放到起点；
  - 管理节点规划去程/回程路径起终点。

### 6.2 控制参数（主要给 path_motion_node）

- `robot_speed`  
  最大/基准线速度。
- `angular_gain`  
  角速度比例增益（角误差越大，转向越快）。
- `arrival_tolerance`  
  到点判定阈值（距离小于该值视为到达当前路径点）。
- `slowdown_distance`  
  接近目标点时触发减速的距离阈值。

### 6.3 地图参数

- `corridor_y`  
  主走廊 y 坐标，路径会先并入该走廊再横向移动。
- `map_draw_speed`  
  地图绘制速度相关参数（影响绘图过程快慢/观感）。

### 6.4 房间参数

- `room_names`  
  房间名列表（动态扩展入口）。
- `<room_name>_x` / `<room_name>_y`  
  每个房间门口停靠点坐标。

例如：
- `room_101_x`, `room_101_y`
- `room_202_x`, `room_202_y`

> 你新增房间时，只要：
> 1) 在 `room_names` 里加名字；
> 2) 增加该房间的 `_x/_y` 参数；
> 地图与任务管理会按动态房间列表生效。

### 6.5 调试参数

- `enable_status_log`  
  控制是否输出调试日志。
- `show_debug_path`  
  控制是否输出详细路径调试信息。
- `return_wait_seconds`  
  到达目标后停留时长（秒），之后自动回起点。

---

## 7. 状态机语义（delivery_manager_node）

系统主要状态：

1. `idle`：空闲，等待任务。
2. `planning`：收到任务后正在生成路径。
3. `delivering_to_corridor`：从起点向走廊并入。
4. `moving_along_corridor`：沿主走廊横向移动。
5. `approaching_room`：从走廊转向房间门口。
6. `arrived`：到达门口。
7. `cancelled`：任务被取消。
8. `error`：非法房间、路径生成失败或关键服务异常。

典型状态迁移：
- `idle -> planning -> delivering_to_corridor -> moving_along_corridor -> approaching_room -> arrived`
- 执行中收到取消：`* -> cancelled`
- 参数/房间异常：`* -> error`

到达逻辑：
- 第一次到达目标门口后进入 `arrived`；
- 等待 `return_wait_seconds`；
- 发布回程路径；
- 回到起点后置回 `idle` 并清任务。

---

## 8. 路径规划与执行机制

### 8.1 路径规划（common + manager）

采用“固定规则路径”，不做全局规划：

去程路径模板：
1. 起点
2. `(start_x, corridor_y)`（先竖直到走廊）
3. `(room_x, corridor_y)`（沿走廊横移）
4. `(room_x, room_y)`（竖直到门口）

回程路径模板：
1. 当前门口
2. `(room_x, corridor_y)`
3. `(start_x, corridor_y)`
4. 起点

### 8.2 路径执行（path_motion_node）

控制策略（闭环）：
- 计算当前位置到目标点的距离与角度误差；
- 角误差大时优先转向；
- 角误差合适后前进；
- 距离小于 `arrival_tolerance` 切下一个路径点；
- 全部点完成后发布 `/arrival_flag=True` 并停车。

这样可以保证 turtlesim 场景下稳定且可解释，便于课程展示。

---

## 9. 地图绘制机制（hotel_map_node）

绘图核心过程：
1. 等待 turtlesim 服务（`/spawn`、`/kill`、`/<name>/teleport_absolute`、`/<name>/set_pen`）。
2. 先将主机器人 `turtle1` 放到起点并关闭画笔（避免留下轨迹）。
3. 生成绘图海龟 `map_drawer`。
4. 通过“抬笔 teleport 到起点 -> 落笔 teleport 到终点”方式画线。
5. 画走廊、房间框、门口连线、起点区域。
6. 依据 `room_names` 动态绘制房间文字标签。

绘图与运动分离：
- 绘图海龟用于地图，不参与送餐控制；
- `turtle1` 只负责“机器人运动”。

---

## 10. 一键运行与常用命令（实操清单）

### 10.1 构建
```bash
cd ~/your_ws
colcon build --packages-select delivery_robot
```

### 10.2 载入环境
```bash
source install/setup.bash
```

### 10.3 启动系统
```bash
ros2 launch delivery_robot hotel_delivery.launch.py
```

### 10.4 发起送餐
```bash
ros2 service call /start_delivery delivery_robot/srv/StartDelivery "{room_name: 'room_101'}"
```

### 10.5 查询状态
```bash
ros2 service call /get_delivery_status delivery_robot/srv/GetDeliveryStatus "{}"
```

### 10.6 取消任务
```bash
ros2 service call /cancel_delivery delivery_robot/srv/CancelDelivery "{}"
```

### 10.7 复位机器人
```bash
ros2 service call /reset_robot_to_start delivery_robot/srv/ResetRobot "{}"
```

### 10.8 观察 topic
```bash
ros2 topic echo /delivery_status
ros2 topic echo /current_target_room
ros2 topic echo /robot_position
ros2 topic echo /path_progress
ros2 topic echo /arrival_flag
```

### 10.9 观察参数
```bash
ros2 param list
ros2 param get /path_motion_node robot_speed
ros2 param get /delivery_manager_node corridor_y
```

---

## 11. 典型演示脚本（课堂推荐）

1. 启动 launch，介绍节点分工。
2. `start_delivery room_102`，展示路径分段运动。
3. 同步 `echo /path_progress`，说明阶段切换。
4. `get_delivery_status` 展示状态/房间/has_task。
5. 演示到达后停留与自动回起点。
6. 再发一次任务，并中途 `cancel_delivery`。
7. 最后 `reset_robot_to_start` 收尾。

---

## 12. 常见问题与定位建议

1. **地图不画**  
- 先看 `hotel_map_node` 是否启动；
- 查服务：`ros2 service list | grep -E "spawn|set_pen|teleport"`。

2. **机器人不动**  
- 查 `path_motion_node` 是否收到 `/delivery_path`；
- 查 `/turtle1/pose` 是否正常发布。

3. **开始任务失败**  
- 房间名必须在 `room_names` 内；
- 可先 `get_delivery_status` 看是否处于忙碌态。

4. **状态看板信息不更新**  
- 检查 `status_monitor_node` 是否存活；
- 分别 echo `/delivery_status`、`/robot_position`、`/path_progress`。

5. **参数改了不生效**  
- 重新 launch；
- 有构建变化时先 `colcon build` 再 `source install/setup.bash`。

---

## 13. 扩展建议（后续可做）

1. 多楼层：
- 在参数中加入 `floor` 维度，路径函数按楼层切换走廊。

2. 更多状态：
- 增加 `returning_to_corridor`、`returning_to_start` 等细分状态，提升可观测性。

3. 更丰富 UI：
- 增加一个 RViz/网页看板（课程允许时）。

4. 更严谨的异常恢复：
- 服务超时重试、路径重规划、失败自动复位策略。

---

## 14. 速查总表（记忆版）

- 管任务：`delivery_manager_node`
- 管运动：`path_motion_node`
- 画地图：`hotel_map_node`
- 看日志：`status_monitor_node`
- 发任务：`/start_delivery`
- 停任务：`/cancel_delivery`
- 查状态：`/get_delivery_status`
- 回起点：`/reset_robot_to_start`
- 参数入口：`config/hotel_params.yaml`
- 一键启动：`ros2 launch delivery_robot hotel_delivery.launch.py`

---

如果你是第一次接手本工程，建议先按“第10节实操清单”跑通，再对照“第4~8节”逐条验证 topic/service/状态机变化，理解会非常快。
