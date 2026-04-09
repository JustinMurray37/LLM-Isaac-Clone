import math
import random
import pygame
from constants import TILE_SIZE
from enemy_stats import EnemyStats
from projectile import Projectile
from pathfinding import line_of_sight, find_path

_PATH_RECOMPUTE_INTERVAL = 0.5    # seconds between A* calls

CHAMPION_CHANCE = 0.02   # updated by main.py each level; 2% + 1% per level, max 10%
CURRENT_LEVEL   = 1      # updated by main.py; scales enemy health and projectile speed
_KNOCKBACK_SPEED         = 120.0  # px/s impulse applied on projectile hit
_KNOCKBACK_DECAY         = 500.0  # px/s² — how fast knockback fades (same for all enemies)



def resolve_enemy_collisions(enemies, room):
    """Push overlapping enemies apart. Only enemies of the same flight type interact."""
    alive = [e for e in enemies if e.alive]
    for i in range(len(alive)):
        a = alive[i]
        for j in range(i + 1, len(alive)):
            b = alive[j]
            if a.stats.flight != b.stats.flight:
                continue
            min_dist = a.stats.size / 2 + b.stats.size / 2
            dx = a.x - b.x
            dy = a.y - b.y
            dist = math.hypot(dx, dy)
            if dist >= min_dist:
                continue
            if dist > 0:
                nx, ny = dx / dist, dy / dist
            else:
                nx, ny = 1.0, 0.0
            push = (min_dist - dist) / 2
            a.x += nx * push
            a.y += ny * push
            b.x -= nx * push
            b.y -= ny * push
            if not a.stats.flight:
                a.x, a.y = room.resolve_position(a.x, a.y, a.stats.size / 2)
                b.x, b.y = room.resolve_position(b.x, b.y, b.stats.size / 2)


def _move_toward(current, target, step):
    diff = target - current
    if abs(diff) <= step:
        return target
    return current + math.copysign(step, diff)


class Enemy:
    """
    Base enemy class. Subclass and override update() to implement AI behaviour.
    Stats are stored on self.stats so they can be read or modified at runtime.
    """

    _champion_eligible = True

    def __init__(self, x, y, stats=None):
        self.x = float(x)
        self.y = float(y)
        self.stats = stats or EnemyStats()
        self.vx = 0.0
        self.vy = 0.0
        self.fire_timer = 0.0
        self._path = []
        self._path_timer = 0.0
        self._kb_vx = 0.0   # knockback velocity, decays independently of AI movement
        self._kb_vy = 0.0
        # Scale health and projectile speed by 1.1 per level above 1
        _scale = 1.1 ** (CURRENT_LEVEL - 1)
        self.stats.health          *= _scale
        self.stats.max_health      *= _scale
        self.stats.projectile_speed *= _scale

        self._hit_flash = 0
        self.contact_damage = 1
        self.champion = self._champion_eligible and random.random() < CHAMPION_CHANCE
        if self.champion:
            self.stats.health         *= 1.5
            self.stats.max_health     *= 1.5
            self.stats.projectile_damage *= 2.0
            self.contact_damage        = 2

    # ------------------------------------------------------------------
    # State

    @property
    def alive(self):
        return self.stats.health > 0

    def take_damage(self, amount):
        self.stats.health -= amount
        self._hit_flash = 4

    def apply_knockback(self, dx, dy):
        """Set a fixed-speed knockback impulse in direction (dx, dy).
        Stored separately so AI movement cannot immediately overwrite it."""
        length = math.hypot(dx, dy)
        if length:
            self._kb_vx = (dx / length) * _KNOCKBACK_SPEED
            self._kb_vy = (dy / length) * _KNOCKBACK_SPEED

    # ------------------------------------------------------------------
    # Movement helpers (available to subclasses)

    def _apply_velocity(self, dt, room):
        """Move by current velocity (plus any active knockback) and resolve tile collisions."""
        self.x += (self.vx + self._kb_vx) * dt
        self.y += (self.vy + self._kb_vy) * dt

        half = self.stats.size / 2
        bounds = room.bounds
        self.x = min(max(self.x, bounds.left + half), bounds.right - half)
        self.y = min(max(self.y, bounds.top + half), bounds.bottom - half)
        if not self.stats.flight:
            self.x, self.y = room.resolve_position(self.x, self.y, half)

    def _move_toward_point(self, tx, ty, dt):
        """Accelerate toward (tx, ty) up to self.stats.speed."""
        dx = tx - self.x
        dy = ty - self.y
        length = math.hypot(dx, dy)
        if length:
            target_vx = (dx / length) * self.stats.speed
            target_vy = (dy / length) * self.stats.speed
        else:
            target_vx = target_vy = 0.0

        step = (self.stats.speed / self.stats.ramp_time) * dt
        self.vx = _move_toward(self.vx, target_vx, step)
        self.vy = _move_toward(self.vy, target_vy, step)

    def _navigate_toward(self, dt, room, target_x, target_y):
        """
        Move toward (target_x, target_y) directly when LOS is clear,
        otherwise follow an A* path around obstacles.
        """
        self._path_timer -= dt

        if self.stats.flight or line_of_sight(room, self.x, self.y, target_x, target_y):
            self._path = []
            self._move_toward_point(target_x, target_y, dt)
            return

        # Recompute path when the timer expires or the current path runs out
        if not self._path or self._path_timer <= 0:
            self._path = find_path(room, self.x, self.y, target_x, target_y)
            self._path_timer = _PATH_RECOMPUTE_INTERVAL

        if self._path:
            wx, wy = self._path[0]
            self._move_toward_point(wx, wy, dt)
            if math.hypot(wx - self.x, wy - self.y) < TILE_SIZE / 2:
                self._path.pop(0)
        else:
            # No path found; try moving directly as a fallback
            self._move_toward_point(target_x, target_y, dt)

    def _push_from_player(self, player, room):
        """Push this enemy out of overlap with the player."""
        half_e = self.stats.size / 2
        half_p = player.stats.size / 2
        min_dist = half_e + half_p
        dx = self.x - player.x
        dy = self.y - player.y
        dist = math.hypot(dx, dy)
        if dist < min_dist:
            if dist > 0:
                self.x = player.x + dx / dist * min_dist
                self.y = player.y + dy / dist * min_dist
            else:
                self.x += min_dist  # exactly overlapping — push arbitrarily
            self.x, self.y = room.resolve_position(self.x, self.y, half_e)

    def _stop(self, dt):
        """Decelerate to a standstill."""
        step = (self.stats.speed / self.stats.ramp_time) * dt
        self.vx = _move_toward(self.vx, 0.0, step)
        self.vy = _move_toward(self.vy, 0.0, step)

    # ------------------------------------------------------------------
    # Firing helpers

    def _shoot_toward(self, tx, ty):
        """Return a Projectile aimed at (tx, ty), or None if on top of target."""
        dx = tx - self.x
        dy = ty - self.y
        length = math.hypot(dx, dy)
        if not length:
            return None
        self.fire_timer = self.stats.fire_cooldown
        return Projectile(
            self.x, self.y,
            dx / length, dy / length,
            self.stats.projectile_speed,
            self.stats.projectile_radius,
            self.stats.projectile_range,
            self.stats.projectile_shrink_rate,
            color=(160, 30, 30),
        )

    # ------------------------------------------------------------------
    # Override in subclasses

    def update(self, dt, _room, _player):
        """
        Called every frame. Override to implement AI behaviour.
        Use _move_toward_point / _stop / _shoot_toward / _apply_velocity.
        Return a list of any Projectiles fired this frame (may be empty).
        """
        if self._hit_flash > 0:
            self._hit_flash -= 1
        if self.fire_timer > 0:
            self.fire_timer -= dt

        # Decay knockback at a fixed rate regardless of enemy speed
        decay = _KNOCKBACK_DECAY * dt
        self._kb_vx = _move_toward(self._kb_vx, 0.0, decay)
        self._kb_vy = _move_toward(self._kb_vy, 0.0, decay)
        return []

    # ------------------------------------------------------------------
    # Drawing

    def draw(self, surface):
        cx, cy = round(self.x), round(self.y)

        _BODY_COLOR = (175, 55, 55)
        _BODY_SHADE = (120, 35, 35)
        _HEAD_COLOR = (205, 80, 75)
        _HIGHLIGHT  = (255, 180, 175)

        # Body: top half of an oval, flat edge facing down
        bw, bh   = 22, 20
        oval_top = cy + 1
        body_rect = pygame.Rect(cx - bw // 2, oval_top, bw, bh)

        old_clip = surface.get_clip()
        surface.set_clip(pygame.Rect(cx - bw // 2, oval_top, bw, bh // 2 + 1))
        pygame.draw.ellipse(surface, _BODY_SHADE,
                            pygame.Rect(cx - bw // 2 + 2, oval_top + 3, bw - 3, bh - 2))
        pygame.draw.ellipse(surface, _BODY_COLOR, body_rect)
        surface.set_clip(old_clip)

        # Head: sphere with specular highlight
        head_r  = 8
        head_cy = oval_top - head_r + 2
        pygame.draw.circle(surface, _HEAD_COLOR, (cx, head_cy), head_r)
        pygame.draw.circle(surface, _HIGHLIGHT,  (cx - 2, head_cy - 2), max(1, head_r // 3))

        self._draw_hit_flash(surface)
        self._draw_champion_overlay(surface)

    def _draw_hit_flash(self, surface):
        if not self._hit_flash:
            return
        cx, cy = round(self.x), round(self.y)
        r = self.stats.size // 2
        flash = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(flash, (255, 50, 50, 180), (r, r), r)
        surface.blit(flash, (cx - r, cy - r))

    def _draw_champion_overlay(self, surface):
        if not self.champion:
            return
        cx, cy = round(self.x), round(self.y)
        r = self.stats.size // 2 + 5
        pygame.draw.circle(surface, (255, 200,  40), (cx, cy), r,     2)
        pygame.draw.circle(surface, (255, 240, 130), (cx, cy), r + 2, 1)
