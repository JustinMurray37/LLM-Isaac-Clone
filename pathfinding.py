import heapq
import math
from constants import TILE_SIZE
from tile import TileType


def line_of_sight(room, x1, y1, x2, y2, ignore_gaps=False):
    """
    Returns True if no blocking tile interrupts the straight line between two
    pixel positions. Samples the ray every half-tile to avoid skipping thin walls.

    ignore_gaps=False (default): walls AND gaps block LOS — used for navigation.
    ignore_gaps=True: only walls block LOS — used for ranged attacks that can
                      fire over gaps.
    """
    dx = x2 - x1
    dy = y2 - y1
    dist = math.hypot(dx, dy)
    if dist == 0:
        return True
    steps = max(1, int(dist / (TILE_SIZE / 2)))
    for i in range(steps + 1):
        t = i / steps
        tile = room.tile_at_pixel(x1 + dx * t, y1 + dy * t)
        if ignore_gaps:
            if tile == TileType.WALL:
                return False
        else:
            if tile in (TileType.WALL, TileType.GAP):
                return False
    return True


def find_path(room, start_x, start_y, goal_x, goal_y):
    """
    A* on the tile grid from pixel start to pixel goal.
    Returns a list of pixel (x, y) waypoints (tile centres), excluding the
    starting tile. Returns [] if already in the same tile or no path exists.
    """
    sc = int(start_x) // TILE_SIZE
    sr = int(start_y) // TILE_SIZE
    gc = int(goal_x)  // TILE_SIZE
    gr = int(goal_y)  // TILE_SIZE

    if (sc, sr) == (gc, gr):
        return []

    # If the goal tile is solid the player can't be there; bail early.
    if room.is_solid(gc, gr):
        return []

    def h(c, r):
        return math.hypot(c - gc, r - gr)

    def tile_centre(c, r):
        return (c * TILE_SIZE + TILE_SIZE // 2, r * TILE_SIZE + TILE_SIZE // 2)

    # (f, tie-break counter, col, row, g)
    counter = 0
    open_heap = [(h(sc, sr), counter, sc, sr, 0.0)]
    g_best = {(sc, sr): 0.0}
    came_from = {}
    closed = set()

    while open_heap:
        _, _, c, r, g = heapq.heappop(open_heap)

        if (c, r) in closed:
            continue
        closed.add((c, r))

        if c == gc and r == gr:
            # Reconstruct path (skip the starting tile)
            path = []
            node = (c, r)
            while node in came_from:
                path.append(tile_centre(*node))
                node = came_from[node]
            path.reverse()
            return path

        for dc, dr in ((-1, 0), (1, 0), (0, -1), (0, 1),
                       (-1, -1), (-1, 1), (1, -1), (1, 1)):
            nc, nr = c + dc, r + dr
            if (nc, nr) in closed:
                continue
            if not (0 <= nc < room.cols and 0 <= nr < room.rows):
                continue
            if room.is_solid(nc, nr):
                continue
            # Block diagonal movement through wall corners
            if dc != 0 and dr != 0:
                if room.is_solid(c + dc, r) or room.is_solid(c, r + dr):
                    continue

            ng = g + math.hypot(dc, dr)
            if ng < g_best.get((nc, nr), float('inf')):
                g_best[(nc, nr)] = ng
                came_from[(nc, nr)] = (c, r)
                counter += 1
                heapq.heappush(open_heap, (ng + h(nc, nr), counter, nc, nr, ng))

    return []  # no path found
