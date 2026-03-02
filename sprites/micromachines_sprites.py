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

    def _make_car_v2(self):
        """V2+ car with underglow, detail shading, windshield glint, exhaust glow."""
        surf = pygame.Surface((24, 32), pygame.SRCALPHA)
        # Underglow ellipse
        pygame.draw.ellipse(surf, (*self.color_accent, 35), (2, 6, 20, 24))
        # Body
        pygame.draw.rect(surf, self.color_main, (4, 2, 16, 28), border_radius=4)
        # Side shading
        side_dark = tuple(max(0, c - 40) for c in self.color_main)
        pygame.draw.rect(surf, side_dark, (4, 2, 3, 28), border_radius=2)
        pygame.draw.rect(surf, side_dark, (17, 2, 3, 28), border_radius=2)
        # Windshield with glint
        pygame.draw.rect(surf, (*self.color_accent, 160), (6, 3, 12, 10), border_radius=2)
        pygame.draw.line(surf, (255, 255, 255), (7, 4), (16, 4), 1)
        # Rear exhaust glow
        pygame.draw.rect(surf, (255, 120, 40, 120), (6, 26, 12, 4))
        pygame.draw.rect(surf, (255, 200, 100, 80), (8, 27, 8, 2))
        # Wheels (with highlights)
        for wx in [1, 20]:
            pygame.draw.rect(surf, (40, 40, 40), (wx, 5, 3, 7))
            pygame.draw.rect(surf, (40, 40, 40), (wx, 21, 3, 7))
            pygame.draw.rect(surf, (70, 70, 70), (wx, 6, 3, 2))
            pygame.draw.rect(surf, (70, 70, 70), (wx, 22, 3, 2))
        return surf

    def _make_car_v3(self):
        """V3 car: 3-tone body, holographic windshield, neon wheel rims, power stripe."""
        surf = pygame.Surface((28, 36), pygame.SRCALPHA)
        # 3-layer underglow
        for ew, eh, a in [(24, 28, 20), (20, 24, 35), (16, 20, 50)]:
            pygame.draw.ellipse(surf, (*self.color_accent, a),
                                (14 - ew // 2, 8, ew, eh))
        # Body — 3-tone shading
        dark = tuple(max(0, c - 50) for c in self.color_main)
        light = tuple(min(255, c + 30) for c in self.color_main)
        pygame.draw.rect(surf, self.color_main, (5, 2, 18, 32), border_radius=4)
        # Left dark panel
        pygame.draw.rect(surf, dark, (5, 2, 4, 32), border_radius=2)
        # Right dark panel
        pygame.draw.rect(surf, dark, (19, 2, 4, 32), border_radius=2)
        # Center highlight
        pygame.draw.rect(surf, light, (12, 4, 4, 28))
        # Holographic cyan windshield with scan line
        pygame.draw.rect(surf, (0, 220, 200, 180), (7, 3, 14, 12), border_radius=2)
        # Moving scan line effect (static for sprite — baked mid-position)
        pygame.draw.line(surf, (0, 255, 255), (8, 8), (20, 8), 1)
        pygame.draw.line(surf, (255, 255, 255), (8, 4), (18, 4), 1)
        # Neon wheel rims
        for wx in [2, 23]:
            pygame.draw.rect(surf, (30, 30, 35), (wx, 6, 3, 8))
            pygame.draw.rect(surf, (30, 30, 35), (wx, 24, 3, 8))
            # Neon rim lines
            pygame.draw.rect(surf, self.color_accent, (wx, 6, 3, 1))
            pygame.draw.rect(surf, self.color_accent, (wx, 13, 3, 1))
            pygame.draw.rect(surf, self.color_accent, (wx, 24, 3, 1))
            pygame.draw.rect(surf, self.color_accent, (wx, 31, 3, 1))
        # Central power stripe
        pygame.draw.line(surf, self.color_accent, (14, 4), (14, 30), 1)
        # Rear exhaust (3-layer)
        pygame.draw.rect(surf, (255, 100, 30, 140), (7, 30, 14, 4))
        pygame.draw.rect(surf, (255, 180, 80, 100), (9, 31, 10, 2))
        pygame.draw.rect(surf, (255, 220, 140, 60), (11, 31, 6, 1))
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

        # Steering
        turn_speed = 0.065
        turning = False
        if self._any_key(keys, self.key_left):
            self.angle -= turn_speed
            turning = True
        if self._any_key(keys, self.key_right):
            self.angle += turn_speed
            turning = True

        # Accel/brake
        if self._any_key(keys, self.key_up):
            self.speed = min(self.speed + 0.26, 8)
            self.heat += 0.8
        if self._any_key(keys, self.key_down):
            self.speed = max(self.speed - 0.4, -2.6)

        # Drift builds heat when turning at speed
        if turning and self.speed > 2:
            self.heat += 1.5

        # Boost
        if self._any_key(keys, self.key_boost) and self.heat > 50:
            self.speed += 4
            self.heat = 0
            from core.sound import play_sfx
            play_sfx("boost")

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
        # Tiers 1-2: auto-attract toward nearest player
        if self.tier <= 2 and players:
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
            if best_p and best_dist < 250:
                dx = best_p.rect.centerx - self.rect.centerx
                dy = best_p.rect.centery - self.rect.centery
                dist = max(1, best_dist)
                self.rect.x += int(dx / dist * 4)
                self.rect.y += int(dy / dist * 4)
        self._draw()
        self.rect.y += scroll_speed
        if self.rect.top > SCREEN_HEIGHT + 30:
            self.kill()
