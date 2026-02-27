"""Evolution Manager — same-run cycling with progressive difficulty.

After beating all 3 bosses, players loop back to Desert with harder bosses
and enhanced V2/V3 backgrounds. Single source of truth for evolution state.

Usage:
    from core.evolution import EvolutionManager
    evolution_mgr = EvolutionManager()
    evolution_mgr.start_run()          # reset at game start
    tier = evolution_mgr.advance_cycle()  # after all 3 bosses beaten
    scale = evolution_mgr.hp_scale()   # boss HP multiplier
"""

import json
import os
import tempfile


class EvolutionManager:
    """Manages level evolution tiers and same-run cycling."""

    def __init__(self):
        self.enabled = False        # toggle from title screen (E key)
        self.max_tier = 1           # highest tier unlocked (persisted)
        self.current_tier = 1       # tier for current run
        self.cycle_count = 0        # how many times we've looped (0 = first pass)
        self._state_file = os.path.join(
            os.path.dirname(__file__), '..', 'brains', 'evolution_state.json')
        self.load()

    # --- Cycling API (called by neon_rush.py) ---

    def start_run(self):
        """Reset for a new game. Tier starts at 1."""
        self.current_tier = 1
        self.cycle_count = 0

    def advance_cycle(self):
        """Called after all 3 bosses defeated. Returns new tier."""
        self.cycle_count += 1
        self.current_tier = self.cycle_count + 1
        self.max_tier = max(self.max_tier, self.current_tier)
        self.save()
        return self.current_tier

    # --- Scaling API (called by bosses, backgrounds, etc.) ---

    def hp_scale(self):
        """Boss HP multiplier: 1.0 -> 1.3 -> 1.6 -> ..."""
        return 1.0 + (self.current_tier - 1) * 0.3

    def speed_scale(self):
        """Obstacle/spawn speed multiplier: 1.0 -> 1.1 -> 1.2 -> ..."""
        return 1.0 + (self.current_tier - 1) * 0.1

    def bg_tier(self):
        """Background visual tier. Capped at 3 (V1/V2/V3)."""
        return min(self.current_tier, 3)

    def tier_label(self):
        """'V2', 'V3', etc. Empty string for tier 1."""
        return f"V{self.current_tier}" if self.current_tier > 1 else ""

    # --- Persistence ---

    def save(self):
        """Atomic JSON save to brains/evolution_state.json."""
        data = {"max_tier": self.max_tier}
        try:
            os.makedirs(os.path.dirname(self._state_file), exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(
                dir=os.path.dirname(self._state_file), suffix='.tmp')
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self._state_file)
        except OSError:
            pass  # Non-critical — max_tier just won't persist

    def load(self):
        """Load max_tier from file."""
        try:
            with open(self._state_file, 'r') as f:
                data = json.load(f)
            self.max_tier = max(1, int(data.get("max_tier", 1)))
        except (OSError, json.JSONDecodeError, ValueError):
            self.max_tier = 1
