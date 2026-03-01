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
        for p in self.particles:
            alpha_ratio = p[4] / p[5]  # life / max_life
            a = int(255 * alpha_ratio)
            color = (p[6], p[7], p[8], a)
            size = p[9]
            ix, iy = int(p[0]), int(p[1])
            if size <= 1:
                # Single pixel — use small surface
                s = pygame.Surface((2, 2), pygame.SRCALPHA)
                s.fill(color)
                surface.blit(s, (ix, iy))
            else:
                s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, color, (size, size), size)
                surface.blit(s, (ix - size, iy - size))

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

    def __init__(self, enable_scanlines=True):
        self.ambient = AmbientParticles(120)
        self._scanline_overlay = None
        self._enable_scanlines = enable_scanlines
        self.flash_alpha = 0
        self.flash_color = (255, 255, 255)
        self._flash_surf = None

    def trigger_flash(self, color=(255, 255, 255), alpha=120):
        """Trigger a brief screen flash (fades over ~15 frames)."""
        self.flash_color = color
        self.flash_alpha = alpha

    def update(self):
        self.ambient.update()
        if self.flash_alpha > 0:
            self.flash_alpha = max(0, self.flash_alpha - 8)

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

        # CRT scanlines (last)
        if self._enable_scanlines:
            if self._scanline_overlay is None:
                self._scanline_overlay = make_scanline_overlay(
                    SCREEN_WIDTH, SCREEN_HEIGHT, spacing=3, alpha=18)
            screen.blit(self._scanline_overlay, (0, 0))
