import pygame
import random
import math

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, NEON_CYAN, NEON_MAGENTA,
    SAND_YELLOW, WHITE, ROAD_LEFT, ROAD_RIGHT, ROAD_WIDTH,
    ROAD_CENTER, ROAD_COLOR, ROAD_EDGE_COLOR, ROAD_SHOULDER,
    DESERT_BG, DASH_LENGTH, DASH_GAP,
)

# V2 deep-sky color (replaces flat DESERT_BG for star visibility)
_V2_SKY = (15, 8, 25)
_V2_MESA_COLOR = (80, 35, 20)
_V2_DUNE_COLOR = (160, 85, 25)
_V2_DUNE_RIDGE = (190, 110, 40)
_V2_RUMBLE_DARK = (50, 45, 40)
_V2_RUMBLE_LIGHT = (90, 80, 65)
_V2_HORIZON_GLOW = (200, 100, 20)


class Background:
    def __init__(self, particles, tier=1):
        self.scroll_y = 0.0
        self.particles = particles
        self.sand_timer = 0
        self.tier = tier
        self._tick = 0

        # V2+ layers — 5 layer parallax
        if tier >= 2:
            self._stars = self._gen_stars()
            self._mesas = self._gen_mesas()
            self._dune_phase = 0.0
            self._drift_particles = []  # sand drift near road edges

    def _gen_stars(self):
        """50 stars with position, size, base brightness, and phase offset."""
        rng = random.Random(77)
        stars = []
        for _ in range(50):
            stars.append({
                'x': rng.randint(0, SCREEN_WIDTH),
                'y': rng.randint(5, int(SCREEN_HEIGHT * 0.28)),
                'sz': rng.choice([1, 1, 1, 2]),
                'bright': rng.randint(140, 255),
                'phase': rng.uniform(0, math.pi * 2),
                'cyan': rng.random() < 0.2,  # 20% are cyan-tinted
            })
        return stars

    def _gen_mesas(self):
        """4-5 flat-topped mesa trapezoidal silhouettes that tile horizontally."""
        rng = random.Random(33)
        mesas = []
        x = -100
        tile_w = SCREEN_WIDTH * 2  # tile width for seamless scroll
        while x < tile_w + 200:
            w = rng.randint(90, 180)
            h = rng.randint(50, 100)
            flat_top = rng.randint(int(w * 0.3), int(w * 0.7))
            mesas.append((x, h, w, flat_top))
            x += w + rng.randint(40, 100)
        return mesas

    # --- Layer 0: Star Field (parallax 0.05x) ---
    def _draw_stars(self, screen):
        star_scroll = self.scroll_y * 0.05
        for s in self._stars:
            dy = int((s['y'] + star_scroll * 0.3) % (SCREEN_HEIGHT * 0.3))
            # Pulsing alpha via sine
            pulse = math.sin(self._tick * 0.03 + s['phase'])
            bright = max(60, min(255, int(s['bright'] + 40 * pulse)))
            if s['cyan']:
                color = (bright // 2, bright, bright)
            else:
                color = (bright, bright, max(0, bright - 30))
            pygame.draw.circle(screen, color, (s['x'], dy), s['sz'])

    # --- Layer 1: Distant Mesas (parallax 0.15x) ---
    def _draw_mesas(self, screen):
        mesa_base_y = int(SCREEN_HEIGHT * 0.32)
        tile_w = SCREEN_WIDTH * 2
        mesa_scroll = int(self.scroll_y * 0.15) % tile_w

        # Orange horizon glow line
        glow_y = mesa_base_y + 2
        glow_alpha = int(60 + 30 * math.sin(self._tick * 0.02))
        glow_surf = pygame.Surface((SCREEN_WIDTH, 3), pygame.SRCALPHA)
        glow_surf.fill((*_V2_HORIZON_GLOW, glow_alpha))
        screen.blit(glow_surf, (0, glow_y))

        for mx, mh, mw, flat in self._mesas:
            sx = (mx - mesa_scroll) % tile_w - 200
            if sx + mw < -50 or sx > SCREEN_WIDTH + 50:
                continue
            inset = (mw - flat) // 3
            points = [
                (sx, mesa_base_y),
                (sx + inset, mesa_base_y - mh),
                (sx + inset + flat, mesa_base_y - mh),
                (sx + mw, mesa_base_y),
            ]
            pygame.draw.polygon(screen, _V2_MESA_COLOR, points)
            # Subtle highlight on flat top
            pygame.draw.line(screen, (100, 50, 30),
                             (sx + inset, mesa_base_y - mh),
                             (sx + inset + flat, mesa_base_y - mh), 1)

    # --- Layer 2: Mid Dunes (parallax 0.35x) ---
    def _draw_dunes(self, screen):
        self._dune_phase += 0.002
        dune_scroll = self.scroll_y * 0.35

        # Draw dune profiles on both sides of road
        for side in ('left', 'right'):
            if side == 'left':
                x_start, x_end = 0, ROAD_LEFT - 20
            else:
                x_start, x_end = ROAD_RIGHT + 20, SCREEN_WIDTH

            if x_end <= x_start:
                continue

            for y in range(int(SCREEN_HEIGHT * 0.32), SCREEN_HEIGHT, 2):
                wave = 18 * math.sin(y * 0.015 + dune_scroll * 0.008 + self._dune_phase)
                wave += 10 * math.sin(y * 0.03 + dune_scroll * 0.012 + 1.5)

                if side == 'left':
                    dx = int(x_end + wave)
                    dx = min(dx, x_end + 30)
                    draw_x = max(x_start, dx - 50)
                    pygame.draw.line(screen, _V2_DUNE_COLOR, (draw_x, y), (dx, y))
                    # Ridge highlight
                    pygame.draw.line(screen, _V2_DUNE_RIDGE, (dx - 2, y), (dx, y), 1)
                else:
                    dx = int(x_start + wave)
                    dx = max(dx, x_start - 30)
                    draw_end = min(x_end, dx + 50)
                    pygame.draw.line(screen, _V2_DUNE_COLOR, (dx, y), (draw_end, y))
                    pygame.draw.line(screen, _V2_DUNE_RIDGE, (dx, y), (dx + 2, y), 1)

    # --- Layer 3: Road Shoulders with rumble strips (parallax 0.7x) ---
    def _draw_v2_shoulders(self, screen):
        rumble_period = 12  # alternating 6px dark / 6px light
        offset = int(self.scroll_y * 0.7) % rumble_period

        for y in range(0, SCREEN_HEIGHT, 2):
            block = ((y - offset) // 6) % 2
            color = _V2_RUMBLE_DARK if block == 0 else _V2_RUMBLE_LIGHT
            # Left shoulder rumble strip
            pygame.draw.line(screen, color, (ROAD_LEFT - 22, y), (ROAD_LEFT - 10, y), 2)
            # Right shoulder rumble strip
            pygame.draw.line(screen, color, (ROAD_RIGHT + 10, y), (ROAD_RIGHT + 22, y), 2)

        # Sand drift particles near road edges
        if self._tick % 4 == 0:
            for _ in range(2):
                side = random.choice([ROAD_LEFT - 15, ROAD_RIGHT + 15])
                self._drift_particles.append({
                    'x': float(side + random.randint(-8, 8)),
                    'y': float(random.randint(0, SCREEN_HEIGHT)),
                    'vx': random.uniform(-0.5, 0.5),
                    'vy': random.uniform(0.3, 1.0),
                    'life': random.randint(30, 60),
                })

        alive = []
        for dp in self._drift_particles:
            dp['x'] += dp['vx']
            dp['y'] += dp['vy']
            dp['life'] -= 1
            if dp['life'] > 0 and 0 <= dp['y'] < SCREEN_HEIGHT:
                alpha = min(120, dp['life'] * 4)
                s = pygame.Surface((3, 3), pygame.SRCALPHA)
                s.fill((180, 150, 100, alpha))
                screen.blit(s, (int(dp['x']), int(dp['y'])))
                alive.append(dp)
        self._drift_particles = alive

    def _draw_v2(self, speed, screen):
        """Full V2+ 5-layer parallax render."""
        # Deep night sky instead of flat desert
        screen.fill(_V2_SKY)

        # Layer 0: Star Field
        self._draw_stars(screen)

        # Layer 1: Distant Mesas
        self._draw_mesas(screen)

        # Layer 2: Mid Dunes
        self._draw_dunes(screen)

        # Layer 3: Road Shoulders with rumble strips
        self._draw_v2_shoulders(screen)

    def update_and_draw(self, speed, screen, slowmo=False):
        actual_speed = speed * (0.5 if slowmo else 1.0)
        self.scroll_y += actual_speed
        self._tick += 1
        dash_period = DASH_LENGTH + DASH_GAP

        if self.tier >= 2:
            # V2+: full parallax pipeline, then road on top
            self._draw_v2(actual_speed, screen)
        else:
            # V1: flat desert fill
            screen.fill(DESERT_BG)

        # --- Layer 4 (V1+V2): Road surface + markers ---
        pygame.draw.rect(screen, ROAD_SHOULDER, (ROAD_LEFT - 24, 0, ROAD_WIDTH + 48, SCREEN_HEIGHT))
        pygame.draw.rect(screen, ROAD_COLOR, (ROAD_LEFT, 0, ROAD_WIDTH, SCREEN_HEIGHT))
        pygame.draw.line(screen, (20, 120, 150), (ROAD_LEFT, 0), (ROAD_LEFT, SCREEN_HEIGHT), 4)
        pygame.draw.line(screen, ROAD_EDGE_COLOR, (ROAD_LEFT, 0), (ROAD_LEFT, SCREEN_HEIGHT), 2)
        pygame.draw.line(screen, (20, 120, 150), (ROAD_RIGHT, 0), (ROAD_RIGHT, SCREEN_HEIGHT), 4)
        pygame.draw.line(screen, ROAD_EDGE_COLOR, (ROAD_RIGHT, 0), (ROAD_RIGHT, SCREEN_HEIGHT), 2)

        # Center line
        offset = int(self.scroll_y) % dash_period
        y = -DASH_LENGTH + offset
        while y < SCREEN_HEIGHT + DASH_LENGTH:
            pygame.draw.line(screen, NEON_MAGENTA, (ROAD_CENTER, y), (ROAD_CENTER, y + DASH_LENGTH), 2)
            y += dash_period

        # Lane lines
        for lane_x in [ROAD_LEFT + ROAD_WIDTH // 4, ROAD_LEFT + 3 * ROAD_WIDTH // 4]:
            y = -DASH_LENGTH + offset
            while y < SCREEN_HEIGHT + DASH_LENGTH:
                pygame.draw.line(screen, (65, 65, 88), (lane_x, y), (lane_x, y + DASH_LENGTH // 2), 1)
                y += dash_period

        # Speed streaks
        if speed > 8:
            intensity = min(30, int((speed - 8) * 12))
            line_surf = pygame.Surface((2, int(speed * 4)), pygame.SRCALPHA)
            line_surf.fill((*WHITE, min(60, intensity * 3)))
            for _ in range(intensity):
                lx = random.randint(0, SCREEN_WIDTH)
                ly = random.randint(0, SCREEN_HEIGHT)
                screen.blit(line_surf, (lx, ly))

        # Sand particles
        self.sand_timer += 1
        if self.sand_timer > 6:
            for _ in range(2):
                x = random.randint(0, SCREEN_WIDTH)
                self.particles.emit(
                    x, random.randint(0, SCREEN_HEIGHT), SAND_YELLOW,
                    [random.uniform(1, 2), random.uniform(0.5, 1.5)], 80, 1,
                )
            self.sand_timer = 0
