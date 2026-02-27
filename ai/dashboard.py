"""AI Learning Lab — title screen dashboard for inspecting and tuning brain pools.

Toggle with L key. Shows brain leaderboard per mode, generation counter,
speed multiplier, and per-brain tuning controls.
"""
import pygame

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    NEON_CYAN, NEON_MAGENTA, SOLAR_YELLOW, SOLAR_WHITE, COIN_GOLD,
    SURGE_PINK,
    MODE_DESERT, MODE_EXCITEBIKE, MODE_MICROMACHINES,
)
from core.fonts import load_font

# Dashboard geometry
DASH_X = 30
DASH_Y = 405
DASH_W = SCREEN_WIDTH - 60
DASH_H_COLLAPSED = 170
DASH_H_EXPANDED = 300


class LearningDashboard:
    """Title screen AI dashboard with tabs, leaderboard, and tuning controls."""

    MODE_TABS = [
        (MODE_DESERT, "DESERT"),
        (MODE_EXCITEBIKE, "EXCITE"),
        (MODE_MICROMACHINES, "MICRO"),
    ]

    SPEED_LEVELS = [1, 2, 4, 8, 16]

    def __init__(self, brain_pools):
        self.brain_pools = brain_pools  # {mode_index: BrainPool}
        self.active = False             # dashboard visible?
        self.enabled = False            # brain learning enabled?
        self.active_tab = 0            # 0=desert, 1=excitebike, 2=micro
        self.expanded = False
        self.scroll_offset = 0
        self.selected_brain_idx = -1   # index in ranked list, -1=none
        self.speed_level = 0           # index into SPEED_LEVELS
        self._tune_open = False        # tuning panel open for selected brain

    @property
    def speed_mult(self):
        return self.SPEED_LEVELS[self.speed_level]

    @property
    def current_pool(self):
        mode_idx = self.MODE_TABS[self.active_tab][0]
        return self.brain_pools.get(mode_idx)

    # ── Event handling ──────────────────────────────────────────

    def handle_key(self, event):
        """Handle keyboard input. Returns True if event was consumed."""
        if event.key == pygame.K_l:
            self.active = not self.active
            self.enabled = self.active  # enable brains when dashboard opens
            return True

        if not self.active:
            return False

        if event.key == pygame.K_TAB:
            self.active_tab = (self.active_tab + 1) % len(self.MODE_TABS)
            self.scroll_offset = 0
            self.selected_brain_idx = -1
            self._tune_open = False
            return True

        if event.key == pygame.K_9:
            self.speed_level = (self.speed_level + 1) % len(self.SPEED_LEVELS)
            return True

        if event.key == pygame.K_0:
            self.expanded = not self.expanded
            return True

        # Arrow keys for brain selection when dashboard is active
        if event.key == pygame.K_j or (event.key == pygame.K_DOWN and self.active):
            pool = self.current_pool
            if pool:
                max_idx = len(pool.brains) - 1
                self.selected_brain_idx = min(self.selected_brain_idx + 1, max_idx)
            return True

        if event.key == pygame.K_k or (event.key == pygame.K_UP and self.active):
            self.selected_brain_idx = max(self.selected_brain_idx - 1, -1)
            return True

        return False

    def handle_click(self, pos):
        """Handle mouse clicks on dashboard elements."""
        if not self.active:
            return

        mx, my = pos

        # Tab clicks (y = DASH_Y + 22 to DASH_Y + 40, spread across tab area)
        if DASH_Y + 22 <= my <= DASH_Y + 42:
            tab_x = DASH_X + 10
            for i, (_, label) in enumerate(self.MODE_TABS):
                tw = 70
                if tab_x <= mx <= tab_x + tw:
                    self.active_tab = i
                    self.scroll_offset = 0
                    self.selected_brain_idx = -1
                    self._tune_open = False
                    return
                tab_x += tw + 8

        # Speed button click (top right area)
        speed_x = DASH_X + DASH_W - 80
        if DASH_Y + 2 <= my <= DASH_Y + 20 and speed_x <= mx <= speed_x + 40:
            self.speed_level = (self.speed_level + 1) % len(self.SPEED_LEVELS)
            return

        # Brain row clicks (leaderboard area)
        row_y_start = DASH_Y + 62
        row_h = 18
        pool = self.current_pool
        if pool and my >= row_y_start:
            ranked = pool.ranked_brains()
            idx = (my - row_y_start) // row_h
            if 0 <= idx < len(ranked):
                if self.selected_brain_idx == idx:
                    self._tune_open = not self._tune_open
                else:
                    self.selected_brain_idx = idx
                    self._tune_open = False

    # ── Drawing ─────────────────────────────────────────────────

    def draw(self, screen, tick):
        """Render the dashboard panel onto the screen."""
        if not self.active:
            return

        dash_h = DASH_H_EXPANDED if self.expanded else DASH_H_COLLAPSED

        # Background panel
        panel = pygame.Surface((DASH_W, dash_h), pygame.SRCALPHA)
        panel.fill((0, 0, 15, 210))
        screen.blit(panel, (DASH_X, DASH_Y))

        # Border with orange gradient based on speed level
        orange_r = min(255, 180 + self.speed_level * 18)
        orange_g = min(255, 100 + self.speed_level * 25)
        border_color = (orange_r, orange_g, 0)
        pygame.draw.rect(screen, border_color,
                         (DASH_X, DASH_Y, DASH_W, dash_h), 2)

        font_sm = load_font("dejavusans", 13)
        font_sm_b = load_font("dejavusans", 13, bold=True)
        font_xs = load_font("dejavusans", 11)
        font_title = load_font("dejavusans", 14, bold=True)

        # ── Header row ──────────────────────────────────────────
        header_y = DASH_Y + 4
        # Lab title
        lab_t = font_title.render("[L] AI LEARNING LAB", True, border_color)
        screen.blit(lab_t, (DASH_X + 8, header_y))

        # Speed button
        speed_str = f"[{self.speed_mult}x]"
        speed_color = border_color
        speed_t = font_sm_b.render(speed_str, True, speed_color)
        screen.blit(speed_t, (DASH_X + DASH_W - 85, header_y + 1))

        # Expand/collapse indicator
        exp_str = "[0] " + ("^" if self.expanded else "v")
        exp_t = font_xs.render(exp_str, True, (120, 120, 140))
        screen.blit(exp_t, (DASH_X + DASH_W - 40, header_y + 2))

        # Brain status
        status_str = "ON" if self.enabled else "OFF"
        status_color = (100, 255, 100) if self.enabled else (255, 80, 80)
        status_t = font_sm.render(status_str, True, status_color)
        screen.blit(status_t, (DASH_X + 200, header_y + 1))

        # ── Mode tabs ───────────────────────────────────────────
        tab_y = DASH_Y + 22
        tab_x = DASH_X + 10
        pool = self.current_pool
        for i, (_, label) in enumerate(self.MODE_TABS):
            is_active = i == self.active_tab
            color = NEON_CYAN if is_active else (80, 80, 100)
            font = font_sm_b if is_active else font_sm
            tt = font.render(label, True, color)
            screen.blit(tt, (tab_x, tab_y))
            if is_active:
                pygame.draw.line(screen, NEON_CYAN,
                                 (tab_x, tab_y + 16), (tab_x + tt.get_width(), tab_y + 16), 2)
            tab_x += tt.get_width() + 12

        # Generation + pool size
        if pool:
            gen_str = f"Gen: {pool.generation}  |  Pool: {len(pool.brains)}/{pool.pool_size}"
            gen_t = font_xs.render(gen_str, True, (140, 140, 160))
            screen.blit(gen_t, (DASH_X + DASH_W - gen_t.get_width() - 10, tab_y + 2))

        # ── Divider ─────────────────────────────────────────────
        pygame.draw.line(screen, (50, 50, 70),
                         (DASH_X + 5, DASH_Y + 42), (DASH_X + DASH_W - 5, DASH_Y + 42))

        # ── Leaderboard header ──────────────────────────────────
        hdr_y = DASH_Y + 46
        cols = [("#", 20), ("Name", 110), ("Avg", 60), ("Best", 60),
                ("Gen", 35), ("Eps", 45), ("Origin", 60)]
        col_x = DASH_X + 10
        for label, width in cols:
            ht = font_xs.render(label, True, (120, 120, 140))
            screen.blit(ht, (col_x, hdr_y))
            col_x += width

        # ── Brain rows ──────────────────────────────────────────
        if pool:
            ranked = pool.ranked_brains()
            max_visible = 5 if not self.expanded else 12
            row_y = DASH_Y + 62
            row_h = 18

            for rank, brain in enumerate(ranked[:max_visible]):
                is_selected = rank == self.selected_brain_idx
                # Row highlight
                if is_selected:
                    sel_rect = pygame.Surface((DASH_W - 20, row_h), pygame.SRCALPHA)
                    sel_rect.fill((40, 60, 80, 150))
                    screen.blit(sel_rect, (DASH_X + 5, row_y))

                # Color coding
                if rank < 2:
                    name_color = SOLAR_YELLOW  # elite
                elif brain.origin == "fresh":
                    name_color = (100, 255, 100)  # fresh = green
                elif brain.origin == "mutation":
                    name_color = SURGE_PINK
                elif brain.origin == "crossover":
                    name_color = NEON_CYAN
                else:
                    name_color = SOLAR_WHITE

                col_x = DASH_X + 10
                # Rank
                rt = font_xs.render(f"{rank + 1}.", True, (160, 160, 180))
                screen.blit(rt, (col_x, row_y))
                col_x += 20

                # Name
                nt = font_xs.render(brain.name[:12], True, name_color)
                screen.blit(nt, (col_x, row_y))
                col_x += 110

                # Avg score
                avg_str = f"{brain.avg_score:,.0f}"
                at = font_xs.render(avg_str, True, SOLAR_WHITE)
                screen.blit(at, (col_x, row_y))
                col_x += 60

                # Best score
                best_str = f"{brain.best_score:,}"
                bt = font_xs.render(best_str, True, COIN_GOLD)
                screen.blit(bt, (col_x, row_y))
                col_x += 60

                # Generation
                gt = font_xs.render(str(brain.generation), True, (140, 140, 160))
                screen.blit(gt, (col_x, row_y))
                col_x += 35

                # Epsilon
                et = font_xs.render(f"{brain.epsilon:.2f}", True, (140, 140, 160))
                screen.blit(et, (col_x, row_y))
                col_x += 45

                # Origin
                ot = font_xs.render(brain.origin[:8], True, (120, 120, 140))
                screen.blit(ot, (col_x, row_y))

                row_y += row_h

            # ── Selected brain detail tooltip ────────────────────
            if self.selected_brain_idx >= 0 and self.selected_brain_idx < len(ranked):
                sel_brain = ranked[self.selected_brain_idx]
                detail_y = row_y + 4
                q_size = len(sel_brain.q_table)
                eps_count = sel_brain.total_episodes
                frames = sel_brain.total_frames
                parent_str = ", ".join(str(p) for p in sel_brain.parent_ids) if sel_brain.parent_ids else "none"

                detail_lines = [
                    f"Q-table: {q_size} states | Episodes: {eps_count} | Frames: {frames:,}",
                    f"alpha={sel_brain.alpha:.3f}  gamma={sel_brain.gamma:.3f}  eps={sel_brain.epsilon:.3f}  | Parents: {parent_str}",
                ]
                for line in detail_lines:
                    dt = font_xs.render(line, True, (160, 160, 180))
                    screen.blit(dt, (DASH_X + 10, detail_y))
                    detail_y += 14

        # ── Bottom bar ──────────────────────────────────────────
        bar_y = DASH_Y + dash_h - 18
        hint = font_xs.render(
            "[L] Toggle  [Tab] Mode  [9] Speed  [0] Expand  [J/K] Select",
            True, (100, 100, 120))
        screen.blit(hint, (DASH_X + 10, bar_y))

        # Evolve status
        if pool:
            evolve_str = f"Evolve: {pool._results_since_evolve}/{pool.pool_size}"
            et = font_xs.render(evolve_str, True, border_color)
            screen.blit(et, (DASH_X + DASH_W - et.get_width() - 10, bar_y))
