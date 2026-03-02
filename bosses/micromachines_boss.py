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
from core.sound import play_sfx
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
        bounced = False
        if self.pos[0] <= margin:
            self.pos[0] = margin
            self.vx = abs(self.vx)
            self.bounces += 1
            bounced = True
        elif self.pos[0] >= SCREEN_WIDTH - margin:
            self.pos[0] = SCREEN_WIDTH - margin
            self.vx = -abs(self.vx)
            self.bounces += 1
            bounced = True

        if self.pos[1] <= margin:
            self.pos[1] = margin
            self.vy = abs(self.vy)
            self.bounces += 1
            bounced = True
        elif self.pos[1] >= SCREEN_HEIGHT - margin:
            self.pos[1] = SCREEN_HEIGHT - margin
            self.vy = -abs(self.vy)
            self.bounces += 1
            bounced = True

        if bounced:
            play_sfx("tire_bounce")

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
        count = 3 + boss.current_phase_idx
        self.drop_times = sorted([random.randint(10, 80) for _ in range(count)])
        self._patrol_slick_placed = False
        self._boss_ref = boss

    def update(self, boss, players, particles, dt=1):
        self.timer += 1

        # Drop oil at scheduled times
        while self.drop_times and self.timer >= self.drop_times[0]:
            self.drop_times.pop(0)
            # Drop on-track near the boss
            ox = boss.rect.centerx + random.randint(-30, 30)
            oy = boss.rect.centery + random.randint(-20, 20)
            # Clamp to track bounds if track_bg available
            if hasattr(boss, 'track_bg') and boss.track_bg:
                world_y = oy + boss.track_bg.scroll_offset_value
                bounds = boss.track_bg.get_track_bounds_at_world_y(world_y)
                if bounds:
                    ox = max(int(bounds[0]) + 10, min(int(bounds[2]) - 10, ox))
            ox = max(20, min(SCREEN_WIDTH - 20, ox))
            oy = max(20, min(SCREEN_HEIGHT - 20, oy))
            slick = OilSlick(ox, oy)
            self.slicks.append(slick)
            particles.burst(ox, oy, [(20, 20, 30), (60, 40, 80)], 6, 2, 15, 2)
            play_sfx("oil_splat")

        # Phase 2+: place one slick on boss patrol path ahead for self-damage
        if (boss.current_phase_idx >= 1 and not self._patrol_slick_placed and
                self.timer > 50):
            ahead_t = (boss.path_t + 0.1) % 1.0
            ax, ay = boss._get_path_position(ahead_t)
            slick = OilSlick(int(ax), int(ay))
            self.slicks.append(slick)
            particles.burst(int(ax), int(ay), [(20, 20, 30), (60, 40, 80)], 6, 2, 15, 2)
            self._patrol_slick_placed = True

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
        # Phase 3: second ring
        self.ring2_radius = 0
        self.ring2_active = False
        self.ring2_hit_players = set()
        self._do_double = False

    def play_start_sfx(self):
        play_sfx("boss_rumble")

    def start(self, boss):
        super().start(boss)
        self.ring_radius = 0
        self.ring_active = False
        self.ring_cx = boss.rect.centerx
        self.ring_cy = boss.rect.centery
        self.hit_players = set()
        self.ring_speed = 5 + boss.current_phase_idx
        self.ring_width = 18 + boss.current_phase_idx * 3
        self._do_double = boss.current_phase_idx >= 2
        self.ring2_radius = 0
        self.ring2_active = False
        self.ring2_hit_players = set()

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
            play_sfx("boss_slam")

        # Launch second ring after delay (phase 3)
        if self._do_double and not self.ring2_active and self.timer == 60:
            self.ring2_active = True

        if self.ring_active:
            self.ring_radius += self.ring_speed

            for p in players:
                if not p.alive or id(p) in self.hit_players:
                    continue
                dist = math.hypot(p.rect.centerx - self.ring_cx,
                                  p.rect.centery - self.ring_cy)
                if abs(dist - self.ring_radius) < self.ring_width + 15:
                    if hasattr(boss, 'shake') and boss.shake:
                        p.take_hit(boss.shake)
                    self.hit_players.add(id(p))

            if self.ring_radius >= self.max_radius:
                self.ring_active = False

        if self.ring2_active:
            self.ring2_radius += self.ring_speed
            for p in players:
                if not p.alive or id(p) in self.ring2_hit_players:
                    continue
                dist = math.hypot(p.rect.centerx - self.ring_cx,
                                  p.rect.centery - self.ring_cy)
                if abs(dist - self.ring2_radius) < self.ring_width + 15:
                    if hasattr(boss, 'shake') and boss.shake:
                        p.take_hit(boss.shake)
                    self.ring2_hit_players.add(id(p))
            if self.ring2_radius >= self.max_radius:
                self.ring2_active = False

        if self.timer >= self.DURATION:
            self.active = False
            return True
        return False

    def _draw_ring(self, screen, cx, cy, radius):
        """Draw a single expanding ring."""
        if radius <= 0:
            return
        ring_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        alpha = max(30, 180 - int(radius * 0.5))
        color = (255, 100, 30, alpha)
        if radius > 3:
            pygame.draw.circle(ring_surf, color, (cx, cy), int(radius), self.ring_width)
        if radius > 5:
            inner_alpha = max(20, alpha - 40)
            pygame.draw.circle(ring_surf, (255, 200, 80, inner_alpha),
                               (cx, cy), int(radius), 2)
        screen.blit(ring_surf, (0, 0))

    def draw(self, screen, boss):
        if not self.ring_active and not self.ring2_active:
            # Telegraph: pulsing glow at boss center
            if self.timer < 30 and (self.timer // 4) % 2 == 0:
                glow_surf = pygame.Surface((60, 60), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (255, 100, 30, 100), (30, 30), 28)
                screen.blit(glow_surf, (boss.rect.centerx - 30, boss.rect.centery - 30))
            return

        if self.ring_active:
            self._draw_ring(screen, self.ring_cx, self.ring_cy, self.ring_radius)
        if self.ring2_active:
            self._draw_ring(screen, self.ring_cx, self.ring_cy, self.ring2_radius)


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
                m.turn_rate = 0.07 + boss.current_phase_idx * 0.01
                self.missiles.append(m)
                particles.burst(boss.rect.centerx, boss.rect.centery,
                                [(255, 120, 30), SOLAR_YELLOW], 4, 3, 15, 2)
                play_sfx("missile_launch")

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
                    play_sfx("missile_hit")
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
        # 5-tire aimed fan spread
        self.fire_times = sorted([random.randint(10, 50) for _ in range(5)])
        self._fan_idx = 0

    def update(self, boss, players, particles, dt=1):
        self.timer += 1

        alive_players = [p for p in players if p.alive]
        while self.fire_times and self.timer >= self.fire_times[0]:
            self.fire_times.pop(0)
            # Aimed fan spread at player: 5 tires ±0.4 rad
            angle = random.uniform(0, 2 * math.pi)
            if alive_players:
                target = random.choice(alive_players)
                dx = target.rect.centerx - boss.rect.centerx
                dy = target.rect.centery - boss.rect.centery
                base_angle = math.atan2(dy, dx)
                spread = (self._fan_idx - 2) * 0.2  # -0.4, -0.2, 0, 0.2, 0.4
                angle = base_angle + spread
                self._fan_idx += 1
            speed = 4.0 + boss.current_phase_idx * 0.5
            tire = BouncingTire(boss.rect.centerx, boss.rect.centery, angle, speed)
            self.tires.append(tire)
            particles.burst(boss.rect.centerx, boss.rect.centery,
                            [(80, 80, 90), (50, 50, 60)], 3, 2, 10, 2)
            play_sfx("tire_launch")

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
# New Attack Patterns
# ---------------------------------------------------------------------------

class DriftChase(AttackPattern):
    """Boss breaks patrol, chases nearest player at high speed.
    Leaves damaging tire marks behind. Phases 2-3.
    Handles collision internally (MM pattern)."""
    NAME = "drift_chase"
    DURATION = 200
    WEIGHT = 1.0

    def __init__(self):
        super().__init__()
        self.tire_marks = []
        self.chasing = False
        self.returning = False
        self.telegraph_frames = 45
        self.chase_speed = 5.0
        self.saved_path_t = 0.0
        self.return_target = (0, 0)
        self.hit_players = set()

    def start(self, boss):
        super().start(boss)
        self.tire_marks = []
        self.chasing = False
        self.returning = False
        self.hit_players = set()
        self.saved_path_t = boss.path_t

    def update(self, boss, players, particles, dt=1):
        self.timer += 1

        alive_players = [p for p in players if p.alive]

        # Telegraph phase: shake + red glow
        if self.timer < self.telegraph_frames:
            boss.rect.x += random.randint(-3, 3)
            boss.rect.y += random.randint(-3, 3)
            return False

        # Start chase
        if not self.chasing and not self.returning and self.timer == self.telegraph_frames:
            self.chasing = True

        if self.chasing:
            if alive_players:
                target = min(alive_players, key=lambda p: math.hypot(
                    p.rect.centerx - boss.rect.centerx,
                    p.rect.centery - boss.rect.centery))
                dx = target.rect.centerx - boss.rect.centerx
                dy = target.rect.centery - boss.rect.centery
                dist = math.sqrt(dx * dx + dy * dy)
                if dist > 1:
                    boss.rect.x += int(dx / dist * self.chase_speed)
                    boss.rect.y += int(dy / dist * self.chase_speed)

            # Leave tire marks
            if self.timer % 5 == 0:
                self.tire_marks.append({
                    'x': boss.rect.centerx,
                    'y': boss.rect.centery,
                    'life': 120,
                    'hit_players': set(),
                })
                particles.emit(boss.rect.centerx + random.randint(-10, 10),
                               boss.rect.centery + random.randint(-10, 10),
                               (40, 40, 50), [random.uniform(-1, 1), random.uniform(-1, 1)], 15, 2)

            # Check boss-player collision during chase
            for p in alive_players:
                if id(p) not in self.hit_players and boss.rect.colliderect(p.rect):
                    if hasattr(boss, 'shake') and boss.shake:
                        p.take_hit(boss.shake)
                    self.hit_players.add(id(p))

            # Chase for ~100 frames then return
            if self.timer >= self.telegraph_frames + 100:
                self.chasing = False
                self.returning = True
                self.return_target = boss._get_path_position(self.saved_path_t)

        if self.returning:
            # Move back to patrol path
            tx, ty = self.return_target
            dx = tx - boss.rect.centerx
            dy = ty - boss.rect.centery
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 5:
                boss.rect.x += int(dx / dist * 4)
                boss.rect.y += int(dy / dist * 4)
            else:
                boss.rect.center = (int(tx), int(ty))
                boss.path_t = self.saved_path_t
                self.returning = False

        # Update tire marks — damage + decay
        for mark in self.tire_marks[:]:
            mark['life'] -= 1
            if mark['life'] <= 0:
                self.tire_marks.remove(mark)
                continue
            mark_rect = pygame.Rect(mark['x'] - 8, mark['y'] - 8, 16, 16)
            for p in alive_players:
                if (p.alive and id(p) not in mark['hit_players'] and
                        p.invincible_timer <= 0 and not p.ghost_mode):
                    if mark_rect.colliderect(p.rect):
                        if hasattr(boss, 'shake') and boss.shake:
                            p.take_hit(boss.shake)
                        mark['hit_players'].add(id(p))

        if self.timer >= self.DURATION:
            # Force return to patrol
            if self.chasing or self.returning:
                tx, ty = boss._get_path_position(self.saved_path_t)
                boss.rect.center = (int(tx), int(ty))
                boss.path_t = self.saved_path_t
            self.tire_marks.clear()
            self.active = False
            return True
        return False

    def draw(self, screen, boss):
        # Telegraph: red glow
        if self.timer < self.telegraph_frames:
            if (self.timer // 4) % 2 == 0:
                glow = pygame.Surface((boss.rect.w + 20, boss.rect.h + 20), pygame.SRCALPHA)
                pygame.draw.ellipse(glow, (255, 50, 30, 80),
                                    (0, 0, boss.rect.w + 20, boss.rect.h + 20))
                screen.blit(glow, (boss.rect.x - 10, boss.rect.y - 10))
            return

        # Draw tire marks
        for mark in self.tire_marks:
            alpha = min(150, int(150 * (mark['life'] / 120.0)))
            mark_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.ellipse(mark_surf, (30, 30, 40, alpha), (0, 0, 16, 16))
            screen.blit(mark_surf, (mark['x'] - 8, mark['y'] - 8))


class MonsterStomp(AttackPattern):
    """Boss jumps to position near player, lands with DUAL shockwave.
    Phase 3 only. Inner ring (fast, short) + outer ring (slow, long).
    Safe zone = gap between rings. Handles collision internally."""
    NAME = "monster_stomp"
    DURATION = 150
    WEIGHT = 0.9

    def __init__(self):
        super().__init__()
        self.telegraph_frames = 40
        self.jumping = False
        self.landing = False
        self.landed = False
        self.land_x = 0
        self.land_y = 0
        self.saved_path_t = 0.0
        self.original_pos = (0, 0)
        self.scale_anim = 1.0
        # Dual rings
        self.inner_ring = {'radius': 0, 'speed': 7, 'max': 200, 'active': False}
        self.outer_ring = {'radius': 0, 'speed': 3, 'max': 350, 'active': False}
        self.inner_hit = set()
        self.outer_hit = set()

    def start(self, boss):
        super().start(boss)
        self.jumping = False
        self.landing = False
        self.landed = False
        self.scale_anim = 1.0
        self.saved_path_t = boss.path_t
        self.original_pos = (boss.rect.centerx, boss.rect.centery)
        self.inner_ring = {'radius': 0, 'speed': 7, 'max': 200, 'active': False}
        self.outer_ring = {'radius': 0, 'speed': 3, 'max': 350, 'active': False}
        self.inner_hit = set()
        self.outer_hit = set()

        # Target: near a player
        alive = [p for p in [] if p.alive]  # will be set in update
        self.land_x = boss.rect.centerx
        self.land_y = boss.rect.centery

    def update(self, boss, players, particles, dt=1):
        self.timer += 1
        alive_players = [p for p in players if p.alive]

        # Telegraph: pulsing target circle
        if self.timer < self.telegraph_frames:
            if alive_players and self.timer == 1:
                target = random.choice(alive_players)
                self.land_x = target.rect.centerx + random.randint(-40, 40)
                self.land_y = target.rect.centery + random.randint(-40, 40)
                self.land_x = max(60, min(SCREEN_WIDTH - 60, self.land_x))
                self.land_y = max(60, min(SCREEN_HEIGHT - 60, self.land_y))
            boss.rect.x += random.randint(-2, 2)
            return False

        # Jump phase (shrink animation)
        if not self.jumping and not self.landed:
            self.jumping = True
            self.scale_anim = 1.0

        if self.jumping:
            self.scale_anim += 0.05
            if self.scale_anim >= 1.5:
                # Land at target
                self.jumping = False
                self.landed = True
                boss.rect.center = (self.land_x, self.land_y)
                self.inner_ring['active'] = True
                self.outer_ring['active'] = True
                particles.burst(self.land_x, self.land_y,
                                [SOLAR_YELLOW, SOLAR_WHITE, NEON_MAGENTA], 20, 6, 40, 4)
                play_sfx("crash")

        if self.landed:
            # Expand rings
            for ring in [self.inner_ring, self.outer_ring]:
                if ring['active']:
                    ring['radius'] += ring['speed']
                    if ring['radius'] >= ring['max']:
                        ring['active'] = False

            # Check inner ring collision
            if self.inner_ring['active']:
                for p in alive_players:
                    if not p.alive or id(p) in self.inner_hit:
                        continue
                    if p.invincible_timer > 0 or p.ghost_mode:
                        continue
                    dist = math.hypot(p.rect.centerx - self.land_x,
                                      p.rect.centery - self.land_y)
                    if abs(dist - self.inner_ring['radius']) < 20:
                        if hasattr(boss, 'shake') and boss.shake:
                            p.take_hit(boss.shake)
                        self.inner_hit.add(id(p))

            # Check outer ring collision
            if self.outer_ring['active']:
                for p in alive_players:
                    if not p.alive or id(p) in self.outer_hit:
                        continue
                    if p.invincible_timer > 0 or p.ghost_mode:
                        continue
                    dist = math.hypot(p.rect.centerx - self.land_x,
                                      p.rect.centery - self.land_y)
                    if abs(dist - self.outer_ring['radius']) < 20:
                        if hasattr(boss, 'shake') and boss.shake:
                            p.take_hit(boss.shake)
                        self.outer_hit.add(id(p))

            # Return to patrol after rings finish
            if not self.inner_ring['active'] and not self.outer_ring['active']:
                # Move back to patrol
                tx, ty = boss._get_path_position(self.saved_path_t)
                boss.rect.center = (int(tx), int(ty))
                boss.path_t = self.saved_path_t

        if self.timer >= self.DURATION:
            tx, ty = boss._get_path_position(self.saved_path_t)
            boss.rect.center = (int(tx), int(ty))
            boss.path_t = self.saved_path_t
            self.active = False
            return True
        return False

    def draw(self, screen, boss):
        # Telegraph: pulsing target circle
        if self.timer < self.telegraph_frames:
            pulse = 0.5 + 0.5 * math.sin(self.timer * 0.3)
            radius = int(30 + 20 * pulse)
            target_surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            alpha = int(100 + 80 * pulse)
            pygame.draw.circle(target_surf, (255, 50, 30, alpha),
                               (radius + 2, radius + 2), radius, 3)
            screen.blit(target_surf, (self.land_x - radius - 2, self.land_y - radius - 2))
            return

        # Draw dual rings
        ring_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for ring, color in [(self.inner_ring, (255, 200, 60)),
                            (self.outer_ring, (255, 100, 30))]:
            if ring['active'] and ring['radius'] > 5:
                alpha = max(30, 180 - int(ring['radius'] * 0.4))
                pygame.draw.circle(ring_surf, (*color, alpha),
                                   (self.land_x, self.land_y), int(ring['radius']), 12)
        screen.blit(ring_surf, (0, 0))


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

    def __init__(self, particles, shake=None, evolution_tier=1, track_bg=None):
        self.shake = shake
        self.track_bg = track_bg  # Track background for track-aware movement
        evo_scale = 1.0 + (evolution_tier - 1) * 0.3
        self.MAX_HP = int(350 * evo_scale)
        self.path_t = 0.0  # parametric position along path [0..1)
        self.path_speed = 0.003  # base speed around path
        self.facing_angle = 0.0
        self.underglow_pulse = 0
        self.tire_rot = 0.0
        self.oil_slicks = []  # persistent oil slicks from attacks
        self._on_curve = False  # True when boss is on a sharp curve (vulnerability)
        super().__init__(SCREEN_WIDTH // 2, self.PATH_MARGIN, particles, tier=evolution_tier)

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
            vulnerability_after_attack=50,
            speed_mult=1.0,
            color=NEON_CYAN,
        )

        # Phase 2: HP 66% - 33%
        phase2_attacks = [
            OilSlickDrop(),
            ShockwaveRing(),
            DriftChase(),
            HomingMissileAttack(count_range=(3, 4)),
        ]
        phase2 = BossPhase(
            hp_threshold=0.66,
            attacks=phase2_attacks,
            vulnerability_after_attack=36,
            speed_mult=1.3,
            color=SOLAR_YELLOW,
        )

        # Phase 3: HP 33% - 0%
        phase3_attacks = [
            OilSlickDrop(),
            ShockwaveRing(),
            DriftChase(),
            MonsterStomp(),
            TireBarrage(),
            HomingMissileAttack(count_range=(4, 5)),
        ]
        phase3 = BossPhase(
            hp_threshold=0.33,
            attacks=phase3_attacks,
            vulnerability_after_attack=25,
            speed_mult=1.6,
            color=NEON_MAGENTA,
        )

        return [phase1, phase2, phase3]

    def _create_surface(self):
        """Draw the monster truck procedurally -- 100x100 px top-down view."""
        tier = self.tier
        if tier >= 3:
            return self._create_surface_v3()

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

    def _create_surface_v3(self):
        """V3: Holographic monster truck — per-tire underglow, 3-tone body, hub spokes."""
        surf = pygame.Surface((100, 100), pygame.SRCALPHA)
        phase_color = self.current_phase.color if hasattr(self, 'current_phase') else NEON_CYAN
        tire_rot = getattr(self, 'tire_rot', 0.0)
        underglow_pulse = getattr(self, 'underglow_pulse', 0)

        # --- Per-tire underglow ellipses (individual glow per wheel) ---
        glow_a = int(50 + 30 * math.sin(underglow_pulse * 0.08))
        for tx, ty in [(16, 24), (78, 24), (16, 72), (78, 72)]:
            pygame.draw.ellipse(surf, (*phase_color[:3], glow_a),
                                (tx - 16, ty - 12, 32, 24))

        # --- 3-tone body panel shading ---
        body_rect = (22, 18, 56, 64)
        # Dark base
        pygame.draw.rect(surf, (40, 40, 55), body_rect, border_radius=8)
        # Center highlight panel
        pygame.draw.rect(surf, (70, 70, 90), (28, 24, 44, 52), border_radius=6)
        # Bright center strip
        pygame.draw.rect(surf, (100, 100, 120), (38, 20, 24, 60), border_radius=4)

        # Cab
        cab_rect = (30, 28, 40, 40)
        pygame.draw.rect(surf, (55, 55, 70), cab_rect, border_radius=4)
        pygame.draw.rect(surf, phase_color, cab_rect, 1, border_radius=4)

        # Windshield with scan line
        pygame.draw.rect(surf, (*phase_color[:3], 100), (34, 30, 32, 12), border_radius=2)
        scan_y = 30 + int((underglow_pulse * 0.3) % 12)
        pygame.draw.line(surf, (*phase_color[:3], 160), (34, scan_y), (66, scan_y), 1)

        # --- Tires with hub spoke animation ---
        for tx, ty in [(16, 24), (78, 24), (16, 72), (78, 72)]:
            pygame.draw.ellipse(surf, (25, 25, 35), (tx - 12, ty - 8, 24, 16))
            # Neon tire rim
            pygame.draw.ellipse(surf, phase_color, (tx - 12, ty - 8, 24, 16), 2)
            # Tread
            for i in range(3):
                offset = int((tire_rot + i * 5) % 14) - 7
                lx = tx + offset
                pygame.draw.line(surf, (40, 40, 50), (lx, ty - 6), (lx, ty + 6), 1)
            # Hub with 4 spokes
            for spoke in range(4):
                angle = tire_rot * 0.1 + spoke * (math.pi / 2)
                sx = tx + int(math.cos(angle) * 5)
                sy = ty + int(math.sin(angle) * 3)
                pygame.draw.line(surf, (120, 120, 140), (tx, ty), (sx, sy), 1)
            pygame.draw.circle(surf, phase_color, (tx, ty), 3)

        # --- Roof lights ---
        for lx in [35, 45, 55, 65]:
            pygame.draw.circle(surf, phase_color, (lx, 20), 3)
            pygame.draw.circle(surf, SOLAR_WHITE, (lx, 20), 1)

        # --- Bull bar ---
        pygame.draw.rect(surf, (90, 90, 110), (26, 14, 48, 4))
        pygame.draw.rect(surf, phase_color, (26, 14, 48, 4), 1)

        # --- Exhaust stacks with glow ---
        for ex in [32, 68]:
            pygame.draw.rect(surf, (70, 70, 85), (ex - 3, 78, 6, 8))
            pygame.draw.circle(surf, (255, 100, 30), (ex, 86), 4)
            pygame.draw.circle(surf, (255, 200, 60), (ex, 86), 2)

        # Chrome edge highlights
        pygame.draw.rect(surf, (*phase_color[:3], 40), body_rect, 2, border_radius=8)

        return surf

    def _get_path_position(self, t):
        """Calculate (x, y) position along the patrol path.

        When track_bg is available: boss follows track center near top of screen,
        weaving side-to-side on straights. Falls back to rounded rectangle patrol.
        """
        if self.track_bg:
            return self._get_track_path_position(t)
        return self._get_rect_path_position(t)

    def _get_track_path_position(self, t):
        """Boss position on-track: follows track center at top portion of screen.

        Uses t to create a weaving motion around track center.
        """
        # Boss stays near top 20-30% of screen
        screen_y = SCREEN_HEIGHT * (0.15 + 0.1 * math.sin(t * 2 * math.pi))
        world_y = self.track_bg.scroll_offset_value + screen_y
        bounds = self.track_bg.get_track_bounds_at_world_y(world_y)
        if bounds is None:
            return (SCREEN_WIDTH // 2, int(screen_y))

        left, center_x, right = bounds
        # Weave side-to-side within track bounds
        weave = math.sin(t * 6 * math.pi) * (right - left) * 0.25
        x = max(left + 50, min(right - 50, center_x + weave))

        # Detect if on a curve (for vulnerability mechanic)
        ahead_bounds = self.track_bg.get_track_bounds_at_world_y(world_y + 50)
        if ahead_bounds:
            curve_diff = abs(ahead_bounds[1] - center_x)
            self._on_curve = curve_diff > 15
        else:
            self._on_curve = False

        return (x, int(screen_y))

    def _get_rect_path_position(self, t):
        """Original rounded rectangular patrol path (fallback).

        t ranges from 0 to 1, traversing the path clockwise.
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
            return (m + cr + frac * straight_w, m)
        elif seg_idx == 1:
            angle = -math.pi / 2 + frac * (math.pi / 2)
            return (m + w - cr + math.cos(angle) * cr,
                    m + cr + math.sin(angle) * cr)
        elif seg_idx == 2:
            return (m + w, m + cr + frac * straight_h)
        elif seg_idx == 3:
            angle = 0 + frac * (math.pi / 2)
            return (m + w - cr + math.cos(angle) * cr,
                    m + h - cr + math.sin(angle) * cr)
        elif seg_idx == 4:
            return (m + w - cr - frac * straight_w, m + h)
        elif seg_idx == 5:
            angle = math.pi / 2 + frac * (math.pi / 2)
            return (m + cr + math.cos(angle) * cr,
                    m + h - cr + math.sin(angle) * cr)
        elif seg_idx == 6:
            return (m, m + h - cr - frac * straight_h)
        else:
            angle = math.pi + frac * (math.pi / 2)
            return (m + cr + math.cos(angle) * cr,
                    m + cr + math.sin(angle) * cr)

    def _update_movement(self, players, dt=1):
        """Move along patrol path. Slow on curves and during vulnerability."""
        vuln_mult = 0.4 if self.vulnerable else 1.0
        # Slow down on curves (creates vulnerability windows)
        curve_mult = 0.5 if self._on_curve else 1.0
        speed = self.path_speed * self.current_phase.speed_mult * vuln_mult * curve_mult
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

        # V3: maintain afterimage trail (3 positions, updated every 4 frames)
        if self.tier >= 3:
            if not hasattr(self, '_v3_trail'):
                self._v3_trail = []
                self._v3_trail_tick = 0
            self._v3_trail_tick += 1
            if self._v3_trail_tick % 4 == 0:
                self._v3_trail.insert(0, (old_x, old_y))
                if len(self._v3_trail) > 3:
                    self._v3_trail.pop()

    def _draw_extras(self, screen):
        """Draw oil slicks, underglow trail, and phase indicator."""
        # Draw persistent oil slicks
        for slick in self.oil_slicks[:]:
            if slick.alive:
                slick.update()
                screen.blit(slick.image, slick.rect)
            else:
                self.oil_slicks.remove(slick)

        # V3: holographic afterimage trail (3 fading ghost blits)
        if (self.tier >= 3 and self.alive and
                self.active and hasattr(self, '_v3_trail')):
            for i, (tx, ty) in enumerate(self._v3_trail):
                ghost_alpha = max(10, 50 - i * 16)
                ghost = self.image.copy()
                ghost.set_alpha(ghost_alpha)
                screen.blit(ghost, (tx - self.image.get_width() // 2,
                                    ty - self.image.get_height() // 2))

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
