import pygame
import random
import math

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, NEON_CYAN, NEON_MAGENTA,
    SOLAR_YELLOW, SOLAR_WHITE, COIN_GOLD, SHIELD_BLUE,
    POWERUP_SHIELD, POWERUP_MAGNET, POWERUP_SLOWMO,
    POWERUP_NUKE, POWERUP_PHASE, POWERUP_SURGE,
    POWERUP_COLORS, NUKE_ORANGE, PHASE_CYAN, SURGE_PINK,
    DIFFICULTY_SETTINGS, DIFF_NORMAL, MODE_EXCITEBIKE,
)
from core.sound import SFX, music_loops
import core.sound as _snd
from core.hud import FloatingText, draw_panel
from core.ui import MilestoneTracker
from core.fonts import load_font
from shared.game_mode import GameMode
from shared.boss_base import HeatBolt
from sprites.excitebike_sprites import (
    ExcitebikePlayer, Ramp, Barrier, MudPatch, SideRacer,
    ExcitebikeCoin, ExcitebikePowerUp,
)
from backgrounds.excitebike_bg import ExcitebikeBg
from sprites.asteroid import Asteroid, DIR_LEFT
from bosses.excitebike_boss import ExcitebikeBoss
from ai.controller import AIController, BrainController


class ExcitebikeMode(GameMode):
    MODE_NAME = "EXCITEBIKE"
    MODE_INDEX = MODE_EXCITEBIKE
    MUSIC_KEY = "excitebike"

    BOSS_DISTANCE_THRESHOLD = 3.0
    BOSS_SCORE_THRESHOLD = 8000
    BOSS_TIME_THRESHOLD = 120 * 60  # 2 min

    def __init__(self, particles, shake, shared_state):
        super().__init__(particles, shake, shared_state)
        self.bg = ExcitebikeBg()
        self.barriers = pygame.sprite.Group()
        self.ramps = pygame.sprite.Group()
        self.mud_patches = pygame.sprite.Group()
        self.racers = pygame.sprite.Group()
        self.coins_group = pygame.sprite.Group()
        self.powerups_group = pygame.sprite.Group()
        self.heat_bolts = pygame.sprite.Group()

        self.ai_controllers = []

        self.obstacle_timer = 0
        self.coin_timer = 0
        self.powerup_timer = 0
        self.racer_timer = 0
        self.ramp_timer = 0
        self.difficulty_scale = 1.0
        self.floating_texts = []
        self.milestone = MilestoneTracker()
        self.screen_flash = 0

    def setup(self):
        diff = self.shared_state.difficulty
        selected_diff = diff if diff in DIFFICULTY_SETTINGS else DIFF_NORMAL

        if self.two_player:
            p1 = ExcitebikePlayer(self.particles, 1, lane=0, diff=selected_diff)
            p2 = ExcitebikePlayer(self.particles, 2, lane=2, diff=selected_diff)
            self.players = [p1, p2]
        else:
            p1 = ExcitebikePlayer(self.particles, 1, lane=1, solo=True, diff=selected_diff)
            self.players = [p1]

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
                brain = brain_map.get(idx)
                if use_brains and brain is not None:
                    p.color_main = BrainController.COLOR_MAIN
                    p.color_accent = BrainController.COLOR_ACCENT
                    p.image = p._make_bike()
                    p.name = brain.name[:10]
                    brain.start_episode(p)
                    self.ai_controllers.append(BrainController(brain, p, MODE_EXCITEBIKE))
                else:
                    p.color_main = AIController.COLOR_MAIN
                    p.color_accent = AIController.COLOR_ACCENT
                    p.image = p._make_bike()
                    p.name = f"AI{idx + 1}"
                    self.ai_controllers.append(AIController(p, MODE_EXCITEBIKE))

        for p in self.players:
            self.all_sprites.add(p)

        if music_loops and not _snd.music_channel.get_busy():
            _snd.music_channel.play(music_loops.get("excitebike", music_loops.get("desert")), loops=-1)
            _snd.music_channel.set_volume(0.08)

    def handle_event(self, event):
        pass  # Lane switching handled in update via held keys

    def update(self, keys):
        super().update(keys)

        alive_players = self.get_alive_players()
        if not alive_players:
            SFX["gameover"].play()
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

        # --- Boss logic ---
        if self.boss_active and self.boss:
            self.boss.update(alive_players, scroll_speed)

            # Heat bolt firing
            for p in alive_players:
                fired, bx, by = p.try_fire_heat_bolt(keys)
                if fired:
                    bolt = HeatBolt(bx, by, p.color_accent)
                    # Side-scroller: bolts go RIGHT
                    bolt.speed = 10
                    bolt.rect.centery = by
                    self.heat_bolts.add(bolt)

            for bolt in list(self.heat_bolts):
                bolt.rect.x += 10  # Move right
                if bolt.rect.left > SCREEN_WIDTH + 20:
                    bolt.kill()
                    continue
                if self.boss and self.boss.alive and bolt.rect.colliderect(self.boss.rect):
                    self.boss.take_damage(bolt.damage, "heat_bolt")
                    self.particles.burst(bolt.rect.centerx, bolt.rect.centery,
                                         [SOLAR_YELLOW, SOLAR_WHITE], 6, 3, 20, 2)
                    bolt.kill()

            # Ram during vulnerability
            if self.boss and self.boss.alive and self.boss.vulnerable:
                for p in alive_players:
                    if p.rect.colliderect(self.boss.rect) and p.invincible_timer <= 0:
                        self.boss.take_damage(self.boss.RAM_DAMAGE, "ram")
                        p.invincible_timer = 30
                        self.shake.trigger(6, 15)

            # Boss attack hazards
            if self.boss and self.boss.alive:
                hazards = self.boss.get_attack_hazards()
                for p in alive_players:
                    if p.invincible_timer > 0 or p.ghost_mode:
                        continue
                    for htype, hdata in hazards:
                        if htype == 'rect' and isinstance(hdata, pygame.Rect):
                            if p.rect.colliderect(hdata):
                                p.take_hit(self.shake)
                                if not p.alive and not any(pl.alive for pl in self.players):
                                    return 'gameover'
                                break

            # Ramp environmental damage to boss
            if self.boss and self.boss.alive:
                for ramp in list(self.ramps):
                    if ramp.rect.colliderect(self.boss.rect):
                        self.boss.take_damage(self.boss.ENVIRONMENTAL_DAMAGE, "environmental")
                        self.particles.burst(ramp.rect.centerx, ramp.rect.centery,
                                             [SOLAR_YELLOW, SOLAR_WHITE], 15, 5, 30, 3)
                        ramp.kill()

            if self.boss and self.boss.defeated and self.boss.death_timer <= 0:
                self.boss_active = False
                self.shared_state.snapshot_from_players(self.players)
                self.shared_state.advance_mode()
                for p in alive_players:
                    boss_pts = 3000 * p.score_mult
                    p.score += boss_pts
                    self.floating_texts.append(
                        FloatingText(p.rect.centerx, p.rect.top - 40, f"+{boss_pts} BOSS!", SOLAR_YELLOW, 28))
                return 'boss_defeated'
        elif self.phase == 'asteroids':
            result = self._update_asteroid_phase(keys, alive_players, scroll_speed, diff_s)
            if result:
                return result
        else:
            if self.check_asteroid_trigger():
                self.start_asteroid_phase()
                SFX["asteroid_warning"].play()

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
                b = Barrier(SCREEN_WIDTH + 50, lane_y)
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
        if self.powerup_timer > 500:
            lane = random.randint(0, 2)
            pu = ExcitebikePowerUp(SCREEN_WIDTH + 40, self.bg.get_lane_y(lane))
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
            pu.update(scroll_speed)

        # Collisions
        for p in alive_players:
            if p.invincible_timer <= 0 and not p.ghost_mode and not p.phase:
                hit = pygame.sprite.spritecollideany(p, self.barriers)
                if hit:
                    hit.kill()
                    p.take_hit(self.shake)
                    if not p.alive and not any(pl.alive for pl in self.players):
                        return 'gameover'

                # Racer collision
                hit_racer = pygame.sprite.spritecollideany(p, self.racers)
                if hit_racer:
                    hit_racer.kill()
                    p.take_hit(self.shake)
                    if not p.alive and not any(pl.alive for pl in self.players):
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
                SFX["boost"].play()

            # Coins
            collected = pygame.sprite.spritecollide(p, self.coins_group, True)
            for _ in collected:
                p.coins += 1
                p.combo.hit()
                pts = p.combo.get_bonus(50) * p.score_mult
                p.score += pts
                self.particles.burst(p.rect.centerx, p.rect.centery - 5,
                                      [COIN_GOLD, SOLAR_YELLOW], 5, 3, 15, 2)
                self.floating_texts.append(
                    FloatingText(p.rect.centerx, p.rect.top - 15, f"+{pts}", COIN_GOLD))
                SFX["coin"].play()

            # Powerups
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
                    for obs in list(self.barriers):
                        self.particles.burst(obs.rect.centerx, obs.rect.centery,
                                              [NUKE_ORANGE, SOLAR_YELLOW], 8, 4, 25, 2)
                        p.score += 50 * p.score_mult
                        obs.kill()
                    for mud in list(self.mud_patches):
                        self.particles.burst(mud.rect.centerx, mud.rect.centery,
                                              [NUKE_ORANGE, SOLAR_YELLOW], 6, 3, 20, 2)
                        p.score += 50 * p.score_mult
                        mud.kill()
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
                                      [POWERUP_COLORS[pu.kind]], 6, 3, 20, 3)
                self.floating_texts.append(
                    FloatingText(p.rect.centerx, p.rect.top - 15, f"+{pts_pu}", POWERUP_COLORS[pu.kind]))
                if pu.kind not in (POWERUP_NUKE, POWERUP_PHASE, POWERUP_SURGE):
                    SFX["powerup"].play()

        self.particles.update()
        self.shake.update()
        return None

    def _update_asteroid_phase(self, keys, alive_players, scroll_speed, diff_s):
        """Handle asteroid phase: horizontal asteroids from right."""
        # Fire heat bolts (go RIGHT)
        for p in alive_players:
            fired, bx, by = p.try_fire_heat_bolt(keys)
            if fired:
                bolt = HeatBolt(bx, by, p.color_accent)
                bolt.speed = 10
                bolt.rect.centery = by
                self.heat_bolts.add(bolt)

        # Update heat bolts — check asteroid collisions
        for bolt in list(self.heat_bolts):
            bolt.rect.x += 10
            if bolt.rect.left > SCREEN_WIDTH + 20:
                bolt.kill()
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

        # Spawn asteroids from right side, in random lanes
        self.asteroid_timer += 1
        if self.asteroid_timer > 45:
            lane = random.randint(0, 2)
            lane_y = self.bg.get_lane_y(lane) + self.bg.LANE_HEIGHT // 2
            ast = Asteroid(SCREEN_WIDTH + 50, lane_y, direction=DIR_LEFT)
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
            self.boss = ExcitebikeBoss(self.particles, shake=self.shake)
            self.boss_active = True
            self.all_sprites.add(self.boss)
            SFX["boss_warning"].play()

        return None

    def draw(self, screen):
        screen.fill(BLACK)
        alive_players = self.get_alive_players()
        max_speed = max((p.speed for p in alive_players), default=3)
        self.bg.update_and_draw(max_speed, screen)

        if self.screen_flash > 0:
            flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            flash_surf.fill((*SOLAR_WHITE, int(60 * (self.screen_flash / 30))))
            screen.blit(flash_surf, (0, 0))
            self.screen_flash -= 1

        self.particles.draw(screen)
        self.all_sprites.draw(screen)

        # Shield bubble
        for p in alive_players:
            if p.shield:
                shield_surf = pygame.Surface((50, 30), pygame.SRCALPHA)
                pulse = 0.65 + 0.35 * math.sin(self.tick * 0.08)
                pygame.draw.ellipse(shield_surf, (*SHIELD_BLUE, int(50 * pulse)), (0, 0, 50, 30), 2)
                screen.blit(shield_surf, (p.rect.centerx - 25, p.rect.centery - 15))
            if p.phase:
                ghost_surf = pygame.Surface((50, 30), pygame.SRCALPHA)
                ghost_surf.set_alpha(100)
                pygame.draw.ellipse(ghost_surf, (*PHASE_CYAN, 60), (0, 0, 50, 30))
                screen.blit(ghost_surf, (p.rect.centerx - 25, p.rect.centery - 15))
            if p.surge:
                for i in range(4):
                    y = random.randint(0, SCREEN_HEIGHT)
                    pygame.draw.line(screen, (*SURGE_PINK, 80), (0, y), (12, y + random.randint(-8, 8)), 2)
                    pygame.draw.line(screen, (*SURGE_PINK, 80), (SCREEN_WIDTH - 12, y), (SCREEN_WIDTH, y + random.randint(-8, 8)), 2)

        # HUD
        self._draw_hud(screen)

        for ft in self.floating_texts:
            ft.draw(screen)

        for p in alive_players:
            p.combo.draw(screen, p.rect.centerx, p.rect.top - 40)

        self.milestone.draw(screen)

        # Asteroid HUD
        self.draw_asteroid_hud(screen)

        if self.boss:
            self.boss.draw(screen)

    def _draw_hud(self, screen):
        from core.fonts import FONT_HUD, FONT_HUD_SM
        from core.hud import draw_lives_icons

        for idx, player in enumerate(self.players):
            if not player.alive and self.two_player:
                continue
            px = 8 if idx == 0 else SCREEN_WIDTH - 200
            if not self.two_player:
                px = 8
            draw_panel(screen, pygame.Rect(px, 8, 190, 80), (0, 0, 0, 180), player.color_accent)

            label = FONT_HUD_SM.render(player.name, True, player.color_accent)
            screen.blit(label, (px + 8, 12))
            draw_lives_icons(screen, player, px + 55, 14)

            heat_pct = min(100, int(player.heat))
            bar_w = 170
            pygame.draw.rect(screen, (32, 32, 42), (px + 10, 34, bar_w, 10))
            fill_w = int(bar_w * heat_pct / 100)
            if fill_w > 0:
                bar_col = NEON_MAGENTA if heat_pct > 80 else player.color_accent
                pygame.draw.rect(screen, bar_col, (px + 10, 34, fill_w, 10))

            spd = FONT_HUD_SM.render(f"{int(player.speed * 10)} km/h", True, SOLAR_WHITE)
            screen.blit(spd, (px + 10, 48))
            score_t = FONT_HUD_SM.render(f"Score: {player.score}  x{player.coins}", True, COIN_GOLD)
            screen.blit(score_t, (px + 10, 64))

        dist_t = FONT_HUD.render(f"{self.game_distance:.1f} km", True, SOLAR_WHITE)
        screen.blit(dist_t, (SCREEN_WIDTH // 2 - dist_t.get_width() // 2, 12))

    def cleanup(self):
        if _snd.engine_channel and _snd.engine_channel.get_busy():
            _snd.engine_channel.fadeout(200)
        if _snd.music_channel and _snd.music_channel.get_busy():
            _snd.music_channel.fadeout(300)
        super().cleanup()
