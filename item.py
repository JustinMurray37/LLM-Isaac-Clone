import pygame

_label_font = None
_LABEL_PROXIMITY = 100  # pixels from item centre to show the name


def _get_label_font():
    global _label_font
    if _label_font is None:
        _label_font = pygame.font.SysFont("monospace", 11)
    return _label_font


class Item:
    """
    Base class for collectible items that modify player stats.

    Subclass and override `apply(stats)` to implement specific effects.
    Override `color` and `name` for visual differentiation.
    """

    color = (200, 200, 200)
    radius = 8
    name = "Item"

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.collected = False

    def apply(self, stats):
        """Modify the player's PlayerStats in place. Override in subclasses."""
        raise NotImplementedError

    def collect(self, stats):
        """Called when the player touches this item."""
        self.apply(stats)
        self.collected = True

    def draw_icon(self, surface, cx, cy):
        """Draw the item's icon centred on (cx, cy). Override for custom appearances."""
        pygame.draw.circle(surface, self.color, (cx, cy), self.radius)

    def check_collection(self, player):
        """Check proximity to player and collect if close enough."""
        if self.collected:
            return
        dx = player.x - self.x
        dy = player.y - self.y
        pickup_radius = player.stats.size / 2 + self.radius
        if dx * dx + dy * dy <= pickup_radius * pickup_radius:
            self.collect(player.stats)

    def draw(self, surface, player_x=None, player_y=None):
        cx, cy = round(self.x), round(self.y)

        # Stone pedestal
        ped_rx  = self.radius + 6   # horizontal radius
        ped_ry  = 5                  # vertical radius (flat disc)
        ped_cy  = cy + self.radius + 2
        pygame.draw.ellipse(surface, (55, 52, 48),
                            (cx - ped_rx - 2, ped_cy - ped_ry + 3,
                             (ped_rx + 2) * 2, (ped_ry + 2) * 2))  # shadow
        pygame.draw.ellipse(surface, (88, 84, 78),
                            (cx - ped_rx, ped_cy - ped_ry,
                             ped_rx * 2, ped_ry * 2))               # face
        pygame.draw.ellipse(surface, (110, 105, 98),
                            (cx - ped_rx, ped_cy - ped_ry,
                             ped_rx * 2, ped_ry // 2 + 1), 0)       # top highlight

        self.draw_icon(surface, cx, cy)

        if player_x is not None and player_y is not None:
            dx = player_x - self.x
            dy = player_y - self.y
            if dx * dx + dy * dy <= _LABEL_PROXIMITY ** 2:
                font = _get_label_font()
                label = font.render(self.name, True, (210, 210, 210))
                surface.blit(label, (cx - label.get_width() // 2, cy + self.radius + 4))
