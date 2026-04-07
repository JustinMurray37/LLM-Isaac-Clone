import math
import pygame

TOUCH_RADIUS = 24   # how close the player centre must be to trigger descent


class Ladder:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def check_touch(self, player):
        return math.hypot(player.x - self.x, player.y - self.y) < TOUCH_RADIUS + player.stats.size / 2

    def draw(self, surface):
        cx, cy = round(self.x), round(self.y)

        _RIM_OUT  = (95,  75, 48)   # outer rim of the hole
        _RIM_IN   = (55,  42, 26)   # inner rim shadow
        _PIT      = (12,   9,  5)   # the dark pit
        _WOOD     = (118, 80, 38)   # ladder rails and rungs
        _WOOD_DK  = ( 72, 48, 18)   # rung shadow edge
        _HIGHLIGHT = (160, 120, 65) # rim highlight

        # Outer ground rim
        pygame.draw.ellipse(surface, _RIM_OUT, (cx - 36, cy - 26, 72, 52))
        # Inner shadow rim
        pygame.draw.ellipse(surface, _RIM_IN,  (cx - 30, cy - 20, 60, 40))
        # Pit
        pygame.draw.ellipse(surface, _PIT,     (cx - 26, cy - 17, 52, 34))

        # Highlight arc on the near (bottom) rim edge
        pygame.draw.arc(surface, _HIGHLIGHT,
                        (cx - 36, cy - 26, 72, 52),
                        math.radians(200), math.radians(340), 2)

        # Ladder: two vertical rails + evenly spaced rungs
        rx1, rx2   = cx - 9,  cx + 9
        rail_top   = cy - 14
        rail_bot   = cy + 14
        rung_gap   = 9

        pygame.draw.line(surface, _WOOD, (rx1, rail_top), (rx1, rail_bot), 3)
        pygame.draw.line(surface, _WOOD, (rx2, rail_top), (rx2, rail_bot), 3)

        ry = rail_top + 5
        while ry <= rail_bot - 3:
            pygame.draw.line(surface, _WOOD,    (rx1, ry),     (rx2, ry),     2)
            pygame.draw.line(surface, _WOOD_DK, (rx1, ry + 1), (rx2, ry + 1), 1)
            ry += rung_gap
