from enum import IntEnum


class TileType(IntEnum):
    FLOOR        = 0
    WALL         = 1
    GAP          = 2
    SPIKE        = 3
    SPIKE_TIMED  = 4
    CRACKED_WALL = 5


# Base color used when drawing each tile type
TILE_COLORS = {
    TileType.FLOOR:        (98,  72,  45),
    TileType.WALL:         (30,  28,  26),
    TileType.GAP:          (15,  15,  20),
    TileType.SPIKE:        (98,  72,  45),
    TileType.SPIKE_TIMED:  (98,  72,  45),
    TileType.CRACKED_WALL: (30,  28,  26),
}
