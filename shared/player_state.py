class SharedPlayerState:
    """Carries persistent state between modes. Score/lives/coins survive transitions."""

    def __init__(self, num_players=1, difficulty="normal", ai_config=None):
        self.num_players = num_players
        self.difficulty = difficulty
        self.ai_config = ai_config or {"ai_players": [], "score_mult": 1}
        self.scores = [0] * num_players
        self.coins = [0] * num_players
        self.lives = [3] * num_players
        self.total_distance = 0.0
        self.total_time = 0
        self.bosses_defeated = 0
        self.current_mode = 0  # 0=desert, 1=excitebike, 2=micromachines

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

    @property
    def best_score(self):
        return max(self.scores) if self.scores else 0

    @property
    def total_coins(self):
        return sum(self.coins)

    @property
    def all_modes_complete(self):
        return self.bosses_defeated >= 3
