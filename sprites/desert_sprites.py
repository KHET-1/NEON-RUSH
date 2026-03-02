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
from sprites.road_sprite import RoadSpriteMixin

# World-Z spawn distance for perspective sprites
_Z_FAR = 800.0


class Obstacle(RoadSpriteMixin, pygame.sprite.Sprite):
    def __init__(self, difficulty=1.0, tier=1, lane_offset=None):
        super().__init__()
        size = random.choice([28, 36, 44])
        self.size = size
        self.tier = tier
        self.pulse = random.randint(0, 100)
        self.speed = random.uniform(2, 4) * difficulty
        self.image = pygame.Surface((size + 6, size + 6), pygame.SRCALPHA)
        self._draw()

        if tier >= 2 and lane_offset is not None:
            self.rect = self.image.get_rect(center=(-999, -999))
            self.init_road(world_z=_Z_FAR, lane_offset=lane_offset)
        else:
            self.rect = self.image.get_rect(center=(random.randint(ROAD_LEFT + 20, ROAD_RIGHT - 20), -40))

    def _draw(self):
        self.image.fill((0, 0, 0, 0))
        s, cx = self.size, (self.size + 6) // 2
        pts = [(cx, 6), (cx + s // 2 - 4, cx), (cx, s - 2), (cx - s // 2 + 4, cx)]

        if self.tier >= 3:
            # V3: 6 crimson/amber glow rings, spinning hazard lines
            pulse = 0.6 + 0.4 * math.sin(self.pulse * 0.1)
            for i in range(6, 0, -1):
                scale = 1.0 + i * 0.12
                outer = [(cx + (p[0] - cx) * scale, cx + (p[1] - cx) * scale) for p in pts]
                # Alternate crimson and amber
                gc = (220, 40, 10) if i % 2 == 0 else (255, 140, 30)
                a = int(55 * pulse * (1 - (i - 1) / 6))
                pygame.draw.polygon(self.image, (*gc, max(4, a)), outer)
            # Crimson body
            pygame.draw.polygon(self.image, (200, 30, 10), pts)
            pygame.draw.polygon(self.image, (255, 180, 60), pts, 2)
            # 4 rotating inner lines (spinning hazard)
            spin = self.pulse * 0.15
            for i in range(4):
                a = spin + i * math.pi / 2
                r_inner = s * 0.15
                r_outer = s * 0.38
                x1 = cx + int(math.cos(a) * r_inner)
                y1 = cx + int(math.sin(a) * r_inner)
                x2 = cx + int(math.cos(a) * r_outer)
                y2 = cx + int(math.sin(a) * r_outer)
                pygame.draw.line(self.image, (255, 200, 80), (x1, y1), (x2, y2), 2)
            # Bright center
            pygame.draw.circle(self.image, (255, 240, 180), (cx, cx), 5)
            pygame.draw.circle(self.image, (255, 255, 240), (cx, cx), 2)
        elif self.tier >= 2:
            # V2: 4 warm glow rings with smooth pulsing
            pulse = 0.6 + 0.4 * math.sin(self.pulse * 0.1)
            glow_color = (255, 100, 50)  # warm amber glow (consistent, no clashing)
            for i in range(4, 0, -1):
                scale = 1.0 + i * 0.14
                outer = [(cx + (p[0] - cx) * scale, cx + (p[1] - cx) * scale) for p in pts]
                a = int(50 * pulse * (1 - (i - 1) / 4))  # outer fades, inner bright
                pygame.draw.polygon(self.image, (*glow_color, max(4, a)), outer)
            pygame.draw.polygon(self.image, (180, 90, 25), pts)
            pygame.draw.polygon(self.image, SAND_YELLOW, pts, 2)
            pygame.draw.lines(self.image, NEON_MAGENTA, True, pts, 1)
            # Bright hot center dot
            pygame.draw.circle(self.image, (255, 220, 160), (cx, cx), 3)
            pygame.draw.circle(self.image, WHITE, (cx, cx), 1)
        else:
            for i in range(2, 0, -1):
                scale = 0.9 + i * 0.15
                outer = [(cx + (p[0] - cx) * scale, cx + (p[1] - cx) * scale) for p in pts]
                pygame.draw.polygon(self.image, (*NEON_MAGENTA, 20 + i * 8), outer)
            pygame.draw.polygon(self.image, (180, 90, 25), pts)
            pygame.draw.polygon(self.image, SAND_YELLOW, pts, 2)
            pygame.draw.lines(self.image, NEON_MAGENTA, True, pts, 1)

    def update(self, scroll_speed, road_geometry=None):
        if self.tier >= 2 and road_geometry and hasattr(self, 'world_z'):
            self.advance_toward_camera(scroll_speed + self.speed)
            if not self.project(road_geometry):
                self.kill()
        else:
            self.rect.y += scroll_speed + self.speed
            if self.rect.y > SCREEN_HEIGHT + 50:
                self.kill()


class Coin(RoadSpriteMixin, pygame.sprite.Sprite):
    def __init__(self, tier=1, lane_offset=None):
        super().__init__()
        self.pulse = random.randint(0, 60)
        self.tier = tier
        surf_size = 40 if tier >= 3 else (36 if tier >= 2 else 28)
        self.image = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
        self._surf_size = surf_size
        self._draw()
        self.base_speed = 2

        if tier >= 2 and lane_offset is not None:
            self.rect = self.image.get_rect(center=(-999, -999))
            self.init_road(world_z=_Z_FAR, lane_offset=lane_offset)
        else:
            self.rect = self.image.get_rect(center=(random.randint(ROAD_LEFT + 30, ROAD_RIGHT - 30), -20))

    def _draw(self):
        self.image.fill((0, 0, 0, 0))
        p = 0.75 + 0.25 * math.sin(self.pulse * 0.12)
        cx = self._surf_size // 2
        cy = cx

        if self.tier >= 3:
            # V3: 40px surface, 8 sparkle lines, secondary inner glow ring
            pygame.draw.circle(self.image, (*COIN_GOLD, int(45 * p)), (cx, cy), 19)
            pygame.draw.circle(self.image, (*COIN_GOLD, int(65 * p)), (cx, cy), 15)
            # Main coin
            pygame.draw.circle(self.image, COIN_GOLD, (cx, cy), 11)
            # Secondary inner glow ring
            pygame.draw.circle(self.image, (255, 200, 50, int(100 * p)), (cx, cy), 7)
            pygame.draw.circle(self.image, (255, 250, 200), (cx, cy), 4)
            pygame.draw.circle(self.image, (255, 230, 100), (cx, cy), 11, 1)
            # 8 sparkle lines
            angle_off = self.pulse * 0.2
            for i in range(8):
                a = angle_off + i * math.pi / 4
                x1 = cx + int(math.cos(a) * 13)
                y1 = cy + int(math.sin(a) * 13)
                x2 = cx + int(math.cos(a) * 19)
                y2 = cy + int(math.sin(a) * 19)
                c = (255, 255, 220) if i % 2 == 0 else (255, 220, 120)
                pygame.draw.line(self.image, c, (x1, y1), (x2, y2), 1)
        elif self.tier >= 2:
            # V2: Outer gold glow ring
            pygame.draw.circle(self.image, (*COIN_GOLD, int(55 * p)), (cx, cy), 17)
            # Main coin
            pygame.draw.circle(self.image, (*COIN_GOLD, int(90 * p)), (cx, cy), 13)
            pygame.draw.circle(self.image, COIN_GOLD, (cx, cy), 9)
            pygame.draw.circle(self.image, (255, 245, 180), (cx, cy), 5)
            pygame.draw.circle(self.image, (255, 230, 100), (cx, cy), 9, 1)
            # 4 sparkle lines — fast rotation, reaching to glow edge
            angle_off = self.pulse * 0.18
            for i in range(4):
                a = angle_off + i * math.pi / 2
                x1 = cx + int(math.cos(a) * 11)
                y1 = cy + int(math.sin(a) * 11)
                x2 = cx + int(math.cos(a) * 17)
                y2 = cy + int(math.sin(a) * 17)
                pygame.draw.line(self.image, (255, 255, 200),
                                 (x1, y1), (x2, y2), 1)
        else:
            pygame.draw.circle(self.image, (*COIN_GOLD, int(60 * p)), (cx, cy), 13)
            pygame.draw.circle(self.image, COIN_GOLD, (cx, cy), 9)
            pygame.draw.circle(self.image, (255, 245, 180), (cx, cy), 5)
            pygame.draw.circle(self.image, (255, 230, 100), (cx, cy), 9, 1)

    def update(self, scroll_speed, players=None, road_geometry=None):
        self.pulse += 1
        if self.tier >= 2 and road_geometry and hasattr(self, 'world_z'):
            # Magnet effect: adjust lane_offset and world_z toward player
            if players:
                for p in players:
                    if p.alive and p.magnet and self._projected:
                        dx = p.rect.centerx - self.rect.centerx
                        dy = p.rect.centery - self.rect.centery
                        dist = max(1, math.sqrt(dx * dx + dy * dy))
                        if dist < 200:
                            # Pull toward player in world space
                            self.lane_offset -= (self.lane_offset * 0.05)
                            self.world_z -= 2.0
            self._draw()
            self._original_image = self.image.copy()
            self.advance_toward_camera(scroll_speed + self.base_speed)
            if not self.project(road_geometry):
                self.kill()
        else:
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


class PowerUp(RoadSpriteMixin, pygame.sprite.Sprite):
    _SURF_SIZE = 48  # larger for glow headroom

    def __init__(self, kind=None, tier=1, lane_offset=None):
        super().__init__()
        self.kind = kind or random.choice(POWERUP_ALL)
        self.color = POWERUP_COLORS[self.kind]
        self.pulse = random.randint(0, 60)
        self.tier = tier
        self.image = pygame.Surface((self._SURF_SIZE, self._SURF_SIZE), pygame.SRCALPHA)
        self._draw()

        if tier >= 2 and lane_offset is not None:
            self.rect = self.image.get_rect(center=(-999, -999))
            self.init_road(world_z=_Z_FAR, lane_offset=lane_offset)
        else:
            self.rect = self.image.get_rect(center=(random.randint(ROAD_LEFT + 30, ROAD_RIGHT - 30), -30))

    def _draw(self):
        sz = self._SURF_SIZE
        self.image.fill((0, 0, 0, 0))
        p = 0.65 + 0.35 * math.sin(self.pulse * 0.1)
        cx = sz // 2
        comp_color = (self.color[2], self.color[1], self.color[0])

        if self.tier >= 2:
            # V2+: Outer shimmer ring — slow color-cycling rainbow
            rainbow_t = self.pulse * 0.03
            rh = int(127 + 127 * math.sin(rainbow_t))
            rg = int(127 + 127 * math.sin(rainbow_t + 2.09))
            rb = int(127 + 127 * math.sin(rainbow_t + 4.19))
            pygame.draw.circle(self.image, (rh, rg, rb, int(35 * p)), (cx, cx), 22)
            # Complementary glow
            pygame.draw.circle(self.image, (*comp_color, int(55 * p)), (cx, cx), 18)
            # Core layers
            for r, a in [(16, int(70 * p)), (13, 120)]:
                pygame.draw.circle(self.image, (*self.color, a), (cx, cx), r)
            pygame.draw.circle(self.image, self.color, (cx, cx), 11, 2)
            pygame.draw.circle(self.image, (*self.color, 230), (cx, cx), 8)
            # 6 sparkle rays — rotating, reaching to shimmer edge
            for i in range(6):
                a = self.pulse * 0.12 + i * math.pi / 3
                x1 = cx + int(math.cos(a) * 12)
                y1 = cx + int(math.sin(a) * 12)
                x2 = cx + int(math.cos(a) * 21)
                y2 = cx + int(math.sin(a) * 21)
                ray_a = int(100 * p)
                pygame.draw.line(self.image, (*self.color, ray_a), (x1, y1), (x2, y2), 1)
            # 4 orbiting accent dots
            for i in range(4):
                orb_a = self.pulse * 0.14 + i * math.pi / 2
                ox = cx + int(math.cos(orb_a) * 16)
                oy = cx + int(math.sin(orb_a) * 16)
                if 0 <= ox < sz and 0 <= oy < sz:
                    pygame.draw.circle(self.image, (*comp_color, 200), (ox, oy), 2)
            # Bright center highlight
            pygame.draw.circle(self.image, (255, 255, 255, int(80 * p)), (cx, cx), 4)
        else:
            # V1: Enhanced glow + sparkle rays
            pygame.draw.circle(self.image, (*self.color, int(30 * p)), (cx, cx), 20)
            for r, a in [(18, int(50 * p)), (14, 90)]:
                pygame.draw.circle(self.image, (*self.color, a), (cx, cx), r)
            pygame.draw.circle(self.image, self.color, (cx, cx), 12, 2)
            pygame.draw.circle(self.image, (*self.color, 190), (cx, cx), 9)
            # 4 sparkle rays
            for i in range(4):
                a = self.pulse * 0.1 + i * math.pi / 2
                x1 = cx + int(math.cos(a) * 10)
                y1 = cx + int(math.sin(a) * 10)
                x2 = cx + int(math.cos(a) * 18)
                y2 = cx + int(math.sin(a) * 18)
                pygame.draw.line(self.image, (*self.color, int(80 * p)), (x1, y1), (x2, y2), 1)

        label = _fonts.FONT_POWERUP.render(POWERUP_LABELS[self.kind], True, WHITE)
        self.image.blit(label, (cx - label.get_width() // 2, cx - label.get_height() // 2))

    def update(self, scroll_speed, players=None, road_geometry=None):
        self.pulse += 1
        if self.tier >= 2 and road_geometry and hasattr(self, 'world_z'):
            # Tiers 1-2: powerups auto-attract toward nearest player
            if self.tier <= 2 and players and self._projected:
                best_dist = 999999
                for p in players:
                    if not p.alive:
                        continue
                    dx = p.rect.centerx - self.rect.centerx
                    dy = p.rect.centery - self.rect.centery
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist < best_dist:
                        best_dist = dist
                if best_dist < 250:
                    self.lane_offset -= self.lane_offset * 0.04
                    self.world_z -= 1.5
            self._draw()
            self._original_image = self.image.copy()
            self.advance_toward_camera(scroll_speed + 2)
            if not self.project(road_geometry):
                self.kill()
        else:
            # V1 + tiers 1-2: screen-space magnetism
            if self.tier <= 2 and players:
                best_dist = 999999
                best_p = None
                for p in players:
                    if not p.alive:
                        continue
                    dx = p.rect.centerx - self.rect.centerx
                    dy = p.rect.centery - self.rect.centery
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist < best_dist:
                        best_dist = dist
                        best_p = p
                if best_p and best_dist < 250:
                    dx = best_p.rect.centerx - self.rect.centerx
                    dy = best_p.rect.centery - self.rect.centery
                    dist = max(1, best_dist)
                    self.rect.x += int(dx / dist * 4)
                    self.rect.y += int(dy / dist * 4)
            self._draw()
            self.rect.y += scroll_speed + 2
            if self.rect.y > SCREEN_HEIGHT + 30:
                self.kill()


class SolarFlare(RoadSpriteMixin, pygame.sprite.Sprite):
    # Neon color cycle for the flare glow
    NEON_CYCLE = [
        (255, 255, 0), (255, 200, 0), (255, 150, 50),
        (255, 100, 100), (255, 50, 200), (200, 50, 255),
        (100, 100, 255), (50, 200, 255), (0, 255, 200),
        (50, 255, 100), (150, 255, 50), (255, 255, 0),
    ]

    def __init__(self, particles, x, tier=1, lane_offset=None):
        super().__init__()
        r = 26
        self.radius = r
        self.pulse = 0
        self.image = pygame.Surface((r * 2 + 24, r * 2 + 24), pygame.SRCALPHA)
        self.active = True
        self.particles = particles
        self.base_speed = 3
        self.tier = tier
        self._redraw()

        if tier >= 2 and lane_offset is not None:
            self.rect = self.image.get_rect(center=(-999, -999))
            self.init_road(world_z=_Z_FAR, lane_offset=lane_offset)
        else:
            self.rect = pygame.Rect(x - r - 12, -60, (r + 12) * 2, (r + 12) * 2)

    def _neon_color(self):
        """Get smoothly cycling neon color."""
        t = (self.pulse * 0.12) % len(self.NEON_CYCLE)
        idx = int(t)
        frac = t - idx
        c1 = self.NEON_CYCLE[idx % len(self.NEON_CYCLE)]
        c2 = self.NEON_CYCLE[(idx + 1) % len(self.NEON_CYCLE)]
        return tuple(int(c1[i] + (c2[i] - c1[i]) * frac) for i in range(3))

    def _is_collidable(self):
        """Check if this sprite is close enough for collision (V2 guard)."""
        if self.tier >= 2 and hasattr(self, '_projected'):
            return self._projected
        return True

    def _redraw(self):
        r = self.radius
        self.image.fill((0, 0, 0, 0))
        cx, cy = r + 12, r + 12
        p = 0.82 + 0.18 * math.sin(self.pulse * 0.12)
        nc = self._neon_color()

        if self.tier >= 3:
            # V3: 8 outer ray spikes radiating from center
            spike_rot = self.pulse * 0.08
            for i in range(8):
                a = spike_rot + i * math.pi / 4
                # Spike: triangle from core outward
                tip_r = r + 18
                base_r = r + 2
                half_w = 4
                tip_x = cx + int(math.cos(a) * tip_r)
                tip_y = cy + int(math.sin(a) * tip_r)
                bl_x = cx + int(math.cos(a - 0.2) * base_r)
                bl_y = cy + int(math.sin(a - 0.2) * base_r)
                br_x = cx + int(math.cos(a + 0.2) * base_r)
                br_y = cy + int(math.sin(a + 0.2) * base_r)
                spike_color = nc if i % 2 == 0 else (255, 220, 100)
                pygame.draw.polygon(self.image, (*spike_color, int(140 * p)),
                                    [(tip_x, tip_y), (bl_x, bl_y), (br_x, br_y)])
            # Outer glow rings
            for i in range(5, 0, -1):
                a_val = int(45 * p * (5 - i) / 5)
                pygame.draw.circle(self.image, (*nc, a_val), (cx, cy), int(r + i * 5))
            # Core
            pygame.draw.circle(self.image, (255, 255, 220, int(150 * p)), (cx, cy), r)
            pygame.draw.circle(self.image, (*nc, 220), (cx, cy), r - 3)
            # Inner neon ring
            pygame.draw.circle(self.image, (*nc, int(180 * p)), (cx, cy), r - 8, 2)
            # Bright center
            pygame.draw.circle(self.image, (255, 255, 255, int(200 * p)), (cx, cy), r // 3 + 1)
            pygame.draw.circle(self.image, (255, 255, 255), (cx, cy), r // 5)
        else:
            # V1/V2: Outer neon glow rings (color cycling)
            for i in range(4, 0, -1):
                a_val = int(40 * p * (4 - i) / 4)
                pygame.draw.circle(self.image, (*nc, a_val), (cx, cy), int(r + i * 6))
            # Inner warm core
            pygame.draw.circle(self.image, (255, 255, 220, int(130 * p)), (cx, cy), r)
            pygame.draw.circle(self.image, (*nc, 200), (cx, cy), r - 4)
            # Bright center
            pygame.draw.circle(self.image, (255, 255, 255, int(180 * p)), (cx, cy), r // 3)

    def update(self, scroll_speed, players, road_geometry=None):
        if not self.active:
            return
        self.pulse += 1
        self._redraw()

        if self.tier >= 2 and road_geometry and hasattr(self, 'world_z'):
            self._original_image = self.image.copy()
            self.advance_toward_camera(scroll_speed + self.base_speed)
            if not self.project(road_geometry):
                self.kill()
                return
        else:
            self.rect.y += scroll_speed + self.base_speed
            if self.rect.y > SCREEN_HEIGHT + 50:
                self.kill()
                return

        # Emit neon-colored trail particles
        if self.pulse % 3 == 0 and self.rect.x > -900:
            nc = self._neon_color()
            self.particles.emit(
                self.rect.centerx + random.randint(-8, 8),
                self.rect.centery, nc,
                [random.uniform(-1.5, 1.5), random.uniform(-2, 0.5)], 35, 2,
            )
        for player in players:
            if player.alive and self._is_collidable() and self.rect.colliderect(player.rect) and not player.ghost_mode:
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
                from core.sound import play_sfx
                play_sfx("powerup")
                self.active = False
                self.kill()
                break
