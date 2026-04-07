import math
import pygame
from enemy import Enemy
from enemy_stats import EnemyStats
from pathfinding import line_of_sight


class Zombie(Enemy):
    """
    Slowly chases the player and deals 1 damage on contact.
    Cannot fire projectiles.
    """

    CONTACT_RANGE  = 20    # pixels between centres to count as a hit
    DAMAGE_COOLDOWN = 1.0  # seconds between damage ticks

    def __init__(self, x, y):
        stats = EnemyStats(health=6.0, speed=70.0, ramp_time=0.3)
        super().__init__(x, y, stats)
        self._damage_timer = 0.0

    def update(self, dt, room, player):
        super().update(dt, room, player)
        self._navigate_toward(dt, room, player.x, player.y)
        self._apply_velocity(dt, room)
        self._push_from_player(player, room)

        if self._damage_timer > 0:
            self._damage_timer -= dt
        if self._damage_timer <= 0:
            if math.hypot(player.x - self.x, player.y - self.y) <= self.CONTACT_RANGE + player.stats.size / 2:
                player.take_damage(self.contact_damage)
                self._damage_timer = self.DAMAGE_COOLDOWN

        return []


class RangedZombie(Enemy):
    """
    Chases the player and fires projectiles when it has line of sight.
    """

    _PROJ_COLOR = (220, 120, 50)

    def __init__(self, x, y):
        stats = EnemyStats(
            health=6.0,
            speed=50.0,
            ramp_time=0.4,
            fire_cooldown=2.0,
            projectile_speed=180.0,
            projectile_radius=5.0,
            projectile_range=350.0,
            projectile_shrink_rate=25.0,
        )
        super().__init__(x, y, stats)

    def update(self, dt, room, player):
        super().update(dt, room, player)

        has_los = line_of_sight(room, self.x, self.y, player.x, player.y, ignore_gaps=True)

        self._navigate_toward(dt, room, player.x, player.y)
        self._apply_velocity(dt, room)
        self._push_from_player(player, room)

        projectiles = []
        if has_los and self.fire_timer <= 0:
            proj = self._shoot_toward(player.x, player.y)
            if proj:
                proj.color = self._PROJ_COLOR
                projectiles.append(proj)
        return projectiles


class Bat(Enemy):
    """
    Fast flying enemy that deals contact damage. Ignores walls and gaps.
    Cannot fire projectiles.
    """

    CONTACT_RANGE  = 16
    DAMAGE_COOLDOWN = 1.0

    def __init__(self, x, y):
        stats = EnemyStats(
            health=4.0,
            speed=130.0,
            ramp_time=0.15,
            flight=True,
        )
        super().__init__(x, y, stats)
        self._damage_timer = 0.0

    def update(self, dt, room, player):
        super().update(dt, room, player)
        self._navigate_toward(dt, room, player.x, player.y)
        self._apply_velocity(dt, room)
        self._push_from_player(player, room)

        if self._damage_timer > 0:
            self._damage_timer -= dt
        if self._damage_timer <= 0:
            if math.hypot(player.x - self.x, player.y - self.y) <= self.CONTACT_RANGE + player.stats.size / 2:
                player.take_damage(self.contact_damage)
                self._damage_timer = self.DAMAGE_COOLDOWN

        return []

    def draw(self, surface):
        cx, cy = round(self.x), round(self.y)

        _WING  = (50, 35, 62)
        _WING_EDGE = (70, 50, 85)
        _BODY  = (78, 55, 92)
        _HEAD  = (95, 70, 110)
        _EAR   = (65, 44, 78)
        _EYE   = (255, 75, 75)

        # Left wing
        pygame.draw.polygon(surface, _WING, [
            (cx - 1, cy - 1), (cx - 5, cy - 4), (cx - 13, cy - 5),
            (cx - 15, cy + 1), (cx - 10, cy + 6), (cx - 3, cy + 3),
        ])
        pygame.draw.polygon(surface, _WING_EDGE, [
            (cx - 5, cy - 4), (cx - 13, cy - 5), (cx - 15, cy + 1),
        ], 1)
        # Right wing (mirrored)
        pygame.draw.polygon(surface, _WING, [
            (cx + 1, cy - 1), (cx + 5, cy - 4), (cx + 13, cy - 5),
            (cx + 15, cy + 1), (cx + 10, cy + 6), (cx + 3, cy + 3),
        ])
        pygame.draw.polygon(surface, _WING_EDGE, [
            (cx + 5, cy - 4), (cx + 13, cy - 5), (cx + 15, cy + 1),
        ], 1)

        # Body
        pygame.draw.circle(surface, _BODY, (cx, cy + 1), 5)

        # Ears
        pygame.draw.polygon(surface, _EAR, [(cx - 5, cy - 7), (cx - 2, cy - 13), (cx - 1, cy - 8)])
        pygame.draw.polygon(surface, _EAR, [(cx + 5, cy - 7), (cx + 2, cy - 13), (cx + 1, cy - 8)])

        # Head
        pygame.draw.circle(surface, _HEAD, (cx, cy - 6), 4)

        # Eyes
        pygame.draw.circle(surface, _EYE, (cx - 2, cy - 7), 1)
        pygame.draw.circle(surface, _EYE, (cx + 2, cy - 7), 1)

        self._draw_champion_overlay(surface)


class Boss(Enemy):
    """
    Massive ranged enemy — 3× the size of a RangedZombie, 2× fire rate, 10× health.
    Chases and fires exactly like RangedZombie.
    """

    _champion_eligible = False
    _PROJ_COLOR = (220, 80, 30)

    def __init__(self, x, y):
        stats = EnemyStats(
            health=30.0,
            speed=35.0,
            ramp_time=0.6,
            size=72,
            fire_cooldown=0.25,
            projectile_speed=200.0,
            projectile_radius=7.0,
            projectile_range=420.0,
            projectile_shrink_rate=20.0,
        )
        super().__init__(x, y, stats)

    def update(self, dt, room, player):
        super().update(dt, room, player)
        has_los = line_of_sight(room, self.x, self.y, player.x, player.y, ignore_gaps=True)
        self._navigate_toward(dt, room, player.x, player.y)
        self._apply_velocity(dt, room)
        self._push_from_player(player, room)
        projectiles = []
        if has_los and self.fire_timer <= 0:
            proj = self._shoot_toward(player.x, player.y)
            if proj:
                proj.color = self._PROJ_COLOR
                projectiles.append(proj)
        return projectiles

    def draw(self, surface):
        cx, cy = round(self.x), round(self.y)

        _BODY_COLOR = (150, 40, 40)
        _BODY_SHADE = (100, 25, 25)
        _HEAD_COLOR = (180, 62, 62)
        _HIGHLIGHT  = (255, 150, 150)
        _HORN       = (90, 30, 30)

        # Body: top half of a wide oval  (3× player scale)
        bw, bh   = 66, 60
        oval_top = cy + 3
        old_clip = surface.get_clip()
        surface.set_clip(pygame.Rect(cx - bw // 2, oval_top, bw, bh // 2 + 1))
        pygame.draw.ellipse(surface, _BODY_SHADE,
                            pygame.Rect(cx - bw // 2 + 3, oval_top + 4, bw - 4, bh - 3))
        pygame.draw.ellipse(surface, _BODY_COLOR,
                            pygame.Rect(cx - bw // 2, oval_top, bw, bh))
        surface.set_clip(old_clip)

        # Head
        head_r  = 24
        head_cy = oval_top - head_r + 6

        # Horns (small dark triangles above the head)
        for side in (-1, 1):
            tip_x = cx + side * 18
            pygame.draw.polygon(surface, _HORN, [
                (cx + side * 8,  head_cy - head_r + 4),
                (tip_x,          head_cy - head_r - 14),
                (cx + side * 14, head_cy - head_r + 2),
            ])

        pygame.draw.circle(surface, _HEAD_COLOR, (cx, head_cy), head_r)
        pygame.draw.circle(surface, _HIGHLIGHT,
                           (cx - head_r // 3, head_cy - head_r // 3),
                           max(1, head_r // 3))


ENEMIES = {
    "zombie":        Zombie,
    "ranged_zombie": RangedZombie,
    "bat":           Bat,
    "boss":          Boss,
}
