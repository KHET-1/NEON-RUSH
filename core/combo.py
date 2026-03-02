"""Combo and milestone tracking — game logic extracted from ui.py."""
import pygame
import math

from core.constants import (
    SCREEN_WIDTH, SOLAR_YELLOW, DESERT_ORANGE, NEON_MAGENTA,
)
from core.fonts import load_font
from core.sound import play_sfx


class ComboTracker:
    def __init__(self):
        self.count = 0
        self.timer = 0
        self.multiplier = 1
        self.display_timer = 0

    def hit(self):
        self.count += 1
        self.timer = 90
        if self.count >= 10:
            self.multiplier = 4
        elif self.count >= 5:
            self.multiplier = 3
        elif self.count >= 3:
            self.multiplier = 2
        else:
            self.multiplier = 1
        if self.multiplier > 1:
            self.display_timer = 90

    def update(self):
        if self.timer > 0:
            self.timer -= 1
            if self.timer <= 0:
                self.count = 0
                self.multiplier = 1
        if self.display_timer > 0:
            self.display_timer -= 1

    def get_bonus(self, base_score):
        return base_score * self.multiplier

    def draw(self, surface, x, y):
        if self.display_timer > 0 and self.multiplier > 1:
            alpha = min(255, self.display_timer * 6)
            scale = 1.0 + 0.3 * math.sin(self.display_timer * 0.2)
            size = int(28 * scale)
            font = load_font("dejavusans", size, bold=True)
            colors = {2: SOLAR_YELLOW, 3: DESERT_ORANGE, 4: NEON_MAGENTA}
            color = colors.get(self.multiplier, SOLAR_YELLOW)
            txt = font.render(f"COMBO x{self.multiplier}!", True, color)
            txt.set_alpha(alpha)
            surface.blit(txt, (x - txt.get_width() // 2, y))


class MilestoneTracker:
    def __init__(self):
        self.last_km = 0
        self.display_text = ""
        self.display_timer = 0
        self.max_timer = 80
        self.display_color = SOLAR_YELLOW
        self._tracer_particles = []  # (x, y, vx, vy, color, life)

    def check(self, distance):
        km = int(distance)
        if km > self.last_km and km > 0:
            self.last_km = km
            if km % 5 == 0:
                self.display_text = f"{km} KM! INCREDIBLE!"
                self.display_color = NEON_MAGENTA
                self.max_timer = 100
                self.display_timer = 100
            else:
                self.display_text = f"{km} KM!"
                self.display_color = SOLAR_YELLOW
                self.max_timer = 70
                self.display_timer = 70
            # Spawn tracer burst
            import random
            cx = SCREEN_WIDTH // 2
            for _ in range(16):
                angle = random.uniform(0, 6.28)
                spd = random.uniform(2.0, 6.0)
                vx = math.cos(angle) * spd
                vy = math.sin(angle) * spd * 0.4 - 1.0
                life = random.randint(20, 45)
                c = self.display_color
                self._tracer_particles.append((cx, 48.0, vx, vy, c, life, life))
            play_sfx("select")

    def update(self):
        if self.display_timer > 0:
            self.display_timer -= 1
        alive = []
        for px, py, vx, vy, c, life, max_l in self._tracer_particles:
            life -= 1
            if life > 0:
                alive.append((px + vx, py + vy, vx * 0.96, vy * 0.96 + 0.05, c, life, max_l))
        self._tracer_particles = alive

    def draw(self, surface):
        for px, py, vx, vy, c, life, max_l in self._tracer_particles:
            t = life / max_l
            alpha = int(180 * t)
            sz = max(1, int(3 * t))
            if alpha > 0:
                ps = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
                pygame.draw.circle(ps, (*c[:3], alpha), (sz, sz), sz)
                surface.blit(ps, (int(px) - sz, int(py) - sz))
                tail_len = int(abs(vx) * 2 + abs(vy) * 2)
                if tail_len > 1:
                    tail_a = max(0, alpha // 3)
                    pygame.draw.line(surface, (*c[:3], tail_a),
                                     (int(px), int(py)),
                                     (int(px - vx * 2), int(py - vy * 2)), 1)

        if self.display_timer <= 0:
            return

        progress = self.display_timer / self.max_timer
        y = 40

        sweep_w = int(SCREEN_WIDTH * 0.6 * min(1.0, progress * 3))
        if sweep_w > 4:
            sweep_x = SCREEN_WIDTH // 2 - sweep_w // 2
            sweep_a = int(60 * progress)
            sweep_surf = pygame.Surface((sweep_w, 2), pygame.SRCALPHA)
            sweep_surf.fill((*self.display_color[:3], sweep_a))
            surface.blit(sweep_surf, (sweep_x, y + 28))

        scale = min(1.0, (1.0 - progress) * 4) if progress > 0.75 else 1.0
        size = int(28 * scale) if scale > 0.3 else 28
        size = max(16, size)
        font = load_font("dejavusans", size, bold=True)
        alpha = int(255 * min(1.0, progress * 4))

        shadow = font.render(self.display_text, True, (0, 0, 0))
        shadow.set_alpha(alpha // 2)
        sx = SCREEN_WIDTH // 2 - shadow.get_width() // 2
        surface.blit(shadow, (sx + 2, y + 2))

        txt = font.render(self.display_text, True, self.display_color)
        txt.set_alpha(alpha)
        surface.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2, y))
