import pygame
import random
import math

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, NEON_CYAN, NEON_MAGENTA,
    SOLAR_YELLOW, SOLAR_WHITE, DESERT_ORANGE, COIN_GOLD,
    POWERUP_SHIELD, POWERUP_MAGNET, POWERUP_SLOWMO,
    POWERUP_NUKE, POWERUP_PHASE, POWERUP_SURGE,
    POWERUP_COLORS, POWERUP_LABELS, POWERUP_ALL, WHITE,
)


class Ramp(pygame.sprite.Sprite):
    """Ramp that launches player into the air when hit."""
    def __init__(self, x, lane_y):
        super().__init__()
        self.image = pygame.Surface((50, 30), pygame.SRCALPHA)
        # Draw ramp shape
        pts = [(0, 30), (50, 30), (50, 5), (10, 25)]
        pygame.draw.polygon(self.image, (180, 140, 60), pts)
        pygame.draw.polygon(self.image, SOLAR_YELLOW, pts, 2)
        # Arrow
        pygame.draw.line(self.image, NEON_CYAN, (25, 25), (40, 10), 2)
        pygame.draw.line(self.image, NEON_CYAN, (35, 15), (40, 10), 2)
        self.rect = self.image.get_rect(midleft=(x, lane_y + 20))
        self.launch_power = -12

    def update(self, scroll_speed):
        self.rect.x -= scroll_speed
        if self.rect.right < -50:
            self.kill()


class Barrier(pygame.sprite.Sprite):
    """Static barrier obstacle in a lane."""
    def __init__(self, x, lane_y, lane_h=55):
        super().__init__()
        w = random.choice([30, 40, 50])
        h = lane_h - 10
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(self.image, (200, 60, 40), (0, 0, w, h))
        pygame.draw.rect(self.image, NEON_MAGENTA, (0, 0, w, h), 2)
        # Hazard stripes
        for sy in range(0, h, 8):
            pygame.draw.line(self.image, (255, 200, 0), (0, sy), (w, sy + 4), 1)
        self.rect = self.image.get_rect(midleft=(x, lane_y + lane_h // 2))

    def update(self, scroll_speed):
        self.rect.x -= scroll_speed
        if self.rect.right < -60:
            self.kill()


class MudPatch(pygame.sprite.Sprite):
    """Mud patch that slows the player."""
    def __init__(self, x, lane_y, lane_h=55):
        super().__init__()
        w = random.randint(60, 120)
        h = lane_h - 5
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(self.image, (80, 50, 20, 140), (0, 0, w, h))
        pygame.draw.ellipse(self.image, (100, 65, 25, 100), (4, 4, w - 8, h - 8))
        self.rect = self.image.get_rect(midleft=(x, lane_y + lane_h // 2))
        self.slow_factor = 0.5

    def update(self, scroll_speed):
        self.rect.x -= scroll_speed
        if self.rect.right < -130:
            self.kill()


class SideRacer(pygame.sprite.Sprite):
    """AI opponent racer in excitebike mode."""
    def __init__(self, x, lane_y, lane_h=55):
        super().__init__()
        self.image = pygame.Surface((36, 20), pygame.SRCALPHA)
        color = random.choice([(200, 80, 80), (80, 200, 80), (80, 80, 200), (200, 200, 80)])
        # Simple bike shape (side view)
        pygame.draw.ellipse(self.image, (40, 40, 40), (0, 10, 12, 12))   # rear wheel
        pygame.draw.ellipse(self.image, (40, 40, 40), (24, 10, 12, 12))  # front wheel
        pygame.draw.rect(self.image, color, (4, 4, 28, 10))              # body
        pygame.draw.polygon(self.image, (*color, 200), [(28, 2), (34, 6), (28, 8)])  # nose
        self.rect = self.image.get_rect(midleft=(x, lane_y + lane_h // 2))
        self.own_speed = random.uniform(1, 4)

    def update(self, scroll_speed):
        self.rect.x -= (scroll_speed - self.own_speed)
        if self.rect.right < -50 or self.rect.left > SCREEN_WIDTH + 50:
            self.kill()


class ExcitebikeCoin(pygame.sprite.Sprite):
    """Coin for excitebike mode (horizontal scrolling)."""
    def __init__(self, x, lane_y, lane_h=55):
        super().__init__()
        self.pulse = random.randint(0, 60)
        self.image = pygame.Surface((22, 22), pygame.SRCALPHA)
        self._draw()
        self.rect = self.image.get_rect(center=(x, lane_y + lane_h // 2))

    def _draw(self):
        self.image.fill((0, 0, 0, 0))
        p = 0.75 + 0.25 * math.sin(self.pulse * 0.12)
        pygame.draw.circle(self.image, (*COIN_GOLD, int(60 * p)), (11, 11), 10)
        pygame.draw.circle(self.image, COIN_GOLD, (11, 11), 7)
        pygame.draw.circle(self.image, (255, 245, 180), (11, 11), 4)

    def update(self, scroll_speed):
        self.pulse += 1
        self._draw()
        self.rect.x -= scroll_speed
        if self.rect.right < -30:
            self.kill()


class ExcitebikePowerUp(pygame.sprite.Sprite):
    """Power-up for excitebike mode."""
    def __init__(self, x, lane_y, kind=None, lane_h=55):
        super().__init__()
        self.kind = kind or random.choice(POWERUP_ALL)
        self.color = POWERUP_COLORS[self.kind]
        self.pulse = random.randint(0, 60)
        self.image = pygame.Surface((30, 30), pygame.SRCALPHA)
        self._draw()
        self.rect = self.image.get_rect(center=(x, lane_y + lane_h // 2))

    def _draw(self):
        self.image.fill((0, 0, 0, 0))
        p = 0.65 + 0.35 * math.sin(self.pulse * 0.1)
        pygame.draw.circle(self.image, (*self.color, int(60 * p)), (15, 15), 14)
        pygame.draw.circle(self.image, self.color, (15, 15), 10, 2)
        pygame.draw.circle(self.image, (*self.color, 180), (15, 15), 7)
        import core.fonts as _fonts
        label = _fonts.FONT_POWERUP.render(POWERUP_LABELS[self.kind], True, WHITE)
        self.image.blit(label, (15 - label.get_width() // 2, 15 - label.get_height() // 2))

    def update(self, scroll_speed):
        self.pulse += 1
        self._draw()
        self.rect.x -= scroll_speed
        if self.rect.right < -40:
            self.kill()


class ExcitebikePlayer(pygame.sprite.Sprite):
    """Side-scrolling bike player for Excitebike mode."""

    def __init__(self, particles, player_num=1, lane=1, solo=False, diff="normal"):
        super().__init__()
        self.player_num = player_num
        self.particles = particles
        self.is_ai = False
        self._ai_keys = {}
        self.score_mult = 1

        if player_num == 1:
            self.color_main = (0, 180, 200)
            self.color_accent = NEON_CYAN
            self.key_up = [pygame.K_w]
            self.key_down = [pygame.K_s]
            self.key_accel = [pygame.K_d]
            self.key_brake = [pygame.K_a]
            self.key_boost = [pygame.K_LSHIFT]
            self.key_fire = [pygame.K_e]
            if solo:
                self.key_up.append(pygame.K_UP)
                self.key_down.append(pygame.K_DOWN)
                self.key_accel.append(pygame.K_RIGHT)
                self.key_brake.append(pygame.K_LEFT)
                self.key_boost.append(pygame.K_RSHIFT)
                self.key_boost.append(pygame.K_SPACE)
                self.key_fire.append(pygame.K_RETURN)
        else:
            self.color_main = (200, 50, 150)
            self.color_accent = NEON_MAGENTA
            self.key_up = [pygame.K_UP]
            self.key_down = [pygame.K_DOWN]
            self.key_accel = [pygame.K_RIGHT]
            self.key_brake = [pygame.K_LEFT]
            self.key_boost = [pygame.K_RSHIFT]
            self.key_fire = [pygame.K_RETURN]

        self._key_groups = {
            "up": self.key_up, "down": self.key_down,
            "accel": self.key_accel, "brake": self.key_brake,
            "boost": self.key_boost, "fire": self.key_fire,
        }

        self.image = self._make_bike()
        self.lane = lane  # 0, 1, 2
        self.target_lane = lane
        self.lane_transition = 0.0

        from backgrounds.excitebike_bg import ExcitebikeBg
        self.lane_ys = ExcitebikeBg.LANE_Y
        self.lane_h = ExcitebikeBg.LANE_HEIGHT

        self.rect = self.image.get_rect(
            center=(150, self.lane_ys[self.lane] + self.lane_h // 2))

        self.speed = 3.0
        self.heat = 0.0
        self.ghost_mode = False
        self.ghost_timer = 0
        self.vel_y = 0.0
        self.airborne = False
        self.alive = True
        self.lives = 3
        self.max_lives = 3
        self.score = 0
        self.distance = 0.0
        self.coins = 0
        self.invincible_timer = 0
        self.shield = False
        self.shield_timer = 0
        self.magnet = False
        self.magnet_timer = 0
        self.slowmo = False
        self.slowmo_timer = 0
        self.phase = False
        self.phase_timer = 0
        self.surge = False
        self.surge_timer = 0
        self.name = f"P{player_num}"
        self.fire_cooldown = 0
        self.last_emit = 0

        from core.ui import ComboTracker
        self.combo = ComboTracker()

    def _make_bike(self):
        surf = pygame.Surface((44, 24), pygame.SRCALPHA)
        # Wheels
        pygame.draw.circle(surf, (60, 60, 60), (8, 18), 6)
        pygame.draw.circle(surf, (60, 60, 60), (36, 18), 6)
        pygame.draw.circle(surf, (100, 100, 100), (8, 18), 4)
        pygame.draw.circle(surf, (100, 100, 100), (36, 18), 4)
        # Body
        pygame.draw.rect(surf, self.color_main, (6, 6, 32, 10))
        # Windshield
        pygame.draw.polygon(surf, (*self.color_accent, 180), [(34, 4), (40, 8), (34, 10)])
        # Rider
        pygame.draw.circle(surf, (200, 180, 160), (20, 3), 4)
        # Exhaust
        pygame.draw.rect(surf, (150, 80, 30), (2, 10, 6, 4))
        return surf

    def _any_key(self, keys, key_list):
        if self.is_ai:
            for name, grp in self._key_groups.items():
                if grp is key_list:
                    return self._ai_keys.get(name, False)
            return False
        return any(keys[k] for k in key_list)

    def try_fire_heat_bolt(self, keys):
        if not self.alive or self.fire_cooldown > 0:
            return False, 0, 0
        if self._any_key(keys, self.key_fire) and self.heat >= 40:
            self.heat -= 40
            self.fire_cooldown = 30
            from core.sound import SFX
            SFX["heat_bolt"].play()
            return True, self.rect.right, self.rect.centery
        return False, 0, 0

    def update(self, keys, scroll_speed=5):
        if not self.alive:
            return

        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1

        # Lane switching
        if self._any_key(keys, self.key_up) and self.lane > 0 and not self.airborne:
            if self.target_lane == self.lane:
                self.target_lane = self.lane - 1
                self.lane_transition = 0.0
        if self._any_key(keys, self.key_down) and self.lane < 2 and not self.airborne:
            if self.target_lane == self.lane:
                self.target_lane = self.lane + 1
                self.lane_transition = 0.0

        # Smooth lane transition
        if self.lane != self.target_lane:
            self.lane_transition += 0.08
            if self.lane_transition >= 1.0:
                self.lane = self.target_lane
                self.lane_transition = 0.0

        # Accel/brake
        if self._any_key(keys, self.key_accel):
            self.speed = min(self.speed + 0.3, 12)
            self.heat += 1.0
        if self._any_key(keys, self.key_brake):
            self.speed = max(self.speed - 0.5, 1)

        # Boost
        if self._any_key(keys, self.key_boost) and self.heat > 50:
            self.speed += 4
            self.heat = 0
            from core.sound import SFX
            SFX["boost"].play()

        # Ghost mode
        if self.heat > 100:
            self.ghost_mode = True
            self.ghost_timer = 180
            self.heat = 0
        if self.ghost_mode:
            self.ghost_timer -= 1
            if self.ghost_timer <= 0:
                self.ghost_mode = False

        self.heat = max(0, self.heat - 0.3)
        self.speed = max(self.speed - 0.05, 1)
        self.distance += self.speed * 0.01
        self.score += int(self.speed * 0.5 * self.score_mult)

        # Position
        current_y = self.lane_ys[self.lane] + self.lane_h // 2
        if self.lane != self.target_lane:
            target_y = self.lane_ys[self.target_lane] + self.lane_h // 2
            current_y = current_y + (target_y - current_y) * self.lane_transition

        if self.airborne:
            self.vel_y += 0.5
            current_y += self.vel_y
            ground_y = self.lane_ys[self.lane] + self.lane_h // 2
            if current_y >= ground_y:
                current_y = ground_y
                self.airborne = False
                self.vel_y = 0

        self.rect.centery = int(current_y)
        self.rect.centerx = 150  # Fixed x position

        # Powerup timers
        if self.invincible_timer > 0:
            self.invincible_timer -= 1
        if self.shield_timer > 0:
            self.shield_timer -= 1
            if self.shield_timer <= 0:
                self.shield = False
        if self.magnet_timer > 0:
            self.magnet_timer -= 1
            if self.magnet_timer <= 0:
                self.magnet = False
        if self.slowmo_timer > 0:
            self.slowmo_timer -= 1
            if self.slowmo_timer <= 0:
                self.slowmo = False
        if self.phase_timer > 0:
            self.phase_timer -= 1
            if self.phase_timer <= 0:
                self.phase = False
        if self.surge_timer > 0:
            self.surge_timer -= 1
            self.speed = max(self.speed, 15)
            if self.surge_timer <= 0:
                self.surge = False

        # Exhaust particles
        now = pygame.time.get_ticks()
        if self._any_key(keys, self.key_accel) and now - self.last_emit > 80:
            self.particles.emit(self.rect.left - 2, self.rect.centery + 2,
                                self.color_accent,
                                [random.uniform(-3, -1), random.uniform(-0.5, 0.5)], 20, 2)
            self.last_emit = now

        self.combo.update()

    def take_hit(self, shake):
        if self.invincible_timer > 0 or self.ghost_mode or self.phase:
            return False
        if self.shield:
            self.shield = False
            self.shield_timer = 0
            self.invincible_timer = 30
            from core.sound import SFX
            SFX["shield_hit"].play()
            shake.trigger(4, 10)
            return False

        self.lives -= 1
        self.invincible_timer = 120

        if self.lives <= 0:
            self.alive = False
            from core.sound import SFX
            SFX["life_lost"].play()
            shake.trigger(12, 30)
        else:
            from core.sound import SFX
            SFX["life_lost"].play()
            shake.trigger(8, 20)
            self.speed = max(1, self.speed - 3)
        return True

    def launch(self, power=-12):
        if not self.airborne:
            self.airborne = True
            self.vel_y = power
