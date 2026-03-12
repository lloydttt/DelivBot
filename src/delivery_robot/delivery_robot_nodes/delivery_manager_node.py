#!/usr/bin/env python3
"""Task/state manager node for hotel delivery workflow."""

from typing import Dict

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Bool, String
from turtlesim.srv import TeleportAbsolute

from delivery_robot_nodes.common import (
    STATE_APPROACHING_ROOM,
    STATE_ARRIVED,
    STATE_CANCELLED,
    STATE_DELIVERING_TO_CORRIDOR,
    STATE_ERROR,
    STATE_IDLE,
    STATE_MOVING_ALONG_CORRIDOR,
    STATE_PLANNING,
    VALID_ROOMS,
    normalize_room_names,
    Point2D,
    build_path_for_room,
    build_return_path_from_room,
    encode_path,
    room_positions_from_params,
)
from delivery_robot.srv import CancelDelivery, GetDeliveryStatus, ResetRobot, StartDelivery


class DeliveryManagerNode(Node):
    """Manage delivery task lifecycle and provide service API."""

    def __init__(self) -> None:
        super().__init__('delivery_manager_node')
        self._declare_parameters()
        self.room_names = []
        self.params = self._read_params()

        self.state = STATE_IDLE
        self.current_room = ''
        self.has_task = False
        self.returning = False
        self.active_path = []
        self.return_timer = None


        self.status_pub = self.create_publisher(String, '/delivery_status', 10)
        self.room_pub = self.create_publisher(String, '/current_target_room', 10)
        self.path_pub = self.create_publisher(String, '/delivery_path', 10)
        self.arrival_sub = self.create_subscription(Bool, '/arrival_flag', self._on_arrival, 10)
        self.path_progress_sub = self.create_subscription(String, '/path_progress', self._on_path_progress, 10)
        self.cmd_pub = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)

        self.start_srv = self.create_service(StartDelivery, '/start_delivery', self._start_delivery)
        self.cancel_srv = self.create_service(CancelDelivery, '/cancel_delivery', self._cancel_delivery)
        self.status_srv = self.create_service(GetDeliveryStatus, '/get_delivery_status', self._get_status)
        self.reset_srv = self.create_service(ResetRobot, '/reset_robot_to_start', self._reset_robot)

        self.teleport_client = self.create_client(TeleportAbsolute, '/turtle1/teleport_absolute')
        self.publish_timer = self.create_timer(0.5, self._periodic_publish)

        self.get_logger().info(f'delivery_manager_node ready. valid rooms={self.room_names}')


    def _declare_if_needed(self, name: str, default_value) -> None:
        """Declare parameter only when it is not declared yet."""
        if not self.has_parameter(name):
            self.declare_parameter(name, default_value)

    def _declare_parameters(self) -> None:
        self._declare_if_needed('start_x', 0.8)
        self._declare_if_needed('start_y', 1.0)
        self._declare_if_needed('corridor_y', 5.5)
        self._declare_if_needed('return_wait_seconds', 2.0)
        self._declare_if_needed('room_names', list(VALID_ROOMS))
        for room in VALID_ROOMS:
            self._declare_if_needed(f'{room}_x', 5.0)
            self._declare_if_needed(f'{room}_y', 5.0)

    def _read_params(self) -> Dict[str, float]:
        self.room_names = normalize_room_names(list(self.get_parameter('room_names').value))

        for room in self.room_names:
            self._declare_if_needed(f'{room}_x', 5.0)
            self._declare_if_needed(f'{room}_y', 5.0)

        values = {
            'start_x': float(self.get_parameter('start_x').value),
            'start_y': float(self.get_parameter('start_y').value),
            'corridor_y': float(self.get_parameter('corridor_y').value),
            'return_wait_seconds': float(self.get_parameter('return_wait_seconds').value),
        }
        for room in self.room_names:
            values[f'{room}_x'] = float(self.get_parameter(f'{room}_x').value)
            values[f'{room}_y'] = float(self.get_parameter(f'{room}_y').value)
        return values

    def _set_state(self, new_state: str) -> None:
        if self.state != new_state:
            self.get_logger().info(f'state transition: {self.state} -> {new_state}')
            self.state = new_state


    def _periodic_publish(self) -> None:
        status = String()
        status.data = self.state
        self.status_pub.publish(status)
        room = String()
        room.data = self.current_room
        self.room_pub.publish(room)

    def _start_delivery(self, request: StartDelivery.Request, response: StartDelivery.Response) -> StartDelivery.Response:
        room_name = request.room_name.strip().lower()
        self.get_logger().info(f'received start_delivery request: room={room_name}')

        if self.has_task and self.state not in (STATE_ARRIVED, STATE_CANCELLED, STATE_ERROR, STATE_IDLE):
            response.success = False
            response.message = f'Robot busy in state={self.state}'
            return response

        if room_name not in self.room_names:
            self._set_state(STATE_ERROR)
            response.success = False
            response.message = f'Invalid room name: {room_name}'
            return response

        self._set_state(STATE_PLANNING)
        room_map = room_positions_from_params(self.params, self.room_names)
        start = Point2D(self.params['start_x'], self.params['start_y'])
        path = build_path_for_room(room_name, start, self.params['corridor_y'], room_map)
        if not path:
            self._set_state(STATE_ERROR)
            response.success = False
            response.message = 'Failed to build a path.'
            return response

        self.current_room = room_name
        self.active_path = path
        self.has_task = True
        self.returning = False

        path_msg = String()
        path_msg.data = encode_path(path)
        self.path_pub.publish(path_msg)
        self.get_logger().info(f'path for {room_name}: {path_msg.data}')

        self._set_state(STATE_DELIVERING_TO_CORRIDOR)
        response.success = True
        response.message = f'Delivery started for {room_name}'
        return response

    def _on_path_progress(self, msg: String) -> None:
        if 'segment 2/' in msg.data:
            self._set_state(STATE_MOVING_ALONG_CORRIDOR)
        elif 'segment 3/' in msg.data:
            self._set_state(STATE_APPROACHING_ROOM)

    def _schedule_return_to_start(self) -> None:
        """Wait briefly at destination then send a return path to start."""
        wait_sec = max(0.0, float(self.params['return_wait_seconds']))
        self.get_logger().info(f'arrived at {self.current_room}, waiting {wait_sec:.1f}s before return')
        if self.return_timer is not None:
            self.return_timer.cancel()
        self.return_timer = self.create_timer(wait_sec, self._start_return_once)

    def _start_return_once(self) -> None:
        if self.return_timer is not None:
            self.return_timer.cancel()
            self.return_timer = None

        if self.state != STATE_ARRIVED or not self.has_task or self.returning:
            return
        room_map = room_positions_from_params(self.params, self.room_names)
        start = Point2D(self.params['start_x'], self.params['start_y'])
        return_path = build_return_path_from_room(self.current_room, start, self.params['corridor_y'], room_map)
        if len(return_path) <= 1:
            self.get_logger().error('failed to build return path; keeping robot at current position')
            return
        self.returning = True
        msg = String()
        msg.data = encode_path(return_path)
        self.path_pub.publish(msg)
        self._set_state(STATE_DELIVERING_TO_CORRIDOR)
        self.get_logger().info(f'return path to start published: {msg.data}')

    def _on_arrival(self, msg: Bool) -> None:
        if not msg.data or not self.has_task:
            return

        if self.returning:
            self._set_state(STATE_IDLE)
            self.get_logger().info('robot returned to start, task completed')
            self.current_room = ''
            self.has_task = False
            self.active_path = []
            self.returning = False
            if self.return_timer is not None:
                self.return_timer.cancel()
                self.return_timer = None
            return

        self._set_state(STATE_ARRIVED)
        self._schedule_return_to_start()

    def _cancel_delivery(self, _: CancelDelivery.Request, response: CancelDelivery.Response) -> CancelDelivery.Response:
        if not self.has_task or self.state in (STATE_IDLE, STATE_CANCELLED):
            response.success = False
            response.message = 'No active delivery to cancel.'
            return response

        self._set_state(STATE_CANCELLED)
        stop = Twist()
        self.cmd_pub.publish(stop)
        self.path_pub.publish(String(data=''))
        self.has_task = False
        self.returning = False
        if self.return_timer is not None:
            self.return_timer.cancel()
            self.return_timer = None
        response.success = True
        response.message = 'Delivery cancelled.'
        return response

    def _get_status(self, _: GetDeliveryStatus.Request, response: GetDeliveryStatus.Response) -> GetDeliveryStatus.Response:
        response.status = self.state
        response.current_room = self.current_room
        response.has_task = self.has_task
        return response

    def _reset_robot(self, _: ResetRobot.Request, response: ResetRobot.Response) -> ResetRobot.Response:
        self.get_logger().info('reset_robot_to_start requested')
        if not self.teleport_client.wait_for_service(timeout_sec=2.0):
            response.success = False
            response.message = 'teleport service unavailable'
            return response
        stop = Twist()
        self.cmd_pub.publish(stop)

        req = TeleportAbsolute.Request()
        req.x = float(self.params['start_x'])
        req.y = float(self.params['start_y'])
        req.theta = 0.0
        future = self.teleport_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)
        if future.result() is None:
            response.success = False
            response.message = 'reset failed: teleport call timeout'
            return response

        self.current_room = ''
        self.has_task = False
        self.returning = False
        if self.return_timer is not None:
            self.return_timer.cancel()
            self.return_timer = None
        self._set_state(STATE_IDLE)
        response.success = True
        response.message = 'Robot reset to start point.'
        return response


def main() -> None:
    rclpy.init()
    node = DeliveryManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
