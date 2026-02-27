import pygame
import random
import math

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, NEON_MAGENTA, SAND_YELLOW,
    SOLAR_YELLOW, SOLAR_WHITE, COIN_GOLD, ROAD_LEFT, ROAD_RIGHT,
    POWERUP_SHIELD, POWERUP_MAGNET, POWERUP_SLOWMO,
    POWERUP_NUKE, POWERUP_PHASE, POWERUP_SURGE,
    POWERUP_COLORS, POWERUP_LABELS, POWERUP_ALL, WHITE,
    NUKE_ORANGE, PHASE_CYAN, SURGE_PINK,
)
import core.fonts as _fonts


class Obstacle(pygame.sprite.Sprite):
    def __init__(self, difficulty=1.0):
        super().__init__()
        size = random.choice([28, 36, 44])
        self.size = size
        self.image = pygame.Surface((size + 6, size + 6), pygame.SRCALPHA)
        self._draw()
        self.rect = self.image.get_rect(center=(random.randint(ROAD_LEFT + 20, ROAD_RIGHT - 20), -40))
        self.speed = random.uniform(2, 4) * difficulty
        self.pulse = random.randint(0, 100)

    def _draw(self):
        self.image.fill((0, 0, 0, 0))
        s, cx = self.size, (self.size + 6) // 2
        pts = [(cx, 6), (cx + s // 2 - 4, cx), (cx, s - 2), (cx - s // 2 + 4, cx)]
        for i in range(2, 0, -1):
            scale = 0.9 + i * 0.15
            outer = [(cx + (p[0] - cx) * scale, cx + (p[1] - cx) * scale) for p in pts]
            pygame.draw.polygon(self.image, (*NEON_MAGENTA, 20 + i * 8), outer)
        pygame.draw.polygon(self.image, (180, 90, 25), pts)
        pygame.draw.polygon(self.image, SAND_YELLOW, pts, 2)
        pygame.draw.lines(self.image, NEON_MAGENTA, True, pts, 1)

    def update(self, scroll_speed):
        self.rect.y += scroll_speed + self.speed
        if self.rect.y > SCREEN_HEIGHT + 50:
            self.kill()


class Coin(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.pulse = random.randint(0, 60)
        self.image = pygame.Surface((28, 28), pygame.SRCALPHA)
        self._draw()
        self.rect = self.image.get_rect(center=(random.randint(ROAD_LEFT + 30, ROAD_RIGHT - 30), -20))
        self.base_speed = 2

    def _draw(self):
        self.image.fill((0, 0, 0, 0))
        p = 0.75 + 0.25 * math.sin(self.pulse * 0.12)
        cx, cy = 14, 14
        pygame.draw.circle(self.image, (*COIN_GOLD, int(60 * p)), (cx, cy), 13)
        pygame.draw.circle(self.image, COIN_GOLD, (cx, cy), 9)
        pygame.draw.circle(self.image, (255, 245, 180), (cx, cy), 5)
        pygame.draw.circle(self.image, (255, 230, 100), (cx, cy), 9, 1)

    def update(self, scroll_speed, players=None):
        self.pulse += 1
        self._draw()
        self.rect.y += scroll_speed + self.base_speed
        if players:
            for p in players:
                if p.alive and p.magnet:
                    dx = p.rect.centerx - self.rect.centerx
                    dy = p.rect.centery - self.rect.centery
                    dist = max(1, math.sqrt(dx * dx + dy * dy))
                    if dist < 200:
                        self.rect.x += int(dx / dist * 6)
                        self.rect.y += int(dy / dist * 6)
        if self.rect.y > SCREEN_HEIGHT + 30:
            self.kill()


class PowerUp(pygame.sprite.Sprite):
    def __init__(self, kind=None):
        super().__init__()
        self.kind = kind or random.choice(POWERUP_ALL)
        self.color = POWERUP_COLORS[self.kind]
        self.pulse = random.randint(0, 60)
        self.image = pygame.Surface((38, 38), pygame.SRCALPHA)
        self._draw()
        self.rect = self.image.get_rect(center=(random.randint(ROAD_LEFT + 30, ROAD_RIGHT - 30), -30))

    def _draw(self):
        self.image.fill((0, 0, 0, 0))
        p = 0.65 + 0.35 * math.sin(self.pulse * 0.1)
        cx = 19
        for r, a in [(18, int(45 * p)), (14, 80)]:
            pygame.draw.circle(self.image, (*self.color, a), (cx, cx), r)
        pygame.draw.circle(self.image, self.color, (cx, cx), 12, 2)
        pygame.draw.circle(self.image, (*self.color, 180), (cx, cx), 9)
        label = _fonts.FONT_POWERUP.render(POWERUP_LABELS[self.kind], True, WHITE)
        self.image.blit(label, (cx - label.get_width() // 2, cx - label.get_height() // 2))

    def update(self, scroll_speed):
        self.pulse += 1
        self._draw()
        self.rect.y += scroll_speed + 2
        if self.rect.y > SCREEN_HEIGHT + 30:
            self.kill()


class SolarFlare(pygame.sprite.Sprite):
    # Neon color cycle for the flare glow
    NEON_CYCLE = [
        (255, 255, 0), (255, 200, 0), (255, 150, 50),
        (255, 100, 100), (255, 50, 200), (200, 50, 255),
        (100, 100, 255), (50, 200, 255), (0, 255, 200),
        (50, 255, 100), (150, 255, 50), (255, 255, 0),
    ]

    def __init__(self, particles, x):
        super().__init__()
        r = 26
        self.radius = r
        self.pulse = 0
        self.image = pygame.Surface((r * 2 + 24, r * 2 + 24), pygame.SRCALPHA)
        self.rect = pygame.Rect(x - r - 12, -60, (r + 12) * 2, (r + 12) * 2)
        self.active = True
        self.particles = particles
        self.base_speed = 3
        self._redraw()

    def _neon_color(self):
        """Get smoothly cycling neon color."""
        t = (self.pulse * 0.04) % len(self.NEON_CYCLE)
        idx = int(t)
        frac = t - idx
        c1 = self.NEON_CYCLE[idx % len(self.NEON_CYCLE)]
        c2 = self.NEON_CYCLE[(idx + 1) % len(self.NEON_CYCLE)]
        return tuple(int(c1[i] + (c2[i] - c1[i]) * frac) for i in range(3))

    def _redraw(self):
        r = self.radius
        self.image.fill((0, 0, 0, 0))
        cx, cy = r + 12, r + 12
        p = 0.82 + 0.18 * math.sin(self.pulse * 0.12)
        nc = self._neon_color()
        # Outer neon glow rings (color cycling)
        for i in range(4, 0, -1):
            a = int(40 * p * (4 - i) / 4)
            pygame.draw.circle(self.image, (*nc, a), (cx, cy), int(r + i * 6))
        # Inner warm core
        pygame.draw.circle(self.image, (255, 255, 220, int(130 * p)), (cx, cy), r)
        pygame.draw.circle(self.image, (*nc, 200), (cx, cy), r - 4)
        # Bright center
        pygame.draw.circle(self.image, (255, 255, 255, int(180 * p)), (cx, cy), r // 3)

    def update(self, scroll_speed, players):
        if not self.active:
            return
        self.pulse += 1
        self._redraw()
        self.rect.y += scroll_speed + self.base_speed
        if self.rect.y > SCREEN_HEIGHT + 50:
            self.kill()
            return
        # Emit neon-colored trail particles
        if self.pulse % 3 == 0:
            nc = self._neon_color()
            self.particles.emit(
                self.rect.centerx + random.randint(-8, 8),
                self.rect.centery, nc,
                [random.uniform(-1.5, 1.5), random.uniform(-2, 0.5)], 35, 2,
            )
        for player in players:
            if player.alive and self.rect.colliderect(player.rect) and not player.ghost_mode:
                # Expanding particle ring (satisfying burst)
                nc = self._neon_color()
                for angle_i in range(16):
                    a = angle_i * (2 * math.pi / 16)
                    spd = random.uniform(4, 7)
                    vx = math.cos(a) * spd
                    vy = math.sin(a) * spd
                    color = random.choice([nc, SOLAR_YELLOW, SOLAR_WHITE, (255, 150, 50)])
                    self.particles.emit(
                        self.rect.centerx, self.rect.centery, color,
                        [vx, vy], 45, 3)
                player.vel_y = -14
                player.flare_boost_timer = 150
                player.heat = 0
                player.flare_hit = True
                player.score += 200 * getattr(player, 'score_mult', 1)
                from core.sound import SFX
                SFX["powerup"].play()
                self.active = False
                self.kill()
                break
