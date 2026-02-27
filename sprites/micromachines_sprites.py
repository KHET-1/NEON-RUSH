import pygame
import random
import math

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, NEON_CYAN, NEON_MAGENTA,
    SOLAR_YELLOW, SOLAR_WHITE, COIN_GOLD,
    POWERUP_SHIELD, POWERUP_MAGNET, POWERUP_SLOWMO,
    POWERUP_NUKE, POWERUP_PHASE, POWERUP_SURGE,
    POWERUP_COLORS, POWERUP_LABELS, POWERUP_ALL, WHITE,
)


class MicroPlayer(pygame.sprite.Sprite):
    """Top-down tiny car with rotation steering and drift=heat."""

    def __init__(self, particles, player_num=1, solo=False, diff="normal"):
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
            self.key_left = [pygame.K_a]
            self.key_right = [pygame.K_d]
            self.key_boost = [pygame.K_LSHIFT]
            self.key_fire = [pygame.K_e]
            if solo:
                self.key_up.append(pygame.K_UP)
                self.key_down.append(pygame.K_DOWN)
                self.key_left.append(pygame.K_LEFT)
                self.key_right.append(pygame.K_RIGHT)
                self.key_boost.append(pygame.K_RSHIFT)
                self.key_boost.append(pygame.K_SPACE)
                self.key_fire.append(pygame.K_RETURN)
        else:
            self.color_main = (200, 50, 150)
            self.color_accent = NEON_MAGENTA
            self.key_up = [pygame.K_UP]
            self.key_down = [pygame.K_DOWN]
            self.key_left = [pygame.K_LEFT]
            self.key_right = [pygame.K_RIGHT]
            self.key_boost = [pygame.K_RSHIFT]
            self.key_fire = [pygame.K_RETURN]

        self._key_groups = {
            "up": self.key_up, "down": self.key_down,
            "left": self.key_left, "right": self.key_right,
            "boost": self.key_boost, "fire": self.key_fire,
        }

        self.angle = -math.pi / 2  # Facing up
        self.speed = 0.0
        self.px = float(SCREEN_WIDTH // 2)
        self.py = float(SCREEN_HEIGHT // 2 + 100)
        self.heat = 0.0
        self.drift_angle = 0.0

        self.base_surf = self._make_car()
        self.image = self.base_surf.copy()
        self.rect = self.image.get_rect(center=(int(self.px), int(self.py)))

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
        self.ghost_mode = False
        self.ghost_timer = 0
        self.name = f"P{player_num}"
        self.fire_cooldown = 0
        self.vel_y = 0  # Compatibility

        from core.ui import ComboTracker
        self.combo = ComboTracker()

    def _make_car(self):
        surf = pygame.Surface((20, 28), pygame.SRCALPHA)
        # Body
        pygame.draw.rect(surf, self.color_main, (3, 2, 14, 24), border_radius=3)
        # Windshield
        pygame.draw.rect(surf, (*self.color_accent, 150), (5, 3, 10, 8), border_radius=2)
        # Rear
        pygame.draw.rect(surf, (200, 80, 30), (5, 22, 10, 4))
        # Wheels
        for wx in [1, 17]:
            pygame.draw.rect(surf, (50, 50, 50), (wx, 5, 3, 6))
            pygame.draw.rect(surf, (50, 50, 50), (wx, 19, 3, 6))
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
            return True, self.rect.centerx, self.rect.centery
        return False, 0, 0

    def update(self, keys, scroll_speed=0):
        if not self.alive:
            return

        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1

        # Steering
        turn_speed = 0.05
        turning = False
        if self._any_key(keys, self.key_left):
            self.angle -= turn_speed
            turning = True
        if self._any_key(keys, self.key_right):
            self.angle += turn_speed
            turning = True

        # Accel/brake
        if self._any_key(keys, self.key_up):
            self.speed = min(self.speed + 0.2, 6)
            self.heat += 0.8
        if self._any_key(keys, self.key_down):
            self.speed = max(self.speed - 0.3, -2)

        # Drift builds heat when turning at speed
        if turning and self.speed > 2:
            self.heat += 1.5

        # Boost
        if self._any_key(keys, self.key_boost) and self.heat > 50:
            self.speed += 3
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
        self.speed *= 0.98  # Friction

        # Move
        self.px += math.cos(self.angle) * self.speed
        self.py += math.sin(self.angle) * self.speed

        # Keep on screen
        self.px = max(20, min(SCREEN_WIDTH - 20, self.px))
        self.py = max(20, min(SCREEN_HEIGHT - 20, self.py))

        self.distance += abs(self.speed) * 0.01
        self.score += int(abs(self.speed) * 0.3 * self.score_mult)

        # Rotate image
        deg = -math.degrees(self.angle) - 90
        self.image = pygame.transform.rotate(self.base_surf, deg)
        self.rect = self.image.get_rect(center=(int(self.px), int(self.py)))

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
            self.speed = max(self.speed, 8)
            if self.surge_timer <= 0:
                self.surge = False

        # Tire smoke when drifting
        if turning and self.speed > 3:
            self.particles.emit(
                self.rect.centerx, self.rect.centery,
                (150, 150, 150),
                [random.uniform(-1, 1), random.uniform(-1, 1)], 15, 2)

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
        self.speed = 0

        if self.lives <= 0:
            self.alive = False
            from core.sound import SFX
            SFX["life_lost"].play()
            shake.trigger(12, 30)
        else:
            from core.sound import SFX
            SFX["life_lost"].play()
            shake.trigger(8, 20)
        return True


class OilSlickHazard(pygame.sprite.Sprite):
    """Oil slick on track that spins the player."""
    def __init__(self, x, y):
        super().__init__()
        w, h = random.randint(30, 50), random.randint(20, 35)
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(self.image, (20, 20, 30, 160), (0, 0, w, h))
        pygame.draw.ellipse(self.image, (40, 30, 50, 100), (4, 4, w - 8, h - 8))
        self.rect = self.image.get_rect(center=(x, y))

    def update(self, scroll_speed):
        self.rect.y += scroll_speed
        if self.rect.top > SCREEN_HEIGHT + 50:
            self.kill()


class TrackBarrier(pygame.sprite.Sprite):
    """Barrier on the track edge."""
    def __init__(self, x, y):
        super().__init__()
        w = random.randint(20, 40)
        h = random.randint(15, 25)
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(self.image, (180, 50, 50), (0, 0, w, h))
        pygame.draw.rect(self.image, NEON_MAGENTA, (0, 0, w, h), 2)
        self.rect = self.image.get_rect(center=(x, y))

    def update(self, scroll_speed):
        self.rect.y += scroll_speed
        if self.rect.top > SCREEN_HEIGHT + 50:
            self.kill()


class TinyCar(pygame.sprite.Sprite):
    """AI opponent car in top-down view."""
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((16, 22), pygame.SRCALPHA)
        color = random.choice([(200, 80, 80), (80, 200, 80), (200, 200, 80), (80, 80, 200)])
        pygame.draw.rect(self.image, color, (2, 1, 12, 20), border_radius=3)
        pygame.draw.rect(self.image, (50, 50, 50), (0, 4, 3, 5))
        pygame.draw.rect(self.image, (50, 50, 50), (13, 4, 3, 5))
        pygame.draw.rect(self.image, (50, 50, 50), (0, 14, 3, 5))
        pygame.draw.rect(self.image, (50, 50, 50), (13, 14, 3, 5))
        self.rect = self.image.get_rect(center=(x, y))
        self.own_speed = random.uniform(0.5, 2)

    def update(self, scroll_speed):
        self.rect.y += scroll_speed - self.own_speed
        if self.rect.top > SCREEN_HEIGHT + 50 or self.rect.bottom < -50:
            self.kill()


class MicroCoin(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.pulse = random.randint(0, 60)
        self.image = pygame.Surface((18, 18), pygame.SRCALPHA)
        self._draw()
        self.rect = self.image.get_rect(center=(x, y))

    def _draw(self):
        self.image.fill((0, 0, 0, 0))
        p = 0.75 + 0.25 * math.sin(self.pulse * 0.12)
        pygame.draw.circle(self.image, (*COIN_GOLD, int(60 * p)), (9, 9), 8)
        pygame.draw.circle(self.image, COIN_GOLD, (9, 9), 6)

    def update(self, scroll_speed):
        self.pulse += 1
        self._draw()
        self.rect.y += scroll_speed
        if self.rect.top > SCREEN_HEIGHT + 30:
            self.kill()


class MicroPowerUp(pygame.sprite.Sprite):
    def __init__(self, x, y, kind=None):
        super().__init__()
        self.kind = kind or random.choice(POWERUP_ALL)
        self.color = POWERUP_COLORS[self.kind]
        self.pulse = random.randint(0, 60)
        self.image = pygame.Surface((24, 24), pygame.SRCALPHA)
        self._draw()
        self.rect = self.image.get_rect(center=(x, y))

    def _draw(self):
        self.image.fill((0, 0, 0, 0))
        p = 0.65 + 0.35 * math.sin(self.pulse * 0.1)
        pygame.draw.circle(self.image, (*self.color, int(60 * p)), (12, 12), 11)
        pygame.draw.circle(self.image, self.color, (12, 12), 8, 2)
        pygame.draw.circle(self.image, (*self.color, 180), (12, 12), 6)
        import core.fonts as _fonts
        label = _fonts.FONT_POWERUP.render(POWERUP_LABELS[self.kind], True, WHITE)
        self.image.blit(label, (12 - label.get_width() // 2, 12 - label.get_height() // 2))

    def update(self, scroll_speed):
        self.pulse += 1
        self._draw()
        self.rect.y += scroll_speed
        if self.rect.top > SCREEN_HEIGHT + 30:
            self.kill()
