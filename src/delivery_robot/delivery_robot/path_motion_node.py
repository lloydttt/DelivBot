#!/usr/bin/env python3
"""Path following and closed-loop controller for turtle robot."""

from math import hypot
from typing import List, Optional

import rclpy
from geometry_msgs.msg import Point, Twist
from rclpy.node import Node
from std_msgs.msg import Bool, String
from turtlesim.msg import Pose

from delivery_robot.common import Point2D, decode_path, heading_to, normalize_angle


class PathMotionNode(Node):
    """Follow pre-defined waypoints published by delivery_manager_node."""

    def __init__(self) -> None:
        super().__init__('path_motion_node')
        self._declare_parameters()
        self.speed = float(self.get_parameter('robot_speed').value)
        self.angular_gain = float(self.get_parameter('angular_gain').value)
        self.arrival_tolerance = float(self.get_parameter('arrival_tolerance').value)
        self.slowdown_distance = float(self.get_parameter('slowdown_distance').value)
        self.debug_path = bool(self.get_parameter('show_debug_path').value)

        self.pose: Optional[Pose] = None
        self.path: List[Point2D] = []
        self.index = 0
        self.active = False

        self.cmd_pub = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)
        self.position_pub = self.create_publisher(Point, '/robot_position', 10)
        self.progress_pub = self.create_publisher(String, '/path_progress', 10)
        self.arrival_pub = self.create_publisher(Bool, '/arrival_flag', 10)

        self.pose_sub = self.create_subscription(Pose, '/turtle1/pose', self._on_pose, 20)
        self.path_sub = self.create_subscription(String, '/delivery_path', self._on_path, 10)
        self.timer = self.create_timer(0.05, self._control_loop)

        self.get_logger().info('path_motion_node ready.')

    def _declare_parameters(self) -> None:
        self.declare_parameter('robot_speed', 1.4)
        self.declare_parameter('angular_gain', 4.0)
        self.declare_parameter('arrival_tolerance', 0.12)
        self.declare_parameter('slowdown_distance', 0.7)
        self.declare_parameter('show_debug_path', True)

    def _on_pose(self, msg: Pose) -> None:
        self.pose = msg
        p = Point(x=msg.x, y=msg.y, z=0.0)
        self.position_pub.publish(p)

    def _on_path(self, msg: String) -> None:
        try:
            parsed = decode_path(msg.data)
        except Exception as exc:
            self.get_logger().error(f'failed to decode path: {exc}')
            return

        self.path = parsed
        if len(self.path) <= 1:
            self.active = False
            self.index = 0
            self._publish_stop(arrived=False)
            self.get_logger().info('path cleared or invalid; robot stopped')
            return

        self.index = 1
        self.active = True
        self.arrival_pub.publish(Bool(data=False))
        self.get_logger().info(f'new path received with {len(self.path)} points')
        if self.debug_path:
            self.get_logger().info(f'path detail: {msg.data}')

    def _publish_stop(self, arrived: bool) -> None:
        self.cmd_pub.publish(Twist())
        self.arrival_pub.publish(Bool(data=arrived))

    def _control_loop(self) -> None:
        if not self.active or self.pose is None or not self.path:
            return

        if self.index >= len(self.path):
            self.active = False
            self._publish_stop(arrived=True)
            self.progress_pub.publish(String(data='arrived: all waypoints completed'))
            return

        pose_pt = Point2D(self.pose.x, self.pose.y)
        target = self.path[self.index]
        dx = target.x - pose_pt.x
        dy = target.y - pose_pt.y
        distance = hypot(dx, dy)

        total_segments = max(len(self.path) - 1, 1)
        progress = String()
        progress.data = (
            f'segment {self.index}/{total_segments} | '
            f'current=({pose_pt.x:.2f},{pose_pt.y:.2f}) -> target=({target.x:.2f},{target.y:.2f}) | dist={distance:.3f}'
        )
        self.progress_pub.publish(progress)

        if distance < self.arrival_tolerance:
            self.index += 1
            self.cmd_pub.publish(Twist())
            return

        desired = heading_to(pose_pt, target)
        angle_error = normalize_angle(desired - self.pose.theta)

        cmd = Twist()
        cmd.angular.z = max(min(self.angular_gain * angle_error, 2.5), -2.5)
        if abs(angle_error) > 0.45:
            cmd.linear.x = 0.0
        else:
            linear = min(self.speed, self.speed * (distance / max(self.slowdown_distance, 1e-3)))
            cmd.linear.x = max(0.15, linear)
        self.cmd_pub.publish(cmd)


def main() -> None:
    rclpy.init()
    node = PathMotionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
