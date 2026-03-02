"""New weapon projectile sprites: MultishotBolt, HomingRocket, OrbitOrb."""

import pygame
import math
import random

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, SOLAR_WHITE, SOLAR_YELLOW,
    MULTISHOT_ORANGE, ROCKETS_RED, ORBIT8_PURPLE,
)
from core.sound import play_sfx


class MultishotBolt(pygame.sprite.Sprite):
    """Angled heat bolt for multishot fan. Same as HeatBolt but flies at an angle."""

    def __init__(self, x, y, angle_offset, color=None, direction="up"):
        super().__init__()
        self.image = pygame.Surface((8, 20), pygame.SRCALPHA)
        c = color or MULTISHOT_ORANGE
        pygame.draw.ellipse(self.image, (*c[:3], 200), (0, 0, 8, 20))
        pygame.draw.ellipse(self.image, SOLAR_WHITE, (2, 2, 4, 16))
        self.rect = self.image.get_rect(center=(x, y))
        self.damage = 15
        self.alive = True

        # Calculate velocity based on direction and angle offset
        if direction == "right":
            base_angle = 0.0  # rightward
        elif direction == "up":
            base_angle = -math.pi / 2  # upward
        else:
            base_angle = -math.pi / 2

        angle = base_angle + angle_offset
        speed = 10.0
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed

    def update(self):
        self.rect.x += int(self.vx)
        self.rect.y += int(self.vy)
        if (self.rect.bottom < -20 or self.rect.top > SCREEN_HEIGHT + 20 or
                self.rect.right < -20 or self.rect.left > SCREEN_WIDTH + 20):
            self.alive = False
            self.kill()


class HomingRocket(pygame.sprite.Sprite):
    """Homing rocket that steers toward nearest target."""

    def __init__(self, x, y, color=None):
        super().__init__()
        c = color or ROCKETS_RED
        self.color = c
        self.image = pygame.Surface((12, 24), pygame.SRCALPHA)
        self._draw_rocket()
        self.rect = self.image.get_rect(center=(x, y))
        self.px = float(x)
        self.py = float(y)
        self.angle = -math.pi / 2  # start heading up
        self.speed = 5.0
        self.turn_rate = 0.04
        self.damage = 40
        self.life = 360
        self.alive = True

    def _draw_rocket(self):
        self.image.fill((0, 0, 0, 0))
        c = self.color
        # Rocket body
        pygame.draw.rect(self.image, c, (3, 4, 6, 16))
        # Nose cone
        pygame.draw.polygon(self.image, c, [(6, 0), (2, 6), (10, 6)])
        # Fins
        pygame.draw.polygon(self.image, (*c[:3], 180), [(1, 18), (3, 14), (3, 20)])
        pygame.draw.polygon(self.image, (*c[:3], 180), [(11, 18), (9, 14), (9, 20)])
        # Flame
        flame_colors = [(255, 200, 50), (255, 120, 30), (255, 60, 10)]
        fc = random.choice(flame_colors)
        pygame.draw.ellipse(self.image, (*fc, 200), (4, 19, 4, 5))

    def update(self, targets=None):
        self.life -= 1
        if self.life <= 0:
            self.alive = False
            self.kill()
            return

        # Steer toward nearest target
        if targets:
            nearest = None
            nearest_dist = float('inf')
            for t in targets:
                if not hasattr(t, 'rect'):
                    continue
                dx = t.rect.centerx - self.px
                dy = t.rect.centery - self.py
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest = t

            if nearest:
                dx = nearest.rect.centerx - self.px
                dy = nearest.rect.centery - self.py
                target_angle = math.atan2(dy, dx)
                # Shortest angle difference
                diff = target_angle - self.angle
                while diff > math.pi:
                    diff -= 2 * math.pi
                while diff < -math.pi:
                    diff += 2 * math.pi
                # Clamp turn
                if abs(diff) < self.turn_rate:
                    self.angle = target_angle
                elif diff > 0:
                    self.angle += self.turn_rate
                else:
                    self.angle -= self.turn_rate

        # Move
        self.px += math.cos(self.angle) * self.speed
        self.py += math.sin(self.angle) * self.speed

        # Redraw with rotation
        self._draw_rocket()
        deg = -math.degrees(self.angle) - 90
        rotated = pygame.transform.rotate(self.image, deg)
        self.rect = rotated.get_rect(center=(int(self.px), int(self.py)))
        self.image = rotated

        # Off-screen kill
        margin = 40
        if (self.px < -margin or self.px > SCREEN_WIDTH + margin or
                self.py < -margin or self.py > SCREEN_HEIGHT + margin):
            self.alive = False
            self.kill()


class OrbitOrb(pygame.sprite.Sprite):
    """Glowing orb that orbits player in a figure-8 (lemniscate) pattern."""

    def __init__(self, owner, index, total=8, color=None):
        super().__init__()
        c = color or ORBIT8_PURPLE
        self.color = c
        self.owner = owner
        self.index = index
        self.total = total
        self.phase = (index * 2 * math.pi) / total
        self.t = self.phase
        self.radius = 60
        self.damage = 20
        self.alive = True

        self.image = pygame.Surface((12, 12), pygame.SRCALPHA)
        self._draw_orb()
        self.rect = self.image.get_rect(center=(0, 0))

    def _draw_orb(self):
        self.image.fill((0, 0, 0, 0))
        c = self.color
        # Glow
        pygame.draw.circle(self.image, (*c[:3], 60), (6, 6), 6)
        # Core
        pygame.draw.circle(self.image, c, (6, 6), 4)
        # Bright center
        pygame.draw.circle(self.image, (255, 220, 255), (6, 6), 2)

    def update(self):
        if not self.owner or not self.owner.alive:
            self.alive = False
            self.kill()
            return

        self.t += 0.06

        # Lemniscate of Bernoulli: x = a*cos(t)/(1+sin^2(t)), y = a*sin(t)*cos(t)/(1+sin^2(t))
        sin_t = math.sin(self.t)
        cos_t = math.cos(self.t)
        denom = 1.0 + sin_t * sin_t
        lx = self.radius * cos_t / denom
        ly = self.radius * sin_t * cos_t / denom

        cx = self.owner.rect.centerx + int(lx)
        cy = self.owner.rect.centery + int(ly)
        self.rect.center = (cx, cy)

        # Redraw with slight pulse
        self._draw_orb()
