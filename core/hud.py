import pygame
import math

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, NEON_CYAN, NEON_MAGENTA,
    DARK_PANEL, SOLAR_WHITE, SOLAR_YELLOW, COIN_GOLD,
    SHIELD_BLUE, MAGNET_PURPLE, SLOWMO_GREEN,
)
from core.fonts import load_font


def draw_panel(surface, rect, color=(0, 0, 0, 200), border_color=NEON_CYAN, border=2):
    panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(panel, color, (0, 0, rect.w, rect.h))
    pygame.draw.rect(panel, border_color, (0, 0, rect.w, rect.h), border)
    surface.blit(panel, rect)


class FloatingText:
    def __init__(self, x, y, text, color, size=20):
        self.x = x
        self.y = float(y)
        self.text = text
        self.color = color
        self.font = load_font("dejavusans", size, bold=True)
        self.life = 60
        self.max_life = 60

    def update(self):
        self.y -= 1.2
        self.life -= 1
        return self.life > 0

    def draw(self, surface):
        alpha = int(255 * (self.life / self.max_life))
        txt = self.font.render(self.text, True, self.color)
        txt.set_alpha(alpha)
        surface.blit(txt, (int(self.x) - txt.get_width() // 2, int(self.y)))


def draw_lives_icons(screen, player, x, y):
    for i in range(player.max_lives):
        color = player.color_accent if i < player.lives else (45, 45, 55)
        cx = x + i * 24 + 10
        pts = [(cx, y + 2), (cx + 7, y + 14), (cx - 7, y + 14)]
        pygame.draw.polygon(screen, (30, 30, 35), [(p[0] + 1, p[1] + 1) for p in pts])
        pygame.draw.polygon(screen, color, pts)


def draw_ai_badge(screen, x, y, color):
    """Draw a 24x24 procedural circuit-brain AI badge."""
    surf = pygame.Surface((24, 24), pygame.SRCALPHA)
    cx, cy = 12, 12
    # Circle (brain outline)
    pygame.draw.circle(surf, color, (cx, cy), 10, 2)
    # Three radiating circuit lines
    pygame.draw.line(surf, color, (cx, cy - 10), (cx, cy - 3), 1)
    pygame.draw.line(surf, color, (cx - 8, cy + 6), (cx - 3, cy + 2), 1)
    pygame.draw.line(surf, color, (cx + 8, cy + 6), (cx + 3, cy + 2), 1)
    # Small nodes at circuit endpoints
    pygame.draw.circle(surf, color, (cx, cy - 3), 2)
    pygame.draw.circle(surf, color, (cx - 3, cy + 2), 2)
    pygame.draw.circle(surf, color, (cx + 3, cy + 2), 2)
    # "AI" text centered
    font = load_font("dejavusans", 8, bold=True)
    txt = font.render("AI", True, color)
    surf.blit(txt, (cx - txt.get_width() // 2, cy + 1))
    screen.blit(surf, (x, y))


def draw_ai_badges(screen, ai_controllers):
    """Draw 1 or 2 AI badges in the top-right corner during gameplay."""
    if not ai_controllers:
        return
    colors = [(60, 255, 60), (160, 255, 60)]
    for i, _ in enumerate(ai_controllers[:2]):
        bx = SCREEN_WIDTH - 30 - i * 28
        draw_ai_badge(screen, bx, 4, colors[i % len(colors)])


def draw_hud(screen, players, game_distance, flare_timer, two_player):
    from core.fonts import FONT_HUD, FONT_HUD_SM

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
        bar_h = 12
        pygame.draw.rect(screen, (32, 32, 42), (px + 10, 34, bar_w, bar_h))
        fill_w = int(bar_w * heat_pct / 100)
        if fill_w > 0:
            bar_col = NEON_MAGENTA if heat_pct > 80 else player.color_accent
            pygame.draw.rect(screen, bar_col, (px + 10, 34, fill_w, bar_h))
            if heat_pct >= 100:
                pygame.draw.rect(screen, SOLAR_WHITE, (px + 10, 34, fill_w, bar_h), 1)

        spd = FONT_HUD_SM.render(f"{int(player.speed * 10)} km/h", True, SOLAR_WHITE)
        screen.blit(spd, (px + 10, 50))

        score_t = FONT_HUD_SM.render(f"Score: {player.score}", True, COIN_GOLD)
        screen.blit(score_t, (px + 10, 68))
        coin_t = FONT_HUD_SM.render(f"x{player.coins}", True, COIN_GOLD)
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

    dist_t = FONT_HUD.render(f"{game_distance:.1f} km", True, SOLAR_WHITE)
    screen.blit(dist_t, (SCREEN_WIDTH // 2 - dist_t.get_width() // 2, 12))

    if flare_timer < 180:
        warn = FONT_HUD.render("SOLAR FLARE!", True, SOLAR_YELLOW)
        screen.blit(warn, (SCREEN_WIDTH // 2 - warn.get_width() // 2, 38))
