import pygame


def load_font(name, size, bold=False):
    try:
        return pygame.font.SysFont(name, size, bold=bold)
    except Exception:
        return pygame.font.SysFont(None, size, bold=bold)


FONT_TITLE = None
FONT_SUBTITLE = None
FONT_HUD = None
FONT_HUD_SM = None
FONT_HUD_SM_BOLD = None
FONT_HUD_LG = None
FONT_SCORE_ENTRY = None
FONT_POWERUP = None


def init_fonts():
    global FONT_TITLE, FONT_SUBTITLE, FONT_HUD, FONT_HUD_SM
    global FONT_HUD_SM_BOLD, FONT_HUD_LG, FONT_SCORE_ENTRY, FONT_POWERUP
    FONT_TITLE = load_font("freesans", 64, bold=True)
    FONT_SUBTITLE = load_font("dejavusans", 28)
    FONT_HUD = load_font("dejavusans", 20)
    FONT_HUD_SM = load_font("dejavusans", 16)
    FONT_HUD_SM_BOLD = load_font("dejavusans", 16, bold=True)
    FONT_HUD_LG = load_font("dejavusans", 36, bold=True)
    FONT_SCORE_ENTRY = load_font("dejavusans", 48, bold=True)
    FONT_POWERUP = load_font("dejavusans", 14, bold=True)
