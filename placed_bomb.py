import math
import pygame
from constants import TILE_SIZE
from tile import TileType

EXPLOSION_RADIUS   = 64
_EXPLOSION_DAMAGE  = 4
_FUSE_DURATION     = 3.0
_EXPLOSION_DURATION = 0.45
_BOMB_RADIUS       = 9


class PlacedBomb:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self._fuse          = _FUSE_DURATION
        self._exploding     = False
        self._explode_timer = 0.0
        self._flash_on      = True
        self._flash_timer   = 0.0

    @property
    def done(self):
        return self._exploding and self._explode_timer <= 0

    def _flash_rate(self):
        """Half-cycle duration; speeds up as fuse runs down."""
        if self._fuse > 2.0: return 0.30
        if self._fuse > 1.0: return 0.15
        return 0.07

    def update(self, dt, player, enemies, room=None):
        if self._exploding:
            self._explode_timer -= dt
            return

        self._flash_timer -= dt
        if self._flash_timer <= 0:
            self._flash_on    = not self._flash_on
            self._flash_timer = self._flash_rate()

        self._fuse -= dt
        if self._fuse <= 0:
            self._trigger(player, enemies, room)

    def _trigger(self, player, enemies, room=None):
        self._exploding     = True
        self._explode_timer = _EXPLOSION_DURATION

        for enemy in enemies:
            dx   = enemy.x - self.x
            dy   = enemy.y - self.y
            dist = math.hypot(dx, dy)
            if dist <= EXPLOSION_RADIUS:
                enemy.take_damage(_EXPLOSION_DAMAGE)
                enemy.apply_knockback(dx, dy)

        if math.hypot(player.x - self.x, player.y - self.y) <= EXPLOSION_RADIUS:
            player.take_damage(_EXPLOSION_DAMAGE)

        if room is not None:
            col_min = max(0, int((self.x - EXPLOSION_RADIUS) // TILE_SIZE))
            col_max = min(room.cols - 1, int((self.x + EXPLOSION_RADIUS) // TILE_SIZE))
            row_min = max(0, int((self.y - EXPLOSION_RADIUS) // TILE_SIZE))
            row_max = min(room.rows - 1, int((self.y + EXPLOSION_RADIUS) // TILE_SIZE))
            for r in range(row_min, row_max + 1):
                for c in range(col_min, col_max + 1):
                    # Never destroy border walls (they frame the room)
                    if c == 0 or c == room.cols - 1 or r == 0 or r == room.rows - 1:
                        continue
                    if room.grid[r][c] != TileType.WALL:
                        continue
                    tile_cx = c * TILE_SIZE + TILE_SIZE // 2
                    tile_cy = r * TILE_SIZE + TILE_SIZE // 2
                    if math.hypot(tile_cx - self.x, tile_cy - self.y) <= EXPLOSION_RADIUS:
                        room.set_tile(c, r, TileType.FLOOR)

    def draw(self, surface):
        cx, cy = round(self.x), round(self.y)

        if self._exploding:
            t        = self._explode_timer / _EXPLOSION_DURATION  # 1 → 0
            progress = 1.0 - t                                     # 0 → 1
            radius   = max(1, int(EXPLOSION_RADIUS * progress))
            size     = radius * 2 + 8
            c        = size // 2

            exp_surf = pygame.Surface((size, size), pygame.SRCALPHA)
            # Filled disc fades out
            pygame.draw.circle(exp_surf, (255, 120, 10,  int(160 * t)), (c, c), radius)
            # Bright outer ring
            pygame.draw.circle(exp_surf, (255, 240, 80,  int(255 * t)), (c, c), radius, 3)
            # Bright inner core that shrinks
            core_r = max(0, int(radius * 0.35))
            if core_r > 0:
                pygame.draw.circle(exp_surf, (255, 255, 200, int(255 * t)), (c, c), core_r)

            surface.blit(exp_surf, (cx - c, cy - c))
        else:
            r     = _BOMB_RADIUS
            color = (255, 255, 255) if self._flash_on else (45, 45, 55)
            pygame.draw.circle(surface, color,       (cx, cy + 2), r - 1)
            pygame.draw.circle(surface, (60, 60, 75),(cx, cy + 2), r - 1, 1)
            # Fuse
            fx, fy = cx + r // 2, cy - r // 2 + 2
            pygame.draw.line(surface, (160, 130, 80), (fx, fy), (fx + r // 2, fy - r // 2), 2)
            # Spark flickers with the flash
            if self._flash_on:
                pygame.draw.circle(surface, (255, 210, 60), (fx + r // 2, fy - r // 2), 2)
