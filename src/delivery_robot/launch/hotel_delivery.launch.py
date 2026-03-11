"""Launch all nodes required for the hotel delivery turtlesim demo."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    pkg_share = get_package_share_directory('delivery_robot')
    params_file = os.path.join(pkg_share, 'config', 'hotel_params.yaml')

    # Use Qt geometry argument to set actual window resolution (not just DPI scaling).
    geometry_arg = DeclareLaunchArgument(
        'turtlesim_window_geometry',
        default_value='1400x1400+80+80',
        description='Qt window geometry for turtlesim: <width>x<height>+<x>+<y>.',
    )


    # Optional UI scale factor for desktop environments where -geometry is ignored by window manager.
    scale_arg = DeclareLaunchArgument(
        'turtlesim_window_scale',
        default_value='1.0',
        description='UI scale factor hint (does not change turtlesim world size).',
    )

    turtlesim = Node(
        package='turtlesim',
        executable='turtlesim_node',
        name='turtlesim_node',
        output='screen',
        arguments=['-geometry', LaunchConfiguration('turtlesim_window_geometry')],
        additional_env={'QT_SCALE_FACTOR': LaunchConfiguration('turtlesim_window_scale')},
    )
    map_node = Node(package='delivery_robot', executable='hotel_map_node.py', name='hotel_map_node', output='screen', parameters=[params_file])

    # Delay functional nodes slightly so map drawing is likely finished first.
    delayed_nodes = TimerAction(
        period=2.5,
        actions=[
            Node(package='delivery_robot', executable='delivery_manager_node.py', name='delivery_manager_node', output='screen', parameters=[params_file]),
            Node(package='delivery_robot', executable='path_motion_node.py', name='path_motion_node', output='screen', parameters=[params_file]),
            Node(package='delivery_robot', executable='status_monitor_node.py', name='status_monitor_node', output='screen', parameters=[params_file]),
        ],
    )

    info1 = LogInfo(msg=['[delivery_robot] turtlesim_window_geometry=', LaunchConfiguration('turtlesim_window_geometry')])
    info2 = LogInfo(msg=['[delivery_robot] turtlesim_window_scale=', LaunchConfiguration('turtlesim_window_scale')])

    return LaunchDescription([geometry_arg, scale_arg, info1, info2, turtlesim, map_node, delayed_nodes])
