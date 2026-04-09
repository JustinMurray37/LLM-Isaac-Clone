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
        self._facing_right = True

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

        if self.vx > 0.5:
            self._facing_right = True
        elif self.vx < -0.5:
            self._facing_right = False

        SIZE = 52
        tmp  = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
        cx   = SIZE // 2
        cy   = SIZE // 2 + 4     # shift down so head doesn't clip the top

        _SKIN    = (255, 205, 172)
        _SHADOW  = (218, 162, 128)
        _ROSY    = (248, 148, 138)
        _HAIR    = (172, 132, 64)
        _DIAPER  = (210, 210, 232)
        _DIAP_SH = (172, 172, 200)
        _EYE     = (68,  42,  30)
        _MOUTH   = (190, 72,  68)
        _TEAR    = (148, 200, 255)

        # ---- diaper / body ----
        pygame.draw.ellipse(tmp, _DIAP_SH, (cx - 9,  cy + 7, 18, 11))
        pygame.draw.ellipse(tmp, _DIAPER,  (cx - 9,  cy + 5, 18, 11))
        # diaper waistband
        pygame.draw.line(tmp, _DIAP_SH, (cx - 8, cy + 5), (cx + 8, cy + 5), 1)

        # ---- stubby arms ----
        pygame.draw.line(tmp, _SKIN,   (cx - 7, cy + 4), (cx - 13, cy + 1), 4)
        pygame.draw.circle(tmp, _SKIN, (cx - 13, cy + 1), 3)
        pygame.draw.line(tmp, _SKIN,   (cx + 7, cy + 4), (cx + 13, cy + 1), 4)
        pygame.draw.circle(tmp, _SKIN, (cx + 13, cy + 1), 3)

        # ---- large round head ----
        hr   = 13
        hcy  = cy - 8
        pygame.draw.circle(tmp, _SHADOW, (cx + 1, hcy + 1), hr)
        pygame.draw.circle(tmp, _SKIN,   (cx,     hcy),     hr)

        # ---- hair tuft ----
        pygame.draw.arc(tmp, _HAIR, (cx - 6, hcy - hr - 1,  8, 8),
                        math.radians(0), math.radians(180), 2)
        pygame.draw.arc(tmp, _HAIR, (cx,     hcy - hr + 1,  7, 7),
                        math.radians(10), math.radians(170), 2)

        # ---- rosy cheeks ----
        pygame.draw.circle(tmp, _ROSY, (cx - 7, hcy + 4), 4)
        pygame.draw.circle(tmp, _ROSY, (cx + 7, hcy + 4), 4)

        # ---- scrunched crying eyes (top-arc = ∩ pressed shut) ----
        eye_y = hcy - 1
        for ex in (cx - 5, cx + 4):
            pygame.draw.arc(tmp, _EYE, (ex, eye_y, 6, 4),
                            math.radians(0), math.radians(180), 2)

        # ---- tears ----
        pygame.draw.ellipse(tmp, _TEAR, (cx - 7, hcy + 2, 3, 5))
        pygame.draw.ellipse(tmp, _TEAR, (cx + 4, hcy + 2, 3, 5))

        # ---- open crying mouth ----
        pygame.draw.ellipse(tmp, _MOUTH,        (cx - 4, hcy + 5, 8, 6))
        pygame.draw.ellipse(tmp, (220, 90, 85), (cx - 3, hcy + 5, 6, 3))  # upper lip line

        # ---- specular highlight on forehead ----
        pygame.draw.circle(tmp, (255, 240, 228), (cx - 4, hcy - 5), 3)

        if not self._facing_right:
            tmp = pygame.transform.flip(tmp, True, False)

        surface.blit(tmp, (round(self.x) - SIZE // 2, round(self.y) - SIZE // 2))
