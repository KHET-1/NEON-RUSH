"""NEON RUSH — Autoplay runner functions.

Moved from root autoplay.py (B3 refactor).
Contains: parse_args, run_grid, run_single, main.
"""
import argparse
import os
import sys
import time

# Ensure project root is on path (parent of ai/)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from ai.learning_brain import LearningBrain, SmartKeys, FakeKeys
from ai.run_stats import RunStats
from ai.game_instance import GameInstance


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
#  GRID MODE
# ══════════════════════════════════════════════════════════════════

def run_grid(args):
    import pygame
    from core.fonts import init_fonts
    from core.sound import init_sounds
    from core.constants import SIM_DT, SIM_RATE, NEON_CYAN, SOLAR_YELLOW

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
    target_fps = min(144, SIM_RATE * args.speed)
    effective_dt = SIM_DT / args.speed  # --speed 4 = 4x faster sim
    accumulator = 0.0

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
        # Timing
        frame_dt = clock.tick(target_fps) / 1000.0
        accumulator = min(accumulator + frame_dt, effective_dt * 8)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False

        # Fixed-timestep sim steps
        while accumulator >= effective_dt:
            for g in games:
                if not g.finished:
                    g.sim_step()
            accumulator -= effective_dt

        # Check alive status after sim
        any_alive = any(not g.finished for g in games)

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

        # --- Render the grid (once per display frame) ---
        for g in games:
            g.draw()

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
    import pygame
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
        SCREEN_WIDTH, SCREEN_HEIGHT, SIM_DT, SIM_RATE,
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

    target_fps = min(144, SIM_RATE * args.speed) if not args.headless else 0
    effective_dt = SIM_DT / args.speed
    accumulator = 0.0
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
        # Timing
        frame_dt = clock.tick(target_fps) / 1000.0
        if args.headless:
            # Headless: run one sim step per loop at max throughput
            accumulator = effective_dt
        else:
            accumulator = min(accumulator + frame_dt, effective_dt * 8)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Fixed-timestep sim steps
        while accumulator >= effective_dt:
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

            stats.frames += 1
            accumulator -= effective_dt

        # Render (once per display frame)
        if not args.headless:
            if state == STATE_PLAY and current_mode:
                current_mode.draw(screen)
            elif state == STATE_TRANSITION and transition:
                transition.draw(screen)

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
    import pygame
    from core.constants import SIM_RATE

    args = parse_args()

    if args.headless:
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        os.environ['SDL_AUDIODRIVER'] = 'dummy'

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
        print(f"  Speed:      {args.speed}x (sim {SIM_RATE * args.speed} Hz, render capped {min(144, SIM_RATE * args.speed)} FPS)")
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
    print(f"  Speed:      {args.speed}x (sim {SIM_RATE * args.speed} Hz)")
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
