import random
from room import Room
from tile import TileType
from items import ITEMS
from enemies import ENEMIES
from constants import TILE_SIZE, TESTING_MODE

# Pixel centre of tile (col, row)
def _tc(col, row):
    return col * TILE_SIZE + TILE_SIZE // 2, row * TILE_SIZE + TILE_SIZE // 2

# Cardinal directions and grid offsets used by the generator
_OFFSET = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


# ---------------------------------------------------------------------------
# Flip helper
# ---------------------------------------------------------------------------

def _flip_room(room, flip_x, flip_y):
    """
    Mirror a room's tile grid and entity positions in place.

    flip_x  →  horizontal mirror  (left ↔ right)
    flip_y  →  vertical mirror    (top  ↔ bottom)

    Border walls map to border walls after either flip, so doorway carving
    (which always targets the centre of each border) remains correct.

    Pixel formula:
        flip_x: new_x = cols * TILE_SIZE - old_x
        flip_y: new_y = rows * TILE_SIZE - old_y
    Proof: centre of tile c  =  c*T + T/2.
           Centre of mirror  =  (cols-1-c)*T + T/2  =  cols*T - c*T - T + T/2
           Sum               =  c*T + T/2 + cols*T - c*T - T/2  =  cols * T  ✓
    """
    if not flip_x and not flip_y:
        return
    W = room.cols * TILE_SIZE
    H = room.rows * TILE_SIZE
    if flip_x:
        room.grid = [row[::-1] for row in room.grid]
    if flip_y:
        room.grid = room.grid[::-1]
    for e in room.enemies:
        if flip_x: e.x = W - e.x
        if flip_y: e.y = H - e.y
    for item in room.items:
        if flip_x: item.x = W - item.x
        if flip_y: item.y = H - item.y


# ---------------------------------------------------------------------------
# Fixed rooms
# ---------------------------------------------------------------------------

def make_start_room():
    """Empty starting room — no obstacles or enemies."""
    room = Room()
    if TESTING_MODE:
        b = room.bounds
        all_items = list(ITEMS.values())
        cols = 5
        spacing = 48
        start_x = b.left + 40
        start_y = b.top  + 40
        for i, item_cls in enumerate(all_items):
            col = i % cols
            row = i // cols
            room.items.append(item_cls(start_x + col * spacing, start_y + row * spacing))
    return room


def make_boss_room():
    """Open room with the boss enemy at the centre."""
    room = Room()
    room.is_boss_room = True
    b = room.bounds
    room.enemies = [ENEMIES["boss"](b.centerx, b.centery)]
    return room


def make_treasure_room():
    """Empty room with a single random stat item at the centre."""
    room = Room()
    b = room.bounds
    room.items = [random.choice(list(ITEMS.values()))(b.centerx, b.centery)]
    return room


# ---------------------------------------------------------------------------
# Combat rooms  (all asymmetric on both axes)
#
# Door paths that must stay clear of SOLID tiles:
#   horizontal  rows 8-10  (left ↔ right doors at the middle of each side wall)
#   vertical    cols 11-13 (up   ↔ down  doors at the middle of top/bottom walls)
# Spikes are walkable so they may cross door paths without blocking them.
# ---------------------------------------------------------------------------

def make_pillars_room():
    """
    Four wall pillars, each a different size and placed asymmetrically.
    Static spikes left of centre; timed spikes right of centre at a
    different row, so neither axis has a mirror line.

    Asymmetry check
      H-axis: top pillars at rows 3-4 (TL) and rows 4-5 (TR, shifted down 1)
      V-axis: TL is 2×2, TR is 3×2; BL is 2×3, BR is 2×2 at a different column
    """
    room = Room()

    # Top-left: 2 wide × 2 tall  (cols 3-4, rows 3-4)
    for dr in range(2):
        for dc in range(2):
            room.set_tile(3 + dc, 3 + dr, TileType.WALL)

    # Top-right: 3 wide × 2 tall, one row lower  (cols 17-19, rows 4-5)
    for dr in range(2):
        for dc in range(3):
            room.set_tile(17 + dc, 4 + dr, TileType.WALL)

    # Bottom-left: 2 wide × 3 tall  (cols 3-4, rows 12-14)
    for dr in range(3):
        for dc in range(2):
            room.set_tile(3 + dc, 12 + dr, TileType.WALL)

    # Bottom-right: 2 wide × 2 tall at a different column  (cols 20-21, rows 12-13)
    for dr in range(2):
        for dc in range(2):
            room.set_tile(20 + dc, 12 + dr, TileType.WALL)

    # Static spikes left of centre (row 7, cols 7-11; col 11 = door col but walkable)
    for c in range(7, 12):
        room.set_tile(c, 7, TileType.SPIKE)

    # Timed spikes right of centre at a lower row (row 11, cols 13-18)
    for c in range(13, 19):
        room.set_tile(c, 11, TileType.SPIKE_TIMED)

    room.enemies = [
        ENEMIES["zombie"]       (*_tc( 3,  9)),   # left middle
        ENEMIES["zombie"]       (*_tc(21,  9)),   # right middle
        ENEMIES["ranged_zombie"](*_tc(12,  9)),   # centre
        ENEMIES["bat"]          (*_tc( 8,  3)),   # top-left open area
        ENEMIES["bat"]          (*_tc(18, 14)),   # bottom-right open area
    ]
    return room


def make_gauntlet_room():
    """
    Two offset horizontal wall strips of different lengths.
    Upper strip (row 5) is shorter and sits left; lower strip (row 13)
    is longer and sits right — forming a Z-path.
    Gap pits are in opposite corners but of different dimensions.

    Asymmetry check
      H-axis: strips at rows 5 and 13 (not equidistant from centre row 9)
      V-axis: upper strip cols 3-9 (left-heavy); lower strip cols 15-22 (right-heavy)
    """
    room = Room()

    # Upper-left wall strip: row 5, cols 3-9
    for c in range(3, 10):
        room.set_tile(c, 5, TileType.WALL)

    # Lower-right wall strip: row 13, cols 15-22 (longer)
    for c in range(15, 23):
        room.set_tile(c, 13, TileType.WALL)

    # Gap pit upper-right: 3 wide × 3 tall
    for r in range(2, 5):
        for c in range(20, 23):
            room.set_tile(c, r, TileType.GAP)

    # Gap pit lower-left: 3 wide × 2 tall (smaller)
    for r in range(14, 16):
        for c in range(1, 4):
            room.set_tile(c, r, TileType.GAP)

    # Spikes extending the upper strip rightward (row 5, cols 10-13; walkable door cols)
    for c in range(10, 14):
        room.set_tile(c, 5, TileType.SPIKE)

    # Timed spikes extending the lower strip leftward (row 13, cols 11-14; walkable)
    for c in range(11, 15):
        room.set_tile(c, 13, TileType.SPIKE_TIMED)

    room.enemies = [
        ENEMIES["zombie"]       (*_tc( 5,  9)),   # left side
        ENEMIES["zombie"]       (*_tc(19,  9)),   # right side
        ENEMIES["ranged_zombie"](*_tc(20,  7)),   # top-right open area
        ENEMIES["ranged_zombie"](*_tc( 4, 14)),   # bottom-left (outside gap)
        ENEMIES["bat"]          (*_tc(12,  9)),   # centre
    ]
    return room


def make_crypt_room():
    """
    Two horizontal wall bars that bracket the vertical door path.
    Top bar is heavier on the right; bottom bar is heavier on the left,
    creating a Z-shaped obstruction.
    Gap corners are four different sizes.
    Spike columns at asymmetric column positions (col 5 vs col 19).

    Asymmetry check
      H-axis: top bar at row 6, bottom bar at row 12 (not equidistant from row 9)
      V-axis: top bar — left part 5 tiles, right part 8 tiles
              bottom bar — left part 6 tiles, right part 4 tiles
    """
    room = Room()

    # Spike columns set FIRST so bar tiles take priority at overlapping rows
    for r in range(7, 12):          # rows 7-11; avoids bar rows 6 and 12
        room.set_tile( 5, r, TileType.SPIKE)
        room.set_tile(19, r, TileType.SPIKE)

    # Top bar: row 6; left part short (cols 6-10), right part long (cols 14-21)
    for c in list(range(6, 11)) + list(range(14, 22)):
        room.set_tile(c, 6, TileType.WALL)

    # Bottom bar: row 12; left part long (cols 5-10), right part short (cols 14-17)
    for c in list(range(5, 11)) + list(range(14, 18)):
        room.set_tile(c, 12, TileType.WALL)

    # Gap pits — all four corners are different sizes
    for r in range(1, 5):           # top-left: 3 wide × 4 tall
        for c in range(1, 4):
            room.set_tile(c, r, TileType.GAP)
    for r in range(1, 4):           # top-right: 3 wide × 3 tall
        for c in range(21, 24):
            room.set_tile(c, r, TileType.GAP)
    for r in range(14, 17):         # bottom-left: 2 wide × 3 tall
        for c in range(1, 3):
            room.set_tile(c, r, TileType.GAP)
    for r in range(14, 17):         # bottom-right: 4 wide × 3 tall
        for c in range(20, 24):
            room.set_tile(c, r, TileType.GAP)

    room.enemies = [
        ENEMIES["ranged_zombie"](*_tc( 9,  4)),   # top, left of bars
        ENEMIES["ranged_zombie"](*_tc(16, 13)),   # bottom, right of bars
        ENEMIES["zombie"]       (*_tc(12,  9)),   # centre corridor
        ENEMIES["bat"]          (*_tc(22,  9)),   # right corridor
        ENEMIES["bat"]          (*_tc( 3,  9)),   # left corridor
    ]
    return room


def make_arena_room():
    """
    Four corner obstacles of deliberately different shapes:
      TL — full L-shape (horizontal + vertical arm)
      TR — horizontal bar only, at a different row than TL
      BL — vertical bar only (no horizontal arm)
      BR — smaller L-shape

    Spike bands appear on different sides at different rows.

    Asymmetry check
      H-axis: TL arm at row 3, TR bar at row 2; BL bar rows 11-15, BR arm at row 15
      V-axis: TL has two arms, TR has one; BL has one, BR has two (but smaller)
    """
    room = Room()

    # Top-left: full L-shape
    for c in range(2, 9):           # horizontal arm: cols 2-8, row 3
        room.set_tile(c, 3, TileType.WALL)
    for r in range(3, 8):           # vertical arm:   col 2, rows 3-7
        room.set_tile(2, r, TileType.WALL)

    # Top-right: horizontal bar only, at row 2 (different from TL's row 3)
    for c in range(16, 23):
        room.set_tile(c, 2, TileType.WALL)

    # Bottom-left: vertical bar only
    for r in range(11, 16):
        room.set_tile(3, r, TileType.WALL)

    # Bottom-right: smaller L-shape
    for c in range(18, 23):         # horizontal arm: cols 18-22, row 15
        room.set_tile(c, 15, TileType.WALL)
    for r in range(12, 16):         # vertical arm:   col 22, rows 12-15
        room.set_tile(22, r, TileType.WALL)

    # Static spikes left side only (row 6, cols 6-10)
    for c in range(6, 11):
        room.set_tile(c, 6, TileType.SPIKE)

    # Timed spikes right side only, at a lower row (row 12, cols 15-19)
    for c in range(15, 20):
        room.set_tile(c, 12, TileType.SPIKE_TIMED)

    room.enemies = [
        ENEMIES["zombie"]       (*_tc( 7,  9)),   # left centre
        ENEMIES["zombie"]       (*_tc(17,  9)),   # right centre
        ENEMIES["zombie"]       (*_tc(12,  4)),   # top centre
        ENEMIES["ranged_zombie"](*_tc(12, 14)),   # bottom centre
        ENEMIES["ranged_zombie"](*_tc( 6,  9)),   # left corridor
        ENEMIES["bat"]          (*_tc(12,  9)),   # centre
    ]
    return room


# ---------------------------------------------------------------------------
# Dungeon generator
# ---------------------------------------------------------------------------

def generate_dungeon():
    """
    Randomly grow a connected dungeon of 10-15 rooms starting from the
    start room.  Exactly one treasure room (locked) and one boss room are
    placed at dead ends.

    Each combat room is flipped independently on each axis with 50 % chance,
    giving up to 4 orientations per room type.

    Algorithm
    ---------
    1. Place start at grid origin (0, 0).
    2. Repeat: pick a random room that still borders a free cell;
       place a random (and randomly flipped) combat room there.
       New rooms are auto-connected to all existing neighbours.
    3. Attach the boss room to one dead end and the treasure room (locked)
       to a different dead end.
    """
    target = random.randint(10, 15)   # total rooms incl. start + treasure + boss

    grid  = {}   # (x, y) → Room
    order = []   # [(room, pos)] in placement order

    def _place(room, pos):
        grid[pos] = room
        order.append((room, pos))
        for d, (dx, dy) in _OFFSET.items():
            nbr_pos = (pos[0] + dx, pos[1] + dy)
            if nbr_pos in grid and d not in room.connections:
                room.connect(d, grid[nbr_pos])

    def _free(pos):
        return [(d, (pos[0]+dx, pos[1]+dy))
                for d, (dx, dy) in _OFFSET.items()
                if (pos[0]+dx, pos[1]+dy) not in grid]

    _POOL = [make_pillars_room, make_gauntlet_room,
             make_crypt_room,   make_arena_room]

    _place(make_start_room(), (0, 0))

    # --- Grow combat rooms ---
    while len(order) < target - 1:
        frontier = [(r, p) for r, p in order if _free(p)]
        if not frontier:
            break
        parent, ppos = random.choice(frontier)
        d, npos      = random.choice(_free(ppos))

        new_room = random.choice(_POOL)()
        _flip_room(new_room, random.random() < 0.5, random.random() < 0.5)
        _place(new_room, npos)

    # Collect dead ends excluding the start room
    dead_ends = [(r, p) for r, p in order
                 if len(r.connections) == 1 and r is not order[0][0] and _free(p)]
    candidates = dead_ends or [(r, p) for r, p in order
                                if r is not order[0][0] and _free(p)]

    # --- Place boss room at one dead end ---
    if candidates:
        random.shuffle(candidates)
        parent, ppos = candidates.pop()
        d, bpos = random.choice(_free(ppos))
        _place(make_boss_room(), bpos)

    # Refresh dead-end list after boss placement
    dead_ends = [(r, p) for r, p in order
                 if len(r.connections) == 1 and r is not order[0][0]
                 and not r.is_boss_room and _free(p)]
    candidates = dead_ends or [(r, p) for r, p in order
                                if r is not order[0][0] and not r.is_boss_room and _free(p)]

    # --- Place treasure at a different dead end (locked) ---
    if candidates:
        parent, ppos = random.choice(candidates)
        d, tpos      = random.choice(_free(ppos))
        parent.connect_locked(d, make_treasure_room())

    return order[0][0], grid   # start room, {(x,y): Room} grid
