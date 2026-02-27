import pygame
import random
import math

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, NEON_CYAN, NEON_MAGENTA,
    SOLAR_YELLOW, SOLAR_WHITE, COIN_GOLD, SAND_YELLOW, DESERT_ORANGE,
    ROAD_LEFT, ROAD_RIGHT, ROAD_CENTER,
    DIFF_NORMAL, DIFFICULTY_SETTINGS, SHIELD_BLUE,
    POWERUP_SHIELD, POWERUP_MAGNET, POWERUP_SLOWMO,
    POWERUP_NUKE, POWERUP_PHASE, POWERUP_SURGE,
    POWERUP_COLORS, NUKE_ORANGE, PHASE_CYAN, SURGE_PINK,
    MODE_DESERT,
)
from core.sound import SFX, music_loops
import core.sound as _snd
from core.hud import draw_hud, FloatingText
from core.ui import MilestoneTracker
from shared.game_mode import GameMode
from shared.boss_base import HeatBolt
from sprites.vehicle import Player
from sprites.desert_sprites import Obstacle, Coin, PowerUp, SolarFlare
from backgrounds.desert_bg import Background
from sprites.asteroid import Asteroid, DIR_DOWN
from bosses.desert_boss import DesertBoss
from ai.controller import AIController, BrainController


class DesertVelocityMode(GameMode):
    MODE_NAME = "DESERT VELOCITY"
    MODE_INDEX = MODE_DESERT
    MUSIC_KEY = "desert"

    BOSS_DISTANCE_THRESHOLD = 5.0
    BOSS_SCORE_THRESHOLD = 5000
    BOSS_TIME_THRESHOLD = 180 * 60  # 3 min

    def __init__(self, particles, shake, shared_state):
        super().__init__(particles, shake, shared_state)
        self.bg = Background(particles)
        self.obstacles = pygame.sprite.Group()
        self.coins_group = pygame.sprite.Group()
        self.powerups_group = pygame.sprite.Group()
        self.flares = pygame.sprite.Group()
        self.heat_bolts = pygame.sprite.Group()

        self.ai_controllers = []

        self.obstacle_timer = 0
        self.coin_timer = 0
        self.powerup_timer = 0
        self.flare_timer = random.randint(600, 1200)
        self.screen_flash = 0
        self.difficulty_scale = 1.0
        self.floating_texts = []
        self.milestone = MilestoneTracker()

    def setup(self):
        diff = self.shared_state.difficulty
        selected_diff = diff if diff in DIFFICULTY_SETTINGS else DIFF_NORMAL

        if self.two_player:
            p1 = Player(self.particles, 1, ROAD_CENTER - 60, diff=selected_diff)
            p2 = Player(self.particles, 2, ROAD_CENTER + 60, diff=selected_diff)
            self.players = [p1, p2]
        else:
            p1 = Player(self.particles, 1, ROAD_CENTER, solo=True, diff=selected_diff)
            self.players = [p1]

        # Inject carried state from previous modes (if any)
        if self.shared_state.bosses_defeated > 0:
            self.shared_state.inject_into_players(self.players)

        # Configure AI players
        ai_cfg = self.shared_state.ai_config
        ai_indices = ai_cfg.get("ai_players", [])
        score_mult = ai_cfg.get("score_mult", 1)
        use_brains = self.shared_state.brain_config.get("use_brains", False)
        brain_map = self.shared_state.brain_config.get("brain_map", {})
        self.ai_controllers = []
        for idx in ai_indices:
            if idx < len(self.players):
                p = self.players[idx]
                p.is_ai = True
                p.score_mult = score_mult
                # Use BrainController if brain assigned, else heuristic AIController
                brain = brain_map.get(idx)
                if use_brains and brain is not None:
                    p.color_main = BrainController.COLOR_MAIN
                    p.color_accent = BrainController.COLOR_ACCENT
                    from sprites.vehicle import make_vehicle_surface
                    p.base_image = make_vehicle_surface(p.color_main, p.color_accent)
                    p.ghost_image = make_vehicle_surface(p.color_main, p.color_accent, True)
                    p.image = p.base_image.copy()
                    p.name = brain.name[:10]
                    brain.start_episode(p)
                    self.ai_controllers.append(BrainController(brain, p, MODE_DESERT))
                else:
                    p.color_main = AIController.COLOR_MAIN
                    p.color_accent = AIController.COLOR_ACCENT
                    from sprites.vehicle import make_vehicle_surface
                    p.base_image = make_vehicle_surface(p.color_main, p.color_accent)
                    p.ghost_image = make_vehicle_surface(p.color_main, p.color_accent, True)
                    p.image = p.base_image.copy()
                    p.name = f"AI{idx + 1}"
                    self.ai_controllers.append(AIController(p, MODE_DESERT))

        for p in self.players:
            self.all_sprites.add(p)

        # Start music
        if music_loops and not _snd.music_channel.get_busy():
            _snd.music_channel.play(music_loops["desert"], loops=-1)
            _snd.music_channel.set_volume(0.08)

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
            SFX["gameover"].play()
            return 'gameover'

        max_speed = max(p.speed for p in alive_players)
        scroll_speed = max_speed * slowmo_mult

        for ai in self.ai_controllers:
            ai.update(self)

        for p in self.players:
            p.update(keys, any_slowmo)

        self.game_distance += scroll_speed * 0.01
        self.difficulty_scale = 1.0 + self.game_distance * 0.15
        diff_s = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS[DIFF_NORMAL])

        self.milestone.check(self.game_distance)
        self.milestone.update()

        for p in self.players:
            if p.alive:
                p.combo.update()

        self.floating_texts[:] = [ft for ft in self.floating_texts if ft.update()]

        # --- Boss logic ---
        if self.boss_active and self.boss:
            self.boss.update(alive_players, scroll_speed)

            # Check heat bolt firing
            for p in alive_players:
                fired, bx, by = p.try_fire_heat_bolt(keys)
                if fired:
                    bolt = HeatBolt(bx, by, p.color_accent)
                    self.heat_bolts.add(bolt)
                    self.all_sprites.add(bolt)

            # Update heat bolts
            for bolt in list(self.heat_bolts):
                bolt.update()
                if not bolt.alive:
                    continue
                if self.boss and self.boss.alive and bolt.rect.colliderect(self.boss.rect):
                    self.boss.take_damage(bolt.damage, "heat_bolt")
                    self.particles.burst(bolt.rect.centerx, bolt.rect.centery,
                                         [SOLAR_YELLOW, SOLAR_WHITE], 6, 3, 20, 2)
                    bolt.kill()

            # Check ram damage (player colliding with boss during vulnerability)
            if self.boss and self.boss.alive and self.boss.vulnerable:
                for p in alive_players:
                    if p.rect.colliderect(self.boss.rect) and p.invincible_timer <= 0:
                        self.boss.take_damage(self.boss.RAM_DAMAGE, "ram")
                        p.invincible_timer = 30
                        self.shake.trigger(6, 15)
                        self.particles.burst(p.rect.centerx, p.rect.top,
                                             [NEON_CYAN, SOLAR_YELLOW], 10, 4, 25, 3)

            # Check boss attack hazards hitting players
            if self.boss and self.boss.alive:
                hazards = self.boss.get_attack_hazards()
                for p in alive_players:
                    if p.invincible_timer > 0 or p.ghost_mode:
                        continue
                    for htype, hdata in hazards:
                        hit = False
                        if htype == 'rect' and isinstance(hdata, pygame.Rect):
                            hit = p.rect.colliderect(hdata)
                        elif htype == 'ring':
                            cx, cy, radius, thickness = hdata
                            dx = p.rect.centerx - cx
                            dy = p.rect.centery - cy
                            dist = math.sqrt(dx * dx + dy * dy)
                            hit = abs(dist - radius) < thickness
                        if hit:
                            p.take_hit(self.shake)
                            if not p.alive and not any(pl.alive for pl in self.players):
                                return 'gameover'
                            break

            # Environmental damage: flares hitting boss
            if self.boss and self.boss.alive:
                for flare in list(self.flares):
                    if flare.active and flare.rect.colliderect(self.boss.rect):
                        self.boss.take_damage(self.boss.ENVIRONMENTAL_DAMAGE, "environmental")
                        self.particles.burst(flare.rect.centerx, flare.rect.centery,
                                             [SOLAR_YELLOW, SOLAR_WHITE], 20, 6, 40, 4)
                        flare.active = False
                        flare.kill()

            # Boss defeated?
            if self.boss and self.boss.defeated and self.boss.death_timer <= 0:
                self.boss_active = False
                self.shared_state.snapshot_from_players(self.players)
                self.shared_state.advance_mode()
                for p in alive_players:
                    boss_pts = 2000 * p.score_mult
                    p.score += boss_pts
                    self.floating_texts.append(
                        FloatingText(p.rect.centerx, p.rect.top - 40, f"+{boss_pts} BOSS!", SOLAR_YELLOW, 28))
                return 'boss_defeated'

        elif self.phase == 'asteroids':
            result = self._update_asteroid_phase(keys, alive_players, scroll_speed, diff_s)
            if result:
                return result
        else:
            # Normal gameplay — check asteroid trigger (at 50% of boss thresholds)
            if self.check_asteroid_trigger():
                self.start_asteroid_phase()
                SFX["asteroid_warning"].play()

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
            obs = Obstacle(min(self.difficulty_scale * diff_s["obstacle_mult"], 3.0))
            self.all_sprites.add(obs)
            self.obstacles.add(obs)
            self.obstacle_timer = 0

        self.coin_timer += 1
        if self.coin_timer > diff_s.get("coin_interval", 40):
            c = Coin()
            self.all_sprites.add(c)
            self.coins_group.add(c)
            self.coin_timer = 0

        self.powerup_timer += 1
        if self.powerup_timer > diff_s.get("powerup_interval", 600):
            pu = PowerUp()
            self.all_sprites.add(pu)
            self.powerups_group.add(pu)
            self.powerup_timer = 0

        self.flare_timer -= 1
        if self.flare_timer <= 0:
            flare_x = random.randint(ROAD_LEFT + 30, ROAD_RIGHT - 30)
            flare = SolarFlare(self.particles, flare_x)
            self.all_sprites.add(flare)
            self.flares.add(flare)
            self.flare_timer = random.randint(600, 1200)

        # Update sprites
        for obs in list(self.obstacles):
            obs.update(scroll_speed)
        for c in list(self.coins_group):
            c.update(scroll_speed, alive_players)
        for pu in list(self.powerups_group):
            pu.update(scroll_speed)
        for flare in list(self.flares):
            flare.update(scroll_speed, alive_players)

        # Collisions (non-boss)
        for p in alive_players:
            if p.invincible_timer <= 0 and not p.ghost_mode and not p.phase:
                hit = pygame.sprite.spritecollideany(p, self.obstacles)
                if hit:
                    hit.kill()
                    p.take_hit(self.shake)
                    if not p.alive and not any(pl.alive for pl in self.players):
                        return 'gameover'

            collected_coins = pygame.sprite.spritecollide(p, self.coins_group, True)
            for _ in collected_coins:
                p.coins += 1
                p.combo.hit()
                pts = p.combo.get_bonus(50) * p.score_mult
                p.score += pts
                self.particles.burst(p.rect.centerx, p.rect.centery - 10,
                                      [COIN_GOLD, SOLAR_YELLOW], 6, 3, 20, 2)
                color = NEON_MAGENTA if p.combo.multiplier > 1 else COIN_GOLD
                self.floating_texts.append(FloatingText(p.rect.centerx, p.rect.top - 15, f"+{pts}", color))
                SFX["coin"].play()

            collected_pups = pygame.sprite.spritecollide(p, self.powerups_group, True)
            for pu in collected_pups:
                if pu.kind == POWERUP_SHIELD:
                    p.shield = True
                    p.shield_timer = 600
                elif pu.kind == POWERUP_MAGNET:
                    p.magnet = True
                    p.magnet_timer = 480
                elif pu.kind == POWERUP_SLOWMO:
                    p.slowmo = True
                    p.slowmo_timer = 300
                elif pu.kind == POWERUP_NUKE:
                    for obs in list(self.obstacles):
                        self.particles.burst(obs.rect.centerx, obs.rect.centery,
                                              [NUKE_ORANGE, SOLAR_YELLOW], 8, 4, 25, 2)
                        p.score += 50 * p.score_mult
                        obs.kill()
                    for ast in list(self.asteroids):
                        self.particles.burst(*ast.get_death_particles())
                        p.score += ast.points * p.score_mult
                        self.asteroids_cleared += 1
                        ast.kill()
                    self.shake.trigger(8, 20)
                    self.screen_flash = 20
                    SFX["nuke"].play()
                elif pu.kind == POWERUP_PHASE:
                    p.phase = True
                    p.phase_timer = 360
                    SFX["phase"].play()
                elif pu.kind == POWERUP_SURGE:
                    p.surge = True
                    p.surge_timer = 180
                    p.speed = 15
                    p.invincible_timer = max(p.invincible_timer, 180)
                    SFX["surge"].play()
                pts_pu = 100 * p.score_mult
                p.score += pts_pu
                self.particles.burst(p.rect.centerx, p.rect.centery,
                                      [POWERUP_COLORS[pu.kind]], 8, 4, 30, 3)
                self.floating_texts.append(
                    FloatingText(p.rect.centerx, p.rect.top - 15, f"+{pts_pu}", POWERUP_COLORS[pu.kind]))
                if pu.kind not in (POWERUP_NUKE, POWERUP_PHASE, POWERUP_SURGE):
                    SFX["powerup"].play()

            if p.flare_hit:
                self.screen_flash = 8
                p.flare_hit = False
                self.floating_texts.append(
                    FloatingText(p.rect.centerx, p.rect.top - 30, "+200 FLARE!", SOLAR_YELLOW, 28))

        self.particles.update()
        self.shake.update()

        # Engine sound
        if max_speed > 1 and _snd.engine_channel and not _snd.engine_channel.get_busy():
            _snd.engine_channel.play(_snd.engine_sound, loops=-1)
            _snd.engine_channel.set_volume(0.05)
        elif max_speed <= 1 and _snd.engine_channel and _snd.engine_channel.get_busy():
            _snd.engine_channel.fadeout(200)
        elif _snd.engine_channel and _snd.engine_channel.get_busy():
            _snd.engine_channel.set_volume(min(0.12, max_speed * 0.01))

        return None

    def _update_asteroid_phase(self, keys, alive_players, scroll_speed, diff_s):
        """Handle asteroid phase: spawn, shoot, collide, check boss trigger."""
        # Fire heat bolts
        for p in alive_players:
            fired, bx, by = p.try_fire_heat_bolt(keys)
            if fired:
                bolt = HeatBolt(bx, by, p.color_accent)
                self.heat_bolts.add(bolt)
                self.all_sprites.add(bolt)

        # Update heat bolts — check asteroid collisions
        for bolt in list(self.heat_bolts):
            bolt.update()
            if not bolt.alive:
                continue
            for ast in list(self.asteroids):
                if bolt.rect.colliderect(ast.rect):
                    destroyed = ast.take_hit(bolt.damage)
                    self.particles.burst(bolt.rect.centerx, bolt.rect.centery,
                                         [SOLAR_YELLOW, SOLAR_WHITE], 6, 3, 20, 2)
                    bolt.kill()
                    if destroyed:
                        self.particles.burst(*ast.get_death_particles())
                        for p in alive_players:
                            pts = ast.points * p.score_mult
                            p.score += pts
                            self.floating_texts.append(
                                FloatingText(ast.rect.centerx, ast.rect.top - 10,
                                             f"+{pts}", SOLAR_YELLOW))
                        self.asteroids_cleared += 1
                        SFX["asteroid_destroy"].play()
                    else:
                        SFX["asteroid_hit"].play()
                    break

        # Spawn asteroids
        self.asteroid_timer += 1
        if self.asteroid_timer > 40:
            ax = random.randint(ROAD_LEFT + 20, ROAD_RIGHT - 20)
            ast = Asteroid(ax, -50, direction=DIR_DOWN)
            self.asteroids.add(ast)
            self.all_sprites.add(ast)
            self.asteroid_timer = 0

        # Update asteroids
        for ast in list(self.asteroids):
            ast.update(scroll_speed)

        # Asteroid-player collision
        for p in alive_players:
            if p.invincible_timer <= 0 and not p.ghost_mode and not p.phase:
                hit = pygame.sprite.spritecollideany(p, self.asteroids)
                if hit:
                    hit.kill()
                    p.take_hit(self.shake)
                    if not p.alive and not any(pl.alive for pl in self.players):
                        return 'gameover'

        # Check boss trigger
        if self.check_boss_trigger():
            self.start_boss_phase()
            self.boss = DesertBoss(self.particles, self.difficulty)
            self.boss_active = True
            self.all_sprites.add(self.boss)
            SFX["boss_warning"].play()

        return None

    def draw(self, screen):
        alive_players = self.get_alive_players()
        any_slowmo = any(p.slowmo for p in self.players if p.alive)
        max_speed = max((p.speed for p in alive_players), default=0)
        scroll_speed = max_speed * (0.5 if any_slowmo else 1.0)

        screen.fill(BLACK)
        self.bg.update_and_draw(scroll_speed, screen, any_slowmo)

        if self.screen_flash > 0:
            flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            # Neon-tinted flash instead of harsh white
            t = self.screen_flash / 20.0
            r = int(255 * t)
            g = int(200 * t + 55 * (1 - t))
            b = int(50 * t + 200 * (1 - t))
            flash_surf.fill((r, g, b, int(45 * t)))
            screen.blit(flash_surf, (0, 0))
            self.screen_flash -= 1

        self.particles.draw(screen)
        self.all_sprites.draw(screen)

        # Shield bubble
        for p in alive_players:
            if p.shield:
                shield_surf = pygame.Surface((54, 76), pygame.SRCALPHA)
                pulse = 0.65 + 0.35 * math.sin(self.tick * 0.08)
                pygame.draw.ellipse(shield_surf, (*SHIELD_BLUE, int(50 * pulse)), (0, 0, 54, 76), 2)
                screen.blit(shield_surf, (p.rect.centerx - 27, p.rect.centery - 38))
            if p.phase:
                ghost_surf = pygame.Surface((54, 76), pygame.SRCALPHA)
                ghost_surf.set_alpha(100)
                pygame.draw.ellipse(ghost_surf, (*PHASE_CYAN, 60), (0, 0, 54, 76))
                screen.blit(ghost_surf, (p.rect.centerx - 27, p.rect.centery - 38))
            if p.surge:
                for i in range(4):
                    y = random.randint(0, SCREEN_HEIGHT)
                    pygame.draw.line(screen, (*SURGE_PINK, 80), (0, y), (12, y + random.randint(-8, 8)), 2)
                    pygame.draw.line(screen, (*SURGE_PINK, 80), (SCREEN_WIDTH - 12, y), (SCREEN_WIDTH, y + random.randint(-8, 8)), 2)

        # Slowmo tint
        if any_slowmo:
            tint = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            tint.fill((0, 50, 30, 25))
            screen.blit(tint, (0, 0))

        draw_hud(screen, self.players, self.game_distance, self.flare_timer, self.two_player)

        for ft in self.floating_texts:
            ft.draw(screen)

        for p in alive_players:
            p.combo.draw(screen, p.rect.centerx, p.rect.top - 50)

        self.milestone.draw(screen)

        # Asteroid HUD
        self.draw_asteroid_hud(screen)

        # Boss draw
        if self.boss:
            self.boss.draw(screen)

    def cleanup(self):
        if _snd.engine_channel and _snd.engine_channel.get_busy():
            _snd.engine_channel.fadeout(200)
        if _snd.music_channel and _snd.music_channel.get_busy():
            _snd.music_channel.fadeout(300)
        super().cleanup()
