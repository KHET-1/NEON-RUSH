import pygame
import math
import random

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, NEON_CYAN, NEON_MAGENTA


# Color palette for excitebike
SKY_TOP = (30, 20, 60)
SKY_BOTTOM = (80, 40, 100)
MOUNTAIN_FAR = (50, 30, 70)
MOUNTAIN_NEAR = (70, 40, 80)
GROUND_COLOR = (100, 65, 30)
ROAD_DARK = (60, 55, 50)
ROAD_LIGHT = (80, 75, 65)
GRASS_GREEN = (40, 90, 30)
LANE_LINE = (200, 180, 120)


class ExcitebikeBg:
    """Side-scrolling hilly terrain with parallax mountains."""

    # 3 lanes (top=fast, mid=normal, bottom=slow)
    LANE_Y = [340, 400, 460]
    LANE_HEIGHT = 55
    GROUND_Y = 310  # Where ground/road starts

    def __init__(self, tier=1):
        self.scroll_x = 0.0
        self.mountain_scroll = 0.0
        self.tier = tier
        self._tick = 0
        # Pre-generate mountain silhouettes
        self.mountains_far = self._gen_mountains(20, 80, 150, seed=42)
        self.mountains_near = self._gen_mountains(15, 100, 200, seed=99)

        # V2+ layers
        if tier >= 2:
            self.mountains_deep = self._gen_mountains(25, 40, 90, seed=7)
            self._grass_tufts = self._gen_grass_tufts()

            from core.vfx import (
                make_multi_gradient, make_dither_overlay,
                TWILIGHT_PALETTE, AmbientParticles, VFXState,
            )
            self._twilight = TWILIGHT_PALETTE

            # Pre-rendered sky gradient (replaces 310 per-scanline draw.line calls)
            self._sky_gradient = make_multi_gradient(SCREEN_WIDTH, self.GROUND_Y, [
                (0.0, (10, 8, 30)),       # deep twilight
                (0.30, (20, 12, 45)),     # dark purple
                (0.55, (30, 15, 55)),     # mid purple
                (0.75, (80, 35, 80)),     # pink transition
                (0.90, (120, 60, 100)),   # warm horizon
                (1.0, (160, 80, 70)),     # sunset glow
            ])
            self._sky_dither = make_dither_overlay(SCREEN_WIDTH, self.GROUND_Y, strength=15)

            # Pre-generated cloud surfaces
            self._clouds_far = self._gen_clouds(8, (25, 15, 45, 80), seed=10)
            self._clouds_near = self._gen_clouds(6, (50, 30, 70, 60), seed=20)

            # Pre-rendered tree silhouettes
            self._trees = self._gen_trees()

            # Flower dot positions (seeded)
            self._flowers = self._gen_flowers()

            # Pre-rendered lane tile with dither texture
            self._lane_tile = self._make_lane_tile()

            # Pre-rendered headlight cone
            self._headlight_surf = self._make_headlight()

            # Atmospheric dust motes
            self._dust = AmbientParticles(60)
            self._dust_timer = 0

            # VFX post-processing
            self._vfx = VFXState(enable_scanlines=True)

        # --- V3 Midnight Neon Rain Upgrades ---
        if tier >= 3:
            from core.vfx import (
                make_multi_gradient, NEONRAIN_PALETTE, AmbientParticles, VFXState,
            )
            self._neonrain = NEONRAIN_PALETTE

            # Midnight sky (near-black 4-stop)
            self._v3_sky = make_multi_gradient(SCREEN_WIDTH, self.GROUND_Y, [
                (0.0, (2, 2, 6)),
                (0.35, (4, 4, 12)),
                (0.70, (6, 5, 16)),
                (1.0, (8, 6, 18)),
            ])

            # Rain particles (250 cap)
            self._rain = AmbientParticles(250)

            # Neon billboard surfaces (2 pre-baked)
            self._billboards = self._make_billboards()
            self._billboard_flicker = [0, 0]

            # Wet lane reflection tile
            self._wet_lane_tile = self._make_wet_lane_tile()

            # Fog band surfaces (3 layers at different depths)
            self._fog_bands = []
            for i in range(3):
                fog = pygame.Surface((SCREEN_WIDTH, 20), pygame.SRCALPHA)
                a = 25 - i * 6
                fog.fill((10, 10, 25, max(8, a)))
                self._fog_bands.append({'surf': fog, 'y': 120 + i * 50, 'speed': 0.1 + i * 0.05})

            # Puddle ripple states
            self._puddles = []
            p_rng = random.Random(99)
            for _ in range(8):
                self._puddles.append({
                    'x': p_rng.randint(50, SCREEN_WIDTH - 50),
                    'lane': p_rng.randint(0, 2),
                    'phase': p_rng.uniform(0, math.pi * 2),
                    'size': p_rng.randint(8, 16),
                })

            # Override VFX with V3 tier + blue tone
            self._vfx = VFXState(enable_scanlines=False, tier=3,
                                 tone_color=(20, 30, 80))

    def _gen_mountains(self, num_peaks, min_h, max_h, seed=0):
        rng = random.Random(seed)
        points = []
        x = 0
        while x < SCREEN_WIDTH * 3:
            h = rng.randint(min_h, max_h)
            w = rng.randint(60, 140)
            points.append((x, h, w))
            x += w * 0.7
        return points

    def _gen_grass_tufts(self):
        """Small grass triangle positions for V2+."""
        rng = random.Random(55)
        tufts = []
        for _ in range(40):
            tufts.append((
                rng.randint(0, SCREEN_WIDTH),
                rng.randint(-10, 5),  # offset from terrain line
                rng.randint(3, 7),    # height
                rng.choice([(50, 110, 35), (35, 80, 25), (60, 100, 30)]),
            ))
        return tufts

    def _gen_clouds(self, count, color, seed=0):
        """Pre-generate cloud surfaces at init (3-5 ellipses per cloud)."""
        rng = random.Random(seed)
        clouds = []
        for _ in range(count):
            w = rng.randint(80, 200)
            h = rng.randint(25, 50)
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            # 3-5 overlapping ellipses
            num_blobs = rng.randint(3, 5)
            for _ in range(num_blobs):
                bx = rng.randint(0, w - 30)
                by = rng.randint(0, h - 15)
                bw = rng.randint(30, min(w - bx, 80))
                bh = rng.randint(12, min(h - by, 30))
                pygame.draw.ellipse(surf, color, (bx, by, bw, bh))
            x_pos = rng.randint(0, SCREEN_WIDTH)
            y_pos = rng.randint(30, self.GROUND_Y - 80)
            clouds.append((surf, x_pos, y_pos))
        return clouds

    def _gen_trees(self):
        """Pre-render 6 tree silhouette surfaces."""
        rng = random.Random(66)
        trees = []
        for _ in range(6):
            w, h = 20, 30
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            tree_color = rng.choice([(30, 60, 25), (25, 50, 20), (35, 70, 30)])
            # Trunk
            pygame.draw.rect(surf, (40, 30, 20), (8, 18, 4, 12))
            # Canopy (triangle or circle)
            if rng.random() < 0.5:
                pygame.draw.polygon(surf, tree_color, [(10, 2), (2, 20), (18, 20)])
            else:
                pygame.draw.circle(surf, tree_color, (10, 12), 9)
            x_offset = rng.randint(0, SCREEN_WIDTH)
            trees.append((surf, x_offset))
        return trees

    def _gen_flowers(self):
        """Pre-generate flower positions for terrain decoration."""
        rng = random.Random(77)
        flowers = []
        for _ in range(30):
            flowers.append((
                rng.randint(0, SCREEN_WIDTH),
                rng.randint(-5, 3),
                rng.choice([(220, 60, 60), (220, 180, 40), (180, 60, 200), (255, 255, 100)]),
            ))
        return flowers

    def _make_lane_tile(self):
        """Pre-render 800x55 lane tile with subtle dither texture."""
        from core.vfx import make_dither_overlay
        tile = pygame.Surface((SCREEN_WIDTH, self.LANE_HEIGHT))
        tile.fill(ROAD_DARK)
        dither = make_dither_overlay(SCREEN_WIDTH, self.LANE_HEIGHT, strength=10)
        tile.blit(dither, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        return tile

    def _make_headlight(self):
        """Pre-render headlight cone (120x200 gradient, SRCALPHA)."""
        w, h = 120, 200
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx = w // 2
        # Cone from bottom center expanding upward-right
        for y in range(h):
            t = y / h  # 0=top (far), 1=bottom (player)
            spread = int(cx * (1 - t * 0.7))
            alpha = int(35 * (1 - t))
            if spread > 0 and alpha > 0:
                pygame.draw.line(surf, (255, 240, 200, alpha),
                                 (cx - spread, y), (cx + spread, y))
        return surf

    def _make_billboards(self):
        """Pre-bake 2 neon billboard surfaces."""
        boards = []
        colors = [(0, 255, 220), (255, 0, 180)]
        texts = ["NEON", "RUSH"]
        for i, (color, text) in enumerate(zip(colors, texts)):
            w, h = 80, 35
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            # Dark backing
            pygame.draw.rect(surf, (10, 10, 20, 200), (0, 0, w, h))
            # Neon border
            pygame.draw.rect(surf, (*color, 200), (0, 0, w, h), 2)
            # Glow border
            pygame.draw.rect(surf, (*color, 60), (-2, -2, w + 4, h + 4), 4)
            # Text (simple horizontal lines as pseudo-text)
            for cy in range(8, h - 8, 5):
                lw = random.Random(i * 100 + cy).randint(20, w - 20)
                lx = (w - lw) // 2
                pygame.draw.line(surf, color, (lx, cy), (lx + lw, cy), 2)
            boards.append({'surf': surf, 'x': 120 + i * 500, 'y': 80 + i * 40})
        return boards

    def _make_wet_lane_tile(self):
        """Pre-render wet lane tile with neon color smears."""
        tile = pygame.Surface((SCREEN_WIDTH, self.LANE_HEIGHT), pygame.SRCALPHA)
        tile.fill((30, 35, 50))
        # Neon reflection smears
        rng = random.Random(42)
        for _ in range(30):
            x = rng.randint(0, SCREEN_WIDTH)
            w = rng.randint(20, 80)
            color = rng.choice([(0, 255, 220, 15), (255, 0, 180, 12), (0, 180, 255, 10)])
            pygame.draw.line(tile, color, (x, rng.randint(5, self.LANE_HEIGHT - 5)),
                             (x + w, rng.randint(5, self.LANE_HEIGHT - 5)), 2)
        return tile

    def get_hill_y(self, x):
        """Get ground height at position x (for physics)."""
        # Sine-sum terrain
        base = self.GROUND_Y
        h = 0
        h += 20 * math.sin((x + self.scroll_x) * 0.008)
        h += 12 * math.sin((x + self.scroll_x) * 0.015 + 1.5)
        h += 8 * math.sin((x + self.scroll_x) * 0.025 + 3.0)
        return base - h

    def get_lane_y(self, lane_idx):
        """Get the Y position for a lane (0-2)."""
        if 0 <= lane_idx < len(self.LANE_Y):
            return self.LANE_Y[lane_idx]
        return self.LANE_Y[1]

    def _draw_snow_caps(self, screen):
        """Draw white snow lines along top 15% of far mountain peaks."""
        offset = int(self.mountain_scroll * 0.4) % (SCREEN_WIDTH * 3)
        for px, ph, pw in self.mountains_far:
            sx = px - offset
            if sx + pw < -100 or sx > SCREEN_WIDTH + 100:
                continue
            peak_y = 180 - ph
            cap_h = int(ph * 0.15)
            # Snow highlight along peak ridge
            p1 = (sx + pw // 3, peak_y)
            p2 = (sx + pw * 2 // 3, int(peak_y + ph * 0.3))
            pygame.draw.line(screen, (200, 200, 220, 120), p1, p2, 2)

    def _draw_v2_terrain_detail(self, screen):
        """V2+ grass tufts, flowers, and tree silhouettes."""
        tuft_offset = int(self.scroll_x * 0.6) % SCREEN_WIDTH
        # Grass tufts (arcs)
        for tx, ty_off, th, tc in self._grass_tufts:
            sx = (tx - tuft_offset) % SCREEN_WIDTH
            base_y = self.get_hill_y(sx)
            tip_y = int(base_y) + ty_off - th
            # Curved grass blade via arc
            rect = pygame.Rect(sx - 4, tip_y, 8, int(base_y) + ty_off - tip_y)
            if rect.height > 2 and rect.width > 2:
                pygame.draw.arc(screen, tc, rect, 0, math.pi, 2)

        # Flower dots
        if hasattr(self, '_flowers'):
            for fx, fy_off, fc in self._flowers:
                sx = (fx - tuft_offset) % SCREEN_WIDTH
                base_y = self.get_hill_y(sx)
                pygame.draw.circle(screen, fc, (sx, int(base_y) + fy_off), 2)

        # Tree silhouettes
        if hasattr(self, '_trees'):
            tree_offset = int(self.scroll_x * 0.4) % SCREEN_WIDTH
            for surf, tx in self._trees:
                sx = (tx - tree_offset) % SCREEN_WIDTH
                base_y = self.get_hill_y(sx)
                screen.blit(surf, (sx - 10, int(base_y) - 28))

    def _draw_v2_lane_features(self, screen):
        """V2+ lane textures, neon border glow, and headlight cone."""
        pulse = math.sin(self.scroll_x * 0.015)

        # Neon glow on each lane boundary (expanded)
        for i in range(len(self.LANE_Y) + 1):
            if i == 0:
                ly = self.LANE_Y[0]
                color = NEON_CYAN
            elif i == len(self.LANE_Y):
                ly = self.LANE_Y[-1] + self.LANE_HEIGHT
                color = NEON_MAGENTA
            else:
                ly = self.LANE_Y[i]
                color = NEON_CYAN if i % 2 == 0 else NEON_MAGENTA

            glow_w = int(2 + 2 * (0.5 + 0.5 * pulse))
            glow_a = int(60 + 40 * (0.5 + 0.5 * pulse))
            glow_surf = pygame.Surface((SCREEN_WIDTH, max(1, glow_w)), pygame.SRCALPHA)
            glow_surf.fill((*color[:3], glow_a))
            screen.blit(glow_surf, (0, ly - glow_w // 2))

        # Headlight cone at player position (fixed at x=150)
        if hasattr(self, '_headlight_surf'):
            screen.blit(self._headlight_surf, (90, self.LANE_Y[0] - 120),
                         special_flags=pygame.BLEND_RGB_ADD)

    def update_and_draw(self, speed, screen):
        self.scroll_x += speed
        self.mountain_scroll += speed * 0.3
        self._tick += 1

        if self.tier >= 3 and hasattr(self, '_v3_sky'):
            self._draw_v3(speed, screen)
            return

        # Sky gradient
        if self.tier >= 2 and hasattr(self, '_sky_gradient'):
            screen.blit(self._sky_gradient, (0, 0))
            screen.blit(self._sky_dither, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        else:
            for y in range(self.GROUND_Y):
                t = y / self.GROUND_Y
                r = int(SKY_TOP[0] + (SKY_BOTTOM[0] - SKY_TOP[0]) * t)
                g = int(SKY_TOP[1] + (SKY_BOTTOM[1] - SKY_TOP[1]) * t)
                b = int(SKY_TOP[2] + (SKY_BOTTOM[2] - SKY_TOP[2]) * t)
                pygame.draw.line(screen, (r, g, b), (0, y), (SCREEN_WIDTH, y))

        # V2+: Far cloud layer
        if self.tier >= 2 and hasattr(self, '_clouds_far'):
            cloud_offset_far = int(self.mountain_scroll * 0.1) % SCREEN_WIDTH
            for surf, cx, cy in self._clouds_far:
                bx = (cx - cloud_offset_far) % (SCREEN_WIDTH + surf.get_width()) - surf.get_width()
                screen.blit(surf, (bx, cy))

        # V2+: Deep mountain layer
        if self.tier >= 2:
            MOUNTAIN_DEEP = (35, 22, 50)
            self._draw_mountains(screen, self.mountains_deep, MOUNTAIN_DEEP,
                                 self.mountain_scroll * 0.2, 220)

        # Far mountains
        self._draw_mountains(screen, self.mountains_far, MOUNTAIN_FAR,
                             self.mountain_scroll * 0.4, 180)

        # V2+: Atmospheric fog band
        if self.tier >= 2:
            fog_alpha = int(20 + 10 * math.sin(self._tick * 0.01))
            fog = pygame.Surface((SCREEN_WIDTH, 30), pygame.SRCALPHA)
            fog.fill((60, 40, 80, fog_alpha))
            screen.blit(fog, (0, 165))

        # Near mountains
        self._draw_mountains(screen, self.mountains_near, MOUNTAIN_NEAR,
                             self.mountain_scroll * 0.8, self.GROUND_Y - 20)

        # V2+: Snow caps
        if self.tier >= 2:
            self._draw_snow_caps(screen)

        # V2+: Near cloud layer
        if self.tier >= 2 and hasattr(self, '_clouds_near'):
            cloud_offset_near = int(self.mountain_scroll * 0.3) % SCREEN_WIDTH
            for surf, cx, cy in self._clouds_near:
                bx = (cx - cloud_offset_near) % (SCREEN_WIDTH + surf.get_width()) - surf.get_width()
                screen.blit(surf, (bx, min(cy, self.GROUND_Y - 60)))

        # Ground
        pygame.draw.rect(screen, GROUND_COLOR,
                         (0, self.GROUND_Y, SCREEN_WIDTH, SCREEN_HEIGHT - self.GROUND_Y))

        # Draw terrain hills
        self._draw_terrain(screen)

        # V2+: Terrain decoration
        if self.tier >= 2:
            self._draw_v2_terrain_detail(screen)

        # Draw lanes
        self._draw_lanes(screen)

        # V2+: Enhanced lane features
        if self.tier >= 2:
            self._draw_v2_lane_features(screen)

        # V2+: Atmospheric dust motes
        if self.tier >= 2 and hasattr(self, '_dust'):
            self._dust_timer += 1
            if self._dust_timer >= 6:
                self._dust_timer = 0
                for _ in range(2):
                    x = random.randint(0, SCREEN_WIDTH)
                    y = random.randint(self.LANE_Y[0] - 40, self.LANE_Y[-1] + self.LANE_HEIGHT)
                    color = random.choice([(200, 200, 220), (180, 180, 200), (220, 210, 190)])
                    vx = random.uniform(-0.5, -0.2)
                    vy = random.uniform(-0.3, 0.3)
                    self._dust.spawn(x, y, vx, vy, random.randint(80, 160), color, size=1)
            self._dust.update()
            self._dust.draw(screen)

        # V2+ post-processing
        if self.tier >= 2 and hasattr(self, '_vfx'):
            self._vfx.update()
            self._vfx.draw_post(screen)

    def _draw_v3(self, speed, screen):
        """Full V3: midnight sky, fog, rain, neon billboards, wet lanes, puddles."""
        # Midnight sky
        screen.blit(self._v3_sky, (0, 0))

        # Fog bands at parallax depths (replaces mountains — hidden in fog)
        for fb in self._fog_bands:
            ox = int(self.mountain_scroll * fb['speed']) % 40
            screen.blit(fb['surf'], (-ox, fb['y']))

        # Neon billboards with periodic flicker
        for i, bb in enumerate(self._billboards):
            scroll_x = int(self.scroll_x * 0.15) % (SCREEN_WIDTH + 100)
            bx = (bb['x'] - scroll_x) % (SCREEN_WIDTH + 100) - 50
            # Flicker: briefly dim every ~120 frames
            self._billboard_flicker[i] = max(0, self._billboard_flicker[i] - 1)
            if random.random() < 0.008:
                self._billboard_flicker[i] = random.randint(3, 8)
            if self._billboard_flicker[i] <= 0:
                screen.blit(bb['surf'], (bx, bb['y']))
            else:
                # Dimmed version
                dim = bb['surf'].copy()
                dim.set_alpha(80)
                screen.blit(dim, (bx, bb['y']))

        # Dark ground
        pygame.draw.rect(screen, (8, 8, 14),
                         (0, self.GROUND_Y, SCREEN_WIDTH, SCREEN_HEIGHT - self.GROUND_Y))

        # Minimal terrain (dark outline only, no grass fill)
        points = [(0, SCREEN_HEIGHT)]
        for x in range(0, SCREEN_WIDTH + 4, 4):
            y = self.get_hill_y(x)
            points.append((x, int(y)))
        points.append((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.draw.polygon(screen, (12, 14, 22), points)

        # Wet lane tiles
        for i, ly in enumerate(self.LANE_Y):
            screen.blit(self._wet_lane_tile, (0, ly))
            # Lane borders (dim cyan)
            pygame.draw.line(screen, (0, 100, 120, 120), (0, ly), (SCREEN_WIDTH, ly), 1)
            pygame.draw.line(screen, (0, 100, 120, 120),
                             (0, ly + self.LANE_HEIGHT), (SCREEN_WIDTH, ly + self.LANE_HEIGHT), 1)
            # Dashed center
            dash_offset = int(self.scroll_x * 0.8) % 40
            center_y = ly + self.LANE_HEIGHT // 2
            for dx in range(-40 + dash_offset, SCREEN_WIDTH + 40, 40):
                pygame.draw.line(screen, (60, 70, 90), (dx, center_y), (dx + 20, center_y), 1)

        # Neon edge lines
        pygame.draw.line(screen, NEON_CYAN,
                         (0, self.LANE_Y[0] - 2), (SCREEN_WIDTH, self.LANE_Y[0] - 2), 2)
        pygame.draw.line(screen, NEON_MAGENTA,
                         (0, self.LANE_Y[-1] + self.LANE_HEIGHT + 2),
                         (SCREEN_WIDTH, self.LANE_Y[-1] + self.LANE_HEIGHT + 2), 2)

        # Neon glow on lane boundaries (V3: brighter, blue-shifted)
        pulse = math.sin(self.scroll_x * 0.015)
        for i in range(len(self.LANE_Y) + 1):
            if i == 0:
                ly = self.LANE_Y[0]
            elif i == len(self.LANE_Y):
                ly = self.LANE_Y[-1] + self.LANE_HEIGHT
            else:
                ly = self.LANE_Y[i]
            glow_a = int(40 + 30 * (0.5 + 0.5 * pulse))
            glow_surf = pygame.Surface((SCREEN_WIDTH, 3), pygame.SRCALPHA)
            glow_surf.fill((0, 180, 255, glow_a))
            screen.blit(glow_surf, (0, ly - 1))

        # Puddle ripples (expanding circles, fading alpha)
        for puddle in self._puddles:
            px = (puddle['x'] - int(self.scroll_x * 0.6)) % SCREEN_WIDTH
            py = self.LANE_Y[puddle['lane']] + self.LANE_HEIGHT // 2
            phase = (self._tick * 0.06 + puddle['phase']) % (math.pi * 2)
            r = int(puddle['size'] * (0.3 + 0.7 * abs(math.sin(phase))))
            a = max(20, int(60 * (1 - abs(math.sin(phase)))))
            if r > 2:
                pygame.draw.circle(screen, (40, 60, 120, a), (px, py), r, 1)
                if r > 5:
                    pygame.draw.circle(screen, (60, 80, 140, a // 2), (px, py), r - 3, 1)

        # Rain particles (fast downward, 8-12 per 2 frames)
        if self._tick % 2 == 0:
            for _ in range(random.randint(8, 12)):
                rx = random.randint(0, SCREEN_WIDTH)
                ry = random.randint(-20, 0)
                self._rain.spawn(rx, ry, random.uniform(-0.3, 0.3),
                                 random.uniform(8, 14), random.randint(40, 70),
                                 (160, 180, 255), size=1)
        self._rain.update()
        self._rain.draw(screen)

        # V3 post-processing
        self._vfx.update()
        self._vfx.draw_post(screen)

    def _draw_mountains(self, screen, peaks, color, scroll, base_y):
        offset = int(scroll) % (SCREEN_WIDTH * 3)
        for px, ph, pw in peaks:
            sx = px - offset
            if sx + pw < -100 or sx > SCREEN_WIDTH + 100:
                continue
            points = [
                (sx, base_y),
                (sx + pw // 3, base_y - ph),
                (sx + pw * 2 // 3, base_y - ph * 0.7),
                (sx + pw, base_y),
            ]
            pygame.draw.polygon(screen, color, points)

            # V2+: Mountain gradient highlight (lighter ridge)
            if self.tier >= 2:
                highlight = tuple(min(255, c + 20) for c in color)
                ridge_pts = [
                    (sx + pw // 3, base_y - ph),
                    (sx + pw * 2 // 3, base_y - ph * 0.7),
                    (sx + pw // 2, base_y - ph * 0.5),
                ]
                if len(ridge_pts) >= 3:
                    pygame.draw.polygon(screen, highlight, ridge_pts)

    def _draw_terrain(self, screen):
        """Draw sine-wave terrain along the ground line."""
        points = [(0, SCREEN_HEIGHT)]
        for x in range(0, SCREEN_WIDTH + 4, 4):
            y = self.get_hill_y(x)
            points.append((x, int(y)))
        points.append((SCREEN_WIDTH, SCREEN_HEIGHT))

        # Grass on top of terrain
        pygame.draw.polygon(screen, GRASS_GREEN, points)

        # Terrain outline
        terrain_line = points[1:-1]
        if len(terrain_line) > 1:
            pygame.draw.lines(screen, (60, 120, 40), False, terrain_line, 2)

    def _draw_lanes(self, screen):
        """Draw 3 racing lanes."""
        for i, ly in enumerate(self.LANE_Y):
            # V2+: Use pre-rendered lane tile with dither texture
            if self.tier >= 2 and hasattr(self, '_lane_tile'):
                # Alternate dark/light by tinting
                if i % 2 == 0:
                    screen.blit(self._lane_tile, (0, ly))
                else:
                    # Lighter variant — just draw light color then overlay dither
                    pygame.draw.rect(screen, ROAD_LIGHT,
                                     (0, ly, SCREEN_WIDTH, self.LANE_HEIGHT))
                    from core.vfx import make_dither_overlay
                    # Use cached tile approach: blit with offset
                    screen.blit(self._lane_tile, (0, ly),
                                special_flags=pygame.BLEND_RGB_ADD)
            else:
                # V1: flat color
                color = ROAD_DARK if i % 2 == 0 else ROAD_LIGHT
                pygame.draw.rect(screen, color,
                                 (0, ly, SCREEN_WIDTH, self.LANE_HEIGHT))

            # Lane borders
            pygame.draw.line(screen, LANE_LINE, (0, ly), (SCREEN_WIDTH, ly), 1)
            pygame.draw.line(screen, LANE_LINE, (0, ly + self.LANE_HEIGHT),
                             (SCREEN_WIDTH, ly + self.LANE_HEIGHT), 1)

            # Dashed center line
            dash_offset = int(self.scroll_x * 0.8) % 40
            center_y = ly + self.LANE_HEIGHT // 2
            for dx in range(-40 + dash_offset, SCREEN_WIDTH + 40, 40):
                pygame.draw.line(screen, (*LANE_LINE, 120), (dx, center_y),
                                 (dx + 20, center_y), 1)

        # Neon edge lines
        pygame.draw.line(screen, NEON_CYAN,
                         (0, self.LANE_Y[0] - 2), (SCREEN_WIDTH, self.LANE_Y[0] - 2), 2)
        pygame.draw.line(screen, NEON_MAGENTA,
                         (0, self.LANE_Y[-1] + self.LANE_HEIGHT + 2),
                         (SCREEN_WIDTH, self.LANE_Y[-1] + self.LANE_HEIGHT + 2), 2)
