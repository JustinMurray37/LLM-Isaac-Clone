import pygame

_font = None
_level_font = None
_notif_font = None
_gameover_font = None
_gameover_sub_font = None

# Panel visual constants
_P          = 12    # inner padding
_SECTION_GAP = 14   # gap between sections
_LINE_H      = 18   # stat line height

_PANEL_BG     = (16,  16,  24)
_PANEL_BORDER = (48,  48,  65)
_DIVIDER      = (40,  40,  55)
_LABEL_COL    = (110, 110, 135)

# Health
_HP_R         = 10
_HP_GAP       = 5
_HP_COLOR     = (210, 40,  40)
_HP_EMPTY     = (70,  25,  25)

_NOTIF_DURATION = 1.5
_NOTIF_FADE     = 0.4
_RESTART_HOLD   = 3.0
_BAR_WIDTH      = 200
_BAR_HEIGHT     = 12


def _get_font():
    global _font
    if _font is None:
        _font = pygame.font.SysFont("monospace", 13)
    return _font


def _get_level_font():
    global _level_font
    if _level_font is None:
        _level_font = pygame.font.SysFont("monospace", 13, bold=True)
    return _level_font


def _get_notif_font():
    global _notif_font
    if _notif_font is None:
        _notif_font = pygame.font.SysFont("monospace", 22, bold=True)
    return _notif_font


def _get_gameover_fonts():
    global _gameover_font, _gameover_sub_font
    if _gameover_font is None:
        _gameover_font     = pygame.font.SysFont("monospace", 52, bold=True)
        _gameover_sub_font = pygame.font.SysFont("monospace", 18)
    return _gameover_font, _gameover_sub_font


# ---------------------------------------------------------------------------
# Heart helpers
# ---------------------------------------------------------------------------

def _draw_heart(surface, color, cx, cy, r):
    pygame.draw.circle(surface, color, (cx - r // 2, cy - r // 3), r // 2 + 1)
    pygame.draw.circle(surface, color, (cx + r // 2, cy - r // 3), r // 2 + 1)
    pygame.draw.polygon(surface, color, [
        (cx - r, cy - r // 3),
        (cx + r, cy - r // 3),
        (cx,     cy + r),
    ])


def _draw_half_heart(surface, color, empty_color, cx, cy, r):
    _draw_heart(surface, empty_color, cx, cy, r)
    old_clip = surface.get_clip()
    surface.set_clip(pygame.Rect(cx - r - 2, 0, r + 2, surface.get_height()))
    _draw_heart(surface, color, cx, cy, r)
    surface.set_clip(old_clip)


# ---------------------------------------------------------------------------
# Section helpers
# ---------------------------------------------------------------------------

def _label(surface, text, x, y):
    font = _get_font()
    surf = font.render(text, True, _LABEL_COL)
    surface.blit(surf, (x, y))
    return y + surf.get_height() + 3


def _divider(surface, panel, y):
    pygame.draw.line(surface, _DIVIDER,
                     (panel.left + _P, y), (panel.right - _P, y))


# ---------------------------------------------------------------------------
# Public draw functions — all accept a `panel` Rect (the side panel area)
# ---------------------------------------------------------------------------

def draw_panel_bg(surface, panel):
    """Draw the panel background and right-edge border line."""
    pygame.draw.rect(surface, _PANEL_BG, panel)
    pygame.draw.line(surface, _PANEL_BORDER,
                     (panel.right - 1, panel.top),
                     (panel.right - 1, panel.bottom), 2)


def draw_health(surface, stats, panel):
    """Hearts arranged in rows.  Returns the y just below the section."""
    x = panel.left + _P
    y = panel.top  + _P
    y = _label(surface, "HEALTH", x, y)

    r    = _HP_R
    step = r * 2 + _HP_GAP
    per_row = max(1, (panel.width - _P * 2) // step)

    hp          = int(stats.health)
    max_hp      = int(stats.max_health)
    full_hearts = hp // 2
    half_heart  = hp % 2
    total       = (max_hp + 1) // 2

    for i in range(total):
        col = i % per_row
        row = i // per_row
        hx  = x + r + col * step
        hy  = y + r + row * (r * 2 + 4)
        if i < full_hearts:
            _draw_heart(surface, _HP_COLOR, hx, hy, r)
        elif i == full_hearts and half_heart:
            _draw_half_heart(surface, _HP_COLOR, _HP_EMPTY, hx, hy, r)
        else:
            _draw_heart(surface, _HP_EMPTY, hx, hy, r)

    rows_used = max(1, (total + per_row - 1) // per_row)
    return y + rows_used * (r * 2 + 4)


def draw_keys(surface, stats, panel, y):
    """Key icon + counter.  Returns the y just below the section."""
    from pickup import _draw_key_shape
    _KEY_COLOR = (220, 180, 50)
    font = _get_font()
    x = panel.left + _P

    y = _label(surface, "KEYS", x, y)

    r  = 11
    cy = y + r
    _draw_key_shape(surface, _KEY_COLOR, x + r, cy, r)
    count = font.render(f"x{stats.keys}", True, (220, 210, 160))
    surface.blit(count, (x + r * 2 + 6, cy - count.get_height() // 2))
    return cy + r + 2


def draw_bombs(surface, stats, panel, y):
    """Bomb icon + counter.  Returns the y just below the section."""
    font = _get_font()
    x = panel.left + _P

    y = _label(surface, "BOMBS", x, y)

    r  = 11
    cy = y + r
    _draw_bomb_icon(surface, x + r, cy, r)
    count = font.render(f"x{stats.bombs}", True, (200, 200, 180))
    surface.blit(count, (x + r * 2 + 6, cy - count.get_height() // 2))
    return cy + r + 2


def draw_stats(surface, stats, panel):
    """Stat lines anchored to the bottom of the panel."""
    font = _get_font()
    lines = [
        ("speed",      f"{stats.speed:.0f}"),
        ("damage",     f"{stats.projectile_damage:.1f}"),
        ("proj spd",   f"{stats.projectile_speed:.0f}"),
        ("proj range", f"{stats.projectile_range:.0f}"),
        ("fire rate",  f"{1 / stats.fire_cooldown:.1f}/s"),
    ]
    total_h = len(lines) * _LINE_H + _P
    y = panel.bottom - total_h

    _divider(surface, panel, y - 6)

    x = panel.left + _P
    for label, value in lines:
        label_s = font.render(label, True, _LABEL_COL)
        value_s = font.render(value, True, (220, 220, 220))
        surface.blit(label_s, (x, y))
        surface.blit(value_s, (panel.right - _P - value_s.get_width(), y))
        y += _LINE_H


def draw_minimap(surface, area, rooms_grid, visited, current):
    """
    Render explored rooms as small rectangles inside `area`.
    Only rooms in `visited` are shown.  The current room is highlighted green.
    Corridors between visited rooms are drawn as thin lines; locked ones in gold.
    """
    if not rooms_grid or not visited:
        return

    xs = [p[0] for p in rooms_grid]
    ys = [p[1] for p in rooms_grid]
    min_x, min_y = min(xs), min(ys)
    gw = max(xs) - min_x + 1
    gh = max(ys) - min_y + 1

    # Scale room+gap cells to fit the area
    ROOM_W = max(6,  min(14, (area.width  - 4) // gw - 2))
    ROOM_H = max(5,  min(10, (area.height - 4) // gh - 2))
    GAP_X  = max(2,  min(6,  (area.width  - 4) // gw - ROOM_W))
    GAP_Y  = max(2,  min(6,  (area.height - 4) // gh - ROOM_H))
    STEP_X = ROOM_W + GAP_X
    STEP_Y = ROOM_H + GAP_Y

    total_w = gw * STEP_X - GAP_X
    total_h = gh * STEP_Y - GAP_Y
    ox = area.left + (area.width  - total_w) // 2
    oy = area.top  + (area.height - total_h) // 2

    _MAP_BG    = (22, 22, 34)
    _ROOM_COL  = (60, 60, 82)
    _CURR_COL  = (80, 200, 100)
    _CORR_COL  = (48, 48, 66)
    _LOCK_COL  = (170, 130, 20)

    pygame.draw.rect(surface, _MAP_BG, area, border_radius=4)
    pygame.draw.rect(surface, _PANEL_BORDER, area, 1, border_radius=4)

    for (gx, gy), room in rooms_grid.items():
        if room not in visited:
            continue
        rx = ox + (gx - min_x) * STEP_X
        ry = oy + (gy - min_y) * STEP_Y

        # Corridors to right / down neighbours (draw once per pair)
        for d, (dx, dy) in (("right", (1, 0)), ("down", (0, 1))):
            nbr = rooms_grid.get((gx + dx, gy + dy))
            if nbr is None or nbr not in visited:
                continue
            if d not in room.connections or room.connections[d] is not nbr:
                continue
            locked = d in room.locked_connections
            col = _LOCK_COL if locked else _CORR_COL
            if d == "right":
                pygame.draw.line(surface, col,
                                 (rx + ROOM_W, ry + ROOM_H // 2),
                                 (rx + STEP_X, ry + ROOM_H // 2))
            else:
                pygame.draw.line(surface, col,
                                 (rx + ROOM_W // 2, ry + ROOM_H),
                                 (rx + ROOM_W // 2, ry + STEP_Y))

        color = _CURR_COL if room is current else _ROOM_COL
        pygame.draw.rect(surface, color, (rx, ry, ROOM_W, ROOM_H))


def draw_hud(surface, stats, panel,
             rooms_grid=None, visited=None, current=None, level=1):
    """Draw the complete HUD panel: bg, health, keys, bombs, minimap, stats."""
    draw_panel_bg(surface, panel)

    y = draw_health(surface, stats, panel)
    y += _SECTION_GAP
    _divider(surface, panel, y)
    y += _SECTION_GAP

    y = draw_keys(surface, stats, panel, y)
    y += _SECTION_GAP
    _divider(surface, panel, y)
    y += _SECTION_GAP

    y = draw_bombs(surface, stats, panel, y)
    y += _SECTION_GAP
    _divider(surface, panel, y)
    y += _SECTION_GAP

    # Minimap fills the space between the counters and the stats block
    stats_top = panel.bottom - (5 * _LINE_H + _P + 14)
    map_area  = pygame.Rect(panel.left + _P, y,
                            panel.width - _P * 2, stats_top - y - _SECTION_GAP)
    if map_area.height > 20 and rooms_grid:
        lbl_surf = _get_level_font().render(f"Level {level}", True, (220, 220, 220))
        surface.blit(lbl_surf, (panel.left + _P, y - (_SECTION_GAP + 2)))
        draw_minimap(surface, map_area, rooms_grid, visited or set(), current)

    draw_stats(surface, stats, panel)


def _draw_bomb_icon(surface, cx, cy, r):
    pygame.draw.circle(surface, (45, 45, 55), (cx, cy + 1), r // 2 + 2)
    fx, fy = cx + r // 4, cy - r // 4
    pygame.draw.line(surface, (160, 130, 80), (fx, fy), (fx + r // 3, fy - r // 3), 2)
    pygame.draw.circle(surface, (255, 210, 60), (fx + r // 3, fy - r // 3), 2)


# ---------------------------------------------------------------------------
# Overlay draws (notifications, game over)
# ---------------------------------------------------------------------------

def draw_boss_healthbar(surface, boss, screen_width):
    """Draw a centered boss health bar near the top of the game surface."""
    bar_w = 320
    bar_h = 16
    x = (screen_width - bar_w) // 2
    y = 14

    font = _get_font()
    label = font.render("BOSS", True, (220, 80, 80))
    surface.blit(label, (x + (bar_w - label.get_width()) // 2, y - label.get_height() - 2))

    ratio = max(0.0, boss.stats.health / boss.stats.max_health)
    pygame.draw.rect(surface, (60, 20, 20),  (x,     y, bar_w,          bar_h))
    pygame.draw.rect(surface, (200, 50, 50), (x,     y, int(bar_w * ratio), bar_h))
    pygame.draw.rect(surface, (140, 60, 60), (x,     y, bar_w,          bar_h), 1)


def draw_notification(surface, text, timer, game_x, screen_width, screen_height):
    """Centred over the game area (game_x is the left edge of the game surface)."""
    alpha = 255
    if timer < _NOTIF_FADE:
        alpha = int(255 * (timer / _NOTIF_FADE))
    font = _get_notif_font()
    surf = font.render(text, True, (255, 255, 255))
    surf.set_alpha(alpha)
    x = game_x + (screen_width - surf.get_width()) // 2
    y = screen_height // 3
    surface.blit(surf, (x, y))


def draw_game_over(surface, game_x, screen_width, screen_height, hold_progress):
    overlay = pygame.Surface((game_x + screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    surface.blit(overlay, (0, 0))

    title_font, sub_font = _get_gameover_fonts()
    cx = game_x + screen_width // 2
    cy = screen_height // 2

    title = title_font.render("GAME OVER", True, (220, 50, 50))
    surface.blit(title, (cx - title.get_width() // 2, cy - 60))

    sub = sub_font.render("Hold R to restart", True, (180, 180, 180))
    surface.blit(sub, (cx - sub.get_width() // 2, cy + 10))

    bar_x = cx - _BAR_WIDTH // 2
    bar_y = cy + 40
    pygame.draw.rect(surface, (60, 60, 60),   (bar_x, bar_y, _BAR_WIDTH, _BAR_HEIGHT))
    pygame.draw.rect(surface, (180, 60, 60),  (bar_x, bar_y, int(_BAR_WIDTH * hold_progress), _BAR_HEIGHT))
    pygame.draw.rect(surface, (120, 120, 120),(bar_x, bar_y, _BAR_WIDTH, _BAR_HEIGHT), 1)
