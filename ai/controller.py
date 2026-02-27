"""AI Controller — drives a player sprite autonomously across all 3 game modes."""
import math
import random

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    ROAD_LEFT, ROAD_RIGHT, ROAD_CENTER,
    MODE_DESERT, MODE_EXCITEBIKE, MODE_MICROMACHINES,
)


class AIController:
    """Single AI brain that adapts its strategy based on the current game mode."""

    # AI vehicle colors
    COLOR_MAIN = (50, 200, 50)
    COLOR_ACCENT = (100, 255, 100)

    def __init__(self, player, mode_index):
        self.player = player
        self.mode_index = mode_index
        self.frame = 0
        self.lane_switch_cooldown = 0

        # Micro Machines wander state
        self._wander_angle = random.uniform(0, math.pi * 2)
        self._wander_timer = 0

    def update(self, mode):
        """Called once per frame before player.update(). Sets _ai_keys on the player."""
        self.frame += 1
        p = self.player
        if not p.alive:
            p._ai_keys = {}
            return

        if self.lane_switch_cooldown > 0:
            self.lane_switch_cooldown -= 1

        if self.mode_index == MODE_DESERT:
            self._update_desert(mode)
        elif self.mode_index == MODE_EXCITEBIKE:
            self._update_excitebike(mode)
        elif self.mode_index == MODE_MICROMACHINES:
            self._update_micromachines(mode)

    # -------------------------------------------------------------------------
    # Desert Velocity — vertical scroller
    # -------------------------------------------------------------------------
    def _update_desert(self, mode):
        p = self.player
        keys = {"up": True, "down": False, "left": False, "right": False,
                "boost": False, "fire": False}

        # Scan obstacles ahead (within 250px above player)
        threat_left = False
        threat_right = False
        nearest_dist = 999
        for obs in mode.obstacles:
            dy = p.rect.top - obs.rect.bottom
            if 0 < dy < 250 and abs(obs.rect.centerx - p.rect.centerx) < 50:
                nearest_dist = min(nearest_dist, dy)
                if obs.rect.centerx < p.rect.centerx:
                    threat_left = True
                else:
                    threat_right = True

        # Dodge opposite side of threat
        if threat_left and not threat_right:
            keys["right"] = True
        elif threat_right and not threat_left:
            keys["left"] = True
        elif threat_left and threat_right:
            # Both sides blocked — emergency leap
            if p.leap_cooldown <= 0:
                p.leap_request = random.choice([-1, 1])
                p.leap_cooldown = p.LEAP_COOLDOWN_FRAMES

        # Seek coins when safe
        if nearest_dist > 150:
            best_coin = None
            best_d = 999
            for c in mode.coins_group:
                dy = p.rect.top - c.rect.centery
                if 0 < dy < 300:
                    dx = abs(c.rect.centerx - p.rect.centerx)
                    if dx < best_d:
                        best_d = dx
                        best_coin = c
            if best_coin:
                if best_coin.rect.centerx < p.rect.centerx - 10:
                    keys["left"] = True
                elif best_coin.rect.centerx > p.rect.centerx + 10:
                    keys["right"] = True

        # Fire heat bolts at boss
        if mode.boss_active and mode.boss and mode.boss.alive:
            if p.heat >= p.HEAT_COST and p.fire_cooldown <= 0:
                keys["fire"] = True
        elif mode.phase == 'asteroids' and len(mode.asteroids) > 0:
            if p.heat >= p.HEAT_COST and p.fire_cooldown <= 0:
                keys["fire"] = True

        # Boost occasionally when heat is high
        if p.heat > 60 and not p.ghost_mode and random.random() < 0.02:
            keys["boost"] = True

        p._ai_keys = keys

    # -------------------------------------------------------------------------
    # Excitebike — side scroller with 3 lanes
    # -------------------------------------------------------------------------
    def _update_excitebike(self, mode):
        p = self.player
        keys = {"up": False, "down": False, "accel": True, "brake": False,
                "boost": False, "fire": False}

        # Assess lane danger
        lane_danger = [0, 0, 0]
        for b in mode.barriers:
            if b.rect.left < SCREEN_WIDTH and b.rect.right > 0:
                dx = b.rect.left - p.rect.right
                if -30 < dx < 300:
                    for lane_idx in range(3):
                        lane_y = mode.bg.get_lane_y(lane_idx) + mode.bg.LANE_HEIGHT // 2
                        if abs(b.rect.centery - lane_y) < mode.bg.LANE_HEIGHT:
                            lane_danger[lane_idx] += max(0, 300 - dx)

        for r in mode.racers:
            dx = r.rect.left - p.rect.right
            if -30 < dx < 250:
                for lane_idx in range(3):
                    lane_y = mode.bg.get_lane_y(lane_idx) + mode.bg.LANE_HEIGHT // 2
                    if abs(r.rect.centery - lane_y) < mode.bg.LANE_HEIGHT:
                        lane_danger[lane_idx] += max(0, 250 - dx)

        # Also assess mud patches
        for m in mode.mud_patches:
            dx = m.rect.left - p.rect.right
            if -30 < dx < 200:
                for lane_idx in range(3):
                    lane_y = mode.bg.get_lane_y(lane_idx) + mode.bg.LANE_HEIGHT // 2
                    if abs(m.rect.centery - lane_y) < mode.bg.LANE_HEIGHT:
                        lane_danger[lane_idx] += max(0, 100 - dx) * 0.3

        # Switch to safest lane (rate limited)
        if self.lane_switch_cooldown <= 0:
            safest = min(range(3), key=lambda i: lane_danger[i])
            if safest != p.lane and lane_danger[p.lane] > 50:
                if safest < p.lane:
                    keys["up"] = True
                else:
                    keys["down"] = True
                self.lane_switch_cooldown = 30

        # Fire at boss
        if mode.boss_active and mode.boss and mode.boss.alive:
            if p.heat >= 40 and p.fire_cooldown <= 0:
                keys["fire"] = True
        elif mode.phase == 'asteroids' and len(mode.asteroids) > 0:
            if p.heat >= 40 and p.fire_cooldown <= 0:
                keys["fire"] = True

        # Boost occasionally
        if p.heat > 60 and not p.ghost_mode and random.random() < 0.02:
            keys["boost"] = True

        p._ai_keys = keys

    # -------------------------------------------------------------------------
    # Micro Machines — top-down free movement
    # -------------------------------------------------------------------------
    def _update_micromachines(self, mode):
        p = self.player
        keys = {"up": True, "down": False, "left": False, "right": False,
                "boost": False, "fire": False}

        # Compute target point
        target_x, target_y = None, None

        # Priority 1: Avoid nearby obstacles / cars
        nearest_threat_dist = 999
        threat_x, threat_y = 0, 0
        for grp in [mode.obstacles, mode.tiny_cars]:
            for obs in grp:
                dx = obs.rect.centerx - p.px
                dy = obs.rect.centery - p.py
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < nearest_threat_dist:
                    nearest_threat_dist = dist
                    threat_x, threat_y = dx, dy

        if nearest_threat_dist < 80:
            # Flee opposite direction
            target_x = p.px - threat_x * 2
            target_y = p.py - threat_y * 2
        else:
            # Priority 2: Seek nearest coin
            best_coin = None
            best_d = 999
            for c in mode.coins_group:
                dx = c.rect.centerx - p.px
                dy = c.rect.centery - p.py
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < best_d:
                    best_d = dist
                    best_coin = c
            if best_coin and best_d < 300:
                target_x = best_coin.rect.centerx
                target_y = best_coin.rect.centery
            else:
                # Wander pattern
                self._wander_timer += 1
                if self._wander_timer > 120:
                    self._wander_angle = random.uniform(0, math.pi * 2)
                    self._wander_timer = 0
                target_x = p.px + math.cos(self._wander_angle) * 150
                target_y = p.py + math.sin(self._wander_angle) * 150

        # Wall avoidance — push target away from edges
        margin = 80
        if p.px < margin:
            target_x = max(target_x or margin, margin + 50)
        elif p.px > SCREEN_WIDTH - margin:
            target_x = min(target_x or SCREEN_WIDTH - margin, SCREEN_WIDTH - margin - 50)
        if p.py < margin:
            target_y = max(target_y or margin, margin + 50)
        elif p.py > SCREEN_HEIGHT - margin:
            target_y = min(target_y or SCREEN_HEIGHT - margin, SCREEN_HEIGHT - margin - 50)

        # Steer towards target via signed angle difference
        if target_x is not None and target_y is not None:
            desired_angle = math.atan2(target_y - p.py, target_x - p.px)
            diff = desired_angle - p.angle
            # Normalize to [-pi, pi]
            while diff > math.pi:
                diff -= 2 * math.pi
            while diff < -math.pi:
                diff += 2 * math.pi

            dead_zone = 0.1
            if diff > dead_zone:
                keys["right"] = True
            elif diff < -dead_zone:
                keys["left"] = True

        # Fire at boss
        if mode.boss_active and mode.boss and mode.boss.alive:
            if p.heat >= 40 and p.fire_cooldown <= 0:
                keys["fire"] = True
        elif mode.phase == 'asteroids' and len(mode.asteroids) > 0:
            if p.heat >= 40 and p.fire_cooldown <= 0:
                keys["fire"] = True

        # Boost occasionally
        if p.heat > 60 and not p.ghost_mode and random.random() < 0.02:
            keys["boost"] = True

        p._ai_keys = keys


class BrainController:
    """Wraps a BaseBrain to drive a player sprite — same interface as AIController.

    Each frame: get state → choose action → set _ai_keys → learn from reward.
    """

    # Learning brain vehicle colors (orange tint to distinguish from heuristic green)
    COLOR_MAIN = (200, 140, 50)
    COLOR_ACCENT = (255, 180, 80)

    def __init__(self, brain, player, mode_index):
        self.brain = brain
        self.player = player
        self.mode_index = mode_index
        self.frame = 0
        self._prev_state = None
        self._prev_action = None

    def update(self, mode):
        """Called once per frame before player.update(). Sets _ai_keys on the player."""
        self.frame += 1
        p = self.player
        if not p.alive:
            p._ai_keys = {}
            # Learn terminal state
            if self._prev_state is not None:
                reward = self.brain.compute_reward(p, mode, died=True)
                state = self.brain.get_state(p, mode)
                self.brain.learn(self._prev_state, self._prev_action, reward, state, True)
                self._prev_state = None
                self._prev_action = None
            return

        state = self.brain.get_state(p, mode)

        # Learn from previous step
        if self._prev_state is not None:
            reward = self.brain.compute_reward(p, mode)
            self.brain.learn(self._prev_state, self._prev_action, reward, state, False)

        # Choose and apply action
        action = self.brain.choose_action(state)
        p._ai_keys = self.brain.action_to_keys(action, p)

        self._prev_state = state
        self._prev_action = action
