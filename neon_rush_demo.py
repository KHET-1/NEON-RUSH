import pygame
import sys
import random
import math

pygame.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
BLACK = (0, 0, 0)
NEON_CYAN = (0, 255, 255)
NEON_MAGENTA = (255, 0, 255)
DESERT_ORANGE = (255, 102, 0)
SAND_YELLOW = (255, 204, 0)
SOLAR_YELLOW = (255, 255, 0)
SOLAR_WHITE = (255, 255, 200)
DARK_PANEL = (0, 0, 0, 180)
PARTICLE_CAP = 1500
GRAVITY = 0.6
ROAD_LEFT = 150
ROAD_RIGHT = SCREEN_WIDTH - 150
ROAD_WIDTH = ROAD_RIGHT - ROAD_LEFT
ROAD_CENTER = (ROAD_LEFT + ROAD_RIGHT) // 2

# Game states
STATE_TITLE = "title"
STATE_PLAY = "play"
STATE_GAMEOVER = "gameover"


def load_font(name, size, bold=False):
    try:
        return pygame.font.SysFont(name, size, bold=bold)
    except Exception:
        return pygame.font.SysFont(None, size, bold=bold)


# Fonts
FONT_TITLE = load_font("freesans", 64, bold=True)
FONT_SUBTITLE = load_font("dejavusans", 24)
FONT_HUD = load_font("dejavusans", 20)
FONT_HUD_SM = load_font("dejavusans", 16)


def draw_panel(surface, rect, color=(0, 0, 0, 180), border_color=NEON_CYAN, border=2):
    """Draw semi-transparent panel with neon border."""
    panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(panel, color, (0, 0, rect.w, rect.h))
    pygame.draw.rect(panel, border_color, (0, 0, rect.w, rect.h), border)
    surface.blit(panel, rect)


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
        self.vel[1] += GRAVITY * 0.1
        self.vel[0] *= 0.98
        self.vel[1] *= 0.98
        self.life -= 1
        alpha = int(255 * (self.life / self.max_life))
        self.image.set_alpha(alpha)
        if self.life <= 0 or self.rect.y > SCREEN_HEIGHT + 50 or self.rect.x < -50 or self.rect.x > SCREEN_WIDTH + 50:
            self.kill()


class ParticleSystem:
    def __init__(self):
        self.particles = pygame.sprite.Group()
        self.emitters = []

    def add_emitter(self, emitter_func):
        self.emitters.append(emitter_func)

    def update(self):
        for emitter in self.emitters:
            emitter(self)
        self.particles.update()
        if len(self.particles) > PARTICLE_CAP:
            for _ in range(150):
                if self.particles.sprites():
                    self.particles.sprites()[0].kill()

    def draw(self, surface):
        self.particles.draw(surface)


def make_vehicle_surface(is_ghost=False):
    """Create a sleek racing wedge pointing UP (direction of travel)."""
    surf = pygame.Surface((36, 56), pygame.SRCALPHA)
    alpha = 140 if is_ghost else 255
    cx, cy = 18, 28
    # Nose at top, wide exhaust at bottom
    body = [(cx, 4), (cx + 14, cy + 16), (cx + 10, cy + 22), (cx - 10, cy + 22), (cx - 14, cy + 16)]
    pygame.draw.polygon(surf, (0, 180, 200, alpha), body)
    # Inner highlight
    inner = [(cx, 8), (cx + 10, cy + 12), (cx + 7, cy + 18), (cx - 7, cy + 18), (cx - 10, cy + 12)]
    pygame.draw.polygon(surf, (*NEON_CYAN, alpha), inner)
    # Outline
    pygame.draw.lines(surf, (*NEON_CYAN, min(255, alpha + 50)), True, body, 2)
    # Cockpit
    pygame.draw.ellipse(surf, (*SOLAR_WHITE, alpha // 3), (cx - 5, 12, 10, 14))
    # Exhaust glow
    pygame.draw.rect(surf, (*DESERT_ORANGE, alpha // 2), (cx - 6, cy + 20, 12, 4))
    return surf


class Player(pygame.sprite.Sprite):
    def __init__(self, particles):
        super().__init__()
        self.base_image = make_vehicle_surface(False)
        self.ghost_image = make_vehicle_surface(True)
        self.image = self.base_image.copy()
        self.rect = self.image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60))
        self.speed = 0
        self.heat = 0
        self.ghost_mode = False
        self.ghost_timer = 0
        self.vel_y = 0
        self.flare_boost_timer = 0
        self.particles = particles
        self.last_emit = 0
        self.crash_emit = False
        self.flare_hit = False

    def update(self, keys):
        if keys[pygame.K_LEFT]:
            self.rect.x -= 5
        if keys[pygame.K_RIGHT]:
            self.rect.x += 5
        if keys[pygame.K_UP]:
            self.speed = min(self.speed + 1, 12)
            self.heat += 2
        if keys[pygame.K_DOWN]:
            self.speed = max(self.speed - 1, 0)

        self.rect.x = max(ROAD_LEFT + 5, min(self.rect.x, ROAD_RIGHT - self.rect.width - 5))

        # Only apply gravity during flare jumps, not normal driving
        if self.vel_y != 0:
            self.vel_y += GRAVITY
            self.rect.y += self.vel_y
            if self.rect.bottom >= SCREEN_HEIGHT - 30:
                self.rect.bottom = SCREEN_HEIGHT - 30
                self.vel_y = 0
        else:
            self.rect.bottom = SCREEN_HEIGHT - 30

        if self.heat > 100:
            self.ghost_mode = True
            self.ghost_timer = 300
            self.heat = 0
        if self.ghost_mode:
            self.image = self.ghost_image.copy()
            self.ghost_timer -= 1
            if self.ghost_timer <= 0:
                self.ghost_mode = False
                self.image = self.base_image.copy()
        elif keys[pygame.K_SPACE] and self.heat > 50:
            self.speed += 5
            self.heat = 0

        if self.flare_boost_timer > 0:
            self.flare_boost_timer -= 1
            self.speed = min(self.speed + 0.1, 15)
        else:
            self.speed = max(self.speed - 0.2, 0)

        self.heat = max(0, self.heat - 0.5)

        now = pygame.time.get_ticks()
        if (keys[pygame.K_UP] or self.flare_boost_timer > 0) and now - self.last_emit > 60:
            num = 3 if self.flare_boost_timer > 0 else 2
            colors = [SOLAR_YELLOW, SOLAR_WHITE] if self.flare_boost_timer > 0 else [NEON_CYAN, (100, 100, 120)]
            for _ in range(num):
                vx = random.uniform(-1, 1)
                vy = random.uniform(2, 4)
                color = random.choice(colors)
                sz = 3 if self.flare_boost_timer > 0 else 2
                self.particles.particles.add(Particle(self.rect.centerx, self.rect.bottom + 6, color, [vx, vy], life=30, size=sz))
            self.last_emit = now

        if self.ghost_mode and now - self.last_emit > 80:
            self.particles.particles.add(Particle(self.rect.centerx, self.rect.centery, NEON_CYAN,
                [random.uniform(-1, 1), random.uniform(-1, 1)], life=20, size=2))

        if self.crash_emit:
            for _ in range(30):
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(4, 9)
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed + self.vel_y
                color = random.choice([SAND_YELLOW, DESERT_ORANGE])
                self.particles.particles.add(Particle(self.rect.centerx, self.rect.centery, color, [vx, vy], life=70, size=4))
            self.crash_emit = False


class Obstacle(pygame.sprite.Sprite):
    """Falling debris/crystal - diamond shape with hazard look."""
    def __init__(self):
        super().__init__()
        size = random.choice([28, 36, 44])
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2
        pts = [(cx, 4), (size - 6, cy), (cx, size - 4), (6, cy)]
        pygame.draw.polygon(self.image, DESERT_ORANGE, pts)
        pygame.draw.polygon(self.image, SAND_YELLOW, pts, 2)
        pygame.draw.lines(self.image, NEON_MAGENTA, True, pts, 1)
        # Spawn on the road, not off in the desert
        self.rect = self.image.get_rect(center=(random.randint(ROAD_LEFT + 20, ROAD_RIGHT - 20), -40))
        self.speed = random.uniform(3, 6)

    def update(self, scroll_speed):
        self.rect.y += scroll_speed + self.speed
        if self.rect.y > SCREEN_HEIGHT:
            self.kill()


class SolarFlare(pygame.sprite.Sprite):
    def __init__(self, particles, x):
        super().__init__()
        r = 30
        self.radius = r
        self.pulse = 0
        self.image = pygame.Surface((r * 2 + 20, r * 2 + 20), pygame.SRCALPHA)
        self._redraw()
        self.rect = pygame.Rect(x - r - 10, SCREEN_HEIGHT - 70, (r + 10) * 2, (r + 10) * 2)

    def _redraw(self):
        r = self.radius
        self.image.fill((0, 0, 0, 0))
        cx, cy = r + 10, r + 10
        p = 0.8 + 0.2 * math.sin(self.pulse * 0.15)
        # Pulsing outer glow
        for i in range(4, 0, -1):
            a = int(25 * p * (4 - i))
            pygame.draw.circle(self.image, (*SOLAR_YELLOW, a), (cx, cy), int(r + i * 6))
        pygame.draw.circle(self.image, (255, 255, 200, int(100 * p)), (cx, cy), r)
        pygame.draw.circle(self.image, (255, 255, 0, 220), (cx, cy), r - 3)
        self.active = True
        self.timer = 180
        self.particles = particles
        self.explode_timer = 0

    def update(self, player):
        if self.active:
            self.pulse += 1
            self._redraw()
            self.timer -= 1
            if self.timer <= 0:
                self.kill()
                return

            # Gentle ambient glow particles (2 per frame, not 8)
            if self.pulse % 3 == 0:
                for _ in range(2):
                    vx = random.uniform(-1, 1)
                    vy = random.uniform(-3, -1)
                    self.particles.particles.add(Particle(self.rect.centerx, self.rect.bottom, SOLAR_YELLOW,
                        [vx, vy], life=40, size=3))

            if self.rect.colliderect(player.rect) and not player.ghost_mode:
                # Burst on pickup
                for _ in range(12):
                    angle = random.uniform(0, 2 * math.pi)
                    spd = random.uniform(3, 8)
                    vx = math.cos(angle) * spd
                    vy = math.sin(angle) * spd
                    color = random.choice([SOLAR_YELLOW, SOLAR_WHITE])
                    self.particles.particles.add(Particle(self.rect.centerx, self.rect.centery, color, [vx, vy], life=50, size=4))
                player.vel_y = -16
                player.flare_boost_timer = 180
                player.heat = 0
                player.flare_hit = True
                self.active = False
                self.kill()


ROAD_COLOR = (40, 40, 50)
ROAD_EDGE_COLOR = NEON_CYAN
ROAD_SHOULDER = (80, 50, 20)
DESERT_BG = (160, 75, 20)
DASH_LENGTH = 40
DASH_GAP = 30


class Background:
    def __init__(self, particles):
        self.scroll_y = 0.0
        self.particles = particles
        self.sand_emit_timer = 0

    def update_and_draw(self, speed, screen):
        self.scroll_y += speed
        dash_period = DASH_LENGTH + DASH_GAP

        # Desert fill
        screen.fill(DESERT_BG)

        # Road shoulder (slightly lighter strip)
        pygame.draw.rect(screen, ROAD_SHOULDER, (ROAD_LEFT - 20, 0, ROAD_WIDTH + 40, SCREEN_HEIGHT))

        # Road surface
        pygame.draw.rect(screen, ROAD_COLOR, (ROAD_LEFT, 0, ROAD_WIDTH, SCREEN_HEIGHT))

        # Road edge lines (solid neon)
        pygame.draw.line(screen, ROAD_EDGE_COLOR, (ROAD_LEFT, 0), (ROAD_LEFT, SCREEN_HEIGHT), 3)
        pygame.draw.line(screen, ROAD_EDGE_COLOR, (ROAD_RIGHT, 0), (ROAD_RIGHT, SCREEN_HEIGHT), 3)

        # Center dashed line (scrolls with speed)
        offset = int(self.scroll_y) % dash_period
        y = -DASH_LENGTH + offset
        while y < SCREEN_HEIGHT + DASH_LENGTH:
            pygame.draw.line(screen, NEON_MAGENTA, (ROAD_CENTER, y), (ROAD_CENTER, y + DASH_LENGTH), 2)
            y += dash_period

        # Lane dashes (quarter marks)
        for lane_x in [ROAD_LEFT + ROAD_WIDTH // 4, ROAD_LEFT + 3 * ROAD_WIDTH // 4]:
            y = -DASH_LENGTH + offset
            while y < SCREEN_HEIGHT + DASH_LENGTH:
                pygame.draw.line(screen, (80, 80, 100), (lane_x, y), (lane_x, y + DASH_LENGTH // 2), 1)
                y += dash_period

        # Sand particles blowing across
        self.sand_emit_timer += 1
        if self.sand_emit_timer > 5:
            for _ in range(3):
                x = random.randint(0, SCREEN_WIDTH)
                self.particles.particles.add(Particle(x, random.randint(0, SCREEN_HEIGHT), SAND_YELLOW,
                    [random.uniform(1, 3), random.uniform(0.5, 2)], life=90, size=1))
            self.sand_emit_timer = 0


# === Title Screen ===
def draw_title(screen, tick):
    # Animated gradient background
    t = (tick % 180) / 180
    r = int(20 + 15 * math.sin(t * math.pi * 2))
    g = int(80 + 40 * math.sin(t * math.pi * 2 + 0.5))
    b = int(120 + 60 * math.sin(t * math.pi * 2 + 1))
    screen.fill((r, g // 2, b))

    # Subtle moving stripes (parallax feel)
    for i in range(0, SCREEN_WIDTH + 200, 80):
        x = (i + tick // 2) % (SCREEN_WIDTH + 200) - 100
        pygame.draw.line(screen, (r + 30, g, min(255, b + 40)), (x, 0), (x, SCREEN_HEIGHT), 3)

    # Sand particles (ambient)
    for _ in range(3):
        x = random.randint(0, SCREEN_WIDTH)
        y = (random.randint(0, SCREEN_HEIGHT) + tick) % (SCREEN_HEIGHT + 20) - 10
        pygame.draw.circle(screen, SAND_YELLOW, (x, y), 1)

    # Title with glow
    title_text = "NEON RUSH"
    subtitle_text = "DESERT VELOCITY"
    for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
        glow = FONT_TITLE.render(title_text, True, NEON_MAGENTA)
        screen.blit(glow, (SCREEN_WIDTH // 2 - glow.get_width() // 2 + dx, 140 + dy))
    title = FONT_TITLE.render(title_text, True, NEON_CYAN)
    screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 140))

    sub = FONT_SUBTITLE.render(subtitle_text, True, SOLAR_YELLOW)
    screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 220))

    # Blinking prompt
    blink = (tick // 30) % 2
    if blink:
        prompt = FONT_HUD.render("PRESS SPACE TO RACE", True, SOLAR_WHITE)
        screen.blit(prompt, (SCREEN_WIDTH // 2 - prompt.get_width() // 2, 380))

    # Controls hint
    ctrl = FONT_HUD_SM.render("↑↓ Accelerate / Brake  •  ←→ Steer  •  SPACE Heat Sync Boost", True, NEON_CYAN)
    screen.blit(ctrl, (SCREEN_WIDTH // 2 - ctrl.get_width() // 2, 440))
    disp = FONT_HUD_SM.render("F2 — Toggle 2x  •  F11 — Fullscreen", True, NEON_MAGENTA)
    screen.blit(disp, (SCREEN_WIDTH // 2 - disp.get_width() // 2, 465))

    # Footer
    foot = FONT_HUD_SM.render("Demo • Phoenix Desert Racing", True, (100, 100, 120))
    screen.blit(foot, (SCREEN_WIDTH // 2 - foot.get_width() // 2, 560))


# === HUD ===
def draw_hud(screen, player, flare_timer):
    # Heat bar panel
    panel_w, panel_h = 180, 80
    draw_panel(screen, pygame.Rect(12, 12, panel_w, panel_h), DARK_PANEL, NEON_CYAN)

    heat_pct = min(100, int(player.heat))
    bar_w = 160
    bar_x, bar_y = 22, 50
    pygame.draw.rect(screen, (40, 40, 50), (bar_x, bar_y, bar_w, 12))
    fill_w = int(bar_w * heat_pct / 100)
    if fill_w > 0:
        pygame.draw.rect(screen, NEON_CYAN, (bar_x, bar_y, fill_w, 12))
        if heat_pct >= 100:
            pygame.draw.rect(screen, NEON_MAGENTA, (bar_x, bar_y, bar_w, 12), 1)

    heat_label = FONT_HUD_SM.render("HEAT SYNC", True, NEON_CYAN)
    screen.blit(heat_label, (22, 22))
    heat_val = FONT_HUD.render(f"{heat_pct}%", True, SOLAR_WHITE)
    screen.blit(heat_val, (22 + panel_w - heat_val.get_width() - 12, 22))

    # Speed
    speed_label = FONT_HUD_SM.render("VELOCITY", True, NEON_CYAN)
    screen.blit(speed_label, (22, 68))
    speed_val = FONT_HUD.render(f"{int(player.speed * 10)} km/h", True, SOLAR_WHITE)
    screen.blit(speed_val, (22 + panel_w - speed_val.get_width() - 12, 68))

    # Center status
    if player.ghost_mode:
        mode = FONT_HUD.render("GHOST MODE", True, NEON_MAGENTA)
    elif player.flare_boost_timer > 0:
        mode = FONT_HUD.render(f"FLARE BOOST {player.flare_boost_timer // 60}s", True, SOLAR_YELLOW)
    elif flare_timer < 300:
        mode = FONT_HUD.render("SOLAR FLARE INCOMING", True, SOLAR_YELLOW)
    else:
        mode = None
    if mode:
        screen.blit(mode, (SCREEN_WIDTH // 2 - mode.get_width() // 2, 16))


# === Game Over ===
def draw_gameover(screen, player, tick):
    # Dark overlay
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))

    # Panel
    pw, ph = 400, 220
    px, py = (SCREEN_WIDTH - pw) // 2, (SCREEN_HEIGHT - ph) // 2 - 20
    draw_panel(screen, pygame.Rect(px, py, pw, ph), (0, 0, 20, 220), NEON_MAGENTA, 3)

    gameover = FONT_TITLE.render("CRASH", True, NEON_MAGENTA)
    screen.blit(gameover, (SCREEN_WIDTH // 2 - gameover.get_width() // 2, py + 30))

    speed_at_crash = int(player.speed * 10)
    stat = FONT_SUBTITLE.render(f"Velocity at impact: {speed_at_crash} km/h", True, SOLAR_WHITE)
    screen.blit(stat, (SCREEN_WIDTH // 2 - stat.get_width() // 2, py + 110))

    blink = (tick // 30) % 2
    if blink:
        retry = FONT_HUD.render("SPACE — Retry    ESC — Quit", True, NEON_CYAN)
        screen.blit(retry, (SCREEN_WIDTH // 2 - retry.get_width() // 2, py + 160))


def reset_game(particles, all_sprites, obstacles, flares):
    """Reset all game objects for a new run."""
    for s in list(all_sprites):
        s.kill()
    for o in list(obstacles):
        o.kill()
    for f in list(flares):
        f.kill()
    for p in list(particles.particles):
        p.kill()


# === Display Management ===
current_scale = 1
is_fullscreen = False
display_surface: pygame.Surface | None = None


def create_display():
    """Create or recreate the display surface for current mode."""
    global display_surface
    if is_fullscreen:
        display_surface = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        display_surface = pygame.display.set_mode(
            (SCREEN_WIDTH * current_scale, SCREEN_HEIGHT * current_scale)
        )
    pygame.display.set_caption("NEON RUSH: Desert Velocity")


# === Main ===
screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
create_display()
clock = pygame.time.Clock()

particles = ParticleSystem()
all_sprites = pygame.sprite.Group()
obstacles = pygame.sprite.Group()
flares = pygame.sprite.Group()

player = Player(particles)
all_sprites.add(player)
bg = Background(particles)

state = STATE_TITLE
obstacle_timer = 0
flare_timer = random.randint(600, 1200)
screen_flash = 0
tick = 0

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if state == STATE_TITLE:
                    running = False
                elif state == STATE_GAMEOVER:
                    running = False
                else:
                    state = STATE_TITLE
            if event.key == pygame.K_F11:
                is_fullscreen = not is_fullscreen
                create_display()
            if event.key == pygame.K_F2:
                if not is_fullscreen:
                    current_scale = 2 if current_scale == 1 else 1
                    create_display()
            if event.key == pygame.K_SPACE:
                if state == STATE_TITLE:
                    state = STATE_PLAY
                    reset_game(particles, all_sprites, obstacles, flares)
                    player = Player(particles)
                    all_sprites.add(player)
                    obstacle_timer = 0
                    flare_timer = random.randint(600, 1200)
                elif state == STATE_GAMEOVER:
                    state = STATE_PLAY
                    reset_game(particles, all_sprites, obstacles, flares)
                    player = Player(particles)
                    all_sprites.add(player)
                    obstacle_timer = 0
                    flare_timer = random.randint(600, 1200)

    keys = pygame.key.get_pressed()

    if state == STATE_TITLE:
        draw_title(screen, tick)

    elif state == STATE_PLAY:
        player.flare_hit = False
        player.update(keys)
        scroll_speed = player.speed

        obstacle_timer += 1
        spawn_rate = max(15, 50 - int(player.speed * 3))
        if obstacle_timer > spawn_rate:
            obs = Obstacle()
            all_sprites.add(obs)
            obstacles.add(obs)
            obstacle_timer = 0

        flare_timer -= 1
        if flare_timer <= 0:
            flare_x = random.randint(ROAD_LEFT + 30, ROAD_RIGHT - 30)
            flare = SolarFlare(particles, flare_x)
            all_sprites.add(flare)
            flares.add(flare)
            flare_timer = random.randint(900, 1800)

        for obs in obstacles.sprites():
            obs.update(scroll_speed)
        for flare in list(flares):
            flare.update(player)
            if player.flare_hit:
                screen_flash = 40

        if not player.ghost_mode:
            collided = pygame.sprite.spritecollideany(player, obstacles)
            if collided:
                collided.kill()
                player.speed = 0
                player.heat = 0
                player.vel_y = 0
                player.crash_emit = True
                state = STATE_GAMEOVER

        particles.update()
        screen.fill(BLACK)
        bg.update_and_draw(scroll_speed, screen)

        if screen_flash > 0:
            flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            flash_surf.set_alpha(int(80 * (screen_flash / 40)))
            flash_surf.fill(SOLAR_WHITE)
            screen.blit(flash_surf, (0, 0))
            screen_flash -= 1

        particles.draw(screen)
        all_sprites.draw(screen)

        draw_hud(screen, player, flare_timer)

    elif state == STATE_GAMEOVER:
        # Keep last frame visible, draw overlay
        draw_gameover(screen, player, tick)

    # Scale render surface to display
    assert display_surface is not None
    if is_fullscreen:
        dw, dh = display_surface.get_size()
        scale_factor = min(dw / SCREEN_WIDTH, dh / SCREEN_HEIGHT)
        sw = int(SCREEN_WIDTH * scale_factor)
        sh = int(SCREEN_HEIGHT * scale_factor)
        display_surface.fill(BLACK)
        display_surface.blit(
            pygame.transform.smoothscale(screen, (sw, sh)),
            ((dw - sw) // 2, (dh - sh) // 2),
        )
    elif current_scale == 1:
        display_surface.blit(screen, (0, 0))
    else:
        display_surface.blit(
            pygame.transform.scale(
                screen,
                (SCREEN_WIDTH * current_scale, SCREEN_HEIGHT * current_scale),
            ),
            (0, 0),
        )
    pygame.display.flip()
    clock.tick(60)
    tick += 1

pygame.quit()
sys.exit()
