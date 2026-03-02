"""Shared VFX utility library — backbone of all V2+ visual upgrades.

Provides palettes, gradient builders, glow/dither/scanline helpers,
and a lightweight array-based particle system for atmospheric effects.
All heavy surfaces are pre-rendered at init time; runtime cost is minimal.
"""

import pygame
import math
import random

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT

# ---------------------------------------------------------------------------
# V2 Palettes
# ---------------------------------------------------------------------------

SYNTH_PALETTE = {  # Desert V2 "Synthwave Wasteland"
    'sky_top': (8, 4, 28),
    'sky_mid': (25, 8, 50),
    'sky_horizon': (180, 50, 80),
    'sun_core': (255, 200, 100),
    'sun_glow': (255, 80, 120),
    'road_neon': (0, 255, 200),
    'mesa_dark': (40, 15, 35),
    'ember': (255, 120, 40),
}

TWILIGHT_PALETTE = {  # Excitebike V2 "Twilight Circuit"
    'sky_top': (10, 8, 30),
    'sky_mid': (30, 15, 55),
    'sky_horizon': (120, 60, 100),
    'cloud_dark': (25, 15, 45),
    'cloud_light': (50, 30, 70),
    'headlight': (255, 240, 200),
}

CYBER_PALETTE = {  # Micro Machines V2 "Neon Grid"
    'ground_dark': (10, 8, 18),
    'grid_line': (0, 180, 200),
    'barrier_glow': (255, 0, 120),
    'road_surface': (25, 22, 35),
}

# ---------------------------------------------------------------------------
# V3 Palettes
# ---------------------------------------------------------------------------

CRIMSON_PALETTE = {  # Desert V3 "Crimson Sandstorm"
    'sky_top': (25, 2, 2),
    'sky_mid': (80, 8, 8),
    'sky_horizon': (180, 30, 10),
    'storm_wall': (120, 20, 10),
    'lightning': (255, 220, 180),
    'ember': (255, 80, 20),
    'road_a': (60, 30, 10),
    'road_b': (75, 40, 15),
    'mesa_tint': (140, 40, 20),
    'crack': (90, 45, 15),
}

NEONRAIN_PALETTE = {  # Excitebike V3 "Midnight Neon Rain"
    'sky_top': (2, 2, 6),
    'sky_mid': (4, 4, 12),
    'sky_bottom': (8, 6, 18),
    'rain': (160, 180, 255),
    'billboard_cyan': (0, 255, 220),
    'billboard_magenta': (255, 0, 180),
    'puddle': (40, 60, 120),
    'fog': (10, 10, 25),
    'wet_lane': (30, 35, 50),
}

HOLO_PALETTE = {  # Micro Machines V3 "Holographic Wireframe"
    'void': (2, 3, 8),
    'grid_bright': (0, 255, 180),
    'grid_dim': (0, 120, 90),
    'data_wave': (0, 200, 255),
    'road_base': (2, 3, 8),
    'intersection': (0, 255, 220),
    'edge_glow': (0, 255, 200),
}


# ---------------------------------------------------------------------------
# Color Utilities
# ---------------------------------------------------------------------------

def lerp_color(c1, c2, t):
    """Linearly interpolate between two RGB(A) colors."""
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


# ---------------------------------------------------------------------------
# Surface Generators (init-time only)
# ---------------------------------------------------------------------------

def make_gradient_surface(w, h, color_top, color_bottom):
    """Pre-render a vertical two-stop gradient surface."""
    surf = pygame.Surface((w, h))
    if h <= 1:
        surf.fill(color_top)
        return surf
    for y in range(h):
        t = y / (h - 1)
        color = lerp_color(color_top, color_bottom, t)
        pygame.draw.line(surf, color, (0, y), (w - 1, y))
    return surf


def make_multi_gradient(w, h, stops):
    """Pre-render a multi-stop vertical gradient.

    Args:
        stops: list of (position, color) where position is 0.0-1.0
               e.g. [(0.0, (8,4,28)), (0.5, (25,8,50)), (1.0, (180,50,80))]
    """
    surf = pygame.Surface((w, h))
    if h <= 1 or len(stops) < 2:
        surf.fill(stops[0][1] if stops else (0, 0, 0))
        return surf

    stops = sorted(stops, key=lambda s: s[0])

    for y in range(h):
        t = y / (h - 1)
        # Find bounding stops
        lower = stops[0]
        upper = stops[-1]
        for i in range(len(stops) - 1):
            if stops[i][0] <= t <= stops[i + 1][0]:
                lower = stops[i]
                upper = stops[i + 1]
                break

        span = upper[0] - lower[0]
        local_t = (t - lower[0]) / span if span > 0 else 0.0
        color = lerp_color(lower[1], upper[1], local_t)
        pygame.draw.line(surf, color, (0, y), (w - 1, y))

    return surf


# ---------------------------------------------------------------------------
# Glow / Bloom
# ---------------------------------------------------------------------------

_glow_cache = {}


def draw_glow(surface, center, radius, color, intensity=0.6, rings=5):
    """Draw concentric circle bloom with BLEND_ADD. Cached by params."""
    key = (radius, color[:3], int(intensity * 100), rings)
    if key not in _glow_cache:
        size = radius * 2 + 4
        glow_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2
        for i in range(rings, 0, -1):
            r = int(radius * i / rings)
            a = int(255 * intensity * (1 - i / (rings + 1)))
            a = max(0, min(255, a))
            pygame.draw.circle(glow_surf, (*color[:3], a), (cx, cy), r)
        _glow_cache[key] = glow_surf

    cached = _glow_cache[key]
    blit_x = center[0] - cached.get_width() // 2
    blit_y = center[1] - cached.get_height() // 2
    surface.blit(cached, (blit_x, blit_y), special_flags=pygame.BLEND_RGB_ADD)


# ---------------------------------------------------------------------------
# Dither / Scanline Overlays (init-time)
# ---------------------------------------------------------------------------

# Bayer 4x4 dither matrix (normalized 0-1)
_BAYER_4x4 = [
    [0 / 16, 8 / 16, 2 / 16, 10 / 16],
    [12 / 16, 4 / 16, 14 / 16, 6 / 16],
    [3 / 16, 11 / 16, 1 / 16, 9 / 16],
    [15 / 16, 7 / 16, 13 / 16, 5 / 16],
]


def make_dither_overlay(w, h, strength=25):
    """Pre-render a Bayer 4x4 ordered dither SRCALPHA surface.

    Blitting this over flat-colored regions breaks color banding.
    strength: max alpha variation (0-255).
    """
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pixels = pygame.PixelArray(surf)
    for y in range(h):
        row = _BAYER_4x4[y % 4]
        for x in range(w):
            val = row[x % 4]
            a = int(val * strength)
            # Slight brightness modulation: bright dither dots
            pixels[x, y] = (255, 255, 255, a)
    del pixels
    return surf


def make_scanline_overlay(w, h, spacing=3, alpha=18):
    """Pre-render CRT scanline overlay (dark horizontal lines)."""
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(0, h, spacing):
        pygame.draw.line(surf, (0, 0, 0, alpha), (0, y), (w - 1, y))
    return surf


def make_vignette_overlay(w, h, strength=0.45):
    """Pre-bake radial darkening vignette (init-time only).

    strength: 0.0 = no darkening, 1.0 = corners fully black.
    """
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w / 2.0, h / 2.0
    max_dist = math.sqrt(cx * cx + cy * cy)
    # Build with concentric rectangles for speed (not per-pixel)
    steps = 24
    for i in range(steps):
        t = i / steps
        inset_x = int(cx * (1 - t))
        inset_y = int(cy * (1 - t))
        if inset_x <= 0 or inset_y <= 0:
            continue
        a = int(255 * strength * (t ** 1.8))
        a = min(255, max(0, a))
        rect = pygame.Rect(w - inset_x, h - inset_y, inset_x * 2 - w, inset_y * 2 - h)
        # Draw frame ring at this inset
        pygame.draw.rect(surf, (0, 0, 0, a),
                         (w // 2 - inset_x, h // 2 - inset_y, inset_x * 2, inset_y * 2),
                         max(1, int(max_dist / steps)))
    return surf


def make_tone_overlay(w, h, color, alpha=18):
    """Pre-bake a uniform color tone overlay (SRCALPHA)."""
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((*color[:3], alpha))
    return surf


_glow_rect_cache = {}


def draw_glow_rect(surface, rect, color, glow_width=4, alpha=80):
    """Draw a glowing rectangle border, cached by dimensions."""
    key = (rect.w, rect.h, color[:3], glow_width, alpha)
    if key not in _glow_rect_cache:
        w, h = rect.w + glow_width * 2, rect.h + glow_width * 2
        gsurf = pygame.Surface((w, h), pygame.SRCALPHA)
        for i in range(glow_width, 0, -1):
            a = int(alpha * (1 - (i - 1) / glow_width))
            pygame.draw.rect(gsurf, (*color[:3], a),
                             (glow_width - i, glow_width - i,
                              rect.w + i * 2, rect.h + i * 2), 2)
        _glow_rect_cache[key] = gsurf
    surface.blit(_glow_rect_cache[key],
                 (rect.x - glow_width, rect.y - glow_width),
                 special_flags=pygame.BLEND_RGB_ADD)


# ---------------------------------------------------------------------------
# AmbientParticles — lightweight array-based atmospheric particles
# ---------------------------------------------------------------------------

class AmbientParticles:
    """Fast atmospheric particle system using plain lists (no Sprite overhead).

    Independent of the main ParticleSystem and its PARTICLE_CAP.
    Each particle: [x, y, vx, vy, life, max_life, r, g, b, size]
    """

    def __init__(self, cap=120):
        self.cap = cap
        self.particles = []

    def spawn(self, x, y, vx, vy, life, color, size=1):
        if len(self.particles) >= self.cap:
            return
        self.particles.append([
            float(x), float(y), float(vx), float(vy),
            life, life,
            color[0], color[1], color[2],
            size,
        ])

    def update(self):
        alive = []
        for p in self.particles:
            p[0] += p[2]  # x += vx
            p[1] += p[3]  # y += vy
            p[4] -= 1     # life -= 1
            if p[4] > 0:
                alive.append(p)
        self.particles = alive

    def draw(self, surface):
        # Direct draw — no Surface allocations per particle
        draw_circle = pygame.draw.circle
        for p in self.particles:
            alpha_ratio = p[4] / p[5]  # life / max_life
            # Fade brightness instead of alpha (avoids SRCALPHA surfaces)
            f = max(0.1, alpha_ratio)
            color = (int(p[6] * f), int(p[7] * f), int(p[8] * f))
            ix, iy = int(p[0]), int(p[1])
            size = p[9]
            draw_circle(surface, color, (ix, iy), max(1, size))

    def clear(self):
        self.particles.clear()


# ---------------------------------------------------------------------------
# VFXState — per-mode visual effects state holder
# ---------------------------------------------------------------------------

class VFXState:
    """Holds ambient particles, scanline overlay, and screen flash state.

    Usage:
        vfx = VFXState()
        # in update loop:
        vfx.update()
        # after all drawing:
        vfx.draw_post(screen)
    """

    def __init__(self, enable_scanlines=True, tier=1, tone_color=None):
        self.ambient = AmbientParticles(120)
        self._scanline_overlay = None
        self._enable_scanlines = enable_scanlines
        self.flash_alpha = 0
        self.flash_color = (255, 255, 255)
        self._flash_surf = None
        self.tier = tier

        # V3 post-processing surfaces (pre-baked at init)
        self._vignette = None
        self._tone_overlay = None
        self._v3_scanline_offset = 0

        if tier >= 3:
            self._vignette = make_vignette_overlay(SCREEN_WIDTH, SCREEN_HEIGHT, strength=0.45)
            if tone_color:
                self._tone_overlay = make_tone_overlay(
                    SCREEN_WIDTH, SCREEN_HEIGHT, tone_color, alpha=15)
            # Animated scanlines: denser, with scroll offset
            self._v3_scanlines = make_scanline_overlay(
                SCREEN_WIDTH, SCREEN_HEIGHT + 6, spacing=2, alpha=22)

    def trigger_flash(self, color=(255, 255, 255), alpha=120):
        """Trigger a brief screen flash (fades over ~15 frames)."""
        self.flash_color = color
        self.flash_alpha = alpha

    def update(self):
        self.ambient.update()
        if self.flash_alpha > 0:
            self.flash_alpha = max(0, self.flash_alpha - 8)
        if self.tier >= 3:
            self._v3_scanline_offset = (self._v3_scanline_offset + 1) % 6

    def draw_post(self, screen):
        """Draw post-processing effects (ambient particles, scanlines, flash)."""
        # Ambient particles
        self.ambient.draw(screen)

        # Screen flash
        if self.flash_alpha > 0:
            if self._flash_surf is None:
                self._flash_surf = pygame.Surface(
                    (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            self._flash_surf.fill((*self.flash_color[:3], self.flash_alpha))
            screen.blit(self._flash_surf, (0, 0))

        if self.tier >= 3:
            # V3: color tone overlay
            if self._tone_overlay:
                screen.blit(self._tone_overlay, (0, 0))
            # V3: vignette (multiplicative darkening)
            if self._vignette:
                screen.blit(self._vignette, (0, 0))
            # V3: animated scrolling scanlines
            if hasattr(self, '_v3_scanlines'):
                screen.blit(self._v3_scanlines, (0, -self._v3_scanline_offset))
        elif self._enable_scanlines:
            # V2: static CRT scanlines
            if self._scanline_overlay is None:
                self._scanline_overlay = make_scanline_overlay(
                    SCREEN_WIDTH, SCREEN_HEIGHT, spacing=3, alpha=18)
            screen.blit(self._scanline_overlay, (0, 0))
