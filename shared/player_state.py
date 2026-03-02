MODE_NAMES = {0: "DESERT VELOCITY", 1: "EXCITEBIKE", 2: "MICRO MACHINES"}


class SharedPlayerState:
    """Carries persistent state between modes. Score/lives/coins survive transitions."""

    def __init__(self, num_players=1, difficulty="normal", ai_config=None,
                 brain_config=None, evolution_tier=1):
        self.num_players = num_players
        self.difficulty = difficulty
        self.ai_config = ai_config or {"ai_players": [], "score_mult": 1}
        self.brain_config = brain_config or {"use_brains": False}
        self.scores = [0] * num_players
        self.coins = [0] * num_players
        self.lives = [3] * num_players
        self.total_distance = 0.0
        self.total_time = 0
        self.bosses_defeated = 0
        self.current_mode = 0  # 0=desert, 1=excitebike, 2=micromachines
        self.evolution_tier = evolution_tier  # 1=normal, 2=V2, 3=V3...
        self.cycle_count = 0

    def snapshot_from_players(self, players):
        """Pull current stats from player objects at end of a mode."""
        for i, p in enumerate(players):
            if i < self.num_players:
                self.scores[i] = p.score
                self.coins[i] = p.coins
                self.lives[i] = p.lives
                self.total_distance += p.distance

    def inject_into_players(self, players):
        """Push carried state into new player objects at start of next mode."""
        for i, p in enumerate(players):
            if i < self.num_players:
                p.score = self.scores[i]
                p.coins = self.coins[i]
                p.lives = max(1, self.lives[i])  # At least 1 life entering new mode

    def advance_mode(self):
        """Move to next mode after boss defeat."""
        self.bosses_defeated += 1
        self.current_mode += 1

    def reset_for_cycle(self, new_tier):
        """Reset mode index for a new evolution cycle, keeping scores/lives."""
        self.current_mode = 0
        self.cycle_count += 1
        self.evolution_tier = new_tier
        # Don't reset bosses_defeated — it accumulates across cycles

    @property
    def best_score(self):
        return max(self.scores) if self.scores else 0

    @property
    def total_coins(self):
        return sum(self.coins)

    @property
    def all_modes_complete(self):
        return self.bosses_defeated >= 3

    @property
    def level_label(self):
        """Return level label like '1-1', '2-3', etc.
        World = evolution_tier (1-3), Stage = mode within cycle (1-3).
        1-1=Desert T1, 1-2=Excitebike T1, 1-3=Micro T1, 2-1=Desert T2, etc."""
        # Task system can override with proper format
        if hasattr(self, '_task_level_label') and self._task_level_label:
            return self._task_level_label
        tier = max(1, min(3, self.evolution_tier))
        return f"{tier}-{self.current_mode + 1}"

    @property
    def level_name(self):
        """Return full level name like '1-1 DESERT VELOCITY'."""
        mode_name = MODE_NAMES.get(self.current_mode, "UNKNOWN")
        return f"{self.level_label} {mode_name}"
