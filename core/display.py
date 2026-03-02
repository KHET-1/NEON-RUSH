import sys
import pygame
from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT

current_scale = 1
is_fullscreen = '--windowed' not in sys.argv
display_surface = None
vsync_enabled = True
use_scaled = is_fullscreen  # Only use SCALED in fullscreen


def set_windowed():
    """Force windowed mode."""
    global is_fullscreen, use_scaled, current_scale
    is_fullscreen = False
    use_scaled = False
    current_scale = 1


def create_display():
    global display_surface

    if is_fullscreen and use_scaled:
        flags = pygame.SCALED | pygame.FULLSCREEN
        size = (SCREEN_WIDTH, SCREEN_HEIGHT)
    elif is_fullscreen:
        flags = pygame.DOUBLEBUF | pygame.FULLSCREEN
        size = (0, 0)
    else:
        flags = pygame.DOUBLEBUF | pygame.RESIZABLE
        size = (SCREEN_WIDTH * current_scale, SCREEN_HEIGHT * current_scale)

    try:
        display_surface = pygame.display.set_mode(size, flags, vsync=1 if vsync_enabled else 0)
    except pygame.error:
        try:
            display_surface = pygame.display.set_mode(size, flags)
        except pygame.error:
            flags = pygame.DOUBLEBUF | (pygame.FULLSCREEN if is_fullscreen else pygame.RESIZABLE)
            size = (0, 0) if is_fullscreen else (SCREEN_WIDTH * current_scale, SCREEN_HEIGHT * current_scale)
            display_surface = pygame.display.set_mode(size, flags)
    pygame.display.set_caption("NEON RUSH")


def toggle_fullscreen():
    global is_fullscreen, use_scaled
    is_fullscreen = not is_fullscreen
    use_scaled = is_fullscreen
    create_display()


def toggle_scale():
    global current_scale
    if not is_fullscreen:
        current_scale = 2 if current_scale == 1 else 1
        create_display()


def toggle_vsync():
    global vsync_enabled
    vsync_enabled = not vsync_enabled
    create_display()
