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

    def __init__(self, particles, player_num=1, solo=False, diff="normal", tier=1):
        super().__init__()
        self.player_num = player_num
        self.particles = particles
        self.is_ai = False
        self._ai_keys = {}
        self.score_mult = 1
        self.tier = tier

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
        self.max_speed = 12
        self.px = float(SCREEN_WIDTH // 2)
        self.py = float(SCREEN_HEIGHT // 2 + 100)
        self.heat = 0.0
        self.drift_angle = 0.0

        if tier >= 3:
            self.base_surf = self._make_car_v3()
        elif tier >= 2:
            self.base_surf = self._make_car_v2()
        else:
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
        self.multishot = False
        self.multishot_timer = 0
        self.rockets = False
        self.rockets_timer = 0
        self.rocket_fire_cd = 0
        self.orbit8 = False
        self.orbit8_timer = 0
        self._orbit8_spawn_pending = False
        self.ghost_mode = False
        self.ghost_timer = 0
        self.name = f"P{player_num}"
        self.fire_cooldown = 0
        self.vel_y = 0  # Compatibility

        # Tiered boost system
        self.boost_timer = 0
        self.boost_power = 0
        self.boost_cooldown = 0

        # Track constraint + spinout
        self.track_bg = None  # Set by mode in setup()
        self.spinout_timer = 0
        self.spinout_dir = 0  # +1 or -1

        from core.ui import ComboTracker
        self.combo = ComboTracker()

    def _make_car(self):
        surf = pygame.Surface((28, 40), pygame.SRCALPHA)
        # Body (slightly rounded)
        pygame.draw.rect(surf, self.color_main, (4, 3, 20, 34), border_radius=4)
        # Windshield
        pygame.draw.rect(surf, (*self.color_accent, 150), (7, 4, 14, 11), border_radius=3)
        # Rear section
        pygame.draw.rect(surf, (200, 80, 30), (7, 31, 14, 6))
        # Brake lights
        pygame.draw.rect(surf, (255, 50, 30), (8, 32, 4, 3))
        pygame.draw.rect(surf, (255, 50, 30), (16, 32, 4, 3))
        # Wheels with visible gaps
        for wx in [1, 24]:
            pygame.draw.rect(surf, (40, 40, 40), (wx, 7, 4, 9))
            pygame.draw.rect(surf, (40, 40, 40), (wx, 27, 4, 9))
            # Wheel gap (dark line between wheel and body)
            pygame.draw.rect(surf, (20, 20, 20), (wx, 16, 4, 1))
        return surf

    def _make_car_v2(self):
        """V2+ car with underglow, detail shading, windshield glint, exhaust glow."""
        surf = pygame.Surface((34, 46), pygame.SRCALPHA)
        # Underglow ellipse
        pygame.draw.ellipse(surf, (*self.color_accent, 35), (3, 9, 28, 34))
        # Body
        pygame.draw.rect(surf, self.color_main, (6, 3, 22, 40), border_radius=5)
        # Side shading
        side_dark = tuple(max(0, c - 40) for c in self.color_main)
        pygame.draw.rect(surf, side_dark, (6, 3, 4, 40), border_radius=2)
        pygame.draw.rect(surf, side_dark, (24, 3, 4, 40), border_radius=2)
        # Windshield with glint
        pygame.draw.rect(surf, (*self.color_accent, 160), (9, 4, 16, 14), border_radius=3)
        pygame.draw.line(surf, (255, 255, 255), (10, 6), (23, 6), 1)
        # Rear exhaust glow
        pygame.draw.rect(surf, (255, 120, 40, 120), (9, 37, 16, 6))
        pygame.draw.rect(surf, (255, 200, 100, 80), (11, 39, 12, 3))
        # Wheels (with highlights)
        for wx in [1, 29]:
            pygame.draw.rect(surf, (40, 40, 40), (wx, 7, 4, 10))
            pygame.draw.rect(surf, (40, 40, 40), (wx, 30, 4, 10))
            pygame.draw.rect(surf, (70, 70, 70), (wx, 9, 4, 3))
            pygame.draw.rect(surf, (70, 70, 70), (wx, 32, 4, 3))
        return surf

    def _make_car_v3(self):
        """V3 car: 3-tone body, holographic windshield, neon wheel rims, power stripe."""
        surf = pygame.Surface((40, 52), pygame.SRCALPHA)
        # 3-layer underglow
        for ew, eh, a in [(34, 40, 20), (29, 34, 35), (23, 29, 50)]:
            pygame.draw.ellipse(surf, (*self.color_accent, a),
                                (20 - ew // 2, 11, ew, eh))
        # Body — 3-tone shading
        dark = tuple(max(0, c - 50) for c in self.color_main)
        light = tuple(min(255, c + 30) for c in self.color_main)
        pygame.draw.rect(surf, self.color_main, (7, 3, 26, 46), border_radius=6)
        # Left dark panel
        pygame.draw.rect(surf, dark, (7, 3, 6, 46), border_radius=3)
        # Right dark panel
        pygame.draw.rect(surf, dark, (27, 3, 6, 46), border_radius=3)
        # Center highlight
        pygame.draw.rect(surf, light, (17, 6, 6, 40))
        # Holographic cyan windshield with scan line
        pygame.draw.rect(surf, (0, 220, 200, 180), (10, 4, 20, 17), border_radius=3)
        # Moving scan line effect (static for sprite — baked mid-position)
        pygame.draw.line(surf, (0, 255, 255), (11, 12), (29, 12), 1)
        pygame.draw.line(surf, (255, 255, 255), (11, 6), (26, 6), 1)
        # Neon wheel rims
        for wx in [3, 33]:
            pygame.draw.rect(surf, (30, 30, 35), (wx, 9, 4, 11))
            pygame.draw.rect(surf, (30, 30, 35), (wx, 35, 4, 11))
            # Neon rim lines
            pygame.draw.rect(surf, self.color_accent, (wx, 9, 4, 1))
            pygame.draw.rect(surf, self.color_accent, (wx, 19, 4, 1))
            pygame.draw.rect(surf, self.color_accent, (wx, 35, 4, 1))
            pygame.draw.rect(surf, self.color_accent, (wx, 45, 4, 1))
        # Central power stripe
        pygame.draw.line(surf, self.color_accent, (20, 6), (20, 43), 1)
        # Rear exhaust (3-layer)
        pygame.draw.rect(surf, (255, 100, 30, 140), (10, 43, 20, 6))
        pygame.draw.rect(surf, (255, 180, 80, 100), (13, 45, 14, 3))
        pygame.draw.rect(surf, (255, 220, 140, 60), (16, 46, 8, 2))
        return surf

    def _any_key(self, keys, key_list):
        if self.is_ai:
            for name, grp in self._key_groups.items():
                if grp is key_list:
                    return self._ai_keys.get(name, False)
            return False
        return any(keys[k] for k in key_list)

    def try_fire_heat_bolt(self, keys, auto_fire=False):
        if not self.alive or self.fire_cooldown > 0:
            return False, 0, 0
        if auto_fire:
            self.fire_cooldown = 12
            return True, self.rect.centerx, self.rect.centery
        if self._any_key(keys, self.key_fire) and self.heat >= 40:
            self.heat -= 40
            self.fire_cooldown = 30
            from core.sound import play_sfx
            play_sfx("heat_bolt")
            return True, self.rect.centerx, self.rect.centery
        return False, 0, 0

    def update(self, keys, scroll_speed=0):
        if not self.alive:
            return

        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1

        # --- Spinout handling (cannot steer during spinout) ---
        in_spinout = self.spinout_timer > 0
        if in_spinout:
            self.spinout_timer -= 1
            self.angle += 0.15 * self.spinout_dir
            self.speed *= 0.95

        # Steering (disabled during spinout)
        turn_speed = 0.065
        turning = False
        if not in_spinout:
            if self._any_key(keys, self.key_left):
                self.angle -= turn_speed
                turning = True
            if self._any_key(keys, self.key_right):
                self.angle += turn_speed
                turning = True

        # Accel/brake
        if self._any_key(keys, self.key_up):
            self.speed = min(self.speed + 0.3, 12)
            self.heat += 0.8
        if self._any_key(keys, self.key_down):
            self.speed = max(self.speed - 0.4, -2.6)

        # Drift builds heat when turning at speed
        if turning and self.speed > 2:
            self.heat += 1.5
            # Drift enhancement: more slide at high speed
            if abs(self.speed) > 5:
                self.heat += 0.5

        # Tiered boost system
        boost_pressed = self._any_key(keys, self.key_boost)
        if boost_pressed and self.boost_cooldown <= 0 and self.boost_timer <= 0:
            from core.sound import play_sfx as _play_sfx
            if self.heat >= 100:
                # Tier 3: Ghost Surge
                self.heat = 0
                self.boost_timer = 90
                self.boost_power = 10
                self.ghost_mode = True
                self.ghost_timer = 90
                self.invincible_timer = max(self.invincible_timer, 90)
                self.boost_cooldown = 18
                _play_sfx("boost")
            elif self.heat >= 60:
                # Tier 2: Power Boost
                self.heat -= 60
                self.boost_timer = 54
                self.boost_power = 6
                self.invincible_timer = max(self.invincible_timer, 18)
                self.boost_cooldown = 18
                _play_sfx("boost")
            elif self.heat >= 30:
                # Tier 1: Quick Boost
                self.heat -= 30
                self.boost_timer = 36
                self.boost_power = 3
                self.boost_cooldown = 18
                _play_sfx("boost")

        if self.boost_timer > 0:
            self.speed = min(self.speed + self.boost_power * 0.15, self.max_speed + self.boost_power)
            self.boost_timer -= 1
        if self.boost_cooldown > 0:
            self.boost_cooldown -= 1

        if self.ghost_mode:
            self.ghost_timer -= 1
            if self.ghost_timer <= 0:
                self.ghost_mode = False

        self.heat = max(0, self.heat - 0.3)
        # Drift enhancement: less friction when turning at high speed
        friction = 0.96 if (turning and abs(self.speed) > 5) else 0.98
        self.speed *= friction

        # Combo momentum: speed bonus from active combo, penalty on drop
        self.speed += self.combo.speed_bonus
        if self.combo.drop_penalty > 0:
            self.speed *= 0.85

        # Move
        self.px += math.cos(self.angle) * self.speed
        self.py += math.sin(self.angle) * self.speed

        # --- Track wall constraint ---
        if self.track_bg is not None:
            world_y = self.py + self.track_bg.scroll_offset_value
            bounds = self.track_bg.get_track_bounds_at_world_y(world_y)
            if bounds is not None:
                left, _center, right = bounds
                wall_margin = 10
                if self.px < left + wall_margin:
                    self.px = left + wall_margin
                    # Wall bounce
                    self.speed *= -0.3
                    self.angle = math.pi - self.angle  # Reflect horizontally
                    self.heat += 15
                elif self.px > right - wall_margin:
                    self.px = right - wall_margin
                    self.speed *= -0.3
                    self.angle = math.pi - self.angle
                    self.heat += 15

        # Keep on screen (fallback, should rarely trigger with track constraint)
        self.px = max(20, min(SCREEN_WIDTH - 20, self.px))
        self.py = max(20, min(SCREEN_HEIGHT - 20, self.py))

        self.distance += abs(self.speed) * 0.01
        self.score += int(abs(self.speed) * 0.3 * self.score_mult * getattr(self, 'speed_mult_factor', 1.0))

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
            self.speed = max(self.speed, 10)
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

        # Tire smoke when drifting
        if turning and self.speed > 3:
            # V2+: more smoke particles, larger
            count = 3 if self.tier >= 2 else 1
            size = 3 if self.tier >= 2 else 2
            for _ in range(count):
                self.particles.emit(
                    self.rect.centerx, self.rect.centery,
                    (150, 150, 150),
                    [random.uniform(-1, 1), random.uniform(-1, 1)], 15, size)

        # V2+: Exhaust particles
        if self.tier >= 2 and abs(self.speed) > 1:
            # Emit 2 exhaust particles from rear
            rear_x = self.rect.centerx - int(math.cos(self.angle) * 12)
            rear_y = self.rect.centery - int(math.sin(self.angle) * 12)
            for _ in range(2):
                ec = random.choice([(255, 120, 40), (200, 100, 30), (150, 150, 150)])
                evx = -math.cos(self.angle) * random.uniform(0.5, 1.5) + random.uniform(-0.3, 0.3)
                evy = -math.sin(self.angle) * random.uniform(0.5, 1.5) + random.uniform(-0.3, 0.3)
                self.particles.emit(rear_x, rear_y, ec, [evx, evy], 20, 2)

        self.combo.update()

    def take_hit(self, shake):
        if self.invincible_timer > 0 or self.ghost_mode or self.phase:
            return False
        if self.shield:
            self.shield = False
            self.shield_timer = 0
            self.invincible_timer = 30
            from core.sound import play_sfx
            play_sfx("shield_hit")
            shake.trigger(4, 10)
            return False

        self.lives -= 1
        self.invincible_timer = 120
        self.speed = 0

        if self.lives <= 0:
            self.alive = False
            from core.sound import play_sfx
            play_sfx("life_lost")
            shake.trigger(12, 30)
        else:
            from core.sound import play_sfx
            play_sfx("life_lost")
            shake.trigger(8, 20)
        return True


class OilSlickHazard(pygame.sprite.Sprite):
    """Oil slick on track that spins the player."""
    def __init__(self, x, y, tier=1):
        super().__init__()
        self.w, self.h = random.randint(30, 50), random.randint(20, 35)
        self.tier = tier
        self._shimmer_tick = 0
        self.image = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        if tier >= 3:
            self._draw_v3_shimmer()
        elif tier >= 2:
            # V2+: Rainbow iridescence — 3 overlapping ellipses with shifted hues
            pygame.draw.ellipse(self.image, (20, 20, 30, 140), (0, 0, self.w, self.h))
            pygame.draw.ellipse(self.image, (60, 20, 80, 70), (2, 2, self.w - 4, self.h - 4))
            pygame.draw.ellipse(self.image, (20, 60, 60, 50), (6, 4, self.w - 12, self.h - 8))
            pygame.draw.ellipse(self.image, (80, 40, 120, 40), (8, 6, self.w - 16, self.h - 12))
        else:
            pygame.draw.ellipse(self.image, (20, 20, 30, 160), (0, 0, self.w, self.h))
            pygame.draw.ellipse(self.image, (40, 30, 50, 100), (4, 4, self.w - 8, self.h - 8))
        self.rect = self.image.get_rect(center=(x, y))

    def _draw_v3_shimmer(self):
        """V3: animated hue-shifted iridescent ellipses."""
        w, h = self.w, self.h
        self.image.fill((0, 0, 0, 0))
        t = self._shimmer_tick * 0.15
        # Hue-shifting ellipses
        for i in range(4):
            inset = i * 3
            hue_shift = t + i * 1.2
            r = int(127 + 80 * math.sin(hue_shift))
            g = int(80 + 60 * math.sin(hue_shift + 2.1))
            b = int(100 + 80 * math.sin(hue_shift + 4.2))
            a = max(30, 120 - i * 25)
            pygame.draw.ellipse(self.image, (r, g, b, a),
                                (inset, inset, w - inset * 2, h - inset * 2))
        # Bright center highlight
        pygame.draw.ellipse(self.image, (200, 200, 255, 40),
                            (w // 3, h // 3, w // 3, h // 3))

    def update(self, scroll_speed):
        self._shimmer_tick += 1
        # V3: redraw shimmer every 8 frames
        if self.tier >= 3 and self._shimmer_tick % 8 == 0:
            self._draw_v3_shimmer()
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
    """AI opponent car in top-down view — follows track center."""
    def __init__(self, x, y, direction='same', track_bg=None):
        super().__init__()
        self.direction = direction  # 'same' = slower ahead, 'oncoming' = head-on
        self.track_bg = track_bg
        self.own_speed = random.uniform(1.0, 3.0)
        self.car_angle = 0.0  # facing angle for sprite rotation
        self.lateral_wander = random.uniform(-15, 15)
        self.wander_phase = random.uniform(0, math.pi * 2)

        # Build base sprite
        self.color = random.choice([(200, 80, 80), (80, 200, 80), (200, 200, 80), (80, 80, 200)])
        self.base_surf = pygame.Surface((16, 22), pygame.SRCALPHA)
        pygame.draw.rect(self.base_surf, self.color, (2, 1, 12, 20), border_radius=3)
        pygame.draw.rect(self.base_surf, (50, 50, 50), (0, 4, 3, 5))
        pygame.draw.rect(self.base_surf, (50, 50, 50), (13, 4, 3, 5))
        pygame.draw.rect(self.base_surf, (50, 50, 50), (0, 14, 3, 5))
        pygame.draw.rect(self.base_surf, (50, 50, 50), (13, 14, 3, 5))
        self.image = self.base_surf.copy()
        self.rect = self.image.get_rect(center=(x, y))

        # Track world_y for track queries
        self.world_y = y + (track_bg.scroll_offset_value if track_bg else 0)

    def update(self, scroll_speed):
        # Advance world position
        if self.direction == 'same':
            self.world_y += scroll_speed - self.own_speed
        else:
            self.world_y += scroll_speed + self.own_speed

        # Steer toward track center with wander
        if self.track_bg:
            center = self.track_bg.get_track_center_ahead(self.world_y, 50)
            self.wander_phase += 0.02
            target_x = center + self.lateral_wander * math.sin(self.wander_phase)
            # Steer laterally
            dx = target_x - self.rect.centerx
            steer = max(-2.0, min(2.0, dx * 0.08))
            self.rect.x += int(steer)
            # Compute facing angle for rotation
            self.car_angle = math.atan2(scroll_speed - self.own_speed, steer) if self.direction == 'same' else math.atan2(-(scroll_speed + self.own_speed), steer)

        # Update screen position from world_y
        screen_y = self.world_y - (self.track_bg.scroll_offset_value if self.track_bg else 0)
        self.rect.centery = int(screen_y)

        # Rotate sprite to face direction
        if self.direction == 'oncoming':
            deg = 180  # Facing player (down)
        else:
            deg = 0  # Facing up (same direction)
        # Add slight steering rotation
        if self.track_bg:
            deg += max(-15, min(15, -self.car_angle * 10))
        self.image = pygame.transform.rotate(self.base_surf, deg)
        self.rect = self.image.get_rect(center=self.rect.center)

        if self.rect.top > SCREEN_HEIGHT + 50 or self.rect.bottom < -80:
            self.kill()


class MicroCoin(pygame.sprite.Sprite):
    def __init__(self, x, y, hazard=False):
        super().__init__()
        self.pulse = random.randint(0, 60)
        self.hazard = hazard
        self.image = pygame.Surface((18, 18), pygame.SRCALPHA)
        self._draw()
        self.rect = self.image.get_rect(center=(x, y))

    def _draw(self):
        self.image.fill((0, 0, 0, 0))
        p = 0.75 + 0.25 * math.sin(self.pulse * 0.12)
        if self.hazard:
            pulse_r = int(8 + 1.5 * math.sin(self.pulse * 0.15))
            pygame.draw.circle(self.image, (255, 140, 0, int(50 * p)), (9, 9), pulse_r)
            pygame.draw.circle(self.image, (255, 140, 0), (9, 9), 6)
            pygame.draw.circle(self.image, (255, 200, 80), (9, 9), 3)
            pygame.draw.circle(self.image, (255, 140, 0, int(120 * p)), (9, 9), 8, 2)
            return
        pygame.draw.circle(self.image, (*COIN_GOLD, int(60 * p)), (9, 9), 8)
        pygame.draw.circle(self.image, COIN_GOLD, (9, 9), 6)

    def update(self, scroll_speed, players=None):
        self.pulse += 1
        self._draw()
        # Baseline magnetism — coins always pull toward nearest player
        if players:
            best_dist = 999999
            best_p = None
            for p in players:
                if not p.alive:
                    continue
                dx = p.rect.centerx - self.rect.centerx
                dy = p.rect.centery - self.rect.centery
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < best_dist:
                    best_dist = dist
                    best_p = p
            if best_p:
                dx = best_p.rect.centerx - self.rect.centerx
                dy = best_p.rect.centery - self.rect.centery
                dist = max(1, best_dist)
                if getattr(best_p, 'magnet', False) and dist < 450:
                    self.rect.x += int(dx / dist * 15)
                    self.rect.y += int(dy / dist * 15)
                elif dist < 300:
                    self.rect.x += int(dx / dist * 5)
                    self.rect.y += int(dy / dist * 5)
        self.rect.y += scroll_speed
        if self.rect.top > SCREEN_HEIGHT + 30:
            self.kill()


class MicroPowerUp(pygame.sprite.Sprite):
    def __init__(self, x, y, kind=None, tier=1):
        super().__init__()
        self.kind = kind or random.choice(POWERUP_ALL)
        self.color = POWERUP_COLORS[self.kind]
        self.pulse = random.randint(0, 60)
        self.tier = tier
        self.image = pygame.Surface((24, 24), pygame.SRCALPHA)
        self._draw()
        self.rect = self.image.get_rect(center=(x, y))

    def _draw(self):
        self.image.fill((0, 0, 0, 0))
        p = 0.65 + 0.35 * math.sin(self.pulse * 0.1)
        cx, cy = 12, 12
        # Rainbow shimmer ring
        rainbow_t = self.pulse * 0.03
        rh = int(127 + 127 * math.sin(rainbow_t))
        rg = int(127 + 127 * math.sin(rainbow_t + 2.09))
        rb = int(127 + 127 * math.sin(rainbow_t + 4.19))
        pygame.draw.circle(self.image, (rh, rg, rb, int(25 * p)), (cx, cy), 11)
        # Core glow
        pygame.draw.circle(self.image, (*self.color, int(65 * p)), (cx, cy), 9)
        pygame.draw.circle(self.image, self.color, (cx, cy), 8, 2)
        pygame.draw.circle(self.image, (*self.color, 190), (cx, cy), 6)
        # 4 sparkle rays
        for i in range(4):
            a = self.pulse * 0.12 + i * math.pi / 2
            x1 = cx + int(math.cos(a) * 6)
            y1 = cy + int(math.sin(a) * 6)
            x2 = cx + int(math.cos(a) * 10)
            y2 = cy + int(math.sin(a) * 10)
            pygame.draw.line(self.image, (*self.color, int(80 * p)), (x1, y1), (x2, y2), 1)
        # Bright center
        pygame.draw.circle(self.image, (255, 255, 255, int(50 * p)), (cx, cy), 2)
        import core.fonts as _fonts
        label = _fonts.FONT_POWERUP.render(POWERUP_LABELS[self.kind], True, WHITE)
        self.image.blit(label, (cx - label.get_width() // 2, cy - label.get_height() // 2))

    def update(self, scroll_speed, players=None):
        self.pulse += 1
        # Powerups always aggressively attract toward nearest player
        if players:
            best_dist = 999999
            best_p = None
            for p in players:
                if not p.alive:
                    continue
                dx = p.rect.centerx - self.rect.centerx
                dy = p.rect.centery - self.rect.centery
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < best_dist:
                    best_dist = dist
                    best_p = p
            if best_p and best_dist < 450:
                dx = best_p.rect.centerx - self.rect.centerx
                dy = best_p.rect.centery - self.rect.centery
                dist = max(1, best_dist)
                self.rect.x += int(dx / dist * 12)
                self.rect.y += int(dy / dist * 12)
        self._draw()
        self.rect.y += scroll_speed
        if self.rect.top > SCREEN_HEIGHT + 30:
            self.kill()
