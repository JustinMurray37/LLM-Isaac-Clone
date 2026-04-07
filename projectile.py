import math
import pygame
from constants import COLOR_PROJECTILE


class Projectile:
    def __init__(self, x, y, dx, dy, speed, radius, range_, shrink_rate, vx_bonus=0.0, vy_bonus=0.0, spectral=False, damage=1.0, piercing=False, color=None):
        self.x = float(x)
        self.y = float(y)
        # Full velocity = base direction * speed + inherited player velocity
        self.vx = dx * speed + vx_bonus
        self.vy = dy * speed + vy_bonus
        self.radius = float(radius)
        self.range = range_
        self.shrink_rate = shrink_rate
        self.damage = damage
        self.piercing = piercing
        self.distance = 0.0
        self.spectral = spectral
        self.alive = True
        self.color = color or COLOR_PROJECTILE
        self._hit_ids = set()  # enemies already struck (prevents multi-hit per pass)

    def update(self, dt, room):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.distance += math.hypot(self.vx, self.vy) * dt

        if not room.bounds.collidepoint(self.x, self.y) or (not self.spectral and room.is_wall_at_pixel(self.x, self.y)):
            self.alive = False
            return

        if self.distance > self.range:
            self.radius -= self.shrink_rate * dt
            if self.radius <= 0:
                self.alive = False

    def draw(self, surface):
        r  = max(1, int(self.radius))
        cx, cy = int(self.x), int(self.y)
        pygame.draw.circle(surface, self.color, (cx, cy), r)
        # Shiny highlight: small white spot offset toward upper-left
        hr = max(1, r // 3)
        hx = cx - max(1, r // 3)
        hy = cy - max(1, r // 3)
        pygame.draw.circle(surface, (255, 255, 255), (hx, hy), hr)
