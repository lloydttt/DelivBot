# delivery_robot 项目讲解PPT内容大纲（README_PPT）

> 用途：本文件用于指导后续 AI 或人工制作项目讲解 PPT。  
> 目标：形成一个**6部分**、逻辑完整、可直接用于答辩/课程展示的演示内容。

---

## 第1部分：项目实现效果与框架内容讲解（总览）

> 本部分来源于同目录 `README_A.md` 的提炼版：保留核心信息，弱化实现细枝末节，重点突出“系统做了什么、怎么组织、怎么跑起来”。

### 1.1 项目背景与目标

- 项目名称：`delivery_robot`
- 技术栈：ROS2 Humble + Python(rclpy) + turtlesim
- 目标：实现“酒店送餐机器人可视化仿真系统”，完整体现：
  1. Topic 通信
  2. Service 通信
  3. Parameter 参数化
  4. Launch 一键启动

### 1.2 项目实现效果（演示口径）

启动后能够看到：
1. turtlesim 窗口出现并绘制酒店地图（走廊、房间、门口、起点）；
2. 调用服务下发目标房间后，机器人按预定义路径分段移动；
3. 终端持续显示状态、目标房间、路径进度、当前坐标；
4. 支持取消任务、查询状态、复位到起点；
5. 到达房间后停留并自动回起点（按参数设定等待时长）。

### 1.3 工程框架（包级结构）

在 PPT 中建议用“分层图 + 目录树”展示：

- `delivery_robot/`
  - `delivery_robot_nodes/`：4个功能节点 + `common.py`
  - `srv/`：4个自定义服务
  - `config/hotel_params.yaml`：参数配置
  - `launch/hotel_delivery.launch.py`：一键启动
  - `README.md`：简版使用手册
  - `README_A.md`：详细架构手册

### 1.4 核心通信链路（系统路径方案）

建议用一张“节点-连线图”展示：

1. 任务入口：
   - 用户 -> `/start_delivery`（service）-> `delivery_manager_node`
2. 路径下发：
   - `delivery_manager_node` -> `/delivery_path`（topic）-> `path_motion_node`
3. 运动执行：
   - `path_motion_node` -> `/turtle1/cmd_vel` -> `turtlesim_node`
   - `turtlesim_node` -> `/turtle1/pose` -> `path_motion_node`
4. 状态反馈：
   - `path_motion_node` -> `/path_progress`、`/robot_position`、`/arrival_flag`
   - `delivery_manager_node` -> `/delivery_status`、`/current_target_room`
   - `status_monitor_node`订阅并打印看板

### 1.5 状态机总览（课堂讲解关键）

状态定义：
- `idle`
- `planning`
- `delivering_to_corridor`
- `moving_along_corridor`
- `approaching_room`
- `arrived`
- `cancelled`
- `error`

典型迁移：
- `idle -> planning -> delivering_to_corridor -> moving_along_corridor -> approaching_room -> arrived`
- 执行中取消：`* -> cancelled`
- 非法房间/路径失败：`* -> error`

### 1.6 本部分 PPT 页建议

建议 4~6 页：
1. 项目背景/目标页
2. 功能效果页（流程+截图占位）
3. 工程目录与模块页
4. 系统通信架构页
5. 状态机总览页（可选）

---

## 第2部分：Node实现方案（一）hotel_map_node

> 这一部分聚焦“地图怎么画出来”。

### 2.1 节点职责

`hotel_map_node` 负责：
1. 等待 turtlesim 绘图服务可用；
2. 将主机器人放到起点并关闭轨迹笔；
3. 生成绘图海龟 `map_drawer`；
4. 绘制走廊、房间、门口、起点区域；
5. 按参数化房间名动态标注文字。

### 2.2 涉及的服务与接口

主要使用 turtlesim service：
- `/spawn`：生成 `map_drawer`
- `/kill`：清理旧 `map_drawer`
- `/turtle1/teleport_absolute`：主机器人归位起点
- `/turtle1/set_pen`：关闭主机器人画笔
- `/<drawer>/teleport_absolute`：绘图移动
- `/<drawer>/set_pen`：控制绘图开关和线宽颜色

### 2.3 参数使用

- `start_x`, `start_y`：起点位置
- `corridor_y`：走廊 y 坐标
- `room_names`：动态房间列表
- `<room>_x`, `<room>_y`：房间门坐标

### 2.4 核心实现思路（代码讲解顺序）

PPT 建议按函数流程讲：
1. `__init__`：声明参数 -> 建 client -> wait_for_service -> `_prepare_main_robot()` -> `_draw_once_on_startup()`
2. `_prepare_main_robot`：
   - `set_pen(off=1)` 防止起始轨迹
   - `teleport_absolute(start_x,start_y)` 放置起点
3. `_spawn_drawer`：kill旧海龟并spawn新海龟，绑定其 service client
4. 绘图原语：
   - `_set_pen`
   - `_teleport`
   - `_draw_line`
   - `_draw_rectangle`
   - `_draw_text`
5. `_draw_map`：
   - 画走廊主线
   - 逐房间绘制框体/门线/标签
   - 画起点区域框

### 2.5 本节点相关 topic/service/parameter 梳理（PPT可直接表格）

- Topic：无核心业务topic发布（以 service 绘图为主）
- Service Client：如上 turtlesim 服务
- Parameter：地图布局全部参数化

### 2.6 讲解要点

- 为什么单独绘图海龟？（避免影响主机器人控制）
- 为什么先关闭 `turtle1` 画笔？（不留下非业务轨迹）
- 为什么参数化房间名？（支持后续扩展房间）

---

## 第3部分：Node实现方案（二）delivery_manager_node

> 这一部分是系统“大脑”，必须讲清楚状态机和服务逻辑。

### 3.1 节点职责

`delivery_manager_node` 负责：
1. 提供四个服务接口；
2. 管理任务生命周期与状态机；
3. 根据目标房间构建路径并发布；
4. 订阅到达标志，触发到达/回程逻辑；
5. 周期发布系统状态与当前目标房间。

### 3.2 提供的服务（Server）

1. `/start_delivery`：开始任务
2. `/cancel_delivery`：取消任务
3. `/get_delivery_status`：查询状态
4. `/reset_robot_to_start`：复位起点

### 3.3 订阅与发布的 Topic

发布：
- `/delivery_status`（状态字符串）
- `/current_target_room`（目标房间）
- `/delivery_path`（编码路径）
- `/turtle1/cmd_vel`（仅取消/复位时发停速）

订阅：
- `/arrival_flag`（执行完成通知）
- `/path_progress`（用于阶段状态更新）

### 3.4 参数使用

- 任务几何参数：`start_x/start_y/corridor_y`
- 动态房间参数：`room_names` + `<room>_x/<room>_y`
- 到达后停留参数：`return_wait_seconds`

### 3.5 关键逻辑讲解

#### A. `start_delivery` 处理流程

1. 检查当前是否忙碌；
2. 校验房间是否在 `room_names`；
3. 状态置 `planning`；
4. 调用 `build_path_for_room()` 生成去程路径；
5. 发布 `/delivery_path`；
6. 状态切到执行阶段。

#### B. `arrival_flag` 处理流程

- 首次到达目标门口：
  - 状态 -> `arrived`
  - 启动定时器等待 `return_wait_seconds`
- 定时器触发：
  - 调用 `build_return_path_from_room()`
  - 发布回程路径
  - 标记 `returning=True`
- 回程到达起点：
  - 状态 -> `idle`
  - 清空任务上下文

#### C. 取消与复位

- 取消：发零速度，清空路径与任务，状态 `cancelled`
- 复位：调用 `/turtle1/teleport_absolute` 回起点，状态恢复 `idle`

### 3.6 讲解要点

- 为什么管理节点不直接算速度？（解耦：管理 vs 控制）
- 为什么路径用 topic 下发？（运动节点可独立替换）
- 为什么状态按阶段发布？（便于教学演示与调试）

---

## 第4部分：Node实现方案（三）path_motion_node

> 这一部分讲“控制器如何让海龟稳定走路径”。

### 4.1 节点职责

`path_motion_node` 负责：
1. 接收路径字符串并解析为路径点；
2. 持续订阅 `/turtle1/pose` 获取当前位姿；
3. 按闭环控制生成 `/turtle1/cmd_vel`；
4. 发布 `/robot_position`、`/path_progress`；
5. 路径完成后发布 `/arrival_flag=True`。

### 4.2 订阅/发布的 Topic

订阅：
- `/turtle1/pose`
- `/delivery_path`

发布：
- `/turtle1/cmd_vel`
- `/robot_position`
- `/path_progress`
- `/arrival_flag`

### 4.3 参数使用（控制器核心）

- `robot_speed`：线速度上限或主速度
- `angular_gain`：角度误差的比例系数
- `arrival_tolerance`：当前目标点到达判定
- `slowdown_distance`：接近目标时减速阈值

### 4.4 核心控制流程（建议做成流程图）

每个控制周期：
1. 若无有效路径：保持停止；
2. 取当前目标路径点；
3. 计算：
   - 目标方向角 `target_yaw`
   - 角度误差 `yaw_error`
   - 距离误差 `dist`
4. 若 `dist < arrival_tolerance`：切下一个点；
5. 否则：
   - 角误差大：优先转向（线速度小/为0）
   - 角误差小：前进 + 角速度微调
   - 临近目标：按 `slowdown_distance` 降低线速度
6. 当所有点完成：停车并发布 `/arrival_flag=True`。

### 4.5 路径进度输出（教学价值）

`/path_progress` 包含：
- 当前段编号/总段数
- 当前目标点
- 误差信息（距离/角度）

这使得老师或评审能直观看到：
- 机器人是否按预期分段执行；
- 当前处于走廊阶段还是接近房间阶段。

### 4.6 讲解要点

- 闭环控制比“直给速度”更稳定；
- 路径点切换阈值如何影响抖动；
- 为什么需要“先转后走”的策略。

---

## 第5部分：Node实现方案（四）status_monitor_node

> 这一部分讲“可观测性与调试输出”。

### 5.1 节点职责

`status_monitor_node` 负责将分散在多个 topic 的信息整合成易读看板，持续打印：
- 当前状态
- 目标房间
- 路径阶段/进度
- 机器人坐标

### 5.2 订阅的 Topic

- `/delivery_status`
- `/current_target_room`
- `/robot_position`
- `/path_progress`

### 5.3 输出方式

- 以固定模板周期打印，便于演示时口头讲解；
- 统一格式可快速定位问题：
  - 状态不变 -> 可能服务未触发
  - 坐标不变 -> 可能运动控制未生效
  - path_progress 卡住 -> 可能阈值或目标点问题

### 5.4 讲解要点

- 为什么单独做监视节点，而不是散落日志？
  - 便于教学/答辩现场展示；
  - 便于对比“任务意图 vs 实际执行”。

---

## 第6部分：launch文件解释 + 项目总结与展望

### 6.1 launch 文件实现逻辑

`launch/hotel_delivery.launch.py` 负责：
1. 启动 `turtlesim_node`；
2. 启动 `hotel_map_node`（优先绘图）；
3. 通过延时动作启动管理/运动/监视节点，降低启动竞争问题；
4. 为业务节点加载统一参数文件 `config/hotel_params.yaml`。

### 6.2 启动命令与演示流程（一页可讲清）

1. 构建
```bash
colcon build --packages-select delivery_robot
```

2. source
```bash
source install/setup.bash
```

3. 启动
```bash
ros2 launch delivery_robot hotel_delivery.launch.py
```

4. 下发任务
```bash
ros2 service call /start_delivery delivery_robot/srv/StartDelivery "{room_name: 'room_102'}"
```

5. 查询/取消/复位
```bash
ros2 service call /get_delivery_status delivery_robot/srv/GetDeliveryStatus "{}"
ros2 service call /cancel_delivery delivery_robot/srv/CancelDelivery "{}"
ros2 service call /reset_robot_to_start delivery_robot/srv/ResetRobot "{}"
```

### 6.3 最终总结（一页）

可用三句话总结：
1. 本项目完成了 ROS2 基础能力（topic/service/parameter/launch）的闭环示范；
2. 采用“管理-控制-可视化”解耦架构，结构清晰、可维护、可演示；
3. 支持参数化扩展房间和布局，适合课程作业与二次开发。

### 6.4 展望（答辩加分点）

建议列 4 点：
1. 引入更复杂路径规划（A*/Dijkstra）并保留当前可解释状态机；
2. 支持多机器人调度（任务队列 + 冲突管理）；
3. 增加可视化 UI（Web Dashboard 或 RViz辅助层）；
4. 增加测试体系（节点级单元测试 + 集成测试脚本）。

---

## 附录：PPT制作建议（给AI/人工）

### A. 总体页数建议

- 第1部分：4~6页
- 第2~5部分：每部分3~5页（共12~20页）
- 第6部分：2~3页

总计建议：18~28页。

### B. 每页建议结构

- 左侧：流程图/架构图/代码片段（关键函数名）
- 右侧：3~5条解释要点（避免大段文字）
- 页脚：对应命令（可复制）

### C. 配图占位建议

1. 启动后地图全景图（走廊+房间标签）
2. 任务执行中轨迹图
3. 状态看板终端截图
4. service 调用返回结果截图

### D. 讲解节奏建议

- 先讲“做成了什么”（效果）
- 再讲“怎么组织的”（架构）
- 再讲“怎么实现的”（4个node）
- 最后讲“为什么这样设计”（总结与展望）

> 这样能保证听众即使不懂代码，也能跟上系统逻辑；懂代码的同学也能看到具体实现细节。
