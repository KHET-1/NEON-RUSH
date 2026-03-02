"""Excitebike Boss — Armored Motorcycle side-scroller boss fight.

A large armored bike that drives alongside the player on the right side
of the screen. 3 phases with escalating attack patterns:
  Phase 1: Shockwave + Missile Barrage
  Phase 2: + Charge Attack
  Phase 3: + Combo (Shockwave -> Missiles)

Damage methods:
  1. Ram during vulnerability window
  2. Heat bolt projectiles
  3. Environmental ramp hazards
"""

import pygame
import random
import math

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    NEON_CYAN, NEON_MAGENTA, SOLAR_YELLOW, SOLAR_WHITE,
    ROAD_LEFT, ROAD_RIGHT, ROAD_COLOR,
)
from core.sound import play_sfx
from core.fonts import load_font
from shared.boss_base import Boss, BossPhase, AttackPattern, HeatBolt


# ---------------------------------------------------------------------------
# Projectile: Homing Missile
# ---------------------------------------------------------------------------

class HomingMissile(pygame.sprite.Sprite):
    """Small homing missile that tracks the nearest alive player."""

    def __init__(self, x, y, target, speed=3.5):
        super().__init__()
        self.image = pygame.Surface((10, 18), pygame.SRCALPHA)
        # Missile body -- red cone with orange exhaust
        pygame.draw.polygon(self.image, (255, 60, 30), [(5, 0), (10, 14), (0, 14)])
        pygame.draw.polygon(self.image, (255, 160, 40), [(3, 14), (7, 14), (5, 18)])
        pygame.draw.rect(self.image, SOLAR_WHITE, (4, 2, 2, 4))
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = [float(x), float(y)]
        self.speed = speed
        self.target = target
        self.turn_rate = 0.10  # was 0.06 — tighter tracking
        self.angle = math.pi / 2  # pointing down initially
        self.alive = True
        self.life = 180  # was 300 — shorter but deadlier

    def update(self):
        self.life -= 1
        if self.life <= 0:
            self.alive = False
            self.kill()
            return

        # Track target if alive
        if self.target and self.target.alive:
            dx = self.target.rect.centerx - self.pos[0]
            dy = self.target.rect.centery - self.pos[1]
            desired = math.atan2(dy, dx)
            # Smooth turning
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

        # Off-screen cull
        if (self.rect.top > SCREEN_HEIGHT + 40 or self.rect.bottom < -40 or
                self.rect.left > SCREEN_WIDTH + 40 or self.rect.right < -40):
            self.alive = False
            self.kill()


# ---------------------------------------------------------------------------
# Environmental Hazard: Ramp
# ---------------------------------------------------------------------------

class RampHazard(pygame.sprite.Sprite):
    """Scrolling ramp that damages the boss on overlap."""

    def __init__(self, x, scroll_speed):
        super().__init__()
        self.width = 80
        self.height = 30
        self.image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        # Ramp shape -- angled yellow/orange block
        points = [(0, self.height), (10, 0), (self.width - 10, 0), (self.width, self.height)]
        pygame.draw.polygon(self.image, (200, 140, 30), points)
        pygame.draw.polygon(self.image, SOLAR_YELLOW, points, 2)
        # Chevron markings
        for i in range(3):
            cx = 20 + i * 20
            pygame.draw.lines(self.image, SOLAR_WHITE, False,
                              [(cx - 6, self.height - 5), (cx, 8), (cx + 6, self.height - 5)], 2)
        self.rect = self.image.get_rect(center=(x, -40))
        self.scroll_speed = scroll_speed
        self.alive = True
        self.hit_boss = False  # track if it already damaged boss this pass

    def update(self, scroll_speed=None):
        if scroll_speed is not None:
            self.scroll_speed = scroll_speed
        self.rect.y += max(3, int(self.scroll_speed))
        if self.rect.top > SCREEN_HEIGHT + 20:
            self.alive = False
            self.kill()


# ---------------------------------------------------------------------------
# Attack Patterns
# ---------------------------------------------------------------------------

class ShockwaveAttack(AttackPattern):
    """Boss slams ground sending a horizontal shockwave the player must jump over."""

    NAME = "shockwave"
    DURATION = 150
    WEIGHT = 1.0

    def __init__(self):
        super().__init__()
        self.wave_y = 0
        self.wave_active = False
        self.wave_speed = 5
        self.wave_height = 20
        self.telegraph_done = False
        self.damage_dealt = set()
        # Phase 3: second delayed shockwave
        self.wave2_y = 0
        self.wave2_active = False
        self.wave2_delay = 30  # frames after first wave
        self.wave2_damage_dealt = set()

    def play_start_sfx(self):
        play_sfx("boss_rumble")

    def start(self, boss):
        super().start(boss)
        self.wave_y = 0
        self.wave_active = False
        self.telegraph_done = False
        self.damage_dealt = set()
        self.wave_speed = 5 + boss.current_phase_idx * 2
        self.wave2_y = 0
        self.wave2_active = False
        self.wave2_damage_dealt = set()
        self._do_double = boss.current_phase_idx >= 2

    def update(self, boss, players, particles, dt=1):
        self.timer += 1

        # Telegraph phase: boss shakes for first 40 frames
        if self.timer < 40:
            boss.rect.x += random.randint(-3, 3)
            return False

        # Release shockwave
        if not self.telegraph_done:
            self.telegraph_done = True
            self.wave_active = True
            self.wave_y = boss.rect.bottom
            play_sfx("boss_slam")

        # Launch second wave after delay (phase 3)
        if (self._do_double and not self.wave2_active and
                self.timer >= 40 + self.wave2_delay):
            self.wave2_active = True
            self.wave2_y = boss.rect.bottom

        # Advance shockwave(s) downward
        if self.wave_active:
            self.wave_y += self.wave_speed
        if self.wave2_active:
            self.wave2_y += self.wave_speed
            # Check collision with players (wave 1)
            wave_rect = pygame.Rect(ROAD_LEFT, int(self.wave_y) - self.wave_height // 2,
                                    ROAD_RIGHT - ROAD_LEFT, self.wave_height)
            for p in players:
                if not p.alive or id(p) in self.damage_dealt:
                    continue
                if (wave_rect.colliderect(p.rect) and p.vel_y >= 0 and
                        p.rect.bottom >= self.wave_y - 25):
                    if hasattr(boss, 'shake') and boss.shake:
                        p.take_hit(boss.shake)
                    self.damage_dealt.add(id(p))

            # Wave off-screen
            if self.wave_y > SCREEN_HEIGHT + 30:
                self.wave_active = False

        # Check collision for wave 2
        if self.wave2_active:
            wave2_rect = pygame.Rect(ROAD_LEFT, int(self.wave2_y) - self.wave_height // 2,
                                     ROAD_RIGHT - ROAD_LEFT, self.wave_height)
            for p in players:
                if not p.alive or id(p) in self.wave2_damage_dealt:
                    continue
                if (wave2_rect.colliderect(p.rect) and p.vel_y >= 0 and
                        p.rect.bottom >= self.wave2_y - 25):
                    if hasattr(boss, 'shake') and boss.shake:
                        p.take_hit(boss.shake)
                    self.wave2_damage_dealt.add(id(p))
            if self.wave2_y > SCREEN_HEIGHT + 30:
                self.wave2_active = False

        if self.timer >= self.DURATION:
            self.active = False
            return True
        return False

    def _draw_wave(self, screen, wy, boss):
        """Draw a single shockwave band at y position."""
        alpha = max(60, 200 - abs(wy - boss.rect.bottom))
        wave_surf = pygame.Surface((ROAD_RIGHT - ROAD_LEFT, self.wave_height), pygame.SRCALPHA)
        pygame.draw.rect(wave_surf, (255, 100, 30, min(255, alpha)),
                         (0, 0, ROAD_RIGHT - ROAD_LEFT, self.wave_height))
        pygame.draw.line(wave_surf, (255, 220, 100, min(255, alpha + 50)),
                         (0, self.wave_height // 2),
                         (ROAD_RIGHT - ROAD_LEFT, self.wave_height // 2), 3)
        screen.blit(wave_surf, (ROAD_LEFT, wy - self.wave_height // 2))

    def draw(self, screen, boss):
        if not self.wave_active and not self.wave2_active:
            # Telegraph: draw warning lines
            if self.timer < 40 and (self.timer // 5) % 2 == 0:
                pygame.draw.line(screen, (255, 80, 30),
                                 (ROAD_LEFT, boss.rect.bottom + 10),
                                 (ROAD_RIGHT, boss.rect.bottom + 10), 3)
            return

        if self.wave_active:
            self._draw_wave(screen, int(self.wave_y), boss)
        if self.wave2_active:
            self._draw_wave(screen, int(self.wave2_y), boss)


class MissileBarrageAttack(AttackPattern):
    """Boss fires 3-5 homing missiles that track the nearest alive player."""

    NAME = "missile_barrage"
    DURATION = 200
    WEIGHT = 1.0

    def __init__(self, missile_count=4):
        super().__init__()
        self.base_count = missile_count
        self.missiles = []
        self.fire_times = []

    def start(self, boss):
        super().start(boss)
        self.missiles = []
        count = random.randint(max(3, self.base_count - 1), self.base_count + 1)
        # Stagger missile launches across the first 90 frames
        self.fire_times = sorted([random.randint(20, 90) for _ in range(count)])

    def update(self, boss, players, particles, dt=1):
        self.timer += 1

        # Fire missiles at scheduled times
        alive_players = [p for p in players if p.alive]
        while self.fire_times and self.timer >= self.fire_times[0]:
            self.fire_times.pop(0)
            if alive_players:
                target = random.choice(alive_players)
                m = HomingMissile(boss.rect.centerx - 20, boss.rect.centery,
                                  target, speed=4.0 + boss.current_phase.speed_mult)
                m.turn_rate = 0.10 + boss.current_phase_idx * 0.02
                self.missiles.append(m)
                particles.burst(boss.rect.centerx - 20, boss.rect.centery,
                                [(255, 120, 30), (255, 200, 60)], 4, 3, 15, 2)
                play_sfx("missile_launch")

        # Update missiles
        for m in self.missiles[:]:
            m.update()
            if not m.alive:
                if m in self.missiles:
                    self.missiles.remove(m)
                continue
            # Check player collision
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
            # Clean up remaining missiles
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
                # Exhaust trail glow
                ex = m.rect.centerx + random.randint(-2, 2)
                ey = m.rect.centery + random.randint(-2, 2)
                trail_size = random.randint(2, 5)
                trail_surf = pygame.Surface((trail_size * 2, trail_size * 2), pygame.SRCALPHA)
                pygame.draw.circle(trail_surf, (255, 140, 40, 120),
                                   (trail_size, trail_size), trail_size)
                screen.blit(trail_surf, (ex - trail_size, ey - trail_size))


class ChargeAttack(AttackPattern):
    """Boss telegraphs then charges horizontally across the road."""

    NAME = "charge"
    DURATION = 180
    WEIGHT = 0.8

    def __init__(self):
        super().__init__()
        self.telegraph_frames = 60
        self.charging = False
        self.charge_dir = -1  # charge left toward player
        self.charge_speed = 12
        self.original_x = 0
        self.warning_y = 0
        self.hit_players = set()
        self.charges_done = 0
        self.max_charges = 1
        self._between_charges = False
        self._between_timer = 0

    def play_start_sfx(self):
        play_sfx("boss_rumble")

    def start(self, boss):
        super().start(boss)
        self.charging = False
        self.original_x = boss.rect.centerx
        self.warning_y = boss.rect.centery
        # Phase 2+: random direction
        self.charge_dir = random.choice([-1, 1]) if boss.current_phase_idx >= 1 else -1
        self.hit_players = set()
        # Phase 3: double charge
        self.max_charges = 2 if boss.current_phase_idx >= 2 else 1
        self.charges_done = 0
        self._between_charges = False
        self._between_timer = 0
        self.charge_speed = 12 + boss.current_phase_idx * 3
        self.telegraph_frames = max(30, 50 - boss.current_phase_idx * 10)

    def update(self, boss, players, particles, dt=1):
        self.timer += 1

        # Between charges pause
        if self._between_charges:
            self._between_timer += 1
            if self._between_timer >= 30:
                self._between_charges = False
                self.charging = True
                self.charge_dir = -self.charge_dir  # reverse direction
                self.hit_players = set()
                play_sfx("charge_whoosh")
            return False

        if self.timer < self.telegraph_frames and self.charges_done == 0:
            # Telegraph: boss revs and shakes
            boss.rect.x += random.choice([-2, 2])
            return False

        if not self.charging and self.charges_done == 0 and self.timer >= self.telegraph_frames:
            self.charging = True
            play_sfx("charge_whoosh")

        if self.charging:
            boss.rect.x += self.charge_dir * int(self.charge_speed * boss.current_phase.speed_mult)
            # Emit exhaust particles
            particles.emit(boss.rect.right + 5, boss.rect.centery + random.randint(-10, 10),
                           (255, 140, 30), [4, random.uniform(-1, 1)], 20, 3)

            # Hit players
            for p in players:
                if p.alive and id(p) not in self.hit_players and boss.rect.colliderect(p.rect):
                    if hasattr(boss, 'shake') and boss.shake:
                        p.take_hit(boss.shake)
                    self.hit_players.add(id(p))

            # Went off edge — reverse or finish
            off_left = boss.rect.right < ROAD_LEFT - 50
            off_right = boss.rect.left > SCREEN_WIDTH + 50
            if off_left or off_right:
                self.charges_done += 1
                self.charging = False
                boss.rect.centerx = self.original_x
                if self.charges_done < self.max_charges:
                    self._between_charges = True
                    self._between_timer = 0

        if self.timer >= self.DURATION or (self.charges_done >= self.max_charges and not self.charging):
            boss.rect.centerx = self.original_x
            self.active = False
            return True
        return False

    def draw(self, screen, boss):
        if self.timer < self.telegraph_frames:
            # Warning line across the road at boss height
            progress = self.timer / self.telegraph_frames
            alpha = int(80 + 120 * progress)
            if (self.timer // 8) % 2 == 0:
                warn_surf = pygame.Surface((SCREEN_WIDTH, 6), pygame.SRCALPHA)
                pygame.draw.rect(warn_surf, (255, 50, 30, alpha), (0, 0, SCREEN_WIDTH, 6))
                screen.blit(warn_surf, (0, self.warning_y - 3))


class ComboAttack(AttackPattern):
    """Shockwave immediately followed by missile barrage."""

    NAME = "combo"
    DURATION = 240
    WEIGHT = 1.2

    def __init__(self):
        super().__init__()
        self.shockwave = ShockwaveAttack()
        self.missiles = MissileBarrageAttack(missile_count=4)
        self.phase = "shockwave"

    def start(self, boss):
        super().start(boss)
        self.phase = "shockwave"
        self.shockwave.start(boss)

    def update(self, boss, players, particles, dt=1):
        self.timer += 1

        if self.phase == "shockwave":
            done = self.shockwave.update(boss, players, particles, dt)
            if done:
                self.phase = "missiles"
                self.missiles.start(boss)
        elif self.phase == "missiles":
            done = self.missiles.update(boss, players, particles, dt)
            if done:
                self.active = False
                return True

        if self.timer >= self.DURATION:
            # Force cleanup
            for m in self.missiles.missiles:
                m.kill()
            self.missiles.missiles.clear()
            self.active = False
            return True
        return False

    def draw(self, screen, boss):
        if self.phase == "shockwave":
            self.shockwave.draw(screen, boss)
        elif self.phase == "missiles":
            self.missiles.draw(screen, boss)


# ---------------------------------------------------------------------------
# New Attack Patterns
# ---------------------------------------------------------------------------

class RampBarrage(AttackPattern):
    """Boss kicks 3-5 ramps backward at player. Phases 2-3.
    Risk/reward: jump onto ramp = launch + env damage to boss. Hit on ground = player damage."""
    NAME = "ramp_barrage"
    DURATION = 180
    WEIGHT = 0.9

    def __init__(self):
        super().__init__()
        self.ramp_projectiles = []
        self.fire_times = []

    def start(self, boss):
        super().start(boss)
        self.ramp_projectiles = []
        count = random.randint(3, 5)
        self.fire_times = sorted([random.randint(20, 120) for _ in range(count)])

    def update(self, boss, players, particles, dt=1):
        self.timer += 1

        # Fire ramps at scheduled times
        while self.fire_times and self.timer >= self.fire_times[0]:
            self.fire_times.pop(0)
            ry = boss.rect.centery + random.randint(-30, 30)
            self.ramp_projectiles.append({
                'x': float(boss.rect.left),
                'y': float(ry),
                'speed': random.uniform(8, 10),
                'width': 50,
                'height': 20,
                'alive': True,
                'hit_players': set(),
            })
            particles.burst(boss.rect.left, int(ry),
                            [SOLAR_YELLOW, (200, 140, 30)], 4, 3, 15, 2)

        # Update ramps — fly LEFT
        for ramp in self.ramp_projectiles:
            if ramp['alive']:
                ramp['x'] -= ramp['speed']
                if ramp['x'] < -80:
                    ramp['alive'] = False
                # Check player collision (ground hit = damage)
                ramp_rect = pygame.Rect(int(ramp['x']), int(ramp['y'] - ramp['height'] // 2),
                                        ramp['width'], ramp['height'])
                for p in players:
                    if not p.alive or id(p) in ramp['hit_players']:
                        continue
                    if ramp_rect.colliderect(p.rect):
                        # Airborne player = ramp deals environmental damage to boss
                        if hasattr(p, 'airborne') and p.airborne:
                            boss.take_damage(boss.ENVIRONMENTAL_DAMAGE, "environmental")
                            if hasattr(boss, 'shake') and boss.shake:
                                boss.shake.trigger(6, 18)
                            if boss.particles:
                                boss.particles.burst(
                                    int(ramp['x']), int(ramp['y']),
                                    [SOLAR_YELLOW, SOLAR_WHITE], 12, 5, 30, 3)
                            ramp['alive'] = False
                        else:
                            # Ground hit = player damage
                            if hasattr(boss, 'shake') and boss.shake:
                                p.take_hit(boss.shake)
                            ramp['hit_players'].add(id(p))

        self.ramp_projectiles = [r for r in self.ramp_projectiles if r['alive']]

        if self.timer >= self.DURATION:
            self.active = False
            return True
        return False

    def draw(self, screen, boss):
        for ramp in self.ramp_projectiles:
            if ramp['alive']:
                rx = int(ramp['x'])
                ry = int(ramp['y'] - ramp['height'] // 2)
                rw, rh = ramp['width'], ramp['height']
                surf = pygame.Surface((rw, rh), pygame.SRCALPHA)
                points = [(0, rh), (5, 0), (rw - 5, 0), (rw, rh)]
                pygame.draw.polygon(surf, (200, 140, 30), points)
                pygame.draw.polygon(surf, SOLAR_YELLOW, points, 2)
                screen.blit(surf, (rx, ry))

    def get_ramp_rects(self):
        """Return hazard rects for grounded players."""
        rects = []
        for ramp in self.ramp_projectiles:
            if ramp['alive']:
                rects.append(pygame.Rect(int(ramp['x']),
                                         int(ramp['y'] - ramp['height'] // 2),
                                         ramp['width'], ramp['height']))
        return rects


class ExhaustTrail(AttackPattern):
    """Boss drives across screen leaving fire trails on 2-3 lane Y positions.
    Phase 3 only. Lane control forces player to read which lanes are on fire."""
    NAME = "exhaust_trail"
    DURATION = 200
    WEIGHT = 0.8

    def __init__(self):
        super().__init__()
        self.flame_segments = []
        self.passes = []
        self.current_pass = 0

    def start(self, boss):
        super().start(boss)
        self.flame_segments = []
        self.current_pass = 0
        # Plan 2-3 passes across different Y positions
        num_passes = random.randint(2, 3)
        self.passes = []
        for i in range(num_passes):
            lane_y = random.randint(150, SCREEN_HEIGHT - 100)
            self.passes.append({
                'y': lane_y,
                'start_frame': 30 + i * 50,  # 30-frame telegraph per pass
                'x': -50.0,
                'active': False,
                'done': False,
                'dir': 1 if i % 2 == 0 else -1,
                'telegraphed': False,
            })

    def update(self, boss, players, particles, dt=1):
        self.timer += 1

        for i, pass_info in enumerate(self.passes):
            if pass_info['done']:
                continue

            # Telegraph phase
            if self.timer >= pass_info['start_frame'] - 30 and not pass_info['telegraphed']:
                pass_info['telegraphed'] = True

            # Start pass
            if self.timer >= pass_info['start_frame'] and not pass_info['active']:
                pass_info['active'] = True
                pass_info['x'] = -50.0 if pass_info['dir'] == 1 else float(SCREEN_WIDTH + 50)

            if pass_info['active']:
                pass_info['x'] += pass_info['dir'] * 12
                # Leave flame segment
                if self.timer % 3 == 0:
                    self.flame_segments.append({
                        'x': int(pass_info['x']),
                        'y': pass_info['y'],
                        'width': 30,
                        'height': 16,
                        'life': 120,
                        'hit_players': set(),
                    })
                # Check if pass is done
                if pass_info['dir'] == 1 and pass_info['x'] > SCREEN_WIDTH + 60:
                    pass_info['done'] = True
                elif pass_info['dir'] == -1 and pass_info['x'] < -60:
                    pass_info['done'] = True

        # Update flame segments — damage players, decay
        for seg in self.flame_segments[:]:
            seg['life'] -= 1
            if seg['life'] <= 0:
                self.flame_segments.remove(seg)
                continue
            seg_rect = pygame.Rect(seg['x'] - seg['width'] // 2,
                                   seg['y'] - seg['height'] // 2,
                                   seg['width'], seg['height'])
            for p in players:
                if not p.alive or id(p) in seg['hit_players']:
                    continue
                if p.invincible_timer > 0 or p.ghost_mode:
                    continue
                if seg_rect.colliderect(p.rect):
                    if hasattr(boss, 'shake') and boss.shake:
                        p.take_hit(boss.shake)
                    seg['hit_players'].add(id(p))

        if self.timer >= self.DURATION:
            self.flame_segments.clear()
            self.active = False
            return True
        return False

    def draw(self, screen, boss):
        # Draw telegraph indicators
        for pass_info in self.passes:
            if pass_info['telegraphed'] and not pass_info['active']:
                if (self.timer // 5) % 2 == 0:
                    pygame.draw.line(screen, (255, 100, 30),
                                     (ROAD_LEFT, pass_info['y']),
                                     (ROAD_RIGHT, pass_info['y']), 2)

        # Draw flame segments
        for seg in self.flame_segments:
            alpha = min(200, int(200 * (seg['life'] / 120.0)))
            sx = seg['x'] - seg['width'] // 2
            sy = seg['y'] - seg['height'] // 2
            flame_surf = pygame.Surface((seg['width'], seg['height']), pygame.SRCALPHA)
            flame_surf.fill((255, 80, 20, alpha))
            screen.blit(flame_surf, (sx, sy))
            # Bright core
            if seg['life'] > 60:
                core_surf = pygame.Surface((seg['width'] - 4, seg['height'] - 4), pygame.SRCALPHA)
                core_surf.fill((255, 200, 60, alpha // 2))
                screen.blit(core_surf, (sx + 2, sy + 2))

    def get_flame_rects(self):
        """Return active flame segment rects for collision."""
        rects = []
        for seg in self.flame_segments:
            rects.append(pygame.Rect(seg['x'] - seg['width'] // 2,
                                     seg['y'] - seg['height'] // 2,
                                     seg['width'], seg['height']))
        return rects


# ---------------------------------------------------------------------------
# Excitebike Boss
# ---------------------------------------------------------------------------

class ExcitebikeBoss(Boss):
    """Large armored motorcycle boss for the Excitebike mode.

    Hovers on the right side of the screen, bobbing sinusoidally.
    3 phases of escalating attacks. Can be damaged by ram (during
    vulnerability), heat bolts, and environmental ramp hazards.
    """

    MAX_HP = 300
    RAM_DAMAGE = 25
    ENVIRONMENTAL_DAMAGE = 50

    def __init__(self, particles, shake=None, evolution_tier=1):
        self.shake = shake
        self.bob_offset = 0.0
        self.base_y = 200
        self.base_x = 650
        evo_scale = 1.0 + (evolution_tier - 1) * 0.3
        self.MAX_HP = int(300 * evo_scale)
        self.wheel_angle = 0.0
        self.exhaust_timer = 0
        self.ramps = pygame.sprite.Group()
        self.ramp_spawn_timer = 0
        self.ramp_scroll_speed = 4
        super().__init__(self.base_x, self.base_y, particles, tier=evolution_tier)

    def _build_phases(self):
        """Construct 3 boss phases with escalating attack pools."""
        # Phase 1: HP 100% - 66%
        phase1_attacks = [
            ShockwaveAttack(),
            MissileBarrageAttack(missile_count=4),
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
            ShockwaveAttack(),
            MissileBarrageAttack(missile_count=5),
            ChargeAttack(),
            RampBarrage(),
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
            ShockwaveAttack(),
            MissileBarrageAttack(missile_count=6),
            ChargeAttack(),
            ComboAttack(),
            ExhaustTrail(),
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
        """Draw the armored motorcycle procedurally."""
        tier = self.tier
        if tier >= 3:
            return self._create_surface_v3()

        surf = pygame.Surface((120, 80), pygame.SRCALPHA)
        phase_color = self.current_phase.color if hasattr(self, 'current_phase') else NEON_CYAN

        # --- Main body / chassis ---
        body_pts = [(15, 55), (30, 25), (90, 20), (110, 40), (105, 60), (15, 60)]
        pygame.draw.polygon(surf, (60, 60, 80), body_pts)
        pygame.draw.polygon(surf, phase_color, body_pts, 2)

        # Upper armor plate
        armor_pts = [(35, 25), (50, 10), (85, 8), (95, 20), (90, 30), (35, 30)]
        pygame.draw.polygon(surf, (80, 80, 100), armor_pts)
        pygame.draw.polygon(surf, phase_color, armor_pts, 2)

        # Windshield
        windshield_pts = [(50, 12), (65, 5), (78, 5), (85, 12)]
        pygame.draw.polygon(surf, (*phase_color[:3], 100), windshield_pts)

        # Engine block (center mass)
        pygame.draw.rect(surf, (50, 50, 70), (40, 35, 35, 20))
        pygame.draw.rect(surf, phase_color, (40, 35, 35, 20), 1)

        # Exhaust pipes (rear)
        for ey in [42, 50]:
            pygame.draw.line(surf, (180, 180, 200), (10, ey), (25, ey), 3)
            pygame.draw.circle(surf, (255, 100, 30), (10, ey), 3)

        # --- Wheels with rotation spokes ---
        wheel_angle = getattr(self, 'wheel_angle', 0.0)
        for wx, wy in [(95, 62), (25, 62)]:
            pygame.draw.circle(surf, (40, 40, 50), (wx, wy), 14)
            pygame.draw.circle(surf, (80, 80, 90), (wx, wy), 14, 2)
            # Rotating spokes
            for spoke in range(4):
                angle = wheel_angle + spoke * (math.pi / 2)
                sx = wx + int(math.cos(angle) * 10)
                sy = wy + int(math.sin(angle) * 10)
                pygame.draw.line(surf, phase_color, (wx, wy), (sx, sy), 1)
            pygame.draw.circle(surf, phase_color, (wx, wy), 4, 1)

        # --- Headlight ---
        pygame.draw.circle(surf, SOLAR_WHITE, (108, 38), 5)
        pygame.draw.circle(surf, SOLAR_YELLOW, (108, 38), 3)

        # --- Armor spikes ---
        for sx in [45, 60, 75]:
            pygame.draw.polygon(surf, phase_color, [(sx, 10), (sx + 4, 3), (sx + 8, 10)])

        return surf

    def _create_surface_v3(self):
        """V3: Dark chrome armored bike — 130x85 with plasma vents and neon hubs."""
        surf = pygame.Surface((130, 85), pygame.SRCALPHA)
        phase_color = self.current_phase.color if hasattr(self, 'current_phase') else NEON_CYAN

        # --- Dark chrome chassis ---
        body_pts = [(15, 58), (32, 22), (98, 18), (120, 40), (115, 62), (15, 64)]
        pygame.draw.polygon(surf, (35, 35, 50), body_pts)
        # Chrome highlight stripe along top
        pygame.draw.line(surf, (120, 120, 140), (35, 24), (96, 20), 2)

        # Upper armor plate — darker
        armor_pts = [(38, 24), (52, 10), (90, 8), (100, 19), (95, 30), (38, 30)]
        pygame.draw.polygon(surf, (50, 50, 65), armor_pts)
        pygame.draw.polygon(surf, phase_color, armor_pts, 2)

        # Windshield with glow
        windshield_pts = [(54, 11), (68, 4), (82, 4), (90, 11)]
        pygame.draw.polygon(surf, (*phase_color[:3], 120), windshield_pts)
        pygame.draw.lines(surf, (200, 200, 220), False, windshield_pts, 1)

        # Engine block
        pygame.draw.rect(surf, (40, 40, 55), (44, 35, 38, 22))
        pygame.draw.rect(surf, phase_color, (44, 35, 38, 22), 1)

        # 4 plasma vent circles on chassis
        for vx, vy in [(48, 42), (58, 42), (68, 42), (78, 42)]:
            pygame.draw.circle(surf, (20, 20, 30), (vx, vy), 4)
            pygame.draw.circle(surf, phase_color, (vx, vy), 3)
            pygame.draw.circle(surf, (200, 200, 255), (vx, vy), 1)

        # Exhaust pipes with bloom
        for ey in [44, 52]:
            pygame.draw.line(surf, (140, 140, 160), (8, ey), (28, ey), 4)
            # Exhaust bloom
            pygame.draw.circle(surf, (255, 120, 40, 80), (6, ey), 5)
            pygame.draw.circle(surf, (255, 200, 80), (6, ey), 2)

        # --- Wheels with 6 spokes + neon hub rim ---
        wheel_angle = getattr(self, 'wheel_angle', 0.0)
        for wx, wy in [(105, 66), (28, 66)]:
            pygame.draw.circle(surf, (30, 30, 40), (wx, wy), 15)
            # Neon hub rim
            pygame.draw.circle(surf, phase_color, (wx, wy), 15, 2)
            # 6 spokes
            for spoke in range(6):
                angle = wheel_angle + spoke * (math.pi / 3)
                sx = wx + int(math.cos(angle) * 11)
                sy = wy + int(math.sin(angle) * 11)
                pygame.draw.line(surf, (100, 100, 120), (wx, wy), (sx, sy), 1)
            pygame.draw.circle(surf, phase_color, (wx, wy), 4)
            pygame.draw.circle(surf, (200, 200, 220), (wx, wy), 2)

        # --- Headlight ---
        pygame.draw.circle(surf, SOLAR_WHITE, (118, 38), 6)
        pygame.draw.circle(surf, SOLAR_YELLOW, (118, 38), 3)

        # --- 5 armor spikes with bright tips ---
        for sx in [42, 54, 66, 78, 90]:
            pygame.draw.polygon(surf, (80, 80, 100),
                                [(sx, 10), (sx + 3, 2), (sx + 6, 10)])
            pygame.draw.circle(surf, phase_color, (sx + 3, 3), 2)

        # Chrome edge highlight
        pygame.draw.polygon(surf, (*phase_color[:3], 50), body_pts, 2)

        return surf

    def _rebuild_surface(self):
        """Rebuild the boss surface to reflect current phase color + wheel animation."""
        self.wheel_angle += 0.2 * self.current_phase.speed_mult
        self.image = self._create_surface()

    def _update_movement(self, players, dt=1):
        """Sinusoidal bobbing with lane targeting toward player."""
        self.bob_offset += 0.03 * self.current_phase.speed_mult

        target_y = self.base_y + math.sin(self.bob_offset) * 60

        # Lane targeting: bias toward player's Y position (more aggressive in later phases)
        alive = [p for p in players if p.alive]
        if alive and not self.vulnerable:
            player_y = alive[0].rect.centery
            lane_bias = (player_y - target_y) * (0.15 + self.current_phase_idx * 0.1)
            target_y += lane_bias

        if self.vulnerable:
            # Drift lower to make ramming easier
            target_y = SCREEN_HEIGHT - 140 + math.sin(self.bob_offset * 0.5) * 20

        # Smooth approach
        self.rect.centery += int((target_y - self.rect.centery) * 0.08)
        self.rect.centerx = self.base_x + int(math.sin(self.bob_offset * 0.7) * 30)

        # Keep in bounds
        self.rect.clamp_ip(pygame.Rect(ROAD_LEFT, 40, SCREEN_WIDTH - ROAD_LEFT, SCREEN_HEIGHT - 80))

        # Spawn ramps periodically as environmental hazards
        self.ramp_spawn_timer += 1
        if self.ramp_spawn_timer >= 180:
            self.ramp_spawn_timer = 0
            rx = random.randint(ROAD_LEFT + 40, ROAD_RIGHT - 40)
            ramp = RampHazard(rx, self.ramp_scroll_speed)
            self.ramps.add(ramp)

    def _draw_extras(self, screen):
        """Draw exhaust particles and phase indicator."""
        self.exhaust_timer += 1

        # V3: speed blur lines behind boss
        if self.tier >= 3 and self.alive and self.active:
            blur_alpha = int(40 + 20 * math.sin(self.exhaust_timer * 0.1))
            for i in range(5):
                ly = self.rect.centery - 15 + i * 8
                lx = self.rect.left - 20 - i * 12
                lw = 15 + i * 5
                line_surf = pygame.Surface((lw, 2), pygame.SRCALPHA)
                line_surf.fill((*self.current_phase.color[:3], max(10, blur_alpha - i * 8)))
                screen.blit(line_surf, (lx, ly))

        # Neon exhaust from rear
        if self.exhaust_timer % 3 == 0 and self.alive and self.active:
            ex = self.rect.left - 2
            ey = self.rect.centery + random.randint(-8, 8)
            color = random.choice([
                self.current_phase.color,
                (255, 100, 30),
                (255, 200, 60),
            ])
            self.particles.emit(ex, ey, color,
                                [-random.uniform(2, 5), random.uniform(-1, 1)], 20, 3)

        # Phase indicator text
        if self.alive and self.active:
            phase_names = ["PHASE I", "PHASE II", "PHASE III"]
            if self.current_phase_idx < len(phase_names):
                font = load_font("dejavusans", 14, bold=True)
                txt = font.render(phase_names[self.current_phase_idx], True,
                                  self.current_phase.color)
                screen.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2,
                                  SCREEN_HEIGHT - 58))

    def _on_phase_change(self, new_phase_idx):
        """Flash effect and rebuild sprite on phase transition."""
        self._rebuild_surface()
        self.particles.burst(
            self.rect.centerx, self.rect.centery,
            [self.current_phase.color, SOLAR_WHITE], 25, 6, 50, 4,
        )

    def _on_death(self, particles):
        """Massive explosion on defeat."""
        for i in range(5):
            ox = random.randint(-50, 50)
            oy = random.randint(-30, 30)
            particles.burst(
                self.rect.centerx + ox, self.rect.centery + oy,
                [SOLAR_YELLOW, SOLAR_WHITE, NEON_MAGENTA, NEON_CYAN],
                12, 7, 60, 4,
            )
        # Clean up ramps
        for r in list(self.ramps):
            r.kill()
        self.ramps.empty()

    def update(self, players, scroll_speed=0):
        """Extended update: also update ramps and check environmental damage."""
        super().update(players, scroll_speed)

        self.ramp_scroll_speed = max(3, scroll_speed) if scroll_speed else 4

        # Update ramps
        for ramp in list(self.ramps):
            ramp.update(self.ramp_scroll_speed)
            if not ramp.alive:
                continue

            # Environmental damage: boss overlaps ramp
            if (self.alive and self.active and not ramp.hit_boss and
                    self.rect.colliderect(ramp.rect)):
                self.take_damage(self.ENVIRONMENTAL_DAMAGE, source="environmental")
                ramp.hit_boss = True
                self.particles.burst(ramp.rect.centerx, ramp.rect.centery,
                                     [SOLAR_YELLOW, (255, 200, 60)], 10, 5, 30, 3)

        # Rebuild surface each frame for wheel animation and phase color
        if self.alive and self.active:
            self._rebuild_surface()

    def draw(self, screen):
        """Draw ramps behind boss, then boss itself."""
        self.ramps.draw(screen)
        super().draw(screen)

    def get_ramps(self):
        """Public accessor for the ramp sprite group (for mode-level collision)."""
        return self.ramps

    def get_attack_hazards(self):
        """Return collision data for the mode to check against players.

        Returns list of (type, data) tuples:
          ('rect', pygame.Rect) — rectangular hazard zone
        """
        hazards = []
        if self.current_attack and self.current_attack.active:
            if isinstance(self.current_attack, ShockwaveAttack):
                if self.current_attack.wave_active:
                    wy = int(self.current_attack.wave_y)
                    hazards.append(('rect', pygame.Rect(
                        ROAD_LEFT, wy - self.current_attack.wave_height // 2,
                        ROAD_RIGHT - ROAD_LEFT, self.current_attack.wave_height)))
                if self.current_attack.wave2_active:
                    wy2 = int(self.current_attack.wave2_y)
                    hazards.append(('rect', pygame.Rect(
                        ROAD_LEFT, wy2 - self.current_attack.wave_height // 2,
                        ROAD_RIGHT - ROAD_LEFT, self.current_attack.wave_height)))
            elif isinstance(self.current_attack, MissileBarrageAttack):
                for m in self.current_attack.missiles:
                    if m.alive:
                        hazards.append(('rect', m.rect))
            elif isinstance(self.current_attack, ChargeAttack):
                if self.current_attack.charging:
                    hazards.append(('rect', self.rect))
            elif isinstance(self.current_attack, ComboAttack):
                sub = self.current_attack
                if sub.phase == "shockwave":
                    if sub.shockwave.wave_active:
                        wy = int(sub.shockwave.wave_y)
                        hazards.append(('rect', pygame.Rect(
                            ROAD_LEFT, wy - sub.shockwave.wave_height // 2,
                            ROAD_RIGHT - ROAD_LEFT, sub.shockwave.wave_height)))
                    if sub.shockwave.wave2_active:
                        wy2 = int(sub.shockwave.wave2_y)
                        hazards.append(('rect', pygame.Rect(
                            ROAD_LEFT, wy2 - sub.shockwave.wave_height // 2,
                            ROAD_RIGHT - ROAD_LEFT, sub.shockwave.wave_height)))
                elif sub.phase == "missiles":
                    for m in sub.missiles.missiles:
                        if m.alive:
                            hazards.append(('rect', m.rect))
            elif isinstance(self.current_attack, RampBarrage):
                hazards.extend(('rect', r) for r in self.current_attack.get_ramp_rects())
            elif isinstance(self.current_attack, ExhaustTrail):
                hazards.extend(('rect', r) for r in self.current_attack.get_flame_rects())
        return hazards
