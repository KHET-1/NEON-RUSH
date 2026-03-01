import pygame
import math
import random

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, NEON_CYAN, NEON_MAGENTA, SOLAR_YELLOW, SOLAR_WHITE, BLACK
from core.fonts import load_font


class TransitionEffect:
    """Animated transition between game modes.

    Styles:
        'zoom_rotate' — camera swings (Desert → Excitebike)
        'scanline'    — CRT scanline wipe (Excitebike → Micro Machines)
        'glitch'      — digital glitch dissolve (generic)

    Usage:
        transition = TransitionEffect('zoom_rotate', 'EXCITEBIKE', from_surface)
        while not transition.done:
            transition.update()
            transition.draw(screen)
    """

    DURATION = 180  # 3 seconds at 60fps

    def __init__(self, style, mode_name, from_surface=None, evolution_tier=1):
        self.style = style
        self.mode_name = mode_name
        self.evolution_tier = evolution_tier
        self.from_surface = from_surface.copy() if from_surface else pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.timer = 0
        self.done = False
        self.particles = []

    @property
    def progress(self):
        return min(1.0, self.timer / self.DURATION)

    def update(self):
        self.timer += 1
        if self.timer >= self.DURATION:
            self.done = True

        # Spawn some particles
        if self.timer % 3 == 0:
            self.particles.append({
                'x': random.randint(0, SCREEN_WIDTH),
                'y': random.randint(0, SCREEN_HEIGHT),
                'vx': random.uniform(-3, 3),
                'vy': random.uniform(-3, 3),
                'life': 40,
                'color': random.choice([NEON_CYAN, NEON_MAGENTA, SOLAR_YELLOW]),
                'size': random.randint(2, 5),
            })

        # Update particles
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= 1
        self.particles = [p for p in self.particles if p['life'] > 0]

    def draw(self, screen):
        t = self.progress

        if self.style == 'zoom_rotate':
            self._draw_zoom_rotate(screen, t)
        elif self.style == 'scanline':
            self._draw_scanline(screen, t)
        elif self.style == 'evolution':
            self._draw_evolution(screen, t)
        else:
            self._draw_glitch(screen, t)

        # Draw particles
        for p in self.particles:
            alpha = min(255, int(255 * (p['life'] / 40)))
            s = pygame.Surface((p['size'] * 2, p['size'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*p['color'][:3], alpha), (p['size'], p['size']), p['size'])
            screen.blit(s, (int(p['x']), int(p['y'])))

        # Mode name announcement
        if 0.3 < t < 0.9:
            name_progress = (t - 0.3) / 0.6
            alpha = int(255 * min(1.0, name_progress * 3) * min(1.0, (1.0 - name_progress) * 3))
            scale = 1.0 + 0.3 * math.sin(name_progress * math.pi)
            size = int(52 * scale)
            font = load_font("freesans", size, bold=True)

            # Glow
            for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
                glow = font.render(self.mode_name, True, NEON_MAGENTA)
                glow.set_alpha(alpha // 2)
                screen.blit(glow, (SCREEN_WIDTH // 2 - glow.get_width() // 2 + dx,
                                   SCREEN_HEIGHT // 2 - glow.get_height() // 2 + dy))

            txt = font.render(self.mode_name, True, SOLAR_YELLOW)
            txt.set_alpha(alpha)
            screen.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2,
                              SCREEN_HEIGHT // 2 - txt.get_height() // 2))

            # Tier badge above mode name (V2, V3, etc.)
            if self.evolution_tier > 1:
                badge_font = load_font("freesans", int(28 * scale), bold=True)
                badge_text = f"V{self.evolution_tier}"
                badge_surf = badge_font.render(badge_text, True, SOLAR_YELLOW)
                badge_surf.set_alpha(alpha)
                screen.blit(badge_surf, (SCREEN_WIDTH // 2 - badge_surf.get_width() // 2,
                                         SCREEN_HEIGHT // 2 - txt.get_height() // 2 - 35))

    def _draw_zoom_rotate(self, screen, t):
        """Zoom-rotate: camera swings from vertical to side view."""
        screen.fill(BLACK)

        if t < 0.5:
            # Zoom out + rotate the from_surface
            zoom = 1.0 - t * 1.5
            angle = t * 180
            if zoom > 0.1:
                w = int(SCREEN_WIDTH * zoom)
                h = int(SCREEN_HEIGHT * zoom)
                if w > 0 and h > 0:
                    scaled = pygame.transform.scale(self.from_surface, (w, h))
                    rotated = pygame.transform.rotate(scaled, angle)
                    rx = SCREEN_WIDTH // 2 - rotated.get_width() // 2
                    ry = SCREEN_HEIGHT // 2 - rotated.get_height() // 2
                    screen.blit(rotated, (rx, ry))
        else:
            # Fade in black then mode name handles the rest
            pass

        # Radial lines effect
        for i in range(12):
            angle = (i / 12) * math.pi * 2 + t * 3
            length = 100 + 300 * t
            cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
            ex = cx + math.cos(angle) * length
            ey = cy + math.sin(angle) * length
            alpha = int(100 * (1 - t))
            line_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(line_surf, (*NEON_CYAN, alpha), (cx, cy), (int(ex), int(ey)), 2)
            screen.blit(line_surf, (0, 0))

    def _draw_scanline(self, screen, t):
        """CRT scanline wipe: old image dissolves with scanlines."""
        screen.fill(BLACK)

        # Show from_surface with increasing scanline density
        if t < 0.7:
            screen.blit(self.from_surface, (0, 0))
            scanline_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            num_lines = int(t * 200)
            for i in range(num_lines):
                y = (i * 7 + int(t * 500)) % SCREEN_HEIGHT
                h = max(1, int(3 * t))
                pygame.draw.rect(scanline_surf, (0, 0, 0, int(200 * t)), (0, y, SCREEN_WIDTH, h))
            screen.blit(scanline_surf, (0, 0))

        # CRT flicker
        if random.random() < t * 0.3:
            flicker = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            flicker.fill((255, 255, 255, random.randint(5, 20)))
            screen.blit(flicker, (0, 0))

        # Horizontal color bars
        if t > 0.4:
            bar_progress = (t - 0.4) / 0.6
            bar_h = int(SCREEN_HEIGHT * bar_progress)
            bar_y = SCREEN_HEIGHT // 2 - bar_h // 2
            colors = [NEON_CYAN, NEON_MAGENTA, SOLAR_YELLOW, (50, 255, 50)]
            stripe_h = max(1, bar_h // len(colors))
            for i, c in enumerate(colors):
                y = bar_y + i * stripe_h
                s = pygame.Surface((SCREEN_WIDTH, stripe_h), pygame.SRCALPHA)
                s.fill((*c[:3], int(40 * bar_progress)))
                screen.blit(s, (0, y))

    def _draw_glitch(self, screen, t):
        """Digital glitch dissolve."""
        screen.fill(BLACK)

        if t < 0.6:
            # Break from_surface into strips and offset them
            strip_h = 8
            for y in range(0, SCREEN_HEIGHT, strip_h):
                offset = 0
                if random.random() < t * 0.5:
                    offset = random.randint(-int(50 * t), int(50 * t))
                strip = self.from_surface.subsurface((0, y, SCREEN_WIDTH, min(strip_h, SCREEN_HEIGHT - y)))
                alpha = int(255 * max(0, 1.0 - t * 1.5))
                strip.set_alpha(alpha)
                screen.blit(strip, (offset, y))

        # Random colored blocks
        num_blocks = int(t * 30)
        for _ in range(num_blocks):
            bx = random.randint(0, SCREEN_WIDTH - 20)
            by = random.randint(0, SCREEN_HEIGHT - 10)
            bw = random.randint(10, 60)
            bh = random.randint(2, 8)
            c = random.choice([NEON_CYAN, NEON_MAGENTA, SOLAR_YELLOW])
            s = pygame.Surface((bw, bh), pygame.SRCALPHA)
            s.fill((*c[:3], random.randint(30, 100)))
            screen.blit(s, (bx, by))

    def _draw_evolution(self, screen, t):
        """Evolution flash: V1→V2 transition. 4 phases over 180 frames.

        Phase 1 (0-0.25): Glitch deterioration — horizontal slice displacement + gray overlay
        Phase 2 (0.25-0.50): White-out — screen flashes white, hex text falls
        Phase 3 (0.50-0.67): Color explosion — expanding rainbow ring, V2 bg fades in
        Phase 4 (0.67-1.0): Title card — "EVOLUTION V2" with heavy glow + particle shower
        """
        cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2

        if t < 0.25:
            # Phase 1: Glitch deterioration
            phase_t = t / 0.25
            screen.blit(self.from_surface, (0, 0))
            # Increasing horizontal slice displacement
            strip_h = 6
            for y in range(0, SCREEN_HEIGHT, strip_h):
                if random.random() < phase_t * 0.6:
                    offset = random.randint(-int(80 * phase_t), int(80 * phase_t))
                    h = min(strip_h, SCREEN_HEIGHT - y)
                    if h > 0:
                        strip = self.from_surface.subsurface((0, y, SCREEN_WIDTH, h))
                        screen.blit(strip, (offset, y))
            # Gray desaturation overlay
            gray_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            gray_overlay.fill((128, 128, 128, int(100 * phase_t)))
            screen.blit(gray_overlay, (0, 0))

        elif t < 0.50:
            # Phase 2: White-out with cascading hex text
            phase_t = (t - 0.25) / 0.25
            # Flash intensity
            flash_alpha = int(255 * min(1.0, phase_t * 2))
            screen.fill(BLACK)
            white_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            white_surf.fill((255, 255, 255, flash_alpha))
            screen.blit(white_surf, (0, 0))
            # Cascading hex/binary text
            hex_font = load_font("dejavusans", 10)
            num_cols = 20
            for col in range(num_cols):
                x = col * (SCREEN_WIDTH // num_cols)
                # Each column drops at different speed
                drop_y = int((phase_t * 3 + col * 0.1) * SCREEN_HEIGHT) % SCREEN_HEIGHT
                for row in range(5):
                    hy = drop_y + row * 14
                    if 0 <= hy < SCREEN_HEIGHT:
                        hex_text = f"{random.randint(0, 255):02X}"
                        h_color = random.choice([NEON_CYAN, NEON_MAGENTA, (0, 255, 100)])
                        h_surf = hex_font.render(hex_text, True, h_color)
                        h_surf.set_alpha(int(200 * (1 - row / 5)))
                        screen.blit(h_surf, (x, hy))

        elif t < 0.67:
            # Phase 3: Color explosion — expanding rainbow ring
            phase_t = (t - 0.50) / 0.17
            screen.fill(BLACK)
            # Expanding ring
            ring_r = int(phase_t * max(SCREEN_WIDTH, SCREEN_HEIGHT))
            ring_colors = [(255, 0, 0), (255, 165, 0), (255, 255, 0),
                           (0, 255, 0), (0, 150, 255), (150, 0, 255)]
            for i, rc in enumerate(ring_colors):
                r = max(1, ring_r - i * 15)
                ring_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                a = int(120 * (1 - phase_t * 0.5))
                pygame.draw.circle(ring_surf, (*rc, a), (cx, cy), r, max(1, 8 - i))
                screen.blit(ring_surf, (0, 0))

        else:
            # Phase 4: Title card — "EVOLUTION V{tier}" with heavy neon glow
            phase_t = (t - 0.67) / 0.33
            screen.fill(BLACK)

            # Background subtle gradient flash
            bg_alpha = int(30 * (1 - phase_t))
            if bg_alpha > 0:
                bg_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                bg_surf.fill((*NEON_MAGENTA[:3], bg_alpha))
                screen.blit(bg_surf, (0, 0))

            # Title text
            title_text = f"EVOLUTION V{self.evolution_tier}"
            scale = 1.0 + 0.2 * math.sin(phase_t * math.pi * 2)
            size = int(56 * scale)
            font = load_font("freesans", size, bold=True)

            # Heavy glow (multiple offsets)
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    if dx == 0 and dy == 0:
                        continue
                    dist = abs(dx) + abs(dy)
                    glow_alpha = max(10, int(80 / dist))
                    glow = font.render(title_text, True, NEON_CYAN)
                    glow.set_alpha(glow_alpha)
                    screen.blit(glow, (cx - glow.get_width() // 2 + dx,
                                       cy - glow.get_height() // 2 + dy))

            # Main text
            alpha = int(255 * min(1.0, phase_t * 3))
            txt = font.render(title_text, True, SOLAR_WHITE)
            txt.set_alpha(alpha)
            screen.blit(txt, (cx - txt.get_width() // 2, cy - txt.get_height() // 2))

            # Particle shower from top
            if random.random() < 0.4:
                self.particles.append({
                    'x': random.randint(0, SCREEN_WIDTH),
                    'y': -5,
                    'vx': random.uniform(-1, 1),
                    'vy': random.uniform(3, 7),
                    'life': 60,
                    'color': random.choice([NEON_CYAN, NEON_MAGENTA, SOLAR_YELLOW, SOLAR_WHITE]),
                    'size': random.randint(2, 4),
                })
