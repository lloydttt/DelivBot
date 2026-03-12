# delivery_robot 四个节点源码逐行/逐函数讲解（README_function）

> 说明：你要求“把四个 node 节点 py 源文件中每一个函数、每一行是什么意思和作用讲清楚”。  
> 本文档采用“**文件级 → 函数级 → 关键行级**”结构，尽可能覆盖所有代码行。为了可读性，import、空行、注释、结构性语句也会解释。

---

## 目录

1. `hotel_map_node.py` 逐行讲解
2. `delivery_manager_node.py` 逐行讲解
3. `path_motion_node.py` 逐行讲解
4. `status_monitor_node.py` 逐行讲解
5. 四个节点协同关系总表（便于对外讲解）

---

## 1) `hotel_map_node.py` 逐行讲解

### 1.1 文件作用（一句话）

该节点负责在 turtlesim 中绘制酒店地图（走廊、房间、门口、起点区），并在绘图前把主机器人 `turtle1` 放到起点并关闭画笔，避免产生无关轨迹。

### 1.2 顶部导入与常量

- `#!/usr/bin/env python3`  
  指定脚本解释器，保证在 Linux/ROS2 环境可直接作为可执行脚本运行。

- 模块 docstring：说明这是“绘制酒店地图”的节点。

- `import time`  
  用于在 kill 旧绘图海龟后短暂等待，降低服务时序冲突概率。

- `from typing import Dict, List, Tuple`  
  用于类型标注，增强可读性与静态分析能力。

- `import rclpy`、`from rclpy.node import Node`  
  ROS2 Python 客户端库与节点基类。

- `from turtlesim.srv import Kill, SetPen, Spawn, TeleportAbsolute`  
  声明本节点要调用的 turtlesim 服务类型。

- `from delivery_robot_nodes.common import ...`  
  引入公共工具：
  - `Point2D`：点坐标数据结构
  - `VALID_ROOMS`：默认房间名集合
  - `normalize_room_names`：房间名标准化
  - `room_positions_from_params`：从参数构造房间坐标映射

- `FONT = {...}`  
  这是一个“简化矢量字库”。每个字符由若干线段定义，线段由起止点 `(x1,y1)->(x2,y2)` 组成。  
  作用：用海龟画线模拟文本，实现在地图上标注房间名。

### 1.3 类定义：`class HotelMapNode(Node)`

继承 ROS2 `Node`，封装全部地图绘制逻辑。

#### `__init__(self)`

执行顺序：
1. `super().__init__('hotel_map_node')`  
   设置 ROS 节点名。
2. `self._declare_parameters()`  
   声明本节点需要的参数及默认值。
3. `self.params = self._read_params()`  
   读取参数到字典。
4. 创建服务 client：
   - `/spawn`
   - `/kill`
   - `/turtle1/teleport_absolute`
   - `/turtle1/set_pen`
5. 设置绘图海龟相关成员：
   - `self.drawer_name = 'map_drawer'`
   - `self.teleport_client = None`
   - `self.pen_client = None`
6. 依次等待服务就绪（循环重试）：
   - `self._wait_client(...)`
7. `self._prepare_main_robot()`  
   先把主机器人移动到起点并关笔。
8. `self._draw_once_on_startup()`  
   节点启动后立即绘图一次。

#### `_declare_if_needed(self, name, default_value)`

- 含义：若参数未声明则声明。  
- 作用：避免重复声明参数导致 `ParameterAlreadyDeclaredException`。

#### `_declare_parameters(self)`

逐项声明参数：
- `start_x/start_y`：起点
- `corridor_y`：走廊高度
- `room_names`：动态房间列表
- 对 `VALID_ROOMS` 中每个房间，声明 `<room>_x/<room>_y`

这是“参数 schema + 默认值”的声明入口。

#### `_read_params(self) -> Dict[str, float]`

读取参数并构造统一字典：
1. 先读取并规范化 `room_names`；
2. 针对动态房间名补声明其坐标参数（防止未声明）；
3. 填充基础参数：`start_x/start_y/corridor_y`；
4. 遍历房间名读取每个房间 `_x/_y`；
5. 返回 `values`。

注意：`values['room_names']` 放的是列表（虽然函数标注写了 `Dict[str,float]`，但实际也存了 list，这是 Python 运行时允许的）。

#### `_wait_client(self, client, name)`

- 作用：服务等待循环。  
- 若 `wait_for_service(timeout_sec=1.0)` 返回 False，就打印 warn 并继续等待。

#### `_call_sync(self, client, req, timeout=3.0)`

- 发起异步服务调用 `call_async`；
- 用 `rclpy.spin_until_future_complete` 阻塞等待结果；
- 若超时/无结果，抛出 `RuntimeError`；
- 否则返回服务响应对象。

这是本节点所有服务调用的统一封装。

#### `_prepare_main_robot(self)`

- 用 `/turtle1/set_pen` 把主机器人的画笔关闭（`off=1`）；
- 用 `/turtle1/teleport_absolute` 把主机器人放到 `start_x,start_y`；
- 打印 info 日志说明准备完成。

核心价值：保证地图绘制期间主机器人不留轨迹且初始位置正确。

#### `_draw_once_on_startup(self)`

- 打印“开始绘制”；
- try 中调用：
  - `_spawn_drawer()`
  - `_draw_map()`
- 成功打印 completed，失败捕获异常并打印 error。

#### `_spawn_drawer(self)`

1. 尝试 kill 同名旧海龟（容错，失败忽略）；
2. `Spawn.Request(x=1.0,y=1.0,theta=0.0,name='map_drawer')` 创建新绘图海龟；
3. 保存服务返回名字；
4. 为该海龟创建 `/teleport_absolute` 与 `/set_pen` client；
5. 等待这两个服务可用。

#### `_set_pen(self, r,g,b,width,off)`

包装 `SetPen` 服务调用：
- 设置颜色、线宽、开关笔。

#### `_teleport(self, x,y,theta=0.0)`

包装 `TeleportAbsolute` 服务调用：
- 将绘图海龟瞬移到指定点。

#### `_draw_line(self, x1,y1,x2,y2,width=2)`

绘线套路：
1. 先关笔并移到起点；
2. 再开笔并移到终点；

这样可以避免从“上一次位置”到“本次起点”的多余连线。

#### `_draw_rectangle(self, x,y,w,h)`

连续调用 `_draw_line` 画四条边，形成矩形。

#### `_draw_text(self, text,x,y,scale=0.22,spacing=0.10)`

- 遍历字符；
- 查 `FONT` 字典获取字符线段；
- 把每条线段从字形局部坐标映射到世界坐标并绘制；
- `cursor_x` 逐字符右移，实现文本串行排布。

#### `_draw_room_and_label(self, room_name, door, corridor_y)`

给单个房间绘制：
1. 设定房间框宽高；
2. 判断房间在走廊上方还是下方：`upper = door.y >= corridor_y`；
3. 根据门点算房间矩形位置；
4. 画房间矩形；
5. 画门连线（粗线 width=4）；
6. 计算文字位置并 `_draw_text(room_name,...)`。

#### `_draw_map(self)`

地图总控：
1. 读取起点/走廊/房间参数；
2. 画走廊主线 `_draw_line(1.0, corridor_y, 10.2, corridor_y)`；
3. 遍历房间映射，逐房间 `_draw_room_and_label`；
4. 画起点区域矩形（围绕 start_x,start_y）。

### 1.4 `main()`

标准 ROS2 Python 节点启动模板：
1. `rclpy.init()`
2. 创建 `HotelMapNode`
3. `rclpy.spin(node)` 保持运行
4. KeyboardInterrupt 时优雅退出
5. `destroy_node()` + `rclpy.shutdown()`

---

## 2) `delivery_manager_node.py` 逐行讲解

### 2.1 文件作用（一句话）

任务管理中心：对外提供 service API，内部维护状态机，负责生成/发布路径并处理到达、取消、复位。

### 2.2 import 区解释

- `typing.Dict`：参数字典类型注解。
- `rclpy` / `Node`：ROS2 Python 节点基础。
- `Twist`：必要时发停止速度。
- `Bool, String`：状态/路径/到达等 topic 数据。
- `TeleportAbsolute`：复位服务。
- `from delivery_robot_nodes.common import ...`：
  - 状态常量
  - 房间名工具
  - 路径构建函数（去程+回程）
  - 路径编码函数
  - 参数转房间映射
- `from delivery_robot.srv import ...`：4个自定义服务类型。

### 2.3 类定义：`DeliveryManagerNode`

#### `__init__(self)`

1. 初始化节点名：`delivery_manager_node`。
2. 参数声明+读取：
   - `_declare_parameters()`
   - `_read_params()`
3. 初始化运行态成员：
   - `self.state = STATE_IDLE`
   - `self.current_room = ''`
   - `self.has_task = False`
   - `self.returning = False`
   - `self.active_path = []`
   - `self.return_timer = None`
4. 创建 publisher：
   - `/delivery_status`
   - `/current_target_room`
   - `/delivery_path`
   - `/turtle1/cmd_vel`
5. 创建 subscriber：
   - `/arrival_flag` -> `_on_arrival`
   - `/path_progress` -> `_on_path_progress`
6. 创建 service server：
   - `/start_delivery`
   - `/cancel_delivery`
   - `/get_delivery_status`
   - `/reset_robot_to_start`
7. 创建 `teleport_client`：用于 reset。
8. 创建定时器 `publish_timer`（0.5s）周期发布状态。
9. 打印 ready 与合法房间列表。

#### `_declare_if_needed(self, name, default_value)`

与地图节点同理：防重复声明。

#### `_declare_parameters(self)`

声明参数：
- `start_x/start_y/corridor_y`
- `return_wait_seconds`
- `room_names`
- 预定义房间坐标默认值

#### `_read_params(self)`

1. 读取并规范化 `room_names`；
2. 对动态房间补声明坐标参数；
3. 读取基础参数到 `values`；
4. 读取每个房间坐标到 `values`；
5. 返回字典。

#### `_set_state(self, new_state)`

- 若新状态与旧状态不同，打印状态迁移日志并更新 `self.state`。

#### `_periodic_publish(self)`

每 0.5s 执行一次：
- 发布 `/delivery_status` 当前状态；
- 发布 `/current_target_room` 当前目标房间。

#### `_start_delivery(self, request, response)`

这是最关键服务回调：

流程：
1. 取 `room_name` 并标准化（去空格+小写）；
2. 若正在忙（且不在 idle/arrived/cancelled/error），拒绝新任务；
3. 若房间不在合法列表，置 `error` 并失败返回；
4. 状态置 `planning`；
5. 由参数构造 `room_map`；
6. 调用 `build_path_for_room(room,start,corridor_y,room_map)` 得到去程路径；
7. 路径为空则失败并置 `error`；
8. 更新任务上下文（current_room/has_task/active_path/returning）；
9. 用 `encode_path(path)` 编码后发布到 `/delivery_path`；
10. 状态切到 `delivering_to_corridor`；
11. service 返回 success。

#### `_on_path_progress(self, msg)`

通过解析进度字符串触发阶段状态切换：
- 包含 `segment 2/` -> `moving_along_corridor`
- 包含 `segment 3/` -> `approaching_room`

#### `_schedule_return_to_start(self)`

- 读取 `return_wait_seconds`；
- 记录日志“到达后等待 N 秒回起点”；
- 若已有旧定时器先取消；
- 新建 one-shot 风格定时器（回调 `_start_return_once`，回调里会自取消）。

#### `_start_return_once(self)`

回程触发逻辑：
1. 先取消并清理 `return_timer`（避免重复触发）；
2. 若当前不满足回程条件（不是 arrived/无任务/已在回程）则直接返回；
3. 重新构建 `room_map` 与 `start`；
4. 调 `build_return_path_from_room()` 得回程路径；
5. 若回程路径无效则 error 日志返回；
6. `self.returning=True`；
7. 发布回程路径到 `/delivery_path`；
8. 状态设回 `delivering_to_corridor`（回程阶段的统一入口）。

#### `_on_arrival(self, msg)`

处理 `/arrival_flag`：
- 若 `msg.data` 不是 True 或当前无任务，忽略；

两种分支：
1. `self.returning == True`：说明是“回起点后到达”
   - 状态 -> idle
   - 清理任务上下文
   - 取消定时器
2. 否则说明“首次到达目标房间”
   - 状态 -> arrived
   - 调 `_schedule_return_to_start()`

#### `_cancel_delivery(self, _, response)`

取消服务：
1. 若无任务或本来已 idle/cancelled，返回失败提示；
2. 否则状态 -> cancelled；
3. 发布 `Twist()` 零速度停机；
4. 发布空路径 `String(data='')` 让运动节点停止路径执行；
5. 清理任务上下文+回程定时器；
6. 返回 success。

#### `_get_status(self, _, response)`

查询服务：
- 直接填充当前 `state/current_room/has_task`。

#### `_reset_robot(self, _, response)`

复位服务：
1. 等待 `/turtle1/teleport_absolute` 服务；
2. 发布零速度停机；
3. 调 teleport 把机器人送回起点；
4. 若调用超时，返回失败；
5. 清理任务上下文；
6. 状态 -> idle；
7. 返回 success。

### 2.4 `main()`

与其他节点同样：init -> create node -> spin -> destroy -> shutdown。

---

## 3) `path_motion_node.py` 逐行讲解

### 3.1 文件作用（一句话）

将“路径点序列”转换成稳定的速度控制指令，驱动 turtle1 按段到达目标，并发布实时进度/位置/到达标志。

### 3.2 顶部导入解释

- `math`：用于距离、角度、三角函数计算。
- `rclpy` / `Node`：ROS2 节点基础。
- `Point, Twist`：位置与速度消息。
- `Pose`：turtlesim 姿态。
- `Bool, String`：进度与控制消息。
- `from common import Point2D, decode_path, normalize_angle`：
  - `decode_path`：解析 manager 发来的路径字符串
  - `normalize_angle`：把角误差压到 [-pi,pi]

### 3.3 类定义：`PathMotionNode`

#### `__init__(self)`

1. 初始化节点名 `path_motion_node`；
2. 声明并读取控制参数：
   - `robot_speed`
   - `angular_gain`
   - `arrival_tolerance`
   - `slowdown_distance`
3. 初始化运行态：
   - `self.pose = None`（当前姿态）
   - `self.path = []`（当前路径）
   - `self.target_index = 0`（当前目标点索引）
   - `self.has_arrived_published = False`（防重复发布到达）
4. 创建订阅：
   - `/turtle1/pose` -> `_on_pose`
   - `/delivery_path` -> `_on_path`
5. 创建发布：
   - `/turtle1/cmd_vel`
   - `/robot_position`
   - `/path_progress`
   - `/arrival_flag`
6. 创建控制定时器（常见为 20Hz 附近，如 0.05s）；
7. 打印 ready 日志。

> 注：具体定时周期以源码为准，讲解时可说“固定周期闭环控制”。

#### `_declare_parameters(self)` / `_read_params(self)`

- 声明默认控制参数并读取为成员变量（或字典）。
- 这些参数直接影响速度大小、转向灵敏度、到点判定与减速行为。

#### `_on_pose(self, msg: Pose)`

- 缓存当前姿态到 `self.pose`。
- 同时把当前位置包装为 `Point` 发布到 `/robot_position`（供 monitor 展示）。

#### `_on_path(self, msg: String)`

- 若收到空字符串路径：清空任务并停机；
- 否则 `decode_path(msg.data)` 解析成点列表；
- 设置 `self.path`，`self.target_index=0`，重置到达标志；
- 进入“执行路径”状态。

#### `_publish_stop(self)`

- 发布零速度 `Twist()`，确保机器人停止。

#### `_publish_progress(self, text: str)`

- 将进度文本发到 `/path_progress`。
- 文本通常包含当前段号、总段数、目标点、误差等调试信息。

#### `_control_loop(self)`

核心控制周期函数，每次执行逻辑大致是：

1. **前置校验**
   - 若 `self.pose is None`：无姿态，不能控制，直接返回；
   - 若 `self.path` 为空：保持停止并返回。

2. **取当前目标点**
   - `target = self.path[self.target_index]`

3. **误差计算**
   - `dx = target.x - pose.x`
   - `dy = target.y - pose.y`
   - `distance = hypot(dx,dy)`
   - `target_heading = atan2(dy,dx)`
   - `heading_error = normalize_angle(target_heading - pose.theta)`

4. **到点判断**
   - 若 `distance < arrival_tolerance`：
     - `target_index += 1`
     - 若还有下一个点，继续下一段
     - 若已完成所有点：
       - 停机
       - 发布 `/arrival_flag=True`（且仅发布一次）
       - 发布完成进度文本

5. **速度控制**
   - 角速度：`angular.z = angular_gain * heading_error`
   - 线速度：与距离相关，并受 `robot_speed` 限制
   - 当角误差较大：线速度降低甚至置 0（先转向）
   - 当接近目标（`distance < slowdown_distance`）：线速度按比例减小

6. **发布控制量与进度**
   - `/turtle1/cmd_vel`
   - `/path_progress`

这是一套典型“转向优先 + 距离减速 + 阈值到点切换”的稳定控制器。

### 3.4 `main()`

同标准节点模板：init/spin/shutdown。

---

## 4) `status_monitor_node.py` 逐行讲解

### 4.1 文件作用（一句话）

把多个 topic 的分散状态聚合成统一终端仪表板，便于教学与调试。

### 4.2 顶部导入解释

- `rclpy`, `Node`：ROS2 节点基础。
- `Point`：接收机器人坐标。
- `String`：接收状态、目标房间、路径进度文本。

### 4.3 类定义：`StatusMonitorNode`

#### `__init__(self)`

1. 初始化节点名 `status_monitor_node`；
2. 初始化本地缓存变量（用于展示）：
   - `self.status`
   - `self.target_room`
   - `self.path_progress`
   - `self.position`
3. 创建订阅：
   - `/delivery_status` -> `_on_status`
   - `/current_target_room` -> `_on_target_room`
   - `/robot_position` -> `_on_position`
   - `/path_progress` -> `_on_path_progress`
4. 创建打印定时器（常见 1Hz）：回调 `_print_dashboard`。

#### `_on_status(self, msg: String)`

- 更新本地 `self.status = msg.data`。

#### `_on_target_room(self, msg: String)`

- 更新本地 `self.target_room`，为空时可显示 `-`。

#### `_on_position(self, msg: Point)`

- 缓存最新坐标 `(x,y)`。

#### `_on_path_progress(self, msg: String)`

- 缓存最新路径进度文本。

#### `_print_dashboard(self)`

- 按统一格式打印可读看板，通常包括：
  - status
  - target room
  - path stage / progress
  - robot position

这个函数不参与控制，只做“可观测性增强”。

### 4.4 `main()`

同样是标准 ROS2 Python 节点启动模板。

---

## 5) 四个节点协同关系总表（对外讲解用）

### 5.1 职责边界

1. `hotel_map_node`：只管地图绘制和初始摆位。
2. `delivery_manager_node`：只管任务/状态/路径下发/服务接口。
3. `path_motion_node`：只管路径跟踪与运动控制。
4. `status_monitor_node`：只管监控输出。

这是一种典型的**高内聚、低耦合**架构。

### 5.2 关键消息路径

- 命令入口：用户 service 调用 -> manager
- 路径执行：manager -> `/delivery_path` -> motion
- 控制闭环：motion <-> turtlesim（pose/cmd_vel）
- 状态可视：manager+motion -> monitor

### 5.3 对外讲解建议（你可直接照读）

- 第一句讲“系统目标”：模拟酒店送餐。
- 第二句讲“模块分工”：管理、控制、绘图、监视四块。
- 第三句讲“通信链路”：service 触发，topic 执行与反馈。
- 第四句讲“可维护性”：参数化+状态机+解耦。

---

## 6) 补充：如何把“每一行”讲得让听众能懂

你向他人讲代码时，可把每行归类到以下 8 类（本工程几乎都能套用）：

1. **导入行**：引入能力（消息类型/服务类型/工具函数）。
2. **参数声明行**：定义可配置项与默认值。
3. **成员变量初始化行**：定义节点运行时状态。
4. **通信接口创建行**：publisher/subscriber/service/client/timer。
5. **回调函数入口行**：收到消息或请求后的处理起点。
6. **算法计算行**：误差计算、路径构建、状态切换。
7. **消息发布/服务返回行**：向外输出结果。
8. **日志行**：辅助观测与排障。

按这个模板讲，听众会很容易把代码理解为“输入—处理—输出”的流程，而不是碎片化语句。

---

## 7) 面向讲解场景的最终结论

- 这四个节点组合，形成了一个完整的 ROS2 教学闭环：
  - 地图可视化
  - 任务服务化
  - 运动控制闭环化
  - 调试可观测化
- 代码结构清晰，职责明确，非常适合课程讲解与作业答辩。

