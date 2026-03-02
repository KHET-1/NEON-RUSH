import pygame
import math
import random

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, NEON_CYAN, NEON_MAGENTA,
    DARK_PANEL, SOLAR_WHITE, SOLAR_YELLOW, COIN_GOLD,
    SHIELD_BLUE, MAGNET_PURPLE, SLOWMO_GREEN,
    MULTISHOT_ORANGE, ROCKETS_RED, ORBIT8_PURPLE,
)
from core.fonts import load_font


# Internal tick counter for V2 animations
_hud_tick = 0


# Cache for V2 gradient panel backgrounds (keyed by (w, h))
_panel_grad_cache = {}


def _get_panel_gradient(w, h):
    """Pre-render dark gradient panel background, cached by size."""
    key = (w, h)
    if key not in _panel_grad_cache:
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            t = y / max(1, h - 1)
            r = int(5 + 8 * t)
            g = int(2 + 4 * t)
            b = int(10 + 15 * t)
            a = int(200 - 15 * t)
            pygame.draw.line(surf, (r, g, b, a), (0, y), (w - 1, y))
        _panel_grad_cache[key] = surf
    return _panel_grad_cache[key]


def _draw_corner_brackets(surface, rect, color, bracket_len=14, thickness=2):
    """V3: Draw 4 L-shaped corner brackets instead of a full rect border."""
    x, y, w, h = rect.x, rect.y, rect.w, rect.h
    bl = bracket_len
    # Top-left
    pygame.draw.line(surface, color, (x, y), (x + bl, y), thickness)
    pygame.draw.line(surface, color, (x, y), (x, y + bl), thickness)
    # Top-right
    pygame.draw.line(surface, color, (x + w - 1, y), (x + w - bl - 1, y), thickness)
    pygame.draw.line(surface, color, (x + w - 1, y), (x + w - 1, y + bl), thickness)
    # Bottom-left
    pygame.draw.line(surface, color, (x, y + h - 1), (x + bl, y + h - 1), thickness)
    pygame.draw.line(surface, color, (x, y + h - 1), (x, y + h - bl - 1), thickness)
    # Bottom-right
    pygame.draw.line(surface, color, (x + w - 1, y + h - 1), (x + w - bl - 1, y + h - 1), thickness)
    pygame.draw.line(surface, color, (x + w - 1, y + h - 1), (x + w - 1, y + h - bl - 1), thickness)


def draw_panel(surface, rect, color=(0, 0, 0, 200), border_color=NEON_CYAN, border=2, tier=1):
    if tier >= 3:
        # V3: Gradient bg + corner bracket frame
        grad = _get_panel_gradient(rect.w, rect.h)
        surface.blit(grad, rect)
        _draw_corner_brackets(surface, rect, border_color, bracket_len=16, thickness=2)
        # Subtle dim inner border
        pygame.draw.rect(surface, (*border_color[:3], 25),
                         (rect.x + 1, rect.y + 1, rect.w - 2, rect.h - 2), 1)
    elif tier >= 2:
        # V2: Cached gradient background
        grad = _get_panel_gradient(rect.w, rect.h)
        surface.blit(grad, rect)
        # 2-layer neon border (cleaner, less cluttered than 3-layer)
        pygame.draw.rect(surface, (*border_color[:3], 50),
                         (rect.x - 1, rect.y - 1, rect.w + 2, rect.h + 2), 3)
        pygame.draw.rect(surface, border_color,
                         (rect.x, rect.y, rect.w, rect.h), 2)
    else:
        panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
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


def _draw_player_panel(screen, player, px, tier, compact, tick):
    """Draw one player's HUD panel: name, lives, heat bar, speed, score."""
    from core.fonts import FONT_HUD_SM
    if FONT_HUD_SM is None:
        return

    panel_h = 80 if compact else 100
    bar_h = 10 if compact else 12

    spd_val = abs(player.speed) if compact else player.speed
    if tier >= 2:
        speed_t = min(1.0, spd_val / 12.0)
        border_col = tuple(
            int(player.color_accent[i] * (1 - speed_t) + NEON_MAGENTA[i] * speed_t)
            for i in range(3)
        )
    else:
        border_col = player.color_accent

    panel_color = (0, 0, 0, 180) if compact else DARK_PANEL
    draw_panel(screen, pygame.Rect(px, 8, 190, panel_h), panel_color, border_col, tier=tier)

    if tier >= 2:
        _draw_text_glow(screen, FONT_HUD_SM, player.name, player.color_accent,
                        px + 8, 12, accent_color=NEON_CYAN)
    else:
        label = FONT_HUD_SM.render(player.name, True, player.color_accent)
        screen.blit(label, (px + 8, 12))

    draw_lives_icons(screen, player, px + 55, 14)

    # Heat bar
    heat_pct = min(100, int(player.heat))
    bar_w = 170
    pygame.draw.rect(screen, (32, 32, 42), (px + 10, 34, bar_w, bar_h))
    fill_w = int(bar_w * heat_pct / 100)
    if fill_w > 0:
        bar_col = NEON_MAGENTA if heat_pct > 80 else player.color_accent
        pygame.draw.rect(screen, bar_col, (px + 10, 34, fill_w, bar_h))

        if tier >= 2:
            flow_rate = 0.1 if compact else 0.12
            flow_range = 0.3 if compact else 0.45
            flow_min = 4 if compact else 6
            flow_div = 4 if compact else 3
            flow_x = int(math.sin(tick * flow_rate) * fill_w * flow_range)
            flow_w = max(flow_min, fill_w // flow_div)
            flow_start = px + 10 + max(0, min(fill_w - flow_w, fill_w // 2 + flow_x))
            if compact:
                flow_surf = pygame.Surface((flow_w, bar_h), pygame.SRCALPHA)
                flow_surf.fill((255, 255, 255, 40))
                screen.blit(flow_surf, (flow_start, 34))
            else:
                pygame.draw.rect(screen, (255, 255, 255, 80),
                                 (flow_start, 34, flow_w, bar_h))

            if heat_pct > 80:
                glow_rate = 0.15 if compact else 0.2
                glow_max = 80 if compact else 140
                glow_pulse = 0.5 + 0.5 * math.sin(tick * glow_rate)
                glow_a = max(0, min(255, int(glow_max * glow_pulse)))
                pygame.draw.rect(screen, (*NEON_MAGENTA[:3], glow_a),
                                 (px + 9, 33, fill_w + 2, bar_h + 2), 2)

        if not compact and heat_pct >= 100:
            pygame.draw.rect(screen, SOLAR_WHITE, (px + 10, 34, fill_w, bar_h), 1)

    # V3 heat fragment dots
    if tier >= 3 and heat_pct > 50:
        frag_count = min(8, (heat_pct - 50) // 6)
        for fi in range(frag_count):
            fx = px + 12 + fi * 22 + random.randint(-2, 2)
            fy = 30 + random.randint(-3, -1)
            fc = NEON_MAGENTA if heat_pct > 80 else player.color_accent
            pygame.draw.circle(screen, (*fc[:3], 180), (fx, fy), 2)

    # Speed + score text
    spd_y = 48 if compact else 50
    score_y = 64 if compact else 68
    spd_display = int(spd_val * 10)

    if compact:
        if tier >= 2 and FONT_HUD_SM:
            _draw_text_glow(screen, FONT_HUD_SM, f"{spd_display} km/h",
                            SOLAR_WHITE, px + 10, spd_y, accent_color=player.color_accent)
            _draw_text_glow(screen, FONT_HUD_SM, f"Score: {player.score}  x{player.coins}",
                            COIN_GOLD, px + 10, score_y, accent_color=(200, 180, 0))
        elif FONT_HUD_SM:
            spd_t = FONT_HUD_SM.render(f"{spd_display} km/h", True, SOLAR_WHITE)
            screen.blit(spd_t, (px + 10, spd_y))
            score_t = FONT_HUD_SM.render(f"Score: {player.score}  x{player.coins}", True, COIN_GOLD)
            screen.blit(score_t, (px + 10, score_y))
    else:
        if tier >= 3 and FONT_HUD_SM:
            spd_str = f"{spd_display} km/h"
            ghost = FONT_HUD_SM.render(spd_str, True, player.color_accent)
            ghost.set_alpha(90)
            screen.blit(ghost, (px + 11, spd_y + 1))
            main_t = FONT_HUD_SM.render(spd_str, True, SOLAR_WHITE)
            screen.blit(main_t, (px + 10, spd_y))
            _draw_text_glow(screen, FONT_HUD_SM, f"Score: {player.score}",
                            COIN_GOLD, px + 10, score_y, accent_color=(200, 180, 0))
        elif tier >= 2:
            _draw_text_glow(screen, FONT_HUD_SM, f"{spd_display} km/h",
                            SOLAR_WHITE, px + 10, spd_y, accent_color=player.color_accent)
            _draw_text_glow(screen, FONT_HUD_SM, f"Score: {player.score}",
                            COIN_GOLD, px + 10, score_y, accent_color=(200, 180, 0))
        else:
            spd_t = FONT_HUD_SM.render(f"{spd_display} km/h", True, SOLAR_WHITE)
            screen.blit(spd_t, (px + 10, spd_y))
            score_t = FONT_HUD_SM.render(f"Score: {player.score}", True, COIN_GOLD)
            screen.blit(score_t, (px + 10, score_y))

        # Coin icon + count
        coin_t = FONT_HUD_SM.render(f"x{player.coins}", True, COIN_GOLD)
        pygame.draw.circle(screen, COIN_GOLD, (px + 125, 76), 5)
        pygame.draw.circle(screen, (255, 240, 150), (px + 125, 76), 3)
        screen.blit(coin_t, (px + 133, 68))


def _draw_powerup_indicators(screen, player, px, pup_y, tier):
    """Draw active powerup indicators for one player."""
    from core.fonts import FONT_HUD_SM
    pup_x = px + 10

    if tier >= 3:
        if player.shield:
            _draw_powerup_icon_pentagon(screen, pup_x, pup_y, SHIELD_BLUE)
            pup_x += 18
        if player.magnet:
            _draw_powerup_icon_horseshoe(screen, pup_x, pup_y, MAGNET_PURPLE)
            pup_x += 18
        if player.slowmo:
            _draw_powerup_icon_clock(screen, pup_x, pup_y, SLOWMO_GREEN)
            pup_x += 18
        if getattr(player, 'multishot', False):
            _draw_powerup_icon_multi(screen, pup_x, pup_y, MULTISHOT_ORANGE)
            pup_x += 18
        if getattr(player, 'rockets', False):
            _draw_powerup_icon_rocket(screen, pup_x, pup_y, ROCKETS_RED)
            pup_x += 18
        if getattr(player, 'orbit8', False):
            _draw_powerup_icon_orbit(screen, pup_x, pup_y, ORBIT8_PURPLE)
    else:
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
            pup_x += 48
        if getattr(player, 'multishot', False):
            s = FONT_HUD_SM.render("MULTI", True, MULTISHOT_ORANGE)
            screen.blit(s, (pup_x, pup_y))
            pup_x += 52
        if getattr(player, 'rockets', False):
            s = FONT_HUD_SM.render("ROCKETS", True, ROCKETS_RED)
            screen.blit(s, (pup_x, pup_y))
            pup_x += 65
        if getattr(player, 'orbit8', False):
            s = FONT_HUD_SM.render("ORBIT", True, ORBIT8_PURPLE)
            screen.blit(s, (pup_x, pup_y))


def _draw_game_info(screen, game_distance, flare_timer, tier, level_label, compact):
    """Draw distance, level label, flare warning, and controls overlay."""
    from core.fonts import FONT_HUD, FONT_HUD_SM
    if FONT_HUD is None:
        return

    if level_label and FONT_HUD_SM:
        if tier >= 2:
            lbl_w = FONT_HUD_SM.size(level_label)[0]
            _draw_text_glow(screen, FONT_HUD_SM, level_label,
                            NEON_CYAN, SCREEN_WIDTH // 2 - lbl_w // 2, 2,
                            accent_color=NEON_MAGENTA)
        else:
            lbl_t = FONT_HUD_SM.render(level_label, True, NEON_CYAN)
            screen.blit(lbl_t, (SCREEN_WIDTH // 2 - lbl_t.get_width() // 2, 2))

    dist_text = f"{game_distance:.1f} km"
    dist_y = 16 if level_label else 12
    if tier >= 2:
        if FONT_HUD:
            dist_w = FONT_HUD.size(dist_text)[0]
        else:
            dist_w = 80
        _draw_text_glow(screen, FONT_HUD, dist_text,
                        SOLAR_WHITE, SCREEN_WIDTH // 2 - dist_w // 2, dist_y, accent_color=NEON_CYAN)
    else:
        dist_t = FONT_HUD.render(dist_text, True, SOLAR_WHITE)
        screen.blit(dist_t, (SCREEN_WIDTH // 2 - dist_t.get_width() // 2, dist_y))

    if not compact and flare_timer < 180:
        warn = FONT_HUD.render("SOLAR FLARE!", True, SOLAR_YELLOW)
        screen.blit(warn, (SCREEN_WIDTH // 2 - warn.get_width() // 2, 38))

    if not compact:
        draw_controls_overlay(screen)


def draw_hud(screen, players, game_distance, flare_timer, two_player, tier=1, compact=False,
             level_label=None):
    global _hud_tick
    _hud_tick += 1

    for idx, player in enumerate(players):
        if not player.alive and two_player:
            continue
        px = 8 if idx == 0 else SCREEN_WIDTH - 200
        if not two_player:
            px = 8

        _draw_player_panel(screen, player, px, tier, compact, _hud_tick)

        if not compact:
            _draw_powerup_indicators(screen, player, px, 88, tier)

    _draw_game_info(screen, game_distance, flare_timer, tier, level_label, compact)


# --- V3 Powerup Icon Helpers (12x12 shapes) ---

def _draw_powerup_icon_pentagon(screen, x, y, color):
    """Shield icon: small pentagon."""
    cx, cy = x + 6, y + 6
    pts = []
    for i in range(5):
        a = -math.pi / 2 + i * 2 * math.pi / 5
        pts.append((cx + int(math.cos(a) * 5), cy + int(math.sin(a) * 5)))
    pygame.draw.polygon(screen, color, pts)
    pygame.draw.polygon(screen, (255, 255, 255), pts, 1)


def _draw_powerup_icon_horseshoe(screen, x, y, color):
    """Magnet icon: U-shape."""
    pygame.draw.arc(screen, color, (x + 1, y + 2, 10, 10), math.pi, 2 * math.pi, 2)
    pygame.draw.line(screen, color, (x + 1, y + 7), (x + 1, y + 12), 2)
    pygame.draw.line(screen, color, (x + 11, y + 7), (x + 11, y + 12), 2)


def _draw_powerup_icon_clock(screen, x, y, color):
    """Slow-mo icon: clock face."""
    cx, cy = x + 6, y + 6
    pygame.draw.circle(screen, color, (cx, cy), 5, 1)
    pygame.draw.line(screen, color, (cx, cy), (cx, cy - 4), 1)
    pygame.draw.line(screen, color, (cx, cy), (cx + 3, cy), 1)


def _draw_powerup_icon_multi(screen, x, y, color):
    """Multishot icon: three dots in spread pattern."""
    pygame.draw.circle(screen, color, (x + 3, y + 9), 2)
    pygame.draw.circle(screen, color, (x + 6, y + 3), 2)
    pygame.draw.circle(screen, color, (x + 9, y + 9), 2)


def _draw_powerup_icon_rocket(screen, x, y, color):
    """Rockets icon: upward arrow."""
    cx = x + 6
    pts = [(cx, y + 1), (cx + 5, y + 7), (cx + 2, y + 7),
           (cx + 2, y + 11), (cx - 2, y + 11), (cx - 2, y + 7), (cx - 5, y + 7)]
    pygame.draw.polygon(screen, color, pts)


def _draw_powerup_icon_orbit(screen, x, y, color):
    """Orbit icon: ring with dot."""
    cx, cy = x + 6, y + 6
    pygame.draw.circle(screen, color, (cx, cy), 5, 1)
    pygame.draw.circle(screen, color, (cx + 4, cy - 2), 2)
