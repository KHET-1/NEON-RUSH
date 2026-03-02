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
_V2_MESA_COLOR = (70, 30, 22)
_V2_MESA_DEEP = (35, 14, 30)
_V2_MESA_RIM = (200, 110, 50)       # warm gold rim catch
_V2_HORIZON_GLOW = (180, 90, 40)

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

# Off-road ground — alternating 5-tier depth gradient (BRIGHT, visible terrain)
_STRIP_A = [
    (60, 35, 50),    # far — warm purple-brown
    (90, 60, 40),    # mid-far — dusty sand
    (130, 85, 45),   # mid — rich sand
    (160, 110, 55),  # mid-near — bright warm sand
    (185, 130, 60),  # near — golden sand (vivid)
]
_STRIP_B = [
    (45, 28, 40),    # far — darker band (clear contrast with A)
    (70, 48, 32),    # mid-far
    (105, 70, 38),   # mid
    (135, 95, 48),   # mid-near
    (160, 115, 52),  # near
]

# Road surface perspective bands (visible grey with contrast)
_ROAD_BAND_A = (50, 48, 65)     # cool dark asphalt
_ROAD_BAND_B = (65, 62, 80)     # lighter band — clear scrolling motion

# Shoulder perspective bands (warm brown, visible)
_SHOULDER_BAND_A = (110, 70, 30)   # warm shoulder
_SHOULDER_BAND_B = (85, 55, 22)    # darker shoulder

# Rumble strips (high contrast markers)
_RUMBLE_A = (220, 60, 60)
_RUMBLE_B = (240, 240, 240)

# Edge / marker colors (brighter neon)
_EDGE_GLOW = (30, 180, 220)
_LANE_COLOR = (90, 90, 120)


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

            # Pre-rendered synthwave sky gradient (smooth 8-stop sunset)
            self._sky_gradient = make_multi_gradient(SCREEN_WIDTH, _HORIZON_Y, [
                (0.00, (4, 2, 18)),       # deep space — near black
                (0.15, (8, 4, 28)),       # space indigo
                (0.30, (14, 6, 38)),      # dark purple
                (0.45, (22, 8, 48)),      # dusky purple
                (0.58, (40, 12, 52)),     # warm purple transition
                (0.70, (65, 18, 55)),     # muted magenta
                (0.82, (110, 40, 65)),    # dusty rose
                (0.92, (150, 65, 55)),    # warm amber
                (1.00, (180, 90, 45)),    # horizon gold (toned down)
            ])

            # Dither overlay for banding reduction
            self._sky_dither = make_dither_overlay(SCREEN_WIDTH, _HORIZON_Y, strength=20)

            # Pre-rendered synthwave sun
            self._sun_surf = self._make_synthwave_sun()

            # Warm sun glow band — wider and brighter
            self._sun_glow_band = pygame.Surface((SCREEN_WIDTH, 50), pygame.SRCALPHA)
            for row in range(50):
                a = int(70 * (1 - row / 50))
                pygame.draw.line(self._sun_glow_band, (255, 150, 60, a),
                                 (0, row), (SCREEN_WIDTH, row))

            # Constellation connections and shooting star state
            self._constellations = self._gen_constellations()
            self._shooting_star = None  # active shooting star dict or None
            self._shooting_star_cooldown = 0

            # Heat shimmer surfaces (pre-rendered, fewer but more visible)
            self._shimmer_lines = []
            for _ in range(10):
                line = pygame.Surface((SCREEN_WIDTH, 2), pygame.SRCALPHA)
                line.fill((255, 180, 100, 25))
                self._shimmer_lines.append(line)

            # (Edge glow now uses direct draw.line — no cached surfaces needed)

            # Ember particles (ambient, separate from main particle system)
            self._embers = AmbientParticles(60)
            self._ember_timer = 0

            # VFX post-processing state (scanlines disabled — saves ~1ms/frame)
            self._vfx = VFXState(enable_scanlines=False)

        # --- V3 Crimson Sandstorm Upgrades ---
        if tier >= 3:
            from core.vfx import (
                make_multi_gradient, CRIMSON_PALETTE, AmbientParticles, VFXState,
            )
            self._crimson = CRIMSON_PALETTE

            # Crimson 6-stop sky gradient
            self._v3_sky = make_multi_gradient(SCREEN_WIDTH, _HORIZON_Y, [
                (0.00, (25, 2, 2)),
                (0.20, (50, 5, 5)),
                (0.40, (80, 8, 8)),
                (0.60, (120, 15, 8)),
                (0.80, (160, 25, 10)),
                (1.00, (180, 30, 10)),
            ])

            # Storm wall surfaces (3 semi-transparent oscillating columns)
            self._storm_walls = []
            rng = random.Random(42)
            for _ in range(3):
                w = rng.randint(60, 120)
                wall_surf = pygame.Surface((w, _HORIZON_Y), pygame.SRCALPHA)
                for wy in range(_HORIZON_Y):
                    a = rng.randint(15, 40)
                    pygame.draw.line(wall_surf, (120, 20, 10, a), (0, wy), (w, wy))
                self._storm_walls.append({
                    'surf': wall_surf,
                    'base_x': rng.randint(0, SCREEN_WIDTH),
                    'speed': rng.uniform(0.3, 0.8),
                    'phase': rng.uniform(0, math.pi * 2),
                })

            # Lightning state
            self._lightning = None  # dict with points + life when active
            self._lightning_cooldown = 0

            # Aggressive embers (160 cap)
            self._embers = AmbientParticles(160)
            self._ember_timer = 0

            # Road crack overlay tile (pre-baked)
            self._crack_tile = self._make_crack_tile()

            # Dust devil positions
            self._dust_devils = []
            dd_rng = random.Random(88)
            for _ in range(3):
                self._dust_devils.append({
                    'x': dd_rng.randint(50, SCREEN_WIDTH - 50),
                    'phase': dd_rng.uniform(0, math.pi * 2),
                    'size': dd_rng.randint(15, 30),
                })

            # V3 VFX with crimson tone
            self._vfx = VFXState(enable_scanlines=False, tier=3,
                                 tone_color=(180, 30, 10))

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
        """Pre-render synthwave setting sun — big, blazing, classic retrowave."""
        size = 320
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2
        body_r = 110

        # Hot outer glow — 16 rings, exponential alpha falloff
        for i in range(16, 0, -1):
            r = body_r + i * 10
            a = int(130 * ((1 - i / 16) ** 1.5))
            pygame.draw.circle(surf, (255, 100, 40, a), (cx, cy), r)

        # Corona ring — bright edge just outside the body
        pygame.draw.circle(surf, (255, 200, 100, 80), (cx, cy), body_r + 2, 3)

        # Sun body — smooth warm gradient (amber edge → gold → white-hot core)
        pygame.draw.circle(surf, (240, 100, 30), (cx, cy), body_r)
        pygame.draw.circle(surf, (250, 160, 60), (cx, cy), body_r - 15)
        pygame.draw.circle(surf, (255, 210, 120), (cx, cy), body_r - 35)
        pygame.draw.circle(surf, (255, 240, 180), (cx, cy), body_r - 55)
        pygame.draw.circle(surf, (255, 250, 220), (cx, cy), body_r - 70)

        # Classic synthwave horizontal stripes (5 clean bands, wider near bottom)
        stripe_offsets = [20, 40, 58, 72, 85]
        for gap in stripe_offsets:
            sy = cy + gap
            stripe_h = max(2, 6 - gap // 18)
            dy = sy - cy
            if abs(dy) < body_r:
                half_w = int(math.sqrt(body_r * body_r - dy * dy))
                pygame.draw.rect(surf, (0, 0, 0, 150),
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
                        pygame.draw.aaline(screen, (140, 140, 200), p1, p2)

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

            # Draw trail (direct draw, no Surface allocs)
            for idx, (tx, ty) in enumerate(ss['trail']):
                brightness = int(200 * (idx + 1) / len(ss['trail']) * (ss['life'] / 40))
                brightness = max(30, min(255, brightness))
                sz = max(1, 2 - idx // 3)
                pygame.draw.circle(screen, (brightness, brightness, int(brightness * 0.85)), (tx, ty), sz)

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

        # Horizon glow (pre-allocated surface)
        if not hasattr(self, '_mesa_horizon_glow'):
            self._mesa_horizon_glow = pygame.Surface((SCREEN_WIDTH, 6), pygame.SRCALPHA)
        glow_alpha = int(40 + 20 * math.sin(self._tick * 0.015))
        self._mesa_horizon_glow.fill((*_V2_HORIZON_GLOW, glow_alpha))
        screen.blit(self._mesa_horizon_glow, (0, _HORIZON_Y - 3))

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
            # Left slope rim highlight (warm amber)
            pygame.draw.line(screen, (180, 90, 40),
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

        # Pre-fetch arrays for inner loop speed
        line_z = self._line_z
        line_t = self._line_t
        draw_line = pygame.draw.line
        floor = math.floor

        for i in range(_GROUND_ROWS):
            t = line_t[i]

            # === Skip every other scanline in the top 30% (near horizon, lines are <2px wide) ===
            if t < 0.30 and (i & 1):
                continue

            z = line_z[i]

            # === Get center and width from road geometry or straight fallback ===
            if use_rg:
                sd = rg.scanline_data[i]
                center_x = sd.center_x
                half_road = int(sd.half_w)
                y = int(sd.screen_y)
                if y < _HORIZON_Y or y >= SCREEN_HEIGHT:
                    continue
            else:
                center_x = ROAD_CENTER
                half_road = int(road_half_base * t)
                y = _HORIZON_Y + i

            road_l = int(center_x - half_road)
            road_r = int(center_x + half_road)

            # === Band index (perspective-correct) ===
            pattern = (z - camera_z) / _BAND_WORLD
            band = int(floor(pattern)) & 1
            slot = min(4, int(t * 5))
            gc = _STRIP_A[slot] if band == 0 else _STRIP_B[slot]

            # Skip road details when too narrow (near horizon) — single fill
            if half_road < 4:
                draw_line(screen, gc, (0, y), (SCREEN_WIDTH, y))
                continue

            sh_w = int(_SHOULDER_W * t)
            shoulder_l = road_l - sh_w
            shoulder_r = road_r + sh_w
            rw = max(1, int(_RUMBLE_W * t))

            # === Full scanline drawn in order: ground, shoulder, road, rumble, edge, markers ===
            # Off-road ground
            if shoulder_l > 0:
                draw_line(screen, gc, (0, y), (shoulder_l, y))
            if shoulder_r < SCREEN_WIDTH:
                draw_line(screen, gc, (shoulder_r, y), (SCREEN_WIDTH, y))

            # Shoulders + road as 3 lines (shoulder_l, road, shoulder_r)
            sc = _SHOULDER_BAND_A if band == 0 else _SHOULDER_BAND_B
            road_c = _ROAD_BAND_A if band == 0 else _ROAD_BAND_B
            if sh_w > 1:
                draw_line(screen, sc, (shoulder_l, y), (road_l, y))
                draw_line(screen, sc, (road_r, y), (shoulder_r, y))
            draw_line(screen, road_c, (road_l + rw, y), (road_r - rw, y))

            # Rumble strips
            rc = _RUMBLE_A if (int(floor(pattern * 3)) & 1) == 0 else _RUMBLE_B
            draw_line(screen, rc, (road_l, y), (road_l + rw, y))
            draw_line(screen, rc, (road_r - rw, y), (road_r, y))

            # Edge glow
            ew = max(1, int(2 * t))
            draw_line(screen, _EDGE_GLOW, (road_l - ew, y), (road_l + ew, y))
            draw_line(screen, _EDGE_GLOW, (road_r - ew, y), (road_r + ew, y))

            # === Dashed markers ===
            dash_phase = ((z - camera_z) / _DASH_WORLD_PERIOD) % 1.0
            cx = int(center_x)

            if dash_phase < _DASH_ON_RATIO:
                draw_line(screen, NEON_MAGENTA, (cx - 1, y), (cx, y))

            if dash_phase < _LANE_ON_RATIO and half_road > 15:
                quarter = half_road >> 1
                draw_line(screen, _LANE_COLOR, (cx - quarter, y), (cx - quarter, y))
                draw_line(screen, _LANE_COLOR, (cx + quarter, y), (cx + quarter, y))

    def _make_crack_tile(self):
        """Pre-bake 800x4 road crack overlay."""
        tile = pygame.Surface((SCREEN_WIDTH, 4), pygame.SRCALPHA)
        rng = random.Random(77)
        for _ in range(20):
            x = rng.randint(0, SCREEN_WIDTH)
            w = rng.randint(10, 60)
            pygame.draw.line(tile, (90, 45, 15, 80), (x, rng.randint(0, 3)),
                             (x + w, rng.randint(0, 3)), 1)
        return tile

    def _make_lightning_bolt(self):
        """Generate jagged midpoint-displaced polyline for lightning."""
        x1 = random.randint(SCREEN_WIDTH // 4, 3 * SCREEN_WIDTH // 4)
        y1 = 0
        x2 = x1 + random.randint(-80, 80)
        y2 = _HORIZON_Y
        points = [(x1, y1), (x2, y2)]
        # 3 levels of midpoint displacement
        for _ in range(3):
            new_pts = [points[0]]
            for i in range(len(points) - 1):
                mx = (points[i][0] + points[i + 1][0]) // 2 + random.randint(-25, 25)
                my = (points[i][1] + points[i + 1][1]) // 2
                new_pts.append((mx, my))
                new_pts.append(points[i + 1])
            points = new_pts
        return points

    def _draw_v3(self, speed, screen):
        """Full V3: crimson storm sky, no sun, tinted mesas, storm walls, lightning."""
        # Crimson sky
        screen.blit(self._v3_sky, (0, 0))

        # Storm walls (oscillating position)
        for wall in self._storm_walls:
            ox = int(math.sin(self._tick * 0.01 + wall['phase']) * 60)
            bx = (wall['base_x'] + ox + int(self.scroll_y * wall['speed'])) % (SCREEN_WIDTH + wall['surf'].get_width()) - wall['surf'].get_width()
            screen.blit(wall['surf'], (bx, 0))

        # Stars still visible (dimmer through storm)
        self._draw_stars(screen)

        # Skip sun — storm-obscured

        # Mesas tinted crimson
        self._draw_mesas_deep(screen)
        self._draw_mesas(screen)

        # Horizon glow (crimson)
        if not hasattr(self, '_v3_horizon_glow'):
            self._v3_horizon_glow = pygame.Surface((SCREEN_WIDTH, 14), pygame.SRCALPHA)
        pulse = 0.7 + 0.3 * math.sin(self._tick * 0.008)
        glow_a = int(40 + 25 * pulse)
        self._v3_horizon_glow.fill((180, 30, 10, glow_a))
        screen.blit(self._v3_horizon_glow, (0, _HORIZON_Y - 7))

        # Draw scorched road (override colors)
        self._draw_perspective_ground_v3(screen)

        # Lightning bolts (1/200 chance per frame, 8-frame life)
        if self._lightning_cooldown > 0:
            self._lightning_cooldown -= 1
        if self._lightning is None and random.random() < 0.005 and self._lightning_cooldown <= 0:
            self._lightning = {
                'points': self._make_lightning_bolt(),
                'life': 8,
            }
            self._lightning_cooldown = 60
        if self._lightning:
            bolt = self._lightning
            a = int(255 * (bolt['life'] / 8))
            color = (255, 220, 180, min(255, a))
            if len(bolt['points']) >= 2:
                pygame.draw.lines(screen, color[:3], False, bolt['points'], 2)
                # Bright core
                pygame.draw.lines(screen, (255, 255, 255), False, bolt['points'], 1)
            bolt['life'] -= 1
            if bolt['life'] <= 0:
                self._lightning = None

        # Dust devils
        for dd in self._dust_devils:
            dd_x = (dd['x'] + int(self.scroll_y * 0.1)) % SCREEN_WIDTH
            dd_phase = self._tick * 0.05 + dd['phase']
            for ring in range(4):
                r = dd['size'] - ring * 4
                if r < 3:
                    break
                ox = int(math.sin(dd_phase + ring * 0.5) * ring * 2)
                y_base = _HORIZON_Y + 20 + ring * 8
                pygame.draw.ellipse(screen, (120, 60, 20, max(20, 80 - ring * 20)),
                                    (dd_x + ox - r, y_base - r // 3, r * 2, r))

        # Floating embers (aggressive, 160 cap)
        self._ember_timer += 1
        if self._ember_timer >= 4:
            self._ember_timer = 0
            for _ in range(4):
                ex = random.randint(0, SCREEN_WIDTH)
                ey = random.randint(SCREEN_HEIGHT * 2 // 3, SCREEN_HEIGHT)
                color = random.choice([
                    (255, 80, 20), (255, 50, 10), (255, 120, 30), (200, 40, 10),
                ])
                vx = random.uniform(-0.5, 0.5)
                vy = random.uniform(-1.5, -0.5)
                life = random.randint(100, 180)
                self._embers.spawn(ex, ey, vx, vy, life, color, size=random.choice([1, 2]))
        self._embers.update()
        self._embers.draw(screen)

    def _draw_perspective_ground_v3(self, screen):
        """V3 scorched road with crack overlay — delegates to base with color override."""
        camera_z = self.scroll_y * _SCROLL_K
        rg = self.road_geometry
        use_rg = rg is not None
        road_half_base = _V2_ROAD_HALF if use_rg else _ROAD_HALF

        line_z = self._line_z
        line_t = self._line_t
        draw_line = pygame.draw.line
        floor = math.floor

        # V3 scorched road colors
        v3_road_a = (60, 30, 10)
        v3_road_b = (75, 40, 15)
        # V3 ground strips — dark scorched earth
        v3_strip_a = [
            (40, 18, 12), (55, 28, 15), (70, 35, 18), (85, 42, 22), (100, 50, 25),
        ]
        v3_strip_b = [
            (30, 14, 10), (42, 22, 12), (55, 30, 15), (68, 38, 18), (80, 45, 22),
        ]

        for i in range(_GROUND_ROWS):
            t = line_t[i]
            if t < 0.30 and (i & 1):
                continue
            z = line_z[i]

            if use_rg:
                sd = rg.scanline_data[i]
                center_x = sd.center_x
                half_road = int(sd.half_w)
                y = int(sd.screen_y)
                if y < _HORIZON_Y or y >= SCREEN_HEIGHT:
                    continue
            else:
                center_x = ROAD_CENTER
                half_road = int(road_half_base * t)
                y = _HORIZON_Y + i

            road_l = int(center_x - half_road)
            road_r = int(center_x + half_road)

            pattern = (z - camera_z) / _BAND_WORLD
            band = int(floor(pattern)) & 1
            slot = min(4, int(t * 5))
            gc = v3_strip_a[slot] if band == 0 else v3_strip_b[slot]

            if half_road < 4:
                draw_line(screen, gc, (0, y), (SCREEN_WIDTH, y))
                continue

            sh_w = int(_SHOULDER_W * t)
            shoulder_l = road_l - sh_w
            shoulder_r = road_r + sh_w
            rw = max(1, int(_RUMBLE_W * t))

            if shoulder_l > 0:
                draw_line(screen, gc, (0, y), (shoulder_l, y))
            if shoulder_r < SCREEN_WIDTH:
                draw_line(screen, gc, (shoulder_r, y), (SCREEN_WIDTH, y))

            sc = _SHOULDER_BAND_A if band == 0 else _SHOULDER_BAND_B
            road_c = v3_road_a if band == 0 else v3_road_b
            if sh_w > 1:
                draw_line(screen, sc, (shoulder_l, y), (road_l, y))
                draw_line(screen, sc, (road_r, y), (shoulder_r, y))
            draw_line(screen, road_c, (road_l + rw, y), (road_r - rw, y))

            rc = _RUMBLE_A if (int(floor(pattern * 3)) & 1) == 0 else _RUMBLE_B
            draw_line(screen, rc, (road_l, y), (road_l + rw, y))
            draw_line(screen, rc, (road_r - rw, y), (road_r, y))

            ew = max(1, int(2 * t))
            draw_line(screen, (200, 50, 20), (road_l - ew, y), (road_l + ew, y))
            draw_line(screen, (200, 50, 20), (road_r - ew, y), (road_r + ew, y))

            # Dashed markers
            dash_phase = ((z - camera_z) / _DASH_WORLD_PERIOD) % 1.0
            cx = int(center_x)
            if dash_phase < _DASH_ON_RATIO:
                draw_line(screen, (200, 40, 20), (cx - 1, y), (cx, y))
            if dash_phase < _LANE_ON_RATIO and half_road > 15:
                quarter = half_road >> 1
                draw_line(screen, (100, 50, 30), (cx - quarter, y), (cx - quarter, y))
                draw_line(screen, (100, 50, 30), (cx + quarter, y), (cx + quarter, y))

        # Road crack overlay (blit every 8th scanline group)
        if hasattr(self, '_crack_tile'):
            for cy in range(_HORIZON_Y + 20, SCREEN_HEIGHT, 30):
                screen.blit(self._crack_tile, (0, cy), special_flags=pygame.BLEND_RGB_ADD)

    def _draw_v2(self, speed, screen):
        """Full V2+ pseudo-3D: synthwave sky -> stars -> sun -> mesas -> ground."""
        # Synthwave gradient sky (1 blit, clean — no dither noise)
        if hasattr(self, '_sky_gradient'):
            screen.blit(self._sky_gradient, (0, 0))
        else:
            screen.fill(_V2_SKY)

        self._draw_stars(screen)

        # Synthwave sun — sitting on horizon, deeply submerged (classic retrowave)
        if hasattr(self, '_sun_surf'):
            sun_h = self._sun_surf.get_height()
            sun_y = _HORIZON_Y - int(sun_h * 0.45) + int(2.0 * math.sin(self._tick * 0.003))
            sun_x = SCREEN_WIDTH // 2 - self._sun_surf.get_width() // 2
            screen.blit(self._sun_surf, (sun_x, sun_y))

        # Warm sun glow band along horizon
        if hasattr(self, '_sun_glow_band'):
            screen.blit(self._sun_glow_band, (0, _HORIZON_Y - 15))

        # Deep mesa layer (slowest parallax) — partially occludes rays for depth
        if hasattr(self, '_mesas_deep'):
            self._draw_mesas_deep(screen)

        self._draw_mesas(screen)

        # Soft horizon glow band — wider, warmer, gentle pulse
        if hasattr(self, '_synth'):
            if not hasattr(self, '_horizon_glow'):
                self._horizon_glow = pygame.Surface((SCREEN_WIDTH, 14), pygame.SRCALPHA)
            pulse = 0.7 + 0.3 * math.sin(self._tick * 0.006)
            glow_a = int(35 + 20 * pulse)
            self._horizon_glow.fill((180, 100, 50, glow_a))
            screen.blit(self._horizon_glow, (0, _HORIZON_Y - 7))

        self._draw_perspective_ground(screen)

        # Heat shimmer near horizon (gentle wave distortion)
        if hasattr(self, '_shimmer_lines'):
            for idx, line in enumerate(self._shimmer_lines):
                base_y = _HORIZON_Y + 8 + idx * 10
                offset_x = int(math.sin(idx * 0.8 + self._tick * 0.02) * 3.0)
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
            if self.tier >= 3 and hasattr(self, '_v3_sky'):
                self._draw_v3(actual_speed, screen)
            else:
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

        # Speed streaks (shared V1+V2) — subtle, fewer
        if speed > 10:
            intensity = min(12, int((speed - 10) * 4))
            if not hasattr(self, '_streak_surf'):
                self._streak_surf = pygame.Surface((1, 30), pygame.SRCALPHA)
                self._streak_surf.fill((255, 255, 255, 35))
            for _ in range(intensity):
                lx = random.randint(0, SCREEN_WIDTH)
                ly = random.randint(_HORIZON_Y, SCREEN_HEIGHT)
                screen.blit(self._streak_surf, (lx, ly))

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
