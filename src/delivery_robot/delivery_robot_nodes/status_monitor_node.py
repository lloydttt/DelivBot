#!/usr/bin/env python3
"""Terminal-friendly monitor node for demo and debugging."""

from geometry_msgs.msg import Point
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class StatusMonitorNode(Node):
    """Aggregate status topics and print formatted diagnostics."""

    def __init__(self) -> None:
        super().__init__('status_monitor_node')
        self.declare_parameter('enable_status_log', True)
        self.enabled = bool(self.get_parameter('enable_status_log').value)

        self.status = 'unknown'
        self.room = '-'
        self.path_progress = 'waiting path...'
        self.pos = Point()

        self.create_subscription(String, '/delivery_status', self._on_status, 10)
        self.create_subscription(String, '/current_target_room', self._on_room, 10)
        self.create_subscription(String, '/path_progress', self._on_progress, 10)
        self.create_subscription(Point, '/robot_position', self._on_position, 20)
        self.timer = self.create_timer(1.0, self._print_board)

    def _on_status(self, msg: String) -> None:
        self.status = msg.data

    def _on_room(self, msg: String) -> None:
        self.room = msg.data if msg.data else '-'

    def _on_progress(self, msg: String) -> None:
        self.path_progress = msg.data

    def _on_position(self, msg: Point) -> None:
        self.pos = msg

    def _print_board(self) -> None:
        if not self.enabled:
            return
        block = (
            '\n========== DELIVERY DEBUG DASHBOARD ==========' +
            f'\nstatus         : {self.status}' +
            f'\ntarget room    : {self.room}' +
            f'\npath stage     : {self.path_progress}' +
            f'\nrobot position : ({self.pos.x:.2f}, {self.pos.y:.2f})' +
            '\n=============================================\n'
        )
        self.get_logger().info(block)


def main() -> None:
    rclpy.init()
    node = StatusMonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
