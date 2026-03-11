"""Common data structures and helper functions for delivery_robot."""

from dataclasses import dataclass
from math import atan2, pi
from typing import Dict, List

STATE_IDLE = 'idle'
STATE_PLANNING = 'planning'
STATE_DELIVERING_TO_CORRIDOR = 'delivering_to_corridor'
STATE_MOVING_ALONG_CORRIDOR = 'moving_along_corridor'
STATE_APPROACHING_ROOM = 'approaching_room'
STATE_ARRIVED = 'arrived'
STATE_CANCELLED = 'cancelled'
STATE_ERROR = 'error'

VALID_ROOMS = ('room_101', 'room_102', 'room_103', 'room_201', 'room_202', 'room_203')


@dataclass
class Point2D:
    """Simple 2D point container."""

    x: float
    y: float


def normalize_angle(angle: float) -> float:
    """Normalize an angle in radians to [-pi, pi]."""
    while angle > pi:
        angle -= 2.0 * pi
    while angle < -pi:
        angle += 2.0 * pi
    return angle


def heading_to(from_pt: Point2D, to_pt: Point2D) -> float:
    """Compute heading angle from one point to another."""
    return atan2(to_pt.y - from_pt.y, to_pt.x - from_pt.x)


def room_positions_from_params(params: Dict[str, float]) -> Dict[str, Point2D]:
    """Build room target map from parameter dict."""
    return {
        'room_101': Point2D(params['room_101_x'], params['room_101_y']),
        'room_102': Point2D(params['room_102_x'], params['room_102_y']),
        'room_103': Point2D(params['room_103_x'], params['room_103_y']),
        'room_201': Point2D(params['room_201_x'], params['room_201_y']),
        'room_202': Point2D(params['room_202_x'], params['room_202_y']),
        'room_203': Point2D(params['room_203_x'], params['room_203_y']),
    }


def build_path_for_room(room_name: str, start: Point2D, corridor_y: float, room_map: Dict[str, Point2D]) -> List[Point2D]:
    """Create a corridor-constrained waypoint list for one room."""
    if room_name not in room_map:
        return []

    target = room_map[room_name]
    path = [
        Point2D(start.x, start.y),
        Point2D(start.x, corridor_y),
        Point2D(target.x, corridor_y),
        Point2D(target.x, target.y),
    ]

    compact_path: List[Point2D] = [path[0]]
    for pt in path[1:]:
        prev = compact_path[-1]
        if abs(prev.x - pt.x) > 1e-6 or abs(prev.y - pt.y) > 1e-6:
            compact_path.append(pt)
    return compact_path


def encode_path(path: List[Point2D]) -> str:
    """Encode waypoints to a compact topic-friendly string."""
    return ';'.join(f'{p.x:.3f},{p.y:.3f}' for p in path)


def decode_path(data: str) -> List[Point2D]:
    """Decode waypoint string into Point2D list."""
    points: List[Point2D] = []
    if not data.strip():
        return points
    for pair in data.split(';'):
        sx, sy = pair.split(',')
        points.append(Point2D(float(sx), float(sy)))
    return points
