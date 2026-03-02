"""Tests for core/tasks.py — task system pure functions, ActiveTask, TaskManager."""
import random
import pytest

from core.constants import (
    MODE_DESERT, MODE_EXCITEBIKE, MODE_MICROMACHINES,
    DIFF_EASY, DIFF_NORMAL, DIFF_HARD,
)
from core.tasks import (
    _tier_index, _scale_target, level_label,
    ActiveTask, TaskDef, TaskManager, SIM_RATE, TASK_POOL,
)


# =========================================================================
# _tier_index — clamp tier to 0-2
# =========================================================================

class TestTierIndex:
    def test_clamp_low(self):
        assert _tier_index(0) == 0

    def test_clamp_high(self):
        assert _tier_index(5) == 2

    def test_tier1(self):
        assert _tier_index(1) == 0

    def test_tier2(self):
        assert _tier_index(2) == 1

    def test_tier3(self):
        assert _tier_index(3) == 2


# =========================================================================
# _scale_target — mode pace × difficulty scaling
# =========================================================================

class TestScaleTarget:
    def test_float_keeps_decimal(self):
        result = _scale_target(0.5, MODE_DESERT, DIFF_NORMAL)
        assert isinstance(result, float)
        assert result == round(0.5 * 0.7 * 1.0, 2)

    def test_int_rounds(self):
        result = _scale_target(8, MODE_DESERT, DIFF_NORMAL)
        assert isinstance(result, int)
        assert result == int(8 * 0.7 * 1.0)

    def test_floor_at_one(self):
        result = _scale_target(1, MODE_DESERT, DIFF_EASY)
        assert result >= 1


# =========================================================================
# level_label — "tier-mode" format
# =========================================================================

class TestLevelLabel:
    def test_format(self):
        assert level_label(0, 1) == "1-1"
        assert level_label(1, 2) == "2-2"
        assert level_label(2, 3) == "3-3"

    def test_clamps_tier(self):
        assert level_label(0, 0) == "1-1"
        assert level_label(0, 99) == "3-1"


# =========================================================================
# ActiveTask — progress tracking
# =========================================================================

class TestActiveTask:
    def _make_task(self, target=10):
        td = TaskDef("test_key", "TEST", (10, 20, 30), "event")
        return ActiveTask(td, target, tier=1)

    def test_pct_normal(self):
        t = self._make_task(10)
        t.progress = 5
        assert t.pct == pytest.approx(0.5)

    def test_pct_zero_target(self):
        t = self._make_task(0)
        assert t.pct == 1.0

    def test_check_complete_triggers(self):
        t = self._make_task(10)
        t.progress = 10
        assert t._check_complete() is True
        assert t.complete is True
        assert t.flash_timer == 60

    def test_check_complete_idempotent(self):
        t = self._make_task(10)
        t.progress = 10
        t._check_complete()
        assert t._check_complete() is False  # already complete


# =========================================================================
# TaskManager — assignment, notify, check_all_done, boss rush, tick
# =========================================================================

class TestTaskManager:
    def test_assign_picks_two(self):
        random.seed(42)
        tm = TaskManager(MODE_DESERT, tier=1, difficulty=DIFF_NORMAL)
        assert len(tm.tasks) == 2

    def test_respects_mode_filter(self):
        """Desert mode should never get ramp_master (Excitebike-only)."""
        random.seed(0)
        for _ in range(50):
            tm = TaskManager(MODE_DESERT, tier=1, difficulty=DIFF_NORMAL)
            for task in tm.tasks:
                assert task.key != "ramp_master"

    def test_notify_coin_rush(self):
        random.seed(42)
        tm = TaskManager(MODE_DESERT, tier=1, difficulty=DIFF_NORMAL)
        # Force a coin_rush task for testing
        td = TaskDef("coin_rush", "COIN RUSH", (8, 12, 18), "event")
        tm.tasks = [ActiveTask(td, 3, tier=1)]
        tm.all_done = False
        tm.notify("coin_collected", 1)
        assert tm.tasks[0].progress == 1

    def test_notify_heat_kills(self):
        td = TaskDef("heat_kills", "HEAT KILLS", (5, 8, 12), "event")
        tm = TaskManager(MODE_DESERT, tier=1, difficulty=DIFF_NORMAL)
        tm.tasks = [ActiveTask(td, 2, tier=1)]
        tm.all_done = False
        tm.notify("obstacle_killed", 1)
        tm.notify("obstacle_killed", 1)
        assert tm.tasks[0].progress == 2
        assert tm.tasks[0].complete is True

    def test_notify_coin_combo_chain(self):
        td = TaskDef("coin_combo", "COIN COMBO", (4, 6, 8), "event")
        tm = TaskManager(MODE_DESERT, tier=1, difficulty=DIFF_NORMAL)
        tm.tasks = [ActiveTask(td, 3, tier=1)]
        tm.all_done = False
        tm.notify("coin_collected", 1)
        tm.notify("coin_collected", 1)
        tm.notify("coin_collected", 1)
        # coin_combo tracks best chain length
        assert tm.tasks[0].progress == 3
        assert tm.tasks[0].complete is True

    def test_check_all_done_triggers(self):
        td1 = TaskDef("coin_rush", "COIN RUSH", (8, 12, 18), "event")
        td2 = TaskDef("heat_kills", "HEAT KILLS", (5, 8, 12), "event")
        tm = TaskManager(MODE_DESERT, tier=1, difficulty=DIFF_NORMAL)
        tm.tasks = [ActiveTask(td1, 1, tier=1), ActiveTask(td2, 1, tier=1)]
        tm.all_done = False
        tm.notify("coin_collected", 1)
        tm.notify("obstacle_killed", 1)
        assert tm.all_done is True
        assert tm.boss_delay_timer == 2 * SIM_RATE

    def test_boss_rush_mode(self):
        tm = TaskManager(MODE_DESERT, tier=1, difficulty=DIFF_NORMAL, boss_rush=True)
        assert tm.all_done is True
        assert tm.boss_delay_timer == 5 * SIM_RATE
        assert len(tm.tasks) == 0

    def test_tick_score_target(self):
        td = TaskDef("score_target", "SCORE TARGET", (800, 1500, 2500), "tick")
        tm = TaskManager(MODE_DESERT, tier=1, difficulty=DIFF_NORMAL)
        tm.tasks = [ActiveTask(td, 100, tier=1)]
        tm.all_done = False

        class MockPlayer:
            score = 150
            speed = 5.0
            alive = True
            combo = type("C", (), {"multiplier": 1})()
            _was_hit_this_frame = False
            drift_angle = 0.0

        class MockMode:
            game_distance = 0.0
            def get_alive_players(self):
                return [MockPlayer()]

        tm.tick(MockMode())
        assert tm.tasks[0].progress == 150
        assert tm.tasks[0].complete is True

    def test_tick_speed_demon_frame_counting(self):
        td = TaskDef("speed_demon", "SPEED DEMON", (3, 3, 3), "tick")
        tm = TaskManager(MODE_DESERT, tier=1, difficulty=DIFF_NORMAL)
        tm.tasks = [ActiveTask(td, 3, tier=1)]
        tm.all_done = False

        class MockPlayer:
            score = 0
            speed = 10.0  # above threshold (6 for tier 1)
            alive = True
            combo = type("C", (), {"multiplier": 1})()
            _was_hit_this_frame = False
            drift_angle = 0.0

        class MockMode:
            game_distance = 0.0
            def get_alive_players(self):
                return [MockPlayer()]

        mode = MockMode()
        # Tick enough frames for 3 seconds at SIM_RATE
        for _ in range(3 * SIM_RATE):
            tm.tick(mode)
        assert tm.tasks[0].progress >= 3
        assert tm.tasks[0].complete is True

    def test_tick_survivor_hit_reset(self):
        td = TaskDef("survivor", "SURVIVOR", (10, 15, 20), "tick")
        tm = TaskManager(MODE_DESERT, tier=1, difficulty=DIFF_NORMAL)
        tm.tasks = [ActiveTask(td, 2, tier=1)]
        tm.all_done = False

        class MockPlayer:
            score = 0
            speed = 5.0
            alive = True
            combo = type("C", (), {"multiplier": 1})()
            _was_hit_this_frame = False
            drift_angle = 0.0

        class MockMode:
            game_distance = 0.0
            def get_alive_players(self):
                return [MockPlayer()]

        mode = MockMode()
        # Build up survivor frames
        for _ in range(SIM_RATE):
            tm.tick(mode)
        assert tm.tasks[0]._no_hit_frames == SIM_RATE

        # Simulate hit — resets counter
        MockPlayer._was_hit_this_frame = True
        tm.tick(mode)
        assert tm.tasks[0]._no_hit_frames == 0
