import pygame
import random
import math

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, NEON_MAGENTA, NEON_CYAN,
    SOLAR_YELLOW, SOLAR_WHITE, SAND_YELLOW, DESERT_ORANGE,
    ROAD_LEFT, ROAD_RIGHT, ROAD_CENTER,
    DIFFICULTY_SETTINGS, DIFF_NORMAL,
)
from core.sound import SFX
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
            })

    def update(self, boss, players, particles, dt=1):
        self.timer += 1
        for col in self.columns:
            if self.timer >= col['delay']:
                col['active'] = True
            if col['active']:
                # Damage players in column
                for p in players:
                    if p.alive and not p.ghost_mode and p.invincible_timer <= 0:
                        if abs(p.rect.centerx - col['x']) < col['width'] // 2:
                            from core.shake import ScreenShake
                            # We can't access shake directly, so just flag damage
                            pass  # Collision handled by mode
                if self.timer % 6 == 0:
                    particles.emit(col['x'] + random.randint(-20, 20), 0,
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
        # Spawn boulders periodically
        interval = max(10, 30 - boss.current_phase_idx * 8)
        if self.timer % interval == 0:
            self.boulders.append({
                'x': random.randint(ROAD_LEFT + 20, ROAD_RIGHT - 20),
                'y': boss.rect.bottom,
                'vy': random.uniform(3, 6),
                'size': random.randint(15, 25),
                'alive': True,
            })

        for b in self.boulders:
            if b['alive']:
                b['y'] += b['vy']
                b['vy'] += 0.1
                if b['y'] > SCREEN_HEIGHT + 30:
                    b['alive'] = False
                # Trail
                if self.timer % 3 == 0:
                    particles.emit(b['x'], b['y'], DESERT_ORANGE,
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

    def start(self, boss):
        super().start(boss)
        self.original_y = boss.rect.y
        self.diving = True
        self.retreating = False
        self.target_x = ROAD_CENTER

    def update(self, boss, players, particles, dt=1):
        self.timer += 1

        alive = [p for p in players if p.alive]
        if alive and self.timer < 10:
            self.target_x = random.choice(alive).rect.centerx

        if self.diving:
            boss.rect.y += 6
            boss.rect.x += (self.target_x - boss.rect.centerx) * 0.05
            if boss.rect.y > SCREEN_HEIGHT * 0.65:
                self.diving = False
                self.retreating = True
                particles.burst(boss.rect.centerx, boss.rect.bottom,
                                [DESERT_ORANGE, SAND_YELLOW], 15, 5, 30, 3)
                SFX["crash"].play()
        elif self.retreating:
            boss.rect.y -= 4
            if boss.rect.y <= self.original_y:
                boss.rect.y = self.original_y
                self.retreating = False

        if self.timer >= self.DURATION:
            boss.rect.y = self.original_y
            self.active = False
            return True
        return False

    def draw(self, screen, boss):
        if self.diving:
            # Warning line
            pygame.draw.line(screen, (*NEON_MAGENTA, 120),
                             (self.target_x, boss.rect.bottom),
                             (self.target_x, SCREEN_HEIGHT), 3)


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
        interval = max(20, 40 - boss.current_phase_idx * 10)
        if self.timer % interval == 0:
            self.rings.append({
                'cx': boss.rect.centerx,
                'cy': boss.rect.centery,
                'radius': 20,
                'max_radius': 300,
                'speed': 3 + boss.current_phase_idx,
            })

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

    def start(self, boss):
        super().start(boss)
        self.beam_x = boss.rect.centerx
        self.beam_dir = random.choice([-1, 1])

    def update(self, boss, players, particles, dt=1):
        self.timer += 1
        speed = 3 + boss.current_phase_idx * 1.5
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
        super().__init__(ROAD_CENTER, 80, particles)
        self.move_dir = 1
        self.move_speed = 1.5
        self.bob_offset = 0

    def _build_phases(self):
        vm = self._diff_s.get("vulnerability_mult", 1.0)
        return [
            BossPhase(
                hp_threshold=1.0,
                attacks=[SandstormAttack(), BoulderBarrage(), DiveAttack()],
                vulnerability_after_attack=int(90 * vm),
                speed_mult=1.0,
                color=SAND_YELLOW,
            ),
            BossPhase(
                hp_threshold=0.66,
                attacks=[BoulderBarrage(), HeatWaveAttack(), DiveAttack(), SandstormAttack()],
                vulnerability_after_attack=int(75 * vm),
                speed_mult=1.3,
                color=DESERT_ORANGE,
            ),
            BossPhase(
                hp_threshold=0.33,
                attacks=[SolarBeamAttack(), BoulderBarrage(), DiveAttack(), HeatWaveAttack()],
                vulnerability_after_attack=int(60 * vm),
                speed_mult=1.6,
                color=NEON_MAGENTA,
            ),
        ]

    def _create_surface(self):
        """Draw a menacing desert colossus head."""
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
                    hazards.append(('ring', (cx, cy, radius, 15)))  # 15px ring thickness
            elif isinstance(self.current_attack, SolarBeamAttack):
                bx = self.current_attack.beam_x
                bw = self.current_attack.beam_width
                hazards.append(('rect', pygame.Rect(int(bx - bw // 2), 0, bw, SCREEN_HEIGHT)))
            elif isinstance(self.current_attack, SandstormAttack):
                for col in self.current_attack.columns:
                    if col['active']:
                        hazards.append(('rect', pygame.Rect(
                            col['x'] - col['width'] // 2, 0,
                            col['width'], SCREEN_HEIGHT)))
        return hazards
