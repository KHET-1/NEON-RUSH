"""Asteroid sprite — shootable obstacles for the asteroid phase."""
import pygame
import random
import math

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    ASTEROID_GRAY, ASTEROID_GLOW, SOLAR_YELLOW, SOLAR_WHITE,
)
from sprites.road_sprite import RoadSpriteMixin

# Direction constants
DIR_DOWN = "down"    # Desert / Micro Machines (vertical scroll)
DIR_LEFT = "left"    # Excitebike (horizontal scroll)

# Size configs: (name, hp, bolts_to_kill, points, radius)
SIZES = {
    "small":  {"hp": 15, "bolts": 1, "pts": 100, "radius": 14},
    "medium": {"hp": 30, "bolts": 2, "pts": 250, "radius": 22},
    "large":  {"hp": 45, "bolts": 3, "pts": 500, "radius": 32},
}

# Fragment chain: what each size splits into on destruction
FRAGMENT_CHAIN = {
    "large":  ("medium", 2),
    "medium": ("small", 2),
    "small":  None,          # terminal — dies for good
}


def _pick_size():
    """Weighted random: 50% small, 35% medium, 15% large."""
    r = random.random()
    if r < 0.50:
        return "small"
    elif r < 0.85:
        return "medium"
    return "large"


class Asteroid(RoadSpriteMixin, pygame.sprite.Sprite):
    """Procedural asteroid with irregular polygon, glow, cracks, and HP dots."""

    def __init__(self, x, y, direction=DIR_DOWN, size=None, tier=1, lane_offset=None):
        super().__init__()
        self.size_name = size or _pick_size()
        cfg = SIZES[self.size_name]
        self.hp = cfg["hp"]
        self.max_hp = cfg["hp"]
        self.bolts_needed = cfg["bolts"]
        self.points = cfg["pts"]
        self.base_radius = cfg["radius"]
        self.direction = direction

        # Movement — smaller = faster, larger = slower (scenic drift)
        speed_mult = {"large": 0.4, "medium": 0.7, "small": 1.0}[self.size_name]
        if direction == DIR_DOWN:
            self.vx = random.uniform(-0.12, 0.12) * speed_mult
            self.vy = random.uniform(0.4, 0.9) * speed_mult
        else:  # DIR_LEFT
            self.vx = random.uniform(-0.9, -0.4) * speed_mult
            self.vy = random.uniform(-0.12, 0.12) * speed_mult

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

        self.tier = tier

        # Build initial surface
        self._build_surface()
        self.rect = self.image.get_rect(center=(x, y))
        self.fx, self.fy = float(x), float(y)

        if tier >= 2 and direction == DIR_DOWN and lane_offset is not None:
            self.rect.center = (-999, -999)
            self.init_road(world_z=800.0, lane_offset=lane_offset)

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
        """Apply damage. Returns dict with fragment info if destroyed, False if alive.
        Dict is truthy so `if destroyed:` still works."""
        self.hp -= damage
        if self.hp <= 0:
            chain = FRAGMENT_CHAIN.get(self.size_name)
            result = {
                'terminal': chain is None,
                'fragments': self._get_fragment_info() if chain else [],
            }
            self.kill()
            return result
        # Rebuild surface to update HP dots
        self._build_surface()
        old_center = self.rect.center
        self.rect = self.image.get_rect(center=old_center)
        return False

    def _get_fragment_info(self):
        """Compute spawn info for child fragments."""
        chain = FRAGMENT_CHAIN.get(self.size_name)
        if not chain:
            return []
        child_size, count = chain
        cx, cy = self.rect.center
        spread = self.base_radius * 0.6
        fragments = []
        for i in range(count):
            # Fan children outward from parent center
            sign = -1 if i == 0 else 1
            if self.direction == DIR_DOWN:
                fx = cx + sign * spread
                fy = cy
                child_vx = self.vx + sign * random.uniform(0.3, 0.6)
                child_vy = self.vy * 1.1
            else:  # DIR_LEFT
                fx = cx
                fy = cy + sign * spread
                child_vx = self.vx * 1.1
                child_vy = self.vy + sign * random.uniform(0.3, 0.6)
            fragments.append({
                'size': child_size,
                'x': fx, 'y': fy,
                'vx': child_vx, 'vy': child_vy,
                'direction': self.direction,
                'tier': self.tier,
                'lane_offset': getattr(self, 'lane_offset', None),
            })
        return fragments

    @classmethod
    def spawn_fragment(cls, info):
        """Create a child asteroid from fragment info dict."""
        ast = cls(info['x'], info['y'],
                  direction=info['direction'],
                  size=info['size'],
                  tier=info.get('tier', 1),
                  lane_offset=info.get('lane_offset'))
        # Override velocity with inherited + spread values
        ast.vx = info['vx']
        ast.vy = info['vy']
        # Faster spin for fragments
        ast.spin_speed = random.uniform(-4.0, 4.0)
        return ast

    def get_split_particles(self):
        """Smaller particle burst for splitting (not terminal death)."""
        count = {"large": 10, "medium": 7, "small": 5}.get(self.size_name, 6)
        return (
            self.rect.centerx, self.rect.centery,
            [ASTEROID_GRAY, SOLAR_YELLOW, (255, 180, 80)],
            count, 2, 20, 2,
        )

    def update(self, scroll_speed, road_geometry=None):
        """Move + spin + wobble."""
        self.angle += self.spin_speed
        self.wobble_phase += 0.05

        if self.tier >= 2 and road_geometry and self.direction == DIR_DOWN and hasattr(self, 'world_z'):
            # Perspective mode: use road sprite projection
            self.advance_toward_camera(scroll_speed * 0.5 + self.vy)
            self._build_surface()
            self._original_image = self.image.copy()
            if not self.project(road_geometry):
                self.kill()
            return

        # Classic movement
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
