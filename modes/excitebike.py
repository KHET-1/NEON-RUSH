import pygame
import random

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, NEON_CYAN,
    SOLAR_YELLOW, SOLAR_WHITE,
    DIFFICULTY_SETTINGS, DIFF_NORMAL, MODE_EXCITEBIKE,
)
from core.sound import music_loops
import core.sound as _snd
from core.hud import FloatingText, draw_hud
from shared.game_mode import GameMode
from sprites.excitebike_sprites import (
    ExcitebikePlayer, Ramp, Barrier, MudPatch, SideRacer,
    ExcitebikeCoin, ExcitebikePowerUp,
)
from backgrounds.excitebike_bg import ExcitebikeBg
from bosses.excitebike_boss import ExcitebikeBoss


class ExcitebikeMode(GameMode):
    MODE_NAME = "EXCITEBIKE"
    MODE_INDEX = MODE_EXCITEBIKE
    MUSIC_KEY = "excitebike"

    BOSS_DISTANCE_THRESHOLD = 0.8
    BOSS_SCORE_THRESHOLD = 2000
    BOSS_TIME_THRESHOLD = 1800  # ~30s

    BOSS_POINTS = 3000

    # Smaller coin particles for side-scroll
    COIN_PARTICLE_COUNT = 5
    COIN_PARTICLE_SPEED = 15
    COIN_PARTICLE_LIFE = 2
    COIN_PARTICLE_OFFSET_Y = -5

    # Horizontal ellipse shield for bike sprite
    SHIELD_DIMS = (50, 30)
    SHIELD_OFFSET = (-25, -15)

    # Slower asteroid spawning
    ASTEROID_SPAWN_INTERVAL = 45

    # Lighter environmental boss damage particles
    ENV_DAMAGE_PARTICLE_ARGS = (15, 5, 30, 3)

    def __init__(self, particles, shake, shared_state):
        super().__init__(particles, shake, shared_state)
        self.bg = ExcitebikeBg(tier=shared_state.evolution_tier)
        self.barriers = pygame.sprite.Group()
        self.ramps = pygame.sprite.Group()
        self.mud_patches = pygame.sprite.Group()
        self.racers = pygame.sprite.Group()

        self.obstacle_timer = 0
        self.coin_timer = 0
        self.powerup_timer = 0
        self.racer_timer = 0
        self.ramp_timer = 0

    def setup(self):
        diff = self.shared_state.difficulty
        selected_diff = diff if diff in DIFFICULTY_SETTINGS else DIFF_NORMAL

        tier = self.shared_state.evolution_tier
        if self.two_player:
            p1 = ExcitebikePlayer(self.particles, 1, lane=0, diff=selected_diff, tier=tier)
            p2 = ExcitebikePlayer(self.particles, 2, lane=2, diff=selected_diff, tier=tier)
            self.players = [p1, p2]
        else:
            p1 = ExcitebikePlayer(self.particles, 1, lane=1, solo=True, diff=selected_diff, tier=tier)
            self.players = [p1]

        self.shared_state.inject_into_players(self.players)

        # Configure AI players
        self.configure_ai_players(rebuild_sprite_fn=lambda p: setattr(p, 'image', p._make_bike()))

        for p in self.players:
            self.all_sprites.add(p)

        # Initialize task system
        self.init_tasks(boss_rush=getattr(self, '_boss_rush', False))

        if _snd.sound_enabled and music_loops and not _snd.music_channel.get_busy():
            _snd.music_channel.play(music_loops.get("excitebike", music_loops.get("desert")), loops=-1)
            _snd.music_channel.set_volume(0.08)

    def handle_event(self, event):
        pass  # Lane switching handled in update via held keys

    def update(self, keys):
        super().update(keys)

        alive_players = self.get_alive_players()
        if not alive_players:
            _snd.play_sfx("gameover")
            return 'gameover'

        max_speed = max(p.speed for p in alive_players)
        scroll_speed = max_speed

        for ai in self.ai_controllers:
            ai.update(self)

        for p in self.players:
            p.update(keys, scroll_speed)

        self.game_distance += scroll_speed * 0.01
        self.difficulty_scale = 1.0 + self.game_distance * 0.12
        diff_s = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS[DIFF_NORMAL])

        self.milestone.check(self.game_distance)
        self.milestone.update()
        for p in alive_players:
            p.combo.update()
        self.floating_texts[:] = [ft for ft in self.floating_texts if ft.update()]

        # --- Phase dispatch (boss/asteroid/normal) ---
        result = self._update_phase_logic(keys, alive_players,
                                          scroll_speed, diff_s)
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
        spawn_rate = max(20, int(60 / (self.difficulty_scale * diff_s["spawn_div"])))
        if self.obstacle_timer > spawn_rate and random.random() < spawn_mult:
            lane = random.randint(0, 2)
            lane_y = self.bg.get_lane_y(lane)
            if random.random() < 0.6:
                b = Barrier(SCREEN_WIDTH + 50, lane_y, tier=self.shared_state.evolution_tier)
            else:
                b = MudPatch(SCREEN_WIDTH + 80, lane_y)
            self.all_sprites.add(b)
            if isinstance(b, Barrier):
                self.barriers.add(b)
            else:
                self.mud_patches.add(b)
            self.obstacle_timer = 0

        self.ramp_timer += 1
        if self.ramp_timer > 300:
            lane = random.randint(0, 2)
            r = Ramp(SCREEN_WIDTH + 60, self.bg.get_lane_y(lane))
            self.all_sprites.add(r)
            self.ramps.add(r)
            self.ramp_timer = 0

        self.racer_timer += 1
        if self.racer_timer > 180:
            lane = random.randint(0, 2)
            racer = SideRacer(SCREEN_WIDTH + 100, self.bg.get_lane_y(lane))
            self.all_sprites.add(racer)
            self.racers.add(racer)
            self.racer_timer = 0

        self.coin_timer += 1
        if self.coin_timer > 35:
            lane = random.randint(0, 2)
            c = ExcitebikeCoin(SCREEN_WIDTH + 30, self.bg.get_lane_y(lane))
            self.all_sprites.add(c)
            self.coins_group.add(c)
            self.coin_timer = 0

        self.powerup_timer += 1
        if self.powerup_timer > 250:
            lane = random.randint(0, 2)
            pu = ExcitebikePowerUp(SCREEN_WIDTH + 40, self.bg.get_lane_y(lane),
                                   tier=self.shared_state.evolution_tier)
            self.all_sprites.add(pu)
            self.powerups_group.add(pu)
            self.powerup_timer = 0

        # Update sprites
        for b in list(self.barriers):
            b.update(scroll_speed)
        for m in list(self.mud_patches):
            m.update(scroll_speed)
        for r in list(self.ramps):
            r.update(scroll_speed)
        for racer in list(self.racers):
            racer.update(scroll_speed)
        for c in list(self.coins_group):
            c.update(scroll_speed)
        for pu in list(self.powerups_group):
            pu.update(scroll_speed, players=alive_players)
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
                hit = pygame.sprite.spritecollideany(p, self.barriers)
                if hit:
                    hit.kill()
                    p.take_hit(self.shake)
                    if self._check_all_dead():
                        return 'gameover'

                # Racer collision
                hit_racer = pygame.sprite.spritecollideany(p, self.racers)
                if hit_racer:
                    hit_racer.kill()
                    p.take_hit(self.shake)
                    if self._check_all_dead():
                        return 'gameover'

            # Mud slowdown (phase skips mud too)
            mud_hit = pygame.sprite.spritecollideany(p, self.mud_patches)
            if mud_hit and not p.ghost_mode and not p.phase:
                p.speed = max(1, p.speed * 0.95)

            # Ramp launch
            ramp_hit = pygame.sprite.spritecollideany(p, self.ramps)
            if ramp_hit and not p.airborne:
                p.launch(ramp_hit.launch_power)
                ramp_hit.kill()
                self.particles.burst(p.rect.centerx, p.rect.centery,
                                      [SOLAR_YELLOW, NEON_CYAN], 8, 4, 25, 3)
                ramp_pts = 150 * p.score_mult
                p.score += ramp_pts
                self.floating_texts.append(
                    FloatingText(p.rect.centerx, p.rect.top - 20, f"+{ramp_pts} RAMP!", NEON_CYAN))
                _snd.play_sfx("boost")
                self._notify_task('ramp_launched')

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
        alive_players = self.get_alive_players()
        max_speed = max((p.speed for p in alive_players), default=3)
        self.bg.update_and_draw(max_speed, screen)

        if self.screen_flash > 0:
            if not hasattr(self, '_flash_surf'):
                self._flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            self._flash_surf.fill((*SOLAR_WHITE, int(60 * (self.screen_flash / 30))))
            screen.blit(self._flash_surf, (0, 0))
            self.screen_flash -= 1

        self.particles.draw(screen)
        self.all_sprites.draw(screen)

        # Draw heat bolts, homing rockets, and orbit orbs
        self.heat_bolts.draw(screen)
        self.homing_rockets.draw(screen)
        self.orbit_orbs.draw(screen)

        self._draw_powerup_effects(screen, alive_players)

        # HUD
        draw_hud(screen, self.players, self.game_distance, 999, self.two_player,
                 tier=self.shared_state.evolution_tier, compact=True,
                 level_label=self.shared_state.level_label)

        for p in alive_players:
            p.combo.draw(screen, p.rect.centerx, p.rect.top - 40)

        self._draw_common_overlay(screen)

    # --- Hook overrides for horizontal bolt handling ---

    def _update_boss_bolts(self, keys, alive_players):
        """Excitebike: bolts go right instead of up."""
        has_target = self.boss and self.boss.alive
        for p in alive_players:
            fired, bx, by = p.try_fire_heat_bolt(keys, auto_fire=has_target)
            if fired:
                self._create_bolts_for_player(p, bx, by, self.heat_bolts)

        for bolt in list(self.heat_bolts):
            self._asteroid_update_bolt(bolt)
            if not bolt.alive:
                continue
            if self._asteroid_bolt_offscreen(bolt):
                bolt.kill()
                continue
            if self.boss and self.boss.alive and bolt.rect.colliderect(self.boss.rect):
                self.boss.take_damage(bolt.damage, "heat_bolt")
                self.particles.burst(bolt.rect.centerx, bolt.rect.centery,
                                     [SOLAR_YELLOW, SOLAR_WHITE], 6, 3, 20, 2)
                bolt.kill()

    def _asteroid_update_bolt(self, bolt):
        """Horizontal bolt movement."""
        if hasattr(bolt, 'vx'):
            bolt.update()
        else:
            bolt.rect.x += 10

    def _asteroid_bolt_offscreen(self, bolt):
        """Horizontal offscreen check."""
        return bolt.rect.left > SCREEN_WIDTH + 20 or bolt.rect.right < -20

    # --- Asteroid phase hooks ---

    def _asteroid_spawn_pos(self):
        """Spawn asteroids from right side, in random lanes."""
        from sprites.asteroid import DIR_LEFT
        lane = random.randint(0, 2)
        lane_y = self.bg.get_lane_y(lane) + self.bg.LANE_HEIGHT // 2
        return (SCREEN_WIDTH + 50, lane_y, DIR_LEFT, {})

    # --- Environmental + near-miss hooks ---

    def _get_boss_hazard_group(self):
        return self.ramps

    def _get_near_miss_obstacles(self):
        return self.barriers, lambda b: b.rect.right < 0

    # --- Mode-specific ---

    def _create_boss(self):
        return ExcitebikeBoss(self.particles, shake=self.shake,
                              evolution_tier=self.shared_state.evolution_tier)

    _surge_speed = 15

    def _bolt_direction(self):
        return "right"

    def get_rocket_targets(self):
        targets = super().get_rocket_targets()
        targets.extend(list(self.barriers))
        targets.extend(list(self.racers))
        return targets

    def get_nukeable_groups(self):
        return [self.barriers, self.mud_patches]

    def cleanup(self):
        if _snd.engine_channel and _snd.engine_channel.get_busy():
            _snd.engine_channel.fadeout(200)
        if _snd.music_channel and _snd.music_channel.get_busy():
            _snd.music_channel.fadeout(300)
        super().cleanup()
