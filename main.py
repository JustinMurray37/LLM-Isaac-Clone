import asyncio
import sys
import math
import random
import pygame

_WASM = sys.platform == "emscripten"
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, HUD_WIDTH, FPS, TILE_SIZE
from room import Room, _OPPOSITE
from player import Player
from pickup import PICKUPS
from chest import Chest, GoldenChest
from placed_bomb import PlacedBomb
from tile import TileType
from rooms import generate_dungeon
from items import ITEMS
from hud import draw_hud, draw_notification, draw_game_over, draw_boss_healthbar, _NOTIF_DURATION, _RESTART_HOLD
from enemies import Boss, Slimer
from ladder import Ladder
from blood import add_stain
import enemy as enemy_module
import room as room_module

SHOOT_DIRS = {
    pygame.K_UP:    ( 0, -1),
    pygame.K_DOWN:  ( 0,  1),
    pygame.K_LEFT:  (-1,  0),
    pygame.K_RIGHT: ( 1,  0),
}


def _spawn_room_clear_reward(room):
    """Called once when a room's last enemy dies. Rolls for a center reward."""
    if room.is_boss_room:
        b = room.bounds
        room.ladder = Ladder(b.centerx, b.centery)
        room.items.append(random.choice(list(ITEMS.values()))(b.centerx, b.bottom - 40))
        return
    cx = room.bounds.centerx
    cy = room.bounds.centery
    roll = random.random()
    if roll < 0.50:
        count = random.randint(1, 2)
        offsets = [(-22, 0), (22, 0)]
        for i in range(count):
            ox, oy = offsets[i] if count == 2 else (0, 0)
            room.pickups.append(random.choice(list(PICKUPS.values()))(cx + ox, cy + oy))
    elif roll < 0.80:           # 30 % — regular chest
        room.chests.append(Chest(cx, cy))
    elif roll < 0.90:           # 10 % — golden chest
        room.chests.append(GoldenChest(cx, cy))
    # else 10 % — nothing


def _place_at_entry(player, room, from_direction):
    """Position the player just inside the doorway they walked through."""
    entry = _OPPOSITE[from_direction]
    bounds = room.bounds
    half = player.stats.size / 2
    door_y = room.rows // 2 * TILE_SIZE + TILE_SIZE // 2
    door_x = room.cols // 2 * TILE_SIZE + TILE_SIZE // 2

    if entry == "left":
        player.x = bounds.left  + half + 4
        player.y = door_y
    elif entry == "right":
        player.x = bounds.right - half - 4
        player.y = door_y
    elif entry == "up":
        player.x = door_x
        player.y = bounds.top    + half + 4
    elif entry == "down":
        player.x = door_x
        player.y = bounds.bottom - half - 4

    player.vx = 0.0
    player.vy = 0.0


def _set_champion_chance(level):
    enemy_module.CHAMPION_CHANCE = min(0.10, (level*2) / 100)
    enemy_module.CURRENT_LEVEL   = level


def build_game():
    """Initialise and return all game-state objects for a fresh run."""
    _set_champion_chance(1)
    room_module.randomize_level_colors()
    start, rooms_grid = generate_dungeon()
    player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

    return dict(
        active_room=start,
        player=player,
        projectiles=[],
        enemy_projectiles=[],
        notif_text="",
        notif_timer=0.0,
        rooms_grid=rooms_grid,
        visited_rooms={start},
        level=1,
    )


def _setup_wasm_scaling(native_w, native_h):
    """Inject JS that CSS-scales the pygbag canvas to fill the browser window."""
    from js import document
    script = document.createElement("script")
    script.textContent = f"""
    (function() {{
        var GW = {native_w}, GH = {native_h};
        function resize() {{
            var cvs = document.querySelector('canvas');
            if (!cvs) {{ setTimeout(resize, 50); return; }}
            var s = Math.min(window.innerWidth / GW, window.innerHeight / GH);
            cvs.style.position        = 'absolute';
            cvs.style.width           = (GW * s) + 'px';
            cvs.style.height          = (GH * s) + 'px';
            cvs.style.left            = ((window.innerWidth  - GW * s) / 2) + 'px';
            cvs.style.top             = ((window.innerHeight - GH * s) / 2) + 'px';
            cvs.style.imageRendering  = 'auto';
            document.body.style.margin     = '0';
            document.body.style.background = '#000';
            document.body.style.overflow   = 'hidden';
        }}
        resize();
        window.addEventListener('resize', resize);

        // Auto-dismiss pygbag's "click to start" loading screen
        function tryStart() {{
            var cvs = document.querySelector('canvas');
            if (!cvs) {{ setTimeout(tryStart, 100); return; }}
            cvs.dispatchEvent(new MouseEvent('click', {{bubbles: true}}));
        }}
        setTimeout(tryStart, 500);
    }})();
    """
    document.body.appendChild(script)


async def main():
    pygame.init()
    NATIVE_W  = HUD_WIDTH + SCREEN_WIDTH   # 960
    NATIVE_H  = SCREEN_HEIGHT              # 576
    if _WASM:
        display = pygame.display.set_mode((NATIVE_W, NATIVE_H))
        _setup_wasm_scaling(NATIVE_W, NATIVE_H)
    else:
        display = pygame.display.set_mode((NATIVE_W, NATIVE_H), pygame.RESIZABLE)
    pygame.display.set_caption("Roguelike")
    clock     = pygame.time.Clock()
    canvas    = pygame.Surface((NATIVE_W, NATIVE_H))   # fixed-res render target
    game_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    hud_panel = pygame.Rect(0, 0, HUD_WIDTH, SCREEN_HEIGHT)
    screen    = canvas   # all existing draw calls use this name unchanged

    state = build_game()
    game_over = False
    restart_hold = 0.0
    running = True

    while running:
        dt = clock.tick(FPS) / 1000.0

        # --- Events ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if not _WASM and event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if not _WASM and event.type == pygame.VIDEORESIZE:
                display = pygame.display.set_mode(event.size, pygame.RESIZABLE)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
                if not game_over:
                    _p = state["player"]
                    _r = state["active_room"]
                    if _p.stats.bombs > 0:
                        _p.stats.bombs -= 1
                        _r.placed_bombs.append(PlacedBomb(_p.x, _p.y))

        keys = pygame.key.get_pressed()

        # --- Restart (hold R) ---
        if keys[pygame.K_r]:
            restart_hold += dt
            if restart_hold >= _RESTART_HOLD:
                state = build_game()
                game_over = False
                restart_hold = 0.0
        else:
            restart_hold = 0.0

        # --- Game over handling ---
        if not game_over:
            room   = state["active_room"]
            player = state["player"]

            room.update(dt)
            open_sides = set() if room.enemies else set(room.connections.keys())
            player.update(dt, keys, room, open_sides=open_sides)

            # --- Room transition ---
            exit_dir = room.check_exit(player.x, player.y)
            if exit_dir and exit_dir in room.locked_connections:
                if player.stats.keys > 0:
                    player.stats.keys -= 1
                    room._unlock_connection(exit_dir)
                else:
                    half = player.stats.size / 2
                    b = room.bounds
                    if exit_dir == "right":
                        player.x = b.right - half
                        player.vx = 0.0
                    elif exit_dir == "left":
                        player.x = b.left + half
                        player.vx = 0.0
                    elif exit_dir == "down":
                        player.y = b.bottom - half
                        player.vy = 0.0
                    elif exit_dir == "up":
                        player.y = b.top + half
                        player.vy = 0.0
                    exit_dir = None
            if exit_dir:
                new_room = room.connections[exit_dir]
                _place_at_entry(player, new_room, exit_dir)
                state["active_room"] = new_room
                state["visited_rooms"].add(new_room)
                state["projectiles"] = []
                state["enemy_projectiles"] = []
                room = new_room

            # --- Spike tile damage (1 HP/s cooldown, flight immune) ---
            if not player.stats.flight and player._spike_timer <= 0:
                tile = room.tile_at_pixel(player.x, player.y)
                if tile == TileType.SPIKE or (tile == TileType.SPIKE_TIMED and room.spike_timed_active):
                    player.take_damage(1)
                    player._spike_timer = 1.0

            # --- Player shooting ---
            if player.can_shoot:
                for key, (dx, dy) in SHOOT_DIRS.items():
                    if keys[key]:
                        state["projectiles"].append(player.shoot(dx, dy))
                        break

            # --- Update player projectiles ---
            for proj in state["projectiles"]:
                proj.update(dt, room)
            state["projectiles"] = [p for p in state["projectiles"] if p.alive]

            # --- Update enemies and collect their projectiles ---
            enemy_projectiles = state["enemy_projectiles"]
            _enemy_hp_before = {id(e): e.stats.health for e in room.enemies}
            _player_hp_before = player.stats.health
            for enemy in room.enemies:
                fired = enemy.update(dt, room, player)
                enemy_projectiles.extend(fired)
            enemy_module.resolve_enemy_collisions(room.enemies, room)

            for proj in enemy_projectiles:
                proj.update(dt, room)

            # Enemy projectiles vs player
            for proj in enemy_projectiles:
                if not proj.alive:
                    continue
                if math.hypot(proj.x - player.x, proj.y - player.y) < proj.radius + player.stats.size / 2:
                    player.take_damage(proj.damage)
                    proj.alive = False
            state["enemy_projectiles"] = [p for p in enemy_projectiles if p.alive]

            # Player projectiles vs enemies
            for proj in state["projectiles"]:
                for enemy in room.enemies:
                    if not proj.alive:
                        break
                    if id(enemy) in proj._hit_ids:
                        continue
                    dx = proj.x - enemy.x
                    dy = proj.y - enemy.y
                    if math.hypot(dx, dy) < proj.radius + enemy.stats.size / 2:
                        enemy.take_damage(proj.damage)
                        enemy.apply_knockback(proj.vx, proj.vy)
                        proj._hit_ids.add(id(enemy))
                        if not proj.piercing:
                            proj.alive = False

            # --- Blood stains ---
            if player.stats.health < _player_hp_before:
                add_stain(room, player.x, player.y)
            for e in room.enemies:
                if e.stats.health < _enemy_hp_before.get(id(e), e.stats.health):
                    add_stain(room, e.x, e.y)
            had_enemies = bool(room.enemies)
            room.enemies = [e for e in room.enemies if e.alive]
            if had_enemies and not room.enemies and not room._reward_given:
                room._reward_given = True
                _spawn_room_clear_reward(room)

            # --- Items ---
            for item in room.items:
                if not item.collected:
                    item.check_collection(player)
                    if item.collected:
                        state["notif_text"]  = item.name
                        state["notif_timer"] = _NOTIF_DURATION
            room.items = [i for i in room.items if not i.collected]

            # --- Ladder (next level descent) ---
            if room.ladder and room.ladder.check_touch(player):
                next_level = state["level"] + 1
                _set_champion_chance(next_level)
                room_module.randomize_level_colors()
                start, rooms_grid = generate_dungeon()
                player.x = SCREEN_WIDTH // 2
                player.y = SCREEN_HEIGHT // 2
                player.vx = 0.0
                player.vy = 0.0
                state["active_room"]     = start
                state["rooms_grid"]      = rooms_grid
                state["visited_rooms"]   = {start}
                state["projectiles"]     = []
                state["enemy_projectiles"] = []
                state["level"]           = next_level
                state["notif_text"]      = f"LEVEL  {next_level}"
                state["notif_timer"]     = _NOTIF_DURATION
                room = start

            # --- Placed bombs ---
            for bomb in room.placed_bombs:
                bomb.update(dt, player, room.enemies, room)
            room.placed_bombs = [b for b in room.placed_bombs if not b.done]

            # --- Chests ---
            for chest in room.chests:
                chest.update(dt, room)
                chest.check_interaction(player, room)

            # --- Slime puddles ---
            for puddle in room.slime_puddles:
                puddle.update(dt)
                puddle.check_damage(player)
            room.slime_puddles = [p for p in room.slime_puddles if not p.expired]

            # --- Pickups ---
            for pickup in room.pickups:
                pickup.update(dt, room)
                pickup.check_collection(player)
            room.pickups = [p for p in room.pickups if not p.collected]

            if state["notif_timer"] > 0:
                state["notif_timer"] -= dt

            if player.stats.health <= 0:
                game_over = True

        # --- Draw ---
        room   = state["active_room"]
        player = state["player"]

        # Game world → off-screen surface, then blit to the right of the HUD
        room.draw(game_surf)
        for bomb in room.placed_bombs:
            bomb.draw(game_surf)
        for chest in room.chests:
            chest.draw(game_surf)
        for item in room.items:
            item.draw(game_surf, player.x, player.y)
        for pickup in room.pickups:
            pickup.draw(game_surf)
        for enemy in room.enemies:
            enemy.draw(game_surf)
        player.draw(game_surf)
        for proj in state["projectiles"]:
            proj.draw(game_surf)
        for proj in state["enemy_projectiles"]:
            proj.draw(game_surf)
        boss = next((e for e in room.enemies if isinstance(e, (Boss, Slimer))), None)
        if boss:
            draw_boss_healthbar(game_surf, boss, SCREEN_WIDTH)
        screen.blit(game_surf, (HUD_WIDTH, 0))

        # HUD panel on the left
        draw_hud(screen, player.stats, hud_panel,
                 state["rooms_grid"], state["visited_rooms"], room,
                 level=state["level"])

        if state["notif_timer"] > 0:
            draw_notification(screen, state["notif_text"], state["notif_timer"],
                              HUD_WIDTH, SCREEN_WIDTH, SCREEN_HEIGHT)

        if game_over:
            draw_game_over(screen, HUD_WIDTH, SCREEN_WIDTH, SCREEN_HEIGHT,
                           restart_hold / _RESTART_HOLD)

        # Scale canvas to display, letterboxing to preserve aspect ratio
        dw, dh = display.get_size()
        scale  = min(dw / NATIVE_W, dh / NATIVE_H)
        sw, sh = int(NATIVE_W * scale), int(NATIVE_H * scale)
        if sw == NATIVE_W and sh == NATIVE_H:
            display.blit(canvas, (0, 0))
        else:
            display.fill((0, 0, 0))
            display.blit(pygame.transform.scale(canvas, (sw, sh)),
                         ((dw - sw) // 2, (dh - sh) // 2))
        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()


asyncio.run(main())
