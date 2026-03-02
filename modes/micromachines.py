import pygame
import random

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
    SHIELD_DIMS = (30, 30)
    SHIELD_OFFSET = (-15, -15)
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

        max_speed = max(abs(p.speed) for p in alive_players)
        self.scroll_speed = max(2, max_speed * 0.8)

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
            x = random.randint(100, SCREEN_WIDTH - 100)
            b = TrackBarrier(x, -30)
            self.all_sprites.add(b)
            self.obstacles.add(b)
            self.obstacle_timer = 0

        self.oil_timer += 1
        if self.oil_timer > 200:
            x = random.randint(100, SCREEN_WIDTH - 100)
            oil = OilSlickHazard(x, -30, tier=self.shared_state.evolution_tier)
            self.all_sprites.add(oil)
            self.oil_slicks.add(oil)
            self.oil_timer = 0

        self.car_timer += 1
        if self.car_timer > 120:
            x = random.randint(100, SCREEN_WIDTH - 100)
            car = TinyCar(x, -30)
            self.all_sprites.add(car)
            self.tiny_cars.add(car)
            self.car_timer = 0

        self.coin_timer += 1
        if self.coin_timer > 30:
            x = random.randint(100, SCREEN_WIDTH - 100)
            c = MicroCoin(x, -20)
            self.all_sprites.add(c)
            self.coins_group.add(c)
            self.coin_timer = 0

        self.powerup_timer += 1
        if self.powerup_timer > 200:
            x = random.randint(100, SCREEN_WIDTH - 100)
            pu = MicroPowerUp(x, -30, tier=self.shared_state.evolution_tier)
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
            c.update(self.scroll_speed)
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

            # Oil slick = spin + slow (phase skips oil too)
            oil_hit = pygame.sprite.spritecollideany(p, self.oil_slicks)
            if oil_hit and not p.ghost_mode and not p.phase:
                p.angle += random.uniform(-0.3, 0.3)
                p.speed *= 0.9

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

    def _create_boss(self):
        return MicroMachinesBoss(self.particles, shake=self.shake,
                                evolution_tier=self.shared_state.evolution_tier)

    _surge_speed = 8

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
