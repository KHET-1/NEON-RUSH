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
_V2_MESA_DEEP = (40, 15, 35)
_V2_MESA_RIM = (160, 60, 40)
_V2_HORIZON_GLOW = (200, 100, 20)

# --- Pseudo-3D perspective constants ---
_HORIZON_Y = int(SCREEN_HEIGHT * 0.30)
_GROUND_ROWS = SCREEN_HEIGHT - _HORIZON_Y
_PROJECTION_D = 100.0       # perspective scale (world-Z = D / t)
_BAND_WORLD = 6.0           # world-space depth per color band
_SCROLL_K = 0.15            # scroll_y -> camera_z conversion

# Road geometry (tapers with perspective: width * t)
_ROAD_HALF = ROAD_WIDTH // 2   # 300 — half road width at full scale (V1)
_V2_ROAD_HALF = 350             # 700px road at bottom for V2
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
        self.road_geometry = None
        self._rg_ticked = False

        if tier >= 2:
            self._stars = self._gen_stars()
            self._mesas = self._gen_mesas()
            self._mesas_deep = self._gen_mesas_deep()
            # Pre-compute per-scanline world Z and depth ratio
            self._line_z = []
            self._line_t = []
            for y in range(_HORIZON_Y, SCREEN_HEIGHT):
                t = (y - _HORIZON_Y + 1) / max(1, _GROUND_ROWS)
                self._line_t.append(t)
                self._line_z.append(_PROJECTION_D / max(t, 0.003))
            # Road geometry for curves and hills
            from backgrounds.road_geometry import RoadGeometry
            self.road_geometry = RoadGeometry()

            # --- V2 Synthwave Upgrades ---
            from core.vfx import (
                make_multi_gradient, make_dither_overlay,
                SYNTH_PALETTE, AmbientParticles, VFXState,
            )
            self._synth = SYNTH_PALETTE

            # Pre-rendered synthwave sky gradient (replaces flat fill)
            self._sky_gradient = make_multi_gradient(SCREEN_WIDTH, _HORIZON_Y, [
                (0.0, (8, 4, 28)),       # deep space indigo
                (0.25, (15, 6, 40)),      # dark purple
                (0.50, (25, 8, 50)),      # dusky purple
                (0.70, (80, 20, 60)),     # magenta transition
                (0.85, (180, 50, 80)),    # warm orange-pink
                (1.0, (220, 120, 60)),    # horizon gold
            ])

            # Dither overlay for banding reduction
            self._sky_dither = make_dither_overlay(SCREEN_WIDTH, _HORIZON_Y, strength=20)

            # Pre-rendered synthwave sun
            self._sun_surf = self._make_synthwave_sun()

            # Constellation connections and shooting star state
            self._constellations = self._gen_constellations()
            self._shooting_star = None  # active shooting star dict or None
            self._shooting_star_cooldown = 0

            # Heat shimmer surfaces (pre-rendered)
            self._shimmer_lines = []
            for _ in range(20):
                line = pygame.Surface((SCREEN_WIDTH, 1), pygame.SRCALPHA)
                line.fill((255, 180, 80, 15))
                self._shimmer_lines.append(line)

            # Ember particles (ambient, separate from main particle system)
            self._embers = AmbientParticles(60)
            self._ember_timer = 0

            # VFX post-processing state
            self._vfx = VFXState(enable_scanlines=True)

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

    def _gen_mesas_deep(self):
        """Deeper mesa layer at slower parallax for V2+."""
        rng = random.Random(55)
        mesas = []
        x = -150
        tile_w = SCREEN_WIDTH * 2
        while x < tile_w + 200:
            w = rng.randint(120, 250)
            h = rng.randint(25, 55)
            flat_top = rng.randint(int(w * 0.4), int(w * 0.8))
            mesas.append((x, h, w, flat_top))
            x += w + rng.randint(30, 80)
        return mesas

    def _make_synthwave_sun(self):
        """Pre-render synthwave setting sun with glow and horizontal stripes."""
        size = 180
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2
        body_r = 55

        # Wide outer glow rings (soft warm bloom)
        for i in range(10, 0, -1):
            r = body_r + i * 6
            a = max(3, 35 - i * 3)
            pygame.draw.circle(surf, (255, 80, 120, a), (cx, cy), r)

        # Main sun body — gradient from warm orange edge to bright center
        pygame.draw.circle(surf, (255, 180, 80), (cx, cy), body_r)
        pygame.draw.circle(surf, (255, 210, 120), (cx, cy), body_r - 8)
        pygame.draw.circle(surf, (255, 235, 160), (cx, cy), body_r - 20)

        # Classic synthwave horizontal stripes through lower half
        stripe_gaps = [8, 18, 26, 33, 39, 44]
        for gap in stripe_gaps:
            sy = cy + gap
            stripe_h = max(2, 4 - gap // 15)
            dy = sy - cy
            if abs(dy) < body_r:
                half_w = int(math.sqrt(body_r * body_r - dy * dy))
                pygame.draw.rect(surf, (0, 0, 0, 180),
                                 (cx - half_w, sy, half_w * 2, stripe_h))

        return surf

    def _gen_constellations(self):
        """Find 3-5 star pairs close enough to draw constellation lines."""
        connections = []
        stars = self._stars
        for i in range(len(stars)):
            for j in range(i + 1, len(stars)):
                dx = stars[i]['x'] - stars[j]['x']
                dy = stars[i]['y'] - stars[j]['y']
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < 60:
                    connections.append((i, j))
                if len(connections) >= 5:
                    return connections
        return connections

    # --- Layer 0: Stars ---
    def _draw_stars(self, screen):
        star_scroll = self.scroll_y * 0.05
        # Curve parallax: shift stars opposite to current curve (subtle)
        curve_shift = 0.0
        if self.road_geometry:
            curve_shift = -self.road_geometry.current_curve * 12

        # Collect screen positions for constellation lines
        star_positions = []
        for s in self._stars:
            dy = int((s['y'] + star_scroll * 0.3) % _HORIZON_Y)
            sx = int(s['x'] + curve_shift * 0.5)
            pulse = math.sin(self._tick * 0.03 + s['phase'])
            bright = max(60, min(255, int(s['bright'] + 40 * pulse)))
            if s['cyan']:
                color = (bright // 2, bright, bright)
            else:
                color = (bright, bright, max(0, bright - 30))
            pygame.draw.circle(screen, color, (sx, dy), s['sz'])
            star_positions.append((sx, dy))

        # Constellation lines (V2+)
        if hasattr(self, '_constellations'):
            for i, j in self._constellations:
                if i < len(star_positions) and j < len(star_positions):
                    p1, p2 = star_positions[i], star_positions[j]
                    if 0 <= p1[0] < SCREEN_WIDTH and 0 <= p2[0] < SCREEN_WIDTH:
                        pygame.draw.aaline(screen, (100, 100, 160, 40), p1, p2)

        # Shooting star (V2+)
        if hasattr(self, '_shooting_star'):
            self._update_shooting_star(screen)

    def _update_shooting_star(self, screen):
        """Manage shooting star lifecycle and drawing."""
        if self._shooting_star is None:
            self._shooting_star_cooldown -= 1
            if self._shooting_star_cooldown <= 0:
                # Spawn new shooting star
                self._shooting_star = {
                    'x': random.randint(50, SCREEN_WIDTH - 50),
                    'y': random.randint(10, _HORIZON_Y // 2),
                    'vx': random.uniform(4, 8) * random.choice([-1, 1]),
                    'vy': random.uniform(1, 3),
                    'life': 40,
                    'trail': [],
                }
                self._shooting_star_cooldown = random.randint(200, 400)
        else:
            ss = self._shooting_star
            ss['trail'].append((int(ss['x']), int(ss['y'])))
            if len(ss['trail']) > 5:
                ss['trail'].pop(0)
            ss['x'] += ss['vx']
            ss['y'] += ss['vy']
            ss['life'] -= 1

            # Draw trail
            for idx, (tx, ty) in enumerate(ss['trail']):
                a = int(180 * (idx + 1) / len(ss['trail']) * (ss['life'] / 40))
                sz = max(1, 2 - idx // 3)
                s = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (255, 255, 220, a), (sz, sz), sz)
                screen.blit(s, (tx - sz, ty - sz))

            # Draw head
            head_a = int(255 * (ss['life'] / 40))
            pygame.draw.circle(screen, (255, 255, 255), (int(ss['x']), int(ss['y'])), 2)

            if ss['life'] <= 0 or ss['x'] < -20 or ss['x'] > SCREEN_WIDTH + 20:
                self._shooting_star = None
                self._shooting_star_cooldown = random.randint(200, 400)

    # --- Layer 0.5: Deep Mesas (V2+) ---
    def _draw_mesas_deep(self, screen):
        """Deeper, darker mesa layer at slowest parallax for V2+."""
        tile_w = SCREEN_WIDTH * 2
        curve_offset = 0
        if self.road_geometry:
            curve_offset = int(-self.road_geometry.current_curve * 10)
        mesa_scroll = (int(self.scroll_y * 0.08) - curve_offset) % tile_w

        for mx, mh, mw, flat in self._mesas_deep:
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
            pygame.draw.polygon(screen, _V2_MESA_DEEP, pts)

    # --- Layer 1: Mesas ---
    def _draw_mesas(self, screen):
        tile_w = SCREEN_WIDTH * 2
        # Curve parallax: mesas shift opposite to road curve (subtle)
        curve_offset = 0
        if self.road_geometry:
            curve_offset = int(-self.road_geometry.current_curve * 20)
        mesa_scroll = (int(self.scroll_y * 0.15) - curve_offset) % tile_w

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
            # V2+ rim lighting: bright top edge
            pygame.draw.line(screen, _V2_MESA_RIM,
                             (sx + inset, _HORIZON_Y - mh),
                             (sx + inset + flat, _HORIZON_Y - mh), 2)
            # Left slope rim highlight
            pygame.draw.line(screen, (120, 50, 35),
                             (sx, _HORIZON_Y),
                             (sx + inset, _HORIZON_Y - mh), 1)

    # --- Layer 2: Pseudo-3D perspective ground + road (tapered) ---
    def _draw_perspective_ground(self, screen):
        """Pseudo-3D ground plane with road width tapering to vanishing point.

        When road_geometry is active, uses its scanline_data for per-scanline
        center_x and half_w — giving curves and hills. Otherwise falls back
        to straight-road rendering.
        """
        camera_z = self.scroll_y * _SCROLL_K
        rg = self.road_geometry
        use_rg = rg is not None
        road_half_base = _V2_ROAD_HALF if use_rg else _ROAD_HALF

        for i in range(_GROUND_ROWS):
            z = self._line_z[i]
            t = self._line_t[i]

            # === Get center and width from road geometry or straight fallback ===
            if use_rg:
                sd = rg.scanline_data[i]
                center_x = sd.center_x
                half_road = int(sd.half_w)
                y = int(sd.screen_y)
                # Clamp y to valid screen range
                if y < _HORIZON_Y or y >= SCREEN_HEIGHT:
                    continue
            else:
                center_x = ROAD_CENTER
                half_road = int(road_half_base * t)
                y = _HORIZON_Y + i

            road_l = int(center_x - half_road)
            road_r = int(center_x + half_road)
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

            # === Edge glow (tapers with perspective, V2+ enhanced) ===
            ew = max(1, int(2 * t))
            pygame.draw.line(screen, _EDGE_GLOW,
                             (road_l - ew, y), (road_l + ew, y))
            pygame.draw.line(screen, _EDGE_GLOW,
                             (road_r - ew, y), (road_r + ew, y))

            # V2+ enhanced road edge glow (every 3rd scanline)
            if self.tier >= 2 and i % 3 == 0:
                # Speed-responsive color: cyan → hot pink at high speed
                edge_color = _EDGE_GLOW
                if hasattr(self, '_synth'):
                    speed_t = min(1.0, self.scroll_y * _SCROLL_K * 0.001)
                    edge_color = (
                        int(20 + 235 * speed_t),
                        int(120 - 70 * speed_t),
                        int(150 - 30 * speed_t),
                    )
                # Inner glow (w4, alpha ~80)
                iw = max(1, int(4 * t))
                s_inner = pygame.Surface((iw, 1), pygame.SRCALPHA)
                s_inner.fill((*edge_color, 80))
                screen.blit(s_inner, (road_l - iw // 2, y))
                screen.blit(s_inner, (road_r - iw // 2, y))
                # Mid glow (w8, alpha ~40)
                mw = max(1, int(8 * t))
                s_mid = pygame.Surface((mw, 1), pygame.SRCALPHA)
                s_mid.fill((*edge_color, 40))
                screen.blit(s_mid, (road_l - mw // 2, y))
                screen.blit(s_mid, (road_r - mw // 2, y))
                # Outer glow (w12, alpha ~15)
                ow = max(1, int(12 * t))
                s_out = pygame.Surface((ow, 1), pygame.SRCALPHA)
                s_out.fill((*edge_color, 15))
                screen.blit(s_out, (road_l - ow // 2, y))
                screen.blit(s_out, (road_r - ow // 2, y))

            # === Perspective-correct dashed markers ===
            dash_phase = ((z - camera_z) / _DASH_WORLD_PERIOD) % 1.0
            cx = int(center_x)

            # Center line (magenta, 2px)
            if dash_phase < _DASH_ON_RATIO:
                pygame.draw.line(screen, NEON_MAGENTA,
                                 (cx - 1, y), (cx, y))

            # Lane lines (at 1/4 and 3/4 of tapered road width)
            if dash_phase < _LANE_ON_RATIO and half_road > 15:
                quarter = half_road // 2
                lane1 = cx - quarter
                lane2 = cx + quarter
                pygame.draw.line(screen, _LANE_COLOR,
                                 (lane1, y), (lane1, y))
                pygame.draw.line(screen, _LANE_COLOR,
                                 (lane2, y), (lane2, y))

    def _draw_v2(self, speed, screen):
        """Full V2+ pseudo-3D: synthwave sky -> stars -> sun -> mesas -> ground."""
        # Synthwave gradient sky (1 blit, clean — no dither noise)
        if hasattr(self, '_sky_gradient'):
            screen.blit(self._sky_gradient, (0, 0))
        else:
            screen.fill(_V2_SKY)

        self._draw_stars(screen)

        # Synthwave sun — half-sunk into horizon, very slow bob
        if hasattr(self, '_sun_surf'):
            sun_h = self._sun_surf.get_height()
            sun_y = _HORIZON_Y - sun_h // 2 + int(1.5 * math.sin(self._tick * 0.002))
            sun_x = SCREEN_WIDTH // 2 - self._sun_surf.get_width() // 2
            screen.blit(self._sun_surf, (sun_x, sun_y))

        # Deep mesa layer (slowest parallax)
        if hasattr(self, '_mesas_deep'):
            self._draw_mesas_deep(screen)

        self._draw_mesas(screen)

        # Soft horizon glow band (pre-rendered, slow pulse)
        if hasattr(self, '_synth'):
            if not hasattr(self, '_horizon_glow'):
                self._horizon_glow = pygame.Surface((SCREEN_WIDTH, 8), pygame.SRCALPHA)
            pulse = 0.6 + 0.4 * math.sin(self._tick * 0.008)
            glow_a = int(30 + 25 * pulse)
            self._horizon_glow.fill((220, 120, 60, glow_a))
            screen.blit(self._horizon_glow, (0, _HORIZON_Y - 4))

        self._draw_perspective_ground(screen)

        # Heat shimmer near horizon (slow, subtle)
        if hasattr(self, '_shimmer_lines'):
            for idx, line in enumerate(self._shimmer_lines):
                base_y = _HORIZON_Y + 10 + idx * 6
                offset_x = int(math.sin(base_y * 0.05 + self._tick * 0.015) * 1.5)
                screen.blit(line, (offset_x, base_y))

        # Floating ember particles
        if hasattr(self, '_embers'):
            self._ember_timer += 1
            if self._ember_timer >= 8:
                self._ember_timer = 0
                for _ in range(2):
                    ex = random.randint(0, SCREEN_WIDTH)
                    ey = random.randint(SCREEN_HEIGHT * 3 // 4, SCREEN_HEIGHT)
                    color = random.choice([
                        (255, 120, 40), (255, 80, 20), (255, 160, 60),
                    ])
                    vx = random.uniform(-0.3, 0.3)
                    vy = random.uniform(-1.2, -0.4)
                    life = random.randint(120, 200)
                    self._embers.spawn(ex, ey, vx, vy, life, color, size=random.choice([1, 2]))
            self._embers.update()
            self._embers.draw(screen)

    def tick_road(self, speed):
        """Advance road geometry without drawing. Call from update() so
        projection works even in headless mode."""
        if self.road_geometry:
            self.road_geometry.advance(speed)
            self.road_geometry.compute_projection()
            self._rg_ticked = True

    def update_and_draw(self, speed, screen, slowmo=False):
        actual_speed = speed * (0.5 if slowmo else 1.0)
        self.scroll_y += actual_speed
        self._tick += 1
        dash_period = DASH_LENGTH + DASH_GAP

        if self.tier >= 2:
            # Advance road geometry and recompute projection
            # (skip if already ticked this frame via tick_road())
            if self.road_geometry and not self._rg_ticked:
                self.road_geometry.advance(actual_speed)
                self.road_geometry.compute_projection()
            self._rg_ticked = False
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

        # V2+ post-processing (scanlines, flash)
        if self.tier >= 2 and hasattr(self, '_vfx'):
            self._vfx.update()
            self._vfx.draw_post(screen)
