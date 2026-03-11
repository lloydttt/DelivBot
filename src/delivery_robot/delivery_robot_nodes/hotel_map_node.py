#!/usr/bin/env python3
"""Draw a simplified hotel map in turtlesim using helper turtle."""

import time
from typing import Dict, List, Tuple

import rclpy
from rclpy.node import Node
from turtlesim.srv import Kill, SetPen, Spawn, TeleportAbsolute

from delivery_robot_nodes.common import Point2D, VALID_ROOMS, normalize_room_names, room_positions_from_params

# Very small vector-font strokes in normalized [0,1] coordinates.
# Each char is a list of line segments: ((x1, y1), (x2, y2))
FONT: Dict[str, List[Tuple[Tuple[float, float], Tuple[float, float]]]] = {
    '0': [((0, 0), (1, 0)), ((1, 0), (1, 1)), ((1, 1), (0, 1)), ((0, 1), (0, 0))],
    '1': [((0.5, 0), (0.5, 1))],
    '2': [((0, 1), (1, 1)), ((1, 1), (1, 0.5)), ((1, 0.5), (0, 0.5)), ((0, 0.5), (0, 0)), ((0, 0), (1, 0))],
    '3': [((0, 1), (1, 1)), ((1, 1), (1, 0)), ((0, 0.5), (1, 0.5)), ((0, 0), (1, 0))],
    '4': [((0, 1), (0, 0.5)), ((0, 0.5), (1, 0.5)), ((1, 1), (1, 0))],
    '5': [((1, 1), (0, 1)), ((0, 1), (0, 0.5)), ((0, 0.5), (1, 0.5)), ((1, 0.5), (1, 0)), ((1, 0), (0, 0))],
    '6': [((1, 1), (0, 0.5)), ((0, 0.5), (0, 0)), ((0, 0), (1, 0)), ((1, 0), (1, 0.5)), ((1, 0.5), (0, 0.5))],
    '7': [((0, 1), (1, 1)), ((1, 1), (0.4, 0))],
    '8': [((0, 0), (1, 0)), ((1, 0), (1, 1)), ((1, 1), (0, 1)), ((0, 1), (0, 0)), ((0, 0.5), (1, 0.5))],
    '9': [((1, 0.5), (0, 1)), ((0, 1), (1, 1)), ((1, 1), (1, 0)), ((1, 0), (0, 0))],
    'R': [((0, 0), (0, 1)), ((0, 1), (0.8, 1)), ((0.8, 1), (0.8, 0.5)), ((0.8, 0.5), (0, 0.5)), ((0, 0.5), (1, 0))],
    'O': [((0, 0), (1, 0)), ((1, 0), (1, 1)), ((1, 1), (0, 1)), ((0, 1), (0, 0))],
    'M': [((0, 0), (0, 1)), ((0, 1), (0.5, 0.5)), ((0.5, 0.5), (1, 1)), ((1, 1), (1, 0))],
    '_': [((0, 0), (1, 0))],
}


class HotelMapNode(Node):
    """Draw corridor, room blocks, doors and start zone with room labels."""

    def __init__(self) -> None:
        super().__init__('hotel_map_node')
        self._declare_parameters()
        self.params = self._read_params()

        self.spawn_client = self.create_client(Spawn, '/spawn')
        self.kill_client = self.create_client(Kill, '/kill')

        self.drawer_name = 'map_drawer'
        self.teleport_client = None
        self.pen_client = None

        self.get_logger().info('waiting turtlesim drawing services...')
        self._wait_client(self.spawn_client, '/spawn')
        self._wait_client(self.kill_client, '/kill')
        self._draw_once_on_startup()

    def _declare_parameters(self) -> None:
        self.declare_parameter('start_x', 0.8)
        self.declare_parameter('start_y', 1.0)
        self.declare_parameter('corridor_y', 5.5)
        self.declare_parameter('room_names', list(VALID_ROOMS))
        for room in VALID_ROOMS:
            self.declare_parameter(f'{room}_x', 5.0)
            self.declare_parameter(f'{room}_y', 5.0)

    def _read_params(self) -> Dict[str, float]:
        room_names = normalize_room_names(list(self.get_parameter('room_names').value))
        for room in room_names:
            self.declare_parameter(f'{room}_x', 5.0)
            self.declare_parameter(f'{room}_y', 5.0)

        values: Dict[str, float] = {
            'start_x': float(self.get_parameter('start_x').value),
            'start_y': float(self.get_parameter('start_y').value),
            'corridor_y': float(self.get_parameter('corridor_y').value),
        }
        values['room_names'] = room_names  # type: ignore[assignment]
        for room in room_names:
            values[f'{room}_x'] = float(self.get_parameter(f'{room}_x').value)
            values[f'{room}_y'] = float(self.get_parameter(f'{room}_y').value)
        return values

    def _wait_client(self, client, name: str) -> None:
        while not client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn(f'service {name} not ready, retrying...')

    def _call_sync(self, client, req, timeout: float = 3.0):
        future = client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout)
        if not future.done() or future.result() is None:
            raise RuntimeError(f'service call timeout: {client.srv_name}')
        return future.result()

    def _draw_once_on_startup(self) -> None:
        self.get_logger().info('start drawing hotel map')
        try:
            self._spawn_drawer()
            self._draw_map()
            self.get_logger().info('hotel map drawing completed')
        except Exception as exc:
            self.get_logger().error(f'hotel map drawing failed: {exc}')

    def _spawn_drawer(self) -> None:
        try:
            self.kill_client.call_async(Kill.Request(name=self.drawer_name))
            time.sleep(0.05)
        except Exception:
            pass

        result = self._call_sync(self.spawn_client, Spawn.Request(x=1.0, y=1.0, theta=0.0, name=self.drawer_name))
        self.drawer_name = result.name

        self.teleport_client = self.create_client(TeleportAbsolute, f'/{self.drawer_name}/teleport_absolute')
        self.pen_client = self.create_client(SetPen, f'/{self.drawer_name}/set_pen')
        self._wait_client(self.teleport_client, f'/{self.drawer_name}/teleport_absolute')
        self._wait_client(self.pen_client, f'/{self.drawer_name}/set_pen')

    def _set_pen(self, r: int, g: int, b: int, width: int, off: bool) -> None:
        self._call_sync(self.pen_client, SetPen.Request(r=r, g=g, b=b, width=width, off=int(off)))

    def _teleport(self, x: float, y: float, theta: float = 0.0) -> None:
        self._call_sync(self.teleport_client, TeleportAbsolute.Request(x=x, y=y, theta=theta))

    def _draw_line(self, x1: float, y1: float, x2: float, y2: float, width: int = 2) -> None:
        self._set_pen(30, 30, 30, width, True)
        self._teleport(x1, y1)
        self._set_pen(30, 30, 30, width, False)
        self._teleport(x2, y2)

    def _draw_rectangle(self, x: float, y: float, w: float, h: float) -> None:
        self._draw_line(x, y, x + w, y)
        self._draw_line(x + w, y, x + w, y + h)
        self._draw_line(x + w, y + h, x, y + h)
        self._draw_line(x, y + h, x, y)

    def _draw_text(self, text: str, x: float, y: float, scale: float = 0.22, spacing: float = 0.10) -> None:
        """Draw text using simple line strokes."""
        cursor_x = x
        for ch in text.upper():
            glyph = FONT.get(ch)
            if glyph is None:
                cursor_x += scale + spacing
                continue
            for (x1, y1), (x2, y2) in glyph:
                self._draw_line(
                    cursor_x + x1 * scale,
                    y + y1 * scale,
                    cursor_x + x2 * scale,
                    y + y2 * scale,
                    width=2,
                )
            cursor_x += scale + spacing

    def _draw_room_and_label(self, room_name: str, door: Point2D, corridor_y: float) -> None:
        room_w = 1.4
        room_h = 1.6
        door_len = 0.5

        upper = door.y >= corridor_y
        rect_x = max(0.3, min(door.x - room_w / 2.0, 10.7 - room_w))
        rect_y = door.y + 0.4 if upper else door.y - 0.4 - room_h
        rect_y = max(0.3, min(rect_y, 10.7 - room_h))

        self._draw_rectangle(rect_x, rect_y, room_w, room_h)
        if upper:
            self._draw_line(door.x, rect_y, door.x, door.y - door_len * 0.5, width=4)
            text_y = min(10.6, rect_y + room_h + 0.1)
        else:
            self._draw_line(door.x, rect_y + room_h, door.x, door.y + door_len * 0.5, width=4)
            text_y = max(0.2, rect_y - 0.35)

        text_x = max(0.2, min(10.0, door.x - 0.45))
        self._draw_text(room_name, text_x, text_y)

    def _draw_map(self) -> None:
        start_x = float(self.params['start_x'])
        start_y = float(self.params['start_y'])
        corridor_y = float(self.params['corridor_y'])
        room_names = self.params['room_names']
        room_map = room_positions_from_params(self.params, room_names)

        self._draw_line(1.0, corridor_y, 10.5, corridor_y, width=3)
        for room_name, door in room_map.items():
            self._draw_room_and_label(room_name, door, corridor_y)

        # Start zone moved with start parameters so turtle starts far from corridor.
        self._draw_rectangle(max(0.2, start_x - 0.8), max(0.2, start_y - 0.6), 1.6, 1.2)


def main() -> None:
    rclpy.init()
    node = HotelMapNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
