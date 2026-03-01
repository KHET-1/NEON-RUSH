import pygame
from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT

current_scale = 1
is_fullscreen = True
display_surface = None
vsync_enabled = True  # VSync on by default


def create_display():
    global display_surface
    flags = pygame.DOUBLEBUF
    if is_fullscreen:
        flags |= pygame.FULLSCREEN
        size = (0, 0)
    else:
        size = (SCREEN_WIDTH * current_scale, SCREEN_HEIGHT * current_scale)

    try:
        display_surface = pygame.display.set_mode(size, flags, vsync=1 if vsync_enabled else 0)
    except pygame.error:
        # Fallback if driver doesn't support vsync param
        display_surface = pygame.display.set_mode(size, flags)
    pygame.display.set_caption("NEON RUSH")


def toggle_fullscreen():
    global is_fullscreen
    is_fullscreen = not is_fullscreen
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
