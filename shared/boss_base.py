import pygame
import random
import math

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, NEON_MAGENTA, SOLAR_YELLOW, SOLAR_WHITE, NEON_CYAN
from core.sound import play_sfx
from core.fonts import load_font


class AttackPattern:
    """A single boss attack pattern with duration and behavior.

    Subclass and override:
        start(boss)        — called when pattern begins
        update(boss, players, particles, dt) — called each frame; return True when done
        draw(screen, boss) — render attack visuals
    """

    NAME = "base_attack"
    DURATION = 180  # frames
    WEIGHT = 1.0    # selection weight for RNG

    def __init__(self):
        self.timer = 0
        self.active = False

    def start(self, boss):
        self.timer = 0
        self.active = True

    def play_start_sfx(self):
        """Override to play SFX when attack begins."""
        pass

    def update(self, boss, players, particles, dt=1):
        self.timer += 1
        if self.timer >= self.DURATION:
            self.active = False
            return True
        return False

    def draw(self, screen, boss):
        pass


class BossPhase:
    """A boss phase with HP threshold, attack pool, and vulnerability windows.

    Attributes:
        hp_threshold: phase transitions when boss HP drops below this ratio (0.0-1.0)
        attacks: list of AttackPattern instances
        vulnerability_after_attack: frames of vulnerability after each attack
        speed_mult: movement speed multiplier for this phase
    """

    def __init__(self, hp_threshold, attacks, vulnerability_after_attack=90,
                 speed_mult=1.0, color=NEON_MAGENTA):
        self.hp_threshold = hp_threshold
        self.attacks = attacks
        self.vulnerability_after_attack = vulnerability_after_attack
        self.speed_mult = speed_mult
        self.color = color
        self.entered = False

    def select_attack(self):
        """Weighted random selection from attack pool."""
        total = sum(a.WEIGHT for a in self.attacks)
        roll = random.random() * total
        cumulative = 0
        for attack in self.attacks:
            cumulative += attack.WEIGHT
            if roll <= cumulative:
                return attack
        return self.attacks[-1]


class HeatBolt(pygame.sprite.Sprite):
    """Projectile fired by player at boss when they have enough heat."""

    def __init__(self, x, y, color=SOLAR_YELLOW):
        super().__init__()
        self.image = pygame.Surface((8, 20), pygame.SRCALPHA)
        pygame.draw.ellipse(self.image, (*color[:3], 200), (0, 0, 8, 20))
        pygame.draw.ellipse(self.image, SOLAR_WHITE, (2, 2, 4, 16))
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = -10
        self.damage = 15
        self.alive = True

    def update(self):
        self.rect.y += self.speed
        if self.rect.bottom < -20:
            self.alive = False
            self.kill()


class Boss(pygame.sprite.Sprite):
    """Base boss class. 3 phases, randomized attacks, 3 damage methods.

    Damage methods:
        1. Ram — player collides during vulnerability window
        2. Heat bolt — player fires projectile (HeatBolt)
        3. Environmental — boss collides with hazards (solar flares, ramps, etc.)

    Subclass and override:
        _build_phases() → list of BossPhase
        _create_surface() → pygame.Surface for the boss sprite
        _update_movement(players, dt) — custom movement AI
        _draw_extras(screen) — extra visual effects
        _on_phase_change(new_phase_idx) — react to phase transition
        _on_death(particles) — death explosion / effects
    """

    MAX_HP = 300
    RAM_DAMAGE = 25
    ENVIRONMENTAL_DAMAGE = 50
    INVULN_AFTER_HIT = 30  # frames

    def __init__(self, x, y, particles, tier=1):
        super().__init__()
        self.tier = tier
        self.max_hp = self.MAX_HP
        self.hp = self.max_hp
        self.particles = particles

        self.phases = self._build_phases()
        self.current_phase_idx = 0
        self.current_phase = self.phases[0]
        self.current_phase.entered = True

        self.current_attack = None
        self.vulnerable = False
        self.vulnerability_timer = 0
        self.invuln_timer = 0

        self.alive = True
        self.defeated = False
        self.death_timer = 0
        self.DEATH_ANIM_FRAMES = 120

        self.warning_timer = 180  # 3 second warning before active
        self.active = False
        play_sfx("boss_enter")

        self.image = self._create_surface()
        self.rect = self.image.get_rect(center=(x, y))

        self.pulse = 0

    def _build_phases(self):
        """Override: return list of BossPhase."""
        return [BossPhase(1.0, [AttackPattern()])]

    def _create_surface(self):
        """Override: return pygame.Surface for boss."""
        surf = pygame.Surface((80, 80), pygame.SRCALPHA)
        pygame.draw.circle(surf, NEON_MAGENTA, (40, 40), 38)
        pygame.draw.circle(surf, SOLAR_YELLOW, (40, 40), 30, 3)
        return surf

    def _update_movement(self, players, dt=1):
        """Override: boss movement AI."""
        pass

    def _draw_extras(self, screen):
        """Override: additional boss visuals."""
        pass

    def _on_phase_change(self, new_phase_idx):
        """Override: react to phase transition."""
        pass

    def _on_death(self, particles):
        """Override: death effects."""
        particles.burst(self.rect.centerx, self.rect.centery,
                        [SOLAR_YELLOW, SOLAR_WHITE, NEON_MAGENTA], 40, 8, 80, 5)

    def get_attack_hazards(self):
        """Return list of (type, data) tuples for active attack hitboxes.
        Override in subclass. Default: no hazards."""
        return []

    @property
    def hp_ratio(self):
        return self.hp / self.max_hp

    def take_damage(self, amount, source="ram"):
        """Apply damage. Returns True if damage was dealt."""
        if self.invuln_timer > 0 or not self.alive:
            return False

        # Ram damage only during vulnerability
        if source == "ram" and not self.vulnerable:
            return False

        self.hp -= amount
        self.invuln_timer = self.INVULN_AFTER_HIT
        play_sfx("boss_hit")

        # Phase transition check
        self._check_phase_transition()

        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            self.defeated = True
            self.death_timer = self.DEATH_ANIM_FRAMES
            play_sfx("boss_defeat")
            self._on_death(self.particles)
            return True

        return True

    def _check_phase_transition(self):
        """Advance to next phase if HP dropped below threshold."""
        for i, phase in enumerate(self.phases):
            if i > self.current_phase_idx and not phase.entered:
                if self.hp_ratio <= phase.hp_threshold:
                    self.current_phase_idx = i
                    self.current_phase = phase
                    phase.entered = True
                    self.current_attack = None
                    self.vulnerable = False
                    self._on_phase_change(i)
                    play_sfx("boss_phase_drop")
                    break

    def update(self, players, scroll_speed=0):
        """Main boss update. Call from mode's update()."""
        self.pulse += 1

        # Warning phase
        if self.warning_timer > 0:
            self.warning_timer -= 1
            if self.warning_timer <= 0:
                self.active = True
            return

        # Death animation
        if self.defeated:
            if self.death_timer == self.DEATH_ANIM_FRAMES - 1:
                play_sfx("boss_death_rumble")
            self.death_timer -= 1
            if self.death_timer <= 0:
                self.kill()
            elif self.death_timer % 8 == 0:
                ox = random.randint(-40, 40)
                oy = random.randint(-40, 40)
                self.particles.burst(
                    self.rect.centerx + ox, self.rect.centery + oy,
                    [SOLAR_YELLOW, NEON_MAGENTA], 5, 4, 30, 3
                )
            return

        if not self.active or not self.alive:
            return

        # Invulnerability cooldown
        if self.invuln_timer > 0:
            self.invuln_timer -= 1

        # Attack state machine
        if self.current_attack and self.current_attack.active:
            done = self.current_attack.update(self, players, self.particles)
            if done:
                self.current_attack = None
                self.vulnerable = True
                self.vulnerability_timer = self.current_phase.vulnerability_after_attack
        elif self.vulnerable:
            self.vulnerability_timer -= 1
            if self.vulnerability_timer <= 0:
                self.vulnerable = False
                # Pick next attack
                self.current_attack = self.current_phase.select_attack()
                self.current_attack.start(self)
                self.current_attack.play_start_sfx()
        else:
            # No attack active, not vulnerable — start next attack
            self.current_attack = self.current_phase.select_attack()
            self.current_attack.start(self)
            self.current_attack.play_start_sfx()

        # Movement
        self._update_movement(players)

    def draw(self, screen):
        """Draw boss + HP bar + warning."""
        if self.warning_timer > 0:
            self._draw_warning(screen)
            return

        if self.defeated and self.death_timer > 0:
            # Flash during death
            if self.death_timer % 4 < 2:
                screen.blit(self.image, self.rect)
            return

        if not self.alive:
            return

        # Invuln flash
        if self.invuln_timer > 0 and self.invuln_timer % 4 < 2:
            return  # Skip draw frame for flash

        # Vulnerability glow
        if self.vulnerable:
            glow = pygame.Surface((self.rect.w + 20, self.rect.h + 20), pygame.SRCALPHA)
            pulse_a = int(80 + 40 * math.sin(self.pulse * 0.15))
            pygame.draw.ellipse(glow, (*SOLAR_YELLOW, pulse_a),
                                (0, 0, self.rect.w + 20, self.rect.h + 20))
            screen.blit(glow, (self.rect.x - 10, self.rect.y - 10))

        screen.blit(self.image, self.rect)

        # Draw current attack visuals
        if self.current_attack and self.current_attack.active:
            self.current_attack.draw(screen, self)

        self._draw_extras(screen)

        # HP bar
        self._draw_hp_bar(screen)

    def _draw_warning(self, screen):
        """Draw boss warning overlay."""
        progress = 1.0 - (self.warning_timer / 180)
        alpha = int(min(200, progress * 300))

        # Flashing WARNING text
        if (self.warning_timer // 15) % 2 == 0:
            font = load_font("dejavusans", 48, bold=True)
            txt = font.render("WARNING", True, (255, 50, 50))
            txt.set_alpha(alpha)
            screen.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2,
                              SCREEN_HEIGHT // 2 - 60))

        font_sm = load_font("dejavusans", 24, bold=True)
        name_txt = font_sm.render("BOSS APPROACHING", True, SOLAR_YELLOW)
        name_txt.set_alpha(alpha)
        screen.blit(name_txt, (SCREEN_WIDTH // 2 - name_txt.get_width() // 2,
                                SCREEN_HEIGHT // 2))

    def _draw_hp_bar(self, screen):
        """Draw boss HP bar at top of screen."""
        bar_w = 300
        bar_h = 16
        bar_x = (SCREEN_WIDTH - bar_w) // 2
        bar_y = SCREEN_HEIGHT - 40

        # Background
        pygame.draw.rect(screen, (20, 20, 30), (bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4))
        pygame.draw.rect(screen, (40, 40, 50), (bar_x, bar_y, bar_w, bar_h))

        # Fill
        fill_w = int(bar_w * self.hp_ratio)
        if fill_w > 0:
            color = NEON_CYAN if self.hp_ratio > 0.5 else SOLAR_YELLOW if self.hp_ratio > 0.25 else (255, 50, 50)
            pygame.draw.rect(screen, color, (bar_x, bar_y, fill_w, bar_h))

        # Border
        border_color = SOLAR_YELLOW if self.vulnerable else NEON_MAGENTA
        pygame.draw.rect(screen, border_color, (bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4), 2)

        # Label
        font = load_font("dejavusans", 12, bold=True)
        label = font.render("BOSS", True, SOLAR_WHITE)
        screen.blit(label, (bar_x + bar_w // 2 - label.get_width() // 2, bar_y))
