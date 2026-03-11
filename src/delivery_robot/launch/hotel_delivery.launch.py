"""Launch all nodes required for the hotel delivery turtlesim demo."""

import os

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, LogInfo, OpaqueFunction, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _create_turtlesim_action(_context):
    """Prefer workspace-local turtlesim executable to avoid using system-installed binary."""
    turtlesim_prefix = get_package_prefix('turtlesim')
    install_root = os.path.dirname(turtlesim_prefix)
    local_turtlesim_exe = os.path.join(install_root, 'turtlesim', 'lib', 'turtlesim', 'turtlesim_node')

    geometry = LaunchConfiguration('turtlesim_window_geometry')

    if os.path.exists(local_turtlesim_exe):
        return [
            LogInfo(msg=f'[delivery_robot] using local turtlesim executable: {local_turtlesim_exe}'),
            ExecuteProcess(
                cmd=[
                    local_turtlesim_exe,
                    '--ros-args',
                    '-r',
                    '__node:=turtlesim_node',
                    '-geometry',
                    geometry,
                    '-qwindowgeometry',
                    geometry,
                ],
                name='turtlesim_node',
                output='screen',
            ),
        ]

    return [
        LogInfo(msg='[delivery_robot] local turtlesim executable not found; fallback to package launcher.'),
        Node(
            package='turtlesim',
            executable='turtlesim_node',
            name='turtlesim_node',
            output='screen',
            arguments=[
                '-geometry',
                geometry,
                '-qwindowgeometry',
                geometry,
            ],
        ),
    ]


def generate_launch_description() -> LaunchDescription:
    pkg_share = get_package_share_directory('delivery_robot')
    params_file = os.path.join(pkg_share, 'config', 'hotel_params.yaml')

    geometry_arg = DeclareLaunchArgument(
        'turtlesim_window_geometry',
        default_value='1400x1400+80+80',
        description='Qt window geometry for turtlesim: <width>x<height>+<x>+<y>.',
    )

    map_node = Node(package='delivery_robot', executable='hotel_map_node.py', name='hotel_map_node', output='screen', parameters=[params_file])

    delayed_nodes = TimerAction(
        period=2.5,
        actions=[
            Node(package='delivery_robot', executable='delivery_manager_node.py', name='delivery_manager_node', output='screen', parameters=[params_file]),
            Node(package='delivery_robot', executable='path_motion_node.py', name='path_motion_node', output='screen', parameters=[params_file]),
            Node(package='delivery_robot', executable='status_monitor_node.py', name='status_monitor_node', output='screen', parameters=[params_file]),
        ],
    )

    info = LogInfo(msg=['[delivery_robot] turtlesim_window_geometry=', LaunchConfiguration('turtlesim_window_geometry')])
    turtlesim_action = OpaqueFunction(function=_create_turtlesim_action)

    return LaunchDescription([geometry_arg, info, turtlesim_action, map_node, delayed_nodes])
