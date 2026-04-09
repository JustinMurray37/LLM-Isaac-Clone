import math
import pygame

_PUSH_SPEED = 180.0   # px/s impulse when the player shoves a pickup
_FRICTION   = 350.0   # px/s² deceleration


class Pickup:
    """
    Base class for consumable pickups that are used on contact and then removed.
    Unlike Items, pickups receive the full player object so they can affect
    health and other non-stat attributes.

    When can_collect() returns False and the player overlaps, the pickup
    behaves as a physics object: it is pushed away and slides to a stop.
    Subclasses override apply(player) and set color/radius/name.
    """

    color  = (200, 200, 200)
    radius = 8
    name   = "Pickup"

    def __init__(self, x, y):
        self.x  = float(x)
        self.y  = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.collected = False

    def apply(self, player):
        """Apply the pickup effect to the player. Override in subclasses."""
        raise NotImplementedError

    def can_collect(self, player):
        """Return True if the player is eligible to collect this pickup."""
        return True

    def update(self, dt, room):
        """Advance physics: move, collide with room walls, apply friction."""
        if self.vx == 0.0 and self.vy == 0.0:
            return

        self.x += self.vx * dt
        self.y += self.vy * dt

        # Clamp to playable bounds
        r = self.radius
        bounds = room.bounds
        self.x = max(self.x, bounds.left   + r)
        self.x = min(self.x, bounds.right  - r)
        self.y = max(self.y, bounds.top    + r)
        self.y = min(self.y, bounds.bottom - r)

        # Tile collision — zero out velocity on the corrected axis
        new_x, new_y = room.resolve_position(self.x, self.y, r)
        if abs(new_x - self.x) > 0.1:
            self.vx = 0.0
        if abs(new_y - self.y) > 0.1:
            self.vy = 0.0
        self.x, self.y = new_x, new_y

        # Friction
        speed = math.hypot(self.vx, self.vy)
        if speed > 0:
            slow = min(speed, _FRICTION * dt)
            scale = (speed - slow) / speed
            self.vx *= scale
            self.vy *= scale

    def check_collection(self, player):
        if self.collected:
            return
        dx = self.x - player.x
        dy = self.y - player.y
        dist_sq  = dx * dx + dy * dy
        min_dist = player.stats.size / 2 + self.radius

        if dist_sq > min_dist * min_dist:
            return

        if self.can_collect(player):
            self.apply(player)
            self.collected = True
        else:
            # Physics push: resolve overlap and apply impulse
            dist = math.sqrt(dist_sq)
            if dist > 0:
                nx, ny = dx / dist, dy / dist
            else:
                nx, ny = 1.0, 0.0
            self.x = player.x + nx * min_dist
            self.y = player.y + ny * min_dist
            self.vx = nx * _PUSH_SPEED
            self.vy = ny * _PUSH_SPEED

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (round(self.x), round(self.y)), self.radius)


class Heart(Pickup):
    """Heals the player for 2 HP. Cannot be collected at full health."""

    color  = (220, 60, 80)
    radius = 9
    name   = "Heart"

    def can_collect(self, player):
        return player.stats.health < player.stats.max_health

    def apply(self, player):
        player.stats.health = min(player.stats.health + 2, player.stats.max_health)

    def draw(self, surface):
        cx, cy = round(self.x), round(self.y)
        r = self.radius
        pygame.draw.circle(surface, self.color, (cx - r // 2, cy - r // 3), r // 2 + 1)
        pygame.draw.circle(surface, self.color, (cx + r // 2, cy - r // 3), r // 2 + 1)
        pygame.draw.polygon(surface, self.color, [
            (cx - r, cy - r // 3),
            (cx + r, cy - r // 3),
            (cx,     cy + r),
        ])


class HalfHeart(Pickup):
    """Heals the player for 1 HP. Cannot be collected at full health."""

    color  = (220, 60, 80)
    radius = 6
    name   = "Half Heart"

    def can_collect(self, player):
        return player.stats.health < player.stats.max_health

    def apply(self, player):
        player.stats.health = min(player.stats.health + 1, player.stats.max_health)

    def draw(self, surface):
        cx, cy = round(self.x), round(self.y)
        r = self.radius
        # Left lobe only (right half clipped)
        old_clip = surface.get_clip()
        surface.set_clip(pygame.Rect(cx - r - 1, cy - r - 1, r + 2, r * 3))
        pygame.draw.circle(surface, self.color, (cx - r // 2, cy - r // 3), r // 2 + 1)
        pygame.draw.circle(surface, self.color, (cx + r // 2, cy - r // 3), r // 2 + 1)
        pygame.draw.polygon(surface, self.color, [
            (cx - r, cy - r // 3),
            (cx + r, cy - r // 3),
            (cx,     cy + r),
        ])
        surface.set_clip(old_clip)
        # Vertical dividing line down the centre
        pygame.draw.line(surface, (255, 120, 140),
                         (cx, cy - r // 3 - r // 2),
                         (cx, cy + r - 1), 1)


class Key(Pickup):
    """Gives the player one key."""

    color  = (220, 180, 50)
    radius = 8
    name   = "Key"

    def apply(self, player):
        player.stats.keys += 1

    def draw(self, surface):
        _draw_key_shape(surface, self.color, round(self.x), round(self.y), self.radius)


def _draw_key_shape(surface, color, cx, cy, r):
    """Draw a horizontal key: circular head on the left, toothed shaft to the right."""
    hx = cx - r // 2   # head centre x
    # Head
    pygame.draw.circle(surface, color, (hx, cy), r // 2 + 1)
    # Hole
    pygame.draw.circle(surface, (40, 40, 55), (hx, cy), r // 4)
    # Shaft
    pygame.draw.rect(surface, color, (hx, cy - 1, r + r // 2, 3))
    # Two teeth
    pygame.draw.rect(surface, color, (cx + r // 4,     cy + 1, 2, r // 3 + 1))
    pygame.draw.rect(surface, color, (cx + r // 4 + 4, cy + 1, 2, r // 4 + 1))


class Bomb(Pickup):
    """Gives the player one bomb."""

    color  = (45, 45, 55)
    radius = 8
    name   = "Bomb"

    def apply(self, player):
        player.stats.bombs += 1

    def draw(self, surface):
        cx, cy = round(self.x), round(self.y)
        r = self.radius
        # Body
        pygame.draw.circle(surface, self.color, (cx, cy + 2), r - 1)
        # Highlight
        pygame.draw.circle(surface, (80, 80, 100), (cx - r // 3, cy - r // 3 + 2), r // 4 + 1)
        # Fuse
        fx, fy = cx + r // 2, cy - r // 2 + 2
        pygame.draw.line(surface, (160, 130, 80), (fx, fy), (fx + r // 2, fy - r // 2), 2)
        # Spark
        pygame.draw.circle(surface, (255, 210, 60), (fx + r // 2, fy - r // 2), 2)


PICKUPS = {
    "heart":      Heart,
    "half_heart": HalfHeart,
    "key":        Key,
    "bomb":       Bomb,
}
