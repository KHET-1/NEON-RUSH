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
        # Pre-generate mountain silhouettes
        self.mountains_far = self._gen_mountains(20, 80, 150, seed=42)
        self.mountains_near = self._gen_mountains(15, 100, 200, seed=99)

        # V2+ layers
        if tier >= 2:
            self.mountains_deep = self._gen_mountains(25, 40, 90, seed=7)
            self._grass_tufts = self._gen_grass_tufts()

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

    def update_and_draw(self, speed, screen):
        self.scroll_x += speed
        self.mountain_scroll += speed * 0.3

        # Sky gradient
        for y in range(self.GROUND_Y):
            t = y / self.GROUND_Y
            r = int(SKY_TOP[0] + (SKY_BOTTOM[0] - SKY_TOP[0]) * t)
            g = int(SKY_TOP[1] + (SKY_BOTTOM[1] - SKY_TOP[1]) * t)
            b = int(SKY_TOP[2] + (SKY_BOTTOM[2] - SKY_TOP[2]) * t)
            pygame.draw.line(screen, (r, g, b), (0, y), (SCREEN_WIDTH, y))

        # V2+: Deep mountain layer (slowest parallax)
        if self.tier >= 2:
            MOUNTAIN_DEEP = (35, 22, 50)
            self._draw_mountains(screen, self.mountains_deep, MOUNTAIN_DEEP,
                                 self.mountain_scroll * 0.2, 220)

        # Far mountains (parallax 0.2x)
        self._draw_mountains(screen, self.mountains_far, MOUNTAIN_FAR,
                             self.mountain_scroll * 0.4, 180)

        # Near mountains (parallax 0.5x)
        self._draw_mountains(screen, self.mountains_near, MOUNTAIN_NEAR,
                             self.mountain_scroll * 0.8, self.GROUND_Y - 20)

        # Ground
        pygame.draw.rect(screen, GROUND_COLOR, (0, self.GROUND_Y, SCREEN_WIDTH, SCREEN_HEIGHT - self.GROUND_Y))

        # Draw terrain hills
        self._draw_terrain(screen)

        # V2+: Grass tufts along terrain line
        if self.tier >= 2:
            tuft_offset = int(self.scroll_x * 0.6) % SCREEN_WIDTH
            for tx, ty_off, th, tc in self._grass_tufts:
                sx = (tx - tuft_offset) % SCREEN_WIDTH
                base_y = self.get_hill_y(sx)
                tip_y = int(base_y) + ty_off - th
                pygame.draw.polygon(screen, tc, [
                    (sx - 3, int(base_y) + ty_off),
                    (sx, tip_y),
                    (sx + 3, int(base_y) + ty_off),
                ])

        # Draw lanes
        self._draw_lanes(screen)

        # V2+: Neon glow on lane edges
        if self.tier >= 2:
            glow_surf = pygame.Surface((SCREEN_WIDTH, 4), pygame.SRCALPHA)
            glow_alpha = int(40 + 20 * math.sin(self.scroll_x * 0.01))
            glow_surf.fill((*NEON_CYAN[:3], glow_alpha))
            for ly in self.LANE_Y:
                screen.blit(glow_surf, (0, ly - 2))
                screen.blit(glow_surf, (0, ly + self.LANE_HEIGHT - 2))

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
            # Lane background
            color = ROAD_DARK if i % 2 == 0 else ROAD_LIGHT
            pygame.draw.rect(screen, color, (0, ly, SCREEN_WIDTH, self.LANE_HEIGHT))

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
