import pygame
from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT

current_scale = 1
is_fullscreen = False
display_surface = None


def create_display():
    global display_surface
    if is_fullscreen:
        display_surface = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        display_surface = pygame.display.set_mode(
            (SCREEN_WIDTH * current_scale, SCREEN_HEIGHT * current_scale)
        )
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
