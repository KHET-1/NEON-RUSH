import pygame
import random
import math

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, NEON_CYAN, NEON_MAGENTA,
    SAND_YELLOW, WHITE, ROAD_LEFT, ROAD_RIGHT, ROAD_WIDTH,
    ROAD_CENTER, ROAD_COLOR, ROAD_EDGE_COLOR, ROAD_SHOULDER,
    DESERT_BG, DASH_LENGTH, DASH_GAP,
)

# V2 palette
_V2_SKY = (15, 8, 25)
_V2_MESA_COLOR = (80, 35, 20)
_V2_HORIZON_GLOW = (200, 100, 20)

# Ground strip colors — alternating pairs that scroll at perspective speed
# Far (horizon) = dark/muted, Near (bottom) = warm/saturated
_STRIP_A = [
    (35, 22, 30),   # far — dark purple-brown
    (55, 35, 25),   # mid-far — dusty brown
    (80, 52, 28),   # mid — warm sand
    (100, 65, 32),  # mid-near — bright sand
    (115, 75, 35),  # near — golden sand
]
_STRIP_B = [
    (28, 18, 24),   # far — darker
    (45, 28, 20),   # mid-far
    (65, 42, 22),   # mid
    (85, 55, 26),   # mid-near
    (100, 65, 30),  # near
]

# Rumble strips
_RUMBLE_A = (200, 50, 50)
_RUMBLE_B = (220, 220, 220)

# Horizon Y — where ground starts
_HORIZON_Y = int(SCREEN_HEIGHT * 0.30)
_GROUND_ROWS = SCREEN_HEIGHT - _HORIZON_Y
_BAND_HEIGHT = 18  # pixel height of each color band before perspective


class Background:
    def __init__(self, particles, tier=1):
        self.scroll_y = 0.0
        self.particles = particles
        self.sand_timer = 0
        self.tier = tier
        self._tick = 0

        if tier >= 2:
            self._stars = self._gen_stars()
            self._mesas = self._gen_mesas()
            # Pre-compute per-scanline parallax speeds (quadratic perspective)
            self._line_speeds = []
            for y in range(_HORIZON_Y, SCREEN_HEIGHT):
                t = (y - _HORIZON_Y) / max(1, _GROUND_ROWS)
                # Quadratic gives good perspective feel
                self._line_speeds.append(t * t)

    def _gen_stars(self):
        rng = random.Random(77)
        stars = []
        for _ in range(50):
            stars.append({
                'x': rng.randint(0, SCREEN_WIDTH),
                'y': rng.randint(5, _HORIZON_Y - 10),
                'sz': rng.choice([1, 1, 1, 2]),
                'bright': rng.randint(140, 255),
                'phase': rng.uniform(0, math.pi * 2),
                'cyan': rng.random() < 0.2,
            })
        return stars

    def _gen_mesas(self):
        rng = random.Random(33)
        mesas = []
        x = -100
        tile_w = SCREEN_WIDTH * 2
        while x < tile_w + 200:
            w = rng.randint(90, 180)
            h = rng.randint(40, 80)
            flat_top = rng.randint(int(w * 0.3), int(w * 0.7))
            mesas.append((x, h, w, flat_top))
            x += w + rng.randint(40, 100)
        return mesas

    # --- Layer 0: Stars ---
    def _draw_stars(self, screen):
        star_scroll = self.scroll_y * 0.05
        for s in self._stars:
            dy = int((s['y'] + star_scroll * 0.3) % _HORIZON_Y)
            pulse = math.sin(self._tick * 0.03 + s['phase'])
            bright = max(60, min(255, int(s['bright'] + 40 * pulse)))
            if s['cyan']:
                color = (bright // 2, bright, bright)
            else:
                color = (bright, bright, max(0, bright - 30))
            pygame.draw.circle(screen, color, (s['x'], dy), s['sz'])

    # --- Layer 1: Mesas ---
    def _draw_mesas(self, screen):
        tile_w = SCREEN_WIDTH * 2
        mesa_scroll = int(self.scroll_y * 0.15) % tile_w

        # Horizon glow
        glow_alpha = int(50 + 30 * math.sin(self._tick * 0.02))
        glow = pygame.Surface((SCREEN_WIDTH, 4), pygame.SRCALPHA)
        glow.fill((*_V2_HORIZON_GLOW, glow_alpha))
        screen.blit(glow, (0, _HORIZON_Y - 2))

        for mx, mh, mw, flat in self._mesas:
            sx = (mx - mesa_scroll) % tile_w - 200
            if sx + mw < -50 or sx > SCREEN_WIDTH + 50:
                continue
            inset = (mw - flat) // 3
            pts = [
                (sx, _HORIZON_Y),
                (sx + inset, _HORIZON_Y - mh),
                (sx + inset + flat, _HORIZON_Y - mh),
                (sx + mw, _HORIZON_Y),
            ]
            pygame.draw.polygon(screen, _V2_MESA_COLOR, pts)
            pygame.draw.line(screen, (100, 50, 30),
                             (sx + inset, _HORIZON_Y - mh),
                             (sx + inset + flat, _HORIZON_Y - mh), 1)

    # --- Layer 2-4: Parallax ground strips + rumble + road shoulders ---
    def _draw_ground_strips(self, screen):
        """Draw off-road ground as horizontal strips scrolling at perspective speed.

        Each scanline from horizon to screen bottom gets its own scroll offset
        based on quadratic distance (simulates perspective). Strips alternate
        colors and scroll faster the closer they are to the player.
        """
        left_w = ROAD_LEFT - 24          # off-road left width
        right_x = ROAD_RIGHT + 24        # off-road right start
        right_w = SCREEN_WIDTH - right_x  # off-road right width
        scroll = self.scroll_y

        for i, y in enumerate(range(_HORIZON_Y, SCREEN_HEIGHT)):
            speed_mult = self._line_speeds[i]
            # Vertical scroll offset for this scanline
            offset = scroll * speed_mult
            # Which color band are we in?
            band_idx = int((y + offset) / _BAND_HEIGHT) % 2

            # Depth ratio: 0=horizon 1=bottom  — picks from color gradient
            t = i / max(1, _GROUND_ROWS)
            color_slot = min(4, int(t * 5))
            color = _STRIP_A[color_slot] if band_idx == 0 else _STRIP_B[color_slot]

            # Draw left off-road strip
            if left_w > 0:
                pygame.draw.line(screen, color, (0, y), (left_w, y))

            # Draw right off-road strip
            if right_w > 0:
                pygame.draw.line(screen, color, (right_x, y), (SCREEN_WIDTH, y))

            # Rumble strips on road shoulder edge (alternating red/white blocks)
            rumble_band = int((y + offset) / 6) % 2
            rc = _RUMBLE_A if rumble_band == 0 else _RUMBLE_B
            # Left rumble
            pygame.draw.line(screen, rc, (left_w, y), (left_w + 10, y))
            # Right rumble
            pygame.draw.line(screen, rc, (right_x - 10, y), (right_x, y))

    def _draw_v2(self, speed, screen):
        """Full V2+ 5-layer parallax: sky → stars → mesas → ground strips → road."""
        screen.fill(_V2_SKY)
        self._draw_stars(screen)
        self._draw_mesas(screen)
        self._draw_ground_strips(screen)

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
