"""Micro Machines Boss — Giant Monster Truck that circles the screen edges.

A top-down boss fight where a massive monster truck patrols a rounded
rectangular path around the screen perimeter.

3 phases with escalating attack patterns:
  Phase 1: Oil Slick Drop + Shockwave Ring
  Phase 2: + Homing Missiles
  Phase 3: + Tire Barrage (bouncing projectiles)

Damage methods:
  1. Ram during vulnerability window
  2. Heat bolt projectiles
  3. Environmental: boss drives over its own oil slicks
"""

import pygame
import random
import math

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    NEON_CYAN, NEON_MAGENTA, SOLAR_YELLOW, SOLAR_WHITE,
    ROAD_LEFT, ROAD_RIGHT,
)
from core.sound import SFX
from core.fonts import load_font
from shared.boss_base import Boss, BossPhase, AttackPattern, HeatBolt


# ---------------------------------------------------------------------------
# Hazard: Oil Slick Patch
# ---------------------------------------------------------------------------

class OilSlick(pygame.sprite.Sprite):
    """Oil patch on the road that slows/damages players and the boss itself."""

    def __init__(self, x, y):
        super().__init__()
        self.radius = random.randint(18, 28)
        self.image = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        # Dark iridescent oil puddle
        pygame.draw.ellipse(self.image, (20, 20, 30, 180),
                            (0, 0, self.radius * 2, self.radius * 2))
        # Rainbow sheen highlights
        for _ in range(5):
            ox = random.randint(4, self.radius * 2 - 8)
            oy = random.randint(4, self.radius * 2 - 8)
            sheen_color = random.choice([
                (80, 40, 120, 60), (40, 80, 120, 60), (120, 80, 40, 60),
            ])
            pygame.draw.ellipse(self.image, sheen_color, (ox, oy, 8, 5))
        self.rect = self.image.get_rect(center=(x, y))
        self.alive = True
        self.life = 600  # frames before disappearing
        self.hit_boss = False  # boss can only be hurt once per slick
        self.hit_players = set()

    def update(self):
        self.life -= 1
        if self.life <= 0:
            self.alive = False
            self.kill()
        elif self.life < 60:
            # Fade out
            self.image.set_alpha(int(255 * (self.life / 60.0)))


# ---------------------------------------------------------------------------
# Projectile: Homing Missile (top-down variant)
# ---------------------------------------------------------------------------

class TopDownMissile(pygame.sprite.Sprite):
    """Homing missile for top-down perspective."""

    def __init__(self, x, y, target, speed=3.0):
        super().__init__()
        self.size = 8
        self.image = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.polygon(self.image, (255, 60, 30),
                            [(self.size, 0), (self.size * 2, self.size * 2),
                             (self.size, int(self.size * 1.5)), (0, self.size * 2)])
        pygame.draw.circle(self.image, SOLAR_YELLOW, (self.size, self.size), 3)
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = [float(x), float(y)]
        self.speed = speed
        self.target = target
        self.turn_rate = 0.05
        self.angle = random.uniform(0, 2 * math.pi)
        self.alive = True
        self.life = 360

    def update(self):
        self.life -= 1
        if self.life <= 0:
            self.alive = False
            self.kill()
            return

        # Track target
        if self.target and self.target.alive:
            dx = self.target.rect.centerx - self.pos[0]
            dy = self.target.rect.centery - self.pos[1]
            desired = math.atan2(dy, dx)
            diff = desired - self.angle
            while diff > math.pi:
                diff -= 2 * math.pi
            while diff < -math.pi:
                diff += 2 * math.pi
            self.angle += max(-self.turn_rate, min(self.turn_rate, diff))

        vx = math.cos(self.angle) * self.speed
        vy = math.sin(self.angle) * self.speed
        self.pos[0] += vx
        self.pos[1] += vy
        self.rect.center = (int(self.pos[0]), int(self.pos[1]))

        if (self.rect.top > SCREEN_HEIGHT + 40 or self.rect.bottom < -40 or
                self.rect.left > SCREEN_WIDTH + 40 or self.rect.right < -40):
            self.alive = False
            self.kill()


# ---------------------------------------------------------------------------
# Projectile: Bouncing Tire
# ---------------------------------------------------------------------------

class BouncingTire(pygame.sprite.Sprite):
    """Tire projectile that ricochets off screen edges."""

    def __init__(self, x, y, angle, speed=4.0):
        super().__init__()
        self.tire_radius = 10
        self.image = pygame.Surface((self.tire_radius * 2 + 2, self.tire_radius * 2 + 2),
                                    pygame.SRCALPHA)
        cx = self.tire_radius + 1
        cy = self.tire_radius + 1
        # Outer tire ring
        pygame.draw.circle(self.image, (50, 50, 60), (cx, cy), self.tire_radius)
        pygame.draw.circle(self.image, (80, 80, 90), (cx, cy), self.tire_radius, 2)
        # Inner hub
        pygame.draw.circle(self.image, (120, 120, 130), (cx, cy), 4)
        # Tread marks
        for spoke in range(6):
            a = spoke * (math.pi / 3)
            sx = cx + int(math.cos(a) * (self.tire_radius - 2))
            sy = cy + int(math.sin(a) * (self.tire_radius - 2))
            pygame.draw.line(self.image, (30, 30, 40), (cx, cy), (sx, sy), 1)

        self.rect = self.image.get_rect(center=(x, y))
        self.pos = [float(x), float(y)]
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.alive = True
        self.life = 480  # 8 seconds at 60fps
        self.bounces = 0
        self.max_bounces = 6

    def update(self):
        self.life -= 1
        if self.life <= 0 or self.bounces > self.max_bounces:
            self.alive = False
            self.kill()
            return

        self.pos[0] += self.vx
        self.pos[1] += self.vy

        # Bounce off screen edges
        margin = 10
        if self.pos[0] <= margin:
            self.pos[0] = margin
            self.vx = abs(self.vx)
            self.bounces += 1
        elif self.pos[0] >= SCREEN_WIDTH - margin:
            self.pos[0] = SCREEN_WIDTH - margin
            self.vx = -abs(self.vx)
            self.bounces += 1

        if self.pos[1] <= margin:
            self.pos[1] = margin
            self.vy = abs(self.vy)
            self.bounces += 1
        elif self.pos[1] >= SCREEN_HEIGHT - margin:
            self.pos[1] = SCREEN_HEIGHT - margin
            self.vy = -abs(self.vy)
            self.bounces += 1

        self.rect.center = (int(self.pos[0]), int(self.pos[1]))


# ---------------------------------------------------------------------------
# Attack Patterns
# ---------------------------------------------------------------------------

class OilSlickDrop(AttackPattern):
    """Boss drops 3-4 oil patches on the road."""

    NAME = "oil_slick"
    DURATION = 160
    WEIGHT = 1.0

    def __init__(self):
        super().__init__()
        self.slicks = []
        self.drop_times = []

    def start(self, boss):
        super().start(boss)
        self.slicks = []
        count = random.randint(3, 4)
        self.drop_times = sorted([random.randint(10, 80) for _ in range(count)])

    def update(self, boss, players, particles, dt=1):
        self.timer += 1

        # Drop oil at scheduled times
        while self.drop_times and self.timer >= self.drop_times[0]:
            self.drop_times.pop(0)
            # Drop behind the boss
            ox = boss.rect.centerx + random.randint(-30, 30)
            oy = boss.rect.centery + random.randint(-20, 20)
            ox = max(20, min(SCREEN_WIDTH - 20, ox))
            oy = max(20, min(SCREEN_HEIGHT - 20, oy))
            slick = OilSlick(ox, oy)
            self.slicks.append(slick)
            particles.burst(ox, oy, [(20, 20, 30), (60, 40, 80)], 6, 2, 15, 2)

        # Update slicks and check player collision
        for slick in self.slicks[:]:
            slick.update()
            if not slick.alive:
                if slick in self.slicks:
                    self.slicks.remove(slick)
                continue
            for p in players:
                if (p.alive and id(p) not in slick.hit_players and
                        slick.rect.colliderect(p.rect)):
                    if hasattr(boss, 'shake') and boss.shake:
                        p.take_hit(boss.shake)
                    slick.hit_players.add(id(p))

        if self.timer >= self.DURATION:
            # Slicks persist after attack ends -- they are transferred to the boss
            self.active = False
            return True
        return False

    def draw(self, screen, boss):
        for slick in self.slicks:
            if slick.alive:
                screen.blit(slick.image, slick.rect)

    def get_active_slicks(self):
        """Return slicks that are still alive for the boss to track."""
        return [s for s in self.slicks if s.alive]


class ShockwaveRing(AttackPattern):
    """Boss emits expanding circular ring from center."""

    NAME = "shockwave_ring"
    DURATION = 150
    WEIGHT = 1.0

    def __init__(self):
        super().__init__()
        self.ring_radius = 0
        self.ring_speed = 4
        self.ring_active = False
        self.ring_cx = 0
        self.ring_cy = 0
        self.max_radius = 350
        self.ring_width = 15
        self.hit_players = set()

    def start(self, boss):
        super().start(boss)
        self.ring_radius = 0
        self.ring_active = False
        self.ring_cx = boss.rect.centerx
        self.ring_cy = boss.rect.centery
        self.hit_players = set()

    def update(self, boss, players, particles, dt=1):
        self.timer += 1

        # Telegraph for 30 frames
        if self.timer < 30:
            boss.rect.x += random.randint(-2, 2)
            boss.rect.y += random.randint(-2, 2)
            return False

        if not self.ring_active and self.timer == 30:
            self.ring_active = True
            self.ring_cx = boss.rect.centerx
            self.ring_cy = boss.rect.centery
            SFX["boost"].play()

        if self.ring_active:
            self.ring_radius += self.ring_speed

            # Check player collision -- player must be near the ring edge
            for p in players:
                if not p.alive or id(p) in self.hit_players:
                    continue
                dist = math.hypot(p.rect.centerx - self.ring_cx,
                                  p.rect.centery - self.ring_cy)
                # Hit if player is within the ring band
                if abs(dist - self.ring_radius) < self.ring_width + 15:
                    if hasattr(boss, 'shake') and boss.shake:
                        p.take_hit(boss.shake)
                    self.hit_players.add(id(p))

            if self.ring_radius >= self.max_radius:
                self.ring_active = False

        if self.timer >= self.DURATION:
            self.active = False
            return True
        return False

    def draw(self, screen, boss):
        if not self.ring_active:
            # Telegraph: pulsing glow at boss center
            if self.timer < 30 and (self.timer // 4) % 2 == 0:
                glow_surf = pygame.Surface((60, 60), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (255, 100, 30, 100), (30, 30), 28)
                screen.blit(glow_surf, (boss.rect.centerx - 30, boss.rect.centery - 30))
            return

        if self.ring_radius > 0:
            # Draw expanding ring
            ring_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            alpha = max(30, 180 - int(self.ring_radius * 0.5))
            color = (255, 100, 30, alpha)
            if self.ring_radius > 3:
                pygame.draw.circle(ring_surf, color,
                                   (self.ring_cx, self.ring_cy),
                                   int(self.ring_radius), self.ring_width)
            # Bright inner edge
            if self.ring_radius > 5:
                inner_alpha = max(20, alpha - 40)
                pygame.draw.circle(ring_surf, (255, 200, 80, inner_alpha),
                                   (self.ring_cx, self.ring_cy),
                                   int(self.ring_radius), 2)
            screen.blit(ring_surf, (0, 0))


class HomingMissileAttack(AttackPattern):
    """Fires 2-4 homing missiles at the nearest alive player."""

    NAME = "homing_missiles"
    DURATION = 200
    WEIGHT = 0.9

    def __init__(self, count_range=(2, 4)):
        super().__init__()
        self.count_range = count_range
        self.missiles = []
        self.fire_times = []

    def start(self, boss):
        super().start(boss)
        self.missiles = []
        count = random.randint(self.count_range[0], self.count_range[1])
        self.fire_times = sorted([random.randint(15, 80) for _ in range(count)])

    def update(self, boss, players, particles, dt=1):
        self.timer += 1

        alive_players = [p for p in players if p.alive]
        while self.fire_times and self.timer >= self.fire_times[0]:
            self.fire_times.pop(0)
            if alive_players:
                target = random.choice(alive_players)
                m = TopDownMissile(boss.rect.centerx, boss.rect.centery,
                                   target, speed=2.8 + boss.current_phase.speed_mult * 0.5)
                self.missiles.append(m)
                particles.burst(boss.rect.centerx, boss.rect.centery,
                                [(255, 120, 30), SOLAR_YELLOW], 4, 3, 15, 2)

        for m in self.missiles[:]:
            m.update()
            if not m.alive:
                if m in self.missiles:
                    self.missiles.remove(m)
                continue
            for p in alive_players:
                if m.rect.colliderect(p.rect) and m.alive:
                    if hasattr(boss, 'shake') and boss.shake:
                        p.take_hit(boss.shake)
                    particles.burst(m.rect.centerx, m.rect.centery,
                                    [(255, 100, 30), (255, 200, 60)], 8, 4, 25, 3)
                    m.alive = False
                    m.kill()
                    if m in self.missiles:
                        self.missiles.remove(m)
                    break

        if self.timer >= self.DURATION:
            for m in self.missiles:
                m.kill()
            self.missiles.clear()
            self.active = False
            return True
        return False

    def draw(self, screen, boss):
        for m in self.missiles:
            if m.alive:
                screen.blit(m.image, m.rect)
                # Trail
                trail_surf = pygame.Surface((6, 6), pygame.SRCALPHA)
                pygame.draw.circle(trail_surf, (255, 140, 40, 100), (3, 3), 3)
                screen.blit(trail_surf, (m.rect.centerx - 3, m.rect.centery - 3))


class TireBarrage(AttackPattern):
    """Launches bouncing tire projectiles that ricochet off screen edges."""

    NAME = "tire_barrage"
    DURATION = 220
    WEIGHT = 1.1

    def __init__(self):
        super().__init__()
        self.tires = []
        self.fire_times = []

    def start(self, boss):
        super().start(boss)
        self.tires = []
        count = random.randint(4, 6)
        self.fire_times = sorted([random.randint(10, 60) for _ in range(count)])

    def update(self, boss, players, particles, dt=1):
        self.timer += 1

        alive_players = [p for p in players if p.alive]
        while self.fire_times and self.timer >= self.fire_times[0]:
            self.fire_times.pop(0)
            # Fire tire in a random direction biased toward players
            angle = random.uniform(0, 2 * math.pi)
            if alive_players:
                target = random.choice(alive_players)
                dx = target.rect.centerx - boss.rect.centerx
                dy = target.rect.centery - boss.rect.centery
                angle = math.atan2(dy, dx) + random.uniform(-0.4, 0.4)
            speed = random.uniform(3.5, 5.5)
            tire = BouncingTire(boss.rect.centerx, boss.rect.centery, angle, speed)
            self.tires.append(tire)
            particles.burst(boss.rect.centerx, boss.rect.centery,
                            [(80, 80, 90), (50, 50, 60)], 3, 2, 10, 2)

        for tire in self.tires[:]:
            tire.update()
            if not tire.alive:
                if tire in self.tires:
                    self.tires.remove(tire)
                continue
            for p in alive_players:
                if tire.rect.colliderect(p.rect) and tire.alive:
                    if hasattr(boss, 'shake') and boss.shake:
                        p.take_hit(boss.shake)
                    particles.burst(tire.rect.centerx, tire.rect.centery,
                                    [(80, 80, 90), (120, 120, 130)], 6, 3, 20, 2)
                    tire.alive = False
                    tire.kill()
                    if tire in self.tires:
                        self.tires.remove(tire)
                    break

        if self.timer >= self.DURATION:
            for t in self.tires:
                t.kill()
            self.tires.clear()
            self.active = False
            return True
        return False

    def draw(self, screen, boss):
        for tire in self.tires:
            if tire.alive:
                screen.blit(tire.image, tire.rect)


# ---------------------------------------------------------------------------
# Micro Machines Boss
# ---------------------------------------------------------------------------

class MicroMachinesBoss(Boss):
    """Giant monster truck boss for the Micro Machines mode.

    Circles the screen edges clockwise along a rounded rectangular path.
    3 phases of escalating attacks. Can be damaged by ram (during
    vulnerability), heat bolts, and its own oil slicks.
    """

    MAX_HP = 350
    RAM_DAMAGE = 25
    ENVIRONMENTAL_DAMAGE = 50

    # Patrol path: rounded rectangle ~50px inside screen bounds
    PATH_MARGIN = 50
    PATH_CORNER_RADIUS = 80

    def __init__(self, particles, shake=None, evolution_tier=1):
        self.shake = shake
        evo_scale = 1.0 + (evolution_tier - 1) * 0.3
        self.MAX_HP = int(350 * evo_scale)
        self.path_t = 0.0  # parametric position along path [0..1)
        self.path_speed = 0.003  # base speed around path
        self.facing_angle = 0.0
        self.underglow_pulse = 0
        self.tire_rot = 0.0
        self.oil_slicks = []  # persistent oil slicks from attacks
        super().__init__(SCREEN_WIDTH // 2, self.PATH_MARGIN, particles)

    def _build_phases(self):
        """Construct 3 boss phases with escalating attack pools."""
        # Phase 1: HP 100% - 66%
        phase1_attacks = [
            OilSlickDrop(),
            ShockwaveRing(),
        ]
        phase1 = BossPhase(
            hp_threshold=1.0,
            attacks=phase1_attacks,
            vulnerability_after_attack=90,
            speed_mult=1.0,
            color=NEON_CYAN,
        )

        # Phase 2: HP 66% - 33%
        phase2_attacks = [
            OilSlickDrop(),
            ShockwaveRing(),
            HomingMissileAttack(count_range=(2, 4)),
        ]
        phase2 = BossPhase(
            hp_threshold=0.66,
            attacks=phase2_attacks,
            vulnerability_after_attack=75,
            speed_mult=1.3,
            color=SOLAR_YELLOW,
        )

        # Phase 3: HP 33% - 0%
        phase3_attacks = [
            OilSlickDrop(),
            ShockwaveRing(),
            HomingMissileAttack(count_range=(3, 4)),
            TireBarrage(),
        ]
        phase3 = BossPhase(
            hp_threshold=0.33,
            attacks=phase3_attacks,
            vulnerability_after_attack=60,
            speed_mult=1.6,
            color=NEON_MAGENTA,
        )

        return [phase1, phase2, phase3]

    def _create_surface(self):
        """Draw the monster truck procedurally -- 100x100 px top-down view."""
        surf = pygame.Surface((100, 100), pygame.SRCALPHA)
        phase_color = self.current_phase.color if hasattr(self, 'current_phase') else NEON_CYAN
        tire_rot = getattr(self, 'tire_rot', 0.0)

        # --- Neon underglow (drawn first, beneath everything) ---
        underglow_pulse = getattr(self, 'underglow_pulse', 0)
        glow_alpha = int(40 + 25 * math.sin(underglow_pulse * 0.08))
        pygame.draw.ellipse(surf, (*phase_color[:3], glow_alpha), (8, 8, 84, 84))

        # --- Chassis / body ---
        # Main body rectangle with rounded feel
        body_rect = (22, 18, 56, 64)
        pygame.draw.rect(surf, (70, 70, 85), body_rect, border_radius=8)
        pygame.draw.rect(surf, phase_color, body_rect, 2, border_radius=8)

        # Raised center section (cab)
        cab_rect = (30, 28, 40, 40)
        pygame.draw.rect(surf, (90, 90, 105), cab_rect, border_radius=4)
        pygame.draw.rect(surf, phase_color, cab_rect, 1, border_radius=4)

        # Windshield (top of cab)
        pygame.draw.rect(surf, (*phase_color[:3], 80), (34, 30, 32, 12), border_radius=2)

        # --- Big chunky tires (4 corners) ---
        tire_positions = [(16, 24), (78, 24), (16, 72), (78, 72)]
        for tx, ty in tire_positions:
            # Tire body
            pygame.draw.ellipse(surf, (35, 35, 45), (tx - 12, ty - 8, 24, 16))
            pygame.draw.ellipse(surf, (60, 60, 70), (tx - 12, ty - 8, 24, 16), 2)
            # Tread lines (animated rotation)
            for i in range(3):
                offset = int((tire_rot + i * 5) % 14) - 7
                lx = tx + offset
                pygame.draw.line(surf, (45, 45, 55), (lx, ty - 6), (lx, ty + 6), 1)
            # Hub
            pygame.draw.circle(surf, (100, 100, 110), (tx, ty), 3)

        # --- Roof lights (top edge) ---
        for lx in [35, 45, 55, 65]:
            pygame.draw.circle(surf, SOLAR_YELLOW, (lx, 20), 3)
            pygame.draw.circle(surf, SOLAR_WHITE, (lx, 20), 1)

        # --- Bull bar (front) ---
        pygame.draw.rect(surf, (100, 100, 110), (26, 14, 48, 4))
        pygame.draw.rect(surf, phase_color, (26, 14, 48, 4), 1)

        # --- Exhaust stacks (rear) ---
        for ex in [32, 68]:
            pygame.draw.rect(surf, (90, 90, 100), (ex - 3, 78, 6, 8))
            pygame.draw.circle(surf, (180, 80, 30), (ex, 86), 3)

        return surf

    def _get_path_position(self, t):
        """Calculate (x, y) position along the rounded rectangular patrol path.

        t ranges from 0 to 1, traversing the path clockwise:
          0.00 - 0.25: top edge (left to right)
          0.25 - 0.50: right edge (top to bottom)
          0.50 - 0.75: bottom edge (right to left)
          0.75 - 1.00: left edge (bottom to top)
        """
        m = self.PATH_MARGIN
        cr = self.PATH_CORNER_RADIUS
        w = SCREEN_WIDTH - 2 * m
        h = SCREEN_HEIGHT - 2 * m

        # Perimeter lengths
        straight_h = h - 2 * cr
        straight_w = w - 2 * cr
        corner_len = 0.5 * math.pi * cr  # quarter circle arc
        total = 2 * straight_w + 2 * straight_h + 4 * corner_len

        d = (t % 1.0) * total

        segments = [
            straight_w,      # top straight
            corner_len,      # top-right corner
            straight_h,      # right straight
            corner_len,      # bottom-right corner
            straight_w,      # bottom straight
            corner_len,      # bottom-left corner
            straight_h,      # left straight
            corner_len,      # top-left corner
        ]

        seg_idx = 0
        for i, seg_len in enumerate(segments):
            if d <= seg_len:
                seg_idx = i
                break
            d -= seg_len
        else:
            seg_idx = 7
            d = 0

        frac = d / max(1, segments[seg_idx])

        if seg_idx == 0:
            # Top straight: left to right
            return (m + cr + frac * straight_w, m)
        elif seg_idx == 1:
            # Top-right corner
            angle = -math.pi / 2 + frac * (math.pi / 2)
            return (m + w - cr + math.cos(angle) * cr,
                    m + cr + math.sin(angle) * cr)
        elif seg_idx == 2:
            # Right straight: top to bottom
            return (m + w, m + cr + frac * straight_h)
        elif seg_idx == 3:
            # Bottom-right corner
            angle = 0 + frac * (math.pi / 2)
            return (m + w - cr + math.cos(angle) * cr,
                    m + h - cr + math.sin(angle) * cr)
        elif seg_idx == 4:
            # Bottom straight: right to left
            return (m + w - cr - frac * straight_w, m + h)
        elif seg_idx == 5:
            # Bottom-left corner
            angle = math.pi / 2 + frac * (math.pi / 2)
            return (m + cr + math.cos(angle) * cr,
                    m + h - cr + math.sin(angle) * cr)
        elif seg_idx == 6:
            # Left straight: bottom to top
            return (m, m + h - cr - frac * straight_h)
        else:
            # Top-left corner
            angle = math.pi + frac * (math.pi / 2)
            return (m + cr + math.cos(angle) * cr,
                    m + cr + math.sin(angle) * cr)

    def _update_movement(self, players, dt=1):
        """Move along rounded rectangular path. Stop during vulnerability."""
        if self.vulnerable:
            # Stay still when vulnerable to allow ramming
            return

        speed = self.path_speed * self.current_phase.speed_mult
        old_x, old_y = self.rect.centerx, self.rect.centery
        self.path_t = (self.path_t + speed) % 1.0
        new_x, new_y = self._get_path_position(self.path_t)

        self.rect.center = (int(new_x), int(new_y))

        # Update facing angle based on movement direction
        dx = new_x - old_x
        dy = new_y - old_y
        if abs(dx) > 0.1 or abs(dy) > 0.1:
            self.facing_angle = math.atan2(dy, dx)

        # Animate underglow and tire rotation
        self.underglow_pulse += 1
        self.tire_rot += 1.5 * self.current_phase.speed_mult

    def _draw_extras(self, screen):
        """Draw oil slicks, underglow trail, and phase indicator."""
        # Draw persistent oil slicks
        for slick in self.oil_slicks[:]:
            if slick.alive:
                slick.update()
                screen.blit(slick.image, slick.rect)
            else:
                self.oil_slicks.remove(slick)

        # Neon underglow trail
        if self.alive and self.active and not self.vulnerable:
            trail_surf = pygame.Surface((30, 30), pygame.SRCALPHA)
            trail_alpha = int(60 + 30 * math.sin(self.underglow_pulse * 0.1))
            pygame.draw.circle(trail_surf, (*self.current_phase.color[:3], trail_alpha),
                               (15, 15), 14)
            screen.blit(trail_surf, (self.rect.centerx - 15, self.rect.centery - 15))

        # Phase indicator
        if self.alive and self.active:
            phase_names = ["PHASE I", "PHASE II", "PHASE III"]
            if self.current_phase_idx < len(phase_names):
                font = load_font("dejavusans", 14, bold=True)
                txt = font.render(phase_names[self.current_phase_idx], True,
                                  self.current_phase.color)
                screen.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2,
                                  SCREEN_HEIGHT - 58))

    def _on_phase_change(self, new_phase_idx):
        """Burst effect on phase transition, rebuild sprite."""
        self.image = self._create_surface()
        self.particles.burst(
            self.rect.centerx, self.rect.centery,
            [self.current_phase.color, SOLAR_WHITE], 30, 7, 60, 4,
        )

    def _on_death(self, particles):
        """Massive explosion with tire debris."""
        for i in range(6):
            ox = random.randint(-50, 50)
            oy = random.randint(-50, 50)
            particles.burst(
                self.rect.centerx + ox, self.rect.centery + oy,
                [SOLAR_YELLOW, SOLAR_WHITE, NEON_MAGENTA, NEON_CYAN],
                10, 8, 70, 5,
            )
        # Clean up all oil slicks
        for slick in self.oil_slicks:
            slick.kill()
        self.oil_slicks.clear()

    def update(self, players, scroll_speed=0):
        """Extended update: track oil slicks, check environmental self-damage."""
        # Collect oil slicks from finished OilSlickDrop attacks
        if (self.current_attack and isinstance(self.current_attack, OilSlickDrop) and
                not self.current_attack.active):
            for slick in self.current_attack.get_active_slicks():
                if slick not in self.oil_slicks:
                    self.oil_slicks.append(slick)

        super().update(players, scroll_speed)

        # Check if boss drives over its own oil (environmental damage)
        if self.alive and self.active:
            for slick in self.oil_slicks[:]:
                if not slick.alive:
                    self.oil_slicks.remove(slick)
                    continue
                if not slick.hit_boss and self.rect.colliderect(slick.rect):
                    self.take_damage(self.ENVIRONMENTAL_DAMAGE, source="environmental")
                    slick.hit_boss = True
                    self.particles.burst(slick.rect.centerx, slick.rect.centery,
                                         [(20, 20, 30), (60, 40, 80)], 8, 4, 20, 2)

        # Rebuild surface for animation
        if self.alive and self.active:
            self.image = self._create_surface()

    def get_oil_slicks(self):
        """Public accessor for persistent oil slick list (for mode-level logic)."""
        return self.oil_slicks
