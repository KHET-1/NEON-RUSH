"""Font definitions for NEON RUSH.

Hierarchy:
  FONT_TITLE / FONT_NEON_TITLE  — title screens (72pt bold)
  FONT_SUBTITLE                 — subtitles (28pt)
  FONT_HUD_LG                   — large HUD text (36pt bold)
  FONT_SCORE_ENTRY              — high-score initials (48pt bold)
  FONT_HUD                      — normal HUD (20pt)
  FONT_HUD_SM / _SM_BOLD        — small HUD labels (16pt)
  FONT_POWERUP                  — powerup labels (14pt bold)
"""
import pygame


_font_cache = {}


def load_font(name, size, bold=False):
    key = (name, size, bold)
    if key not in _font_cache:
        try:
            _font_cache[key] = pygame.font.SysFont(name, size, bold=bold)
        except Exception:
            _font_cache[key] = pygame.font.SysFont(None, size, bold=bold)
    return _font_cache[key]


FONT_TITLE = None
FONT_NEON_TITLE = None
FONT_SUBTITLE = None
FONT_HUD = None
FONT_HUD_SM = None
FONT_HUD_SM_BOLD = None
FONT_HUD_LG = None
FONT_SCORE_ENTRY = None
FONT_POWERUP = None


def init_fonts():
    global FONT_TITLE, FONT_NEON_TITLE, FONT_SUBTITLE, FONT_HUD, FONT_HUD_SM
    global FONT_HUD_SM_BOLD, FONT_HUD_LG, FONT_SCORE_ENTRY, FONT_POWERUP
    FONT_TITLE = load_font("dejavusans", 72, bold=True)
    FONT_NEON_TITLE = load_font("dejavusans", 72, bold=True)
    FONT_SUBTITLE = load_font("dejavusans", 28)
    FONT_HUD = load_font("dejavusans", 20)
    FONT_HUD_SM = load_font("dejavusans", 16)
    FONT_HUD_SM_BOLD = load_font("dejavusans", 16, bold=True)
    FONT_HUD_LG = load_font("dejavusans", 36, bold=True)
    FONT_SCORE_ENTRY = load_font("dejavusans", 48, bold=True)
    FONT_POWERUP = load_font("dejavusans", 14, bold=True)
