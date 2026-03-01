import pygame
import random
import math

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, NEON_CYAN, NEON_MAGENTA,
    SOLAR_WHITE, SOLAR_YELLOW, DESERT_ORANGE, SAND_YELLOW,
    ROAD_LEFT, ROAD_RIGHT, ROAD_CENTER, GRAVITY,
    DIFFICULTY_SETTINGS, DIFF_NORMAL,
    POWERUP_SHIELD, POWERUP_MAGNET, POWERUP_SLOWMO,
)
from core.sound import SFX
from core.ui import ComboTracker


def make_vehicle_surface(color_main, color_accent, is_ghost=False):
    surf = pygame.Surface((40, 60), pygame.SRCALPHA)
    alpha = 140 if is_ghost else 255
    cx, cy = 20, 30
    body = [(cx, 2), (cx + 16, cy + 14), (cx + 12, cy + 26), (cx - 12, cy + 26), (cx - 16, cy + 14)]
    shadow = [(cx + 2, 4), (cx + 16, cy + 14), (cx + 10, cy + 24), (cx - 10, cy + 24), (cx - 14, cy + 14)]
    pygame.draw.polygon(surf, (*color_main, alpha), body)
    pygame.draw.polygon(surf, (*color_accent, int(alpha * 0.4)), shadow)
    inner = [(cx, 10), (cx + 10, cy + 8), (cx + 6, cy + 20), (cx - 6, cy + 20), (cx - 10, cy + 8)]
    pygame.draw.polygon(surf, (*color_accent, int(alpha * 0.6)), inner)
    pygame.draw.lines(surf, (*color_accent, min(255, alpha + 40)), True, body, 2)
    pygame.draw.ellipse(surf, (*SOLAR_WHITE, alpha // 2), (cx - 6, 14, 12, 16))
    pygame.draw.ellipse(surf, (*DESERT_ORANGE, alpha // 3), (cx - 7, cy + 18, 14, 6))
    return surf


def make_vehicle_surface_v2(color_main, color_accent, is_ghost=False):
    """V2+ vehicle with underglow, detail shading, windshield glint, exhaust glow."""
    surf = pygame.Surface((48, 68), pygame.SRCALPHA)
    alpha = 140 if is_ghost else 255
    cx, cy = 24, 34

    # Underglow: wide ellipse beneath car body
    pygame.draw.ellipse(surf, (*color_accent, 40), (cx - 18, cy + 10, 36, 20))

    # Main body (same shape, slightly larger)
    body = [(cx, 4), (cx + 18, cy + 14), (cx + 14, cy + 28), (cx - 14, cy + 28), (cx - 18, cy + 14)]
    shadow = [(cx + 2, 6), (cx + 18, cy + 14), (cx + 12, cy + 26), (cx - 12, cy + 26), (cx - 16, cy + 14)]
    pygame.draw.polygon(surf, (*color_main, alpha), body)
    pygame.draw.polygon(surf, (*color_accent, int(alpha * 0.4)), shadow)

    # Detail shading: darker stripe along each side (2px inset)
    side_dark = tuple(max(0, c - 40) for c in color_main)
    left_stripe = [(cx - 16, cy + 14), (cx - 12, cy + 26), (cx - 14, cy + 26), (cx - 18, cy + 14)]
    right_stripe = [(cx + 16, cy + 14), (cx + 12, cy + 26), (cx + 14, cy + 26), (cx + 18, cy + 14)]
    pygame.draw.polygon(surf, (*side_dark, int(alpha * 0.7)), left_stripe)
    pygame.draw.polygon(surf, (*side_dark, int(alpha * 0.7)), right_stripe)

    # Inner panel
    inner = [(cx, 12), (cx + 12, cy + 8), (cx + 8, cy + 22), (cx - 8, cy + 22), (cx - 12, cy + 8)]
    pygame.draw.polygon(surf, (*color_accent, int(alpha * 0.6)), inner)

    # Body outline
    pygame.draw.lines(surf, (*color_accent, min(255, alpha + 40)), True, body, 2)

    # Windshield with glint
    pygame.draw.ellipse(surf, (*SOLAR_WHITE, alpha // 2), (cx - 7, 16, 14, 18))
    # Bright white glint line across windshield top
    pygame.draw.line(surf, (255, 255, 255, min(255, alpha)), (cx - 5, 17), (cx + 5, 17), 1)

    # Exhaust glow: 2 stacked ellipses (inner bright, outer alpha glow)
    pygame.draw.ellipse(surf, (*DESERT_ORANGE, alpha // 4), (cx - 10, cy + 22, 20, 10))
    pygame.draw.ellipse(surf, (*DESERT_ORANGE, int(alpha * 0.7)), (cx - 6, cy + 24, 12, 6))
    pygame.draw.ellipse(surf, (*SOLAR_WHITE, alpha // 2), (cx - 3, cy + 25, 6, 3))

    return surf


class Player(pygame.sprite.Sprite):
    def __init__(self, particles, player_num=1, x_pos=None, solo=False, diff=DIFF_NORMAL, tier=1):
        super().__init__()
        self.player_num = player_num
        self.diff_settings = DIFFICULTY_SETTINGS[diff]
        self.is_ai = False
        self._ai_keys = {}
        self.score_mult = 1
        self.tier = tier
        if player_num == 1:
            self.color_main = (0, 180, 200)
            self.color_accent = NEON_CYAN
            self.keys_up = [pygame.K_w]
            self.keys_down = [pygame.K_s]
            self.keys_left = [pygame.K_a]
            self.keys_right = [pygame.K_d]
            self.keys_boost = [pygame.K_LSHIFT]
            self.keys_fire = [pygame.K_e]
            if solo:
                self.keys_up.append(pygame.K_UP)
                self.keys_down.append(pygame.K_DOWN)
                self.keys_left.append(pygame.K_LEFT)
                self.keys_right.append(pygame.K_RIGHT)
                self.keys_boost.append(pygame.K_RSHIFT)
                self.keys_boost.append(pygame.K_SPACE)
                self.keys_fire.append(pygame.K_RETURN)
        else:
            self.color_main = (200, 50, 150)
            self.color_accent = NEON_MAGENTA
            self.keys_up = [pygame.K_UP]
            self.keys_down = [pygame.K_DOWN]
            self.keys_left = [pygame.K_LEFT]
            self.keys_right = [pygame.K_RIGHT]
            self.keys_boost = [pygame.K_RSHIFT]
            self.keys_fire = [pygame.K_RETURN]

        self._key_groups = {
            "up": self.keys_up, "down": self.keys_down,
            "left": self.keys_left, "right": self.keys_right,
            "boost": self.keys_boost, "fire": self.keys_fire,
        }

        if tier >= 2:
            self.base_image = make_vehicle_surface_v2(self.color_main, self.color_accent)
            self.ghost_image = make_vehicle_surface_v2(self.color_main, self.color_accent, True)
        else:
            self.base_image = make_vehicle_surface(self.color_main, self.color_accent)
            self.ghost_image = make_vehicle_surface(self.color_main, self.color_accent, True)
        self.image = self.base_image.copy()

        start_x = x_pos if x_pos else ROAD_CENTER
        self.rect = self.image.get_rect(center=(start_x, SCREEN_HEIGHT - 60))

        self.speed = 0.0
        self.heat = 0.0
        self.ghost_mode = False
        self.ghost_timer = 0
        self.vel_y = 0.0
        self.flare_boost_timer = 0
        self.particles = particles
        self.last_emit = 0
        self.crash_emit = False
        self.tilt_angle = 0.0  # visual lean into curves (degrees)
        self.flare_hit = False

        self.lives = self.diff_settings["lives"]
        self.max_lives = self.diff_settings["lives"]
        self.score = 0
        self.distance = 0.0
        self.coins = 0
        self.combo = ComboTracker()
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
        self.alive = True
        self.name = f"P{player_num}"
        self.leap_request = 0
        self.last_tap_left = 0
        self.last_tap_right = 0
        self.leap_cooldown = 0
        self.LEAP_DISTANCE = 90
        self.LEAP_COOLDOWN_FRAMES = 30
        self.DOUBLE_TAP_MS = 350

        # Heat bolt firing
        self.fire_cooldown = 0
        self.FIRE_COOLDOWN_FRAMES = 30
        self.HEAT_COST = 40

    def on_direction_tap(self, direction, now_ms, is_new_press):
        if not self.alive or not is_new_press or self.leap_cooldown > 0:
            return
        if direction < 0:
            if now_ms - self.last_tap_left < self.DOUBLE_TAP_MS:
                self.leap_request = -1
                self.leap_cooldown = self.LEAP_COOLDOWN_FRAMES
            self.last_tap_left = now_ms
        else:
            if now_ms - self.last_tap_right < self.DOUBLE_TAP_MS:
                self.leap_request = 1
                self.leap_cooldown = self.LEAP_COOLDOWN_FRAMES
            self.last_tap_right = now_ms

    def _any_key(self, keys, key_list):
        if self.is_ai:
            for name, grp in self._key_groups.items():
                if grp is key_list:
                    return self._ai_keys.get(name, False)
            return False
        return any(keys[k] for k in key_list)

    def try_fire_heat_bolt(self, keys, auto_fire=False):
        """Attempt to fire a heat bolt. Returns (fired, bolt_x, bolt_y) if successful."""
        if not self.alive or self.fire_cooldown > 0:
            return False, 0, 0
        if auto_fire:
            # Auto-fire: free, fast, silent
            self.fire_cooldown = 12
            return True, self.rect.centerx, self.rect.top
        if self._any_key(keys, self.keys_fire) and self.heat >= self.HEAT_COST:
            self.heat -= self.HEAT_COST
            self.fire_cooldown = self.FIRE_COOLDOWN_FRAMES
            SFX["heat_bolt"].play()
            return True, self.rect.centerx, self.rect.top
        return False, 0, 0

    def update(self, keys, slowmo_active=False, road_geometry=None):
        if not self.alive:
            return

        spd_m = 0.5 if slowmo_active else 1.0

        # Compute dynamic road bounds
        if road_geometry:
            r_left, r_right = road_geometry.get_road_bounds_at_bottom()
            bound_left = int(r_left) + 5
            bound_right = int(r_right) - self.rect.width - 5
            # Curve drift force: very subtle push on curves
            curve_force = road_geometry.current_curve * 0.4
        else:
            bound_left = ROAD_LEFT + 5
            bound_right = ROAD_RIGHT - self.rect.width - 5
            curve_force = 0.0

        if self.leap_cooldown > 0:
            self.leap_cooldown -= 1
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1

        if self.leap_request != 0:
            dx = self.leap_request * self.LEAP_DISTANCE
            self.rect.x = max(bound_left, min(self.rect.x + dx, bound_right))
            for _ in range(8):
                vx = random.uniform(-2, 2) - self.leap_request * 3
                self.particles.emit(self.rect.centerx, self.rect.centery, self.color_accent, [vx, random.uniform(-1, 1)], life=25, size=2)
            SFX["boost"].play()
            self.leap_request = 0

        if self._any_key(keys, self.keys_left):
            self.rect.x -= int(6.5 * spd_m)
        if self._any_key(keys, self.keys_right):
            self.rect.x += int(6.5 * spd_m)
        if self._any_key(keys, self.keys_up):
            self.speed = min(self.speed + 1.0, 16)
            self.heat += 1.5
        if self._any_key(keys, self.keys_down):
            self.speed = max(self.speed - 1.3, 0)

        # Apply curve drift
        if curve_force != 0.0:
            self.rect.x += int(curve_force * spd_m)

        self.rect.x = max(bound_left, min(self.rect.x, bound_right))

        # Vehicle tilt — lean into curves + steering for 3D feel
        target_tilt = 0.0
        if road_geometry:
            target_tilt = -road_geometry.current_curve * 12  # lean opposite to curve
        if self._any_key(keys, self.keys_left):
            target_tilt -= 5
        if self._any_key(keys, self.keys_right):
            target_tilt += 5
        target_tilt = max(-15, min(15, target_tilt))
        self.tilt_angle += (target_tilt - self.tilt_angle) * 0.15  # smooth interpolation

        # Apply tilt rotation to sprite image
        if abs(self.tilt_angle) > 0.5:
            center = self.rect.center
            self.image = pygame.transform.rotate(self.base_image, -self.tilt_angle)
            self.rect = self.image.get_rect(center=center)
        elif not self.ghost_mode:
            self.image = self.base_image.copy()

        if self.vel_y != 0:
            self.vel_y += GRAVITY
            self.rect.y += int(self.vel_y)
            if self.rect.bottom >= SCREEN_HEIGHT - 30:
                self.rect.bottom = SCREEN_HEIGHT - 30
                self.vel_y = 0
        else:
            self.rect.bottom = SCREEN_HEIGHT - 30

        if self.heat > 100:
            self.ghost_mode = True
            self.ghost_timer = 180
            self.heat = 0
        if self.ghost_mode:
            self.image = self.ghost_image.copy()
            self.ghost_timer -= 1
            if self.ghost_timer <= 0:
                self.ghost_mode = False
                self.image = self.base_image.copy()
        elif self._any_key(keys, self.keys_boost) and self.heat > 50:
            self.speed += 5
            self.heat = 0
            SFX["boost"].play()

        if self.flare_boost_timer > 0:
            self.flare_boost_timer -= 1
            self.speed = min(self.speed + 0.13, 20)
        else:
            self.speed = max(self.speed - 0.2, 0)

        self.heat = max(0, self.heat - 0.4)
        self.distance += self.speed * 0.01
        self.score += int(self.speed * 0.5 * self.score_mult)

        if self.invincible_timer > 0:
            self.invincible_timer -= 1
            self.image.set_alpha(100 if self.invincible_timer % 6 < 3 else 255)
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
            self.speed = max(self.speed, 20)
            if self.surge_timer <= 0:
                self.surge = False

        now = pygame.time.get_ticks()
        if (self._any_key(keys, self.keys_up) or self.flare_boost_timer > 0) and now - self.last_emit > 60:
            num = 3 if self.flare_boost_timer > 0 else 2
            colors = (
                [SOLAR_YELLOW, SOLAR_WHITE] if self.flare_boost_timer > 0 else [self.color_accent, (100, 100, 120)]
            )
            for _ in range(num):
                vx = random.uniform(-1, 1)
                vy = random.uniform(2, 4)
                color = random.choice(colors)
                sz = 3 if self.flare_boost_timer > 0 else 2
                self.particles.emit(self.rect.centerx, self.rect.bottom + 6, color, [vx, vy], 30, sz)
            self.last_emit = now

        if self.crash_emit:
            self.particles.burst(self.rect.centerx, self.rect.centery, [SAND_YELLOW, DESERT_ORANGE], 20, 6, 50, 4)
            self.crash_emit = False

    def take_hit(self, shake):
        if self.invincible_timer > 0 or self.ghost_mode or self.phase:
            return False
        if self.shield:
            self.shield = False
            self.shield_timer = 0
            self.invincible_timer = 30
            SFX["shield_hit"].play()
            shake.trigger(4, 10)
            return False

        self.lives -= 1
        self.crash_emit = True
        self.invincible_timer = 120

        if self.lives <= 0:
            self.alive = False
            SFX["life_lost"].play()
            shake.trigger(12, 30)
        else:
            SFX["life_lost"].play()
            shake.trigger(8, 20)
            self.speed = max(0, self.speed - 4)
        return True
