"""Task/objective system for NEON RUSH boss rush mode.

Each level assigns 2 random tasks from a pool of 12. Complete both to
trigger the boss fight. Tasks are tracked via event notifications and
per-frame ticks.
"""
import random
import pygame
from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    MODE_DESERT, MODE_EXCITEBIKE, MODE_MICROMACHINES,
    DIFF_EASY, DIFF_NORMAL, DIFF_HARD,
    NEON_CYAN, SOLAR_WHITE, SOLAR_YELLOW,
)
import core.sound as _snd


# --- Colors (also in constants.py for external use) ---
TASK_BAR_BG = (20, 20, 30)
TASK_BAR_BORDER = (80, 70, 50)
TASK_GREEN = (50, 255, 100)
TASK_AMBER = (255, 200, 50)
TASK_COMPLETE_COLOR = (0, 255, 180)
TASK_LABEL_DIM = (160, 160, 170)

# --- Mode pace multipliers ---
MODE_PACE = {
    MODE_DESERT: 0.7,
    MODE_EXCITEBIKE: 1.0,
    MODE_MICROMACHINES: 1.3,
}

# --- Difficulty multipliers ---
DIFF_MULT = {
    DIFF_EASY: 0.7,
    DIFF_NORMAL: 1.0,
    DIFF_HARD: 1.4,
}

# --- SIM_RATE for frame-to-second conversions ---
SIM_RATE = 36  # from constants.py SIM_RATE


# =========================================================================
# TaskDef — static definition of a task type
# =========================================================================

class TaskDef:
    """Static definition of a task type in the pool."""

    __slots__ = ('key', 'name', 'targets', 'check_type', 'mode_filter')

    def __init__(self, key, name, targets, check_type='event', mode_filter=None):
        """
        Args:
            key: Unique string identifier (e.g. 'coin_rush')
            name: HUD display name (e.g. 'COIN RUSH')
            targets: Tuple of (tier1, tier2, tier3) base targets
            check_type: 'event' (notify) or 'tick' (per-frame check)
            mode_filter: If set, only available in this mode index (e.g. MODE_EXCITEBIKE)
        """
        self.key = key
        self.name = name
        self.targets = targets
        self.check_type = check_type
        self.mode_filter = mode_filter


# =========================================================================
# Task pool — 12 task definitions
# =========================================================================

TASK_POOL = [
    TaskDef('coin_rush',    'COIN RUSH',    (8, 12, 18),    'event'),
    TaskDef('score_target', 'SCORE TARGET', (800, 1500, 2500), 'tick'),
    TaskDef('distance_run', 'DISTANCE RUN', (0.5, 0.8, 1.2), 'tick'),
    TaskDef('heat_kills',   'HEAT KILLS',   (5, 8, 12),     'event'),
    TaskDef('combo_chain',  'COMBO CHAIN',  (2, 3, 4),      'tick'),
    TaskDef('powerup_grab', 'POWER SURGE',  (2, 3, 4),      'event'),
    TaskDef('speed_demon',  'SPEED DEMON',  (3, 3, 3),      'tick'),   # seconds at speed threshold
    TaskDef('survivor',     'SURVIVOR',     (10, 15, 20),   'tick'),   # seconds since last hit
    TaskDef('near_miss',    'NEAR MISS',    (6, 10, 15),    'event'),
    TaskDef('coin_combo',   'COIN COMBO',   (4, 6, 8),      'event'),
    TaskDef('ramp_master',  'RAMP MASTER',  (2, 3, 4),      'event',  MODE_EXCITEBIKE),
    TaskDef('drift_king',   'DRIFT KING',   (60, 100, 150), 'tick',   MODE_MICROMACHINES),
]

# Speed thresholds per tier for speed_demon task
SPEED_THRESHOLDS = (6, 8, 10)


def _tier_index(tier):
    """Clamp tier to 0-2 index for target lookup."""
    return max(0, min(2, tier - 1))


def _scale_target(base, mode_index, difficulty):
    """Apply mode pace and difficulty scaling to a base target."""
    pace = MODE_PACE.get(mode_index, 1.0)
    mult = DIFF_MULT.get(difficulty, 1.0)
    scaled = base * pace * mult
    # For float targets (distance), keep float; for int targets, round up
    if isinstance(base, float):
        return round(scaled, 2)
    return max(1, int(scaled))


# =========================================================================
# ActiveTask — runtime state for an assigned task
# =========================================================================

class ActiveTask:
    """Runtime state for a single active task during gameplay."""

    __slots__ = (
        'task_def', 'target', 'progress', 'complete', 'flash_timer',
        # Aux state for tick-based tasks
        '_speed_frames', '_no_hit_frames', '_drift_frames',
        '_speed_threshold', '_chain_count',
    )

    def __init__(self, task_def, target, tier):
        self.task_def = task_def
        self.target = target
        self.progress = 0
        self.complete = False
        self.flash_timer = 0

        # Aux state
        self._speed_frames = 0
        self._no_hit_frames = 0
        self._drift_frames = 0
        self._chain_count = 0  # for coin_combo: coins in current chain
        ti = _tier_index(tier)
        self._speed_threshold = SPEED_THRESHOLDS[ti]

    @property
    def key(self):
        return self.task_def.key

    @property
    def name(self):
        return self.task_def.name

    @property
    def pct(self):
        if self.target <= 0:
            return 1.0
        return min(1.0, self.progress / self.target)

    def _check_complete(self):
        if not self.complete and self.progress >= self.target:
            self.complete = True
            self.flash_timer = 60  # 60 frames flash on completion
            return True
        return False


# =========================================================================
# TaskManager — owns pool, assignment, update, draw
# =========================================================================

class TaskManager:
    """Manages task assignment, progress tracking, and HUD rendering."""

    def __init__(self, mode_index, tier, difficulty, boss_rush=False):
        self.mode_index = mode_index
        self.tier = tier
        self.difficulty = difficulty
        self.tasks = []  # list of ActiveTask
        self.all_done = False
        self.boss_delay_timer = 0  # countdown after all tasks complete
        self.boss_ready = False
        self._boss_flash_timer = 0

        if boss_rush:
            # Boss rush: no tasks, boss spawns after brief delay
            self.all_done = True
            self.boss_delay_timer = 5 * SIM_RATE  # 5 seconds
        else:
            self._assign_tasks()

    def _assign_tasks(self):
        """Pick 2 tasks from the pool, respecting mode filters."""
        ti = _tier_index(self.tier)

        # Filter pool by mode
        available = [
            td for td in TASK_POOL
            if td.mode_filter is None or td.mode_filter == self.mode_index
        ]

        # Separate mode-specific and universal
        mode_specific = [td for td in available if td.mode_filter is not None]
        universal = [td for td in available if td.mode_filter is None]

        chosen = []

        # Max 1 mode-specific task
        if mode_specific and random.random() < 0.4:
            pick = random.choice(mode_specific)
            chosen.append(pick)

        # Fill remaining slots with universal tasks
        remaining = [td for td in universal if td not in chosen]
        random.shuffle(remaining)
        while len(chosen) < 2 and remaining:
            chosen.append(remaining.pop())

        # Create ActiveTask instances with scaled targets
        for td in chosen:
            base = td.targets[ti]
            target = _scale_target(base, self.mode_index, self.difficulty)
            self.tasks.append(ActiveTask(td, target, self.tier))

    # --- Event notifications ---

    def notify(self, event_key, value=1):
        """Notify tasks of a game event. Called by mode code."""
        for task in self.tasks:
            if task.complete:
                continue
            if task.task_def.check_type != 'event':
                continue

            if event_key == 'coin_collected':
                if task.key == 'coin_rush':
                    task.progress += value
                elif task.key == 'coin_combo':
                    # Count coins in current chain; progress = best chain
                    task._chain_count += 1
                    task.progress = max(task.progress, task._chain_count)
            elif event_key == 'obstacle_killed' and task.key == 'heat_kills':
                task.progress += value
            elif event_key == 'powerup_collected' and task.key == 'powerup_grab':
                task.progress += value
            elif event_key == 'near_miss' and task.key == 'near_miss':
                task.progress += value
            elif event_key == 'ramp_launched' and task.key == 'ramp_master':
                task.progress += value

            task._check_complete()

        self._check_all_done()

    # --- Per-frame tick ---

    def tick(self, mode):
        """Per-frame update for tick-based tasks. Called every sim step."""
        alive = mode.get_alive_players()
        if not alive:
            return

        best_score = max(p.score for p in alive)
        best_combo = max(getattr(p, 'combo', None) and p.combo.multiplier or 1 for p in alive)
        best_speed = max(abs(p.speed) for p in alive)
        game_dist = mode.game_distance

        # Check if any player was hit this frame (for survivor task)
        any_hit = any(getattr(p, '_was_hit_this_frame', False) for p in alive)

        # Reset coin_combo chain when combo drops (event task, but needs tick check)
        any_combo_active = any(
            getattr(p, 'combo', None) and p.combo.multiplier > 1
            for p in alive
        )
        for task in self.tasks:
            if not task.complete and task.key == 'coin_combo' and not any_combo_active:
                task._chain_count = 0

        for task in self.tasks:
            if task.complete:
                if task.flash_timer > 0:
                    task.flash_timer -= 1
                continue
            if task.task_def.check_type != 'tick':
                continue

            if task.key == 'score_target':
                task.progress = best_score
            elif task.key == 'distance_run':
                task.progress = game_dist
            elif task.key == 'combo_chain':
                task.progress = max(task.progress, best_combo)
            elif task.key == 'speed_demon':
                if best_speed >= task._speed_threshold:
                    task._speed_frames += 1
                else:
                    task._speed_frames = 0
                # Target is in seconds
                task.progress = task._speed_frames / SIM_RATE
            elif task.key == 'survivor':
                if any_hit:
                    task._no_hit_frames = 0
                else:
                    task._no_hit_frames += 1
                task.progress = task._no_hit_frames / SIM_RATE
            elif task.key == 'drift_king':
                # Check any player's drift angle
                drifting = any(
                    abs(getattr(p, 'drift_angle', 0) or getattr(p, 'angle', 0)) > 0.15
                    for p in alive
                )
                if drifting:
                    task._drift_frames += 1
                else:
                    task._drift_frames = 0
                task.progress = task._drift_frames

            task._check_complete()

        # Boss delay countdown
        if self.all_done and self.boss_delay_timer > 0:
            self.boss_delay_timer -= 1
            self._boss_flash_timer += 1
            if self.boss_delay_timer <= 0:
                self.boss_ready = True

        self._check_all_done()

    def _check_all_done(self):
        """Check if all tasks are complete, start boss delay if so."""
        if self.all_done:
            return
        if all(t.complete for t in self.tasks):
            self.all_done = True
            self.boss_delay_timer = 2 * SIM_RATE  # 2 second "BOSS INCOMING!" delay
            self._boss_flash_timer = 0
            _snd.play_sfx("boss_warning")

    def all_complete(self):
        """Return True when boss should spawn (all tasks done + delay expired)."""
        return self.boss_ready

    # --- HUD rendering ---

    def draw_hud(self, screen, level_label=None):
        """Draw task progress HUD at bottom-center of screen."""
        from core.fonts import FONT_HUD_SM, FONT_HUD_SM_BOLD

        if not self.tasks and not self.all_done:
            return

        bar_w = 220
        bar_h = 12
        task_h = 22  # height per task row
        pad = 6
        num_tasks = len(self.tasks)
        header_h = 18

        total_h = header_h + num_tasks * task_h + pad * 2
        bx = SCREEN_WIDTH // 2 - (bar_w + pad * 2) // 2
        by = SCREEN_HEIGHT - total_h - 8

        # Panel background
        panel_w = bar_w + pad * 2
        panel_surf = pygame.Surface((panel_w, total_h), pygame.SRCALPHA)
        panel_surf.fill((8, 8, 16, 180))
        pygame.draw.rect(panel_surf, TASK_BAR_BORDER,
                         (0, 0, panel_w, total_h), 1)
        screen.blit(panel_surf, (bx, by))

        # Header: level label
        header_text = f"LEVEL {level_label}" if level_label else "TASKS"
        if FONT_HUD_SM_BOLD:
            header_surf = FONT_HUD_SM_BOLD.render(header_text, True, NEON_CYAN)
        elif FONT_HUD_SM:
            header_surf = FONT_HUD_SM.render(header_text, True, NEON_CYAN)
        else:
            return
        screen.blit(header_surf,
                     (bx + panel_w // 2 - header_surf.get_width() // 2, by + 2))

        # Task bars
        font = FONT_HUD_SM
        if not font:
            return

        for i, task in enumerate(self.tasks):
            ty = by + header_h + pad + i * task_h
            tx = bx + pad

            # Progress bar background
            pygame.draw.rect(screen, TASK_BAR_BG, (tx, ty, bar_w, bar_h))

            # Fill
            fill_w = int(bar_w * task.pct)
            if fill_w > 0:
                if task.complete:
                    color = TASK_COMPLETE_COLOR
                elif task.pct > 0.7:
                    color = TASK_AMBER
                else:
                    color = TASK_GREEN
                pygame.draw.rect(screen, color, (tx, ty, fill_w, bar_h))

            # Flash on completion
            if task.flash_timer > 0:
                flash_alpha = int(120 * (task.flash_timer / 60))
                flash_surf = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
                flash_surf.fill((255, 255, 255, flash_alpha))
                screen.blit(flash_surf, (tx, ty))

            # Border
            pygame.draw.rect(screen, TASK_BAR_BORDER, (tx, ty, bar_w, bar_h), 1)

            # Label + counter
            # Format progress display
            if isinstance(task.target, float):
                prog_str = f"{task.progress:.1f}/{task.target:.1f}"
            else:
                prog_int = int(task.progress) if isinstance(task.progress, float) else task.progress
                prog_str = f"{prog_int}/{task.target}"

            label_text = f"{task.name}  {prog_str}"
            label_color = TASK_COMPLETE_COLOR if task.complete else TASK_LABEL_DIM
            label_surf = font.render(label_text, True, label_color)
            # Center label vertically on the bar
            label_y = ty + (bar_h - label_surf.get_height()) // 2
            screen.blit(label_surf, (tx + 4, label_y))

        # "BOSS INCOMING!" flash when all tasks done
        if self.all_done and self.boss_delay_timer > 0:
            flash_font = FONT_HUD_SM_BOLD or font
            # Flashing text
            show = (self._boss_flash_timer // 8) % 2 == 0
            if show:
                boss_text = flash_font.render("BOSS INCOMING!", True, SOLAR_YELLOW)
                boss_x = SCREEN_WIDTH // 2 - boss_text.get_width() // 2
                boss_y = by - 24
                screen.blit(boss_text, (boss_x, boss_y))


# =========================================================================
# Level label utility
# =========================================================================

def level_label(mode_index, tier):
    """Return level label like '1-1', '2-3', etc.
    World = tier (1-3), Stage = mode within cycle (1-3).
    1-1=Desert T1, 1-2=Excitebike T1, 2-1=Desert T2, etc.
    """
    return f"{max(1, min(tier, 3))}-{mode_index + 1}"
