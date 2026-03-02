import pygame
import random
import math

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, NEON_MAGENTA, NEON_CYAN,
    SOLAR_YELLOW, SOLAR_WHITE, SAND_YELLOW, DESERT_ORANGE,
    ROAD_LEFT, ROAD_RIGHT, ROAD_CENTER,
    DIFFICULTY_SETTINGS, DIFF_NORMAL,
)
from core.sound import play_sfx
from shared.boss_base import Boss, BossPhase, AttackPattern


# === Attack Patterns ===

class SandstormAttack(AttackPattern):
    """Columns of sand sweep across the road."""
    NAME = "sandstorm"
    DURATION = 150
    WEIGHT = 1.0

    def __init__(self):
        super().__init__()
        self.columns = []

    def play_start_sfx(self):
        play_sfx("sandstorm_wind")

    def start(self, boss):
        super().start(boss)
        self.columns = []
        num = 3 + boss.current_phase_idx
        for i in range(num):
            self.columns.append({
                'x': random.randint(ROAD_LEFT + 20, ROAD_RIGHT - 20),
                'delay': i * 25,
                'width': random.randint(40, 70),
                'active': False,
                'drift_speed': random.uniform(-0.5, 0.5) if boss.current_phase_idx >= 1 else 0,
            })

    def update(self, boss, players, particles, dt=1):
        self.timer += 1
        for col in self.columns:
            if self.timer >= col['delay']:
                col['active'] = True
            if col['active']:
                # Phase 2+: columns drift L/R
                col['x'] += col['drift_speed']
                col['x'] = max(ROAD_LEFT + 10, min(ROAD_RIGHT - 10, col['x']))
                if self.timer % 6 == 0:
                    particles.emit(int(col['x']) + random.randint(-20, 20), 0,
                                   SAND_YELLOW, [random.uniform(-1, 1), random.uniform(3, 8)], 40, 3)
        if self.timer >= self.DURATION:
            self.active = False
            return True
        return False

    def draw(self, screen, boss):
        for col in self.columns:
            if col['active']:
                surf = pygame.Surface((col['width'], SCREEN_HEIGHT), pygame.SRCALPHA)
                alpha = int(60 + 30 * math.sin(self.timer * 0.15))
                surf.fill((*SAND_YELLOW, alpha))
                screen.blit(surf, (col['x'] - col['width'] // 2, 0))
                # Warning lines
                pygame.draw.line(screen, (*DESERT_ORANGE, 150),
                                 (col['x'], 0), (col['x'], SCREEN_HEIGHT), 2)


class BoulderBarrage(AttackPattern):
    """Boss drops boulders that fall from top."""
    NAME = "boulder_barrage"
    DURATION = 180
    WEIGHT = 1.2

    def __init__(self):
        super().__init__()
        self.boulders = []

    def start(self, boss):
        super().start(boss)
        self.boulders = []

    def update(self, boss, players, particles, dt=1):
        self.timer += 1
        # Spawn boulders periodically — faster intervals per phase
        interval = max(6, [25, 17, 9][min(boss.current_phase_idx, 2)])
        if self.timer % interval == 0:
            bx = random.randint(ROAD_LEFT + 20, ROAD_RIGHT - 20)
            # 30% of boulders slightly home toward player
            homing = random.random() < 0.3
            self.boulders.append({
                'x': float(bx),
                'y': float(boss.rect.bottom),
                'vy': random.uniform(3, 6),
                'size': random.randint(15, 25),
                'alive': True,
                'homing': homing,
            })
            play_sfx("boulder_drop")

        alive_players = [p for p in players if p.alive]
        for b in self.boulders:
            if b['alive']:
                b['y'] += b['vy']
                b['vy'] += 0.1
                # Homing boulders nudge toward nearest player
                if b.get('homing') and alive_players:
                    nearest = min(alive_players, key=lambda p: abs(p.rect.centerx - b['x']))
                    dx = nearest.rect.centerx - b['x']
                    b['x'] += max(-1.0, min(1.0, dx * 0.02))
                if b['y'] > SCREEN_HEIGHT + 30:
                    b['alive'] = False
                # Trail
                if self.timer % 3 == 0:
                    particles.emit(int(b['x']), int(b['y']), DESERT_ORANGE,
                                   [random.uniform(-1, 1), -1], 20, 2)

        self.boulders = [b for b in self.boulders if b['alive']]

        if self.timer >= self.DURATION:
            self.active = False
            return True
        return False

    def draw(self, screen, boss):
        for b in self.boulders:
            if b['alive']:
                surf = pygame.Surface((b['size'] * 2 + 4, b['size'] * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(surf, (180, 90, 25), (b['size'] + 2, b['size'] + 2), b['size'])
                pygame.draw.circle(surf, SAND_YELLOW, (b['size'] + 2, b['size'] + 2), b['size'], 2)
                screen.blit(surf, (int(b['x'] - b['size'] - 2), int(b['y'] - b['size'] - 2)))

    def get_boulder_rects(self):
        """Return rects for collision detection by the mode."""
        rects = []
        for b in self.boulders:
            if b['alive']:
                rects.append(pygame.Rect(b['x'] - b['size'], b['y'] - b['size'],
                                         b['size'] * 2, b['size'] * 2))
        return rects


class DiveAttack(AttackPattern):
    """Boss charges down toward a player then retreats."""
    NAME = "dive"
    DURATION = 120
    WEIGHT = 0.8

    def __init__(self):
        super().__init__()
        self.target_x = ROAD_CENTER
        self.diving = False
        self.retreating = False
        self.original_y = 0
        self.slam_rect = None  # ground shockwave rect on landing

    def start(self, boss):
        super().start(boss)
        self.original_y = boss.rect.y
        self.diving = True
        self.retreating = False
        self.target_x = ROAD_CENTER
        self.slam_rect = None

    def update(self, boss, players, particles, dt=1):
        self.timer += 1

        alive = [p for p in players if p.alive]
        # Track player until frame 30 (was 10)
        if alive and self.timer < 30:
            self.target_x = random.choice(alive).rect.centerx

        dive_speed = 8 + boss.current_phase_idx * 2  # was flat 6

        if self.diving:
            boss.rect.y += dive_speed
            boss.rect.x += (self.target_x - boss.rect.centerx) * 0.05
            if boss.rect.y > SCREEN_HEIGHT * 0.65:
                self.diving = False
                self.retreating = True
                # Ground slam shockwave on landing
                self.slam_rect = pygame.Rect(
                    boss.rect.centerx - 80, int(SCREEN_HEIGHT * 0.65) - 15, 160, 30)
                particles.burst(boss.rect.centerx, boss.rect.bottom,
                                [DESERT_ORANGE, SAND_YELLOW], 15, 5, 30, 3)
                play_sfx("crash")
        elif self.retreating:
            # Slam rect fades after 20 frames
            if self.slam_rect and self.timer > 20:
                self.slam_rect = None
            boss.rect.y -= 4
            if boss.rect.y <= self.original_y:
                boss.rect.y = self.original_y
                self.retreating = False

        if self.timer >= self.DURATION:
            boss.rect.y = self.original_y
            self.slam_rect = None
            self.active = False
            return True
        return False

    def draw(self, screen, boss):
        if self.diving:
            # Warning line
            pygame.draw.line(screen, (*NEON_MAGENTA, 120),
                             (int(self.target_x), boss.rect.bottom),
                             (int(self.target_x), SCREEN_HEIGHT), 3)
        if self.slam_rect:
            slam_surf = pygame.Surface((self.slam_rect.width, self.slam_rect.height), pygame.SRCALPHA)
            slam_surf.fill((*DESERT_ORANGE, 100))
            screen.blit(slam_surf, self.slam_rect.topleft)


class HeatWaveAttack(AttackPattern):
    """Expanding heat rings from boss position."""
    NAME = "heat_wave"
    DURATION = 160
    WEIGHT = 0.9

    def __init__(self):
        super().__init__()
        self.rings = []

    def start(self, boss):
        super().start(boss)
        self.rings = []

    def update(self, boss, players, particles, dt=1):
        self.timer += 1
        interval = max(15, [35, 25, 15][min(boss.current_phase_idx, 2)])
        if self.timer % interval == 0:
            self.rings.append({
                'cx': boss.rect.centerx,
                'cy': boss.rect.centery,
                'radius': 20,
                'max_radius': 300,
                'speed': [4, 5.5, 7][min(boss.current_phase_idx, 2)],
            })
            play_sfx("ring_pulse")

        for ring in self.rings:
            ring['radius'] += ring['speed']

        self.rings = [r for r in self.rings if r['radius'] < r['max_radius']]

        if self.timer >= self.DURATION:
            self.active = False
            return True
        return False

    def draw(self, screen, boss):
        for ring in self.rings:
            alpha = int(150 * (1 - ring['radius'] / ring['max_radius']))
            if alpha > 0:
                surf = pygame.Surface((ring['radius'] * 2 + 4, ring['radius'] * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*SOLAR_YELLOW, alpha),
                                   (ring['radius'] + 2, ring['radius'] + 2), int(ring['radius']), 3)
                screen.blit(surf, (int(ring['cx'] - ring['radius'] - 2),
                                   int(ring['cy'] - ring['radius'] - 2)))

    def get_ring_data(self):
        """Return ring positions for collision in mode."""
        return [(r['cx'], r['cy'], r['radius']) for r in self.rings]


class SolarBeamAttack(AttackPattern):
    """Sweeping beam of light across the road."""
    NAME = "solar_beam"
    DURATION = 140
    WEIGHT = 0.7

    def __init__(self):
        super().__init__()
        self.beam_x = ROAD_LEFT
        self.beam_dir = 1
        self.beam_width = 50

    def play_start_sfx(self):
        play_sfx("beam_hum")

    def start(self, boss):
        super().start(boss)
        self.beam_x = boss.rect.centerx
        self.beam_dir = random.choice([-1, 1])

    def update(self, boss, players, particles, dt=1):
        self.timer += 1
        speed = [4, 6, 8][min(boss.current_phase_idx, 2)]
        self.beam_width = 50 + boss.current_phase_idx * 10
        self.beam_x += self.beam_dir * speed
        if self.beam_x > ROAD_RIGHT - 30:
            self.beam_dir = -1
        elif self.beam_x < ROAD_LEFT + 30:
            self.beam_dir = 1

        if self.timer % 4 == 0:
            particles.emit(self.beam_x + random.randint(-10, 10),
                           random.randint(0, SCREEN_HEIGHT),
                           SOLAR_YELLOW, [0, random.uniform(-1, 1)], 20, 2)

        if self.timer >= self.DURATION:
            self.active = False
            return True
        return False

    def draw(self, screen, boss):
        surf = pygame.Surface((self.beam_width, SCREEN_HEIGHT), pygame.SRCALPHA)
        alpha = int(50 + 30 * math.sin(self.timer * 0.1))
        surf.fill((*SOLAR_YELLOW, alpha))
        screen.blit(surf, (int(self.beam_x - self.beam_width // 2), 0))
        # Core line
        pygame.draw.line(screen, (*SOLAR_WHITE, 180),
                         (int(self.beam_x), 0), (int(self.beam_x), SCREEN_HEIGHT), 3)


# === New Attack Patterns ===

class QuicksandVortex(AttackPattern):
    """Gravitational pull pools on road — player must steer out while dodging.
    Phases 2-3 only. 2-3 vortex pools with pull radius."""
    NAME = "quicksand_vortex"
    DURATION = 180
    WEIGHT = 1.0

    def __init__(self):
        super().__init__()
        self.vortices = []

    def start(self, boss):
        super().start(boss)
        self.vortices = []
        count = random.randint(2, 3)
        for _ in range(count):
            self.vortices.append({
                'x': float(random.randint(ROAD_LEFT + 40, ROAD_RIGHT - 40)),
                'y': float(random.randint(SCREEN_HEIGHT // 3, SCREEN_HEIGHT - 80)),
                'pull_radius': 120.0,
                'pull_strength': 0.8,
                'core_radius': 25,
                'telegraph': 40,  # frames before activation
                'active': False,
                'spin': 0.0,
            })

    def update(self, boss, players, particles, dt=1):
        self.timer += 1
        for v in self.vortices:
            if self.timer >= v['telegraph'] and not v['active']:
                v['active'] = True
            if v['active']:
                v['spin'] += 0.12
                # Pull nearby alive players toward center
                for p in players:
                    if not p.alive or p.ghost_mode or p.invincible_timer > 0:
                        continue
                    dx = v['x'] - p.rect.centerx
                    dy = v['y'] - p.rect.centery
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist < v['pull_radius'] and dist > 1:
                        # Linear decay: strongest at center
                        strength = v['pull_strength'] * (1.0 - dist / v['pull_radius'])
                        p.rect.x += int(dx / dist * strength)
                        p.rect.y += int(dy / dist * strength)
                # Sand particles
                if self.timer % 4 == 0:
                    angle = random.uniform(0, 2 * math.pi)
                    px = v['x'] + math.cos(angle) * random.uniform(20, 80)
                    py = v['y'] + math.sin(angle) * random.uniform(20, 80)
                    particles.emit(int(px), int(py), SAND_YELLOW,
                                   [math.cos(angle + 1.5) * 2, math.sin(angle + 1.5) * 2], 25, 2)

        if self.timer >= self.DURATION:
            self.active = False
            return True
        return False

    def draw(self, screen, boss):
        for v in self.vortices:
            cx, cy = int(v['x']), int(v['y'])
            if not v['active']:
                # Telegraph: crack lines
                if (self.timer // 4) % 2 == 0:
                    for i in range(4):
                        angle = v['spin'] + i * (math.pi / 2)
                        ex = cx + int(math.cos(angle) * 30)
                        ey = cy + int(math.sin(angle) * 30)
                        pygame.draw.line(screen, SAND_YELLOW, (cx, cy), (ex, ey), 2)
            else:
                # Swirling sand circles
                for ring_r in [20, 40, 60]:
                    surf = pygame.Surface((ring_r * 2 + 4, ring_r * 2 + 4), pygame.SRCALPHA)
                    alpha = max(30, 80 - ring_r)
                    pygame.draw.circle(surf, (*SAND_YELLOW, alpha),
                                       (ring_r + 2, ring_r + 2), ring_r, 2)
                    screen.blit(surf, (cx - ring_r - 2, cy - ring_r - 2))
                # Dark core
                core_surf = pygame.Surface((50, 50), pygame.SRCALPHA)
                pygame.draw.circle(core_surf, (80, 40, 10, 120), (25, 25), v['core_radius'])
                screen.blit(core_surf, (cx - 25, cy - 25))
                # Animated spiral lines
                for i in range(3):
                    angle = v['spin'] + i * (2 * math.pi / 3)
                    for r in range(10, 70, 8):
                        sx = cx + int(math.cos(angle + r * 0.05) * r)
                        sy = cy + int(math.sin(angle + r * 0.05) * r)
                        pygame.draw.circle(screen, (*DESERT_ORANGE, 100), (sx, sy), 2)

    def get_vortex_rects(self):
        """Return damage core rects for collision."""
        rects = []
        for v in self.vortices:
            if v['active']:
                cr = v['core_radius']
                rects.append(pygame.Rect(int(v['x'] - cr), int(v['y'] - cr), cr * 2, cr * 2))
        return rects


class SandstormSweep(AttackPattern):
    """Sand wall sweeps across road L→R or R→L with single 80px gap.
    Phase 3 only. Counter-sweep follows."""
    NAME = "sandstorm_sweep"
    DURATION = 140
    WEIGHT = 0.9

    def __init__(self):
        super().__init__()
        self.wall_x = 0.0
        self.wall_dir = 1
        self.gap_y = 0
        self.gap_size = 80
        self.wall_width = 60
        self.sweep_speed = 4.0
        self.telegraph_frames = 50
        self.sweeping = False
        # Counter-sweep
        self.counter_sweep = False
        self.counter_x = 0.0
        self.counter_gap_y = 0
        self.counter_active = False

    def start(self, boss):
        super().start(boss)
        self.wall_dir = random.choice([-1, 1])
        self.wall_x = float(ROAD_LEFT if self.wall_dir == 1 else ROAD_RIGHT)
        self.gap_y = random.randint(SCREEN_HEIGHT // 4, SCREEN_HEIGHT - 100)
        self.sweeping = False
        self.counter_sweep = boss.current_phase_idx >= 2
        self.counter_active = False
        self.counter_gap_y = random.randint(SCREEN_HEIGHT // 4, SCREEN_HEIGHT - 100)

    def update(self, boss, players, particles, dt=1):
        self.timer += 1

        if self.timer < self.telegraph_frames:
            return False

        if not self.sweeping and self.timer >= self.telegraph_frames:
            self.sweeping = True

        if self.sweeping:
            self.wall_x += self.wall_dir * self.sweep_speed
            # Sand particles along wall
            if self.timer % 3 == 0:
                wy = random.randint(0, SCREEN_HEIGHT)
                particles.emit(int(self.wall_x), wy, SAND_YELLOW,
                               [self.wall_dir * 2, random.uniform(-1, 1)], 20, 2)
            # Wall reached other side
            if self.wall_dir == 1 and self.wall_x > ROAD_RIGHT + self.wall_width:
                self.sweeping = False
                if self.counter_sweep and not self.counter_active:
                    self.counter_active = True
                    self.counter_x = float(ROAD_RIGHT)
            elif self.wall_dir == -1 and self.wall_x < ROAD_LEFT - self.wall_width:
                self.sweeping = False
                if self.counter_sweep and not self.counter_active:
                    self.counter_active = True
                    self.counter_x = float(ROAD_LEFT)

        if self.counter_active:
            self.counter_x -= self.wall_dir * self.sweep_speed
            if self.timer % 3 == 0:
                wy = random.randint(0, SCREEN_HEIGHT)
                particles.emit(int(self.counter_x), wy, DESERT_ORANGE,
                               [-self.wall_dir * 2, random.uniform(-1, 1)], 20, 2)
            if self.wall_dir == 1 and self.counter_x < ROAD_LEFT - self.wall_width:
                self.counter_active = False
            elif self.wall_dir == -1 and self.counter_x > ROAD_RIGHT + self.wall_width:
                self.counter_active = False

        if self.timer >= self.DURATION:
            self.active = False
            return True
        return False

    def draw(self, screen, boss):
        # Telegraph: show gap marker
        if self.timer < self.telegraph_frames:
            if (self.timer // 6) % 2 == 0:
                marker_x = ROAD_LEFT if self.wall_dir == 1 else ROAD_RIGHT - 20
                pygame.draw.rect(screen, (*SOLAR_YELLOW, 150),
                                 (marker_x, self.gap_y, 20, self.gap_size), 2)
            return

        # Draw main sweep wall
        if self.sweeping:
            self._draw_wall(screen, self.wall_x, self.gap_y)
        if self.counter_active:
            self._draw_wall(screen, self.counter_x, self.counter_gap_y)

    def _draw_wall(self, screen, wx, gap_y):
        """Draw a vertical sand wall with a gap."""
        wx = int(wx)
        # Top segment (above gap)
        if gap_y > 0:
            surf_top = pygame.Surface((self.wall_width, gap_y), pygame.SRCALPHA)
            alpha = int(60 + 30 * math.sin(self.timer * 0.15))
            surf_top.fill((*SAND_YELLOW, alpha))
            screen.blit(surf_top, (wx - self.wall_width // 2, 0))
        # Bottom segment (below gap)
        bot_y = gap_y + self.gap_size
        bot_h = SCREEN_HEIGHT - bot_y
        if bot_h > 0:
            surf_bot = pygame.Surface((self.wall_width, bot_h), pygame.SRCALPHA)
            alpha = int(60 + 30 * math.sin(self.timer * 0.15))
            surf_bot.fill((*SAND_YELLOW, alpha))
            screen.blit(surf_bot, (wx - self.wall_width // 2, bot_y))

    def get_wall_rects(self):
        """Return hazard rects for both sweeps."""
        rects = []
        if self.sweeping:
            wx = int(self.wall_x)
            hw = self.wall_width // 2
            # Top part
            if self.gap_y > 0:
                rects.append(pygame.Rect(wx - hw, 0, self.wall_width, self.gap_y))
            # Bottom part
            bot_y = self.gap_y + self.gap_size
            if bot_y < SCREEN_HEIGHT:
                rects.append(pygame.Rect(wx - hw, bot_y, self.wall_width, SCREEN_HEIGHT - bot_y))
        if self.counter_active:
            wx = int(self.counter_x)
            hw = self.wall_width // 2
            if self.counter_gap_y > 0:
                rects.append(pygame.Rect(wx - hw, 0, self.wall_width, self.counter_gap_y))
            bot_y = self.counter_gap_y + self.gap_size
            if bot_y < SCREEN_HEIGHT:
                rects.append(pygame.Rect(wx - hw, bot_y, self.wall_width, SCREEN_HEIGHT - bot_y))
        return rects


# === Desert Boss ===

class DesertBoss(Boss):
    """Desert Colossus — a massive sandstone golem head that hovers at the top of the road."""

    MAX_HP = 300
    RAM_DAMAGE = 25
    ENVIRONMENTAL_DAMAGE = 50

    def __init__(self, particles, difficulty=DIFF_NORMAL, evolution_tier=1):
        self._difficulty = difficulty
        self._diff_s = DIFFICULTY_SETTINGS.get(difficulty, DIFFICULTY_SETTINGS[DIFF_NORMAL])
        # Scale HP before super().__init__ reads it
        evo_scale = 1.0 + (evolution_tier - 1) * 0.3
        self.MAX_HP = int(300 * self._diff_s.get("boss_hp_mult", 1.0) * evo_scale)
        super().__init__(ROAD_CENTER, 80, particles, tier=evolution_tier)
        self.move_dir = 1
        self.move_speed = 1.5
        self.bob_offset = 0

    def _build_phases(self):
        vm = self._diff_s.get("vulnerability_mult", 1.0)
        return [
            BossPhase(
                hp_threshold=1.0,
                attacks=[SandstormAttack(), BoulderBarrage(), DiveAttack()],
                vulnerability_after_attack=int(54 * vm),
                speed_mult=1.0,
                color=SAND_YELLOW,
            ),
            BossPhase(
                hp_threshold=0.66,
                attacks=[BoulderBarrage(), QuicksandVortex(), DiveAttack(), SandstormAttack()],
                vulnerability_after_attack=int(40 * vm),
                speed_mult=1.3,
                color=DESERT_ORANGE,
            ),
            BossPhase(
                hp_threshold=0.33,
                attacks=[SandstormSweep(), QuicksandVortex(), BoulderBarrage(),
                         DiveAttack(), SolarBeamAttack()],
                vulnerability_after_attack=int(30 * vm),
                speed_mult=1.6,
                color=NEON_MAGENTA,
            ),
        ]

    def _create_surface(self):
        """Draw a menacing desert colossus head."""
        tier = self.tier
        if tier >= 3:
            return self._create_surface_v3()

        w, h = 100, 90
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w // 2, h // 2

        # Outer glow
        pygame.draw.ellipse(surf, (*DESERT_ORANGE, 40), (0, 5, w, h - 10))
        # Main body — angular head shape
        body = [(cx, 5), (cx + 40, 25), (cx + 45, 60), (cx + 30, h - 5),
                (cx - 30, h - 5), (cx - 45, 60), (cx - 40, 25)]
        pygame.draw.polygon(surf, (160, 80, 20), body)
        pygame.draw.polygon(surf, SAND_YELLOW, body, 2)

        # Inner face details
        pygame.draw.polygon(surf, (120, 60, 15),
                            [(cx, 15), (cx + 30, 30), (cx + 35, 55),
                             (cx - 35, 55), (cx - 30, 30)])

        # Eyes
        for ex in [cx - 18, cx + 10]:
            pygame.draw.ellipse(surf, (255, 50, 50), (ex, 30, 12, 8))
            pygame.draw.ellipse(surf, SOLAR_YELLOW, (ex + 3, 32, 6, 4))

        # Mouth
        mouth = [(cx - 20, 55), (cx - 10, 65), (cx, 60),
                 (cx + 10, 65), (cx + 20, 55)]
        pygame.draw.lines(surf, (255, 50, 50), False, mouth, 2)

        # Crown horns
        for hx, hy in [(cx - 25, 10), (cx, 0), (cx + 25, 10)]:
            pygame.draw.polygon(surf, SAND_YELLOW,
                                [(hx, hy), (hx - 5, hy + 15), (hx + 5, hy + 15)])

        # Edge glow
        pygame.draw.polygon(surf, (*NEON_MAGENTA, 60), body, 3)

        return surf

    def _create_surface_v3(self):
        """V3: Molten rock colossus — 110x96 with magma cracks and glowing horns."""
        w, h = 110, 96
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w // 2, h // 2

        # 3-ring outer glow (molten)
        for i, (gr, ga) in enumerate([(55, 20), (45, 30), (35, 45)]):
            pygame.draw.ellipse(surf, (220, 60, 10, ga),
                                (i * 4, 5 + i * 2, w - i * 8, h - 10 - i * 4))

        # Main body — molten rock
        body = [(cx, 3), (cx + 45, 22), (cx + 50, 62), (cx + 35, h - 3),
                (cx - 35, h - 3), (cx - 50, 62), (cx - 45, 22)]
        pygame.draw.polygon(surf, (220, 40, 10), body)

        # Inner face — darker
        pygame.draw.polygon(surf, (160, 30, 8),
                            [(cx, 14), (cx + 35, 28), (cx + 38, 58),
                             (cx - 38, 58), (cx - 35, 28)])

        # 6 magma crack lines
        crack_color = (255, 120, 20)
        cracks = [
            [(cx - 30, 20), (cx - 20, 40), (cx - 25, 58)],
            [(cx + 30, 20), (cx + 22, 38), (cx + 28, 55)],
            [(cx - 10, 15), (cx - 5, 35)],
            [(cx + 10, 15), (cx + 8, 32)],
            [(cx - 15, 50), (cx - 8, 65), (cx - 20, 78)],
            [(cx + 15, 50), (cx + 10, 68), (cx + 18, 80)],
        ]
        for crack in cracks:
            if len(crack) >= 2:
                pygame.draw.lines(surf, crack_color, False, crack, 2)

        # Larger bright eyes with white glint
        for ex in [cx - 20, cx + 10]:
            pygame.draw.ellipse(surf, (255, 50, 30), (ex, 30, 14, 10))
            pygame.draw.ellipse(surf, SOLAR_YELLOW, (ex + 2, 32, 10, 6))
            pygame.draw.circle(surf, SOLAR_WHITE, (ex + 5, 34), 2)

        # Mouth with molten glow
        mouth = [(cx - 22, 58), (cx - 12, 68), (cx, 63),
                 (cx + 12, 68), (cx + 22, 58)]
        pygame.draw.lines(surf, (255, 80, 20), False, mouth, 3)
        pygame.draw.lines(surf, (255, 160, 40), False, mouth, 1)

        # 4 crown horns (4th center horn added) with glowing tips
        horns = [(cx - 30, 8), (cx - 10, 0), (cx + 10, 0), (cx + 30, 8)]
        for hx, hy in horns:
            pygame.draw.polygon(surf, (200, 100, 20),
                                [(hx, hy), (hx - 6, hy + 16), (hx + 6, hy + 16)])
            # Glowing tip
            pygame.draw.circle(surf, (255, 200, 60), (hx, hy + 2), 3)
            pygame.draw.circle(surf, (255, 255, 200), (hx, hy + 2), 1)

        # Molten drip lines from chin
        for dx in [-12, 0, 12]:
            drip_x = cx + dx
            pygame.draw.line(surf, (255, 100, 20), (drip_x, h - 6), (drip_x, h - 1), 2)

        # Edge glow — crimson
        pygame.draw.polygon(surf, (255, 60, 20, 80), body, 3)

        return surf

    def _update_movement(self, players, dt=1):
        if not self.active or self.defeated:
            return

        speed = self.move_speed * self.current_phase.speed_mult
        self.rect.x += self.move_dir * speed

        if self.rect.right > ROAD_RIGHT - 10:
            self.move_dir = -1
        elif self.rect.left < ROAD_LEFT + 10:
            self.move_dir = 1

        # Gentle bob
        self.bob_offset = math.sin(self.pulse * 0.03) * 5
        self.rect.y = 60 + int(self.bob_offset)

    def _on_phase_change(self, new_phase_idx):
        self.particles.burst(self.rect.centerx, self.rect.centery,
                             [SOLAR_YELLOW, DESERT_ORANGE, NEON_MAGENTA], 25, 6, 50, 4)
        self.move_speed += 0.5

    def _on_death(self, particles):
        for _ in range(5):
            ox = random.randint(-50, 50)
            oy = random.randint(-40, 40)
            particles.burst(self.rect.centerx + ox, self.rect.centery + oy,
                            [SOLAR_YELLOW, SOLAR_WHITE, DESERT_ORANGE], 15, 7, 60, 4)

    def _draw_extras(self, screen):
        # V3: corona glow behind boss
        if self.tier >= 3 and self.alive and self.active:
            corona_pulse = 0.7 + 0.3 * math.sin(self.pulse * 0.06)
            corona_r = 60
            corona_surf = pygame.Surface((corona_r * 2, corona_r * 2), pygame.SRCALPHA)
            for ring_i in range(3):
                r = corona_r - ring_i * 12
                a = int(30 * corona_pulse * (3 - ring_i) / 3)
                pygame.draw.circle(corona_surf, (255, 60, 10, a), (corona_r, corona_r), r)
            screen.blit(corona_surf,
                        (self.rect.centerx - corona_r, self.rect.centery - corona_r),
                        special_flags=pygame.BLEND_RGB_ADD)

        if self.vulnerable:
            # Pulsing weak point indicator
            font = pygame.font.SysFont("dejavusans", 12, bold=True)
            txt = font.render("VULNERABLE!", True, SOLAR_YELLOW)
            alpha = int(150 + 100 * math.sin(self.pulse * 0.2))
            txt.set_alpha(min(255, alpha))
            screen.blit(txt, (self.rect.centerx - txt.get_width() // 2,
                              self.rect.bottom + 5))

    def get_attack_hazards(self):
        """Return collision data for the mode to check against players."""
        hazards = []
        if self.current_attack and self.current_attack.active:
            if isinstance(self.current_attack, BoulderBarrage):
                hazards.extend(('rect', r) for r in self.current_attack.get_boulder_rects())
            elif isinstance(self.current_attack, HeatWaveAttack):
                for cx, cy, radius in self.current_attack.get_ring_data():
                    hazards.append(('ring', (cx, cy, radius, 15)))
            elif isinstance(self.current_attack, SolarBeamAttack):
                bx = self.current_attack.beam_x
                bw = self.current_attack.beam_width
                hazards.append(('rect', pygame.Rect(int(bx - bw // 2), 0, bw, SCREEN_HEIGHT)))
            elif isinstance(self.current_attack, SandstormAttack):
                for col in self.current_attack.columns:
                    if col['active']:
                        hazards.append(('rect', pygame.Rect(
                            int(col['x']) - col['width'] // 2, 0,
                            col['width'], SCREEN_HEIGHT)))
            elif isinstance(self.current_attack, DiveAttack):
                if self.current_attack.slam_rect:
                    hazards.append(('rect', self.current_attack.slam_rect))
            elif isinstance(self.current_attack, QuicksandVortex):
                hazards.extend(('rect', r) for r in self.current_attack.get_vortex_rects())
            elif isinstance(self.current_attack, SandstormSweep):
                hazards.extend(('rect', r) for r in self.current_attack.get_wall_rects())
        return hazards
