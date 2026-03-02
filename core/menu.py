"""Menu state machine extracted from neon_rush.py.

MenuController handles all title-screen key navigation and launch logic.
"""
import pygame
import logging

from core.constants import (
    DIFF_EASY, DIFF_NORMAL, DIFF_HARD, FPS,
)
from core.ui import (
    MENU_ROW_MODES, MENU_ROW_DIFF, MENU_ROW_AI_REWARD,
    MENU_ROW_RENDER, MENU_ROW_TOGGLES, MENU_NUM_ROWS, _MENU_COLS,
)
import core.sound as _snd

DIFF_LIST = [DIFF_EASY, DIFF_NORMAL, DIFF_HARD]
FPS_CAPS = [30, 60, 120, 144, 0]


class MenuController:
    """Encapsulates title-screen navigation state and input handling."""

    def __init__(self, evolution_mgr=None, dashboard=None):
        self.menu_row = 0
        self.menu_col = 0
        self.selected_diff = DIFF_NORMAL
        self.ai_reward_mult = 1
        self.target_fps = FPS
        self.logging_enabled = False
        self.evolution_mgr = evolution_mgr
        self.dashboard = dashboard

    # --- Public API ---

    def handle_event(self, event):
        """Process a KEYDOWN event on the title screen.

        Returns:
            str or None: 'launch' if a game mode was selected,
                         'quit' for ESC, else None.
        """
        if event.type != pygame.KEYDOWN:
            return None

        # Dashboard handles its own keys first
        if self.dashboard and self.dashboard.handle_key(event):
            return None

        key = event.key

        # Arrow navigation
        if key == pygame.K_UP:
            self.menu_row = (self.menu_row - 1) % MENU_NUM_ROWS
            self.menu_col = min(self.menu_col, _MENU_COLS[self.menu_row] - 1)
            _snd.play_sfx("select")
        elif key == pygame.K_DOWN:
            self.menu_row = (self.menu_row + 1) % MENU_NUM_ROWS
            self.menu_col = min(self.menu_col, _MENU_COLS[self.menu_row] - 1)
            _snd.play_sfx("select")
        elif key == pygame.K_LEFT:
            self._handle_left()
            _snd.play_sfx("select")
        elif key == pygame.K_RIGHT:
            self._handle_right()
            _snd.play_sfx("select")

        # Enter / Space — activate
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            if self.menu_row == MENU_ROW_MODES:
                return 'launch'
            elif self.menu_row == MENU_ROW_TOGGLES:
                self._toggle_current()
                _snd.play_sfx("select")

        # Direct shortcut keys
        elif key in (pygame.K_1, pygame.K_KP1):
            self.menu_col = 0
            return 'launch'
        elif key in (pygame.K_2, pygame.K_KP2):
            self.menu_col = 1
            return 'launch'
        elif key in (pygame.K_3, pygame.K_KP3):
            self.menu_col = 2
            return 'launch'
        elif key in (pygame.K_4, pygame.K_KP4):
            self.menu_col = 3
            return 'launch'
        elif key in (pygame.K_5, pygame.K_KP5):
            self.menu_col = 4
            return 'launch'
        elif key in (pygame.K_6, pygame.K_KP6):
            self.ai_reward_mult = 1 if self.ai_reward_mult == 2 else 2
            _snd.play_sfx("select")
        elif key in (pygame.K_7, pygame.K_KP7):
            self.ai_reward_mult = 1 if self.ai_reward_mult == 4 else 4
            _snd.play_sfx("select")
        elif key in (pygame.K_8, pygame.K_KP8):
            self.ai_reward_mult = 1 if self.ai_reward_mult == 8 else 8
            _snd.play_sfx("select")
        elif key == pygame.K_m:
            _snd.set_sound_enabled(not _snd.sound_enabled)
            _snd.play_sfx("select")
        elif key == pygame.K_e:
            if self.evolution_mgr:
                self.evolution_mgr.enabled = not self.evolution_mgr.enabled
            _snd.play_sfx("select")
        elif key == pygame.K_l:
            self._toggle_logging()
            _snd.play_sfx("select")
        elif key == pygame.K_ESCAPE:
            return 'quit'

        return None

    def get_launch_config(self):
        """Return (num_players, ai_config_or_None) for the selected mode column."""
        col = self.menu_col
        if col == 0:
            return 1, None
        elif col == 1:
            return 2, None
        elif col == 2:
            return 2, {"ai_players": [1], "score_mult": self.ai_reward_mult}
        elif col == 3:
            return 1, {"ai_players": [0], "score_mult": self.ai_reward_mult}
        elif col == 4:
            return 2, {"ai_players": [0, 1], "score_mult": self.ai_reward_mult}
        return 1, None

    # --- Internal ---

    def _handle_left(self):
        row = self.menu_row
        if row == MENU_ROW_MODES:
            self.menu_col = max(0, self.menu_col - 1)
        elif row == MENU_ROW_DIFF:
            idx = DIFF_LIST.index(self.selected_diff)
            self.selected_diff = DIFF_LIST[max(0, idx - 1)]
        elif row == MENU_ROW_AI_REWARD:
            self._cycle_ai_reward(-1)
        elif row == MENU_ROW_RENDER:
            self._cycle_fps(-1)
        elif row == MENU_ROW_TOGGLES:
            self.menu_col = max(0, self.menu_col - 1)

    def _handle_right(self):
        row = self.menu_row
        if row == MENU_ROW_MODES:
            self.menu_col = min(_MENU_COLS[MENU_ROW_MODES] - 1, self.menu_col + 1)
        elif row == MENU_ROW_DIFF:
            idx = DIFF_LIST.index(self.selected_diff)
            self.selected_diff = DIFF_LIST[min(len(DIFF_LIST) - 1, idx + 1)]
        elif row == MENU_ROW_AI_REWARD:
            self._cycle_ai_reward(1)
        elif row == MENU_ROW_RENDER:
            self._cycle_fps(1)
        elif row == MENU_ROW_TOGGLES:
            self.menu_col = min(2, self.menu_col + 1)

    def _toggle_current(self):
        col = self.menu_col
        if col == 0:
            _snd.set_sound_enabled(not _snd.sound_enabled)
        elif col == 1 and self.evolution_mgr:
            self.evolution_mgr.enabled = not self.evolution_mgr.enabled
        elif col == 2:
            self._toggle_logging()

    def _cycle_ai_reward(self, direction):
        ai_vals = [1, 2, 4, 8]
        idx = ai_vals.index(self.ai_reward_mult) if self.ai_reward_mult in ai_vals else 0
        self.ai_reward_mult = ai_vals[max(0, min(len(ai_vals) - 1, idx + direction))]

    def _cycle_fps(self, direction):
        idx = FPS_CAPS.index(self.target_fps) if self.target_fps in FPS_CAPS else 1
        self.target_fps = FPS_CAPS[max(0, min(len(FPS_CAPS) - 1, idx + direction))]

    def _toggle_logging(self):
        self.logging_enabled = not self.logging_enabled
        root_log = logging.getLogger()
        if self.logging_enabled:
            root_log.setLevel(logging.DEBUG)
            logging.info("Logging: ON (DEBUG level)")
        else:
            logging.info("Logging: OFF (WARNING level)")
            root_log.setLevel(logging.WARNING)
