import pygame

_LIFETIME       = 5.0   # seconds before the puddle disappears
_DAMAGE_COOLDOWN = 1.0   # seconds between damage ticks per puddle
_RX, _RY        = 14, 8  # ellipse collision half-radii

_COLORS_GREEN  = ((28, 130, 28), (55, 200, 55), (100, 240, 90), (70, 220, 70))
_COLORS_YELLOW = ((150, 130, 10), (220, 195, 30), (255, 240, 80), (200, 210, 40))


class SlimePuddle:
    def __init__(self, x, y, rx=_RX, ry=_RY, colors=_COLORS_GREEN):
        self.x = float(x)
        self.y = float(y)
        self._rx        = rx
        self._ry        = ry
        self._colors    = colors
        self._life      = _LIFETIME
        self._dmg_timer = 0.0

    @property
    def expired(self):
        return self._life <= 0

    def update(self, dt):
        self._life      -= dt
        self._dmg_timer  = max(0.0, self._dmg_timer - dt)

    def check_damage(self, player):
        if self._dmg_timer > 0 or player.stats.flight:
            return
        dx = player.x - self.x
        dy = player.y - self.y
        if (dx / self._rx) ** 2 + (dy / self._ry) ** 2 <= 1.0:
            player.take_damage(1)
            self._dmg_timer = _DAMAGE_COOLDOWN

    def draw(self, surface):
        cx, cy = round(self.x), round(self.y)
        c_outer, c_main, c_hi, c_bubble = self._colors

        # Shrink slightly as lifetime runs out for a visual cue
        scale = max(0.4, self._life / _LIFETIME)
        rx = max(4, round(self._rx * scale))
        ry = max(2, round(self._ry * scale))

        pygame.draw.ellipse(surface, c_outer,  (cx - rx - 2, cy - ry - 1, (rx + 2) * 2, (ry + 1) * 2))
        pygame.draw.ellipse(surface, c_main,   (cx - rx,     cy - ry,      rx * 2,        ry * 2))
        pygame.draw.ellipse(surface, c_hi,     (cx - rx + 3, cy - ry + 1,  rx - 2,        ry - 1))
        # Bubbles
        pygame.draw.circle(surface, c_bubble, (cx + rx // 3,      cy),           max(1, ry // 2))
        pygame.draw.circle(surface, c_bubble, (cx - rx // 3 - 2,  cy + ry // 3), max(1, ry // 3))
