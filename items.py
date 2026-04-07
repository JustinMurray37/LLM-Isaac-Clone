import pygame
from item import Item


class SpeedBoost(Item):
    name = "Speed Boost"
    color = (100, 255, 100)

    def apply(self, stats):
        stats.speed += 50

    def draw_icon(self, surface, cx, cy):
        _SOLE   = (50,  50,  50)
        _UPPER  = (100, 220, 100)
        _LACE   = (220, 220, 220)
        _TONGUE = (80,  190, 80)

        # Draw two sneakers side by side
        for ox in (-6, 5):
            bx = cx + ox
            # Sole
            pygame.draw.rect(surface, _SOLE,  (bx - 1, cy + 3, 8, 3), border_radius=1)
            # Upper body
            pygame.draw.rect(surface, _UPPER, (bx,     cy - 2, 7, 6), border_radius=2)
            # Tongue flap
            pygame.draw.rect(surface, _TONGUE,(bx + 2, cy - 4, 3, 4))
            # Lace — single horizontal line
            pygame.draw.line(surface, _LACE,  (bx + 1, cy),  (bx + 6, cy), 1)



class RapidFire(Item):
    name = "Rapid Fire"
    color = (255, 150, 50)

    def apply(self, stats):
        stats.fire_cooldown = max(0.05, stats.fire_cooldown - 0.05)

    def draw_icon(self, surface, cx, cy):
        _PROJ  = (160, 210, 255)
        _SHINE = (230, 245, 255)
        r = 4
        for ox in (-9, 0, 9):
            pcx = cx + ox
            pygame.draw.circle(surface, _PROJ,  (pcx, cy), r)
            pygame.draw.circle(surface, _SHINE, (pcx - 1, cy - 1), max(1, r // 3))


class PowerShot(Item):
    name = "Power Shot"
    color = (255, 80, 80)

    def apply(self, stats):
        stats.projectile_speed += 75

    def draw_icon(self, surface, cx, cy):
        _PROJ  = (160, 210, 255)
        _SHINE = (230, 245, 255)
        _LINE  = (200, 200, 220)

        # Speed lines (tapered, trailing left)
        for oy, length in [(-2, 10), (0, 14), (2, 10)]:
            x0 = cx - 8 - length
            x1 = cx - 8
            pygame.draw.line(surface, _LINE, (x0, cy + oy), (x1, cy + oy), 1)

        # Projectile ball
        r = 5
        pygame.draw.circle(surface, _PROJ,  (cx + 3, cy), r)
        pygame.draw.circle(surface, _SHINE, (cx + 2, cy - 2), max(1, r // 3))


class LongRange(Item):
    name = "Long Range"
    color = (200, 100, 255)

    def apply(self, stats):
        stats.projectile_range += 100



class SharpShot(Item):
    name = "Sharp Shot"
    color = (255, 220, 80)

    def apply(self, stats):
        stats.projectile_damage += 0.5

    def draw_icon(self, surface, cx, cy):
        _METAL  = (200, 200, 210)
        _SHINE  = (240, 240, 255)
        _SHADOW = (120, 120, 130)
        # Shaft
        pygame.draw.rect(surface, _METAL,  (cx - 2, cy - 4, 4, 12))
        pygame.draw.line(surface, _SHINE,  (cx - 1, cy - 4), (cx - 1, cy + 8), 1)
        # Point (upward triangle)
        pygame.draw.polygon(surface, _METAL, [(cx, cy - 12), (cx - 4, cy - 4), (cx + 4, cy - 4)])
        pygame.draw.line(surface, _SHINE,    (cx, cy - 12),  (cx - 1, cy - 5), 1)
        # Flat head (nail cap) at bottom
        pygame.draw.rect(surface, _SHADOW, (cx - 5, cy + 8, 10, 3), border_radius=1)
        pygame.draw.line(surface, _SHINE,  (cx - 4, cy + 8), (cx + 4, cy + 8), 1)


class HeavyShot(Item):
    name = "Heavy Shot"
    color = (180, 80, 220)

    def apply(self, stats):
        stats.projectile_damage  += 2.0
        stats.projectile_radius  += 5.0
        stats.projectile_speed   -= 80.0
        stats.projectile_range   -= 80.0
        stats.fire_cooldown      += 0.20

    def draw_icon(self, surface, cx, cy):
        _BODY  = (160, 160, 170)
        _SHINE = (220, 220, 235)
        _SHADE = (90,  90,  100)
        r = 8
        pygame.draw.circle(surface, _SHADE, (cx + 1, cy + 1), r)
        pygame.draw.circle(surface, _BODY,  (cx,     cy),     r)
        pygame.draw.circle(surface, _SHINE, (cx - 3, cy - 3), max(2, r // 3))


class SoyMilk(Item):
    name = "Soy Milk"
    color = (230, 230, 180)

    def apply(self, stats):
        stats.fire_cooldown      = 0.1
        stats.projectile_damage  *= 0.5
        stats.projectile_radius  *= 0.5

    def draw_icon(self, surface, cx, cy):
        _DROP  = (235, 235, 170)
        _SHINE = (255, 255, 220)
        # Teardrop: circle for the body, triangle for the tip pointing up
        pygame.draw.circle(surface, _DROP, (cx, cy + 3), 7)
        pygame.draw.polygon(surface, _DROP, [(cx, cy - 9), (cx - 5, cy - 1), (cx + 5, cy - 1)])
        # Highlight
        pygame.draw.circle(surface, _SHINE, (cx - 2, cy + 1), 2)


class HealthUp(Item):
    name = "Health Up"
    color = (220, 60, 60)

    def apply(self, stats):
        stats.max_health += 2
        stats.health      = min(stats.health + 2, stats.max_health)

    def draw_icon(self, surface, cx, cy):
        _FILL = (210, 40,  40)
        _HI1  = (255, 130, 130)
        _HI2  = (255, 200, 200)
        r = 6
        # Two circles for the top lobes
        pygame.draw.circle(surface, _FILL, (cx - r // 2, cy - r // 3), r // 2 + 2)
        pygame.draw.circle(surface, _FILL, (cx + r // 2, cy - r // 3), r // 2 + 2)
        # Triangle for the bottom point
        pygame.draw.polygon(surface, _FILL, [
            (cx - r,     cy - r // 3),
            (cx + r,     cy - r // 3),
            (cx,         cy + r + 1),
        ])
        # Highlights
        pygame.draw.circle(surface, _HI1, (cx - 3, cy - 3), 2)
        pygame.draw.circle(surface, _HI2, (cx - 2, cy - 4), 1)


class PiercingShot(Item):
    name = "Piercing Shot"
    color = (255, 180, 80)

    def apply(self, stats):
        stats.piercing_shot = True

    def draw_icon(self, surface, cx, cy):
        _SHAFT  = (180, 140, 80)
        _TIP    = (210, 210, 220)
        _FLETCH = (200, 80,  80)
        _SHINE  = (240, 240, 255)
        # Shaft (horizontal, pointing right)
        pygame.draw.line(surface, _SHAFT,  (cx - 10, cy), (cx + 6, cy), 2)
        # Arrowhead tip
        pygame.draw.polygon(surface, _TIP, [(cx + 12, cy), (cx + 5, cy - 3), (cx + 5, cy + 3)])
        pygame.draw.line(surface, _SHINE,  (cx + 6,  cy - 1), (cx + 11, cy), 1)
        # Fletching (two small angled lines at the rear)
        pygame.draw.line(surface, _FLETCH, (cx - 10, cy), (cx - 7, cy - 4), 2)
        pygame.draw.line(surface, _FLETCH, (cx - 10, cy), (cx - 7, cy + 4), 2)


class SpectralShot(Item):
    name = "Spectral Shot"
    color = (180, 255, 220)

    def apply(self, stats):
        stats.spectral_shot = True


class Flight(Item):
    name = "Flight"
    color = (180, 220, 255)

    def apply(self, stats):
        stats.flight = True

    def draw_icon(self, surface, cx, cy):
        _WING    = (190, 225, 255)
        _FEATHER = (150, 195, 240)
        _EDGE    = (220, 240, 255)
        # Left wing
        pygame.draw.polygon(surface, _WING, [
            (cx - 1,  cy),
            (cx - 5,  cy - 5),
            (cx - 12, cy - 3),
            (cx - 13, cy + 4),
            (cx - 6,  cy + 5),
        ])
        pygame.draw.polygon(surface, _EDGE, [
            (cx - 5,  cy - 5),
            (cx - 12, cy - 3),
            (cx - 13, cy + 4),
        ], 1)
        # Feather division lines on left wing
        for tip in [(cx - 10, cy - 4), (cx - 7, cy - 5)]:
            pygame.draw.line(surface, _FEATHER, (cx - 3, cy + 2), tip, 1)
        # Right wing (mirror)
        pygame.draw.polygon(surface, _WING, [
            (cx + 1,  cy),
            (cx + 5,  cy - 5),
            (cx + 12, cy - 3),
            (cx + 13, cy + 4),
            (cx + 6,  cy + 5),
        ])
        pygame.draw.polygon(surface, _EDGE, [
            (cx + 5,  cy - 5),
            (cx + 12, cy - 3),
            (cx + 13, cy + 4),
        ], 1)
        for tip in [(cx + 10, cy - 4), (cx + 7, cy - 5)]:
            pygame.draw.line(surface, _FEATHER, (cx + 3, cy + 2), tip, 1)


# Registry: maps a string key to the item class.
# Use this to spawn items by name, e.g. ITEMS["speed_boost"](x, y)
ITEMS = {
    "speed_boost":  SpeedBoost,
    "rapid_fire":   RapidFire,
    "power_shot":   PowerShot,
    "long_range":   LongRange,
    "sharp_shot":    SharpShot,
    "heavy_shot":    HeavyShot,
    "soy_milk":      SoyMilk,
    "health_up":     HealthUp,
    "piercing_shot": PiercingShot,
    "spectral_shot": SpectralShot,
    "flight":        Flight,
}
