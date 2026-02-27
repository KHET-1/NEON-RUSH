import pygame
import random
import math

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, NEON_CYAN, NEON_MAGENTA,
    SAND_YELLOW, WHITE, ROAD_LEFT, ROAD_RIGHT, ROAD_WIDTH,
    ROAD_CENTER, ROAD_COLOR, ROAD_EDGE_COLOR, ROAD_SHOULDER,
    DESERT_BG, DASH_LENGTH, DASH_GAP,
)


class Background:
    def __init__(self, particles, tier=1):
        self.scroll_y = 0.0
        self.particles = particles
        self.sand_timer = 0
        self.tier = tier

        # V2+ layers
        if tier >= 2:
            self._stars = self._gen_stars()
            self._mesas = self._gen_mesas()
            self._dune_phase = 0.0

    def _gen_stars(self):
        """Random star field for V2+ night sky."""
        rng = random.Random(77)
        stars = []
        for _ in range(30):
            stars.append((
                rng.randint(0, SCREEN_WIDTH),
                rng.randint(5, 120),
                rng.randint(1, 2),
                rng.randint(160, 255),
            ))
        return stars

    def _gen_mesas(self):
        """Mesa silhouettes for V2+ desert horizon."""
        rng = random.Random(33)
        mesas = []
        x = -50
        while x < SCREEN_WIDTH + 200:
            w = rng.randint(80, 160)
            h = rng.randint(40, 90)
            flat_top = rng.randint(30, w - 20)
            mesas.append((x, h, w, flat_top))
            x += w + rng.randint(30, 80)
        return mesas

    def _draw_v2_layers(self, screen, speed):
        """Draw V2+ background layers before road."""
        # Stars — tiny dots, very slow parallax
        star_offset = int(self.scroll_y * 0.02) % 200
        for sx, sy, sz, brightness in self._stars:
            dy = (sy + star_offset) % 140
            twinkle = brightness + int(20 * math.sin(self.scroll_y * 0.01 + sx))
            twinkle = max(100, min(255, twinkle))
            pygame.draw.circle(screen, (twinkle, twinkle, twinkle - 30), (sx, dy), sz)

        # Mesa silhouettes — dark shapes at horizon (0.1x parallax)
        mesa_scroll = int(self.scroll_y * 0.05) % 300
        mesa_base_y = 130
        mesa_color = (40, 25, 50)
        for mx, mh, mw, flat in self._mesas:
            sx = mx - mesa_scroll
            if sx + mw < -50 or sx > SCREEN_WIDTH + 50:
                continue
            points = [
                (sx, mesa_base_y),
                (sx + (mw - flat) // 3, mesa_base_y - mh),
                (sx + (mw - flat) // 3 + flat, mesa_base_y - mh),
                (sx + mw, mesa_base_y),
            ]
            pygame.draw.polygon(screen, mesa_color, points)

        # Dune parallax — sine-wave sand dunes at road edges (0.6x)
        self._dune_phase += speed * 0.003
        dune_color = (120, 90, 50)
        for side_x in [ROAD_LEFT - 60, ROAD_RIGHT + 10]:
            for y in range(140, SCREEN_HEIGHT, 3):
                wave = int(15 * math.sin(y * 0.02 + self._dune_phase))
                dx = side_x + wave
                pygame.draw.line(screen, dune_color, (dx, y), (dx + 40, y), 2)

    def update_and_draw(self, speed, screen, slowmo=False):
        actual_speed = speed * (0.5 if slowmo else 1.0)
        self.scroll_y += actual_speed
        dash_period = DASH_LENGTH + DASH_GAP

        screen.fill(DESERT_BG)

        # V2+ layers drawn before road
        if self.tier >= 2:
            self._draw_v2_layers(screen, actual_speed)

        pygame.draw.rect(screen, ROAD_SHOULDER, (ROAD_LEFT - 24, 0, ROAD_WIDTH + 48, SCREEN_HEIGHT))
        pygame.draw.rect(screen, ROAD_COLOR, (ROAD_LEFT, 0, ROAD_WIDTH, SCREEN_HEIGHT))
        pygame.draw.line(screen, (20, 120, 150), (ROAD_LEFT, 0), (ROAD_LEFT, SCREEN_HEIGHT), 4)
        pygame.draw.line(screen, ROAD_EDGE_COLOR, (ROAD_LEFT, 0), (ROAD_LEFT, SCREEN_HEIGHT), 2)
        pygame.draw.line(screen, (20, 120, 150), (ROAD_RIGHT, 0), (ROAD_RIGHT, SCREEN_HEIGHT), 4)
        pygame.draw.line(screen, ROAD_EDGE_COLOR, (ROAD_RIGHT, 0), (ROAD_RIGHT, SCREEN_HEIGHT), 2)

        offset = int(self.scroll_y) % dash_period
        y = -DASH_LENGTH + offset
        while y < SCREEN_HEIGHT + DASH_LENGTH:
            pygame.draw.line(screen, NEON_MAGENTA, (ROAD_CENTER, y), (ROAD_CENTER, y + DASH_LENGTH), 2)
            y += dash_period

        for lane_x in [ROAD_LEFT + ROAD_WIDTH // 4, ROAD_LEFT + 3 * ROAD_WIDTH // 4]:
            y = -DASH_LENGTH + offset
            while y < SCREEN_HEIGHT + DASH_LENGTH:
                pygame.draw.line(screen, (65, 65, 88), (lane_x, y), (lane_x, y + DASH_LENGTH // 2), 1)
                y += dash_period

        if speed > 8:
            intensity = min(30, int((speed - 8) * 12))
            line_surf = pygame.Surface((2, int(speed * 4)), pygame.SRCALPHA)
            line_surf.fill((*WHITE, min(60, intensity * 3)))
            for _ in range(intensity):
                lx = random.randint(0, SCREEN_WIDTH)
                ly = random.randint(0, SCREEN_HEIGHT)
                screen.blit(line_surf, (lx, ly))

        self.sand_timer += 1
        if self.sand_timer > 6:
            for _ in range(2):
                x = random.randint(0, SCREEN_WIDTH)
                self.particles.emit(
                    x, random.randint(0, SCREEN_HEIGHT), SAND_YELLOW,
                    [random.uniform(1, 2), random.uniform(0.5, 1.5)], 80, 1,
                )
            self.sand_timer = 0
