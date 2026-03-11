#!/usr/bin/env python3
"""Draw a simplified hotel map in turtlesim using helper turtle."""

import time

import rclpy
from rclpy.node import Node
from turtlesim.srv import Kill, SetPen, Spawn, TeleportAbsolute


class HotelMapNode(Node):
    """Draw corridor, room blocks, doors and start zone."""

    def __init__(self) -> None:
        super().__init__('hotel_map_node')
        self.declare_parameter('map_draw_speed', 3)

        self.spawn_client = self.create_client(Spawn, '/spawn')
        self.kill_client = self.create_client(Kill, '/kill')

        self.drawer_name = 'map_drawer'
        self.teleport_client = None
        self.pen_client = None

        self.get_logger().info('waiting turtlesim drawing services...')
        self._wait_client(self.spawn_client, '/spawn')
        self._wait_client(self.kill_client, '/kill')

        # Draw once during startup (before spin loop), avoiding deadlocks that may
        # happen when blocking service calls are made from timer callbacks.
        self._draw_once_on_startup()

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
        # Try kill old drawer; ignore failures.
        try:
            self.kill_client.call_async(Kill.Request(name=self.drawer_name))
            time.sleep(0.05)
        except Exception:
            pass

        result = self._call_sync(
            self.spawn_client,
            Spawn.Request(x=1.0, y=1.0, theta=0.0, name=self.drawer_name),
        )
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

    def _draw_map(self) -> None:
        self._draw_line(1.0, 5.5, 10.5, 5.5, width=3)
        for x in (4.0, 6.2, 8.4):
            self._draw_rectangle(x, 6.4, 1.6, 1.8)
            self._draw_rectangle(x, 2.8, 1.6, 1.8)
        for door_x in (4.8, 7.0, 9.2):
            self._draw_line(door_x, 6.4, door_x, 5.8, width=4)
            self._draw_line(door_x, 4.6, door_x, 5.2, width=4)
        self._draw_rectangle(0.8, 1.2, 1.8, 1.3)


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
