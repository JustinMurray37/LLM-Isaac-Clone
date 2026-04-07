from enum import IntEnum


class TileType(IntEnum):
    FLOOR       = 0
    WALL        = 1
    GAP         = 2
    SPIKE       = 3
    SPIKE_TIMED = 4


# Base color used when drawing each tile type
TILE_COLORS = {
    TileType.FLOOR:       (98,  72,  45),   # walkable floor (wood base)
    TileType.WALL:        (30,  28,  26),   # dark mortar/crevice between stones
    TileType.GAP:         (15,  15,  20),   # hole in the floor
    TileType.SPIKE:       (98,  72,  45),   # same floor background — triangles drawn on top
    TileType.SPIKE_TIMED: (98,  72,  45),   # same — triangles animate up/down
}
