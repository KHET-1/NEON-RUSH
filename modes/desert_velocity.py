import pygame
import random
import logging

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, NEON_CYAN, NEON_MAGENTA,
    SOLAR_YELLOW, SOLAR_WHITE, COIN_GOLD,
    ROAD_LEFT, ROAD_RIGHT, ROAD_CENTER,
    DIFF_NORMAL, DIFFICULTY_SETTINGS,
    MODE_DESERT,
)
from core.sound import music_loops
import core.sound as _snd
from core.hud import draw_hud, FloatingText
from shared.game_mode import GameMode
from sprites.vehicle import Player
from sprites.desert_sprites import Obstacle, Coin, PowerUp, SolarFlare
from backgrounds.desert_bg import Background
from bosses.desert_boss import DesertBoss


log = logging.getLogger("neon_rush.desert_velocity")


class DesertVelocityMode(GameMode):
    MODE_NAME = "DESERT VELOCITY"
    MODE_INDEX = MODE_DESERT
    MUSIC_KEY = "desert"

    BOSS_DISTANCE_THRESHOLD = 1.2
    BOSS_SCORE_THRESHOLD = 1200
    BOSS_TIME_THRESHOLD = 2700  # ~45s

    def __init__(self, particles, shake, shared_state):
        super().__init__(particles, shake, shared_state)
        self.bg = Background(particles, tier=shared_state.evolution_tier)
        self.obstacles = pygame.sprite.Group()
        self.flares = pygame.sprite.Group()

        self.obstacle_timer = 0
        self.coin_timer = 0
        self.powerup_timer = 0
        self.flare_timer = random.randint(600, 1200)

        # Road geometry for V2 pseudo-3D
        self._tier = shared_state.evolution_tier
        self.road_geometry = self.bg.road_geometry  # None for V1
        log.info("DesertVelocityMode init: tier=%d, road_geometry=%s",
                 self._tier, "active" if self.road_geometry else "none")

    def setup(self):
        diff = self.shared_state.difficulty
        selected_diff = diff if diff in DIFFICULTY_SETTINGS else DIFF_NORMAL

        tier = self.shared_state.evolution_tier
        if self.two_player:
            p1 = Player(self.particles, 1, ROAD_CENTER - 60, diff=selected_diff, tier=tier)
            p2 = Player(self.particles, 2, ROAD_CENTER + 60, diff=selected_diff, tier=tier)
            self.players = [p1, p2]
        else:
            p1 = Player(self.particles, 1, ROAD_CENTER, solo=True, diff=selected_diff, tier=tier)
            self.players = [p1]

        # Inject carried state from previous modes (if any)
        if self.shared_state.bosses_defeated > 0:
            self.shared_state.inject_into_players(self.players)

        # Configure AI players
        def _rebuild_vehicle(p):
            from sprites.vehicle import make_vehicle_surface
            p.base_image = make_vehicle_surface(p.color_main, p.color_accent)
            p.ghost_image = make_vehicle_surface(p.color_main, p.color_accent, True)
            p.image = p.base_image.copy()
        self.configure_ai_players(rebuild_sprite_fn=_rebuild_vehicle)

        for p in self.players:
            self.all_sprites.add(p)

        # Initialize task system
        self.init_tasks(boss_rush=getattr(self, '_boss_rush', False))

        # Start music
        if _snd.sound_enabled and music_loops and not _snd.music_channel.get_busy():
            _snd.music_channel.play(music_loops["desert"], loops=-1)
            _snd.music_channel.set_volume(0.04)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            prev_keys = pygame.key.get_pressed()
            is_new = True
            now_ms = pygame.time.get_ticks()
            if event.key in (pygame.K_LEFT, pygame.K_a):
                for p in self.players:
                    if p.alive and not p.is_ai and event.key in p.keys_left:
                        p.on_direction_tap(-1, now_ms, is_new)
                        break
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                for p in self.players:
                    if p.alive and not p.is_ai and event.key in p.keys_right:
                        p.on_direction_tap(1, now_ms, is_new)
                        break

    def update(self, keys):
        super().update(keys)

        any_slowmo = any(p.slowmo for p in self.players if p.alive)
        slowmo_mult = 0.5 if any_slowmo else 1.0

        alive_players = self.get_alive_players()
        if not alive_players:
            if _snd.engine_channel and _snd.engine_channel.get_busy():
                _snd.engine_channel.fadeout(300)
            _snd.play_sfx("gameover")
            return 'gameover'

        max_speed = max(p.speed for p in alive_players)
        scroll_speed = max_speed * slowmo_mult

        # Advance road geometry (needed for V2 sprite projection, even in headless)
        if self._tier >= 2:
            self.bg.tick_road(scroll_speed * (0.5 if any_slowmo else 1.0))

        for ai in self.ai_controllers:
            ai.update(self)

        for p in self.players:
            p.update(keys, any_slowmo, road_geometry=self.road_geometry)

        self.game_distance += scroll_speed * 0.01
        self.difficulty_scale = 1.0 + self.game_distance * 0.15
        diff_s = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS[DIFF_NORMAL])

        # Periodic status log (~every 3s at 144fps)
        if self.tick % 432 == 0:
            rg = self.road_geometry
            curve_info = f"curve={rg.current_curve:.3f}" if rg else "no_rg"
            log.info("tick=%d dist=%.2f spd=%.1f obs=%d coins=%d pups=%d flares=%d | %s",
                     self.tick, self.game_distance, scroll_speed,
                     len(self.obstacles), len(self.coins_group),
                     len(self.powerups_group), len(self.flares), curve_info)

        self.milestone.check(self.game_distance)
        self.milestone.update()

        for p in self.players:
            if p.alive:
                p.combo.update()

        self.floating_texts[:] = [ft for ft in self.floating_texts if ft.update()]

        # --- Phase dispatch (boss/asteroid/normal) ---
        result = self._update_phase_logic(keys, alive_players,
                                          scroll_speed, diff_s)
        if result:
            return result

        # --- Regular spawning (reduced during boss/asteroids, scaled by difficulty) ---
        if self.boss_active:
            spawn_mult = diff_s.get("boss_spawn_suppress", 0.3)
        elif self.phase == 'asteroids':
            spawn_mult = 0.15
        else:
            spawn_mult = 1.0

        self.obstacle_timer += 1
        spawn_rate = max(12, int(45 / (self.difficulty_scale * diff_s["spawn_div"])))
        if self.obstacle_timer > spawn_rate and random.random() < spawn_mult:
            if self._tier >= 2:
                lane = random.uniform(-0.8, 0.8)
                obs = Obstacle(min(self.difficulty_scale * diff_s["obstacle_mult"], 3.0),
                               tier=self._tier, lane_offset=lane)
            else:
                obs = Obstacle(min(self.difficulty_scale * diff_s["obstacle_mult"], 3.0))
            self.all_sprites.add(obs)
            self.obstacles.add(obs)
            # 25% chance to spawn a hazard coin near the obstacle
            if random.random() < 0.25:
                if self._tier >= 2:
                    hlane = obs.lane_offset + random.uniform(-0.15, 0.15) if hasattr(obs, 'lane_offset') else random.uniform(-0.8, 0.8)
                    hc = Coin(tier=self._tier, lane_offset=hlane, hazard=True)
                else:
                    hc = Coin(hazard=True)
                    hc.rect.x = obs.rect.x + random.randint(-40, 40)
                    hc.rect.y = obs.rect.y + random.randint(-20, 20)
                self.all_sprites.add(hc)
                self.coins_group.add(hc)
            self.obstacle_timer = 0

        self.coin_timer += 1
        if self.coin_timer > diff_s.get("coin_interval", 40):
            if self._tier >= 2:
                lane = random.uniform(-0.7, 0.7)
                c = Coin(tier=self._tier, lane_offset=lane)
            else:
                c = Coin()
            self.all_sprites.add(c)
            self.coins_group.add(c)
            self.coin_timer = 0

        self.powerup_timer += 1
        if self.powerup_timer > diff_s.get("powerup_interval", 600):
            if self._tier >= 2:
                lane = random.uniform(-0.6, 0.6)
                pu = PowerUp(tier=self._tier, lane_offset=lane)
            else:
                pu = PowerUp()
            self.all_sprites.add(pu)
            self.powerups_group.add(pu)
            self.powerup_timer = 0

        self.flare_timer -= 1
        if self.flare_timer <= 0:
            if self._tier >= 2:
                lane = random.uniform(-0.5, 0.5)
                flare = SolarFlare(self.particles, ROAD_CENTER, tier=self._tier, lane_offset=lane)
            else:
                flare_x = random.randint(ROAD_LEFT + 30, ROAD_RIGHT - 30)
                flare = SolarFlare(self.particles, flare_x)
            self.all_sprites.add(flare)
            self.flares.add(flare)
            self.flare_timer = random.randint(600, 1200)

        # Update sprites
        rg = self.road_geometry
        for obs in list(self.obstacles):
            obs.update(scroll_speed, road_geometry=rg)
        for c in list(self.coins_group):
            c.update(scroll_speed, alive_players, road_geometry=rg)
        for pu in list(self.powerups_group):
            pu.update(scroll_speed, players=alive_players, road_geometry=rg)
            # Sparkle particle trail
            if pu.alive() and pu.pulse % 4 == 0 and pu.rect.x > -900:
                self.particles.emit(
                    pu.rect.centerx + random.randint(-4, 4),
                    pu.rect.centery + random.randint(-2, 4),
                    pu.color, [random.uniform(-0.8, 0.8), random.uniform(-1.5, 0.3)],
                    25, 2)
        for flare in list(self.flares):
            flare.update(scroll_speed, alive_players, road_geometry=rg)

        # Collisions (non-boss)
        for p in alive_players:
            if p.invincible_timer <= 0 and not p.ghost_mode and not p.phase:
                hit = pygame.sprite.spritecollideany(p, self.obstacles)
                if hit:
                    # V2 guard: only collide with projected (near) sprites
                    if not getattr(hit, '_projected', True):
                        hit = None
                if hit:
                    hit.kill()
                    p.take_hit(self.shake)
                    if self._check_all_dead():
                        return 'gameover'

            # Coins + Powerups (base handles V2 filtering via _filter_projected)
            collected_coins = pygame.sprite.spritecollide(p, self.coins_group, True)
            self._collect_coins(p, collected_coins)

            collected_pups = pygame.sprite.spritecollide(p, self.powerups_group, True)
            self._collect_powerups(p, collected_pups)

            if p.flare_hit:
                self.screen_flash = 8
                p.flare_hit = False
                self.floating_texts.append(
                    FloatingText(p.rect.centerx, p.rect.top - 30, "+200 FLARE!", SOLAR_YELLOW, 28))
                # Solar flare environmental damage to boss
                if self.boss_active and self.boss and self.boss.alive:
                    self.boss.take_damage(10, source="environmental")
                    self.floating_texts.append(
                        FloatingText(self.boss.rect.centerx, self.boss.rect.top - 20,
                                     "FLARE -10!", SOLAR_YELLOW, 22))

        # New weapon systems
        self._update_homing_rockets(alive_players)
        self._update_orbit_orbs(alive_players)

        self.particles.update()
        self.shake.update()

        self._check_near_misses()

        # Task system tick
        if self.task_mgr:
            self.task_mgr.tick(self)

        # Engine sound
        if _snd.sound_enabled and max_speed > 1 and _snd.engine_channel and not _snd.engine_channel.get_busy():
            _snd.engine_channel.play(_snd.engine_sound, loops=-1)
            _snd.engine_channel.set_volume(0.05)
        elif max_speed <= 1 and _snd.engine_channel and _snd.engine_channel.get_busy():
            _snd.engine_channel.fadeout(200)
        elif _snd.engine_channel and _snd.engine_channel.get_busy():
            _snd.engine_channel.set_volume(min(0.12, max_speed * 0.01))

        return None

    def draw(self, screen):
        alive_players = self.get_alive_players()
        any_slowmo = any(p.slowmo for p in self.players if p.alive)
        max_speed = max((p.speed for p in alive_players), default=0)
        scroll_speed = max_speed * (0.5 if any_slowmo else 1.0)

        screen.fill(BLACK)
        self.bg.update_and_draw(scroll_speed, screen, any_slowmo)

        if self.screen_flash > 0:
            if not hasattr(self, '_flash_surf'):
                self._flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            t = self.screen_flash / 20.0
            r = int(255 * t)
            g = int(200 * t + 55 * (1 - t))
            b = int(50 * t + 200 * (1 - t))
            self._flash_surf.fill((r, g, b, int(45 * t)))
            screen.blit(self._flash_surf, (0, 0))
            self.screen_flash -= 1

        self.particles.draw(screen)

        # V2: Draw vehicle shadows on road before sprites
        if self._tier >= 2:
            if not hasattr(self, '_shadow_surf'):
                self._shadow_surf = pygame.Surface((50, 16), pygame.SRCALPHA)
                pygame.draw.ellipse(self._shadow_surf, (0, 0, 0, 60), (0, 0, 50, 16))
            for p in alive_players:
                screen.blit(self._shadow_surf,
                            (p.rect.centerx - 25, p.rect.bottom - 4))

        if self._tier >= 2:
            # Sort sprites back-to-front by world_z for correct overdraw
            sprites_sorted = sorted(self.all_sprites.sprites(),
                                    key=lambda s: getattr(s, 'world_z', 0), reverse=True)
            for s in sprites_sorted:
                screen.blit(s.image, s.rect)
        else:
            self.all_sprites.draw(screen)

        # Draw heat bolts, homing rockets, and orbit orbs
        self.heat_bolts.draw(screen)
        self.homing_rockets.draw(screen)
        self.orbit_orbs.draw(screen)

        self._draw_powerup_effects(screen, alive_players)

        # Speed vignette: darken screen edges at high speed
        if max_speed > 12:
            vignette_alpha = min(60, int((max_speed - 12) * 8))
            if not hasattr(self, '_vignette_surf'):
                self._vignette_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            self._vignette_surf.fill((0, 0, 0, 0))
            edge_w = 80
            for i in range(edge_w):
                a = int(vignette_alpha * (1.0 - i / edge_w))
                pygame.draw.line(self._vignette_surf, (0, 0, 0, a), (i, 0), (i, SCREEN_HEIGHT))
                pygame.draw.line(self._vignette_surf, (0, 0, 0, a),
                                 (SCREEN_WIDTH - 1 - i, 0), (SCREEN_WIDTH - 1 - i, SCREEN_HEIGHT))
            edge_h = 50
            for i in range(edge_h):
                a = int(vignette_alpha * 0.6 * (1.0 - i / edge_h))
                pygame.draw.line(self._vignette_surf, (0, 0, 0, a), (0, i), (SCREEN_WIDTH, i))
                pygame.draw.line(self._vignette_surf, (0, 0, 0, a),
                                 (0, SCREEN_HEIGHT - 1 - i), (SCREEN_WIDTH, SCREEN_HEIGHT - 1 - i))
            screen.blit(self._vignette_surf, (0, 0))

        # Slowmo tint (cached surface)
        if any_slowmo:
            if not hasattr(self, '_slowmo_surf'):
                self._slowmo_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                self._slowmo_surf.fill((0, 50, 30, 25))
            screen.blit(self._slowmo_surf, (0, 0))

        draw_hud(screen, self.players, self.game_distance, self.flare_timer, self.two_player,
                 tier=self._tier, level_label=self.shared_state.level_label)

        for p in alive_players:
            p.combo.draw(screen, p.rect.centerx, p.rect.top - 50)

        self._draw_common_overlay(screen)

    # --- Desert-specific hook overrides ---

    def _filter_projected(self, sprites):
        """V2 guard: only interact with projected (near) sprites."""
        if self._tier >= 2:
            return [s for s in sprites if getattr(s, '_projected', True)]
        return sprites

    def _coin_text_color(self, player):
        """Combo-colored coin text: magenta for combos, gold otherwise."""
        return NEON_MAGENTA if player.combo.multiplier > 1 else COIN_GOLD

    def _update_normal_phase(self, keys, alive_players, scroll_speed, diff_s):
        """Normal phase: auto-fire heat bolts at obstacles."""
        for p in alive_players:
            fired, bx, by = p.try_fire_heat_bolt(keys, auto_fire=True)
            if fired:
                self._create_bolts_for_player(p, bx, by, self.heat_bolts)

        # Update heat bolts — destroy obstacles
        for bolt in list(self.heat_bolts):
            bolt.update()
            if not bolt.alive:
                continue
            hit = pygame.sprite.spritecollideany(bolt, self.obstacles)
            if hit:
                hit.kill()
                self.particles.burst(bolt.rect.centerx, bolt.rect.centery,
                                     [SOLAR_YELLOW, SOLAR_WHITE], 6, 3, 20, 2)
                for p in alive_players:
                    pts = 30 * p.score_mult
                    p.score += pts
                bolt.kill()
                self._notify_task('obstacle_killed')

    # --- Asteroid phase hooks (V2-aware) ---

    def _asteroid_spawn_pos(self):
        """V2: center-lane with offset; V1: random road position."""
        from sprites.asteroid import DIR_DOWN
        if self._tier >= 2:
            lane = random.uniform(-0.8, 0.8)
            return (ROAD_CENTER, -50, DIR_DOWN,
                    {'tier': self._tier, 'lane_offset': lane})
        ax = random.randint(ROAD_LEFT + 20, ROAD_RIGHT - 20)
        return (ax, -50, DIR_DOWN, {})

    def _asteroid_prep_fragment(self, parent_ast, frag_info):
        """V2: propagate lane_offset and tier to asteroid fragments."""
        if self._tier >= 2 and getattr(parent_ast, 'tier', 0) >= 2:
            lo = getattr(parent_ast, 'lane_offset', 0) or 0
            frag_info['lane_offset'] = lo + random.uniform(-0.15, 0.15)
            frag_info['tier'] = parent_ast.tier

    def _asteroid_update(self, ast, scroll_speed):
        """Pass road_geometry for V2 projection."""
        ast.update(scroll_speed, road_geometry=self.road_geometry)

    def _asteroid_hit_valid(self, hit):
        """V2 guard: only collide with projected (near) asteroids."""
        return getattr(hit, '_projected', True)

    # --- Environmental + near-miss hooks ---

    def _get_boss_hazard_group(self):
        return self.flares

    def _get_near_miss_obstacles(self):
        return self.obstacles, lambda obs: obs.rect.top > SCREEN_HEIGHT

    # --- Mode-specific ---

    def _create_boss(self):
        return DesertBoss(self.particles, self.difficulty,
                          evolution_tier=self.shared_state.evolution_tier)

    _surge_speed = 15

    def get_rocket_targets(self):
        targets = super().get_rocket_targets()
        targets.extend(list(self.obstacles))
        return targets

    def get_nukeable_groups(self):
        return [self.obstacles]

    def cleanup(self):
        if _snd.engine_channel and _snd.engine_channel.get_busy():
            _snd.engine_channel.fadeout(200)
        if _snd.music_channel and _snd.music_channel.get_busy():
            _snd.music_channel.fadeout(300)
        super().cleanup()
