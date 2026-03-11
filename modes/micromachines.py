import pygame
import random
import math

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BLACK,
    DIFFICULTY_SETTINGS, DIFF_NORMAL, MODE_MICROMACHINES,
)
from core.sound import music_loops
import core.sound as _snd
from core.hud import draw_hud
from shared.game_mode import GameMode
from sprites.micromachines_sprites import (
    MicroPlayer, OilSlickHazard, TrackBarrier, TinyCar,
    MicroCoin, MicroPowerUp,
)
from backgrounds.micromachines_bg import MicroMachinesBG
from bosses.micromachines_boss import MicroMachinesBoss


class MicroMachinesMode(GameMode):
    MODE_NAME = "MICRO MACHINES"
    MODE_INDEX = MODE_MICROMACHINES
    MUSIC_KEY = "micromachines"

    BOSS_DISTANCE_THRESHOLD = 0.5
    BOSS_SCORE_THRESHOLD = 3000
    BOSS_TIME_THRESHOLD = 1800  # ~30s

    BOSS_POINTS = 5000

    # No coin particles for top-down view
    COIN_PARTICLE_COUNT = 0

    # Circle shield for top-down car
    SHIELD_DIMS = (42, 42)
    SHIELD_OFFSET = (-21, -21)
    SHIELD_SHAPE = 'circle'

    # Faster asteroid spawning
    ASTEROID_SPAWN_INTERVAL = 35

    def __init__(self, particles, shake, shared_state):
        super().__init__(particles, shake, shared_state)
        self.bg = MicroMachinesBG(tier=shared_state.evolution_tier)
        self.obstacles = pygame.sprite.Group()
        self.oil_slicks = pygame.sprite.Group()
        self.tiny_cars = pygame.sprite.Group()

        self.obstacle_timer = 0
        self.oil_timer = 0
        self.car_timer = 0
        self.coin_timer = 0
        self.powerup_timer = 0
        self.scroll_speed = 3.0

    def setup(self):
        diff = self.shared_state.difficulty
        selected_diff = diff if diff in DIFFICULTY_SETTINGS else DIFF_NORMAL

        tier = self.shared_state.evolution_tier
        if self.two_player:
            p1 = MicroPlayer(self.particles, 1, diff=selected_diff, tier=tier)
            p1.px = SCREEN_WIDTH // 2 - 40
            p1.py = SCREEN_HEIGHT - 100
            p2 = MicroPlayer(self.particles, 2, diff=selected_diff, tier=tier)
            p2.px = SCREEN_WIDTH // 2 + 40
            p2.py = SCREEN_HEIGHT - 100
            self.players = [p1, p2]
        else:
            p1 = MicroPlayer(self.particles, 1, solo=True, diff=selected_diff, tier=tier)
            p1.px = SCREEN_WIDTH // 2
            p1.py = SCREEN_HEIGHT - 100
            self.players = [p1]

        # Wire track background into players for track constraint
        for p in self.players:
            p.track_bg = self.bg

        self.shared_state.inject_into_players(self.players)

        # Configure AI players
        def _rebuild_car(p):
            p.base_surf = p._make_car()
            p.image = p.base_surf.copy()
        self.configure_ai_players(rebuild_sprite_fn=_rebuild_car)

        for p in self.players:
            self.all_sprites.add(p)

        # Initialize task system
        self.init_tasks(boss_rush=getattr(self, '_boss_rush', False))

        if _snd.sound_enabled and music_loops and not _snd.music_channel.get_busy():
            _snd.music_channel.play(music_loops.get("micromachines", music_loops.get("desert")), loops=-1)
            _snd.music_channel.set_volume(0.08)

    def handle_event(self, event):
        pass

    def update(self, keys):
        super().update(keys)

        alive_players = self.get_alive_players()
        if not alive_players:
            _snd.play_sfx("gameover")
            return 'gameover'

        # Player-centric camera: scroll speed based on player speed + screen position bias
        avg_speed = sum(abs(p.speed) for p in alive_players) / len(alive_players)
        target_scroll = max(avg_speed * 0.7, 2.0)
        # Bias: if player is high on screen, scroll faster; if low, slow down
        avg_py = sum(p.py for p in alive_players) / len(alive_players)
        screen_bias = (avg_py - SCREEN_HEIGHT * 0.55) * 0.03
        self.scroll_speed = max(1.5, min(10.0, target_scroll - screen_bias))

        # Gently push player py toward home zone (screen center-ish)
        for p in alive_players:
            home_y = SCREEN_HEIGHT * 0.6
            drift = (home_y - p.py) * 0.015
            p.py += drift

        for ai in self.ai_controllers:
            ai.update(self)

        for p in self.players:
            p.update(keys, self.scroll_speed)

        self.game_distance += self.scroll_speed * 0.01
        self.difficulty_scale = 1.0 + self.game_distance * 0.1
        diff_s = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS[DIFF_NORMAL])

        self.milestone.check(self.game_distance)
        self.milestone.update()
        self.floating_texts[:] = [ft for ft in self.floating_texts if ft.update()]

        # Update background
        self.bg.update(self.scroll_speed)

        # --- Phase dispatch (boss/asteroid/normal) ---
        result = self._update_phase_logic(keys, alive_players,
                                          self.scroll_speed, diff_s)
        if result:
            return result

        # --- Spawning ---
        if self.boss_active:
            spawn_mult = 0.3
        elif self.phase == 'asteroids':
            spawn_mult = 0.15
        else:
            spawn_mult = 1.0

        self.obstacle_timer += 1
        if self.obstacle_timer > max(25, int(70 / self.difficulty_scale)) and random.random() < spawn_mult:
            pos = self._spawn_on_track_edge()
            if pos:
                b = TrackBarrier(pos[0], pos[1])
                self.all_sprites.add(b)
                self.obstacles.add(b)
                # 25% chance to spawn a hazard coin near the barrier
                if random.random() < 0.25:
                    hc = MicroCoin(pos[0] + random.randint(-40, 40),
                                   pos[1] + random.randint(-20, 20), hazard=True)
                    self.all_sprites.add(hc)
                    self.coins_group.add(hc)
            self.obstacle_timer = 0

        self.oil_timer += 1
        if self.oil_timer > 200:
            pos = self._spawn_on_track()
            if pos:
                oil = OilSlickHazard(pos[0], pos[1], tier=self.shared_state.evolution_tier)
                self.all_sprites.add(oil)
                self.oil_slicks.add(oil)
            self.oil_timer = 0

        self.car_timer += 1
        if self.car_timer > 120:
            pos = self._spawn_on_track(y_offset=-50)
            if pos:
                direction = random.choice(['same', 'oncoming'])
                car = TinyCar(pos[0], pos[1], direction=direction, track_bg=self.bg)
                self.all_sprites.add(car)
                self.tiny_cars.add(car)
            self.car_timer = 0

        self.coin_timer += 1
        if self.coin_timer > 30:
            pos = self._spawn_on_track(y_offset=-20)
            if pos:
                c = MicroCoin(pos[0], pos[1])
                self.all_sprites.add(c)
                self.coins_group.add(c)
            self.coin_timer = 0

        self.powerup_timer += 1
        if self.powerup_timer > 140:
            # Spawn 1-2 powerups (30% chance for double drop)
            count = 2 if random.random() < 0.3 else 1
            for _ in range(count):
                pos = self._spawn_on_track()
                if pos:
                    pu = MicroPowerUp(pos[0], pos[1], tier=self.shared_state.evolution_tier)
                    self.all_sprites.add(pu)
                    self.powerups_group.add(pu)
            self.powerup_timer = 0

        # Update sprites
        for b in list(self.obstacles):
            b.update(self.scroll_speed)
        for oil in list(self.oil_slicks):
            oil.update(self.scroll_speed)
        for car in list(self.tiny_cars):
            car.update(self.scroll_speed)
        for c in list(self.coins_group):
            c.update(self.scroll_speed, players=alive_players)
        for pu in list(self.powerups_group):
            pu.update(self.scroll_speed, players=alive_players)
            # Sparkle particle trail
            if pu.alive() and pu.pulse % 4 == 0:
                self.particles.emit(
                    pu.rect.centerx + random.randint(-3, 3),
                    pu.rect.centery + random.randint(-2, 3),
                    pu.color, [random.uniform(-0.5, 0.5), random.uniform(-1.0, 0.5)],
                    22, 2)

        # Collisions
        for p in alive_players:
            if p.invincible_timer <= 0 and not p.ghost_mode and not p.phase:
                hit = pygame.sprite.spritecollideany(p, self.obstacles)
                if hit:
                    hit.kill()
                    p.take_hit(self.shake)
                    if self._check_all_dead():
                        return 'gameover'

                car_hit = pygame.sprite.spritecollideany(p, self.tiny_cars)
                if car_hit:
                    car_hit.kill()
                    p.take_hit(self.shake)
                    if self._check_all_dead():
                        return 'gameover'

            # Oil slick = full spinout (phase skips oil too)
            oil_hit = pygame.sprite.spritecollideany(p, self.oil_slicks)
            if oil_hit and not p.ghost_mode and not p.phase:
                if p.spinout_timer <= 0:
                    p.spinout_timer = 45  # 0.75s of uncontrolled spin
                    p.spinout_dir = random.choice([-1, 1])
                    from core.sound import play_sfx
                    play_sfx("oil_splat")

            # Coins + Powerups
            collected = pygame.sprite.spritecollide(p, self.coins_group, True)
            self._collect_coins(p, collected)

            collected_pups = pygame.sprite.spritecollide(p, self.powerups_group, True)
            self._collect_powerups(p, collected_pups)

        self._check_near_misses()

        # Task system tick
        if self.task_mgr:
            self.task_mgr.tick(self)

        # New weapon systems
        self._update_homing_rockets(alive_players)
        self._update_orbit_orbs(alive_players)

        self.particles.update()
        self.shake.update()
        return None

    def draw(self, screen):
        screen.fill(BLACK)
        self.bg.draw(screen)

        self.particles.draw(screen)
        self.all_sprites.draw(screen)

        # Draw heat bolts, homing rockets, and orbit orbs
        self.heat_bolts.draw(screen)
        self.homing_rockets.draw(screen)
        self.orbit_orbs.draw(screen)

        alive_players = self.get_alive_players()
        self._draw_powerup_effects(screen, alive_players)

        draw_hud(screen, self.players, self.game_distance, 999, self.two_player,
                 tier=self.shared_state.evolution_tier, compact=True,
                 level_label=self.shared_state.level_label)

        self._draw_common_overlay(screen)

    # --- Hook overrides ---

    def _asteroid_spawn_pos(self):
        from sprites.asteroid import DIR_DOWN
        ax = random.randint(80, SCREEN_WIDTH - 80)
        return (ax, -40, DIR_DOWN, {})

    def _get_near_miss_obstacles(self):
        return self.obstacles, lambda obs: obs.rect.top > SCREEN_HEIGHT

    # --- Mode-specific ---

    def _spawn_on_track(self, y_offset=-40):
        """Return (x, screen_y) on the track ahead of screen, or None."""
        world_y = self.bg.scroll_offset_value + y_offset
        bounds = self.bg.get_track_bounds_at_world_y(world_y)
        if bounds is None:
            return None
        left, _center, right = bounds
        margin = 20
        if right - left < margin * 2 + 10:
            return None
        x = random.randint(int(left) + margin, int(right) - margin)
        return (x, y_offset)

    def _spawn_on_track_edge(self, y_offset=-40):
        """Return (x, screen_y) near a track edge for barriers."""
        world_y = self.bg.scroll_offset_value + y_offset
        bounds = self.bg.get_track_bounds_at_world_y(world_y)
        if bounds is None:
            return None
        left, _center, right = bounds
        side = random.choice(['left', 'right'])
        x = int(left + 15) if side == 'left' else int(right - 15)
        return (x, y_offset)

    def _create_boss(self):
        return MicroMachinesBoss(self.particles, shake=self.shake,
                                evolution_tier=self.shared_state.evolution_tier,
                                track_bg=self.bg)

    _surge_speed = 8

    def _bolt_direction(self):
        """Micro Machines: bolts fire in player's facing direction."""
        return "aimed"

    def _create_bolts_for_player(self, p, bx, by, heat_bolts_group):
        """Create directional bolts that fire in the player's facing angle."""
        from shared.boss_base import HeatBolt

        bolt = HeatBolt(bx, by, p.color_accent)
        # Override speed to use directional velocity
        bolt_speed = 12
        bolt._vx = math.cos(p.angle) * bolt_speed
        bolt._vy = math.sin(p.angle) * bolt_speed
        bolt._aimed = True  # Flag for directional update
        heat_bolts_group.add(bolt)

    def _update_boss_bolts(self, keys, alive_players):
        """Micro Machines: directional bolts + boss collision."""
        has_target = self.boss and self.boss.alive
        for p in alive_players:
            fired, bx, by = p.try_fire_heat_bolt(keys, auto_fire=has_target)
            if fired:
                self._create_bolts_for_player(p, bx, by, self.heat_bolts)

        from core.constants import SOLAR_YELLOW, SOLAR_WHITE
        for bolt in list(self.heat_bolts):
            if getattr(bolt, '_aimed', False):
                bolt.rect.x += int(bolt._vx)
                bolt.rect.y += int(bolt._vy)
                if (bolt.rect.bottom < -20 or bolt.rect.top > SCREEN_HEIGHT + 20 or
                        bolt.rect.right < -20 or bolt.rect.left > SCREEN_WIDTH + 20):
                    bolt.alive = False
                    bolt.kill()
                    continue
            else:
                bolt.update()
            if not bolt.alive:
                continue
            if self.boss and self.boss.alive and bolt.rect.colliderect(self.boss.rect):
                self.boss.take_damage(bolt.damage, "heat_bolt")
                self.particles.burst(bolt.rect.centerx, bolt.rect.centery,
                                     [SOLAR_YELLOW, SOLAR_WHITE], 6, 3, 20, 2)
                bolt.kill()

    def get_rocket_targets(self):
        targets = super().get_rocket_targets()
        targets.extend(list(self.obstacles))
        targets.extend(list(self.tiny_cars))
        return targets

    def get_nukeable_groups(self):
        return [self.oil_slicks, self.tiny_cars]

    def cleanup(self):
        if _snd.music_channel and _snd.music_channel.get_busy():
            _snd.music_channel.fadeout(300)
        super().cleanup()
