"""Q-learning brain and key-simulation classes for autoplay.

LearningBrain  — tabular Q-learning brain that persists across runs
SmartKeys      — learning AI that uses Q-table to decide actions
FakeKeys       — heuristic AI (non-learning baseline)
"""
import json
import os
import random

BRAIN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          ".neon_rush_brain.json")


# ══════════════════════════════════════════════════════════════════
#  LEARNING AI — Q-Learning Brain
# ══════════════════════════════════════════════════════════════════

class LearningBrain:
    """Tabular Q-learning brain that persists across runs.

    State space (discrete):
        - Player X zone:       5 zones (0-4, left to right)
        - Threat direction:    4 (none, left, center, right)
        - Threat distance:     3 (far, medium, close)
        - Heat level:          3 (low <30, medium 30-70, high >70)
        - Boss active:         2 (no, yes)
        - Boss vulnerable:     2 (no, yes)
        Total: 5 * 4 * 3 * 3 * 2 * 2 = 720 states

    Action space:
        - Move:  3 (left, straight, right)
        - Boost: 2 (no, yes)
        - Fire:  2 (no, yes)
        Total: 3 * 2 * 2 = 12 actions

    Q-table: 720 * 12 = 8,640 entries
    """

    ALPHA = 0.15       # Learning rate
    GAMMA = 0.95       # Discount factor
    EPSILON_START = 0.3
    EPSILON_MIN = 0.02
    EPSILON_DECAY = 0.9995  # Per frame

    def __init__(self, brain_file=BRAIN_FILE):
        self.brain_file = brain_file
        self.q_table = {}       # state_key -> [q_values for 12 actions]
        self.epsilon = self.EPSILON_START
        self.total_episodes = 0
        self.total_frames_trained = 0
        self.best_score = 0
        self.best_survival = 0
        self._prev_state = None
        self._prev_action = None
        self._prev_score = 0
        self._prev_lives = 0
        self.episode_reward = 0
        self.load()

    def load(self):
        if os.path.exists(self.brain_file):
            try:
                with open(self.brain_file, 'r') as f:
                    data = json.load(f)
                self.q_table = data.get("q_table", {})
                self.total_episodes = data.get("total_episodes", 0)
                self.total_frames_trained = data.get("total_frames_trained", 0)
                self.best_score = data.get("best_score", 0)
                self.best_survival = data.get("best_survival", 0)
                # Resume epsilon from where we left off
                self.epsilon = max(self.EPSILON_MIN,
                                   self.EPSILON_START * (self.EPSILON_DECAY ** self.total_frames_trained))
            except (json.JSONDecodeError, KeyError):
                pass  # Start fresh

    def save(self):
        data = {
            "q_table": self.q_table,
            "total_episodes": self.total_episodes,
            "total_frames_trained": self.total_frames_trained,
            "best_score": self.best_score,
            "best_survival": self.best_survival,
            "q_table_size": len(self.q_table),
            "epsilon": self.epsilon,
        }
        tmp = self.brain_file + ".tmp"
        with open(tmp, 'w') as f:
            json.dump(data, f)
        os.replace(tmp, self.brain_file)

    def _get_state(self, player, mode, threats):
        """Discretize the game state into a hashable key."""
        if not hasattr(player, 'rect'):
            return "0,0,0,0,0,0"

        # Player X zone (0-4)
        px = player.rect.centerx
        x_zone = min(4, max(0, int(px / 160)))

        # Nearest threat analysis
        threat_dir = 0   # 0=none
        threat_dist = 0  # 0=far
        py_pos = player.rect.top

        nearest = None
        nearest_d = 999
        for t in threats:
            dy = py_pos - t.rect.bottom
            if -20 < dy < 300:
                h_dist = abs(t.rect.centerx - px)
                if h_dist < 120:
                    if dy < nearest_d:
                        nearest_d = dy
                        nearest = t

        if nearest:
            diff = nearest.rect.centerx - px
            if diff < -40:
                threat_dir = 1  # threat is left
            elif diff > 40:
                threat_dir = 3  # threat is right
            else:
                threat_dir = 2  # threat is center

            if nearest_d < 60:
                threat_dist = 2  # close
            elif nearest_d < 150:
                threat_dist = 1  # medium
            # else 0 = far

        # Heat level
        heat = getattr(player, 'heat', 0)
        heat_level = 0 if heat < 30 else (1 if heat < 70 else 2)

        # Boss state
        boss_active = 1 if (mode and mode.boss_active) else 0
        boss_vuln = 0
        if mode and mode.boss and hasattr(mode.boss, 'vulnerable') and mode.boss.vulnerable:
            boss_vuln = 1

        return f"{x_zone},{threat_dir},{threat_dist},{heat_level},{boss_active},{boss_vuln}"

    def _get_q(self, state_key):
        if state_key not in self.q_table:
            # Initialize with slight bias: straight=0.1, others=0
            self.q_table[state_key] = [0.0] * 12
            # Bias toward going straight (action indices 1,4,7,10 have move=1=straight)
            for i in range(12):
                if (i // 4) == 1:  # straight
                    self.q_table[state_key][i] = 0.1
        return self.q_table[state_key]

    def choose_action(self, state_key):
        """Epsilon-greedy action selection."""
        if random.random() < self.epsilon:
            return random.randint(0, 11)
        q_vals = self._get_q(state_key)
        max_q = max(q_vals)
        # Break ties randomly
        best = [i for i, v in enumerate(q_vals) if v == max_q]
        return random.choice(best)

    def decode_action(self, action_idx):
        """Decode action index into (move, boost, fire).
        move: 0=left, 1=straight, 2=right
        boost: 0=no, 1=yes
        fire: 0=no, 1=yes
        """
        move = action_idx // 4
        remainder = action_idx % 4
        boost = remainder // 2
        fire = remainder % 2
        return move, boost, fire

    def compute_reward(self, player, mode, died=False, boss_hit=False):
        """Compute reward for the current frame."""
        reward = 0.5  # Small reward for surviving each frame

        # Score increase reward
        current_score = getattr(player, 'score', 0)
        if current_score > self._prev_score:
            reward += (current_score - self._prev_score) * 0.01
        self._prev_score = current_score

        # Life loss penalty
        current_lives = getattr(player, 'lives', 0)
        if current_lives < self._prev_lives:
            reward -= 50
        self._prev_lives = current_lives

        # Death penalty
        if died:
            reward -= 200

        # Boss damage reward
        if boss_hit:
            reward += 30

        # Being near center is slightly rewarded
        if hasattr(player, 'rect'):
            center_dist = abs(player.rect.centerx - 400)
            if center_dist < 100:
                reward += 0.2

        return reward

    def learn(self, state, action, reward, next_state, done):
        """Q-learning update: Q(s,a) += alpha * (r + gamma * max Q(s',a') - Q(s,a))"""
        q_vals = self._get_q(state)
        if done:
            target = reward
        else:
            next_q = self._get_q(next_state)
            target = reward + self.GAMMA * max(next_q)
        q_vals[action] += self.ALPHA * (target - q_vals[action])
        self.q_table[state] = q_vals

        # Decay epsilon
        self.epsilon = max(self.EPSILON_MIN, self.epsilon * self.EPSILON_DECAY)
        self.total_frames_trained += 1

    def start_episode(self, player):
        """Call at the start of each episode/run."""
        self._prev_state = None
        self._prev_action = None
        self._prev_score = getattr(player, 'score', 0)
        self._prev_lives = getattr(player, 'lives', 3)
        self.episode_reward = 0

    def end_episode(self, score, frames):
        """Call at the end of each episode/run."""
        self.total_episodes += 1
        if score > self.best_score:
            self.best_score = score
        if frames > self.best_survival:
            self.best_survival = frames

    def stats_str(self):
        return (f"Brain: {len(self.q_table)} states | "
                f"eps={self.epsilon:.3f} | "
                f"episodes={self.total_episodes} | "
                f"best={self.best_score:,}")


# ══════════════════════════════════════════════════════════════════
#  LEARNING KEY SIMULATOR
# ══════════════════════════════════════════════════════════════════

class SmartKeys:
    """Learning AI that uses Q-table to decide actions. Falls back to heuristic for untrained states."""

    def __init__(self, brain, num_players=1):
        self.brain = brain
        self.num_players = num_players
        self._pressed = {}
        self._frame = 0
        self._threats_cache = []

    def tick(self, mode=None, players=None, boss_active=False):
        import pygame
        self._frame += 1
        self._pressed.clear()

        if not players:
            return

        # Gather threats
        threats = []
        if mode and hasattr(mode, 'all_sprites'):
            for sprite in mode.all_sprites:
                if sprite not in players and hasattr(sprite, 'rect'):
                    if 0 <= sprite.rect.y <= 700:
                        threats.append(sprite)
        self._threats_cache = threats

        for p in players:
            if not p.alive:
                continue

            if p.player_num == 1:
                k_up, k_down, k_left, k_right = (
                    pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d)
                k_boost = pygame.K_LSHIFT
                k_fire = pygame.K_e
            else:
                k_up, k_down, k_left, k_right = (
                    pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT)
                k_boost = pygame.K_RSHIFT
                k_fire = pygame.K_RETURN

            # Always accelerate
            self._pressed[k_up] = True

            # Get current state
            state = self.brain._get_state(p, mode, threats)

            # Compute reward from previous action
            died = not p.alive
            reward = self.brain.compute_reward(p, mode, died=died)
            self.brain.episode_reward += reward

            # Learn from previous step
            if self.brain._prev_state is not None:
                self.brain.learn(self.brain._prev_state, self.brain._prev_action,
                                 reward, state, died)

            # Choose action
            action_idx = self.brain.choose_action(state)
            move, boost, fire = self.brain.decode_action(action_idx)

            # Apply move
            if move == 0:
                self._pressed[k_left] = True
            elif move == 2:
                self._pressed[k_right] = True
            # move == 1: straight (no key)

            # Apply boost (only if we have heat and not in ghost mode)
            shooting_phase_active = boss_active or (mode and getattr(mode, 'phase', '') == 'asteroids')
            if boost and hasattr(p, 'heat') and p.heat > 50 and not getattr(p, 'ghost_mode', False):
                if not shooting_phase_active:  # Save heat for bolts during boss/asteroids
                    self._pressed[k_boost] = True

            # Apply fire (during boss or asteroid phase if we have heat)
            shooting_phase = boss_active or (mode and getattr(mode, 'phase', '') == 'asteroids')
            if fire and shooting_phase and hasattr(p, 'heat') and p.heat >= 42:
                if hasattr(p, 'fire_cooldown') and p.fire_cooldown <= 0:
                    self._pressed[k_fire] = True

            # --- Boss combat override: ram during vulnerability ---
            if boss_active and mode and mode.boss and hasattr(mode.boss, 'vulnerable'):
                if mode.boss.vulnerable and hasattr(mode.boss, 'rect') and hasattr(p, 'rect'):
                    if p.rect.centerx < mode.boss.rect.centerx - 15:
                        self._pressed[k_right] = True
                        self._pressed.pop(k_left, None)
                    elif p.rect.centerx > mode.boss.rect.centerx + 15:
                        self._pressed[k_left] = True
                        self._pressed.pop(k_right, None)

            # Save state for next learning step
            self.brain._prev_state = state
            self.brain._prev_action = action_idx

    def __getitem__(self, key):
        return self._pressed.get(key, False)


# ══════════════════════════════════════════════════════════════════
#  HEURISTIC AI (non-learning baseline)
# ══════════════════════════════════════════════════════════════════

class FakeKeys:
    """Simulates pygame.key.get_pressed() with heuristic-driven inputs."""

    def __init__(self, num_players=1):
        self.num_players = num_players
        self._pressed = {}
        self._frame = 0
        self._dodge_dir = 0
        self._dodge_timer = 0

    def tick(self, mode=None, players=None, boss_active=False):
        import pygame
        self._frame += 1
        self._pressed.clear()

        if not players:
            return

        threats = []
        if mode and hasattr(mode, 'all_sprites'):
            for sprite in mode.all_sprites:
                if sprite not in players and hasattr(sprite, 'rect'):
                    if 0 <= sprite.rect.y <= 700:
                        threats.append(sprite)

        for p in players:
            if not p.alive:
                continue

            if p.player_num == 1:
                k_up, k_down, k_left, k_right = (
                    pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d)
                k_boost = pygame.K_LSHIFT
                k_fire = pygame.K_e
            else:
                k_up, k_down, k_left, k_right = (
                    pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT)
                k_boost = pygame.K_RSHIFT
                k_fire = pygame.K_RETURN

            self._pressed[k_up] = True

            dodge = 0
            if hasattr(p, 'rect'):
                px = p.rect.centerx
                py_pos = p.rect.top
                nearest_threat = None
                nearest_dist = 999

                for t in threats:
                    dy = py_pos - t.rect.bottom
                    if -20 < dy < 250:
                        h_dist = abs(t.rect.centerx - px)
                        if h_dist < 80:
                            if dy < nearest_dist:
                                nearest_dist = dy
                                nearest_threat = t

                if nearest_threat:
                    if nearest_threat.rect.centerx > px:
                        dodge = -1
                    else:
                        dodge = 1
                    if nearest_dist < 80:
                        dodge *= 2
                else:
                    if self._dodge_timer <= 0:
                        self._dodge_dir = random.choice([-1, 0, 0, 0, 1])
                        self._dodge_timer = random.randint(40, 100)
                    self._dodge_timer -= 1
                    dodge = self._dodge_dir
                    center_x = 400
                    if px < center_x - 100:
                        dodge = 1
                    elif px > center_x + 100:
                        dodge = -1

            if dodge < 0:
                self._pressed[k_left] = True
            elif dodge > 0:
                self._pressed[k_right] = True

            if boss_active and mode and mode.boss and mode.boss.alive:
                boss = mode.boss
                if hasattr(p, 'heat') and p.heat >= 42 and hasattr(p, 'fire_cooldown') and p.fire_cooldown <= 0:
                    self._pressed[k_fire] = True
                if boss.vulnerable and hasattr(boss, 'rect') and hasattr(p, 'rect'):
                    if p.rect.centerx < boss.rect.centerx - 10:
                        self._pressed[k_right] = True
                        self._pressed.pop(k_left, None)
                    elif p.rect.centerx > boss.rect.centerx + 10:
                        self._pressed[k_left] = True
                        self._pressed.pop(k_right, None)
                    self._pressed[k_up] = True
            elif mode and getattr(mode, 'phase', '') == 'asteroids':
                # Fire at asteroids during asteroid phase
                if hasattr(p, 'heat') and p.heat >= 42 and hasattr(p, 'fire_cooldown') and p.fire_cooldown <= 0:
                    self._pressed[k_fire] = True
                # Steer toward nearest asteroid to line up shots
                best_ast = None
                best_d = 9999
                for ast in getattr(mode, 'asteroids', []):
                    if not getattr(ast, '_projected', True):
                        continue
                    d = abs(ast.rect.centerx - px)
                    if d < best_d:
                        best_d = d
                        best_ast = ast
                if best_ast:
                    dx = best_ast.rect.centerx - px
                    if abs(dx) > 15:
                        self._pressed.pop(k_left, None)
                        self._pressed.pop(k_right, None)
                        if dx < 0:
                            self._pressed[k_left] = True
                        else:
                            self._pressed[k_right] = True
            else:
                if hasattr(p, 'heat') and p.heat > 70 and not getattr(p, 'ghost_mode', False):
                    self._pressed[k_boost] = True

    def __getitem__(self, key):
        return self._pressed.get(key, False)
