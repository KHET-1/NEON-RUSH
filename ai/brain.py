"""Per-mode Q-learning brains for the AI evolution system.

Three brain classes inheriting from BaseBrain:
  - DesertBrain:     720 states × 12 actions =  8,640 Q-entries
  - ExcitebikeBrain: 972 states × 12 actions = 11,664 Q-entries
  - MicroBrain:    1,152 states × 12 actions = 13,824 Q-entries
"""
import math
import random
from collections import deque

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    ROAD_LEFT, ROAD_RIGHT,
    MODE_DESERT, MODE_EXCITEBIKE, MODE_MICROMACHINES,
)

# ── Name generator ──────────────────────────────────────────────
ADJECTIVES = [
    "Blaze", "Neon", "Ghost", "Volt", "Flux", "Pulse", "Zero", "Nova",
    "Hex", "Drift", "Echo", "Apex", "Void", "Surge", "Cryo", "Ion",
    "Arc", "Byte", "Zen", "Lux",
]
NOUNS = [
    "Runner", "Pilot", "Racer", "Storm", "Core", "Edge", "Wire",
    "Grid", "Node", "Spark",
]


def random_brain_name():
    return f"{random.choice(ADJECTIVES)} {random.choice(NOUNS)}"


# ── Base Brain ──────────────────────────────────────────────────

class BaseBrain:
    """Tabular Q-learning with configurable state/action spaces."""

    NUM_ACTIONS = 12  # move(3) × boost(2) × fire(2)

    def __init__(self, brain_id=0, name=None):
        self.id = brain_id
        self.name = name or random_brain_name()
        self.q_table = {}

        # Hyperparameters (mutable per-brain for dashboard tweaking)
        self.alpha = 0.15       # learning rate
        self.gamma = 0.95       # discount factor
        self.epsilon = 0.30     # exploration rate

        # Lineage
        self.generation = 0
        self.parent_ids = []
        self.origin = "fresh"   # fresh / crossover / mutation / elite

        # Stats
        self.total_episodes = 0
        self.total_frames = 0
        self.best_score = 0
        self.recent_scores = deque(maxlen=10)

        # Episode tracking (transient)
        self._prev_state = None
        self._prev_action = None
        self._prev_score = 0
        self._prev_lives = 0

    # ── Q-table access ──────────────────────────────────────────

    def _get_q(self, state_key):
        if state_key not in self.q_table:
            vals = [0.0] * self.NUM_ACTIONS
            # Slight bias toward straight movement (action indices where move=1)
            for i in range(self.NUM_ACTIONS):
                if self._move_from_action(i) == 1:
                    vals[i] = 0.1
            self.q_table[state_key] = vals
        return self.q_table[state_key]

    @staticmethod
    def _move_from_action(action_idx):
        """Extract move component: 0=left, 1=straight, 2=right."""
        return action_idx // 4

    # ── Action selection ────────────────────────────────────────

    def choose_action(self, state_key):
        """Epsilon-greedy action selection."""
        if random.random() < self.epsilon:
            return random.randint(0, self.NUM_ACTIONS - 1)
        q_vals = self._get_q(state_key)
        max_q = max(q_vals)
        best = [i for i, v in enumerate(q_vals) if v == max_q]
        return random.choice(best)

    def decode_action(self, action_idx):
        """Decode action index → (move, boost, fire).
        move:  0=left, 1=straight, 2=right
        boost: 0=no, 1=yes
        fire:  0=no, 1=yes
        """
        move = action_idx // 4
        remainder = action_idx % 4
        boost = remainder // 2
        fire = remainder % 2
        return move, boost, fire

    # ── Reward ──────────────────────────────────────────────────

    def compute_reward(self, player, mode, died=False, boss_hit=False):
        reward = 0.5  # survival reward

        current_score = getattr(player, 'score', 0)
        if current_score > self._prev_score:
            reward += (current_score - self._prev_score) * 0.01
        self._prev_score = current_score

        current_lives = getattr(player, 'lives', 0)
        if current_lives < self._prev_lives:
            reward -= 50
        self._prev_lives = current_lives

        if died:
            reward -= 200
        if boss_hit:
            reward += 30

        return reward

    # ── Learning ────────────────────────────────────────────────

    def learn(self, state, action, reward, next_state, done):
        """Q-learning update: Q(s,a) += alpha * (r + gamma * max Q(s',a') - Q(s,a))"""
        q_vals = self._get_q(state)
        if done:
            target = reward
        else:
            next_q = self._get_q(next_state)
            target = reward + self.gamma * max(next_q)
        q_vals[action] += self.alpha * (target - q_vals[action])
        self.q_table[state] = q_vals

        self.total_frames += 1

    # ── Episode lifecycle ───────────────────────────────────────

    def start_episode(self, player):
        self._prev_state = None
        self._prev_action = None
        self._prev_score = getattr(player, 'score', 0)
        self._prev_lives = getattr(player, 'lives', 3)

    def end_episode(self, score, frames=0):
        self.total_episodes += 1
        if score > self.best_score:
            self.best_score = score
        self.recent_scores.append(score)

    @property
    def avg_score(self):
        if not self.recent_scores:
            return 0
        return sum(self.recent_scores) / len(self.recent_scores)

    # ── State encoding (override in subclasses) ─────────────────

    def get_state(self, player, mode):
        """Override in subclass to produce mode-specific state key."""
        raise NotImplementedError

    def action_to_keys(self, action_idx, player):
        """Override in subclass to produce mode-specific _ai_keys dict."""
        raise NotImplementedError

    # ── Serialization ───────────────────────────────────────────

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "q_table": self.q_table,
            "alpha": self.alpha,
            "gamma": self.gamma,
            "epsilon": self.epsilon,
            "generation": self.generation,
            "parent_ids": self.parent_ids,
            "origin": self.origin,
            "total_episodes": self.total_episodes,
            "total_frames": self.total_frames,
            "best_score": self.best_score,
            "recent_scores": list(self.recent_scores),
        }

    @classmethod
    def from_dict(cls, data):
        brain = cls(brain_id=data.get("id", 0), name=data.get("name"))
        brain.q_table = data.get("q_table", {})
        brain.alpha = data.get("alpha", 0.15)
        brain.gamma = data.get("gamma", 0.95)
        brain.epsilon = data.get("epsilon", 0.30)
        brain.generation = data.get("generation", 0)
        brain.parent_ids = data.get("parent_ids", [])
        brain.origin = data.get("origin", "fresh")
        brain.total_episodes = data.get("total_episodes", 0)
        brain.total_frames = data.get("total_frames", 0)
        brain.best_score = data.get("best_score", 0)
        brain.recent_scores = deque(data.get("recent_scores", []), maxlen=10)
        return brain


# ── Desert Brain ────────────────────────────────────────────────

class DesertBrain(BaseBrain):
    """State: x_zone(5) × threat_dir(4) × threat_dist(3) × heat(3) × boss(2) × vuln(2) = 720"""

    def get_state(self, player, mode):
        if not hasattr(player, 'rect'):
            return "0,0,0,0,0,0"

        # Player X zone (0-4)
        px = player.rect.centerx
        x_zone = min(4, max(0, int(px / (SCREEN_WIDTH / 5))))

        # Nearest threat analysis
        threat_dir = 0  # 0=none, 1=left, 2=center, 3=right
        threat_dist = 0  # 0=far, 1=medium, 2=close
        py_pos = player.rect.top

        nearest_d = 999
        nearest = None
        for obs in mode.obstacles:
            dy = py_pos - obs.rect.bottom
            if -20 < dy < 300:
                h_dist = abs(obs.rect.centerx - px)
                if h_dist < 120 and dy < nearest_d:
                    nearest_d = dy
                    nearest = obs

        if nearest:
            diff = nearest.rect.centerx - px
            if diff < -40:
                threat_dir = 1
            elif diff > 40:
                threat_dir = 3
            else:
                threat_dir = 2
            if nearest_d < 60:
                threat_dist = 2
            elif nearest_d < 150:
                threat_dist = 1

        heat = getattr(player, 'heat', 0)
        heat_level = 0 if heat < 30 else (1 if heat < 70 else 2)

        boss_active = 1 if mode.boss_active else 0
        boss_vuln = 0
        if mode.boss and hasattr(mode.boss, 'vulnerable') and mode.boss.vulnerable:
            boss_vuln = 1

        return f"{x_zone},{threat_dir},{threat_dist},{heat_level},{boss_active},{boss_vuln}"

    def action_to_keys(self, action_idx, player):
        move, boost, fire = self.decode_action(action_idx)
        keys = {
            "up": True,
            "down": False,
            "left": move == 0,
            "right": move == 2,
            "boost": bool(boost),
            "fire": bool(fire),
        }
        return keys

    def compute_reward(self, player, mode, died=False, boss_hit=False):
        reward = super().compute_reward(player, mode, died, boss_hit)
        # Being near center is slightly rewarded
        if hasattr(player, 'rect'):
            center_dist = abs(player.rect.centerx - SCREEN_WIDTH // 2)
            if center_dist < 100:
                reward += 0.2
        return reward


# ── Excitebike Brain ────────────────────────────────────────────

class ExcitebikeBrain(BaseBrain):
    """State: lane(3) × danger_cur(3) × danger_adj(3) × speed_zone(3) × heat(3) × boss(2) × vuln(2) = 972

    Actions: lane_change(3) × accel(2) × fire(2) = 12
    lane_change: 0=up, 1=stay, 2=down
    accel: 0=coast, 1=accelerate
    fire: 0=no, 1=yes
    """

    def get_state(self, player, mode):
        # Current lane (0-2)
        lane = getattr(player, 'lane', 1)
        lane = min(2, max(0, lane))

        # Danger in current lane (0=safe, 1=some, 2=high)
        lane_danger = [0, 0, 0]
        for b in mode.barriers:
            if b.rect.left < SCREEN_WIDTH and b.rect.right > 0:
                dx = b.rect.left - player.rect.right
                if -30 < dx < 300:
                    for li in range(3):
                        lane_y = mode.bg.get_lane_y(li) + mode.bg.LANE_HEIGHT // 2
                        if abs(b.rect.centery - lane_y) < mode.bg.LANE_HEIGHT:
                            lane_danger[li] += max(0, 300 - dx)

        for r in mode.racers:
            dx = r.rect.left - player.rect.right
            if -30 < dx < 250:
                for li in range(3):
                    lane_y = mode.bg.get_lane_y(li) + mode.bg.LANE_HEIGHT // 2
                    if abs(r.rect.centery - lane_y) < mode.bg.LANE_HEIGHT:
                        lane_danger[li] += max(0, 250 - dx)

        for m in mode.mud_patches:
            dx = m.rect.left - player.rect.right
            if -30 < dx < 200:
                for li in range(3):
                    lane_y = mode.bg.get_lane_y(li) + mode.bg.LANE_HEIGHT // 2
                    if abs(m.rect.centery - lane_y) < mode.bg.LANE_HEIGHT:
                        lane_danger[li] += int(max(0, 100 - dx) * 0.3)

        # Discretize current lane danger
        cur_d = lane_danger[lane]
        danger_cur = 0 if cur_d < 50 else (1 if cur_d < 200 else 2)

        # Danger in adjacent lane (best escape option)
        adj_dangers = [lane_danger[i] for i in range(3) if i != lane]
        best_adj = min(adj_dangers) if adj_dangers else 0
        danger_adj = 0 if best_adj < 50 else (1 if best_adj < 200 else 2)

        # Speed zone
        speed = getattr(player, 'speed', 0)
        speed_zone = 0 if speed < 3 else (1 if speed < 6 else 2)

        heat = getattr(player, 'heat', 0)
        heat_level = 0 if heat < 30 else (1 if heat < 70 else 2)

        boss_active = 1 if mode.boss_active else 0
        boss_vuln = 0
        if mode.boss and hasattr(mode.boss, 'vulnerable') and mode.boss.vulnerable:
            boss_vuln = 1

        return f"{lane},{danger_cur},{danger_adj},{speed_zone},{heat_level},{boss_active},{boss_vuln}"

    def action_to_keys(self, action_idx, player):
        move, accel, fire = self.decode_action(action_idx)
        keys = {
            "up": move == 0,      # lane up
            "down": move == 2,    # lane down
            "accel": bool(accel),
            "brake": False,
            "boost": False,
            "fire": bool(fire),
        }
        return keys

    def compute_reward(self, player, mode, died=False, boss_hit=False):
        reward = super().compute_reward(player, mode, died, boss_hit)
        # Reward for being in the safest lane
        lane = getattr(player, 'lane', 1)
        lane_danger = [0, 0, 0]
        for b in mode.barriers:
            dx = b.rect.left - player.rect.right
            if -30 < dx < 200:
                for li in range(3):
                    lane_y = mode.bg.get_lane_y(li) + mode.bg.LANE_HEIGHT // 2
                    if abs(b.rect.centery - lane_y) < mode.bg.LANE_HEIGHT:
                        lane_danger[li] += 1
        safest = min(range(3), key=lambda i: lane_danger[i])
        if lane == safest:
            reward += 0.1
        return reward


# ── Micro Machines Brain ────────────────────────────────────────

class MicroBrain(BaseBrain):
    """State: angle_quad(4) × threat_dir(4) × threat_dist(3) × coin_dir(4) × heat(3) × boss(2) × vuln(2) = 1,152

    Actions: steer(3) × accel(2) × fire(2) = 12
    steer: 0=left, 1=straight, 2=right
    accel: 0=coast, 1=accelerate
    fire: 0=no, 1=yes
    """

    def get_state(self, player, mode):
        # Angle quadrant (0-3: N, E, S, W)
        angle = getattr(player, 'angle', 0)
        # Normalize to [0, 2pi)
        angle_norm = angle % (2 * math.pi)
        angle_quad = int(angle_norm / (math.pi / 2)) % 4

        # Nearest threat direction and distance
        threat_dir = 0  # 0=none, 1=ahead, 2=left, 3=right
        threat_dist = 0  # 0=far, 1=medium, 2=close
        px, py = getattr(player, 'px', player.rect.centerx), getattr(player, 'py', player.rect.centery)

        nearest_d = 999
        nearest_obs = None
        for grp in [mode.obstacles, mode.tiny_cars]:
            for obs in grp:
                dx = obs.rect.centerx - px
                dy = obs.rect.centery - py
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < nearest_d:
                    nearest_d = dist
                    nearest_obs = obs

        if nearest_obs and nearest_d < 200:
            dx = nearest_obs.rect.centerx - px
            dy = nearest_obs.rect.centery - py
            obs_angle = math.atan2(dy, dx)
            angle_diff = obs_angle - angle
            while angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            while angle_diff < -math.pi:
                angle_diff += 2 * math.pi
            if abs(angle_diff) < math.pi / 4:
                threat_dir = 1  # ahead
            elif angle_diff < 0:
                threat_dir = 2  # left
            else:
                threat_dir = 3  # right

            if nearest_d < 60:
                threat_dist = 2
            elif nearest_d < 120:
                threat_dist = 1

        # Nearest coin direction (0=none, 1=ahead, 2=left, 3=right)
        coin_dir = 0
        best_coin_d = 999
        best_coin = None
        for c in mode.coins_group:
            dx = c.rect.centerx - px
            dy = c.rect.centery - py
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < best_coin_d:
                best_coin_d = dist
                best_coin = c

        if best_coin and best_coin_d < 300:
            dx = best_coin.rect.centerx - px
            dy = best_coin.rect.centery - py
            coin_angle = math.atan2(dy, dx)
            angle_diff = coin_angle - angle
            while angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            while angle_diff < -math.pi:
                angle_diff += 2 * math.pi
            if abs(angle_diff) < math.pi / 4:
                coin_dir = 1  # ahead
            elif angle_diff < 0:
                coin_dir = 2  # left
            else:
                coin_dir = 3  # right

        heat = getattr(player, 'heat', 0)
        heat_level = 0 if heat < 30 else (1 if heat < 70 else 2)

        boss_active = 1 if mode.boss_active else 0
        boss_vuln = 0
        if mode.boss and hasattr(mode.boss, 'vulnerable') and mode.boss.vulnerable:
            boss_vuln = 1

        return f"{angle_quad},{threat_dir},{threat_dist},{coin_dir},{heat_level},{boss_active},{boss_vuln}"

    def action_to_keys(self, action_idx, player):
        steer, accel, fire = self.decode_action(action_idx)
        keys = {
            "up": bool(accel),
            "down": False,
            "left": steer == 0,
            "right": steer == 2,
            "boost": False,
            "fire": bool(fire),
        }
        return keys

    def compute_reward(self, player, mode, died=False, boss_hit=False):
        reward = super().compute_reward(player, mode, died, boss_hit)
        # Reward for staying away from walls
        px = getattr(player, 'px', SCREEN_WIDTH // 2)
        py_val = getattr(player, 'py', SCREEN_HEIGHT // 2)
        margin = 60
        if px < margin or px > SCREEN_WIDTH - margin or py_val < margin or py_val > SCREEN_HEIGHT - margin:
            reward -= 0.3
        return reward


# ── Brain class registry ────────────────────────────────────────

BRAIN_CLASSES = {
    MODE_DESERT: DesertBrain,
    MODE_EXCITEBIKE: ExcitebikeBrain,
    MODE_MICROMACHINES: MicroBrain,
}

MODE_BRAIN_NAMES = {
    MODE_DESERT: "desert",
    MODE_EXCITEBIKE: "excitebike",
    MODE_MICROMACHINES: "micro",
}
