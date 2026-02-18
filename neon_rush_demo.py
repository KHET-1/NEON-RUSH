import pygame
import sys
import random
import math
import json
import os
import array

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

# === Constants ===
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
NEON_CYAN = (0, 255, 255)
NEON_MAGENTA = (255, 0, 255)
DESERT_ORANGE = (255, 102, 0)
SAND_YELLOW = (255, 204, 0)
SOLAR_YELLOW = (255, 255, 0)
SOLAR_WHITE = (255, 255, 200)
DARK_PANEL = (0, 0, 0, 180)
SHIELD_BLUE = (50, 150, 255)
MAGNET_PURPLE = (200, 50, 255)
SLOWMO_GREEN = (50, 255, 150)
COIN_GOLD = (255, 215, 0)

ROAD_LEFT = 100
ROAD_RIGHT = SCREEN_WIDTH - 100
ROAD_WIDTH = ROAD_RIGHT - ROAD_LEFT
ROAD_CENTER = (ROAD_LEFT + ROAD_RIGHT) // 2

PARTICLE_CAP = 800
GRAVITY = 0.6
MAX_LIVES = 3

STATE_TITLE = "title"
STATE_PLAY = "play"
STATE_PAUSED = "paused"
STATE_GAMEOVER = "gameover"
STATE_HIGHSCORE = "highscore"

HIGHSCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscores.json")


# === Sound Generation ===
def generate_tone(frequency, duration_ms, volume=0.3, wave="square"):
    sample_rate = 44100
    n_samples = int(sample_rate * duration_ms / 1000)
    buf = array.array("h", [0] * n_samples)
    max_amp = int(32767 * volume)
    fade_start = int(n_samples * 0.8)
    for i in range(n_samples):
        t = i / sample_rate
        if wave == "square":
            val = max_amp if math.sin(2 * math.pi * frequency * t) > 0 else -max_amp
        elif wave == "sine":
            val = int(max_amp * math.sin(2 * math.pi * frequency * t))
        elif wave == "noise":
            val = random.randint(-max_amp, max_amp)
        else:
            val = 0
        if i > fade_start:
            val = int(val * (n_samples - i) / (n_samples - fade_start))
        buf[i] = max(-32768, min(32767, val))
    return pygame.mixer.Sound(buffer=buf)


def generate_sweep(freq_start, freq_end, duration_ms, volume=0.3):
    sample_rate = 44100
    n_samples = int(sample_rate * duration_ms / 1000)
    buf = array.array("h", [0] * n_samples)
    max_amp = int(32767 * volume)
    fade_start = int(n_samples * 0.7)
    for i in range(n_samples):
        t = i / sample_rate
        progress = i / n_samples
        freq = freq_start + (freq_end - freq_start) * progress
        val = int(max_amp * math.sin(2 * math.pi * freq * t))
        if i > fade_start:
            val = int(val * (n_samples - i) / (n_samples - fade_start))
        buf[i] = max(-32768, min(32767, val))
    return pygame.mixer.Sound(buffer=buf)


SFX = {
    "coin": generate_sweep(800, 1200, 80, 0.2),
    "crash": generate_tone(120, 300, 0.4, "noise"),
    "boost": generate_sweep(300, 800, 200, 0.2),
    "powerup": generate_sweep(400, 1000, 150, 0.2),
    "shield_hit": generate_sweep(600, 200, 150, 0.25),
    "life_lost": generate_sweep(500, 100, 400, 0.3),
    "gameover": generate_sweep(400, 80, 800, 0.3),
    "select": generate_tone(600, 60, 0.15, "square"),
    "highscore": generate_sweep(500, 1500, 500, 0.2),
}


def make_engine_sound():
    sample_rate = 44100
    n_samples = int(sample_rate * 0.5)
    buf = array.array("h", [0] * n_samples)
    for i in range(n_samples):
        t = i / sample_rate
        val = int(
            1500 * math.sin(2 * math.pi * 80 * t)
            + 800 * math.sin(2 * math.pi * 160 * t)
            + 400 * math.sin(2 * math.pi * 240 * t)
        )
        buf[i] = max(-32768, min(32767, val))
    return pygame.mixer.Sound(buffer=buf)


engine_sound = make_engine_sound()
engine_channel = pygame.mixer.Channel(7)


# === Fonts ===
def load_font(name, size, bold=False):
    try:
        return pygame.font.SysFont(name, size, bold=bold)
    except Exception:
        return pygame.font.SysFont(None, size, bold=bold)


FONT_TITLE = load_font("freesans", 64, bold=True)
FONT_SUBTITLE = load_font("dejavusans", 28)
FONT_HUD = load_font("dejavusans", 20)
FONT_HUD_SM = load_font("dejavusans", 16)
FONT_HUD_LG = load_font("dejavusans", 36, bold=True)
FONT_SCORE_ENTRY = load_font("dejavusans", 48, bold=True)
FONT_POWERUP = load_font("dejavusans", 14, bold=True)


# === High Scores ===
def load_highscores():
    try:
        with open(HIGHSCORE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_highscores(scores):
    with open(HIGHSCORE_FILE, "w") as f:
        json.dump(scores[:5], f)


def is_highscore(score):
    scores = load_highscores()
    return len(scores) < 5 or score > min(s["score"] for s in scores)


# === Utilities ===
def draw_panel(surface, rect, color=(0, 0, 0, 180), border_color=NEON_CYAN, border=2):
    panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(panel, color, (0, 0, rect.w, rect.h))
    pygame.draw.rect(panel, border_color, (0, 0, rect.w, rect.h), border)
    surface.blit(panel, rect)


# === Screen Shake ===
class ScreenShake:
    def __init__(self):
        self.intensity = 0
        self.duration = 0
        self.offset_x = 0
        self.offset_y = 0

    def trigger(self, intensity, duration):
        self.intensity = intensity
        self.duration = duration

    def update(self):
        if self.duration > 0:
            self.offset_x = random.randint(-int(self.intensity), int(self.intensity))
            self.offset_y = random.randint(-int(self.intensity), int(self.intensity))
            self.duration -= 1
            self.intensity = max(1, self.intensity - 0.3)
        else:
            self.offset_x = 0
            self.offset_y = 0

    def get_offset(self):
        return (int(self.offset_x), int(self.offset_y))


# === Particles ===
class Particle(pygame.sprite.Sprite):
    def __init__(self, x, y, color, vel=None, life=60, size=3):
        super().__init__()
        self.image = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        col = color if len(color) == 4 else color + (128,)
        pygame.draw.circle(self.image, col, (size, size), size)
        self.rect = self.image.get_rect(center=(x, y))
        self.vel = vel or [random.uniform(-2, 2), random.uniform(-1, 1)]
        self.life = self.max_life = life

    def update(self):
        self.rect.x += self.vel[0]
        self.rect.y += self.vel[1]
        self.vel[0] *= 0.98
        self.vel[1] *= 0.98
        self.life -= 1
        alpha = int(255 * (self.life / self.max_life))
        self.image.set_alpha(alpha)
        if self.life <= 0 or not (-50 < self.rect.x < SCREEN_WIDTH + 50 and -50 < self.rect.y < SCREEN_HEIGHT + 50):
            self.kill()


class ParticleSystem:
    def __init__(self):
        self.particles = pygame.sprite.Group()

    def emit(self, x, y, color, vel=None, life=60, size=3):
        self.particles.add(Particle(x, y, color, vel, life, size))

    def burst(self, x, y, colors, count=10, speed=5, life=40, size=3):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            spd = random.uniform(speed * 0.5, speed)
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd
            c = random.choice(colors) if isinstance(colors, list) else colors
            self.particles.add(Particle(x, y, c, [vx, vy], life, size))

    def update(self):
        self.particles.update()
        if len(self.particles) > PARTICLE_CAP:
            sprites = self.particles.sprites()
            for s in sprites[: len(sprites) - PARTICLE_CAP]:
                s.kill()

    def draw(self, surface):
        self.particles.draw(surface)


# === Vehicle ===
def make_vehicle_surface(color_main, color_accent, is_ghost=False):
    surf = pygame.Surface((36, 56), pygame.SRCALPHA)
    alpha = 140 if is_ghost else 255
    cx, cy = 18, 28
    body = [(cx, 4), (cx + 14, cy + 16), (cx + 10, cy + 22), (cx - 10, cy + 22), (cx - 14, cy + 16)]
    pygame.draw.polygon(surf, (*color_main, alpha), body)
    inner = [(cx, 8), (cx + 10, cy + 12), (cx + 7, cy + 18), (cx - 7, cy + 18), (cx - 10, cy + 12)]
    pygame.draw.polygon(surf, (*color_accent, alpha), inner)
    pygame.draw.lines(surf, (*color_accent, min(255, alpha + 50)), True, body, 2)
    pygame.draw.ellipse(surf, (*SOLAR_WHITE, alpha // 3), (cx - 5, 12, 10, 14))
    pygame.draw.rect(surf, (*DESERT_ORANGE, alpha // 2), (cx - 6, cy + 20, 12, 4))
    return surf


# === Player ===
class Player(pygame.sprite.Sprite):
    def __init__(self, particles, player_num=1, x_pos=None, solo=False):
        super().__init__()
        self.player_num = player_num
        if player_num == 1:
            self.color_main = (0, 180, 200)
            self.color_accent = NEON_CYAN
            self.keys_up = [pygame.K_w]
            self.keys_down = [pygame.K_s]
            self.keys_left = [pygame.K_a]
            self.keys_right = [pygame.K_d]
            self.keys_boost = [pygame.K_LSHIFT]
            if solo:
                self.keys_up.append(pygame.K_UP)
                self.keys_down.append(pygame.K_DOWN)
                self.keys_left.append(pygame.K_LEFT)
                self.keys_right.append(pygame.K_RIGHT)
                self.keys_boost.append(pygame.K_RSHIFT)
                self.keys_boost.append(pygame.K_SPACE)
        else:
            self.color_main = (200, 50, 150)
            self.color_accent = NEON_MAGENTA
            self.keys_up = [pygame.K_UP]
            self.keys_down = [pygame.K_DOWN]
            self.keys_left = [pygame.K_LEFT]
            self.keys_right = [pygame.K_RIGHT]
            self.keys_boost = [pygame.K_RSHIFT]

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
        self.flare_hit = False

        self.lives = MAX_LIVES
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
        self.alive = True
        self.name = f"P{player_num}"

    def _any_key(self, keys, key_list):
        return any(keys[k] for k in key_list)

    def update(self, keys, slowmo_active=False):
        if not self.alive:
            return

        spd_m = 0.5 if slowmo_active else 1.0

        if self._any_key(keys, self.keys_left):
            self.rect.x -= int(5 * spd_m)
        if self._any_key(keys, self.keys_right):
            self.rect.x += int(5 * spd_m)
        if self._any_key(keys, self.keys_up):
            self.speed = min(self.speed + 0.8, 12)
            self.heat += 1.5
        if self._any_key(keys, self.keys_down):
            self.speed = max(self.speed - 1, 0)

        self.rect.x = max(ROAD_LEFT + 5, min(self.rect.x, ROAD_RIGHT - self.rect.width - 5))

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
            self.speed += 4
            self.heat = 0
            SFX["boost"].play()

        if self.flare_boost_timer > 0:
            self.flare_boost_timer -= 1
            self.speed = min(self.speed + 0.1, 15)
        else:
            self.speed = max(self.speed - 0.15, 0)

        self.heat = max(0, self.heat - 0.4)
        self.distance += self.speed * 0.01
        self.score += int(self.speed * 0.5)

        # Powerup timers
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

        # Exhaust
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
        if self.invincible_timer > 0 or self.ghost_mode:
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
            self.speed = max(0, self.speed - 3)
        return True


# === Coin ===
class Coin(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.pulse = random.randint(0, 60)
        self.image = pygame.Surface((24, 24), pygame.SRCALPHA)
        self._draw()
        self.rect = self.image.get_rect(center=(random.randint(ROAD_LEFT + 30, ROAD_RIGHT - 30), -20))
        self.base_speed = 2

    def _draw(self):
        self.image.fill((0, 0, 0, 0))
        p = 0.7 + 0.3 * math.sin(self.pulse * 0.12)
        pygame.draw.circle(self.image, (*COIN_GOLD, int(60 * p)), (12, 12), 12)
        pygame.draw.circle(self.image, COIN_GOLD, (12, 12), 8)
        pygame.draw.circle(self.image, (255, 240, 150), (12, 12), 5)

    def update(self, scroll_speed, players=None):
        self.pulse += 1
        self._draw()
        self.rect.y += scroll_speed + self.base_speed
        if players:
            for p in players:
                if p.alive and p.magnet:
                    dx = p.rect.centerx - self.rect.centerx
                    dy = p.rect.centery - self.rect.centery
                    dist = max(1, math.sqrt(dx * dx + dy * dy))
                    if dist < 200:
                        self.rect.x += int(dx / dist * 6)
                        self.rect.y += int(dy / dist * 6)
        if self.rect.y > SCREEN_HEIGHT + 30:
            self.kill()


# === Power-Ups ===
POWERUP_SHIELD = "shield"
POWERUP_MAGNET = "magnet"
POWERUP_SLOWMO = "slowmo"
POWERUP_COLORS = {POWERUP_SHIELD: SHIELD_BLUE, POWERUP_MAGNET: MAGNET_PURPLE, POWERUP_SLOWMO: SLOWMO_GREEN}
POWERUP_LABELS = {POWERUP_SHIELD: "S", POWERUP_MAGNET: "M", POWERUP_SLOWMO: "~"}


class PowerUp(pygame.sprite.Sprite):
    def __init__(self, kind=None):
        super().__init__()
        self.kind = kind or random.choice([POWERUP_SHIELD, POWERUP_MAGNET, POWERUP_SLOWMO])
        self.color = POWERUP_COLORS[self.kind]
        self.pulse = random.randint(0, 60)
        self.image = pygame.Surface((32, 32), pygame.SRCALPHA)
        self._draw()
        self.rect = self.image.get_rect(center=(random.randint(ROAD_LEFT + 30, ROAD_RIGHT - 30), -30))

    def _draw(self):
        self.image.fill((0, 0, 0, 0))
        p = 0.6 + 0.4 * math.sin(self.pulse * 0.1)
        pygame.draw.circle(self.image, (*self.color, int(50 * p)), (16, 16), 16)
        pygame.draw.circle(self.image, self.color, (16, 16), 12, 2)
        pygame.draw.circle(self.image, (*self.color, 120), (16, 16), 10)
        label = FONT_POWERUP.render(POWERUP_LABELS[self.kind], True, WHITE)
        self.image.blit(label, (16 - label.get_width() // 2, 16 - label.get_height() // 2))

    def update(self, scroll_speed):
        self.pulse += 1
        self._draw()
        self.rect.y += scroll_speed + 2
        if self.rect.y > SCREEN_HEIGHT + 30:
            self.kill()


# === Obstacle ===
class Obstacle(pygame.sprite.Sprite):
    def __init__(self, difficulty=1.0):
        super().__init__()
        size = random.choice([28, 36, 44])
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2
        pts = [(cx, 4), (size - 6, cy), (cx, size - 4), (6, cy)]
        pygame.draw.polygon(self.image, DESERT_ORANGE, pts)
        pygame.draw.polygon(self.image, SAND_YELLOW, pts, 2)
        pygame.draw.lines(self.image, NEON_MAGENTA, True, pts, 1)
        self.rect = self.image.get_rect(center=(random.randint(ROAD_LEFT + 20, ROAD_RIGHT - 20), -40))
        self.speed = random.uniform(2, 4) * difficulty

    def update(self, scroll_speed):
        self.rect.y += scroll_speed + self.speed
        if self.rect.y > SCREEN_HEIGHT + 50:
            self.kill()


# === Solar Flare ===
class SolarFlare(pygame.sprite.Sprite):
    def __init__(self, particles, x):
        super().__init__()
        r = 24
        self.radius = r
        self.pulse = 0
        self.image = pygame.Surface((r * 2 + 16, r * 2 + 16), pygame.SRCALPHA)
        self.rect = pygame.Rect(x - r - 8, -60, (r + 8) * 2, (r + 8) * 2)
        self.active = True
        self.particles = particles
        self.base_speed = 3
        self._redraw()

    def _redraw(self):
        r = self.radius
        self.image.fill((0, 0, 0, 0))
        cx, cy = r + 8, r + 8
        p = 0.8 + 0.2 * math.sin(self.pulse * 0.15)
        for i in range(3, 0, -1):
            a = int(30 * p * (3 - i))
            pygame.draw.circle(self.image, (*SOLAR_YELLOW, a), (cx, cy), int(r + i * 5))
        pygame.draw.circle(self.image, (255, 255, 200, int(100 * p)), (cx, cy), r)
        pygame.draw.circle(self.image, (255, 255, 0, 220), (cx, cy), r - 3)

    def update(self, scroll_speed, players):
        if not self.active:
            return
        self.pulse += 1
        self._redraw()
        self.rect.y += scroll_speed + self.base_speed
        if self.rect.y > SCREEN_HEIGHT + 50:
            self.kill()
            return
        if self.pulse % 4 == 0:
            self.particles.emit(
                self.rect.centerx, self.rect.centery, SOLAR_YELLOW,
                [random.uniform(-1, 1), random.uniform(-2, 0)], 30, 2,
            )
        for player in players:
            if player.alive and self.rect.colliderect(player.rect) and not player.ghost_mode:
                self.particles.burst(
                    self.rect.centerx, self.rect.centery, [SOLAR_YELLOW, SOLAR_WHITE], 12, 6, 40, 3
                )
                player.vel_y = -14
                player.flare_boost_timer = 150
                player.heat = 0
                player.flare_hit = True
                player.score += 200
                SFX["powerup"].play()
                self.active = False
                self.kill()
                break


# === Background ===
ROAD_COLOR = (40, 40, 50)
ROAD_EDGE_COLOR = NEON_CYAN
ROAD_SHOULDER = (80, 50, 20)
DESERT_BG = (140, 65, 18)
DASH_LENGTH = 40
DASH_GAP = 30


class Background:
    def __init__(self, particles):
        self.scroll_y = 0.0
        self.particles = particles
        self.sand_timer = 0

    def update_and_draw(self, speed, screen, slowmo=False):
        actual_speed = speed * (0.5 if slowmo else 1.0)
        self.scroll_y += actual_speed
        dash_period = DASH_LENGTH + DASH_GAP

        screen.fill(DESERT_BG)
        pygame.draw.rect(screen, ROAD_SHOULDER, (ROAD_LEFT - 20, 0, ROAD_WIDTH + 40, SCREEN_HEIGHT))
        pygame.draw.rect(screen, ROAD_COLOR, (ROAD_LEFT, 0, ROAD_WIDTH, SCREEN_HEIGHT))
        pygame.draw.line(screen, ROAD_EDGE_COLOR, (ROAD_LEFT, 0), (ROAD_LEFT, SCREEN_HEIGHT), 3)
        pygame.draw.line(screen, ROAD_EDGE_COLOR, (ROAD_RIGHT, 0), (ROAD_RIGHT, SCREEN_HEIGHT), 3)

        offset = int(self.scroll_y) % dash_period
        y = -DASH_LENGTH + offset
        while y < SCREEN_HEIGHT + DASH_LENGTH:
            pygame.draw.line(screen, NEON_MAGENTA, (ROAD_CENTER, y), (ROAD_CENTER, y + DASH_LENGTH), 2)
            y += dash_period

        for lane_x in [ROAD_LEFT + ROAD_WIDTH // 4, ROAD_LEFT + 3 * ROAD_WIDTH // 4]:
            y = -DASH_LENGTH + offset
            while y < SCREEN_HEIGHT + DASH_LENGTH:
                pygame.draw.line(screen, (70, 70, 90), (lane_x, y), (lane_x, y + DASH_LENGTH // 2), 1)
                y += dash_period

        # Speed lines at high velocity
        if speed > 8:
            intensity = min(30, int((speed - 8) * 12))
            line_surf = pygame.Surface((2, int(speed * 4)), pygame.SRCALPHA)
            line_surf.fill((*WHITE, min(60, intensity * 3)))
            for _ in range(intensity):
                lx = random.randint(0, SCREEN_WIDTH)
                ly = random.randint(0, SCREEN_HEIGHT)
                screen.blit(line_surf, (lx, ly))

        self.sand_timer += 1
        if self.sand_timer > 6:
            for _ in range(2):
                x = random.randint(0, SCREEN_WIDTH)
                self.particles.emit(
                    x, random.randint(0, SCREEN_HEIGHT), SAND_YELLOW,
                    [random.uniform(1, 2), random.uniform(0.5, 1.5)], 80, 1,
                )
            self.sand_timer = 0


# === HUD ===
def draw_lives_icons(screen, player, x, y):
    for i in range(MAX_LIVES):
        color = player.color_accent if i < player.lives else (50, 50, 60)
        cx = x + i * 22 + 8
        pts = [(cx, y), (cx + 6, y + 12), (cx - 6, y + 12)]
        pygame.draw.polygon(screen, color, pts)


def draw_hud(screen, players, game_distance, flare_timer, two_player):
    for idx, player in enumerate(players):
        if not player.alive and two_player:
            continue
        px = 8 if idx == 0 else SCREEN_WIDTH - 200
        if not two_player:
            px = 8
        panel_w, panel_h = 190, 100
        draw_panel(screen, pygame.Rect(px, 8, panel_w, panel_h), DARK_PANEL, player.color_accent)

        label = FONT_HUD_SM.render(player.name, True, player.color_accent)
        screen.blit(label, (px + 8, 12))
        draw_lives_icons(screen, player, px + 55, 14)

        heat_pct = min(100, int(player.heat))
        bar_w = 170
        pygame.draw.rect(screen, (40, 40, 50), (px + 10, 36, bar_w, 10))
        fill_w = int(bar_w * heat_pct / 100)
        if fill_w > 0:
            bar_col = NEON_MAGENTA if heat_pct > 80 else player.color_accent
            pygame.draw.rect(screen, bar_col, (px + 10, 36, fill_w, 10))

        spd = FONT_HUD_SM.render(f"{int(player.speed * 10)} km/h", True, SOLAR_WHITE)
        screen.blit(spd, (px + 10, 50))

        score_t = FONT_HUD_SM.render(f"Score: {player.score}", True, COIN_GOLD)
        screen.blit(score_t, (px + 10, 68))
        coin_t = FONT_HUD_SM.render(f"x{player.coins}", True, COIN_GOLD)
        # tiny coin icon
        pygame.draw.circle(screen, COIN_GOLD, (px + 125, 76), 5)
        pygame.draw.circle(screen, (255, 240, 150), (px + 125, 76), 3)
        screen.blit(coin_t, (px + 133, 68))

        pup_x = px + 10
        pup_y = 88
        if player.shield:
            s = FONT_HUD_SM.render("SHIELD", True, SHIELD_BLUE)
            screen.blit(s, (pup_x, pup_y))
            pup_x += 55
        if player.magnet:
            s = FONT_HUD_SM.render("MAGNET", True, MAGNET_PURPLE)
            screen.blit(s, (pup_x, pup_y))
            pup_x += 60
        if player.slowmo:
            s = FONT_HUD_SM.render("SLOW", True, SLOWMO_GREEN)
            screen.blit(s, (pup_x, pup_y))

    # Center distance
    dist_t = FONT_HUD.render(f"{game_distance:.1f} km", True, SOLAR_WHITE)
    screen.blit(dist_t, (SCREEN_WIDTH // 2 - dist_t.get_width() // 2, 12))

    if flare_timer < 180:
        warn = FONT_HUD.render("SOLAR FLARE!", True, SOLAR_YELLOW)
        screen.blit(warn, (SCREEN_WIDTH // 2 - warn.get_width() // 2, 38))


# === Screens ===
def draw_title(screen, tick):
    t = (tick % 180) / 180
    r = int(15 + 10 * math.sin(t * math.pi * 2))
    g = int(5 + 5 * math.sin(t * math.pi * 2 + 0.5))
    b = int(30 + 20 * math.sin(t * math.pi * 2 + 1))
    screen.fill((r, g, b))

    pygame.draw.rect(screen, (30, 30, 40), (ROAD_LEFT, 0, ROAD_WIDTH, SCREEN_HEIGHT))
    offset = int(tick * 2) % (DASH_LENGTH + DASH_GAP)
    y = -DASH_LENGTH + offset
    while y < SCREEN_HEIGHT:
        pygame.draw.line(screen, NEON_MAGENTA, (ROAD_CENTER, y), (ROAD_CENTER, y + DASH_LENGTH), 2)
        y += DASH_LENGTH + DASH_GAP

    title_text = "NEON RUSH"
    for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
        glow = FONT_TITLE.render(title_text, True, NEON_MAGENTA)
        screen.blit(glow, (SCREEN_WIDTH // 2 - glow.get_width() // 2 + dx, 80 + dy))
    title = FONT_TITLE.render(title_text, True, NEON_CYAN)
    screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 80))

    sub = FONT_SUBTITLE.render("DESERT VELOCITY", True, SOLAR_YELLOW)
    screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 155))

    blink = (tick // 30) % 2
    if blink:
        p1 = FONT_HUD.render("[1] SOLO RACE", True, NEON_CYAN)
        screen.blit(p1, (SCREEN_WIDTH // 2 - p1.get_width() // 2, 260))
        p2 = FONT_HUD.render("[2] TWO PLAYER", True, NEON_MAGENTA)
        screen.blit(p2, (SCREEN_WIDTH // 2 - p2.get_width() // 2, 295))

    c1 = FONT_HUD_SM.render("P1: WASD + L.Shift boost", True, NEON_CYAN)
    screen.blit(c1, (SCREEN_WIDTH // 2 - c1.get_width() // 2, 370))
    c1b = FONT_HUD_SM.render("Solo: WASD or Arrows + Shift/Space boost", True, (120, 120, 140))
    screen.blit(c1b, (SCREEN_WIDTH // 2 - c1b.get_width() // 2, 390))
    c2 = FONT_HUD_SM.render("P2: Arrows + R.Shift boost", True, NEON_MAGENTA)
    screen.blit(c2, (SCREEN_WIDTH // 2 - c2.get_width() // 2, 412))
    c3 = FONT_HUD_SM.render("P = Pause   F11 = Fullscreen   F2 = 2x Scale", True, (100, 100, 120))
    screen.blit(c3, (SCREEN_WIDTH // 2 - c3.get_width() // 2, 440))

    scores = load_highscores()
    if scores:
        hs = FONT_HUD_SM.render("HIGH SCORES", True, COIN_GOLD)
        screen.blit(hs, (SCREEN_WIDTH // 2 - hs.get_width() // 2, 480))
        for i, entry in enumerate(scores[:3]):
            txt = FONT_HUD_SM.render(f"{i + 1}. {entry['name']} - {entry['score']}", True, SOLAR_WHITE)
            screen.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2, 500 + i * 20))

    foot = FONT_HUD_SM.render("ESC = Quit", True, (80, 80, 100))
    screen.blit(foot, (SCREEN_WIDTH // 2 - foot.get_width() // 2, 578))


def draw_paused(screen):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))
    pw, ph = 300, 180
    px, py = (SCREEN_WIDTH - pw) // 2, (SCREEN_HEIGHT - ph) // 2
    draw_panel(screen, pygame.Rect(px, py, pw, ph), (0, 0, 20, 220), NEON_CYAN, 3)
    title = FONT_HUD_LG.render("PAUSED", True, NEON_CYAN)
    screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, py + 30))
    r = FONT_HUD.render("P = Resume", True, SOLAR_WHITE)
    screen.blit(r, (SCREEN_WIDTH // 2 - r.get_width() // 2, py + 90))
    q = FONT_HUD.render("R = Restart   ESC = Quit", True, (150, 150, 170))
    screen.blit(q, (SCREEN_WIDTH // 2 - q.get_width() // 2, py + 120))


def draw_gameover(screen, players, game_distance, tick, two_player):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))

    pw = 420
    ph = 300 if two_player else 260
    px, py = (SCREEN_WIDTH - pw) // 2, (SCREEN_HEIGHT - ph) // 2 - 20
    draw_panel(screen, pygame.Rect(px, py, pw, ph), (0, 0, 20, 220), NEON_MAGENTA, 3)

    title = FONT_TITLE.render("GAME OVER", True, NEON_MAGENTA)
    screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, py + 15))

    y_off = py + 85
    for p in players:
        if two_player:
            nm = FONT_HUD.render(p.name, True, p.color_accent)
            screen.blit(nm, (px + 30, y_off))
        col_x = px + (80 if two_player else 30)
        dist = FONT_HUD_SM.render(f"Distance: {p.distance:.1f} km", True, SOLAR_WHITE)
        screen.blit(dist, (col_x, y_off))
        sc = FONT_HUD.render(f"Score: {p.score}", True, COIN_GOLD)
        screen.blit(sc, (col_x, y_off + 20))
        cn = FONT_HUD_SM.render(f"Coins: {p.coins}", True, COIN_GOLD)
        screen.blit(cn, (col_x + 180, y_off + 22))
        y_off += 55 if two_player else 50

    # Winner callout in 2p
    if two_player:
        if players[0].score != players[1].score:
            winner = players[0] if players[0].score > players[1].score else players[1]
            wt = FONT_HUD.render(f"{winner.name} WINS!", True, winner.color_accent)
            screen.blit(wt, (SCREEN_WIDTH // 2 - wt.get_width() // 2, y_off))

    blink = (tick // 30) % 2
    if blink:
        retry = FONT_HUD.render("SPACE = Continue    ESC = Quit", True, NEON_CYAN)
        screen.blit(retry, (SCREEN_WIDTH // 2 - retry.get_width() // 2, py + ph - 45))


# === High Score Entry ===
class HighScoreEntry:
    def __init__(self, score):
        self.score = score
        self.name = ""
        self.done = False

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and len(self.name) > 0:
                scores = load_highscores()
                scores.append({"name": self.name, "score": self.score})
                scores.sort(key=lambda s: s["score"], reverse=True)
                save_highscores(scores[:5])
                SFX["highscore"].play()
                self.done = True
            elif event.key == pygame.K_BACKSPACE:
                self.name = self.name[:-1]
            elif len(self.name) < 3 and event.unicode.isalnum():
                self.name += event.unicode.upper()
                SFX["select"].play()

    def draw(self, screen, tick):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))

        pw, ph = 400, 250
        px, py = (SCREEN_WIDTH - pw) // 2, (SCREEN_HEIGHT - ph) // 2
        draw_panel(screen, pygame.Rect(px, py, pw, ph), (0, 0, 20, 220), COIN_GOLD, 3)

        title = FONT_HUD_LG.render("NEW HIGH SCORE!", True, COIN_GOLD)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, py + 20))

        score_t = FONT_SUBTITLE.render(f"{self.score}", True, SOLAR_WHITE)
        screen.blit(score_t, (SCREEN_WIDTH // 2 - score_t.get_width() // 2, py + 65))

        prompt = FONT_HUD.render("Enter your initials:", True, NEON_CYAN)
        screen.blit(prompt, (SCREEN_WIDTH // 2 - prompt.get_width() // 2, py + 105))

        display_name = self.name
        if len(display_name) < 3 and (tick // 20) % 2:
            display_name += "_"

        total_w = 3 * 50 + 2 * 10
        start_x = SCREEN_WIDTH // 2 - total_w // 2
        for i in range(3):
            bx = start_x + i * 60
            by = py + 145
            color = COIN_GOLD if i < len(self.name) else (60, 60, 70)
            pygame.draw.rect(screen, color, (bx, by, 46, 56), 2)
            if i < len(display_name):
                char = FONT_SCORE_ENTRY.render(display_name[i], True, SOLAR_WHITE)
                screen.blit(char, (bx + 23 - char.get_width() // 2, by + 4))

        hint = FONT_HUD_SM.render("ENTER to confirm", True, (120, 120, 140))
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, py + 215))


# === Display ===
current_scale = 1
is_fullscreen = False
display_surface: pygame.Surface | None = None


def create_display():
    global display_surface
    if is_fullscreen:
        display_surface = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        display_surface = pygame.display.set_mode(
            (SCREEN_WIDTH * current_scale, SCREEN_HEIGHT * current_scale)
        )
    pygame.display.set_caption("NEON RUSH: Desert Velocity")


# === Main ===
def main():
    global current_scale, is_fullscreen, display_surface

    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    create_display()
    clock = pygame.time.Clock()

    particles = ParticleSystem()
    shake = ScreenShake()
    bg = Background(particles)

    all_sprites = pygame.sprite.Group()
    obstacles = pygame.sprite.Group()
    coins_group = pygame.sprite.Group()
    powerups_group = pygame.sprite.Group()
    flares = pygame.sprite.Group()

    players: list[Player] = []
    two_player = False

    state = STATE_TITLE
    obstacle_timer = 0
    coin_timer = 0
    powerup_timer = 0
    flare_timer = random.randint(600, 1200)
    screen_flash = 0
    tick = 0
    game_distance = 0.0
    difficulty = 1.0
    highscore_entry: HighScoreEntry | None = None

    def start_game(num_players):
        nonlocal players, two_player, obstacle_timer, coin_timer, powerup_timer
        nonlocal flare_timer, screen_flash, game_distance, difficulty

        for g in [all_sprites, obstacles, coins_group, powerups_group, flares]:
            for s in list(g):
                s.kill()
        for p in list(particles.particles):
            p.kill()

        two_player = num_players == 2
        players.clear()

        if two_player:
            p1 = Player(particles, 1, ROAD_CENTER - 60)
            p2 = Player(particles, 2, ROAD_CENTER + 60)
            players.extend([p1, p2])
            all_sprites.add(p1, p2)
        else:
            p1 = Player(particles, 1, ROAD_CENTER, solo=True)
            players.append(p1)
            all_sprites.add(p1)

        obstacle_timer = 0
        coin_timer = 0
        powerup_timer = 0
        flare_timer = random.randint(600, 1200)
        screen_flash = 0
        game_distance = 0.0
        difficulty = 1.0

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if state == STATE_TITLE:
                    if event.key in (pygame.K_1, pygame.K_KP1, pygame.K_SPACE):
                        start_game(1)
                        state = STATE_PLAY
                        SFX["select"].play()
                    elif event.key in (pygame.K_2, pygame.K_KP2):
                        start_game(2)
                        state = STATE_PLAY
                        SFX["select"].play()
                    elif event.key == pygame.K_ESCAPE:
                        running = False

                elif state == STATE_PLAY:
                    if event.key == pygame.K_p:
                        state = STATE_PAUSED
                    elif event.key == pygame.K_ESCAPE:
                        state = STATE_TITLE
                        if engine_channel.get_busy():
                            engine_channel.fadeout(200)

                elif state == STATE_PAUSED:
                    if event.key == pygame.K_p:
                        state = STATE_PLAY
                    elif event.key == pygame.K_r:
                        start_game(2 if two_player else 1)
                        state = STATE_PLAY
                    elif event.key == pygame.K_ESCAPE:
                        running = False

                elif state == STATE_GAMEOVER:
                    if event.key == pygame.K_SPACE:
                        best = max(p.score for p in players)
                        if is_highscore(best):
                            highscore_entry = HighScoreEntry(best)
                            state = STATE_HIGHSCORE
                        else:
                            state = STATE_TITLE
                    elif event.key == pygame.K_ESCAPE:
                        running = False

                elif state == STATE_HIGHSCORE:
                    if highscore_entry:
                        highscore_entry.handle_event(event)
                        if highscore_entry.done:
                            state = STATE_TITLE
                            highscore_entry = None

                if event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    create_display()
                if event.key == pygame.K_F2 and not is_fullscreen:
                    current_scale = 2 if current_scale == 1 else 1
                    create_display()

        keys = pygame.key.get_pressed()

        if state == STATE_TITLE:
            draw_title(screen, tick)

        elif state == STATE_PLAY:
            any_slowmo = any(p.slowmo for p in players if p.alive)
            slowmo_mult = 0.5 if any_slowmo else 1.0

            alive_players = [p for p in players if p.alive]
            if not alive_players:
                state = STATE_GAMEOVER
                SFX["gameover"].play()
                if engine_channel.get_busy():
                    engine_channel.fadeout(300)
                tick += 1
                continue

            max_speed = max(p.speed for p in alive_players)
            scroll_speed = max_speed * slowmo_mult

            for p in players:
                p.update(keys, any_slowmo)

            game_distance += scroll_speed * 0.01
            difficulty = 1.0 + game_distance * 0.15

            # Spawn obstacles
            obstacle_timer += 1
            spawn_rate = max(12, int(45 / difficulty))
            if obstacle_timer > spawn_rate:
                obs = Obstacle(min(difficulty, 3.0))
                all_sprites.add(obs)
                obstacles.add(obs)
                obstacle_timer = 0

            # Spawn coins
            coin_timer += 1
            if coin_timer > 40:
                c = Coin()
                all_sprites.add(c)
                coins_group.add(c)
                coin_timer = 0

            # Spawn powerups (~10 seconds)
            powerup_timer += 1
            if powerup_timer > 600:
                pu = PowerUp()
                all_sprites.add(pu)
                powerups_group.add(pu)
                powerup_timer = 0

            # Solar flares
            flare_timer -= 1
            if flare_timer <= 0:
                flare_x = random.randint(ROAD_LEFT + 30, ROAD_RIGHT - 30)
                flare = SolarFlare(particles, flare_x)
                all_sprites.add(flare)
                flares.add(flare)
                flare_timer = random.randint(600, 1200)

            # Update objects
            for obs in list(obstacles):
                obs.update(scroll_speed)
            for c in list(coins_group):
                c.update(scroll_speed, alive_players)
            for pu in list(powerups_group):
                pu.update(scroll_speed)
            for flare in list(flares):
                flare.update(scroll_speed, alive_players)

            # Collisions
            for p in alive_players:
                if p.invincible_timer <= 0 and not p.ghost_mode:
                    hit = pygame.sprite.spritecollideany(p, obstacles)
                    if hit:
                        hit.kill()
                        p.take_hit(shake)
                        if not p.alive and not any(pl.alive for pl in players):
                            state = STATE_GAMEOVER
                            SFX["gameover"].play()
                            if engine_channel.get_busy():
                                engine_channel.fadeout(300)

                collected_coins = pygame.sprite.spritecollide(p, coins_group, True)
                for _ in collected_coins:
                    p.coins += 1
                    p.score += 50
                    particles.burst(p.rect.centerx, p.rect.centery - 10, [COIN_GOLD, SOLAR_YELLOW], 6, 3, 20, 2)
                    SFX["coin"].play()

                collected_pups = pygame.sprite.spritecollide(p, powerups_group, True)
                for pu in collected_pups:
                    if pu.kind == POWERUP_SHIELD:
                        p.shield = True
                        p.shield_timer = 600
                    elif pu.kind == POWERUP_MAGNET:
                        p.magnet = True
                        p.magnet_timer = 480
                    elif pu.kind == POWERUP_SLOWMO:
                        p.slowmo = True
                        p.slowmo_timer = 300
                    p.score += 100
                    particles.burst(p.rect.centerx, p.rect.centery, [POWERUP_COLORS[pu.kind]], 8, 4, 30, 3)
                    SFX["powerup"].play()

                if p.flare_hit:
                    screen_flash = 30
                    p.flare_hit = False

            particles.update()
            shake.update()

            # === Draw ===
            screen.fill(BLACK)
            bg.update_and_draw(scroll_speed, screen, any_slowmo)

            if screen_flash > 0:
                flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                flash_surf.fill((*SOLAR_WHITE, int(60 * (screen_flash / 30))))
                screen.blit(flash_surf, (0, 0))
                screen_flash -= 1

            particles.draw(screen)
            all_sprites.draw(screen)

            # Shield bubble
            for p in alive_players:
                if p.shield:
                    shield_surf = pygame.Surface((50, 70), pygame.SRCALPHA)
                    pulse = 0.6 + 0.4 * math.sin(tick * 0.1)
                    pygame.draw.ellipse(shield_surf, (*SHIELD_BLUE, int(40 * pulse)), (0, 0, 50, 70), 2)
                    screen.blit(shield_surf, (p.rect.centerx - 25, p.rect.centery - 35))

            # Slowmo tint
            if any_slowmo:
                tint = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                tint.fill((0, 50, 30, 25))
                screen.blit(tint, (0, 0))

            draw_hud(screen, players, game_distance, flare_timer, two_player)

            # Engine sound
            if max_speed > 1 and not engine_channel.get_busy():
                engine_channel.play(engine_sound, loops=-1)
                engine_channel.set_volume(0.05)
            elif max_speed <= 1 and engine_channel.get_busy():
                engine_channel.fadeout(200)
            elif engine_channel.get_busy():
                engine_channel.set_volume(min(0.12, max_speed * 0.01))

        elif state == STATE_PAUSED:
            draw_paused(screen)

        elif state == STATE_GAMEOVER:
            draw_gameover(screen, players, game_distance, tick, two_player)
            if engine_channel.get_busy():
                engine_channel.fadeout(300)

        elif state == STATE_HIGHSCORE:
            if highscore_entry:
                highscore_entry.draw(screen, tick)

        # === Render to display ===
        assert display_surface is not None
        sx, sy = shake.get_offset() if state == STATE_PLAY else (0, 0)

        if is_fullscreen:
            dw, dh = display_surface.get_size()
            scale_factor = min(dw / SCREEN_WIDTH, dh / SCREEN_HEIGHT)
            sw = int(SCREEN_WIDTH * scale_factor)
            sh = int(SCREEN_HEIGHT * scale_factor)
            display_surface.fill(BLACK)
            display_surface.blit(
                pygame.transform.smoothscale(screen, (sw, sh)),
                ((dw - sw) // 2 + sx, (dh - sh) // 2 + sy),
            )
        elif current_scale == 1:
            display_surface.fill(BLACK)
            display_surface.blit(screen, (sx, sy))
        else:
            display_surface.fill(BLACK)
            display_surface.blit(
                pygame.transform.scale(screen, (SCREEN_WIDTH * current_scale, SCREEN_HEIGHT * current_scale)),
                (sx * current_scale, sy * current_scale),
            )
        pygame.display.flip()
        clock.tick(FPS)
        tick += 1

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
