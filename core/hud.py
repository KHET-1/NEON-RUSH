import pygame
import math

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, NEON_CYAN, NEON_MAGENTA,
    DARK_PANEL, SOLAR_WHITE, SOLAR_YELLOW, COIN_GOLD,
    SHIELD_BLUE, MAGNET_PURPLE, SLOWMO_GREEN,
)
from core.fonts import load_font


# Internal tick counter for V2 animations
_hud_tick = 0


def draw_panel(surface, rect, color=(0, 0, 0, 200), border_color=NEON_CYAN, border=2, tier=1):
    panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)

    if tier >= 2:
        # V2+: Gradient fill instead of flat black
        for y in range(rect.h):
            t = y / max(1, rect.h - 1)
            r = int(0 + 10 * t)
            g = int(0 + 5 * t)
            b = int(0 + 20 * t)
            a = int(200 - 20 * t)
            pygame.draw.line(panel, (r, g, b, a), (0, y), (rect.w - 1, y))

        # 3-layer neon border: outer glow → mid → inner solid
        # Outer glow (4px, alpha 30)
        pygame.draw.rect(panel, (*border_color[:3], 30), (0, 0, rect.w, rect.h), 4)
        # Mid (3px, alpha 60)
        pygame.draw.rect(panel, (*border_color[:3], 60), (1, 1, rect.w - 2, rect.h - 2), 3)
        # Inner solid (2px)
        pygame.draw.rect(panel, border_color, (2, 2, rect.w - 4, rect.h - 4), 2)

        # Corner accent dots
        for cx, cy in [(3, 3), (rect.w - 4, 3), (3, rect.h - 4), (rect.w - 4, rect.h - 4)]:
            pygame.draw.circle(panel, (*border_color[:3], 200), (cx, cy), 2)
    else:
        pygame.draw.rect(panel, color, (0, 0, rect.w, rect.h))
        pygame.draw.rect(panel, border_color, (0, 0, rect.w, rect.h), border)

    surface.blit(panel, rect)


def _draw_text_glow(surface, font, text, color, x, y, accent_color=None):
    """V2+ text: draw dim offset shadow in accent color, then main text on top."""
    if font is None:
        return
    if accent_color is None:
        accent_color = color
    shadow = font.render(text, True, accent_color)
    shadow.set_alpha(60)
    surface.blit(shadow, (x + 1, y + 1))
    txt = font.render(text, True, color)
    surface.blit(txt, (x, y))


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


_controls_surface = None


def draw_controls_overlay(screen):
    """Draw compact controls reference in bottom-right corner."""
    global _controls_surface
    if _controls_surface is None:
        font = load_font("dejavusans", 11)
        lines = [
            ("WASD/Arrows", "Move"),
            ("Shift/Space", "Boost"),
            ("E/Enter", "Fire"),
        ]
        line_h = 14
        pad = 6
        w = 140
        h = len(lines) * line_h + pad * 2
        _controls_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        _controls_surface.fill((0, 0, 0, 120))
        pygame.draw.rect(_controls_surface, (*NEON_CYAN[:3], 60), (0, 0, w, h), 1)
        for i, (key, action) in enumerate(lines):
            y = pad + i * line_h
            kt = font.render(key, True, NEON_CYAN)
            at = font.render(action, True, (180, 180, 190))
            _controls_surface.blit(kt, (pad, y))
            _controls_surface.blit(at, (w - pad - at.get_width(), y))
    screen.blit(_controls_surface, (SCREEN_WIDTH - 148, SCREEN_HEIGHT - 56))


def draw_hud(screen, players, game_distance, flare_timer, two_player, tier=1):
    global _hud_tick
    _hud_tick += 1

    from core.fonts import FONT_HUD, FONT_HUD_SM

    for idx, player in enumerate(players):
        if not player.alive and two_player:
            continue
        px = 8 if idx == 0 else SCREEN_WIDTH - 200
        if not two_player:
            px = 8
        panel_w, panel_h = 190, 100

        # V2+: Speed-responsive border color (cyan → magenta based on speed)
        if tier >= 2:
            speed_t = min(1.0, player.speed / 12.0)
            border_r = int(player.color_accent[0] * (1 - speed_t) + NEON_MAGENTA[0] * speed_t)
            border_g = int(player.color_accent[1] * (1 - speed_t) + NEON_MAGENTA[1] * speed_t)
            border_b = int(player.color_accent[2] * (1 - speed_t) + NEON_MAGENTA[2] * speed_t)
            border_col = (border_r, border_g, border_b)
        else:
            border_col = player.color_accent

        draw_panel(screen, pygame.Rect(px, 8, panel_w, panel_h), DARK_PANEL, border_col, tier=tier)

        if tier >= 2:
            _draw_text_glow(screen, FONT_HUD_SM, player.name, player.color_accent,
                            px + 8, 12, accent_color=NEON_CYAN)
        else:
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

            if tier >= 2:
                # V2+: Animated inner "flow" bar oscillating left-right
                flow_x = int(math.sin(_hud_tick * 0.1) * fill_w * 0.3)
                flow_w = max(4, fill_w // 4)
                flow_start = px + 10 + max(0, min(fill_w - flow_w, fill_w // 2 + flow_x))
                flow_surf = pygame.Surface((flow_w, bar_h), pygame.SRCALPHA)
                flow_surf.fill((255, 255, 255, 40))
                screen.blit(flow_surf, (flow_start, 34))

                # Pulsing glow outline at >80%
                if heat_pct > 80:
                    glow_pulse = 0.5 + 0.5 * math.sin(_hud_tick * 0.15)
                    glow_a = int(80 * glow_pulse)
                    pygame.draw.rect(screen, (*NEON_MAGENTA[:3], glow_a),
                                     (px + 9, 33, fill_w + 2, bar_h + 2), 2)

            if heat_pct >= 100:
                pygame.draw.rect(screen, SOLAR_WHITE, (px + 10, 34, fill_w, bar_h), 1)

        if tier >= 2:
            _draw_text_glow(screen, FONT_HUD_SM, f"{int(player.speed * 10)} km/h",
                            SOLAR_WHITE, px + 10, 50, accent_color=player.color_accent)
            _draw_text_glow(screen, FONT_HUD_SM, f"Score: {player.score}",
                            COIN_GOLD, px + 10, 68, accent_color=(200, 180, 0))
        else:
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

    if tier >= 2:
        _draw_text_glow(screen, FONT_HUD, f"{game_distance:.1f} km",
                        SOLAR_WHITE, SCREEN_WIDTH // 2 - 40, 12, accent_color=NEON_CYAN)
    else:
        dist_t = FONT_HUD.render(f"{game_distance:.1f} km", True, SOLAR_WHITE)
        screen.blit(dist_t, (SCREEN_WIDTH // 2 - dist_t.get_width() // 2, 12))

    if flare_timer < 180:
        warn = FONT_HUD.render("SOLAR FLARE!", True, SOLAR_YELLOW)
        screen.blit(warn, (SCREEN_WIDTH // 2 - warn.get_width() // 2, 38))

    # Controls overlay (bottom-right)
    draw_controls_overlay(screen)
