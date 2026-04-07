from dataclasses import dataclass, field


@dataclass
class EnemyStats:
    # Health
    health: float = 3.0
    max_health: float = 0.0   # set to health in __post_init__ if left at 0

    def __post_init__(self):
        if self.max_health == 0.0:
            self.max_health = self.health

    # Movement
    flight: bool = False
    speed: float = 80.0        # pixels per second
    size: int = 24             # width and height in pixels
    ramp_time: float = 0.2     # seconds to reach full speed or stop

    # Firing
    fire_cooldown: float = 1.5  # seconds between shots

    # Projectile
    projectile_damage: float = 1.0
    projectile_speed: float = 150.0
    projectile_radius: float = 5.0
    projectile_range: float = 200.0
    projectile_shrink_rate: float = 25.0
