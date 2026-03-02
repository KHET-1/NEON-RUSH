import pygame
import math

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, SOLAR_YELLOW, DESERT_ORANGE,
    NEON_MAGENTA, NEON_CYAN, COIN_GOLD, SOLAR_WHITE,
    DIFF_EASY, DIFF_NORMAL, DIFF_HARD, DIFFICULTY_SETTINGS,
    DASH_LENGTH, DASH_GAP, ROAD_LEFT, ROAD_WIDTH, ROAD_CENTER, SLOWMO_GREEN,
)
from core.fonts import load_font
from core.hud import draw_panel
from core.highscores import load_highscores, save_highscores
import core.sound as _snd
from core.sound import play_sfx

# Backward-compatible re-exports (moved to core.combo)
from core.combo import ComboTracker, MilestoneTracker


class HighScoreEntry:
    def __init__(self, score, auto_type=False):
        self.score = score
        self.name = ""
        self.done = False
        self.auto_type = auto_type
        self._auto_frame = 0

    def handle_event(self, event):
        from core.fonts import FONT_SCORE_ENTRY
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and len(self.name) > 0:
                self._commit()
            elif event.key == pygame.K_BACKSPACE:
                self.name = self.name[:-1]
            elif len(self.name) < 3 and event.unicode.isalnum():
                self.name += event.unicode.upper()
                play_sfx("select")

    def _commit(self):
        scores = load_highscores()
        scores.append({"name": self.name, "score": self.score})
        scores.sort(key=lambda s: s["score"], reverse=True)
        save_highscores(scores[:5])
        play_sfx("highscore")
        self.done = True

    def draw(self, screen, tick):
        from core.fonts import FONT_HUD_LG, FONT_SUBTITLE, FONT_HUD, FONT_HUD_SM, FONT_SCORE_ENTRY
        from core.constants import WHITE

        # Auto-type logic: inject "AI" then confirm
        if self.auto_type and not self.done:
            self._auto_frame += 1
            if self._auto_frame == 30 and len(self.name) < 1:
                self.name += "A"
                play_sfx("select")
            elif self._auto_frame == 60 and len(self.name) < 2:
                self.name += "I"
                play_sfx("select")
            elif self._auto_frame == 90 and len(self.name) >= 2:
                self._commit()

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))

        pw, ph = 400, 250
        px, py = (SCREEN_WIDTH - pw) // 2, (SCREEN_HEIGHT - ph) // 2
        draw_panel(screen, pygame.Rect(px, py, pw, ph), (0, 0, 20, 220), COIN_GOLD, 3)

        title = FONT_HUD_LG.render("NEW HIGH SCORE!", True, COIN_GOLD)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, py + 20))

        score_t = FONT_SUBTITLE.render(f"{self.score}", True, SOLAR_WHITE)
        screen.blit(score_t, (SCREEN_WIDTH // 2 - score_t.get_width() // 2, py + 65))

        prompt = FONT_HUD.render("Enter your initials:", True, NEON_CYAN)
        screen.blit(prompt, (SCREEN_WIDTH // 2 - prompt.get_width() // 2, py + 105))

        display_name = self.name
        if len(display_name) < 3 and (tick // 20) % 2:
            display_name += "_"

        total_w = 3 * 50 + 2 * 10
        start_x = SCREEN_WIDTH // 2 - total_w // 2
        for i in range(3):
            bx = start_x + i * 60
            by = py + 145
            color = COIN_GOLD if i < len(self.name) else (60, 60, 70)
            pygame.draw.rect(screen, color, (bx, by, 46, 56), 2)
            if i < len(display_name):
                char = FONT_SCORE_ENTRY.render(display_name[i], True, SOLAR_WHITE)
                screen.blit(char, (bx + 23 - char.get_width() // 2, by + 4))

        hint_text = "AI typing..." if self.auto_type else "ENTER to confirm"
        hint = FONT_HUD_SM.render(hint_text, True, (120, 120, 140))
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, py + 215))


def _draw_checkstamp(screen, x, y, checked, tick):
    """Draw a custom neon checkmark stamp — procedural glow box with animated check."""
    sz = 16
    # Box outline: cyan glow when checked, dim gray when not
    if checked:
        pulse = 0.7 + 0.3 * math.sin(tick * 0.08)
        box_color = (0, int(200 * pulse), int(255 * pulse))
        # Outer glow
        glow_surf = pygame.Surface((sz + 8, sz + 8), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*NEON_CYAN, 35), (0, 0, sz + 8, sz + 8), border_radius=4)
        screen.blit(glow_surf, (x - 4, y - 4))
    else:
        box_color = (60, 60, 80)

    # Main box
    pygame.draw.rect(screen, (20, 20, 30), (x, y, sz, sz), border_radius=3)
    pygame.draw.rect(screen, box_color, (x, y, sz, sz), 2, border_radius=3)

    if checked:
        # Draw the checkmark — two strokes forming a ✓
        # Short down-stroke then long up-stroke
        check_color = NEON_CYAN
        p1 = (x + 3, y + 8)     # start
        p2 = (x + 6, y + 12)    # bottom of check
        p3 = (x + 13, y + 4)    # top of check
        pygame.draw.line(screen, check_color, p1, p2, 2)
        pygame.draw.line(screen, check_color, p2, p3, 2)
        # Bright center dot at the checkmark vertex
        pygame.draw.circle(screen, (200, 255, 255), p2, 1)


# --- Menu navigation constants ---
MENU_ROW_MODES = 0
MENU_ROW_DIFF = 1
MENU_ROW_AI_REWARD = 2
MENU_ROW_RENDER = 3
MENU_ROW_TOGGLES = 4       # Sound / Evolution / Logging side-by-side
MENU_NUM_ROWS = 5

# Items per row (for LEFT/RIGHT bounds)
_MENU_COLS = {
    MENU_ROW_MODES: 5,       # SOLO, 2P, P+AI, AI, AI+AI
    MENU_ROW_DIFF: 3,        # EASY, NORMAL, HARD
    MENU_ROW_AI_REWARD: 4,   # off, x2, x4, x8
    MENU_ROW_RENDER: 1,      # single cycler
    MENU_ROW_TOGGLES: 3,     # Sound, Evolution, Logging
}

# Y positions of each row (for cursor drawing)
_ROW_Y = {
    MENU_ROW_MODES: 220,
    MENU_ROW_DIFF: 258,
    MENU_ROW_AI_REWARD: 296,
    MENU_ROW_RENDER: 328,
    MENU_ROW_TOGGLES: 358,
}


def _draw_row_cursor(screen, y, tick):
    """Draw a pulsing neon cursor chevron at the left edge of the focused row."""
    pulse = 0.5 + 0.5 * math.sin(tick * 0.1)
    alpha = int(160 + 95 * pulse)
    color = (*NEON_CYAN, alpha)

    # Chevron: two lines forming >
    chev_x = 38
    chev_y = y + 3
    sz = 6
    surf = pygame.Surface((sz * 2 + 4, sz * 2 + 4), pygame.SRCALPHA)
    pts = [(2, 2), (sz * 2, sz + 2), (2, sz * 2 + 2)]
    pygame.draw.lines(surf, color, False, pts, 3)
    # Glow echo
    pygame.draw.lines(surf, (*NEON_MAGENTA, int(50 * pulse)), False, pts, 5)
    screen.blit(surf, (chev_x, chev_y))


def _draw_neon_title(screen, text, font, cx, y, tick, scale=1.0):
    """Procedural neon text: magenta bloom → cyan inner → white core + pulse."""
    pulse = 0.6 + 0.4 * math.sin(tick * 0.05)
    # Cycle hue between cyan and magenta
    mg_a = int(160 * pulse)
    cy_a = int(180 * (1.0 - pulse * 0.4))

    # Layer 1: magenta bloom (8 directions, 4px offset)
    bloom = font.render(text, True, NEON_MAGENTA)
    bloom.set_alpha(mg_a)
    bx = cx - bloom.get_width() // 2
    for dx, dy in [(-4, -4), (4, -4), (-4, 4), (4, 4),
                   (-4, 0), (4, 0), (0, -4), (0, 4)]:
        screen.blit(bloom, (bx + dx, y + dy))

    # Layer 2: cyan inner glow (4 directions, 2px offset)
    inner = font.render(text, True, NEON_CYAN)
    inner.set_alpha(cy_a)
    for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
        screen.blit(inner, (bx + dx, y + dy))

    # Layer 3: white core
    core = font.render(text, True, (255, 255, 255))
    screen.blit(core, (bx, y))

    # Neon underline pulsing cyan↔magenta
    tw = font.size(text)[0]
    ul_y = y + font.get_height() + 2
    line_color = (
        int(NEON_CYAN[0] * (1 - pulse) + NEON_MAGENTA[0] * pulse),
        int(NEON_CYAN[1] * (1 - pulse) + NEON_MAGENTA[1] * pulse),
        int(NEON_CYAN[2] * (1 - pulse) + NEON_MAGENTA[2] * pulse),
    )
    pygame.draw.line(screen, line_color,
                     (cx - tw // 2, ul_y), (cx + tw // 2, ul_y), 2)
    # Glow echo
    glow_line = pygame.Surface((tw, 4), pygame.SRCALPHA)
    glow_line.fill((*line_color, int(50 * pulse)))
    screen.blit(glow_line, (cx - tw // 2, ul_y - 1))


def draw_title(screen, tick, selected_diff=DIFF_NORMAL, ai_reward_mult=1,
               loop_count=0, ai_frames=0, target_fps=144, dashboard=None,
               evolution_mgr=None, vsync=True, logging_enabled=False,
               sound_enabled=True, menu_row=0, menu_col=0):
    from core.fonts import FONT_TITLE, FONT_NEON_TITLE, FONT_SUBTITLE, FONT_HUD, FONT_HUD_SM, FONT_HUD_SM_BOLD

    t = (tick % 180) / 180
    r = int(10 + 8 * math.sin(t * math.pi * 2))
    g = int(4 + 4 * math.sin(t * math.pi * 2 + 0.5))
    b = int(22 + 16 * math.sin(t * math.pi * 2 + 1))
    screen.fill((r, g, b))

    pygame.draw.rect(screen, (28, 28, 38), (ROAD_LEFT, 0, ROAD_WIDTH, SCREEN_HEIGHT))
    offset = int(tick * 2) % (DASH_LENGTH + DASH_GAP)
    y = -DASH_LENGTH + offset
    while y < SCREEN_HEIGHT:
        pygame.draw.line(screen, NEON_MAGENTA, (ROAD_CENTER, y), (ROAD_CENTER, y + DASH_LENGTH), 2)
        y += DASH_LENGTH + DASH_GAP

    cx = SCREEN_WIDTH // 2

    # Neon title with procedural glow
    neon_font = FONT_NEON_TITLE or FONT_TITLE
    _draw_neon_title(screen, "NEON RUSH", neon_font, cx, 72, tick)

    # Subtitle with subtle neon treatment
    sub_pulse = 0.7 + 0.3 * math.sin(tick * 0.04 + 1.0)
    sub = FONT_SUBTITLE.render("DESERT VELOCITY", True, SOLAR_YELLOW)
    sub.set_alpha(int(200 + 55 * sub_pulse))
    screen.blit(sub, (cx - sub.get_width() // 2, 160))

    # === Row 0: Game mode options ===
    modes_data = [
        ("SOLO", NEON_CYAN),
        ("2-PLAYER", NEON_MAGENTA),
        ("PLAYER+AI", (100, 255, 100)),
        ("AI SOLO", (100, 255, 100)),
        ("AI+AI", (100, 255, 100)),
    ]
    is_focused = menu_row == MENU_ROW_MODES
    total_w = sum(FONT_HUD_SM.size(m[0])[0] for m in modes_data) + 12 * (len(modes_data) - 1)
    mx = cx - total_w // 2
    for i, (label, base_color) in enumerate(modes_data):
        is_col_sel = is_focused and menu_col == i
        if is_col_sel:
            font = FONT_HUD_SM_BOLD
            color = base_color
            text = f"> {label} <"
        elif is_focused:
            font = FONT_HUD_SM
            color = tuple(max(40, c // 2) for c in base_color)
            text = label
        else:
            # Blink when not focused
            if (tick // 30) % 2:
                font = FONT_HUD_SM
                color = base_color
                text = label
            else:
                font = FONT_HUD_SM
                color = (0, 0, 0, 0)
                text = ""
        if text:
            mt = font.render(text, True, color)
            screen.blit(mt, (mx, 220))
        # Advance by the base label width to keep spacing stable
        mx += FONT_HUD_SM.size(label)[0] + 12

    # === Row 1: Difficulty selector ===
    diff_y = 258
    diff_list = [DIFF_EASY, DIFF_NORMAL, DIFF_HARD]
    is_focused = menu_row == MENU_ROW_DIFF
    diff_label = FONT_HUD_SM.render("Difficulty:", True,
                                     (200, 200, 220) if is_focused else (150, 150, 170))
    screen.blit(diff_label, (cx - 150, diff_y))
    for i, d in enumerate(diff_list):
        ds = DIFFICULTY_SETTINGS[d]
        is_selected = selected_diff == d
        if is_selected:
            text = f"> {ds['label']} <"
        else:
            text = ds['label']
        color = ds["color"] if is_selected else (80, 80, 100)
        font = FONT_HUD_SM_BOLD if is_selected else FONT_HUD_SM
        dt = font.render(text, True, color)
        screen.blit(dt, (cx - 30 + i * 80, diff_y))

    if is_focused:
        hint = FONT_HUD_SM.render("LEFT/RIGHT to change", True, NEON_CYAN)
    else:
        hint = FONT_HUD_SM.render("(LEFT/RIGHT to change)", True, (100, 100, 120))
    screen.blit(hint, (cx - hint.get_width() // 2, diff_y + 18))

    # === Row 2: AI Reward multiplier ===
    ai_y = 296
    is_focused = menu_row == MENU_ROW_AI_REWARD
    ai_label = FONT_HUD_SM.render("AI Reward:", True,
                                   (200, 200, 220) if is_focused else (150, 150, 170))
    screen.blit(ai_label, (cx - 150, ai_y))
    ai_vals = [1, 2, 4, 8]
    ai_labels = ["off", "x2", "x4", "x8"]
    for i, (val, lbl) in enumerate(zip(ai_vals, ai_labels)):
        is_active = ai_reward_mult == val
        if is_active:
            text = f"> {lbl} <"
            color = (100, 255, 100)
            font = FONT_HUD_SM_BOLD
        else:
            text = lbl
            color = (80, 80, 100)
            font = FONT_HUD_SM
        rt = font.render(text, True, color)
        screen.blit(rt, (cx - 40 + i * 70, ai_y))

    # === Row 3: Render FPS cap + VSync indicator ===
    fps_y = 328
    is_focused = menu_row == MENU_ROW_RENDER
    fps_label = FONT_HUD_SM.render("Render:", True,
                                    (200, 200, 220) if is_focused else (150, 150, 170))
    screen.blit(fps_label, (cx - 150, fps_y))
    if vsync:
        fps_display = "VSync" if target_fps == 0 else f"{target_fps} FPS + VSync"
    else:
        fps_display = "UNL" if target_fps == 0 else f"{target_fps} FPS"
    fps_color = NEON_CYAN if is_focused else (0, 200, 220)
    fps_val_t = FONT_HUD_SM_BOLD.render(f"< {fps_display} >", True, fps_color)
    screen.blit(fps_val_t, (cx - fps_val_t.get_width() // 2, fps_y))

    # === Row 4: Toggles — Sound / Evolution / Logging side-by-side ===
    tog_y = 358
    is_focused = menu_row == MENU_ROW_TOGGLES
    evo_enabled = evolution_mgr.enabled if evolution_mgr else False
    toggles = [
        ("Sound", sound_enabled, NEON_CYAN),
        ("Evolution", evo_enabled, SOLAR_YELLOW),
        ("Logging", logging_enabled, NEON_CYAN),
    ]
    col_spacing = 130
    tog_start_x = cx - col_spacing  # center the 3 columns
    for i, (label, checked, active_color) in enumerate(toggles):
        tx = tog_start_x + i * col_spacing
        is_col_sel = is_focused and menu_col == i
        color = active_color if checked else (80, 80, 100)
        if is_col_sel:
            color = active_color if checked else (150, 150, 170)
        font = FONT_HUD_SM_BOLD if checked or is_col_sel else FONT_HUD_SM
        lt = font.render(label, True, color)
        screen.blit(lt, (tx + 20, tog_y))
        _draw_checkstamp(screen, tx, tog_y + 1, checked, tick)

    # === Row cursor indicator (pulsing chevron) ===
    row_y = _ROW_Y.get(menu_row, 225)
    _draw_row_cursor(screen, row_y, tick)

    # Navigation hint
    nav_hint = FONT_HUD_SM.render("UP/DOWN = Navigate   LEFT/RIGHT = Change   ENTER = Toggle   M = Mute", True, (100, 100, 120))
    screen.blit(nav_hint, (cx - nav_hint.get_width() // 2, 388))

    # Controls hints (condensed)
    c1 = FONT_HUD_SM.render("P1: WASD + Shift   Solo: WASD/Arrows   P2: Arrows + R.Shift", True, (120, 120, 140))
    screen.blit(c1, (cx - c1.get_width() // 2, 406))

    # Dashboard or High scores
    if dashboard and dashboard.active:
        dashboard.draw(screen, tick)
    else:
        scores = load_highscores()
        if scores:
            hs = FONT_HUD_SM.render("HIGH SCORES", True, COIN_GOLD)
            screen.blit(hs, (cx - hs.get_width() // 2, 440))
            for i, entry in enumerate(scores[:3]):
                txt = FONT_HUD_SM.render(f"{i + 1}. {entry['name']} - {entry['score']}", True, SOLAR_WHITE)
                screen.blit(txt, (cx - txt.get_width() // 2, 460 + i * 20))

    # Loop / AI counter in banner area
    if loop_count > 0 or ai_frames > 0:
        parts = [f"Loops: {loop_count:,}"]
        if ai_frames > 0:
            parts.append(f"AI Frames: {ai_frames:,}")
        counter_str = "  |  ".join(parts)
        ct = FONT_HUD_SM.render(counter_str, True, (80, 120, 80))
        screen.blit(ct, (cx - ct.get_width() // 2, 528))

    # Footer
    foot = FONT_HUD_SM.render("ESC = Quit   F11 = Fullscreen   F2 = 2x Scale", True, (80, 80, 100))
    screen.blit(foot, (cx - foot.get_width() // 2, 578))


def draw_paused(screen):
    from core.fonts import FONT_HUD_LG, FONT_HUD

    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))
    pw, ph = 300, 180
    px, py = (SCREEN_WIDTH - pw) // 2, (SCREEN_HEIGHT - ph) // 2
    draw_panel(screen, pygame.Rect(px, py, pw, ph), (0, 0, 20, 220), NEON_CYAN, 3)
    title = FONT_HUD_LG.render("PAUSED", True, NEON_CYAN)
    screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, py + 30))
    r = FONT_HUD.render("P = Resume", True, SOLAR_WHITE)
    screen.blit(r, (SCREEN_WIDTH // 2 - r.get_width() // 2, py + 90))
    q = FONT_HUD.render("R = Restart   ESC = Quit", True, (150, 150, 170))
    screen.blit(q, (SCREEN_WIDTH // 2 - q.get_width() // 2, py + 120))


def draw_gameover(screen, players, game_distance, tick, two_player,
                  fps_snapshots=None, fps_total_frames=0, continues_left=0):
    from core.fonts import FONT_TITLE, FONT_HUD, FONT_HUD_SM

    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))

    has_graph = fps_snapshots and len(fps_snapshots) >= 2
    extra_h = 100 if has_graph else 0
    pw = 420
    ph = (300 if two_player else 260) + extra_h
    px, py = (SCREEN_WIDTH - pw) // 2, (SCREEN_HEIGHT - ph) // 2 - 20
    draw_panel(screen, pygame.Rect(px, py, pw, ph), (0, 0, 20, 220), NEON_MAGENTA, 3)

    title = FONT_TITLE.render("GAME OVER", True, NEON_MAGENTA)
    screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, py + 15))

    y_off = py + 85
    for p in players:
        if two_player:
            nm = FONT_HUD.render(p.name, True, p.color_accent)
            screen.blit(nm, (px + 30, y_off))
        col_x = px + (80 if two_player else 30)
        dist = FONT_HUD_SM.render(f"Distance: {p.distance:.1f} km", True, SOLAR_WHITE)
        screen.blit(dist, (col_x, y_off))
        sc = FONT_HUD.render(f"Score: {p.score}", True, COIN_GOLD)
        screen.blit(sc, (col_x, y_off + 20))
        cn = FONT_HUD_SM.render(f"Coins: {p.coins}", True, COIN_GOLD)
        screen.blit(cn, (col_x + 180, y_off + 22))
        y_off += 55 if two_player else 50

    if two_player:
        if players[0].score != players[1].score:
            winner = players[0] if players[0].score > players[1].score else players[1]
            wt = FONT_HUD.render(f"{winner.name} WINS!", True, winner.color_accent)
            screen.blit(wt, (SCREEN_WIDTH // 2 - wt.get_width() // 2, y_off))

    # FPS mini graph
    if has_graph:
        graph_w, graph_h = 220, 70
        graph_x = SCREEN_WIDTH // 2 - graph_w // 2
        graph_y = py + ph - 145
        # Background
        pygame.draw.rect(screen, (15, 15, 25), (graph_x, graph_y, graph_w, graph_h))
        pygame.draw.rect(screen, (60, 60, 80), (graph_x, graph_y, graph_w, graph_h), 1)

        max_fps = max(s[1] for s in fps_snapshots)
        max_time = max(s[0] for s in fps_snapshots)
        if max_fps > 0 and max_time > 0:
            points = []
            for sec, avg in fps_snapshots:
                gx = graph_x + int((sec / max_time) * (graph_w - 4)) + 2
                gy = graph_y + graph_h - 2 - int((avg / max_fps) * (graph_h - 4))
                points.append((gx, gy))
            if len(points) >= 2:
                # Draw line segments colored by FPS quality
                for j in range(len(points) - 1):
                    avg_fps = fps_snapshots[j][1]
                    if avg_fps >= 55:
                        seg_color = (60, 200, 60)
                    elif avg_fps >= 30:
                        seg_color = (255, 200, 50)
                    else:
                        seg_color = (255, 50, 40)
                    pygame.draw.line(screen, seg_color, points[j], points[j + 1], 2)

        # Label
        frames_t = FONT_HUD_SM.render(f"Frames: {fps_total_frames:,}", True, (120, 120, 140))
        screen.blit(frames_t, (graph_x, graph_y + graph_h + 2))
        fps_label = FONT_HUD_SM.render("FPS", True, (80, 80, 100))
        screen.blit(fps_label, (graph_x + graph_w - fps_label.get_width(), graph_y + graph_h + 2))

    # Continue info
    if continues_left > 0:
        cont_t = FONT_HUD_SM.render(f"Continues: {continues_left}", True, SOLAR_YELLOW)
        screen.blit(cont_t, (SCREEN_WIDTH // 2 - cont_t.get_width() // 2, py + ph - 65))

    blink = (tick // 30) % 2
    if blink:
        if continues_left > 0:
            retry = FONT_HUD.render("SPACE = Continue    ESC = Quit", True, NEON_CYAN)
        else:
            retry = FONT_HUD.render("SPACE = End    ESC = Quit", True, NEON_CYAN)
        screen.blit(retry, (SCREEN_WIDTH // 2 - retry.get_width() // 2, py + ph - 45))


def draw_victory(screen, shared_state, tick):
    """Victory screen with total stats."""
    from core.fonts import FONT_TITLE, FONT_SUBTITLE, FONT_HUD, FONT_HUD_SM

    t = (tick % 120) / 120
    r = int(10 + 20 * math.sin(t * math.pi * 2))
    g = int(5 + 15 * math.sin(t * math.pi * 2 + 1))
    b = int(30 + 25 * math.sin(t * math.pi * 2 + 2))
    screen.fill((r, g, b))

    pw, ph = 500, 380
    px, py = (SCREEN_WIDTH - pw) // 2, (SCREEN_HEIGHT - ph) // 2 - 20
    draw_panel(screen, pygame.Rect(px, py, pw, ph), (0, 0, 20, 220), SOLAR_YELLOW, 3)

    # Neon victory title
    _draw_neon_title(screen, "VICTORY!", FONT_TITLE, SCREEN_WIDTH // 2, py + 10, tick)

    sub = FONT_SUBTITLE.render("ALL BOSSES DEFEATED!", True, NEON_CYAN)
    screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, py + 85))

    if shared_state:
        y = py + 130
        evo_tier = getattr(shared_state, 'evolution_tier', 1)
        cycles = getattr(shared_state, 'cycle_count', 0)
        bosses_total = shared_state.bosses_defeated
        stats = [
            ("Total Score", str(shared_state.best_score)),
            ("Total Coins", str(shared_state.total_coins)),
            ("Distance", f"{shared_state.total_distance:.1f} km"),
            ("Bosses", f"{bosses_total}" + (f" ({cycles} cycles)" if cycles > 0 else "/3")),
            ("Evolution", f"V{evo_tier}" if evo_tier > 1 else "V1 (base)"),
        ]
        for label, value in stats:
            lt = FONT_HUD_SM.render(f"{label}:", True, (180, 180, 200))
            screen.blit(lt, (px + 40, y))
            vt = FONT_HUD.render(value, True, SOLAR_WHITE)
            screen.blit(vt, (px + 200, y - 2))
            y += 35

    blink = (tick // 25) % 2
    if blink:
        cont = FONT_HUD.render("SPACE = Continue    ESC = Title", True, NEON_CYAN)
        screen.blit(cont, (SCREEN_WIDTH // 2 - cont.get_width() // 2, py + ph - 45))
