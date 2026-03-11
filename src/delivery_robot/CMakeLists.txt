cmake_minimum_required(VERSION 3.8)
project(delivery_robot)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "srv/StartDelivery.srv"
  "srv/CancelDelivery.srv"
  "srv/GetDeliveryStatus.srv"
  "srv/ResetRobot.srv"
)

ament_python_install_package(delivery_robot_nodes)

install(PROGRAMS
  delivery_robot_nodes/hotel_map_node.py
  delivery_robot_nodes/delivery_manager_node.py
  delivery_robot_nodes/path_motion_node.py
  delivery_robot_nodes/status_monitor_node.py
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY
  launch
  config
  DESTINATION share/${PROJECT_NAME}
)

install(FILES
  resource/${PROJECT_NAME}
  DESTINATION share/ament_index/resource_index/packages
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
