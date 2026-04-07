import random
import pygame

_MAX_STAINS = 120   # cap per room to avoid unbounded growth


class BloodStain:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        # Pre-randomise the splotch so each stain looks unique
        self._spots = []
        for _ in range(random.randint(3, 6)):
            ox = random.randint(-5, 5)
            oy = random.randint(-5, 5)
            r  = random.randint(1, 3)
            self._spots.append((ox, oy, r))

    def draw(self, surface):
        cx, cy = round(self.x), round(self.y)
        for ox, oy, r in self._spots:
            pygame.draw.circle(surface, (75, 8, 8),  (cx + ox,     cy + oy),     r)
            pygame.draw.circle(surface, (95, 12, 12), (cx + ox - 1, cy + oy - 1), max(1, r - 1))


def add_stain(room, x, y):
    """Append a new stain, evicting the oldest if the cap is reached."""
    if len(room.blood_stains) >= _MAX_STAINS:
        room.blood_stains.pop(0)
    room.blood_stains.append(BloodStain(x, y))
