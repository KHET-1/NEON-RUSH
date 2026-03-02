#!/usr/bin/env python3
"""Balance metrics — headless runner for NEON RUSH pacing analysis.

Measures time-to-boss, score/distance at boss trigger, and boss fight stats
across all 3 modes and 3 difficulties. Outputs a markdown table.

Usage:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 tools/balance_metrics.py
"""
import os
import sys
import time

# Ensure headless operation
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

from core.fonts import init_fonts
from core.sound import init_sounds
from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
    DIFF_EASY, DIFF_NORMAL, DIFF_HARD,
    MODE_DESERT, MODE_EXCITEBIKE, MODE_MICROMACHINES,
)
from core.particles import ParticleSystem
from core.shake import ScreenShake
from shared.player_state import SharedPlayerState
from modes.desert_velocity import DesertVelocityMode
from modes.excitebike import ExcitebikeMode
from modes.micromachines import MicroMachinesMode

init_fonts()
init_sounds()

MODE_CLASSES = [DesertVelocityMode, ExcitebikeMode, MicroMachinesMode]
MODE_LABELS = ["Desert", "Excitebike", "Micro"]
DIFF_LIST = [DIFF_EASY, DIFF_NORMAL, DIFF_HARD]
DIFF_LABELS = ["Easy", "Normal", "Hard"]

MAX_FRAMES = 30000  # ~500s safety cap (at sim rate)
SIM_RATE = 36


def run_trial(mode_idx, difficulty, tier=1):
    """Run a single headless trial. Returns metrics dict."""
    particles = ParticleSystem()
    shake = ScreenShake()
    shared = SharedPlayerState(1, difficulty, evolution_tier=tier)

    # Advance shared_state to correct mode
    for _ in range(mode_idx):
        shared.current_mode += 1

    mode = MODE_CLASSES[mode_idx](particles, shake, shared)
    mode.GOD_MODE = True  # don't die during measurement
    mode.setup()

    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    keys = pygame.key.get_pressed()

    metrics = {
        "mode": MODE_LABELS[mode_idx],
        "difficulty": difficulty,
        "tier": tier,
        "asteroid_start_frame": None,
        "boss_start_frame": None,
        "boss_end_frame": None,
        "score_at_boss": 0,
        "distance_at_boss": 0.0,
        "boss_hits": 0,
    }

    prev_phase = mode.phase
    for frame in range(MAX_FRAMES):
        result = mode.update(keys)

        # Detect phase transitions
        if prev_phase == 'normal' and mode.phase == 'asteroids':
            metrics["asteroid_start_frame"] = frame
        if prev_phase == 'asteroids' and mode.phase == 'boss':
            metrics["boss_start_frame"] = frame
            metrics["score_at_boss"] = mode._best_score()
            metrics["distance_at_boss"] = mode.game_distance
        prev_phase = mode.phase

        if result == 'boss_defeated':
            metrics["boss_end_frame"] = frame
            break
        if result == 'gameover':
            break

    # Calculate derived metrics
    if metrics["boss_start_frame"] is not None:
        metrics["time_to_boss_s"] = metrics["boss_start_frame"] / SIM_RATE
    else:
        metrics["time_to_boss_s"] = None

    if metrics["asteroid_start_frame"] is not None and metrics["boss_start_frame"] is not None:
        metrics["asteroid_duration_s"] = (
            metrics["boss_start_frame"] - metrics["asteroid_start_frame"]
        ) / SIM_RATE
    else:
        metrics["asteroid_duration_s"] = None

    if metrics["boss_start_frame"] is not None and metrics["boss_end_frame"] is not None:
        metrics["boss_fight_s"] = (
            metrics["boss_end_frame"] - metrics["boss_start_frame"]
        ) / SIM_RATE
    else:
        metrics["boss_fight_s"] = None

    mode.cleanup()
    return metrics


def fmt(val, suffix=""):
    if val is None:
        return "N/A"
    if isinstance(val, float):
        return f"{val:.1f}{suffix}"
    return f"{val}{suffix}"


def main():
    print("# NEON RUSH — Balance Metrics Report")
    print(f"\nGenerated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Sim rate: {SIM_RATE} Hz | God mode: ON")
    print()

    print("| Mode | Diff | Tier | Time-to-Boss | Score@Boss | Dist@Boss | Asteroid Phase | Boss Fight |")
    print("|------|------|------|-------------|-----------|----------|---------------|-----------|")

    for mode_idx in range(3):
        for diff_idx, diff in enumerate(DIFF_LIST):
            m = run_trial(mode_idx, diff, tier=1)
            print(
                f"| {m['mode']:<10} "
                f"| {DIFF_LABELS[diff_idx]:<6} "
                f"| {m['tier']} "
                f"| {fmt(m['time_to_boss_s'], 's'):<11} "
                f"| {m['score_at_boss']:<9} "
                f"| {fmt(m['distance_at_boss'], ' km'):<8} "
                f"| {fmt(m['asteroid_duration_s'], 's'):<13} "
                f"| {fmt(m['boss_fight_s'], 's'):<9} |"
            )

    print()
    print("*N/A = phase not reached within safety cap*")


if __name__ == "__main__":
    main()
