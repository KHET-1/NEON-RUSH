import pygame
from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, DIFFICULTY_SETTINGS, DIFF_NORMAL


class GameMode:
    """Base class for all game modes (Desert, Excitebike, Micro Machines).

    Every mode implements:
        setup()          — initialize sprites, timers, state
        handle_event(e)  — process a single pygame event
        update(keys)     — advance one frame; returns 'gameover' | 'boss_defeated' | None
        draw(screen)     — render current frame to the given surface

    The main loop is mode-agnostic — it just calls these methods on current_mode.
    """

    # Override in subclass
    MODE_NAME = "BASE"
    MODE_INDEX = -1
    MUSIC_KEY = "desert"  # key into sound.music_loops

    # Boss trigger thresholds — override per mode
    BOSS_DISTANCE_THRESHOLD = 5.0   # km
    BOSS_SCORE_THRESHOLD = 5000
    BOSS_TIME_THRESHOLD = 180 * 60  # frames (3 min at 60fps)

    def __init__(self, particles, shake, shared_state):
        self.particles = particles
        self.shake = shake
        self.shared_state = shared_state
        self.players = []
        self.two_player = shared_state.num_players == 2
        self.difficulty = shared_state.difficulty
        self.game_distance = 0.0
        self.game_time = 0
        self.tick = 0

        # Boss state
        self.boss = None
        self.boss_active = False
        self.boss_eligible = False
        self.boss_check_timer = 0

        # Sprite groups — modes can add more
        self.all_sprites = pygame.sprite.Group()

    def setup(self):
        """Initialize mode. Called once when mode starts."""
        raise NotImplementedError

    def handle_event(self, event):
        """Handle a single pygame event. Return value ignored."""
        pass

    def update(self, keys):
        """Advance one frame. Returns 'gameover', 'boss_defeated', or None."""
        self.tick += 1
        self.game_time += 1
        return None

    def draw(self, screen):
        """Render current frame."""
        raise NotImplementedError

    def cleanup(self):
        """Called when leaving this mode. Clean up sprites."""
        for s in list(self.all_sprites):
            s.kill()
        self.particles.clear()

    # --- Boss trigger logic (shared across all 3 modes) ---

    def check_boss_trigger(self):
        """Check if boss should spawn. Call from update() after regular gameplay.
        Returns True if boss was just triggered."""
        if self.boss_active or self.boss is not None:
            return False

        # Check thresholds (time scales with difficulty)
        diff_s = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS[DIFF_NORMAL])
        time_threshold = int(self.BOSS_TIME_THRESHOLD * diff_s.get("boss_time_mult", 1.0))
        if (self.game_distance >= self.BOSS_DISTANCE_THRESHOLD and
                self._best_score() >= self.BOSS_SCORE_THRESHOLD and
                self.game_time >= time_threshold):
            self.boss_eligible = True

        if not self.boss_eligible:
            return False

        # 20% chance per second (check every 60 frames)
        self.boss_check_timer += 1
        if self.boss_check_timer >= 60:
            self.boss_check_timer = 0
            import random
            if random.random() < 0.20:
                return True
        return False

    def _best_score(self):
        if self.players:
            return max(p.score for p in self.players if p.alive)
        return 0

    def spawn_boss(self):
        """Override in subclass to create and return the boss."""
        raise NotImplementedError

    def get_alive_players(self):
        return [p for p in self.players if p.alive]
