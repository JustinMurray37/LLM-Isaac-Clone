import math
import pygame
from constants import COLOR_PLAYER
from projectile import Projectile
from stats import PlayerStats

_FLASH_DURATION = 1.0   # seconds the flash effect lasts after a hit
_FLASH_RATE     = 0.1   # seconds per visible/invisible half-cycle (5 flashes)


def _move_toward(current, target, step):
    """Advance current toward target by at most step, without overshooting."""
    diff = target - current
    if abs(diff) <= step:
        return target
    return current + math.copysign(step, diff)


class Player:
    def __init__(self, x, y, stats=None):
        self.x = float(x)
        self.y = float(y)
        self.stats = stats or PlayerStats()
        self.vx = 0.0
        self.vy = 0.0
        self.fire_timer = 0.0
        self._flash_timer = 0.0
        self._spike_timer = 0.0

    def update(self, dt, keys, room, open_sides=frozenset()):
        dx, dy = 0.0, 0.0
        if keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_s]: dy += 1
        if keys[pygame.K_a]: dx -= 1
        if keys[pygame.K_d]: dx += 1

        length = math.hypot(dx, dy)
        if length:
            target_vx = (dx / length) * self.stats.speed
            target_vy = (dy / length) * self.stats.speed
        else:
            target_vx, target_vy = 0.0, 0.0

        # Ramp velocity toward target at a fixed rate so accel and decel
        # always take exactly ramp_time seconds
        step = (self.stats.speed / self.stats.ramp_time) * dt
        self.vx = _move_toward(self.vx, target_vx, step)
        self.vy = _move_toward(self.vy, target_vy, step)

        self.x += self.vx * dt
        self.y += self.vy * dt

        # Clamp to outer room boundary, leaving doorway sides open
        half = self.stats.size / 2
        bounds = room.bounds
        if "left"  not in open_sides:
            self.x = max(self.x, bounds.left   + half)
        if "right" not in open_sides:
            self.x = min(self.x, bounds.right  - half)
        if "up"    not in open_sides:
            self.y = max(self.y, bounds.top    + half)
        if "down"  not in open_sides:
            self.y = min(self.y, bounds.bottom - half)
        if not self.stats.flight:
            self.x, self.y = room.resolve_position(self.x, self.y, half)

        if self.fire_timer > 0:
            self.fire_timer -= dt
        if self._flash_timer > 0:
            self._flash_timer -= dt
        if self._spike_timer > 0:
            self._spike_timer -= dt

    def take_damage(self, amount):
        self.stats.health -= amount
        self._flash_timer = _FLASH_DURATION

    @property
    def can_shoot(self):
        return self.fire_timer <= 0

    def shoot(self, dx, dy):
        self.fire_timer = self.stats.fire_cooldown
        vx_bonus = self.vx * self.stats.projectile_inherit_velocity
        vy_bonus = self.vy * self.stats.projectile_inherit_velocity
        return Projectile(
            self.x, self.y, dx, dy,
            self.stats.projectile_speed,
            self.stats.projectile_radius,
            self.stats.projectile_range,
            self.stats.projectile_shrink_rate,
            vx_bonus, vy_bonus,
            spectral=self.stats.spectral_shot,
            damage=self.stats.projectile_damage,
            piercing=self.stats.piercing_shot,
        )

    def draw(self, surface):
        # Skip every other flash interval so the player flickers
        if self._flash_timer > 0 and int(self._flash_timer / _FLASH_RATE) % 2 == 0:
            return

        cx, cy = round(self.x), round(self.y)

        _BODY_COLOR = COLOR_PLAYER          # (100, 200, 100)
        _BODY_SHADE = (70,  145,  70)       # darker inner shadow on body
        _HEAD_COLOR = (125, 220, 125)       # slightly brighter head
        _HIGHLIGHT  = (220, 255, 220)       # specular dot

        # ---- Body: top half of an oval, flat edge facing down ----
        bw, bh   = 22, 20
        oval_top = cy + 1                   # top of the full oval rect
        body_rect = pygame.Rect(cx - bw // 2, oval_top, bw, bh)

        old_clip = surface.get_clip()
        # Clip so only the upper half of the ellipse is visible
        surface.set_clip(pygame.Rect(cx - bw // 2, oval_top, bw, bh // 2 + 1))
        # Subtle inner shadow: slightly smaller, offset ellipse drawn first
        pygame.draw.ellipse(surface, _BODY_SHADE,
                            pygame.Rect(cx - bw // 2 + 2, oval_top + 3, bw - 3, bh - 2))
        pygame.draw.ellipse(surface, _BODY_COLOR, body_rect)
        surface.set_clip(old_clip)

        # ---- Head: sphere with specular highlight ----
        head_r  = 8
        head_cy = oval_top - head_r + 2     # sits just above body dome
        pygame.draw.circle(surface, _HEAD_COLOR, (cx, head_cy), head_r)
        pygame.draw.circle(surface, _HIGHLIGHT,  (cx - 2, head_cy - 2), max(1, head_r // 3))
