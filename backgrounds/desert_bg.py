import pygame
import random
import math

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, NEON_CYAN, NEON_MAGENTA,
    SAND_YELLOW, WHITE, ROAD_LEFT, ROAD_RIGHT, ROAD_WIDTH,
    ROAD_CENTER, ROAD_COLOR, ROAD_EDGE_COLOR, ROAD_SHOULDER,
    DESERT_BG, DASH_LENGTH, DASH_GAP,
)

# --- V2 palette ---
_V2_SKY = (15, 8, 25)
_V2_MESA_COLOR = (80, 35, 20)
_V2_HORIZON_GLOW = (200, 100, 20)

# --- Pseudo-3D perspective constants ---
_HORIZON_Y = int(SCREEN_HEIGHT * 0.30)
_GROUND_ROWS = SCREEN_HEIGHT - _HORIZON_Y
_PROJECTION_D = 100.0       # perspective scale (world-Z = D / t)
_BAND_WORLD = 6.0           # world-space depth per color band
_SCROLL_K = 0.15            # scroll_y -> camera_z conversion

# Road geometry (tapers with perspective: width * t)
_ROAD_HALF = ROAD_WIDTH // 2   # 300 — half road width at full scale
_SHOULDER_W = 24                # shoulder width at full scale
_RUMBLE_W = 8                   # rumble strip width at full scale

# Perspective dash pattern (world-space)
_DASH_WORLD_PERIOD = 4.0        # world units per dash cycle
_DASH_ON_RATIO = 0.5            # center line: 50% on
_LANE_ON_RATIO = 0.3            # lane lines: 30% on (shorter dashes)

# Off-road ground — alternating 5-tier depth gradient
_STRIP_A = [
    (35, 22, 30),   # far — dark purple-brown
    (55, 35, 25),   # mid-far — dusty brown
    (80, 52, 28),   # mid — warm sand
    (100, 65, 32),  # mid-near — bright sand
    (115, 75, 35),  # near — golden sand
]
_STRIP_B = [
    (28, 18, 24),   # far
    (45, 28, 20),   # mid-far
    (65, 42, 22),   # mid
    (85, 55, 26),   # mid-near
    (100, 65, 30),  # near
]

# Road surface perspective bands (subtle dark/light)
_ROAD_BAND_A = (35, 35, 48)    # matches ROAD_COLOR
_ROAD_BAND_B = (44, 44, 58)    # slightly lighter

# Shoulder perspective bands
_SHOULDER_BAND_A = (75, 45, 18)   # matches ROAD_SHOULDER
_SHOULDER_BAND_B = (58, 36, 14)   # darker variant

# Rumble strips
_RUMBLE_A = (200, 50, 50)
_RUMBLE_B = (220, 220, 220)

# Edge / marker colors
_EDGE_GLOW = (20, 120, 150)
_LANE_COLOR = (65, 65, 88)


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
            # Pre-compute per-scanline world Z and depth ratio
            self._line_z = []
            self._line_t = []
            for y in range(_HORIZON_Y, SCREEN_HEIGHT):
                t = (y - _HORIZON_Y + 1) / max(1, _GROUND_ROWS)
                self._line_t.append(t)
                self._line_z.append(_PROJECTION_D / max(t, 0.003))

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

    # --- Layer 2: Pseudo-3D perspective ground + road (tapered) ---
    def _draw_perspective_ground(self, screen):
        """Pseudo-3D ground plane with road width tapering to vanishing point.

        Road width scales by t (depth ratio) — full width at the bottom,
        converging to a point at the horizon. All elements (off-road,
        shoulders, rumble, road surface, edge glow, center/lane dashes)
        are drawn per-scanline with perspective-correct positions.
        """
        camera_z = self.scroll_y * _SCROLL_K

        for i in range(_GROUND_ROWS):
            y = _HORIZON_Y + i
            z = self._line_z[i]
            t = self._line_t[i]

            # === Perspective taper: road narrows toward horizon ===
            half_road = int(_ROAD_HALF * t)
            road_l = ROAD_CENTER - half_road
            road_r = ROAD_CENTER + half_road
            sh_w = int(_SHOULDER_W * t)
            shoulder_l = road_l - sh_w
            shoulder_r = road_r + sh_w
            rw = max(1, int(_RUMBLE_W * t))

            # === Band index (perspective-correct) ===
            pattern = (z - camera_z) / _BAND_WORLD
            band = int(math.floor(pattern)) % 2
            rumble_band = int(math.floor(pattern * 3)) % 2
            slot = min(4, int(t * 5))

            # === Off-road (full width outside shoulders) ===
            gc = _STRIP_A[slot] if band == 0 else _STRIP_B[slot]
            if shoulder_l > 0:
                pygame.draw.line(screen, gc, (0, y), (shoulder_l, y))
            if shoulder_r < SCREEN_WIDTH:
                pygame.draw.line(screen, gc,
                                 (shoulder_r, y), (SCREEN_WIDTH, y))

            # Skip road details when too narrow (near horizon)
            if half_road < 3:
                # Just fill the center with off-road color
                pygame.draw.line(screen, gc, (shoulder_l, y), (shoulder_r, y))
                continue

            # === Shoulders ===
            if sh_w > 0:
                sc = _SHOULDER_BAND_A if band == 0 else _SHOULDER_BAND_B
                pygame.draw.line(screen, sc, (shoulder_l, y), (road_l, y))
                pygame.draw.line(screen, sc, (road_r, y), (shoulder_r, y))

            # === Rumble strips ===
            rc = _RUMBLE_A if rumble_band == 0 else _RUMBLE_B
            pygame.draw.line(screen, rc, (road_l, y), (road_l + rw, y))
            pygame.draw.line(screen, rc, (road_r - rw, y), (road_r, y))

            # === Road surface ===
            inner_l = road_l + rw
            inner_r = road_r - rw
            if inner_r > inner_l:
                road_c = _ROAD_BAND_A if band == 0 else _ROAD_BAND_B
                pygame.draw.line(screen, road_c, (inner_l, y), (inner_r, y))

            # === Edge glow (tapers with perspective) ===
            ew = max(1, int(2 * t))
            pygame.draw.line(screen, _EDGE_GLOW,
                             (road_l - ew, y), (road_l + ew, y))
            pygame.draw.line(screen, _EDGE_GLOW,
                             (road_r - ew, y), (road_r + ew, y))

            # === Perspective-correct dashed markers ===
            dash_phase = ((z - camera_z) / _DASH_WORLD_PERIOD) % 1.0

            # Center line (magenta, 2px)
            if dash_phase < _DASH_ON_RATIO:
                pygame.draw.line(screen, NEON_MAGENTA,
                                 (ROAD_CENTER - 1, y), (ROAD_CENTER, y))

            # Lane lines (at 1/4 and 3/4 of tapered road width)
            if dash_phase < _LANE_ON_RATIO and half_road > 15:
                quarter = half_road // 2
                lane1 = ROAD_CENTER - quarter
                lane2 = ROAD_CENTER + quarter
                pygame.draw.line(screen, _LANE_COLOR,
                                 (lane1, y), (lane1, y))
                pygame.draw.line(screen, _LANE_COLOR,
                                 (lane2, y), (lane2, y))

    def _draw_v2(self, speed, screen):
        """Full V2+ pseudo-3D: sky -> stars -> mesas -> tapered ground+road."""
        screen.fill(_V2_SKY)
        self._draw_stars(screen)
        self._draw_mesas(screen)
        self._draw_perspective_ground(screen)

    def update_and_draw(self, speed, screen, slowmo=False):
        actual_speed = speed * (0.5 if slowmo else 1.0)
        self.scroll_y += actual_speed
        self._tick += 1
        dash_period = DASH_LENGTH + DASH_GAP

        if self.tier >= 2:
            # V2+: full pseudo-3D (everything drawn inside perspective ground)
            self._draw_v2(actual_speed, screen)
        else:
            # V1: flat desert fill + solid road
            screen.fill(DESERT_BG)
            pygame.draw.rect(screen, ROAD_SHOULDER,
                             (ROAD_LEFT - 24, 0, ROAD_WIDTH + 48,
                              SCREEN_HEIGHT))
            pygame.draw.rect(screen, ROAD_COLOR,
                             (ROAD_LEFT, 0, ROAD_WIDTH, SCREEN_HEIGHT))
            pygame.draw.line(screen, (20, 120, 150),
                             (ROAD_LEFT, 0), (ROAD_LEFT, SCREEN_HEIGHT), 4)
            pygame.draw.line(screen, ROAD_EDGE_COLOR,
                             (ROAD_LEFT, 0), (ROAD_LEFT, SCREEN_HEIGHT), 2)
            pygame.draw.line(screen, (20, 120, 150),
                             (ROAD_RIGHT, 0), (ROAD_RIGHT, SCREEN_HEIGHT), 4)
            pygame.draw.line(screen, ROAD_EDGE_COLOR,
                             (ROAD_RIGHT, 0), (ROAD_RIGHT, SCREEN_HEIGHT), 2)

            # V1 center dashed line
            offset = int(self.scroll_y) % dash_period
            y = -DASH_LENGTH + offset
            while y < SCREEN_HEIGHT + DASH_LENGTH:
                pygame.draw.line(screen, NEON_MAGENTA,
                                 (ROAD_CENTER, y),
                                 (ROAD_CENTER, y + DASH_LENGTH), 2)
                y += dash_period

            # V1 lane lines
            for lane_x in [ROAD_LEFT + ROAD_WIDTH // 4,
                            ROAD_LEFT + 3 * ROAD_WIDTH // 4]:
                y = -DASH_LENGTH + offset
                while y < SCREEN_HEIGHT + DASH_LENGTH:
                    pygame.draw.line(screen, (65, 65, 88),
                                     (lane_x, y),
                                     (lane_x, y + DASH_LENGTH // 2), 1)
                    y += dash_period

        # Speed streaks (shared V1+V2)
        if speed > 8:
            intensity = min(30, int((speed - 8) * 12))
            line_surf = pygame.Surface((2, int(speed * 4)), pygame.SRCALPHA)
            line_surf.fill((*WHITE, min(60, intensity * 3)))
            for _ in range(intensity):
                lx = random.randint(0, SCREEN_WIDTH)
                ly = random.randint(0, SCREEN_HEIGHT)
                screen.blit(line_surf, (lx, ly))

        # Sand particles (shared V1+V2)
        self.sand_timer += 1
        if self.sand_timer > 6:
            for _ in range(2):
                x = random.randint(0, SCREEN_WIDTH)
                self.particles.emit(
                    x, random.randint(0, SCREEN_HEIGHT), SAND_YELLOW,
                    [random.uniform(1, 2), random.uniform(0.5, 1.5)], 80, 1,
                )
            self.sand_timer = 0
