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
        # Draw ramp shape (brighter orange/yellow)
        pts = [(0, 30), (50, 30), (50, 5), (10, 25)]
        pygame.draw.polygon(self.image, (220, 170, 40), pts)
        pygame.draw.polygon(self.image, SOLAR_YELLOW, pts, 2)
        # Chevron arrows (launch-pad look)
        for i in range(3):
            ax = 18 + i * 10
            ay = 26 - i * 6
            pygame.draw.line(self.image, NEON_CYAN, (ax, ay + 4), (ax + 5, ay), 2)
            pygame.draw.line(self.image, NEON_CYAN, (ax + 5, ay), (ax + 10, ay + 4), 2)
        # Top edge glow
        pygame.draw.line(self.image, (255, 255, 200), (12, 24), (48, 6), 1)
        self.rect = self.image.get_rect(midleft=(x, lane_y + 20))
        self.launch_power = -12

    def update(self, scroll_speed):
        self.rect.x -= scroll_speed
        if self.rect.right < -50:
            self.kill()


class Barrier(pygame.sprite.Sprite):
    """Static barrier obstacle in a lane."""
    def __init__(self, x, lane_y, lane_h=55, tier=1):
        super().__init__()
        w = random.choice([30, 40, 50])
        h = lane_h - 10
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        if tier >= 3:
            # V3: near-black base, thick cyan + thin magenta diagonals, corner glow, double neon border
            pygame.draw.rect(self.image, (10, 10, 18), (0, 0, w, h))
            for sy in range(-h, h + w, 8):
                pygame.draw.line(self.image, NEON_CYAN, (0, sy), (w, sy + w), 3)
                pygame.draw.line(self.image, (*NEON_MAGENTA[:3], 120), (0, sy + 4), (w, sy + w + 4), 1)
            # Double neon border
            pygame.draw.rect(self.image, NEON_CYAN, (0, 0, w, h), 2)
            pygame.draw.rect(self.image, (*NEON_MAGENTA[:3], 100), (2, 2, w - 4, h - 4), 1)
            # Corner glow dots (brighter)
            for gx, gy in [(3, 3), (w - 4, 3), (3, h - 4), (w - 4, h - 4)]:
                pygame.draw.circle(self.image, (200, 255, 255), (gx, gy), 3)
                pygame.draw.circle(self.image, (255, 255, 255, 180), (gx, gy), 1)
        elif tier >= 2:
            # V2+: Neon cyan diagonal stripes instead of yellow
            pygame.draw.rect(self.image, (180, 50, 50), (0, 0, w, h))
            for sy in range(-h, h + w, 6):
                pygame.draw.line(self.image, NEON_CYAN, (0, sy), (w, sy + w), 2)
            pygame.draw.rect(self.image, NEON_CYAN, (0, 0, w, h), 2)
            # Corner glow dots
            for gx, gy in [(2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)]:
                pygame.draw.circle(self.image, (200, 255, 255, 180), (gx, gy), 2)
        else:
            pygame.draw.rect(self.image, (200, 60, 40), (0, 0, w, h))
            pygame.draw.rect(self.image, NEON_MAGENTA, (0, 0, w, h), 2)
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
    def __init__(self, x, lane_y, lane_h=55, hazard=False):
        super().__init__()
        self.pulse = random.randint(0, 60)
        self.hazard = hazard
        self.image = pygame.Surface((22, 22), pygame.SRCALPHA)
        self._draw()
        self.rect = self.image.get_rect(center=(x, lane_y + lane_h // 2))

    def _draw(self):
        self.image.fill((0, 0, 0, 0))
        p = 0.75 + 0.25 * math.sin(self.pulse * 0.12)
        if self.hazard:
            pulse_r = int(10 + 1.5 * math.sin(self.pulse * 0.15))
            pygame.draw.circle(self.image, (255, 140, 0, int(50 * p)), (11, 11), pulse_r)
            pygame.draw.circle(self.image, (255, 140, 0), (11, 11), 7)
            pygame.draw.circle(self.image, (255, 200, 80), (11, 11), 4)
            pygame.draw.circle(self.image, (255, 140, 0, int(120 * p)), (11, 11), 10, 2)
            return
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
    def __init__(self, x, lane_y, kind=None, lane_h=55, tier=1):
        super().__init__()
        self.kind = kind or random.choice(POWERUP_ALL)
        self.color = POWERUP_COLORS[self.kind]
        self.pulse = random.randint(0, 60)
        self.tier = tier
        self.image = pygame.Surface((30, 30), pygame.SRCALPHA)
        self._draw()
        self.rect = self.image.get_rect(center=(x, lane_y + lane_h // 2))

    def _draw(self):
        self.image.fill((0, 0, 0, 0))
        p = 0.65 + 0.35 * math.sin(self.pulse * 0.1)
        cx, cy = 15, 15
        # Rainbow shimmer ring
        rainbow_t = self.pulse * 0.03
        rh = int(127 + 127 * math.sin(rainbow_t))
        rg = int(127 + 127 * math.sin(rainbow_t + 2.09))
        rb = int(127 + 127 * math.sin(rainbow_t + 4.19))
        pygame.draw.circle(self.image, (rh, rg, rb, int(30 * p)), (cx, cy), 14)
        # Core glow
        pygame.draw.circle(self.image, (*self.color, int(70 * p)), (cx, cy), 12)
        pygame.draw.circle(self.image, self.color, (cx, cy), 10, 2)
        pygame.draw.circle(self.image, (*self.color, 200), (cx, cy), 7)
        # 4 sparkle rays
        for i in range(4):
            a = self.pulse * 0.12 + i * math.pi / 2
            x1 = cx + int(math.cos(a) * 8)
            y1 = cy + int(math.sin(a) * 8)
            x2 = cx + int(math.cos(a) * 13)
            y2 = cy + int(math.sin(a) * 13)
            pygame.draw.line(self.image, (*self.color, int(90 * p)), (x1, y1), (x2, y2), 1)
        # Bright center
        pygame.draw.circle(self.image, (255, 255, 255, int(60 * p)), (cx, cy), 3)
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
                self.rect.y += int(dy / dist * 3)
        self._draw()
        self.rect.x -= scroll_speed
        if self.rect.right < -40:
            self.kill()


class ExcitebikePlayer(pygame.sprite.Sprite):
    """Side-scrolling bike player for Excitebike mode."""

    def __init__(self, particles, player_num=1, lane=1, solo=False, diff="normal", tier=1):
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

        if tier >= 3:
            self.image = self._make_bike_v3()
        elif tier >= 2:
            self.image = self._make_bike_v2()
        else:
            self.image = self._make_bike()
        self.lane = lane  # 0, 1, 2
        self.target_lane = lane
        self.lane_transition = 0.0

        from backgrounds.excitebike_bg import ExcitebikeBg
        self.lane_ys = ExcitebikeBg.LANE_Y
        self.lane_h = ExcitebikeBg.LANE_HEIGHT

        self.rect = self.image.get_rect(
            center=(150, self.lane_ys[self.lane] + self.lane_h // 2))

        self.speed = 4.0
        self.max_speed = 16
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
        self.multishot = False
        self.multishot_timer = 0
        self.rockets = False
        self.rockets_timer = 0
        self.rocket_fire_cd = 0
        self.orbit8 = False
        self.orbit8_timer = 0
        self._orbit8_spawn_pending = False
        self.name = f"P{player_num}"
        self.fire_cooldown = 0
        self.last_emit = 0

        # Tiered boost system
        self.boost_timer = 0
        self.boost_power = 0
        self.boost_cooldown = 0

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
        # Rider torso (thin rect connecting body to helmet)
        pygame.draw.rect(surf, (60, 60, 70), (18, 3, 5, 4))
        # Helmet (small dark polygon instead of big flesh circle)
        pygame.draw.polygon(surf, (40, 40, 50), [(18, 4), (23, 4), (22, 1), (19, 1)])
        pygame.draw.line(surf, (80, 80, 90), (19, 1), (22, 1), 1)  # visor glint
        # Exhaust
        pygame.draw.rect(surf, (150, 80, 30), (2, 10, 6, 4))
        return surf

    def _make_bike_v2(self):
        """V2+ bike with underglow, detail shading, exhaust glow."""
        surf = pygame.Surface((48, 28), pygame.SRCALPHA)
        # Underglow
        pygame.draw.ellipse(surf, (*self.color_accent, 35), (4, 16, 40, 12))
        # Wheels (larger, with rim highlight)
        for wx, wy in [(10, 20), (38, 20)]:
            pygame.draw.circle(surf, (50, 50, 50), (wx, wy), 7)
            pygame.draw.circle(surf, (90, 90, 90), (wx, wy), 5)
            pygame.draw.circle(surf, (120, 120, 120), (wx, wy), 3)
        # Body with shading
        pygame.draw.rect(surf, self.color_main, (8, 6, 32, 12))
        # Darker side stripe
        side_dark = tuple(max(0, c - 40) for c in self.color_main)
        pygame.draw.rect(surf, side_dark, (8, 14, 32, 4))
        # Windshield with glint
        pygame.draw.polygon(surf, (*self.color_accent, 180), [(36, 4), (44, 8), (36, 12)])
        pygame.draw.line(surf, (255, 255, 255), (37, 5), (42, 7), 1)
        # Rider torso
        pygame.draw.rect(surf, (50, 50, 60), (19, 3, 6, 5))
        # Helmet (rounded rect shape, dark)
        pygame.draw.rect(surf, (50, 50, 60), (19, 0, 6, 5))
        pygame.draw.rect(surf, (70, 70, 80), (19, 0, 6, 5), 1)  # helmet edge
        # Visor stripe
        pygame.draw.line(surf, (60, 200, 255), (19, 2), (25, 2), 1)
        # Exhaust glow
        pygame.draw.ellipse(surf, (255, 120, 40, 100), (0, 10, 10, 6))
        pygame.draw.ellipse(surf, (255, 200, 100, 60), (2, 11, 6, 4))
        return surf

    def _make_bike_v3(self):
        """V3 bike: glossy chassis, fork detail, wheel tread, visor glint."""
        surf = pygame.Surface((50, 30), pygame.SRCALPHA)
        # Underglow (brighter)
        pygame.draw.ellipse(surf, (*self.color_accent, 50), (4, 16, 42, 14))
        # Wheels with tread marks
        for wx, wy in [(10, 22), (40, 22)]:
            pygame.draw.circle(surf, (40, 40, 45), (wx, wy), 8)
            pygame.draw.circle(surf, (80, 80, 85), (wx, wy), 6)
            # Neon rim
            pygame.draw.circle(surf, (*self.color_accent, 150), (wx, wy), 8, 1)
            pygame.draw.circle(surf, (110, 110, 115), (wx, wy), 3)
            # Tread marks
            for ty in range(-5, 6, 3):
                pygame.draw.line(surf, (55, 55, 60), (wx - 1, wy + ty), (wx + 1, wy + ty))
        # Body with glossy highlight stripe
        pygame.draw.rect(surf, self.color_main, (8, 6, 34, 14))
        light = tuple(min(255, c + 40) for c in self.color_main)
        pygame.draw.rect(surf, light, (8, 8, 34, 3))  # highlight
        dark = tuple(max(0, c - 40) for c in self.color_main)
        pygame.draw.rect(surf, dark, (8, 16, 34, 4))
        # Front fork detail
        pygame.draw.line(surf, (100, 100, 110), (38, 14), (42, 20), 2)
        pygame.draw.line(surf, (100, 100, 110), (36, 14), (38, 8), 1)
        # Windshield with glint
        pygame.draw.polygon(surf, (*self.color_accent, 200), [(38, 4), (46, 8), (38, 12)])
        pygame.draw.line(surf, (255, 255, 255), (39, 5), (44, 7), 1)
        # Rider torso (connects body to helmet)
        pygame.draw.rect(surf, (45, 45, 55), (19, 3, 7, 5))
        # Helmet (wider, flatter polygon — looks like proper racing helmet)
        pygame.draw.polygon(surf, (45, 45, 55), [(18, 4), (26, 4), (25, 0), (19, 0)])
        pygame.draw.polygon(surf, (60, 60, 70), [(18, 4), (26, 4), (25, 0), (19, 0)], 1)  # edge
        # Visor (integrated into helmet face)
        pygame.draw.line(surf, (60, 200, 255), (19, 2), (25, 2), 2)
        # Visor glint
        pygame.draw.line(surf, (255, 255, 255), (20, 1), (23, 1), 1)
        # Exhaust glow (brighter for V3)
        pygame.draw.ellipse(surf, (255, 140, 50, 130), (0, 10, 12, 8))
        pygame.draw.ellipse(surf, (255, 220, 120, 80), (2, 11, 8, 6))
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
            return True, self.rect.right, self.rect.centery
        if self._any_key(keys, self.key_fire) and self.heat >= 40:
            self.heat -= 40
            self.fire_cooldown = 30
            from core.sound import play_sfx
            play_sfx("heat_bolt")
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

        # Smooth lane transition (snappy switch)
        if self.lane != self.target_lane:
            self.lane_transition += 0.12
            if self.lane_transition >= 1.0:
                self.lane = self.target_lane
                self.lane_transition = 0.0

        # Accel/brake
        if self._any_key(keys, self.key_accel):
            self.speed = min(self.speed + 0.4, 16)
            self.heat += 1.0
        if self._any_key(keys, self.key_brake):
            self.speed = max(self.speed - 0.65, 1.3)

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
        self.speed = max(self.speed - 0.07, 1.3)

        # Combo momentum: speed bonus from active combo, penalty on drop
        self.speed += self.combo.speed_bonus
        if self.combo.drop_penalty > 0:
            self.speed *= 0.85

        self.distance += self.speed * 0.01
        self.score += int(self.speed * 0.5 * self.score_mult * getattr(self, 'speed_mult_factor', 1.0))

        # Position
        current_y = self.lane_ys[self.lane] + self.lane_h // 2
        if self.lane != self.target_lane:
            target_y = self.lane_ys[self.target_lane] + self.lane_h // 2
            current_y = current_y + (target_y - current_y) * self.lane_transition

        if self.airborne:
            self.vel_y += 0.5
            current_y += self.vel_y
            # Airtime scoring: bonus points while mid-air
            self.score += int(2 * self.score_mult)
            if not hasattr(self, '_airtime_frames'):
                self._airtime_frames = 0
            self._airtime_frames += 1
            ground_y = self.lane_ys[self.lane] + self.lane_h // 2
            if current_y >= ground_y:
                current_y = ground_y
                self.airborne = False
                self.vel_y = 0
                # Landing bonus based on airtime
                if hasattr(self, '_airtime_frames') and self._airtime_frames > 10:
                    landing_bonus = self._airtime_frames * 5
                    self.score += int(landing_bonus * self.score_mult)
                    self._airtime_bonus = landing_bonus  # For mode to show floating text
                self._airtime_frames = 0

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
            from core.sound import play_sfx
            play_sfx("shield_hit")
            shake.trigger(4, 10)
            return False

        self.lives -= 1
        self.invincible_timer = 120

        if self.lives <= 0:
            self.alive = False
            from core.sound import play_sfx
            play_sfx("life_lost")
            shake.trigger(12, 30)
        else:
            from core.sound import play_sfx
            play_sfx("life_lost")
            shake.trigger(8, 20)
            self.speed = max(1.3, self.speed - 4)
        return True

    def launch(self, power=-12):
        if not self.airborne:
            self.airborne = True
            self.vel_y = power
