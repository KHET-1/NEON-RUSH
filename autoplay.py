#!/usr/bin/env python3
"""NEON RUSH — Automated Playtest Script

Plays the game automatically with simulated inputs.
Supports headed (visual) and headless modes, speed up to 6x.
Grid mode shows up to 6 games simultaneously in one window.
Learning mode uses Q-learning AI that improves over runs.

Usage:
    python3 autoplay.py                          # headed, 1x speed, 1 run
    python3 autoplay.py --headless               # headless (no window)
    python3 autoplay.py --speed 4                # 4x speed
    python3 autoplay.py --runs 6                 # play 6 times sequentially
    python3 autoplay.py --grid                   # 6 games visible at once!
    python3 autoplay.py --grid -s 2 --god        # 6 games, 2x speed, god mode
    python3 autoplay.py --grid --learn           # 6 learning AIs competing!
    python3 autoplay.py --learn -r 6 -s 6 --headless  # fast training
"""
import argparse
import os
import sys
import random
import time
import math
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BRAIN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".neon_rush_brain.json")


def parse_args():
    p = argparse.ArgumentParser(description="NEON RUSH autoplay tester")
    p.add_argument("--headless", action="store_true", help="Run without display")
    p.add_argument("--grid", action="store_true",
                   help="Run 6 games simultaneously in a tiled grid window")
    p.add_argument("-s", "--speed", type=int, default=1, choices=range(1, 7),
                   help="Speed multiplier 1-6x (default: 1)")
    p.add_argument("-r", "--runs", type=int, default=1,
                   help="Number of sequential playthroughs (max 6, default: 1)")
    p.add_argument("-d", "--difficulty", default="normal",
                   choices=["easy", "normal", "hard"],
                   help="Difficulty (default: normal)")
    p.add_argument("--max-frames", type=int, default=0,
                   help="Max frames per run (0=unlimited, default: 0)")
    p.add_argument("--players", type=int, default=1, choices=[1, 2],
                   help="Number of players (default: 1)")
    p.add_argument("--god", action="store_true",
                   help="God mode — AI can't die (for testing bosses/transitions)")
    p.add_argument("--learn", action="store_true",
                   help="Enable learning AI (Q-learning, persists to .neon_rush_brain.json)")
    p.add_argument("--evo", action="store_true",
                   help="Enable evolution mode — cycle through levels with increasing difficulty")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="Print frame-by-frame stats")
    args = p.parse_args()
    args.runs = min(args.runs, 6)
    return args


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
            if boost and hasattr(p, 'heat') and p.heat > 50 and not getattr(p, 'ghost_mode', False):
                if not boss_active:  # Save heat for bolts during boss
                    self._pressed[k_boost] = True

            # Apply fire (only during boss if we have heat)
            if fire and boss_active and hasattr(p, 'heat') and p.heat >= 42:
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
            else:
                if hasattr(p, 'heat') and p.heat > 70 and not getattr(p, 'ghost_mode', False):
                    self._pressed[k_boost] = True

    def __getitem__(self, key):
        return self._pressed.get(key, False)


# ══════════════════════════════════════════════════════════════════
#  RUN STATS
# ══════════════════════════════════════════════════════════════════

class RunStats:
    def __init__(self, run_num):
        self.run_num = run_num
        self.frames = 0
        self.start_time = time.time()
        self.end_time = None
        self.result = "running"
        self.modes_played = []
        self.final_score = 0
        self.final_distance = 0.0
        self.bosses_defeated = 0
        self.deaths = 0
        self.transitions = 0

    def finish(self, result, shared_state=None, current_mode=None):
        self.end_time = time.time()
        self.result = result
        if shared_state:
            self.bosses_defeated = shared_state.bosses_defeated
            self.final_score = shared_state.best_score
            self.final_distance = shared_state.total_distance
        if current_mode:
            live_score = max((p.score for p in current_mode.players), default=0)
            live_dist = current_mode.game_distance
            if live_score > self.final_score:
                self.final_score = live_score
            if live_dist > self.final_distance:
                self.final_distance = live_dist

    @property
    def elapsed(self):
        end = self.end_time or time.time()
        return end - self.start_time

    def summary_line(self):
        elapsed = self.elapsed
        return (f"  Run {self.run_num}: {self.result:<12} | "
                f"{self.frames:>7} frames | "
                f"{elapsed:>6.1f}s wall | "
                f"Score {self.final_score:>8} | "
                f"Dist {self.final_distance:>6.1f}km | "
                f"Bosses {self.bosses_defeated}/3 | "
                f"Modes: {', '.join(self.modes_played) or 'none'}")


# ══════════════════════════════════════════════════════════════════
#  GAME INSTANCE (for grid mode)
# ══════════════════════════════════════════════════════════════════

class GameInstance:
    def __init__(self, slot_num, difficulty, num_players, god_mode, brain=None, evo=False):
        from core.particles import ParticleSystem
        from core.shake import ScreenShake
        from shared.player_state import SharedPlayerState
        from modes.desert_velocity import DesertVelocityMode
        from modes.excitebike import ExcitebikeMode
        from modes.micromachines import MicroMachinesMode
        from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, STATE_PLAY

        self.slot = slot_num
        self.god_mode = god_mode
        self.brain = brain
        self.evo_mgr = None
        if evo:
            from core.evolution import EvolutionManager
            self.evo_mgr = EvolutionManager()
            self.evo_mgr.enabled = True
            self.evo_mgr.start_run()
        self.screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.particles = ParticleSystem()
        self.shake = ScreenShake()
        self.shared_state = SharedPlayerState(
            num_players, difficulty,
            evolution_tier=self.evo_mgr.current_tier if self.evo_mgr else 1)
        self.MODE_CLASSES = [DesertVelocityMode, ExcitebikeMode, MicroMachinesMode]
        self.current_mode = self.MODE_CLASSES[0](self.particles, self.shake, self.shared_state)
        self.current_mode.setup()
        self.state = STATE_PLAY
        self.transition = None
        self.difficulty = difficulty

        if brain:
            self.fake_keys = SmartKeys(brain, num_players)
            # Start episode tracking
            if self.current_mode.players:
                brain.start_episode(self.current_mode.players[0])
        else:
            self.fake_keys = FakeKeys(num_players)

        self.stats = RunStats(slot_num)
        self.stats.modes_played.append(self.current_mode.MODE_NAME)
        self.finished = False
        random.seed(time.time_ns() + slot_num * 12345)

    def tick(self):
        if self.finished:
            return False

        import pygame
        from core.constants import STATE_PLAY, STATE_TRANSITION, STATE_VICTORY, MODE_NAMES

        if self.state == STATE_PLAY:
            if self.god_mode and self.current_mode:
                for p in self.current_mode.players:
                    p.invincible_timer = max(p.invincible_timer, 10)
                    p.lives = max(p.lives, 3)

            boss_active = self.current_mode.boss_active if self.current_mode else False
            self.fake_keys.tick(
                mode=self.current_mode,
                players=self.current_mode.players if self.current_mode else [],
                boss_active=boss_active)

            if self.current_mode:
                result = self.current_mode.update(self.fake_keys)
                self.current_mode.draw(self.screen)

                if result == 'gameover':
                    self.stats.deaths += 1
                    self.stats.finish('GAME OVER', self.shared_state, self.current_mode)
                    self.finished = True
                    # Final learning step with death penalty
                    if self.brain and self.brain._prev_state is not None:
                        self.brain.learn(self.brain._prev_state, self.brain._prev_action,
                                         -200, self.brain._prev_state, True)
                    if self.brain:
                        self.brain.end_episode(self.stats.final_score, self.stats.frames)
                    self._draw_overlay("GAME OVER")
                elif result == 'boss_defeated':
                    # Reward for boss kill
                    if self.brain and self.brain._prev_state is not None:
                        self.brain.learn(self.brain._prev_state, self.brain._prev_action,
                                         500, self.brain._prev_state, False)
                    self._advance_to_next_mode()

        elif self.state == STATE_TRANSITION:
            if self.transition:
                self.transition.update()
                self.transition.draw(self.screen)
                if self.transition.done:
                    self.transition = None
                    if self.current_mode:
                        self.current_mode.setup()
                        self.stats.modes_played.append(self.current_mode.MODE_NAME)
                    self.state = STATE_PLAY

        elif self.state == STATE_VICTORY:
            self.stats.finish('VICTORY', self.shared_state, self.current_mode)
            self.finished = True
            if self.brain:
                if self.brain._prev_state is not None:
                    self.brain.learn(self.brain._prev_state, self.brain._prev_action,
                                     1000, self.brain._prev_state, True)
                self.brain.end_episode(self.stats.final_score, self.stats.frames)
            self._draw_overlay("VICTORY!")

        self.stats.frames += 1
        return not self.finished

    def _advance_to_next_mode(self):
        from shared.transition import TransitionEffect
        from core.constants import STATE_TRANSITION, STATE_VICTORY, MODE_NAMES

        mode_idx = self.shared_state.current_mode
        if mode_idx >= len(self.MODE_CLASSES):
            if self.evo_mgr and self.evo_mgr.enabled:
                new_tier = self.evo_mgr.advance_cycle()
                self.shared_state.reset_for_cycle(new_tier)
                from_surface = self.screen.copy()
                if self.current_mode:
                    self.current_mode.cleanup()
                self.transition = TransitionEffect(
                    'glitch', f"EVOLUTION V{new_tier}!",
                    from_surface, evolution_tier=new_tier)
                self.stats.transitions += 1
                self.state = STATE_TRANSITION
                self.current_mode = self.MODE_CLASSES[0](
                    self.particles, self.shake, self.shared_state)
                return
            self.state = STATE_VICTORY
            return
        from_surface = self.screen.copy()
        if self.current_mode:
            self.current_mode.cleanup()
        styles = ['zoom_rotate', 'scanline', 'glitch']
        style = styles[min(mode_idx, len(styles) - 1)]
        mode_name = MODE_NAMES[mode_idx] if mode_idx < len(MODE_NAMES) else "???"
        self.transition = TransitionEffect(style, mode_name, from_surface,
                                           evolution_tier=self.shared_state.evolution_tier)
        self.stats.transitions += 1
        self.state = STATE_TRANSITION
        self.current_mode = self.MODE_CLASSES[mode_idx](
            self.particles, self.shake, self.shared_state)

    def _draw_overlay(self, text):
        import core.fonts as _fonts
        overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        font = _fonts.FONT_TITLE if _fonts.FONT_TITLE else pygame.font.SysFont("freesans", 48)
        color = (0, 255, 255) if "VICTORY" in text else (255, 80, 80)
        rendered = font.render(text, True, color)
        x = 400 - rendered.get_width() // 2
        y = 280 - rendered.get_height() // 2
        self.screen.blit(rendered, (x, y))


# ══════════════════════════════════════════════════════════════════
#  GRID MODE
# ══════════════════════════════════════════════════════════════════

def run_grid(args):
    from core.fonts import init_fonts
    from core.sound import init_sounds
    from core.constants import FPS, NEON_CYAN, SOLAR_YELLOW

    init_fonts()
    init_sounds()

    # Shared brain if learning mode
    brain = LearningBrain() if args.learn else None

    COLS, ROWS = 3, 2
    THUMB_W, THUMB_H = 480, 360
    PAD = 4
    HEADER = 28
    GRID_W = COLS * THUMB_W + (COLS + 1) * PAD
    GRID_H = ROWS * (THUMB_H + HEADER) + (ROWS + 1) * PAD + 40

    display = pygame.display.set_mode((GRID_W, GRID_H))
    pygame.display.set_caption(
        f"NEON RUSH — {'Learning' if args.learn else 'Autoplay'} Grid (6 games)")

    clock = pygame.time.Clock()
    target_fps = FPS * args.speed

    label_font = pygame.font.SysFont("freesans", 16, bold=True)
    title_font = pygame.font.SysFont("freesans", 20, bold=True)

    difficulties = ["easy", "normal", "hard", "easy", "normal", "hard"]
    games = [GameInstance(i + 1, difficulties[i], args.players, args.god, brain, evo=args.evo)
             for i in range(6)]

    total_start = time.time()
    frame_count = 0
    max_frames = args.max_frames if args.max_frames > 0 else float('inf')
    generation = 1

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False

        # Tick all games
        any_alive = False
        for g in games:
            if not g.finished:
                g.tick()
                any_alive = True

        # Auto-restart finished games in learning mode
        if args.learn and not any_alive:
            brain.save()
            generation += 1
            print(f"  Gen {generation} | {brain.stats_str()}")
            games = [GameInstance(i + 1, difficulties[i], args.players, args.god, brain, evo=args.evo)
                     for i in range(6)]
            any_alive = True

        if not args.learn and not any_alive:
            if frame_count > max(g.stats.frames for g in games) + 180:
                running = False

        if frame_count >= max_frames:
            running = False

        # --- Draw the grid ---
        display.fill((10, 10, 20))

        elapsed = time.time() - total_start
        alive_count = sum(1 for g in games if not g.finished)
        brain_str = f"  |  {brain.stats_str()}" if brain else ""
        mode_label = "LEARNING" if args.learn else "AUTOPLAY"
        evo_str = "  |  EVO" if args.evo else ""
        top_text = title_font.render(
            f"NEON RUSH {mode_label}  |  {args.speed}x  |  "
            f"{alive_count}/6 Live  |  Gen {generation}  |  "
            f"{elapsed:.0f}s{'  |  GOD' if args.god else ''}"
            f"{evo_str}{brain_str}",
            True, NEON_CYAN)
        display.blit(top_text, (PAD + 4, 8))

        for idx, g in enumerate(games):
            col = idx % COLS
            row = idx // COLS
            x = PAD + col * (THUMB_W + PAD)
            y = 40 + PAD + row * (THUMB_H + HEADER + PAD)

            mode_name = g.current_mode.MODE_NAME if g.current_mode else "???"
            score = 0
            dist = 0.0
            if g.current_mode and g.current_mode.players:
                score = max((p.score for p in g.current_mode.players), default=0)
                dist = g.current_mode.game_distance
            boss_str = " [BOSS]" if (g.current_mode and g.current_mode.boss_active) else ""
            status = g.stats.result if g.finished else "PLAYING"
            diff_label = g.difficulty.upper()
            tier_str = f" V{g.shared_state.evolution_tier}" if g.shared_state.evolution_tier > 1 else ""

            label_color = (255, 80, 80) if g.finished and g.stats.result == 'GAME OVER' else \
                          (0, 255, 255) if g.finished and g.stats.result == 'VICTORY' else \
                          SOLAR_YELLOW
            label = label_font.render(
                f"#{g.slot} {diff_label}{tier_str} | {mode_name} | "
                f"Score:{score:,} | {dist:.0f}km{boss_str} | {status}",
                True, label_color)
            display.blit(label, (x + 4, y + 2))

            thumb = pygame.transform.smoothscale(g.screen, (THUMB_W, THUMB_H))
            display.blit(thumb, (x, y + HEADER))

            border_color = (255, 80, 80) if g.finished and g.stats.result == 'GAME OVER' else \
                           (0, 255, 255) if g.finished and g.stats.result == 'VICTORY' else \
                           (60, 60, 80)
            pygame.draw.rect(display, border_color,
                             (x - 1, y + HEADER - 1, THUMB_W + 2, THUMB_H + 2), 1)

        pygame.display.flip()
        clock.tick(target_fps)
        frame_count += 1

    # Save brain
    if brain:
        brain.save()

    total_elapsed = time.time() - total_start

    print(f"\n{'='*65}")
    print(f"  NEON RUSH — Grid {'Learning' if args.learn else 'Autoplay'} Summary")
    print(f"{'='*65}")
    for g in games:
        if g.stats.result == "running":
            g.stats.finish('INTERRUPTED', g.shared_state, g.current_mode)
        print(g.stats.summary_line())

    if brain:
        print(f"\n  Brain: {brain.stats_str()}")
        print(f"  Saved to: {brain.brain_file}")

    victories = sum(1 for g in games if g.stats.result == 'VICTORY')
    game_overs = sum(1 for g in games if g.stats.result == 'GAME OVER')
    avg_score = sum(g.stats.final_score for g in games) / 6
    total_frames = sum(g.stats.frames for g in games)

    print(f"\n  Generations:   {generation}")
    print(f"  Victories:     {victories}/6 (last gen)")
    print(f"  Game Overs:    {game_overs}/6 (last gen)")
    print(f"  Avg Score:     {avg_score:,.0f}")
    print(f"  Total Frames:  {total_frames:,}")
    print(f"  Wall Time:     {total_elapsed:.1f}s")
    print(f"{'='*65}\n")


# ══════════════════════════════════════════════════════════════════
#  SEQUENTIAL MODE
# ══════════════════════════════════════════════════════════════════

def run_single(args, run_num, brain=None):
    from core.fonts import init_fonts
    from core.sound import init_sounds
    import core.display as disp
    from core.particles import ParticleSystem
    from core.shake import ScreenShake
    from shared.player_state import SharedPlayerState
    from shared.transition import TransitionEffect
    from modes.desert_velocity import DesertVelocityMode
    from modes.excitebike import ExcitebikeMode
    from modes.micromachines import MicroMachinesMode
    from core.constants import (
        SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
        STATE_PLAY, STATE_TRANSITION, STATE_VICTORY, MODE_NAMES,
    )

    stats = RunStats(run_num)
    init_fonts()
    init_sounds()

    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    if not args.headless:
        disp.create_display()

    clock = pygame.time.Clock()
    particles = ParticleSystem()
    shake = ScreenShake()

    evo_mgr = None
    if args.evo:
        from core.evolution import EvolutionManager
        evo_mgr = EvolutionManager()
        evo_mgr.enabled = True
        evo_mgr.start_run()
    shared_state = SharedPlayerState(
        args.players, args.difficulty,
        evolution_tier=evo_mgr.current_tier if evo_mgr else 1)
    MODE_CLASSES = [DesertVelocityMode, ExcitebikeMode, MicroMachinesMode]
    current_mode = MODE_CLASSES[0](particles, shake, shared_state)
    current_mode.setup()
    stats.modes_played.append(current_mode.MODE_NAME)
    state = STATE_PLAY

    transition = None

    if brain:
        fake_keys = SmartKeys(brain, args.players)
        if current_mode.players:
            brain.start_episode(current_mode.players[0])
    else:
        fake_keys = FakeKeys(args.players)

    target_fps = FPS * args.speed
    max_frames = args.max_frames if args.max_frames > 0 else float('inf')

    def advance_to_next_mode():
        nonlocal current_mode, transition, state
        mode_idx = shared_state.current_mode
        if mode_idx >= len(MODE_CLASSES):
            if evo_mgr and evo_mgr.enabled:
                new_tier = evo_mgr.advance_cycle()
                shared_state.reset_for_cycle(new_tier)
                from_surface = screen.copy()
                if current_mode:
                    current_mode.cleanup()
                transition = TransitionEffect(
                    'glitch', f"EVOLUTION V{new_tier}!",
                    from_surface, evolution_tier=new_tier)
                stats.transitions += 1
                state = STATE_TRANSITION
                current_mode = MODE_CLASSES[0](particles, shake, shared_state)
                return
            state = STATE_VICTORY
            return
        from_surface = screen.copy()
        if current_mode:
            current_mode.cleanup()
        styles = ['zoom_rotate', 'scanline', 'glitch']
        style = styles[min(mode_idx, len(styles) - 1)]
        mode_name = MODE_NAMES[mode_idx] if mode_idx < len(MODE_NAMES) else "???"
        transition = TransitionEffect(style, mode_name, from_surface,
                                       evolution_tier=shared_state.evolution_tier if evo_mgr else 1)
        stats.transitions += 1
        state = STATE_TRANSITION
        current_mode = MODE_CLASSES[mode_idx](particles, shake, shared_state)

    running = True
    while running and stats.frames < max_frames:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        if state == STATE_PLAY:
            if args.god and current_mode:
                for p in current_mode.players:
                    p.invincible_timer = max(p.invincible_timer, 10)
                    p.lives = max(p.lives, 3)

            boss_active = current_mode.boss_active if current_mode else False
            fake_keys.tick(
                mode=current_mode,
                players=current_mode.players if current_mode else [],
                boss_active=boss_active)

            if current_mode:
                result = current_mode.update(fake_keys)
                current_mode.draw(screen)

                if result == 'gameover':
                    stats.deaths += 1
                    stats.finish('GAME OVER', shared_state, current_mode)
                    if brain:
                        if brain._prev_state is not None:
                            brain.learn(brain._prev_state, brain._prev_action,
                                        -200, brain._prev_state, True)
                        brain.end_episode(stats.final_score, stats.frames)
                    running = False
                elif result == 'boss_defeated':
                    if brain and brain._prev_state is not None:
                        brain.learn(brain._prev_state, brain._prev_action,
                                    500, brain._prev_state, False)
                    advance_to_next_mode()

        elif state == STATE_TRANSITION:
            if transition:
                transition.update()
                transition.draw(screen)
                if transition.done:
                    transition = None
                    if current_mode:
                        current_mode.setup()
                        stats.modes_played.append(current_mode.MODE_NAME)
                    state = STATE_PLAY

        elif state == STATE_VICTORY:
            stats.finish('VICTORY', shared_state, current_mode)
            if brain:
                if brain._prev_state is not None:
                    brain.learn(brain._prev_state, brain._prev_action,
                                1000, brain._prev_state, True)
                brain.end_episode(stats.final_score, stats.frames)
            running = False

        if not args.headless:
            ds = disp.display_surface
            if ds is not None:
                sx, sy = shake.get_offset() if state == STATE_PLAY else (0, 0)
                if disp.current_scale == 1:
                    ds.fill((0, 0, 0))
                    ds.blit(screen, (sx, sy))
                else:
                    ds.fill((0, 0, 0))
                    ds.blit(
                        pygame.transform.scale(
                            screen, (SCREEN_WIDTH * disp.current_scale,
                                     SCREEN_HEIGHT * disp.current_scale)),
                        (sx * disp.current_scale, sy * disp.current_scale))
                pygame.display.flip()

        clock.tick(target_fps if not args.headless else 0)
        stats.frames += 1

        if args.verbose and stats.frames % 300 == 0:
            score = 0
            dist = 0.0
            if current_mode:
                alive = [p for p in current_mode.players if p.alive]
                score = max((p.score for p in alive), default=0)
                dist = current_mode.game_distance
            boss_str = "BOSS" if (current_mode and current_mode.boss_active) else ""
            brain_str = f" | {brain.stats_str()}" if brain else ""
            print(f"    [{stats.frames:>6}] {state:<12} "
                  f"Score={score:<8} Dist={dist:<6.1f}km {boss_str}{brain_str}")

    if stats.result == "running":
        stats.finish('MAX FRAMES', shared_state, current_mode)
    if current_mode:
        current_mode.cleanup()
    return stats


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    args = parse_args()

    if args.headless:
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        os.environ['SDL_AUDIODRIVER'] = 'dummy'

    global pygame
    import pygame
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

    if args.headless:
        pygame.display.set_mode((800, 600))

    # Grid mode
    if args.grid:
        if args.headless:
            print("ERROR: --grid requires a display (can't combine with --headless)")
            return 1
        learn_str = " + LEARNING AI" if args.learn else ""
        print(f"\n{'='*65}")
        print(f"  NEON RUSH — Grid Autoplay (6 games){learn_str}")
        print(f"{'='*65}")
        print(f"  Speed:      {args.speed}x ({60 * args.speed} target FPS)")
        print(f"  Difficulty: EASY / NORMAL / HARD x 2")
        print(f"  Players:    {args.players}")
        if args.learn:
            brain = LearningBrain()
            print(f"  Brain:      {brain.stats_str()}")
        if args.god:
            print(f"  God mode:   ON")
        print(f"  Controls:   ESC or Q to quit")
        print(f"{'='*65}\n")
        run_grid(args)
        pygame.quit()
        return 0

    # Sequential mode
    brain = LearningBrain() if args.learn else None
    learn_str = " + LEARNING AI" if args.learn else ""
    print(f"\n{'='*65}")
    print(f"  NEON RUSH — Autoplay Test{learn_str}")
    print(f"{'='*65}")
    print(f"  Mode:       {'HEADLESS' if args.headless else 'HEADED (visual)'}")
    print(f"  Speed:      {args.speed}x ({60 * args.speed} target FPS)")
    print(f"  Runs:       {args.runs}")
    print(f"  Difficulty: {args.difficulty.upper()}")
    print(f"  Players:    {args.players}")
    if args.max_frames:
        print(f"  Max frames: {args.max_frames} per run")
    if args.god:
        print(f"  God mode:   ON")
    if brain:
        print(f"  Brain:      {brain.stats_str()}")
    print(f"{'='*65}\n")

    all_stats = []
    total_start = time.time()

    for i in range(1, args.runs + 1):
        print(f"  Starting run {i}/{args.runs}...")
        st = run_single(args, i, brain)
        all_stats.append(st)
        print(f"  {st.summary_line()}")
        if brain:
            print(f"    {brain.stats_str()}")
            brain.save()
        print()

    total_elapsed = time.time() - total_start

    print(f"{'='*65}")
    print(f"  SUMMARY — {args.runs} run(s) in {total_elapsed:.1f}s")
    print(f"{'='*65}")
    for st in all_stats:
        print(st.summary_line())

    if brain:
        print(f"\n  Brain: {brain.stats_str()}")
        print(f"  Saved: {brain.brain_file}")

    victories = sum(1 for s in all_stats if s.result == 'VICTORY')
    game_overs = sum(1 for s in all_stats if s.result == 'GAME OVER')
    avg_score = sum(s.final_score for s in all_stats) / len(all_stats) if all_stats else 0
    avg_dist = sum(s.final_distance for s in all_stats) / len(all_stats) if all_stats else 0
    total_frames = sum(s.frames for s in all_stats)

    print(f"\n  Victories:     {victories}/{args.runs}")
    print(f"  Game Overs:    {game_overs}/{args.runs}")
    print(f"  Avg Score:     {avg_score:,.0f}")
    print(f"  Avg Distance:  {avg_dist:.1f} km")
    print(f"  Total Frames:  {total_frames:,}")
    print(f"  Wall Time:     {total_elapsed:.1f}s")
    print(f"{'='*65}\n")

    pygame.quit()
    return 0 if all(s.result != 'running' for s in all_stats) else 1


if __name__ == "__main__":
    sys.exit(main())
