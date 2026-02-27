"""Asteroid sprite — shootable obstacles for the asteroid phase."""
import pygame
import random
import math

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    ASTEROID_GRAY, ASTEROID_GLOW, SOLAR_YELLOW, SOLAR_WHITE,
)

# Direction constants
DIR_DOWN = "down"    # Desert / Micro Machines (vertical scroll)
DIR_LEFT = "left"    # Excitebike (horizontal scroll)

# Size configs: (name, hp, bolts_to_kill, points, radius)
SIZES = {
    "small":  {"hp": 15, "bolts": 1, "pts": 100, "radius": 14},
    "medium": {"hp": 30, "bolts": 2, "pts": 250, "radius": 22},
    "large":  {"hp": 45, "bolts": 3, "pts": 500, "radius": 32},
}


def _pick_size():
    """Weighted random: 50% small, 35% medium, 15% large."""
    r = random.random()
    if r < 0.50:
        return "small"
    elif r < 0.85:
        return "medium"
    return "large"


class Asteroid(pygame.sprite.Sprite):
    """Procedural asteroid with irregular polygon, glow, cracks, and HP dots."""

    def __init__(self, x, y, direction=DIR_DOWN, size=None):
        super().__init__()
        self.size_name = size or _pick_size()
        cfg = SIZES[self.size_name]
        self.hp = cfg["hp"]
        self.max_hp = cfg["hp"]
        self.bolts_needed = cfg["bolts"]
        self.points = cfg["pts"]
        self.base_radius = cfg["radius"]
        self.direction = direction

        # Movement
        if direction == DIR_DOWN:
            self.vx = random.uniform(-0.3, 0.3)
            self.vy = random.uniform(1.5, 3.5)
        else:  # DIR_LEFT
            self.vx = random.uniform(-3.5, -1.5)
            self.vy = random.uniform(-0.3, 0.3)

        # Rotation / wobble
        self.angle = random.uniform(0, 360)
        self.spin_speed = random.uniform(-2.0, 2.0)
        self.wobble_phase = random.uniform(0, math.pi * 2)
        self.wobble_amp = random.uniform(0.2, 0.8)

        # Generate procedural shape (offscreen-safe bounding)
        self.num_verts = random.randint(7, 12)
        self.vert_radii = []
        for _ in range(self.num_verts):
            variation = random.uniform(0.7, 1.3)
            self.vert_radii.append(self.base_radius * variation)

        # Crack lines (cosmetic detail)
        self.cracks = []
        num_cracks = random.randint(1, 3)
        for _ in range(num_cracks):
            a1 = random.uniform(0, math.pi * 2)
            a2 = a1 + random.uniform(-0.8, 0.8)
            r1 = random.uniform(0.2, 0.6) * self.base_radius
            r2 = random.uniform(0.5, 0.9) * self.base_radius
            self.cracks.append((a1, r1, a2, r2))

        # Build initial surface
        self._build_surface()
        self.rect = self.image.get_rect(center=(x, y))
        self.fx, self.fy = float(x), float(y)

    def _build_surface(self):
        """Render the asteroid polygon with glow + cracks + HP dots."""
        pad = 6
        size = (self.base_radius + pad) * 2
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2

        # Compute rotated polygon vertices
        points = []
        for i in range(self.num_verts):
            a = (2 * math.pi * i / self.num_verts) + math.radians(self.angle)
            r = self.vert_radii[i]
            points.append((cx + r * math.cos(a), cy + r * math.sin(a)))

        # Glow layer (larger, translucent)
        glow_points = []
        for i in range(self.num_verts):
            a = (2 * math.pi * i / self.num_verts) + math.radians(self.angle)
            r = self.vert_radii[i] + 3
            glow_points.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        pygame.draw.polygon(self.image, (*ASTEROID_GLOW, 60), glow_points)

        # Main body
        pygame.draw.polygon(self.image, ASTEROID_GRAY, points)
        pygame.draw.polygon(self.image, ASTEROID_GLOW, points, 2)

        # Crack detail lines
        for a1, r1, a2, r2 in self.cracks:
            ra = a1 + math.radians(self.angle)
            rb = a2 + math.radians(self.angle)
            x1 = cx + r1 * math.cos(ra)
            y1 = cy + r1 * math.sin(ra)
            x2 = cx + r2 * math.cos(rb)
            y2 = cy + r2 * math.sin(rb)
            pygame.draw.line(self.image, (*ASTEROID_GLOW, 140), (x1, y1), (x2, y2), 1)

        # HP dots indicator (bottom of sprite)
        bolts_left = max(1, math.ceil(self.hp / 15))
        dot_y = cy + self.base_radius + 2
        total_w = bolts_left * 6
        start_x = cx - total_w // 2
        for i in range(bolts_left):
            color = SOLAR_YELLOW if self.hp > self.max_hp * 0.3 else (255, 60, 60)
            pygame.draw.circle(self.image, color, (int(start_x + i * 6 + 3), int(dot_y)), 2)

    def take_hit(self, damage):
        """Apply damage. Returns True if destroyed."""
        self.hp -= damage
        if self.hp <= 0:
            self.kill()
            return True
        # Rebuild surface to update HP dots
        self._build_surface()
        old_center = self.rect.center
        self.rect = self.image.get_rect(center=old_center)
        return False

    def update(self, scroll_speed):
        """Move + spin + wobble."""
        self.angle += self.spin_speed
        self.wobble_phase += 0.05

        # Base movement
        if self.direction == DIR_DOWN:
            self.fy += self.vy + scroll_speed * 0.5
            self.fx += self.vx + math.sin(self.wobble_phase) * self.wobble_amp
        else:  # DIR_LEFT
            self.fx += self.vx - scroll_speed * 0.5
            self.fy += self.vy + math.sin(self.wobble_phase) * self.wobble_amp

        self.rect.center = (int(self.fx), int(self.fy))

        # Rebuild for rotation
        self._build_surface()
        old_center = self.rect.center
        self.rect = self.image.get_rect(center=old_center)

        # Off-screen kill
        margin = 80
        if (self.rect.top > SCREEN_HEIGHT + margin or
                self.rect.bottom < -margin or
                self.rect.left > SCREEN_WIDTH + margin or
                self.rect.right < -margin):
            self.kill()

    def get_death_particles(self):
        """Return (x, y, colors, count, min_speed, max_speed, life) for ParticleSystem.burst()."""
        count = {"small": 8, "medium": 14, "large": 22}.get(self.size_name, 10)
        return (
            self.rect.centerx, self.rect.centery,
            [ASTEROID_GRAY, ASTEROID_GLOW, SOLAR_YELLOW],
            count, 3, 30, 3,
        )
