# delivery_robot

基于 **ROS2 Humble + turtlesim** 的酒店送餐机器人可视化仿真课程项目。

## 1. 项目简介
- 使用 turtle1 作为送餐机器人。
- 使用辅助海龟自动绘制酒店地图（走廊、房间、门口、起点）。
- 支持基于服务接口的任务控制（开始/取消/查询/复位）。
- 路径采用预定义走廊路径点，便于调试与展示。
- 到达房门后会停留 `return_wait_seconds` 秒，然后自动返回起点。

## 2. 功能说明
- Topic：位姿、速度控制、状态、路径进度、到达标记。
- Service：`/start_delivery`、`/cancel_delivery`、`/get_delivery_status`、`/reset_robot_to_start`。
- Parameter + YAML：速度参数、地图参数、房间坐标参数全部可配置。
- Launch：一键启动所有节点。

## 3. 目录结构
```text
delivery_robot/
├── CMakeLists.txt
├── package.xml
├── setup.py
├── setup.cfg
├── resource/
│   └── delivery_robot
├── delivery_robot_nodes/
│   ├── __init__.py
│   ├── common.py
│   ├── hotel_map_node.py
│   ├── delivery_manager_node.py
│   ├── path_motion_node.py
│   └── status_monitor_node.py
├── srv/
│   ├── StartDelivery.srv
│   ├── CancelDelivery.srv
│   ├── GetDeliveryStatus.srv
│   └── ResetRobot.srv
├── config/
│   └── hotel_params.yaml
├── launch/
│   └── hotel_delivery.launch.py
└── README.md
```

## 4. 环境要求
- Ubuntu
- ROS2 Humble
- Python 3
- colcon
- 已安装：`turtlesim`, `geometry_msgs`, `std_msgs`, `std_srvs`, `rclpy`

## 5. 构建方法
```bash
cd ~/your_ws
colcon build --packages-select delivery_robot
```

## 6. 运行方法
```bash
source install/setup.bash
ros2 launch delivery_robot hotel_delivery.launch.py
```

## 7. Service 测试命令
```bash
ros2 service call /start_delivery delivery_robot/srv/StartDelivery "{room_name: 'room_102'}"
ros2 service call /get_delivery_status delivery_robot/srv/GetDeliveryStatus "{}"
ros2 service call /cancel_delivery delivery_robot/srv/CancelDelivery "{}"
ros2 service call /reset_robot_to_start delivery_robot/srv/ResetRobot "{}"
```

## 8. Topic 查看命令
```bash
ros2 topic echo /delivery_status
ros2 topic echo /current_target_room
ros2 topic echo /robot_position
ros2 topic echo /path_progress
ros2 topic echo /arrival_flag
```

## 9. Parameter 查看命令
```bash
ros2 param list
ros2 param get /path_motion_node robot_speed
ros2 param get /delivery_manager_node corridor_y
```

## 10. 常见问题排查
1. **服务调用超时**：确认 `ros2 node list` 中五个节点都已启动。
2. **机器人不动**：检查 `/delivery_path` 是否有消息、`/turtle1/pose` 是否正常。
3. **地图未绘制**：确认 turtlesim 服务存在：`ros2 service list | grep spawn`。
4. **房间号错误**：仅支持 `room_names` 参数中声明的房间名。
5. **`QImage::pixel out of range` 警告**：`turtlesim` 窗口尺寸是固定的，不能在 launch 中直接调大；请把房间坐标控制在 0.6~10.4 范围内（本项目已自动做边界保护和默认坐标优化）。

## 11. 参数化房间命名与位置
- 在 `config/hotel_params.yaml` 中通过 `room_names` 配置房间列表，系统会按该列表动态读取 `<room_name>_x/<room_name>_y`，并在地图上标注对应房间号。
- 例如新增 `vip_a`：将 `room_names` 改为包含 `"vip_a"`，并增加 `vip_a_x` 与 `vip_a_y` 参数。
- 起点由 `start_x/start_y` 控制，已默认放到左下远处，避免初始就在走廊中间。
- 通过调大房间坐标间距（本仓库默认已拉大）可减少房间号文字重叠。
- 可通过 `return_wait_seconds` 控制到房间后停留时长。

## 12. 调试建议
- 观察 `status_monitor_node` 的调试仪表板输出。
- 使用 `ros2 topic echo /path_progress` 看路径段与误差变化。
- 动态调参：`robot_speed`、`angular_gain`、`arrival_tolerance`。

## 13. 演示流程建议
1. 启动 launch。
2. 调用 `/start_delivery` 下发目标房间。
3. 展示状态机阶段切换：`idle -> planning -> ... -> arrived`。
4. 演示 `/cancel_delivery` 与 `/reset_robot_to_start`。

## 14. 易错点
- 自定义 srv 未编译（需要先 `colcon build` 再 `source install/setup.bash`）。
- 启动前未 source 工作区。
- 路径为空时管理器会拒绝任务。
