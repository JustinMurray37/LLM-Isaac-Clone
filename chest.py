import math
import random
import pygame
from pickup import PICKUPS
from items import ITEMS

_WIDTH       = 52    # doubled from original 26
_HEIGHT      = 40    # doubled from original 20
_PUSH_SPEED  = 140.0
_FRICTION    = 300.0

_BODY_COLOR  = (120, 75,  35)
_LID_COLOR   = (145, 95,  45)
_LATCH_COLOR = (210, 175, 50)
_OPEN_COLOR  = (50,  30,  15)

_GOLD_BODY   = (175, 135, 20)
_GOLD_LID    = (210, 165, 40)
_GOLD_LATCH  = (255, 215, 70)
_GOLD_OPEN   = (75,  55,  10)
_LOCK_COLOR  = (150, 110, 15)


class Chest:
    """
    A chest that opens when the player walks into it and drops 1–3 random pickups.
    Acts as a physics object: the player can push it around.
    Enemies do not interact with chests.
    """

    def __init__(self, x, y):
        self.x    = float(x)
        self.y    = float(y)
        self.vx   = 0.0
        self.vy   = 0.0
        self.open = False

    # ------------------------------------------------------------------
    # Subclass hooks

    def _can_open(self, player):
        return True

    def _on_open(self, player, room):
        self.open = True
        count = random.randint(1, 3)
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            dist  = random.uniform(30, 55)
            room.pickups.append(
                random.choice(list(PICKUPS.values()))(
                    self.x + math.cos(angle) * dist,
                    self.y + math.sin(angle) * dist,
                )
            )

    # ------------------------------------------------------------------
    # Geometry

    @staticmethod
    def _hw():
        return _WIDTH  // 2

    @staticmethod
    def _hh():
        return _HEIGHT // 2

    def _player_overlaps(self, player):
        ph = player.stats.size // 2
        return (abs(player.x - self.x) < self._hw() + ph and
                abs(player.y - self.y) < self._hh() + ph)

    def _push_from_player(self, player):
        hw = self._hw()
        hh = self._hh()
        ph = player.stats.size // 2
        dx = self.x - player.x
        dy = self.y - player.y
        ox = hw + ph - abs(dx)
        oy = hh + ph - abs(dy)
        if ox <= 0 or oy <= 0:
            return
        if ox < oy:
            self.x += math.copysign(ox, dx)
            self.vx  = math.copysign(_PUSH_SPEED, dx)
        else:
            self.y += math.copysign(oy, dy)
            self.vy  = math.copysign(_PUSH_SPEED, dy)

    # ------------------------------------------------------------------
    # Per-frame

    def check_interaction(self, player, room):
        if not self.open and self._can_open(player) and self._player_overlaps(player):
            self._on_open(player, room)
        else:
            self._push_from_player(player)

    def update(self, dt, room):
        if self.vx == 0.0 and self.vy == 0.0:
            return

        self.x += self.vx * dt
        self.y += self.vy * dt

        hw = self._hw()
        hh = self._hh()
        bounds = room.bounds
        self.x = max(self.x, bounds.left   + hw)
        self.x = min(self.x, bounds.right  - hw)
        self.y = max(self.y, bounds.top    + hh)
        self.y = min(self.y, bounds.bottom - hh)

        # Use the larger half-dimension so resolve_position treats it as a
        # bounding square; slight overestimate in the shorter axis is acceptable.
        new_x, new_y = room.resolve_position(self.x, self.y, hw)
        if abs(new_x - self.x) > 0.1:
            self.vx = 0.0
        if abs(new_y - self.y) > 0.1:
            self.vy = 0.0
        self.x, self.y = new_x, new_y

        speed = math.hypot(self.vx, self.vy)
        if speed > 0:
            slow  = min(speed, _FRICTION * dt)
            scale = (speed - slow) / speed
            self.vx *= scale
            self.vy *= scale

    # ------------------------------------------------------------------
    # Drawing

    def draw(self, surface):
        self._draw_chest(surface, _BODY_COLOR, _LID_COLOR, _LATCH_COLOR, _OPEN_COLOR)

    def _draw_chest(self, surface, body_col, lid_col, latch_col, open_col):
        cx, cy = round(self.x), round(self.y)
        hw    = self._hw()
        hh    = self._hh()
        lid_h = _HEIGHT // 3

        if self.open:
            pygame.draw.rect(surface, open_col,
                             (cx - hw, cy - hh, _WIDTH, _HEIGHT))
            pygame.draw.rect(surface, body_col,
                             (cx - hw, cy - hh, _WIDTH, _HEIGHT), 2)
            lid_pts = [
                (cx - hw,     cy - hh - 1),
                (cx + hw,     cy - hh - 1),
                (cx + hw - 5, cy - hh - lid_h - 7),
                (cx - hw + 5, cy - hh - lid_h - 7),
            ]
            pygame.draw.polygon(surface, lid_col, lid_pts)
            pygame.draw.polygon(surface, body_col, lid_pts, 1)
        else:
            pygame.draw.rect(surface, body_col,
                             (cx - hw, cy - hh + lid_h, _WIDTH, _HEIGHT - lid_h))
            pygame.draw.rect(surface, lid_col,
                             (cx - hw, cy - hh, _WIDTH, lid_h + 2))
            pygame.draw.circle(surface, latch_col, (cx, cy - hh + lid_h + 4), 5)
            pygame.draw.rect(surface, open_col,
                             (cx - hw, cy - hh, _WIDTH, _HEIGHT), 1)


class GoldenChest(Chest):
    """Requires one key to open; drops 1–3 pickups like a regular chest."""

    def _can_open(self, player):
        return player.stats.keys > 0

    def _on_open(self, player, room):
        player.stats.keys -= 1
        if random.random() < 0.20:
            room.items.append(random.choice(list(ITEMS.values()))(self.x, self.y))
        else:
            super()._on_open(player, room)

    def draw(self, surface):
        self._draw_chest(surface, _GOLD_BODY, _GOLD_LID, _GOLD_LATCH, _GOLD_OPEN)
        if not self.open:
            self._draw_lock(surface)

    def _draw_lock(self, surface):
        cx, cy = round(self.x), round(self.y)
        hh    = self._hh()
        lid_h = _HEIGHT // 3
        lx = cx
        ly = cy - hh + lid_h + 4
        # Shackle (arc above the body)
        pygame.draw.arc(surface, _LOCK_COLOR,
                        (lx - 5, ly - 8, 10, 10), 0, math.pi, 2)
        # Lock body
        pygame.draw.rect(surface, _LOCK_COLOR,
                         (lx - 6, ly - 2, 12, 9), border_radius=2)


CHESTS = {
    "chest":        Chest,
    "golden_chest": GoldenChest,
}
