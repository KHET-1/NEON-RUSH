import pygame
import random
import math

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, NEON_CYAN, NEON_MAGENTA,
    SOLAR_YELLOW, SOLAR_WHITE, COIN_GOLD, SHIELD_BLUE,
    POWERUP_SHIELD, POWERUP_MAGNET, POWERUP_SLOWMO,
    POWERUP_NUKE, POWERUP_PHASE, POWERUP_SURGE,
    POWERUP_COLORS, NUKE_ORANGE, PHASE_CYAN, SURGE_PINK,
    DIFFICULTY_SETTINGS, DIFF_NORMAL, MODE_MICROMACHINES,
)
from core.sound import SFX, music_loops
import core.sound as _snd
from core.hud import FloatingText, draw_panel
from core.ui import MilestoneTracker
from shared.game_mode import GameMode
from shared.boss_base import HeatBolt
from sprites.micromachines_sprites import (
    MicroPlayer, OilSlickHazard, TrackBarrier, TinyCar,
    MicroCoin, MicroPowerUp,
)
from backgrounds.micromachines_bg import MicroMachinesBG
from bosses.micromachines_boss import MicroMachinesBoss
from ai.controller import AIController, BrainController


class MicroMachinesMode(GameMode):
    MODE_NAME = "MICRO MACHINES"
    MODE_INDEX = MODE_MICROMACHINES
    MUSIC_KEY = "micromachines"

    BOSS_DISTANCE_THRESHOLD = 2.0
    BOSS_SCORE_THRESHOLD = 12000
    BOSS_TIME_THRESHOLD = 120 * 60

    def __init__(self, particles, shake, shared_state):
        super().__init__(particles, shake, shared_state)
        self.bg = MicroMachinesBG()
        self.obstacles = pygame.sprite.Group()
        self.oil_slicks = pygame.sprite.Group()
        self.tiny_cars = pygame.sprite.Group()
        self.coins_group = pygame.sprite.Group()
        self.powerups_group = pygame.sprite.Group()
        self.heat_bolts = pygame.sprite.Group()

        self.ai_controllers = []

        self.obstacle_timer = 0
        self.oil_timer = 0
        self.car_timer = 0
        self.coin_timer = 0
        self.powerup_timer = 0
        self.difficulty_scale = 1.0
        self.floating_texts = []
        self.milestone = MilestoneTracker()
        self.scroll_speed = 3.0

    def setup(self):
        diff = self.shared_state.difficulty
        selected_diff = diff if diff in DIFFICULTY_SETTINGS else DIFF_NORMAL

        if self.two_player:
            p1 = MicroPlayer(self.particles, 1, diff=selected_diff)
            p1.px = SCREEN_WIDTH // 2 - 40
            p1.py = SCREEN_HEIGHT - 100
            p2 = MicroPlayer(self.particles, 2, diff=selected_diff)
            p2.px = SCREEN_WIDTH // 2 + 40
            p2.py = SCREEN_HEIGHT - 100
            self.players = [p1, p2]
        else:
            p1 = MicroPlayer(self.particles, 1, solo=True, diff=selected_diff)
            p1.px = SCREEN_WIDTH // 2
            p1.py = SCREEN_HEIGHT - 100
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
                    p.base_surf = p._make_car()
                    p.image = p.base_surf.copy()
                    p.name = brain.name[:10]
                    brain.start_episode(p)
                    self.ai_controllers.append(BrainController(brain, p, MODE_MICROMACHINES))
                else:
                    p.color_main = AIController.COLOR_MAIN
                    p.color_accent = AIController.COLOR_ACCENT
                    p.base_surf = p._make_car()
                    p.image = p.base_surf.copy()
                    p.name = f"AI{idx + 1}"
                    self.ai_controllers.append(AIController(p, MODE_MICROMACHINES))

        for p in self.players:
            self.all_sprites.add(p)

        if music_loops and not _snd.music_channel.get_busy():
            _snd.music_channel.play(music_loops.get("micromachines", music_loops.get("desert")), loops=-1)
            _snd.music_channel.set_volume(0.08)

    def handle_event(self, event):
        pass

    def update(self, keys):
        super().update(keys)

        alive_players = self.get_alive_players()
        if not alive_players:
            SFX["gameover"].play()
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

        # --- Boss logic ---
        if self.boss_active and self.boss:
            self.boss.update(alive_players, self.scroll_speed)

            for p in alive_players:
                fired, bx, by = p.try_fire_heat_bolt(keys)
                if fired:
                    bolt = HeatBolt(bx, by, p.color_accent)
                    bolt.speed = -8
                    self.heat_bolts.add(bolt)

            for bolt in list(self.heat_bolts):
                bolt.update()
                if self.boss and self.boss.alive and bolt.rect.colliderect(self.boss.rect):
                    self.boss.take_damage(bolt.damage, "heat_bolt")
                    self.particles.burst(bolt.rect.centerx, bolt.rect.centery,
                                         [SOLAR_YELLOW, SOLAR_WHITE], 6, 3, 20, 2)
                    bolt.kill()

            if self.boss and self.boss.alive and self.boss.vulnerable:
                for p in alive_players:
                    if p.rect.colliderect(self.boss.rect) and p.invincible_timer <= 0:
                        self.boss.take_damage(self.boss.RAM_DAMAGE, "ram")
                        p.invincible_timer = 30
                        self.shake.trigger(6, 15)

            if self.boss and self.boss.defeated and self.boss.death_timer <= 0:
                self.boss_active = False
                self.shared_state.snapshot_from_players(self.players)
                self.shared_state.advance_mode()
                for p in alive_players:
                    boss_pts = 5000 * p.score_mult
                    p.score += boss_pts
                    self.floating_texts.append(
                        FloatingText(p.rect.centerx, p.rect.top - 40, f"+{boss_pts} FINAL BOSS!", SOLAR_YELLOW, 28))
                return 'boss_defeated'
        else:
            if self.check_boss_trigger():
                self.boss = MicroMachinesBoss(self.particles, shake=self.shake)
                self.boss_active = True
                self.all_sprites.add(self.boss)
                SFX["boss_warning"].play()

        # --- Spawning ---
        spawn_mult = 0.3 if self.boss_active else 1.0

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
            oil = OilSlickHazard(x, -30)
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
        if self.powerup_timer > 400:
            x = random.randint(100, SCREEN_WIDTH - 100)
            pu = MicroPowerUp(x, -30)
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
            pu.update(self.scroll_speed)

        # Collisions
        for p in alive_players:
            if p.invincible_timer <= 0 and not p.ghost_mode and not p.phase:
                hit = pygame.sprite.spritecollideany(p, self.obstacles)
                if hit:
                    hit.kill()
                    p.take_hit(self.shake)
                    if not p.alive and not any(pl.alive for pl in self.players):
                        return 'gameover'

                car_hit = pygame.sprite.spritecollideany(p, self.tiny_cars)
                if car_hit:
                    car_hit.kill()
                    p.take_hit(self.shake)
                    if not p.alive and not any(pl.alive for pl in self.players):
                        return 'gameover'

            # Oil slick = spin + slow (phase skips oil too)
            oil_hit = pygame.sprite.spritecollideany(p, self.oil_slicks)
            if oil_hit and not p.ghost_mode and not p.phase:
                p.angle += random.uniform(-0.3, 0.3)
                p.speed *= 0.9

            # Coins
            collected = pygame.sprite.spritecollide(p, self.coins_group, True)
            for _ in collected:
                p.coins += 1
                p.combo.hit()
                pts = p.combo.get_bonus(50) * p.score_mult
                p.score += pts
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
                    for oil in list(self.oil_slicks):
                        self.particles.burst(oil.rect.centerx, oil.rect.centery,
                                              [NUKE_ORANGE, SOLAR_YELLOW], 6, 3, 20, 2)
                        p.score += 50 * p.score_mult
                        oil.kill()
                    for car in list(self.tiny_cars):
                        self.particles.burst(car.rect.centerx, car.rect.centery,
                                              [NUKE_ORANGE, SOLAR_YELLOW], 8, 4, 25, 2)
                        p.score += 50 * p.score_mult
                        car.kill()
                    self.shake.trigger(8, 20)
                    SFX["nuke"].play()
                elif pu.kind == POWERUP_PHASE:
                    p.phase = True
                    p.phase_timer = 360
                    SFX["phase"].play()
                elif pu.kind == POWERUP_SURGE:
                    p.surge = True
                    p.surge_timer = 180
                    p.speed = 8
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

    def draw(self, screen):
        screen.fill(BLACK)
        self.bg.draw(screen)

        self.particles.draw(screen)
        self.all_sprites.draw(screen)

        # Shield bubbles & powerup effects
        alive_players = self.get_alive_players()
        for p in alive_players:
            if p.shield:
                s = pygame.Surface((30, 30), pygame.SRCALPHA)
                pulse = 0.65 + 0.35 * math.sin(self.tick * 0.08)
                pygame.draw.circle(s, (*SHIELD_BLUE, int(50 * pulse)), (15, 15), 14, 2)
                screen.blit(s, (p.rect.centerx - 15, p.rect.centery - 15))
            if p.phase:
                ghost_surf = pygame.Surface((30, 30), pygame.SRCALPHA)
                ghost_surf.set_alpha(100)
                pygame.draw.circle(ghost_surf, (*PHASE_CYAN, 60), (15, 15), 14)
                screen.blit(ghost_surf, (p.rect.centerx - 15, p.rect.centery - 15))
            if p.surge:
                for i in range(4):
                    y = random.randint(0, SCREEN_HEIGHT)
                    pygame.draw.line(screen, (*SURGE_PINK, 80), (0, y), (12, y + random.randint(-8, 8)), 2)
                    pygame.draw.line(screen, (*SURGE_PINK, 80), (SCREEN_WIDTH - 12, y), (SCREEN_WIDTH, y + random.randint(-8, 8)), 2)

        self._draw_hud(screen)

        for ft in self.floating_texts:
            ft.draw(screen)

        self.milestone.draw(screen)

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

            spd = FONT_HUD_SM.render(f"{int(abs(player.speed) * 10)} km/h", True, SOLAR_WHITE)
            screen.blit(spd, (px + 10, 48))
            score_t = FONT_HUD_SM.render(f"Score: {player.score}  x{player.coins}", True, COIN_GOLD)
            screen.blit(score_t, (px + 10, 64))

        dist_t = FONT_HUD.render(f"{self.game_distance:.1f} km", True, SOLAR_WHITE)
        screen.blit(dist_t, (SCREEN_WIDTH // 2 - dist_t.get_width() // 2, 12))

    def cleanup(self):
        if _snd.music_channel and _snd.music_channel.get_busy():
            _snd.music_channel.fadeout(300)
        super().cleanup()
