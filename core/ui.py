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
from core.sound import SFX


class ComboTracker:
    def __init__(self):
        self.count = 0
        self.timer = 0
        self.multiplier = 1
        self.display_timer = 0

    def hit(self):
        self.count += 1
        self.timer = 90
        if self.count >= 10:
            self.multiplier = 4
        elif self.count >= 5:
            self.multiplier = 3
        elif self.count >= 3:
            self.multiplier = 2
        else:
            self.multiplier = 1
        if self.multiplier > 1:
            self.display_timer = 90

    def update(self):
        if self.timer > 0:
            self.timer -= 1
            if self.timer <= 0:
                self.count = 0
                self.multiplier = 1
        if self.display_timer > 0:
            self.display_timer -= 1

    def get_bonus(self, base_score):
        return base_score * self.multiplier

    def draw(self, surface, x, y):
        if self.display_timer > 0 and self.multiplier > 1:
            alpha = min(255, self.display_timer * 6)
            scale = 1.0 + 0.3 * math.sin(self.display_timer * 0.2)
            size = int(28 * scale)
            font = load_font("dejavusans", size, bold=True)
            colors = {2: SOLAR_YELLOW, 3: DESERT_ORANGE, 4: NEON_MAGENTA}
            color = colors.get(self.multiplier, SOLAR_YELLOW)
            txt = font.render(f"COMBO x{self.multiplier}!", True, color)
            txt.set_alpha(alpha)
            surface.blit(txt, (x - txt.get_width() // 2, y))


class MilestoneTracker:
    def __init__(self):
        self.last_km = 0
        self.display_text = ""
        self.display_timer = 0
        self.display_color = SOLAR_YELLOW

    def check(self, distance):
        km = int(distance)
        if km > self.last_km and km > 0:
            self.last_km = km
            if km % 5 == 0:
                self.display_text = f"{km} KM! INCREDIBLE!"
                self.display_color = NEON_MAGENTA
                self.display_timer = 120
            else:
                self.display_text = f"{km} KM!"
                self.display_color = SOLAR_YELLOW
                self.display_timer = 80
            SFX["select"].play()

    def update(self):
        if self.display_timer > 0:
            self.display_timer -= 1

    def draw(self, surface):
        if self.display_timer > 0:
            progress = self.display_timer / 80
            size = int(36 + 12 * max(0, progress - 0.7) * 3.3)
            font = load_font("dejavusans", size, bold=True)
            txt = font.render(self.display_text, True, self.display_color)
            alpha = min(255, self.display_timer * 5)
            txt.set_alpha(alpha)
            y = SCREEN_HEIGHT // 2 - 60
            surface.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2, y))


class HighScoreEntry:
    def __init__(self, score):
        self.score = score
        self.name = ""
        self.done = False

    def handle_event(self, event):
        from core.fonts import FONT_SCORE_ENTRY
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and len(self.name) > 0:
                scores = load_highscores()
                scores.append({"name": self.name, "score": self.score})
                scores.sort(key=lambda s: s["score"], reverse=True)
                save_highscores(scores[:5])
                SFX["highscore"].play()
                self.done = True
            elif event.key == pygame.K_BACKSPACE:
                self.name = self.name[:-1]
            elif len(self.name) < 3 and event.unicode.isalnum():
                self.name += event.unicode.upper()
                SFX["select"].play()

    def draw(self, screen, tick):
        from core.fonts import FONT_HUD_LG, FONT_SUBTITLE, FONT_HUD, FONT_HUD_SM, FONT_SCORE_ENTRY
        from core.constants import WHITE

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

        hint = FONT_HUD_SM.render("ENTER to confirm", True, (120, 120, 140))
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, py + 215))


def draw_title(screen, tick, selected_diff=DIFF_NORMAL, ai_reward_mult=1,
               loop_count=0, ai_frames=0):
    from core.fonts import FONT_TITLE, FONT_SUBTITLE, FONT_HUD, FONT_HUD_SM, FONT_HUD_SM_BOLD

    t = (tick % 180) / 180
    r = int(18 + 12 * math.sin(t * math.pi * 2))
    g = int(8 + 6 * math.sin(t * math.pi * 2 + 0.5))
    b = int(35 + 22 * math.sin(t * math.pi * 2 + 1))
    screen.fill((r, g, b))

    pygame.draw.rect(screen, (28, 28, 38), (ROAD_LEFT, 0, ROAD_WIDTH, SCREEN_HEIGHT))
    offset = int(tick * 2) % (DASH_LENGTH + DASH_GAP)
    y = -DASH_LENGTH + offset
    while y < SCREEN_HEIGHT:
        pygame.draw.line(screen, NEON_MAGENTA, (ROAD_CENTER, y), (ROAD_CENTER, y + DASH_LENGTH), 2)
        y += DASH_LENGTH + DASH_GAP

    cx = SCREEN_WIDTH // 2

    # Title
    title_text = "NEON RUSH"
    for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
        glow = FONT_TITLE.render(title_text, True, NEON_MAGENTA)
        screen.blit(glow, (cx - glow.get_width() // 2 + dx, 80 + dy))
    title = FONT_TITLE.render(title_text, True, NEON_CYAN)
    screen.blit(title, (cx - title.get_width() // 2, 80))

    # Subtitle
    sub = FONT_SUBTITLE.render("DESERT VELOCITY", True, SOLAR_YELLOW)
    screen.blit(sub, (cx - sub.get_width() // 2, 155))

    # Game mode options row
    blink = (tick // 30) % 2
    if blink:
        modes_row = [
            ("[1] SOLO", NEON_CYAN),
            ("[2] 2-PLAYER", NEON_MAGENTA),
            ("[3] PLAYER+AI", (100, 255, 100)),
            ("[4] AI SOLO", (100, 255, 100)),
            ("[5] AI+AI", (100, 255, 100)),
        ]
        total_w = sum(FONT_HUD_SM.size(m[0])[0] for m in modes_row) + 12 * (len(modes_row) - 1)
        mx = cx - total_w // 2
        for label, color in modes_row:
            mt = FONT_HUD_SM.render(label, True, color)
            screen.blit(mt, (mx, 225))
            mx += mt.get_width() + 12

    # Difficulty selector — LEFT/RIGHT arrows cycle
    diff_y = 268
    diff_list = [DIFF_EASY, DIFF_NORMAL, DIFF_HARD]
    diff_label = FONT_HUD_SM.render("Difficulty:", True, (150, 150, 170))
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

    arrows = FONT_HUD_SM.render("(LEFT/RIGHT to change)", True, (100, 100, 120))
    screen.blit(arrows, (cx - arrows.get_width() // 2, diff_y + 18))

    # AI Reward multiplier row
    ai_y = 308
    ai_label = FONT_HUD_SM.render("AI Reward:", True, (150, 150, 170))
    screen.blit(ai_label, (cx - 150, ai_y))
    for val, key in [(2, "6"), (4, "7"), (8, "8")]:
        is_active = ai_reward_mult == val
        text = f"[{key}] x{val}"
        color = (100, 255, 100) if is_active else (80, 80, 100)
        font = FONT_HUD_SM_BOLD if is_active else FONT_HUD_SM
        rt = font.render(text, True, color)
        screen.blit(rt, (cx - 30 + (int(key) - 6) * 80, ai_y))
    if ai_reward_mult == 1:
        off_label = FONT_HUD_SM.render("x1 (off)", True, (100, 100, 120))
        screen.blit(off_label, (cx + 220, ai_y))

    # Controls hints (condensed)
    c1 = FONT_HUD_SM.render("P1: WASD + Shift   Solo: WASD/Arrows   P2: Arrows + R.Shift", True, (120, 120, 140))
    screen.blit(c1, (cx - c1.get_width() // 2, 345))
    c0 = FONT_HUD_SM.render("Double-tap < or > = Leap   E/Enter = Heat bolt   P = Pause", True, SLOWMO_GREEN)
    screen.blit(c0, (cx - c0.get_width() // 2, 363))

    # High scores
    scores = load_highscores()
    if scores:
        hs = FONT_HUD_SM.render("HIGH SCORES", True, COIN_GOLD)
        screen.blit(hs, (cx - hs.get_width() // 2, 420))
        for i, entry in enumerate(scores[:3]):
            txt = FONT_HUD_SM.render(f"{i + 1}. {entry['name']} - {entry['score']}", True, SOLAR_WHITE)
            screen.blit(txt, (cx - txt.get_width() // 2, 440 + i * 20))

    # Loop / AI counter in banner area
    if loop_count > 0 or ai_frames > 0:
        parts = [f"Loops: {loop_count:,}"]
        if ai_frames > 0:
            parts.append(f"AI Frames: {ai_frames:,}")
        counter_str = "  |  ".join(parts)
        ct = FONT_HUD_SM.render(counter_str, True, (80, 120, 80))
        screen.blit(ct, (cx - ct.get_width() // 2, 508))

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


def draw_gameover(screen, players, game_distance, tick, two_player):
    from core.fonts import FONT_TITLE, FONT_HUD, FONT_HUD_SM

    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))

    pw = 420
    ph = 300 if two_player else 260
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

    blink = (tick // 30) % 2
    if blink:
        retry = FONT_HUD.render("SPACE = Continue    ESC = Quit", True, NEON_CYAN)
        screen.blit(retry, (SCREEN_WIDTH // 2 - retry.get_width() // 2, py + ph - 45))
