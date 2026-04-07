from dataclasses import dataclass


@dataclass
class PlayerStats:
    # Health
    health: int = 6
    max_health: int = 6
    keys:  int = 0
    bombs: int = 0
    flight: bool = False
    spectral_shot: bool = False
    piercing_shot: bool = False

    # Movement
    speed: float = 200.0               # pixels per second
    size: int = 24                     # width and height in pixels
    ramp_time: float = 0.1             # seconds to reach full speed or stop completely

    # Firing
    fire_cooldown: float = 0.4        # seconds between shots (~3.5/sec)

    # Projectile
    projectile_damage: float = 1.0     # damage dealt per hit
    projectile_speed: float = 300.0    # pixels per second
    projectile_radius: float = 5.0     # starting radius in pixels
    projectile_range: float = 250.0    # pixels before shrinking begins
    projectile_shrink_rate: float = 25.0  # radius pixels lost per second while shrinking
    projectile_inherit_velocity: float = 0.5  # fraction of player velocity added to projectiles
