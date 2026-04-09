import math
import pygame
from enemy import Enemy
from enemy_stats import EnemyStats
from pathfinding import line_of_sight
from projectile import Projectile
from slime import SlimePuddle, _COLORS_YELLOW, _RX, _RY

_ZOMBIE_SIZE = 56   # temp-surface side length for zombie sprites


def _draw_zombie_to_surface(tmp, cx, cy, skin, dark, head_col, hi, wound):
    """
    Draw a zombie sprite onto `tmp` centred at (cx, cy).
    The sprite always faces RIGHT — call pygame.transform.flip afterwards
    if the zombie is moving left.
    """
    # --- body (hunched top-half oval) ---
    bw, bh   = 26, 24
    oval_top = cy + 2
    old_clip = tmp.get_clip()
    tmp.set_clip(pygame.Rect(cx - bw // 2, oval_top, bw, bh // 2 + 1))
    pygame.draw.ellipse(tmp, dark,
                        pygame.Rect(cx - bw // 2 + 2, oval_top + 2, bw - 3, bh - 2))
    pygame.draw.ellipse(tmp, skin,
                        pygame.Rect(cx - bw // 2, oval_top, bw, bh))
    tmp.set_clip(old_clip)

    # --- arms — start at the widest point of the half-oval so they look attached ---
    arm_y = oval_top + bh // 2 - 3

    # trailing arm (left / behind)
    pygame.draw.line(tmp, skin,
                     (cx - bw // 2, arm_y), (cx - bw // 2 - 9, arm_y + 7), 3)

    # outstretched arm (right / forward)
    pygame.draw.line(tmp, skin,
                     (cx + bw // 2, arm_y), (cx + bw // 2 + 13, arm_y - 2), 3)
    pygame.draw.circle(tmp, head_col, (cx + bw // 2 + 13, arm_y - 2), 4)

    # --- head (leaning slightly forward) ---
    head_r  = 10
    head_cx = cx + 2
    head_cy = oval_top - head_r + 2
    pygame.draw.circle(tmp, head_col, (head_cx, head_cy), head_r)
    pygame.draw.circle(tmp, hi,       (head_cx - 3, head_cy - 3), 3)

    # sunken eyes
    for ex in (head_cx - 3, head_cx + 3):
        pygame.draw.circle(tmp, (22, 15, 10),   (ex, head_cy),     3)
        pygame.draw.circle(tmp, (210, 190, 50), (ex, head_cy),     1)

    # teeth
    pygame.draw.rect(tmp, (195, 190, 168),
                     (head_cx - 3, head_cy + 4, 7, 3))
    pygame.draw.line(tmp, dark,
                     (head_cx, head_cy + 4), (head_cx, head_cy + 7), 1)

    # wound mark
    pygame.draw.line(tmp, wound,
                     (cx - 3, oval_top + 5), (cx + 2, oval_top + 9), 1)


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

    def draw(self, surface):
        tmp = pygame.Surface((_ZOMBIE_SIZE, _ZOMBIE_SIZE), pygame.SRCALPHA)
        c   = _ZOMBIE_SIZE // 2
        _draw_zombie_to_surface(
            tmp, c, c,
            skin      = (105, 130, 78),
            dark      = (68,   92, 48),
            head_col  = (118, 145, 86),
            hi        = (150, 180, 110),
            wound     = (90,   28, 28),
        )
        if self.vx < 0:
            tmp = pygame.transform.flip(tmp, True, False)
        surface.blit(tmp, (round(self.x) - c, round(self.y) - c))
        self._draw_hit_flash(surface)
        self._draw_champion_overlay(surface)


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
            projectile_radius=7.5,
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

    def draw(self, surface):
        SIZE = _ZOMBIE_SIZE
        tmp  = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
        c    = SIZE // 2

        _BONE   = (218, 212, 190)
        _SHADE  = (165, 158, 138)
        _HI     = (240, 237, 222)
        _SOCKET = (18,  13,  8)

        bw, bh   = 26, 24
        oval_top = c + 2
        arm_y    = oval_top + bh // 2 - 3

        # Spine
        pygame.draw.line(tmp, _SHADE, (c, oval_top), (c, oval_top + bh // 2 + 2), 2)

        # Collarbone
        pygame.draw.line(tmp, _BONE, (c - 10, oval_top + 1), (c + 10, oval_top + 1), 2)

        # Ribs — 3 pairs angled slightly downward
        for i in range(3):
            ry = oval_top + 4 + i * 5
            pygame.draw.line(tmp, _BONE, (c - 1, ry), (c - 10, ry + 3), 2)
            pygame.draw.line(tmp, _BONE, (c + 1, ry), (c + 10, ry + 3), 2)

        # Pelvis hint
        pygame.draw.line(tmp, _SHADE, (c - 7, oval_top + bh // 2 + 1), (c + 7, oval_top + bh // 2 + 1), 2)

        # Trailing arm (left / behind) — two bone segments with elbow joint
        pygame.draw.line(tmp, _BONE, (c - 10, oval_top + 2), (c - 13, arm_y - 3), 2)
        pygame.draw.circle(tmp, _BONE, (c - 13, arm_y - 3), 2)
        pygame.draw.line(tmp, _BONE, (c - 13, arm_y - 3), (c - 20, arm_y + 5), 2)

        # Forward arm (right) — outstretched for ranged attacks
        pygame.draw.line(tmp, _BONE, (c + 10, oval_top + 2), (c + 14, arm_y - 3), 2)
        pygame.draw.circle(tmp, _BONE, (c + 14, arm_y - 3), 2)
        pygame.draw.line(tmp, _BONE, (c + 14, arm_y - 3), (c + 23, arm_y - 5), 2)
        pygame.draw.circle(tmp, _SHADE, (c + 23, arm_y - 5), 3)  # hand

        # Skull
        head_r  = 10
        head_cx = c + 2
        head_cy = oval_top - head_r + 2
        pygame.draw.circle(tmp, _SHADE, (head_cx + 1, head_cy + 1), head_r)
        pygame.draw.circle(tmp, _BONE,  (head_cx,     head_cy),     head_r)
        pygame.draw.circle(tmp, _HI,    (head_cx - 3, head_cy - 3), 3)

        # Eye sockets
        pygame.draw.ellipse(tmp, _SOCKET, (head_cx - 7, head_cy - 2, 5, 4))
        pygame.draw.ellipse(tmp, _SOCKET, (head_cx + 2, head_cy - 2, 5, 4))

        # Nasal cavity
        pygame.draw.polygon(tmp, _SOCKET, [
            (head_cx,     head_cy + 2),
            (head_cx - 2, head_cy + 5),
            (head_cx + 2, head_cy + 5),
        ])

        # Teeth
        for ti in range(4):
            pygame.draw.rect(tmp, _HI, (head_cx - 4 + ti * 3, head_cy + 5, 2, 3))

        if self.vx < 0:
            tmp = pygame.transform.flip(tmp, True, False)
        surface.blit(tmp, (round(self.x) - SIZE // 2, round(self.y) - SIZE // 2))
        self._draw_hit_flash(surface)
        self._draw_champion_overlay(surface)


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
            (cx - 1, cy - 1), (cx - 6, cy - 5), (cx - 17, cy - 6),
            (cx - 20, cy + 1), (cx - 13, cy + 8), (cx - 4, cy + 4),
        ])
        pygame.draw.polygon(surface, _WING_EDGE, [
            (cx - 6, cy - 5), (cx - 17, cy - 6), (cx - 20, cy + 1),
        ], 1)
        # Right wing (mirrored)
        pygame.draw.polygon(surface, _WING, [
            (cx + 1, cy - 1), (cx + 6, cy - 5), (cx + 17, cy - 6),
            (cx + 20, cy + 1), (cx + 13, cy + 8), (cx + 4, cy + 4),
        ])
        pygame.draw.polygon(surface, _WING_EDGE, [
            (cx + 6, cy - 5), (cx + 17, cy - 6), (cx + 20, cy + 1),
        ], 1)

        # Body
        pygame.draw.circle(surface, _BODY, (cx, cy + 1), 7)

        # Ears
        pygame.draw.polygon(surface, _EAR, [(cx - 6, cy - 9), (cx - 3, cy - 17), (cx - 1, cy - 10)])
        pygame.draw.polygon(surface, _EAR, [(cx + 6, cy - 9), (cx + 3, cy - 17), (cx + 1, cy - 10)])

        # Head
        pygame.draw.circle(surface, _HEAD, (cx, cy - 8), 6)

        # Eyes
        pygame.draw.circle(surface, _EYE, (cx - 3, cy - 9), 2)
        pygame.draw.circle(surface, _EYE, (cx + 3, cy - 9), 2)

        self._draw_hit_flash(surface)
        self._draw_champion_overlay(surface)


class Boss(Enemy):
    """
    Massive ranged enemy — 3× the size of a RangedZombie, 2× fire rate, 10× health.
    Chases and fires exactly like RangedZombie.
    """

    _champion_eligible = False
    _PROJ_COLOR  = (220, 80, 30)
    _BURST_COLOR = (255, 160, 20)
    _BURST_COOLDOWN = 5.0
    _BURST_COUNT    = 12

    def __init__(self, x, y):
        stats = EnemyStats(
            health=60.0,
            speed=45.0,
            ramp_time=0.6,
            size=72,
            fire_cooldown=0.25,
            projectile_speed=200.0,
            projectile_radius=9.0,
            projectile_range=420.0,
            projectile_shrink_rate=20.0,
        )
        super().__init__(x, y, stats)
        self._burst_timer = self._BURST_COOLDOWN

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

        self._burst_timer -= dt
        if self._burst_timer <= 0:
            self._burst_timer = self._BURST_COOLDOWN
            for i in range(self._BURST_COUNT):
                angle = (2 * math.pi / self._BURST_COUNT) * i
                proj = Projectile(
                    self.x, self.y,
                    math.cos(angle), math.sin(angle),
                    self.stats.projectile_speed,
                    self.stats.projectile_radius,
                    self.stats.projectile_range,
                    self.stats.projectile_shrink_rate,
                    color=self._BURST_COLOR,
                )
                projectiles.append(proj)

        return projectiles

    def draw(self, surface):
        cx, cy = round(self.x), round(self.y)

        _FLESH    = (228, 198, 175)
        _FLESH_DK = (185, 155, 132)
        _FLESH_HI = (248, 222, 204)
        _SCAR     = (168, 122, 102)
        _GLOW     = (255, 85,  35)
        _EYE_SC   = (238, 225, 168)
        _EYE_IRIS = (205, 45,  25)
        _PUPIL    = (12,  8,   5)
        _MOUTH_IN = (75,  22,  18)
        _TEETH    = (238, 232, 212)

        # Blob body — irregular lumps + main mass
        lumps = [
            (cx - 4,  cy - 26, 15),
            (cx + 20, cy - 15, 13),
            (cx + 28, cy + 4,  11),
            (cx + 17, cy + 24, 14),
            (cx - 5,  cy + 30, 13),
            (cx - 23, cy + 19, 15),
            (cx - 30, cy - 1,  12),
            (cx - 18, cy - 20, 11),
        ]
        # Shadow pass (offset +2)
        for lx, ly, lr in lumps:
            pygame.draw.circle(surface, _FLESH_DK, (lx + 2, ly + 2), lr)
        pygame.draw.circle(surface, _FLESH_DK, (cx + 2, cy + 2), 28)
        # Flesh pass
        for lx, ly, lr in lumps:
            pygame.draw.circle(surface, _FLESH, (lx, ly), lr)
        pygame.draw.circle(surface, _FLESH, (cx, cy), 28)
        # Soft highlight on upper surface
        pygame.draw.circle(surface, _FLESH_HI, (cx - 9, cy - 11), 13)

        # Pustules
        for px, py, pr in [(cx+9,cy+12,4),(cx-13,cy+6,3),(cx+19,cy-1,3),(cx-4,cy+20,4)]:
            pygame.draw.circle(surface, _FLESH_DK, (px,    py),    pr)
            pygame.draw.circle(surface, _FLESH_HI, (px-1, py-1),  max(1, pr - 2))

        # Scar lines
        pygame.draw.line(surface, _SCAR, (cx - 20, cy - 14), (cx - 9,  cy - 4), 2)
        pygame.draw.line(surface, _SCAR, (cx + 8,  cy + 6),  (cx + 20, cy + 16), 2)

        # Mouth — dark cavity + jagged teeth
        mx, my, mw, mh = cx - 22, cy + 9, 44, 14
        pygame.draw.ellipse(surface, _MOUTH_IN, (mx, my, mw, mh))
        tw = 8
        for i in range(5):   # upper teeth pointing down
            tx = mx + 4 + i * tw
            pygame.draw.polygon(surface, _TEETH, [(tx, my), (tx + tw - 1, my), (tx + tw // 2, my + 8)])
        for i in range(4):   # lower teeth pointing up
            tx = mx + 8 + i * tw
            pygame.draw.polygon(surface, _TEETH, [(tx, my + mh), (tx + tw - 1, my + mh), (tx + tw // 2, my + 6)])

        # Eyes — asymmetric for extra menace
        for ex, ey, er in [(cx - 11, cy - 7, 8), (cx + 13, cy - 10, 7)]:
            pygame.draw.circle(surface, _GLOW,     (ex, ey), er + 3)
            pygame.draw.circle(surface, _EYE_SC,   (ex, ey), er)
            pygame.draw.circle(surface, _EYE_IRIS, (ex, ey), er - 2)
            # Vertical slit pupil
            pygame.draw.ellipse(surface, _PUPIL,
                                (ex - 2, ey - er + 4, 4, (er - 3) * 2))
        self._draw_hit_flash(surface)


class Slimer(Enemy):
    """
    Boss enemy. Chases the player like a large Leaker and leaves slime puddles.
    Every 10 s it locks onto the player's direction and charges at high speed
    for 1 s, during which it has no AI control over its movement.
    Fires a 3-projectile cone toward the player when it has line of sight.
    """

    _champion_eligible = False
    CONTACT_RANGE    = 60   # matches size/2 = 60
    DAMAGE_COOLDOWN  = 1.0
    _TRAIL_SPACING   = 22    # pixels between puddle drops
    _CHARGE_COOLDOWN = 10.0
    _CHARGE_DURATION = 1.0
    _CHARGE_SPEED    = 500.0
    _CONE_SPREAD     = math.radians(18)   # ±18° spread for side projectiles

    _PROJ_COLOR = (180, 210, 20)

    def __init__(self, x, y):
        stats = EnemyStats(
            health=80.0,
            speed=55.0,
            ramp_time=0.5,
            size=120,
            fire_cooldown=1.2,
            projectile_speed=130.0,
            projectile_radius=8.0,
            projectile_range=380.0,
            projectile_shrink_rate=20.0,
        )
        super().__init__(x, y, stats)
        self.contact_damage    = 2
        self._damage_timer     = 0.0
        self._last_puddle_x    = x
        self._last_puddle_y    = y
        self._charge_timer     = self._CHARGE_COOLDOWN
        self._charging        = False
        self._charge_active   = 0.0

    def update(self, dt, room, player):
        super().update(dt, room, player)

        has_los = line_of_sight(room, self.x, self.y, player.x, player.y, ignore_gaps=True)

        if self._charging:
            self._charge_active -= dt
            if self._charge_active <= 0:
                self._charging     = False
                self._charge_timer = self._CHARGE_COOLDOWN
        else:
            self._charge_timer -= dt
            if self._charge_timer <= 0:
                dx   = player.x - self.x
                dy   = player.y - self.y
                dist = math.hypot(dx, dy)
                if dist:
                    self.vx = (dx / dist) * self._CHARGE_SPEED
                    self.vy = (dy / dist) * self._CHARGE_SPEED
                self._charging      = True
                self._charge_active = self._CHARGE_DURATION
            else:
                self._navigate_toward(dt, room, player.x, player.y)

        self._apply_velocity(dt, room)
        self._push_from_player(player, room)

        if self._damage_timer > 0:
            self._damage_timer -= dt
        if self._damage_timer <= 0:
            if math.hypot(player.x - self.x, player.y - self.y) <= self.CONTACT_RANGE + player.stats.size / 2:
                player.take_damage(self.contact_damage)
                self._damage_timer = self.DAMAGE_COOLDOWN

        if math.hypot(self.x - self._last_puddle_x, self.y - self._last_puddle_y) >= self._TRAIL_SPACING:
            room.slime_puddles.append(SlimePuddle(
                self.x, self.y, rx=_RX * 2, ry=_RY * 2, colors=_COLORS_YELLOW))
            self._last_puddle_x = self.x
            self._last_puddle_y = self.y

        projectiles = []
        if has_los and self.fire_timer <= 0:
            base = math.atan2(player.y - self.y, player.x - self.x)
            self.fire_timer = self.stats.fire_cooldown
            for offset in (-self._CONE_SPREAD, 0, self._CONE_SPREAD):
                angle = base + offset
                proj = Projectile(
                    self.x, self.y,
                    math.cos(angle), math.sin(angle),
                    self.stats.projectile_speed,
                    self.stats.projectile_radius,
                    self.stats.projectile_range,
                    self.stats.projectile_shrink_rate,
                    color=self._PROJ_COLOR,
                )
                projectiles.append(proj)
        return projectiles

    def draw(self, surface):
        cx, cy = round(self.x), round(self.y)

        _SLIME    = (225, 200, 35)
        _SLIME_DK = (178, 155, 15)
        _SLIME_HI = (255, 238, 105)
        _DRIP     = (195, 215, 20)
        _EYE      = (20, 15, 8)
        _EYE_HI   = (255, 255, 220)
        _MOUTH    = (150, 115, 10)

        lumps = [
            (cx - 42, cy + 3,  24),
            (cx + 42, cy + 3,  24),
            (cx,      cy - 33, 21),
            (cx - 27, cy + 33, 18),
            (cx + 27, cy + 33, 18),
            (cx - 51, cy - 12, 17),
            (cx + 51, cy - 12, 17),
        ]
        # Shadow pass
        for lx, ly, lr in lumps:
            pygame.draw.circle(surface, _SLIME_DK, (lx + 3, ly + 3), lr)
        pygame.draw.circle(surface, _SLIME_DK, (cx + 3, cy + 3), 39)
        # Slime pass
        for lx, ly, lr in lumps:
            pygame.draw.circle(surface, _SLIME, (lx, ly), lr)
        pygame.draw.circle(surface, _SLIME, (cx, cy), 39)
        # Highlight
        pygame.draw.circle(surface, _SLIME_HI, (cx - 12, cy - 15), 18)

        # Slime drips around edges
        for ox, oy, r in [(cx + 12, cy + 45, 6), (cx - 24, cy + 39, 5),
                          (cx + 36, cy + 21, 5), (cx - 42, cy + 15, 6)]:
            pygame.draw.circle(surface, _DRIP, (ox, oy), r)
            pygame.draw.circle(surface, _SLIME_HI, (ox - 1, oy - 1), max(1, r - 1))

        # Eyes
        for ex, ey in [(cx - 15, cy - 9), (cx + 15, cy - 9)]:
            pygame.draw.circle(surface, _EYE,    (ex, ey), 9)
            pygame.draw.circle(surface, _EYE_HI, (ex - 3, ey - 3), 3)

        # Smile — bezier-style curve via plotted points
        smile_pts = []
        for i in range(13):
            t  = math.pi * i / 12
            sx = cx - 20 + round(40 * i / 12)
            sy = cy + 6 + round(14 * math.sin(t))
            smile_pts.append((sx, sy))
        pygame.draw.lines(surface, _MOUTH, False, smile_pts, 4)

        # Flash brighter outline while charging
        if self._charging:
            pygame.draw.circle(surface, _SLIME_HI, (cx, cy), 57, 4)
        self._draw_hit_flash(surface)


class Leaker(Enemy):
    """
    Zombie variant covered in bright green slime.
    Behaves identically to Zombie but periodically drops SlimePuddles that
    damage the player on contact and expire after 3 seconds.
    """

    CONTACT_RANGE   = 20
    DAMAGE_COOLDOWN = 1.0
    _TRAIL_INTERVAL = 0.6   # seconds between puddle drops

    def __init__(self, x, y):
        stats = EnemyStats(health=6.0, speed=55.0, ramp_time=0.3)
        super().__init__(x, y, stats)
        self._damage_timer = 0.0
        self._trail_timer  = 0.0

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

        self._trail_timer -= dt
        if self._trail_timer <= 0:
            room.slime_puddles.append(SlimePuddle(self.x, self.y))
            self._trail_timer = self._TRAIL_INTERVAL

        return []

    def draw(self, surface):
        SIZE = _ZOMBIE_SIZE
        tmp  = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
        c    = SIZE // 2
        _draw_zombie_to_surface(
            tmp, c, c,
            skin     = (80,  140,  70),
            dark     = (50,   95,  45),
            head_col = (90,  160,  80),
            hi       = (130, 210, 115),
            wound    = (30,  100,  30),
        )

        # Slime drips on body
        _SL  = (60, 215, 55)
        _SLH = (110, 255, 100)
        cx, cy = c, c
        for ox, oy, r in ((-4, 6, 3), (5, 4, 2), (0, 10, 2), (-7, 2, 2)):
            pygame.draw.circle(tmp, _SL,  (cx + ox, cy + oy), r)
            pygame.draw.circle(tmp, _SLH, (cx + ox - 1, cy + oy - 1), max(1, r - 1))
        # Drip lines
        pygame.draw.line(tmp, _SL, (cx - 3, cy + 2), (cx - 5, cy + 12), 2)
        pygame.draw.line(tmp, _SL, (cx + 4, cy + 3), (cx + 3, cy + 11), 2)

        if self.vx < 0:
            tmp = pygame.transform.flip(tmp, True, False)
        surface.blit(tmp, (round(self.x) - c, round(self.y) - c))
        self._draw_hit_flash(surface)
        self._draw_champion_overlay(surface)


class FlamingZombie(Enemy):
    """
    Fast zombie that continuously burns, taking 0.5 damage per second.
    Otherwise behaves identically to a regular Zombie.
    """

    CONTACT_RANGE   = 20
    DAMAGE_COOLDOWN = 1.0
    _BURN_RATE      = 0.5   # HP lost per second

    def __init__(self, x, y):
        stats = EnemyStats(health=6.0, speed=140.0, ramp_time=0.2)
        super().__init__(x, y, stats)
        self._damage_timer = 0.0
        self._burn_accum   = 0.0

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

        self._burn_accum += self._BURN_RATE * dt
        if self._burn_accum >= 0.5:
            self.take_damage(0.5)
            self._burn_accum -= 0.5

        return []

    def draw(self, surface):
        tmp = pygame.Surface((_ZOMBIE_SIZE, _ZOMBIE_SIZE), pygame.SRCALPHA)
        c   = _ZOMBIE_SIZE // 2
        _draw_zombie_to_surface(
            tmp, c, c,
            skin     = (200,  80,  20),
            dark     = (140,  45,  10),
            head_col = (220, 100,  30),
            hi       = (255, 180,  60),
            wound    = ( 80,  10,  10),
        )

        # Flames — layered circles rising above the head
        _FL1 = (255, 60,   0)   # deep orange base
        _FL2 = (255, 160,  20)  # mid orange
        _FL3 = (255, 230,  60)  # yellow tip
        bw, bh   = 26, 24
        oval_top = c + 2
        head_r   = 10
        head_cy  = oval_top - head_r + 2
        fx, fy   = c + 2, head_cy - head_r  # base of flames above head

        # Three flame tongues
        for ox, scale in ((-6, 1.0), (0, 1.3), (6, 0.9)):
            pygame.draw.circle(tmp, _FL1, (fx + ox, fy),              round(5 * scale))
            pygame.draw.circle(tmp, _FL2, (fx + ox, fy - round(5 * scale)),     round(4 * scale))
            pygame.draw.circle(tmp, _FL3, (fx + ox, fy - round(9 * scale)),     round(2 * scale))
        # Small body embers
        for ox, oy in ((-6, 4), (5, 2), (0, 8)):
            pygame.draw.circle(tmp, _FL2, (c + ox, oval_top + oy), 2)

        if self.vx < 0:
            tmp = pygame.transform.flip(tmp, True, False)
        surface.blit(tmp, (round(self.x) - c, round(self.y) - c))
        self._draw_hit_flash(surface)
        self._draw_champion_overlay(surface)


ENEMIES = {
    "zombie":         Zombie,
    "ranged_zombie":  RangedZombie,
    "bat":            Bat,
    "leaker":         Leaker,
    "flaming_zombie": FlamingZombie,
    "boss":           Boss,
    "slimer":         Slimer,
}
