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
from core.sound import play_sfx
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
    """V2 clean racing car — simple, bold, recognizable as a car."""
    W, H = 44, 64
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    alpha = 140 if is_ghost else 255
    cx = W // 2

    # Underglow (single soft ellipse)
    pygame.draw.ellipse(surf, (*color_accent, max(1, int(50 * alpha // 255))),
                        (cx - 18, 42, 36, 14))

    # Car body — main rectangle with rounded front
    body_color = (*color_main, alpha)
    dark_body = (*tuple(max(0, c - 40) for c in color_main), alpha)
    # Rear body
    pygame.draw.rect(surf, body_color, (cx - 14, 24, 28, 30))
    # Front hood (narrower, tapered)
    pygame.draw.polygon(surf, body_color, [
        (cx - 14, 24), (cx - 10, 8), (cx + 10, 8), (cx + 14, 24)])
    # Nose tip
    pygame.draw.ellipse(surf, body_color, (cx - 8, 4, 16, 12))

    # Side panels (darker)
    pygame.draw.rect(surf, dark_body, (cx - 14, 28, 4, 22))
    pygame.draw.rect(surf, dark_body, (cx + 10, 28, 4, 22))

    # Windshield
    pygame.draw.polygon(surf, (60, 90, 120, alpha), [
        (cx - 9, 20), (cx - 7, 14), (cx + 7, 14), (cx + 9, 20)])
    # Windshield glint
    pygame.draw.line(surf, (180, 210, 240, min(255, alpha)),
                     (cx - 5, 16), (cx + 3, 14))

    # Rear wing / spoiler
    pygame.draw.rect(surf, (*color_accent, alpha), (cx - 16, 52, 32, 3))

    # Taillights
    pygame.draw.rect(surf, (255, 40, 40, alpha), (cx - 13, 52, 5, 3))
    pygame.draw.rect(surf, (255, 40, 40, alpha), (cx + 8, 52, 5, 3))

    # Headlights
    pygame.draw.rect(surf, (255, 255, 200, alpha), (cx - 8, 5, 4, 3))
    pygame.draw.rect(surf, (255, 255, 200, alpha), (cx + 4, 5, 4, 3))

    # Neon accent stripe down center
    pygame.draw.line(surf, (*color_accent, min(255, alpha)),
                     (cx, 10), (cx, 50), 1)

    # Edge outline
    outline_pts = [
        (cx - 8, 6), (cx - 10, 8), (cx - 14, 24),
        (cx - 14, 54), (cx + 14, 54), (cx + 14, 24),
        (cx + 10, 8), (cx + 8, 6),
    ]
    pygame.draw.lines(surf, (*color_accent, min(255, alpha)), True, outline_pts, 1)

    # Exhaust glow
    pygame.draw.ellipse(surf, (255, 140, 50, max(1, int(alpha * 0.5))),
                        (cx - 5, 54, 10, 6))

    return surf


def make_vehicle_surface_v3(color_main, color_accent, is_ghost=False):
    """V3 metallic racing car — specular highlights, neon wheel rims, 3-layer underglow."""
    W, H = 48, 70
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    alpha = 140 if is_ghost else 255
    cx = W // 2

    # 3-layer underglow (concentric ellipses)
    for i, (ew, eh, a) in enumerate([(42, 18, 25), (36, 14, 40), (28, 10, 55)]):
        pygame.draw.ellipse(surf, (*color_accent, max(1, int(a * alpha // 255))),
                            (cx - ew // 2, 50, ew, eh))

    # Metallic body — 3-strip shading (dark|highlight|mid)
    dark_body = tuple(max(0, c - 50) for c in color_main)
    light_body = tuple(min(255, c + 30) for c in color_main)
    # Rear body
    pygame.draw.rect(surf, (*color_main, alpha), (cx - 16, 28, 32, 34))
    # Left dark strip
    pygame.draw.rect(surf, (*dark_body, alpha), (cx - 16, 28, 5, 34))
    # Right dark strip
    pygame.draw.rect(surf, (*dark_body, alpha), (cx + 11, 28, 5, 34))
    # Center highlight strip (cylindrical metal sim)
    pygame.draw.rect(surf, (*light_body, alpha), (cx - 3, 28, 6, 34))

    # Front hood (tapered)
    pygame.draw.polygon(surf, (*color_main, alpha), [
        (cx - 16, 28), (cx - 11, 8), (cx + 11, 8), (cx + 16, 28)])
    # Nose
    pygame.draw.ellipse(surf, (*color_main, alpha), (cx - 9, 4, 18, 12))

    # Specular highlight ellipse on hood
    pygame.draw.ellipse(surf, (*light_body, min(255, int(alpha * 0.7))),
                        (cx - 6, 10, 12, 8))
    pygame.draw.ellipse(surf, (255, 255, 255, min(255, int(alpha * 0.3))),
                        (cx - 3, 12, 6, 4))

    # Windshield with metallic glint
    pygame.draw.polygon(surf, (40, 70, 100, alpha), [
        (cx - 10, 22), (cx - 8, 14), (cx + 8, 14), (cx + 10, 22)])
    pygame.draw.line(surf, (200, 230, 255, min(255, alpha)),
                     (cx - 6, 16), (cx + 4, 14))

    # 4 wheel pads with neon accent rims
    wheel_positions = [(cx - 18, 32), (cx + 14, 32), (cx - 18, 52), (cx + 14, 52)]
    for wx, wy in wheel_positions:
        pygame.draw.rect(surf, (30, 30, 35, alpha), (wx, wy, 5, 8))
        # Neon rim accent
        pygame.draw.rect(surf, (*color_accent, min(255, alpha)), (wx, wy, 5, 1))
        pygame.draw.rect(surf, (*color_accent, min(255, alpha)), (wx, wy + 7, 5, 1))

    # Rear spoiler
    pygame.draw.rect(surf, (*color_accent, alpha), (cx - 18, 60, 36, 3))

    # Rear diffuser grid
    for dx in range(cx - 10, cx + 10, 3):
        pygame.draw.line(surf, (40, 40, 50, alpha), (dx, 62), (dx, 66))

    # Taillights
    pygame.draw.rect(surf, (255, 30, 30, alpha), (cx - 15, 60, 6, 3))
    pygame.draw.rect(surf, (255, 30, 30, alpha), (cx + 9, 60, 6, 3))

    # Headlights (brighter)
    pygame.draw.rect(surf, (255, 255, 220, alpha), (cx - 9, 5, 5, 3))
    pygame.draw.rect(surf, (255, 255, 220, alpha), (cx + 4, 5, 5, 3))

    # Neon center stripe
    pygame.draw.line(surf, (*color_accent, min(255, alpha)),
                     (cx, 10), (cx, 58), 1)

    # Outline
    outline_pts = [
        (cx - 9, 6), (cx - 11, 8), (cx - 16, 28),
        (cx - 16, 62), (cx + 16, 62), (cx + 16, 28),
        (cx + 11, 8), (cx + 9, 6),
    ]
    pygame.draw.lines(surf, (*color_accent, min(255, alpha)), True, outline_pts, 1)

    # Exhaust glow (brighter for V3)
    pygame.draw.ellipse(surf, (255, 160, 60, max(1, int(alpha * 0.6))),
                        (cx - 6, 62, 12, 8))

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

        if tier >= 3:
            self.base_image = make_vehicle_surface_v3(self.color_main, self.color_accent)
            self.ghost_image = make_vehicle_surface_v3(self.color_main, self.color_accent, True)
        elif tier >= 2:
            self.base_image = make_vehicle_surface_v2(self.color_main, self.color_accent)
            self.ghost_image = make_vehicle_surface_v2(self.color_main, self.color_accent, True)
        else:
            self.base_image = make_vehicle_surface(self.color_main, self.color_accent)
            self.ghost_image = make_vehicle_surface(self.color_main, self.color_accent, True)
        self.image = self.base_image.copy()

        start_x = x_pos if x_pos else ROAD_CENTER
        self.rect = self.image.get_rect(center=(start_x, SCREEN_HEIGHT - 60))

        self.speed = 0.0
        self.max_speed = 16
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
        self.multishot = False
        self.multishot_timer = 0
        self.rockets = False
        self.rockets_timer = 0
        self.rocket_fire_cd = 0
        self.orbit8 = False
        self.orbit8_timer = 0
        self._orbit8_spawn_pending = False
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

        # Tiered boost system
        self.boost_timer = 0
        self.boost_power = 0
        self.boost_cooldown = 0

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
            play_sfx("heat_bolt")
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
            # Strong curve drift — car follows road curves (3.5x for dramatic feel)
            curve_force = road_geometry.current_curve * 3.5

            # Track road center — smoothly pull car toward road center
            bottom_sd = road_geometry.scanline_data[-1]
            road_center_x = bottom_sd.center_x
            car_center_x = self.rect.centerx
            # Gentle pull toward road center (feels like the road carries you)
            center_pull = (road_center_x - car_center_x) * 0.03

            # Track road Y position (hills)
            road_y = int(bottom_sd.screen_y)
            if not hasattr(self, '_road_y_smooth'):
                self._road_y_smooth = float(SCREEN_HEIGHT - 30)
            self._road_y_smooth += (float(road_y - 30) - self._road_y_smooth) * 0.1
        else:
            bound_left = ROAD_LEFT + 5
            bound_right = ROAD_RIGHT - self.rect.width - 5
            curve_force = 0.0
            center_pull = 0.0

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
            play_sfx("boost")
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

        # Apply curve drift + road center tracking
        total_drift = curve_force + center_pull
        if total_drift != 0.0:
            self.rect.x += int(total_drift * spd_m)

        self.rect.x = max(bound_left, min(self.rect.x, bound_right))

        # Vehicle tilt — lean into curves + steering for 3D feel
        target_tilt = 0.0
        if road_geometry:
            target_tilt = -road_geometry.current_curve * 20  # lean opposite to curve
        if self._any_key(keys, self.keys_left):
            target_tilt -= 5
        if self._any_key(keys, self.keys_right):
            target_tilt += 5
        target_tilt = max(-15, min(15, target_tilt))
        self.tilt_angle += (target_tilt - self.tilt_angle) * 0.15  # smooth interpolation

        # Apply tilt rotation to sprite image (only when angle changes significantly)
        if abs(self.tilt_angle) > 1.0:
            rounded_tilt = round(self.tilt_angle * 2) / 2  # snap to 0.5° increments
            if not hasattr(self, '_last_tilt') or abs(rounded_tilt - self._last_tilt) > 0.4:
                center = self.rect.center
                self.image = pygame.transform.rotate(self.base_image, -rounded_tilt)
                self.rect = self.image.get_rect(center=center)
                self._last_tilt = rounded_tilt
        elif not self.ghost_mode:
            if not hasattr(self, '_last_tilt') or self._last_tilt != 0:
                self.image = self.base_image
                self._last_tilt = 0

        if self.vel_y != 0:
            self.vel_y += GRAVITY
            self.rect.y += int(self.vel_y)
            target_bottom = int(getattr(self, '_road_y_smooth', SCREEN_HEIGHT - 30))
            if self.rect.bottom >= target_bottom:
                self.rect.bottom = target_bottom
                self.vel_y = 0
        else:
            target_bottom = int(getattr(self, '_road_y_smooth', SCREEN_HEIGHT - 30))
            self.rect.bottom = target_bottom

        # Tiered boost system
        boost_pressed = self._any_key(keys, self.keys_boost)
        if boost_pressed and self.boost_cooldown <= 0 and self.boost_timer <= 0:
            if self.heat >= 100:
                # Tier 3: Ghost Surge — all-in
                self.heat = 0
                self.boost_timer = 90
                self.boost_power = 10
                self.ghost_mode = True
                self.ghost_timer = 90
                self.invincible_timer = max(self.invincible_timer, 90)
                self.boost_cooldown = 18
                play_sfx("boost")
            elif self.heat >= 60:
                # Tier 2: Power Boost — medium cost, brief invincibility
                self.heat -= 60
                self.boost_timer = 54
                self.boost_power = 6
                self.invincible_timer = max(self.invincible_timer, 18)
                self.boost_cooldown = 18
                play_sfx("boost")
            elif self.heat >= 30:
                # Tier 1: Quick Boost — cheap
                self.heat -= 30
                self.boost_timer = 36
                self.boost_power = 3
                self.boost_cooldown = 18
                play_sfx("boost")

        if self.boost_timer > 0:
            self.speed = min(self.speed + self.boost_power * 0.15, self.max_speed + self.boost_power)
            self.boost_timer -= 1
        if self.boost_cooldown > 0:
            self.boost_cooldown -= 1

        if self.ghost_mode:
            self.image = self.ghost_image.copy()
            self.ghost_timer -= 1
            if self.ghost_timer <= 0:
                self.ghost_mode = False
                self.image = self.base_image.copy()

        if self.flare_boost_timer > 0:
            self.flare_boost_timer -= 1
            self.speed = min(self.speed + 0.13, 20)
        else:
            self.speed = max(self.speed - 0.2, 0)

        # Combo momentum: speed bonus from active combo, penalty on drop
        self.speed += self.combo.speed_bonus
        if self.combo.drop_penalty > 0:
            self.speed *= 0.85

        self.heat = max(0, self.heat - 0.4)
        self.distance += self.speed * 0.01
        self.score += int(self.speed * 0.5 * self.score_mult * getattr(self, 'speed_mult_factor', 1.0))

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
        if self.multishot_timer > 0:
            self.multishot_timer -= 1
            if self.multishot_timer <= 0:
                self.multishot = False
        if self.rockets_timer > 0:
            self.rockets_timer -= 1
            if self.rocket_fire_cd > 0:
                self.rocket_fire_cd -= 1
            if self.rockets_timer <= 0:
                self.rockets = False
        if self.orbit8_timer > 0:
            self.orbit8_timer -= 1
            if self.orbit8_timer <= 0:
                self.orbit8 = False
                self._orbit8_spawn_pending = False

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
            play_sfx("shield_hit")
            shake.trigger(4, 10)
            return False

        self.lives -= 1
        self.crash_emit = True
        self.invincible_timer = 120

        if self.lives <= 0:
            self.alive = False
            play_sfx("life_lost")
            shake.trigger(12, 30)
        else:
            play_sfx("life_lost")
            shake.trigger(8, 20)
            self.speed = max(0, self.speed - 4)
        return True
