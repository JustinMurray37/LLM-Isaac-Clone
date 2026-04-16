import random
import pygame
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, COLOR_BG
from tile import TileType, TILE_COLORS

_color_shift  = (0, 0, 0)
_controls_font = None

def _get_controls_font():
    global _controls_font
    if _controls_font is None:
        _controls_font = pygame.font.SysFont("monospace", 15)
    return _controls_font  # per-level RGB offset applied to all floor and wall colors


def randomize_level_colors():
    global _color_shift
    _color_shift = (
        random.randint(-20, 20),
        random.randint(-20, 20),
        random.randint(-20, 20),
    )


def _sc(color):
    """Apply the current level color shift to a base color, clamped to [0, 255]."""
    return (
        max(0, min(255, color[0] + _color_shift[0])),
        max(0, min(255, color[1] + _color_shift[1])),
        max(0, min(255, color[2] + _color_shift[2])),
    )

COLS = SCREEN_WIDTH  // TILE_SIZE   # 25
ROWS = SCREEN_HEIGHT // TILE_SIZE   # 18

_SPIKE_CYCLE      = 4.0   # seconds for a full extend→retract→extend cycle
_SPIKE_TRANSITION = 0.5   # seconds spent animating between states

_OPPOSITE = {"right": "left", "left": "right", "up": "down", "down": "up"}


class Room:
    def __init__(self, cols=COLS, rows=ROWS):
        self.cols = cols
        self.rows = rows
        self._spike_cycle = 0.0
        self.connections        = {}    # direction → Room
        self.locked_connections = set() # directions that still require a key
        self.enemies      = []
        self.items        = []
        self.pickups      = []
        self.chests       = []
        self.placed_bombs = []
        self._reward_given = False
        self.is_start_room     = False
        self.is_boss_room      = False
        self.is_treasure_room  = False
        self.ladder        = None
        self.blood_stains  = []
        self.slime_puddles = []
        # Default layout: wall border with floor interior
        self.grid = [
            [
                TileType.WALL if (c == 0 or c == cols - 1 or r == 0 or r == rows - 1)
                else TileType.FLOOR
                for c in range(cols)
            ]
            for r in range(rows)
        ]

    # ------------------------------------------------------------------
    # Per-frame update

    def update(self, dt):
        self._spike_cycle = (self._spike_cycle + dt) % _SPIKE_CYCLE

    @property
    def spike_timed_scale(self):
        """Height scale [0.0, 1.0] for timed spike triangles.
        1.0 = fully extended (damaging), 0.0 = fully retracted (safe).
        """
        t    = self._spike_cycle
        half = _SPIKE_CYCLE / 2          # 2.0 s
        tr   = _SPIKE_TRANSITION         # 0.5 s
        _MIN = 0.25   # retracted but still visible
        if t < half - tr:                # 0 → 1.5 s  : fully extended
            return 1.0
        elif t < half:                   # 1.5 → 2.0 s: retracting
            return 1.0 - (1.0 - _MIN) * (t - (half - tr)) / tr
        elif t < _SPIKE_CYCLE - tr:      # 2.0 → 3.5 s: at minimum height
            return _MIN
        else:                            # 3.5 → 4.0 s: extending
            return _MIN + (1.0 - _MIN) * (t - (_SPIKE_CYCLE - tr)) / tr

    @property
    def spike_timed_active(self):
        """True when timed spikes are fully extended and should deal damage."""
        return self.spike_timed_scale >= 1.0

    # ------------------------------------------------------------------
    # Tile access

    def get_tile(self, col, row):
        return self.grid[row][col]

    def set_tile(self, col, row, tile_type):
        if (tile_type == TileType.WALL
                and col != 0 and col != self.cols - 1
                and row != 0 and row != self.rows - 1
                and random.random() < 0.001):
            tile_type = TileType.CRACKED_WALL
        self.grid[row][col] = tile_type

    def tile_at_pixel(self, x, y):
        """Return the tile type at a pixel position, or WALL if out of bounds."""
        col = int(x) // TILE_SIZE
        row = int(y) // TILE_SIZE
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return self.grid[row][col]
        return TileType.WALL

    # ------------------------------------------------------------------
    # Geometry

    @property
    def bounds(self):
        """Playable rect (interior, excluding the border wall tiles)."""
        return pygame.Rect(
            TILE_SIZE,
            TILE_SIZE,
            (self.cols - 2) * TILE_SIZE,
            (self.rows - 2) * TILE_SIZE,
        )

    # ------------------------------------------------------------------
    # Connections and doorways

    def connect(self, direction, other_room):
        """Bidirectionally link this room to other_room through a doorway."""
        self.connections[direction] = other_room
        other_room.connections[_OPPOSITE[direction]] = self
        self._carve_doorway(direction)
        other_room._carve_doorway(_OPPOSITE[direction])

    def connect_locked(self, direction, other_room):
        """Like connect(), but the doorway starts locked and requires a key."""
        self.connect(direction, other_room)
        self.locked_connections.add(direction)
        other_room.locked_connections.add(_OPPOSITE[direction])

    def _unlock_connection(self, direction):
        """Unlock both sides of a connection (called when a key is spent)."""
        self.locked_connections.discard(direction)
        self.connections[direction].locked_connections.discard(_OPPOSITE[direction])

    def _door_rows(self):
        mid = self.rows // 2
        return [mid - 1, mid, mid + 1]

    def _door_cols(self):
        mid = self.cols // 2
        return [mid - 1, mid, mid + 1]

    def _carve_doorway(self, direction):
        if direction == "right":
            for r in self._door_rows():
                self.grid[r][self.cols - 1] = TileType.FLOOR
        elif direction == "left":
            for r in self._door_rows():
                self.grid[r][0] = TileType.FLOOR
        elif direction == "up":
            for c in self._door_cols():
                self.grid[0][c] = TileType.FLOOR
        elif direction == "down":
            for c in self._door_cols():
                self.grid[self.rows - 1][c] = TileType.FLOOR

    def check_exit(self, px, py):
        """Return direction if the player centre has crossed a doorway threshold, else None.
        Returns None whenever there are living enemies in the room."""
        if self.enemies:
            return None
        if "right" in self.connections and px >= (self.cols - 1) * TILE_SIZE + TILE_SIZE // 2:
            return "right"
        if "left"  in self.connections and px <= TILE_SIZE // 2:
            return "left"
        if "down"  in self.connections and py >= (self.rows - 1) * TILE_SIZE + TILE_SIZE // 2:
            return "down"
        if "up"    in self.connections and py <= TILE_SIZE // 2:
            return "up"
        return None

    # ------------------------------------------------------------------
    # Collision

    def is_solid(self, col, row):
        """True for tiles that block movement (WALL, CRACKED_WALL, GAP). SPIKE is walkable."""
        return self.grid[row][col] in (TileType.WALL, TileType.CRACKED_WALL, TileType.GAP)

    def is_wall_at_pixel(self, x, y):
        """True if the pixel sits on a WALL or CRACKED_WALL tile (stops projectiles)."""
        col = int(x) // TILE_SIZE
        row = int(y) // TILE_SIZE
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return self.grid[row][col] in (TileType.WALL, TileType.CRACKED_WALL)
        return True

    def resolve_position(self, x, y, half_size):
        """Push (x, y) out of any solid tiles and return the corrected position."""
        left   = x - half_size
        right  = x + half_size
        top    = y - half_size
        bottom = y + half_size

        col_min = max(0,            int(left)   // TILE_SIZE)
        col_max = min(self.cols-1,  int(right)  // TILE_SIZE)
        row_min = max(0,            int(top)    // TILE_SIZE)
        row_max = min(self.rows-1,  int(bottom) // TILE_SIZE)

        for r in range(row_min, row_max + 1):
            for c in range(col_min, col_max + 1):
                if self.grid[r][c] in (TileType.FLOOR, TileType.SPIKE, TileType.SPIKE_TIMED):
                    continue

                tx, ty = c * TILE_SIZE, r * TILE_SIZE

                # Penetration depths from each side
                ol = right  - tx                # player right into tile left
                or_ = (tx + TILE_SIZE) - left   # tile right into player left
                ot = bottom - ty                # player bottom into tile top
                ob = (ty + TILE_SIZE) - top     # tile bottom into player top

                if ol <= 0 or or_ <= 0 or ot <= 0 or ob <= 0:
                    continue  # no real overlap

                # Push along the axis with the smallest penetration
                if min(ol, or_) < min(ot, ob):
                    x = (x - ol) if ol < or_ else (x + or_)
                else:
                    y = (y - ot) if ot < ob else (y + ob)

                # Recalculate bounds for the next tile check
                left   = x - half_size
                right  = x + half_size
                top    = y - half_size
                bottom = y + half_size

        return x, y

    # ------------------------------------------------------------------
    # Drawing

    def draw(self, surface):
        surface.fill(COLOR_BG)

        # Pass 1: flat background fills for every tile
        for r in range(self.rows):
            for c in range(self.cols):
                pygame.draw.rect(surface, TILE_COLORS[self.grid[r][c]],
                                 (c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE))

        # Pass 2: tile decorations drawn after all backgrounds so edge
        # details on gap/wall tiles aren't overwritten by adjacent fills
        for r in range(self.rows):
            for c in range(self.cols):
                tile = self.grid[r][c]
                if tile in (TileType.FLOOR, TileType.SPIKE, TileType.SPIKE_TIMED):
                    self._draw_floor_tile(surface, c, r)
                elif tile == TileType.WALL:
                    self._draw_wall_tile(surface, c, r)
                elif tile == TileType.CRACKED_WALL:
                    self._draw_cracked_wall_tile(surface, c, r)
                elif tile == TileType.GAP:
                    self._draw_gap_tile(surface, c, r)

                if tile == TileType.SPIKE:
                    self._draw_spike_tile(surface, c, r, scale=1.0)
                elif tile == TileType.SPIKE_TIMED:
                    self._draw_spike_tile(surface, c, r, scale=self.spike_timed_scale)

        for stain in self.blood_stains:
            stain.draw(surface)
        for puddle in self.slime_puddles:
            puddle.draw(surface)
        if self.ladder:
            self.ladder.draw(surface)
        if self.enemies:
            self._draw_door_barriers(surface)
        if self.locked_connections:
            self._draw_locked_barriers(surface)
        self._draw_boss_doorway_markers(surface)
        if self.is_start_room:
            self._draw_controls(surface)

    def _draw_controls(self, surface):
        lines  = ["Move: WASD", "Fire: Arrow Keys", "Bomb: E", "Restart: Hold R"]
        font   = _get_controls_font()
        color  = (180, 175, 160)
        lh     = font.get_linesize() + 2
        total  = len(lines) * lh
        b      = self.bounds
        y      = b.bottom - b.height // 4 - total // 2
        for line in lines:
            surf = font.render(line, True, color)
            surface.blit(surf, (b.centerx - surf.get_width() // 2, y))
            y += lh

    def _draw_floor_tile(self, surface, col, row):
        """Draw a horizontal wood-plank texture on a floor tile."""
        tx = col * TILE_SIZE
        ty = row * TILE_SIZE
        s  = TILE_SIZE          # 32

        _PLANK_A = _sc((108, 80, 50))   # lighter plank
        _PLANK_B = _sc(( 90, 65, 40))   # darker plank
        _GRAIN   = _sc(( 76, 54, 32))   # subtle grain line
        _JOINT   = _sc(( 60, 42, 24))   # gap between planks

        plank_h  = 8               # 4 planks per tile
        planks   = s // plank_h

        for i in range(planks):
            py = ty + i * plank_h
            # Use global plank row so colours align across adjacent tiles
            global_row = row * planks + i
            color = _PLANK_A if global_row % 2 == 0 else _PLANK_B
            pygame.draw.rect(surface, color, (tx, py, s, plank_h))

            # Joint line at the bottom edge of each plank
            pygame.draw.line(surface, _JOINT,
                             (tx, py + plank_h - 1), (tx + s - 1, py + plank_h - 1))

            # One or two subtle grain lines per plank (deterministic by position)
            seed = (col * 11 + global_row * 7) % 6
            if seed < 4:
                gy = py + 2 + (seed % 3)
                x0 = tx + (col * 5) % 4
                x1 = tx + s - 1 - (col * 3) % 4
                pygame.draw.line(surface, _GRAIN, (x0, gy), (x1, gy))

    def _draw_barrier_tile(self, surface, tx, ty):
        """Draw one barrier tile: a wall tile darkened to show the door is sealed."""
        s = TILE_SIZE
        p, b = 2, 5
        x, y = tx + p, ty + p
        w, h = s - p * 2, s - p * 2
        # Dark stone face (about 70 % brightness of normal wall)
        pygame.draw.rect(surface, _sc((62, 58, 54)), (x, y, w, h))
        pygame.draw.polygon(surface, _sc((88, 84, 78)),  [(x,y),(x+w,y),(x+w-b,y+b),(x+b,y+b)])
        pygame.draw.polygon(surface, _sc((74, 70, 65)),  [(x,y),(x+b,y+b),(x+b,y+h-b),(x,y+h)])
        pygame.draw.polygon(surface, _sc((30, 28, 25)),  [(x,y+h),(x+w,y+h),(x+w-b,y+h-b),(x+b,y+h-b)])
        pygame.draw.polygon(surface, _sc((38, 36, 33)),  [(x+w,y),(x+w,y+h),(x+w-b,y+h-b),(x+w-b,y+b)])
        # Subtle crack
        pygame.draw.line(surface, (42, 39, 36), (tx + 10, ty + 12), (tx + 15, ty + 19), 1)

    def _draw_door_barriers(self, surface):
        """Draw darkened wall tiles across every connected doorway while enemies are alive."""
        door_r = self._door_rows()
        door_c = self._door_cols()
        for direction in self.connections:
            if direction == "right":
                for r in door_r:
                    self._draw_barrier_tile(surface, (self.cols - 1) * TILE_SIZE, r * TILE_SIZE)
            elif direction == "left":
                for r in door_r:
                    self._draw_barrier_tile(surface, 0, r * TILE_SIZE)
            elif direction == "down":
                for c in door_c:
                    self._draw_barrier_tile(surface, c * TILE_SIZE, (self.rows - 1) * TILE_SIZE)
            elif direction == "up":
                for c in door_c:
                    self._draw_barrier_tile(surface, c * TILE_SIZE, 0)

    def _draw_gap_tile(self, surface, col, row):
        """Draw bumpy rocky protrusions along edges that border a non-gap tile."""
        tx, ty = col * TILE_SIZE, row * TILE_SIZE
        s = TILE_SIZE
        _BUMP   = (52, 52, 68)
        _SHADOW = (20, 20, 26)
        r = 5
        positions = [5, 16, 27]

        def _neighbor_gap(dc, dr):
            nc, nr = col + dc, row + dr
            return (0 <= nc < self.cols and 0 <= nr < self.rows
                    and self.grid[nr][nc] == TileType.GAP)

        for p in positions:
            if not _neighbor_gap(0, -1):   # top
                pygame.draw.circle(surface, _BUMP,   (tx + p, ty),         r)
                pygame.draw.circle(surface, _SHADOW, (tx + p, ty + r - 1), r - 2)
            if not _neighbor_gap(0,  1):   # bottom
                pygame.draw.circle(surface, _BUMP,   (tx + p, ty + s),         r)
                pygame.draw.circle(surface, _SHADOW, (tx + p, ty + s - r + 1), r - 2)
            if not _neighbor_gap(-1, 0):   # left
                pygame.draw.circle(surface, _BUMP,   (tx,         ty + p), r)
                pygame.draw.circle(surface, _SHADOW, (tx + r - 1, ty + p), r - 2)
            if not _neighbor_gap(1,  0):   # right
                pygame.draw.circle(surface, _BUMP,   (tx + s,         ty + p), r)
                pygame.draw.circle(surface, _SHADOW, (tx + s - r + 1, ty + p), r - 2)

    def _draw_wall_tile(self, surface, col, row):
        """Draw a beveled stone block with highlight, shadow, and a crack."""
        tx = col * TILE_SIZE
        ty = row * TILE_SIZE
        s  = TILE_SIZE
        p  = 2    # gap between tile edge and stone face
        b  = 5    # bevel depth

        x, y = tx + p, ty + p
        w, h = s - p * 2, s - p * 2

        # Stone face
        pygame.draw.rect(surface, _sc((92, 88, 82)), (x, y, w, h))

        # Top bevel — bright highlight
        pygame.draw.polygon(surface, _sc((132, 127, 120)), [
            (x,         y),
            (x + w,     y),
            (x + w - b, y + b),
            (x + b,     y + b),
        ])
        # Left bevel — softer highlight
        pygame.draw.polygon(surface, _sc((112, 108, 102)), [
            (x,     y),
            (x + b, y + b),
            (x + b, y + h - b),
            (x,     y + h),
        ])
        # Bottom bevel — deep shadow
        pygame.draw.polygon(surface, _sc((52, 49, 45)), [
            (x,         y + h),
            (x + w,     y + h),
            (x + w - b, y + h - b),
            (x + b,     y + h - b),
        ])
        # Right bevel — shadow
        pygame.draw.polygon(surface, _sc((62, 59, 55)), [
            (x + w,     y),
            (x + w,     y + h),
            (x + w - b, y + h - b),
            (x + w - b, y + b),
        ])

        # Crack detail
        pygame.draw.line(surface, (65, 62, 57),
                         (tx + 10, ty + 12), (tx + 16, ty + 20), 1)
        pygame.draw.line(surface, (65, 62, 57),
                         (tx + 20, ty +  8), (tx + 22, ty + 14), 1)

    def _draw_cracked_wall_tile(self, surface, col, row):
        """Like _draw_wall_tile but with heavier, more numerous cracks and a lighter face."""
        tx = col * TILE_SIZE
        ty = row * TILE_SIZE
        s  = TILE_SIZE
        p  = 2
        b  = 5

        x, y = tx + p, ty + p
        w, h = s - p * 2, s - p * 2

        # Slightly lighter/damaged stone face
        pygame.draw.rect(surface, _sc((78, 74, 68)), (x, y, w, h))

        pygame.draw.polygon(surface, _sc((115, 110, 103)), [
            (x, y), (x+w, y), (x+w-b, y+b), (x+b, y+b)])
        pygame.draw.polygon(surface, _sc((95, 91, 85)), [
            (x, y), (x+b, y+b), (x+b, y+h-b), (x, y+h)])
        pygame.draw.polygon(surface, _sc((40, 37, 34)), [
            (x, y+h), (x+w, y+h), (x+w-b, y+h-b), (x+b, y+h-b)])
        pygame.draw.polygon(surface, _sc((50, 47, 43)), [
            (x+w, y), (x+w, y+h), (x+w-b, y+h-b), (x+w-b, y+b)])

        # Heavy branching cracks
        _C = (42, 38, 34)
        pygame.draw.line(surface, _C, (tx +  8, ty +  4), (tx + 14, ty + 14), 2)
        pygame.draw.line(surface, _C, (tx + 14, ty + 14), (tx + 10, ty + 22), 1)
        pygame.draw.line(surface, _C, (tx + 14, ty + 14), (tx + 20, ty + 20), 1)
        pygame.draw.line(surface, _C, (tx + 18, ty +  6), (tx + 22, ty + 16), 2)
        pygame.draw.line(surface, _C, (tx +  6, ty + 20), (tx + 12, ty + 26), 1)

    def _draw_locked_barriers(self, surface):
        """Draw a golden barred gate across each locked doorway."""
        _GOLD = (200, 155, 20)
        _BAR  = (120,  90, 10)
        door_r = self._door_rows()
        door_c = self._door_cols()
        for direction in self.locked_connections:
            if direction == "right":
                x, y = (self.cols - 1) * TILE_SIZE, door_r[0] * TILE_SIZE
                w, h = TILE_SIZE, len(door_r) * TILE_SIZE
            elif direction == "left":
                x, y = 0, door_r[0] * TILE_SIZE
                w, h = TILE_SIZE, len(door_r) * TILE_SIZE
            elif direction == "down":
                x, y = door_c[0] * TILE_SIZE, (self.rows - 1) * TILE_SIZE
                w, h = len(door_c) * TILE_SIZE, TILE_SIZE
            elif direction == "up":
                x, y = door_c[0] * TILE_SIZE, 0
                w, h = len(door_c) * TILE_SIZE, TILE_SIZE
            else:
                continue
            pygame.draw.rect(surface, _GOLD, (x, y, w, h))
            # Bars along the short axis
            if direction in ("left", "right"):
                bx = x + 4
                while bx < x + w - 2:
                    pygame.draw.line(surface, _BAR, (bx, y + 2), (bx, y + h - 2), 2)
                    bx += 6
            else:
                by = y + 4
                while by < y + h - 2:
                    pygame.draw.line(surface, _BAR, (x + 2, by), (x + w - 2, by), 2)
                    by += 6

    def _draw_boss_doorway_markers(self, surface):
        """Draw a red stone frame around any doorway that leads to the boss room."""
        _RED_FACE   = (160, 40,  40)
        _RED_HI     = (200, 80,  80)
        _RED_SHADOW = ( 80, 15,  15)
        _RED_BORDER = (220, 60,  60)

        T = TILE_SIZE
        door_r = self._door_rows()
        door_c = self._door_cols()

        for direction, nbr in self.connections.items():
            if not nbr.is_boss_room:
                continue

            # Determine the two flanking wall tiles (above/below or left/right of opening)
            if direction == "right":
                fx = (self.cols - 1) * T
                flanks = [(fx, (door_r[0] - 1) * T), (fx, (door_r[-1] + 1) * T)]
                # Red border lines on interior edge of opening
                ix = fx
                iy0, iy1 = door_r[0] * T, (door_r[-1] + 1) * T
                border_pts = [(ix, iy0), (ix, iy1)]   # vertical line on interior
                horiz = False
            elif direction == "left":
                fx = 0
                flanks = [(fx, (door_r[0] - 1) * T), (fx, (door_r[-1] + 1) * T)]
                ix = fx + T
                iy0, iy1 = door_r[0] * T, (door_r[-1] + 1) * T
                horiz = False
            elif direction == "down":
                fy = (self.rows - 1) * T
                flanks = [((door_c[0] - 1) * T, fy), ((door_c[-1] + 1) * T, fy)]
                ix0, ix1 = door_c[0] * T, (door_c[-1] + 1) * T
                iy = fy
                horiz = True
            elif direction == "up":
                fy = 0
                flanks = [((door_c[0] - 1) * T, fy), ((door_c[-1] + 1) * T, fy)]
                ix0, ix1 = door_c[0] * T, (door_c[-1] + 1) * T
                iy = fy + T
                horiz = True
            else:
                continue

            # Paint flanking tiles red (overwrite existing wall tile appearance)
            for (tx, ty) in flanks:
                p, b = 2, 5
                x, y, w, h = tx + p, ty + p, T - p * 2, T - p * 2
                pygame.draw.rect(surface, _RED_FACE, (x, y, w, h))
                pygame.draw.polygon(surface, _RED_HI,     [(x,y),(x+w,y),(x+w-b,y+b),(x+b,y+b)])
                pygame.draw.polygon(surface, _RED_SHADOW, [(x,y+h),(x+w,y+h),(x+w-b,y+h-b),(x+b,y+h-b)])

            # Draw a thick red line on the interior edge of the opening
            thickness = 4
            if not horiz:
                if direction == "right":
                    lx = ix
                else:
                    lx = ix - thickness
                pygame.draw.rect(surface, _RED_BORDER,
                                 (lx, iy0, thickness, iy1 - iy0))
            else:
                if direction == "down":
                    ly = iy
                else:
                    ly = iy - thickness
                pygame.draw.rect(surface, _RED_BORDER,
                                 (ix0, ly, ix1 - ix0, thickness))

    def _draw_spike_tile(self, surface, col, row, scale=1.0):
        """Draw three upward-pointing gray triangles on a spike tile.
        scale controls the height: 1.0 = fully extended, 0.0 = flat.
        """
        _SPIKE_COLOR = (140, 140, 150)
        tx = col * TILE_SIZE
        ty = row * TILE_SIZE
        w  = TILE_SIZE // 3
        max_tip_y = ty + 4                     # topmost point when fully extended
        base_y    = ty + TILE_SIZE - 2         # base of triangles (bottom of tile)
        max_h     = base_y - max_tip_y
        tip_y     = base_y - int(max_h * scale)
        for i in range(3):
            bx = tx + i * w
            tip_x = bx + w // 2
            pygame.draw.polygon(surface, _SPIKE_COLOR, [
                (bx + 2,     base_y),
                (bx + w - 2, base_y),
                (tip_x,      tip_y),
            ])
