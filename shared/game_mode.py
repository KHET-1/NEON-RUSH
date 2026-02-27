import pygame
import random
from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, DIFFICULTY_SETTINGS, DIFF_NORMAL,
    ASTEROID_GLOW, SOLAR_YELLOW, SOLAR_WHITE, NEON_CYAN,
)


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

        # Phase system: normal → asteroids → boss
        self.phase = 'normal'
        self.asteroids = pygame.sprite.Group()
        self.asteroid_timer = 0
        self.asteroids_cleared = 0
        self.ASTEROID_CLEAR_TARGET = 15

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
        for a in list(self.asteroids):
            a.kill()
        for s in list(self.all_sprites):
            s.kill()
        self.particles.clear()

    # --- Boss trigger logic (shared across all 3 modes) ---

    def check_asteroid_trigger(self):
        """Check if asteroid phase should start. Returns True at 50% of boss thresholds."""
        if self.phase != 'normal' or self.boss_active or self.boss is not None:
            return False
        diff_s = DIFFICULTY_SETTINGS.get(self.difficulty, DIFFICULTY_SETTINGS[DIFF_NORMAL])
        time_threshold = int(self.BOSS_TIME_THRESHOLD * diff_s.get("boss_time_mult", 1.0))
        half_dist = self.BOSS_DISTANCE_THRESHOLD * 0.5
        half_score = self.BOSS_SCORE_THRESHOLD * 0.5
        half_time = time_threshold * 0.5
        return (self.game_distance >= half_dist and
                self._best_score() >= half_score and
                self.game_time >= half_time)

    def start_asteroid_phase(self):
        """Transition to asteroid phase."""
        self.phase = 'asteroids'
        self.asteroids_cleared = 0
        self.asteroid_timer = 0

    def start_boss_phase(self):
        """Transition from asteroids to boss fight."""
        self.phase = 'boss'
        for a in list(self.asteroids):
            a.kill()

    def check_boss_trigger(self):
        """Check if boss should spawn. Only triggers from asteroid phase
        when enough asteroids are cleared. Returns True if boss was just triggered."""
        if self.boss_active or self.boss is not None:
            return False
        if self.phase != 'asteroids':
            return False
        if self.asteroids_cleared < self.ASTEROID_CLEAR_TARGET:
            return False

        # 20% chance per second (check every 60 frames)
        self.boss_check_timer += 1
        if self.boss_check_timer >= 60:
            self.boss_check_timer = 0
            if random.random() < 0.20:
                return True
        return False

    def draw_asteroid_hud(self, screen):
        """Draw asteroid progress bar during asteroid phase."""
        if self.phase != 'asteroids':
            return
        from core.fonts import FONT_HUD_SM
        cleared = min(self.asteroids_cleared, self.ASTEROID_CLEAR_TARGET)
        pct = cleared / self.ASTEROID_CLEAR_TARGET

        bar_w = 200
        bar_h = 14
        bx = SCREEN_WIDTH // 2 - bar_w // 2
        by = SCREEN_HEIGHT - 32

        # Background
        pygame.draw.rect(screen, (20, 20, 30), (bx - 2, by - 2, bar_w + 4, bar_h + 4))
        # Fill
        fill_w = int(bar_w * pct)
        if fill_w > 0:
            color = SOLAR_YELLOW if pct < 1.0 else NEON_CYAN
            pygame.draw.rect(screen, color, (bx, by, fill_w, bar_h))
        # Border
        pygame.draw.rect(screen, ASTEROID_GLOW, (bx - 2, by - 2, bar_w + 4, bar_h + 4), 1)
        # Label
        label = FONT_HUD_SM.render(f"ASTEROIDS {cleared}/{self.ASTEROID_CLEAR_TARGET}", True, SOLAR_WHITE)
        screen.blit(label, (bx + bar_w // 2 - label.get_width() // 2, by - 18))

    def _best_score(self):
        if self.players:
            return max(p.score for p in self.players if p.alive)
        return 0

    def spawn_boss(self):
        """Override in subclass to create and return the boss."""
        raise NotImplementedError

    def get_alive_players(self):
        return [p for p in self.players if p.alive]
