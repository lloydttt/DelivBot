"""Launch all nodes required for the hotel delivery turtlesim demo."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import TimerAction
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    pkg_share = get_package_share_directory('delivery_robot')
    params_file = os.path.join(pkg_share, 'config', 'hotel_params.yaml')

    turtlesim = Node(
        package='turtlesim',
        executable='turtlesim_node',
        name='turtlesim_node',
        output='screen',
    )
    map_node = Node(
        package='delivery_robot',
        executable='hotel_map_node.py',
        name='hotel_map_node',
        output='screen',
        parameters=[params_file],
    )

    delayed_nodes = TimerAction(
        period=2.5,
        actions=[
            Node(package='delivery_robot', executable='delivery_manager_node.py', name='delivery_manager_node', output='screen', parameters=[params_file]),
            Node(package='delivery_robot', executable='path_motion_node.py', name='path_motion_node', output='screen', parameters=[params_file]),
            Node(package='delivery_robot', executable='status_monitor_node.py', name='status_monitor_node', output='screen', parameters=[params_file]),
        ],
    )

    return LaunchDescription([turtlesim, map_node, delayed_nodes])
