#!/usr/bin/env python3
"""NEON RUSH — Three-perspective racing game.

Flow: Desert Velocity → Boss → Excitebike → Boss → Micro Machines → Boss → Victory
"""
import pygame
import sys
import os
import math
import time
import random
import logging

# Ensure package imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.healing import preinit_heal, preflight_heal, crash_heal
from core.crash_report import session, generate_crash_report, show_crash_screen_v2
from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, SIM_DT, BLACK, NEON_CYAN, NEON_MAGENTA,
    SOLAR_YELLOW, SOLAR_WHITE, COIN_GOLD,
    STATE_TITLE, STATE_PLAY, STATE_PAUSED, STATE_GAMEOVER,
    STATE_HIGHSCORE, STATE_TRANSITION, STATE_VICTORY,
    DIFF_EASY, DIFF_NORMAL, DIFF_HARD, DIFFICULTY_SETTINGS,
    MODE_DESERT, MODE_EXCITEBIKE, MODE_MICROMACHINES, MODE_NAMES,
    ROAD_LEFT, ROAD_RIGHT,
)

# Anti-camping: nudge players who sit still too long
CAMP_RADIUS = 15    # pixels — movement less than this counts as "stationary"
CAMP_TIME = 5.0     # seconds before nudge triggers


def _init_pygame():
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)


def main():
    from core.fonts import init_fonts
    from core.sound import init_sounds, SFX
    import core.sound as _snd
    from core.display import create_display, display_surface, is_fullscreen, current_scale
    import core.display as disp
    from core.particles import ParticleSystem
    from core.shake import ScreenShake
    from core.highscores import is_highscore
    from core.ui import draw_title, draw_paused, draw_gameover, HighScoreEntry
    from core.hud import draw_panel, draw_ai_badges
    from core.fps_monitor import FPSMonitor
    from shared.player_state import SharedPlayerState
    from shared.transition import TransitionEffect
    from modes.desert_velocity import DesertVelocityMode
    from modes.excitebike import ExcitebikeMode
    from modes.micromachines import MicroMachinesMode
    from ai.brain_pool import BrainPool
    from ai.brain import MODE_BRAIN_NAMES
    from ai.controller import BrainController
    from ai.dashboard import LearningDashboard
    from core.evolution import EvolutionManager

    init_fonts()
    init_sounds()

    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    disp.create_display()
    clock = pygame.time.Clock()
    fps_mon = FPSMonitor(clock)

    particles = ParticleSystem()
    shake = ScreenShake()

    # Session tracking
    session.start()

    # Brain pools (one per mode) + dashboard
    brain_pools = {
        MODE_DESERT: BrainPool(MODE_DESERT),
        MODE_EXCITEBIKE: BrainPool(MODE_EXCITEBIKE),
        MODE_MICROMACHINES: BrainPool(MODE_MICROMACHINES),
    }
    dashboard = LearningDashboard(brain_pools)
    evolution_mgr = EvolutionManager()
    # Track active brains per player index for result reporting
    active_brains = {}  # player_idx -> brain

    # Game state
    state = STATE_TITLE
    selected_diff = DIFF_NORMAL
    ai_reward_mult = 1
    tick = 0
    ai_total_frames = 0
    highscore_entry = None
    target_fps = FPS
    FPS_CAPS = [30, 60, 120, 144, 0]
    last_input_time = time.monotonic()
    had_ai_players = False
    continues_left = 3
    camp_anchors = {}  # id(player) -> (anchor_x, anchor_y, start_time)

    # Fixed timestep accumulator
    accumulator = 0.0
    MAX_CATCHUP = 8  # cap sim steps per render to prevent spiral of death

    # Mode system
    shared_state = None
    current_mode = None
    transition = None

    MODE_CLASSES = [DesertVelocityMode, ExcitebikeMode, MicroMachinesMode]
    DIFF_LIST = [DIFF_EASY, DIFF_NORMAL, DIFF_HARD]

    def start_game(num_players, ai_config=None):
        nonlocal shared_state, current_mode, had_ai_players, continues_left
        particles.clear()
        evolution_mgr.start_run()

        # Assign brains from pool for AI players if dashboard enabled
        brain_config = {"use_brains": dashboard.enabled, "brain_map": {}}
        active_brains.clear()
        if dashboard.enabled and ai_config and ai_config.get("ai_players"):
            pool = brain_pools.get(MODE_DESERT)
            if pool:
                for pidx in ai_config["ai_players"]:
                    brain = pool.pick_brain()
                    brain_config["brain_map"][pidx] = brain
                    active_brains[pidx] = brain

        shared_state = SharedPlayerState(num_players, selected_diff, ai_config,
                                         brain_config=brain_config,
                                         evolution_tier=evolution_mgr.current_tier)
        current_mode = MODE_CLASSES[0](particles, shake, shared_state)
        current_mode.setup()
        fps_mon.start_tracking()
        fps_mon.target_fps = target_fps
        had_ai_players = bool(ai_config and ai_config.get("ai_players"))
        continues_left = 3
        camp_anchors.clear()

    def _report_brain_results():
        """Report results for any active brains to their pools."""
        if not active_brains or not current_mode:
            return
        prev_mode_idx = shared_state.current_mode - 1  # already advanced
        if prev_mode_idx < 0:
            prev_mode_idx = 0
        pool = brain_pools.get(prev_mode_idx)
        if not pool:
            return
        for pidx, brain in active_brains.items():
            if pidx < len(current_mode.players):
                score = current_mode.players[pidx].score
            elif shared_state:
                score = shared_state.scores[pidx] if pidx < len(shared_state.scores) else 0
            else:
                score = 0
            pool.report_result(brain.id, score)

    def _assign_brains_for_mode(mode_idx):
        """Pick brains from the mode's pool and update brain_config."""
        active_brains.clear()
        if not dashboard.enabled or not shared_state:
            return
        ai_players = shared_state.ai_config.get("ai_players", [])
        if not ai_players:
            return
        pool = brain_pools.get(mode_idx)
        if not pool:
            return
        brain_map = {}
        for pidx in ai_players:
            brain = pool.pick_brain()
            brain_map[pidx] = brain
            active_brains[pidx] = brain
        shared_state.brain_config["brain_map"] = brain_map

    def advance_to_next_mode():
        nonlocal current_mode, transition, state

        # Report results for brains in the mode that just ended
        if dashboard.enabled and active_brains and current_mode:
            cur_mode_idx = shared_state.current_mode - 1
            pool = brain_pools.get(max(0, cur_mode_idx))
            if pool:
                for pidx, brain in active_brains.items():
                    score = 0
                    if pidx < len(current_mode.players):
                        score = current_mode.players[pidx].score
                    pool.report_result(brain.id, score)

        mode_idx = shared_state.current_mode
        if mode_idx >= len(MODE_CLASSES):
            if evolution_mgr.enabled:
                # CYCLE: advance tier, reset to desert
                new_tier = evolution_mgr.advance_cycle()
                shared_state.reset_for_cycle(new_tier)
                mode_idx = 0

                # Brief evolution celebration transition
                from_surface = screen.copy()
                if current_mode:
                    current_mode.cleanup()
                transition = TransitionEffect(
                    'glitch', f"EVOLUTION V{new_tier}!", from_surface,
                    evolution_tier=new_tier)
                session.update_transition('glitch', f"EVOLUTION V{new_tier}!")
                _assign_brains_for_mode(0)
                current_mode = MODE_CLASSES[0](particles, shake, shared_state)
                state = STATE_TRANSITION
                SFX["evolve"].play()
                return
            else:
                # Normal victory — all modes complete
                state = STATE_VICTORY
                SFX["victory"].play()
                return

        # Assign brains for next mode
        _assign_brains_for_mode(mode_idx)

        # Capture current screen for transition
        from_surface = screen.copy()
        if current_mode:
            current_mode.cleanup()

        # Pick transition style
        styles = ['zoom_rotate', 'scanline', 'glitch']
        style = styles[min(mode_idx, len(styles) - 1)]
        mode_name = MODE_NAMES[mode_idx] if mode_idx < len(MODE_NAMES) else "???"
        transition = TransitionEffect(style, mode_name, from_surface,
                                      evolution_tier=shared_state.evolution_tier)
        session.update_transition(style, mode_name)
        state = STATE_TRANSITION

        # Create new mode
        current_mode = MODE_CLASSES[mode_idx](particles, shake, shared_state)

    running = True
    while running:
        # === Phase 0: Timing ===
        # VSync: GPU handles frame pacing, so tick(0). Otherwise software cap.
        render_cap = 0 if disp.vsync_enabled else (target_fps if target_fps > 0 else 0)
        frame_dt = clock.tick(render_cap) / 1000.0
        accumulator = min(accumulator + frame_dt, SIM_DT * MAX_CATCHUP)

        # === Phase 1: Events (once per render frame) ===
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN and state == STATE_TITLE:
                dashboard.handle_click(event.pos)

            if event.type == pygame.KEYDOWN:
                last_input_time = time.monotonic()
                # Global keys
                if event.key == pygame.K_F11:
                    disp.toggle_fullscreen()
                if event.key == pygame.K_F2:
                    disp.toggle_scale()

                if state == STATE_TITLE:
                    # Dashboard handles its own keys first
                    if dashboard.handle_key(event):
                        pass
                    elif event.key in (pygame.K_1, pygame.K_KP1, pygame.K_SPACE):
                        start_game(1)
                        state = STATE_PLAY
                        SFX["select"].play()
                    elif event.key in (pygame.K_2, pygame.K_KP2):
                        start_game(2)
                        state = STATE_PLAY
                        SFX["select"].play()
                    elif event.key in (pygame.K_3, pygame.K_KP3):
                        # Player + AI
                        ai_cfg = {"ai_players": [1], "score_mult": ai_reward_mult}
                        start_game(2, ai_cfg)
                        state = STATE_PLAY
                        SFX["select"].play()
                    elif event.key in (pygame.K_4, pygame.K_KP4):
                        # AI Solo
                        ai_cfg = {"ai_players": [0], "score_mult": ai_reward_mult}
                        start_game(1, ai_cfg)
                        state = STATE_PLAY
                        SFX["select"].play()
                    elif event.key in (pygame.K_5, pygame.K_KP5):
                        # AI + AI
                        ai_cfg = {"ai_players": [0, 1], "score_mult": ai_reward_mult}
                        start_game(2, ai_cfg)
                        state = STATE_PLAY
                        SFX["select"].play()
                    elif event.key == pygame.K_LEFT:
                        idx = DIFF_LIST.index(selected_diff)
                        selected_diff = DIFF_LIST[max(0, idx - 1)]
                        SFX["select"].play()
                    elif event.key == pygame.K_RIGHT:
                        idx = DIFF_LIST.index(selected_diff)
                        selected_diff = DIFF_LIST[min(len(DIFF_LIST) - 1, idx + 1)]
                        SFX["select"].play()
                    elif event.key in (pygame.K_6, pygame.K_KP6):
                        ai_reward_mult = 1 if ai_reward_mult == 2 else 2
                        SFX["select"].play()
                    elif event.key in (pygame.K_7, pygame.K_KP7):
                        ai_reward_mult = 1 if ai_reward_mult == 4 else 4
                        SFX["select"].play()
                    elif event.key in (pygame.K_8, pygame.K_KP8):
                        ai_reward_mult = 1 if ai_reward_mult == 8 else 8
                        SFX["select"].play()
                    elif event.key == pygame.K_UP:
                        idx = FPS_CAPS.index(target_fps) if target_fps in FPS_CAPS else 1
                        target_fps = FPS_CAPS[min(len(FPS_CAPS) - 1, idx + 1)]
                        fps_mon.target_fps = target_fps
                        SFX["select"].play()
                    elif event.key == pygame.K_DOWN:
                        idx = FPS_CAPS.index(target_fps) if target_fps in FPS_CAPS else 1
                        target_fps = FPS_CAPS[max(0, idx - 1)]
                        fps_mon.target_fps = target_fps
                        SFX["select"].play()
                    elif event.key == pygame.K_e:
                        evolution_mgr.enabled = not evolution_mgr.enabled
                        SFX["select"].play()
                    elif event.key == pygame.K_ESCAPE:
                        running = False

                elif state == STATE_PLAY:
                    if event.key == pygame.K_p:
                        state = STATE_PAUSED
                    elif event.key == pygame.K_ESCAPE:
                        state = STATE_TITLE
                        if current_mode:
                            current_mode.cleanup()
                            current_mode = None
                        if _snd.music_channel and _snd.music_channel.get_busy():
                            _snd.music_channel.fadeout(300)
                    else:
                        if current_mode:
                            current_mode.handle_event(event)

                elif state == STATE_PAUSED:
                    if event.key == pygame.K_p:
                        state = STATE_PLAY
                    elif event.key == pygame.K_r:
                        if shared_state:
                            start_game(shared_state.num_players)
                            state = STATE_PLAY
                    elif event.key == pygame.K_ESCAPE:
                        running = False

                elif state == STATE_GAMEOVER:
                    if event.key == pygame.K_SPACE:
                        if continues_left > 0 and current_mode:
                            # Continue from same spot
                            continues_left -= 1
                            for p in current_mode.players:
                                p.lives = 1
                                p.alive = True
                                p.shield = 120  # brief invuln
                            state = STATE_PLAY
                            SFX["select"].play()
                        else:
                            # Hard game over — highscore or title
                            best = shared_state.best_score if shared_state else 0
                            if is_highscore(best):
                                highscore_entry = HighScoreEntry(
                                    best, auto_type=had_ai_players)
                                state = STATE_HIGHSCORE
                            else:
                                state = STATE_TITLE
                    elif event.key == pygame.K_ESCAPE:
                        running = False

                elif state == STATE_HIGHSCORE:
                    if highscore_entry:
                        highscore_entry.handle_event(event)
                        if highscore_entry.done:
                            state = STATE_TITLE
                            highscore_entry = None

                elif state == STATE_TRANSITION:
                    pass  # No input during transitions

                elif state == STATE_VICTORY:
                    if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        best = shared_state.best_score if shared_state else 0
                        if is_highscore(best):
                            highscore_entry = HighScoreEntry(
                                best, auto_type=had_ai_players)
                            state = STATE_HIGHSCORE
                        else:
                            state = STATE_TITLE
                    elif event.key == pygame.K_ESCAPE:
                        state = STATE_TITLE

        keys = pygame.key.get_pressed()

        # === Phase 2: Fixed-timestep simulation loop ===
        while accumulator >= SIM_DT:
            if state == STATE_PLAY:
                if current_mode:
                    result = current_mode.update(keys)
                    # AI frame counting
                    if hasattr(current_mode, 'ai_controllers'):
                        ai_total_frames += len(current_mode.ai_controllers)

                    # Anti-camping: nudge players who park in one spot > 5s
                    now_camp = time.monotonic()
                    for p in current_mode.players:
                        pid = id(p)
                        if not p.alive:
                            camp_anchors.pop(pid, None)
                            continue
                        cx, cy = p.rect.center
                        if pid in camp_anchors:
                            ax, ay, start = camp_anchors[pid]
                            dist_sq = (cx - ax) ** 2 + (cy - ay) ** 2
                            if dist_sq > CAMP_RADIUS ** 2:
                                camp_anchors[pid] = (cx, cy, now_camp)
                            elif now_camp - start > CAMP_TIME:
                                # Camping detected — fake damage nudge
                                shake.trigger(6, 15)
                                p.invincible_timer = max(
                                    getattr(p, 'invincible_timer', 0), 30)
                                nudge = random.choice([-45, 45])
                                if hasattr(p, 'px'):
                                    # Micro Machines — nudge float coords
                                    p.px += nudge
                                    p.py += random.choice([-35, 35])
                                    p.px = max(20, min(SCREEN_WIDTH - 20, p.px))
                                    p.py = max(20, min(SCREEN_HEIGHT - 20, p.py))
                                elif hasattr(p, 'target_lane'):
                                    # Excitebike — force lane change
                                    if p.lane <= 0:
                                        p.target_lane = 1
                                    elif p.lane >= 2:
                                        p.target_lane = 1
                                    else:
                                        p.target_lane = random.choice([0, 2])
                                else:
                                    # Desert Velocity — horizontal shove
                                    p.rect.x += nudge
                                    p.rect.x = max(
                                        ROAD_LEFT + 5,
                                        min(ROAD_RIGHT - p.rect.width - 5,
                                            p.rect.x))
                                camp_anchors[pid] = (
                                    p.rect.centerx, p.rect.centery, now_camp)
                        else:
                            camp_anchors[pid] = (cx, cy, now_camp)

                    if result == 'gameover':
                        state = STATE_GAMEOVER
                        if current_mode:
                            shared_state.snapshot_from_players(current_mode.players)
                        # Report brain results on game over
                        if dashboard.enabled and active_brains:
                            mode_idx = shared_state.current_mode if shared_state else 0
                            pool = brain_pools.get(mode_idx)
                            if pool:
                                for pidx, brain in active_brains.items():
                                    score = 0
                                    if current_mode and pidx < len(current_mode.players):
                                        score = current_mode.players[pidx].score
                                    pool.report_result(brain.id, score)
                    elif result == 'boss_defeated':
                        advance_to_next_mode()

            elif state == STATE_TRANSITION:
                if transition:
                    transition.update()
                    if transition.done:
                        session.update_transition_end()
                        transition = None
                        if current_mode:
                            current_mode.setup()
                        state = STATE_PLAY

            tick += 1
            accumulator -= SIM_DT

        # === Phase 3: Render (once per display frame) ===
        if state == STATE_TITLE:
            draw_title(screen, tick, selected_diff, ai_reward_mult,
                       loop_count=tick, ai_frames=ai_total_frames,
                       target_fps=target_fps, dashboard=dashboard,
                       evolution_mgr=evolution_mgr, vsync=disp.vsync_enabled)

        elif state == STATE_PLAY:
            if current_mode:
                current_mode.draw(screen)
                # AI badges
                if hasattr(current_mode, 'ai_controllers'):
                    draw_ai_badges(screen, current_mode.ai_controllers)
                # FPS tracking (per render frame)
                fps_mon.record_frame()

        elif state == STATE_PAUSED:
            # Draw the game underneath
            if current_mode:
                current_mode.draw(screen)
            draw_paused(screen)

        elif state == STATE_GAMEOVER:
            if current_mode:
                current_mode.draw(screen)
            players = current_mode.players if current_mode else []
            dist = current_mode.game_distance if current_mode else 0
            two_p = shared_state.num_players == 2 if shared_state else False
            snaps = fps_mon.get_snapshots() if continues_left <= 0 else None
            total_f = fps_mon.get_total_frames() if continues_left <= 0 else 0
            draw_gameover(screen, players, dist, tick, two_p,
                          fps_snapshots=snaps, fps_total_frames=total_f,
                          continues_left=continues_left)

        elif state == STATE_HIGHSCORE:
            if highscore_entry:
                highscore_entry.draw(screen, tick)

        elif state == STATE_TRANSITION:
            if transition:
                transition.draw(screen)

        elif state == STATE_VICTORY:
            _draw_victory(screen, shared_state, tick)

        # === Idle auto-actions (15s with no human input) ===
        idle_secs = time.monotonic() - last_input_time
        if idle_secs > 15.0:
            if state == STATE_GAMEOVER:
                # Auto-press SPACE (continue or end)
                if continues_left > 0 and current_mode:
                    continues_left -= 1
                    for p in current_mode.players:
                        p.lives = 1
                        p.alive = True
                        p.shield = 120
                    state = STATE_PLAY
                else:
                    best = shared_state.best_score if shared_state else 0
                    if is_highscore(best):
                        highscore_entry = HighScoreEntry(
                            best, auto_type=True)
                        state = STATE_HIGHSCORE
                    else:
                        state = STATE_TITLE
                last_input_time = time.monotonic()
            elif state == STATE_VICTORY:
                best = shared_state.best_score if shared_state else 0
                if is_highscore(best):
                    highscore_entry = HighScoreEntry(
                        best, auto_type=True)
                    state = STATE_HIGHSCORE
                else:
                    state = STATE_TITLE
                last_input_time = time.monotonic()
            elif state == STATE_TITLE:
                # Auto-start AI Solo
                ai_cfg = {"ai_players": [0], "score_mult": ai_reward_mult}
                start_game(1, ai_cfg)
                state = STATE_PLAY
                last_input_time = time.monotonic()

        # === Auto-complete highscore entry (AI auto-type finishes) ===
        if state == STATE_HIGHSCORE and highscore_entry and highscore_entry.done:
            state = STATE_TITLE
            highscore_entry = None
            last_input_time = time.monotonic()

        # === FPS monitoring (gameplay only) ===
        fps_mon.update(state == STATE_PLAY)
        if state == STATE_PLAY:
            fps_mon.draw(screen)

        # === Render to display ===
        ds = disp.display_surface
        if ds is None:
            disp.create_display()
            ds = disp.display_surface

        sx, sy = shake.get_offset() if state == STATE_PLAY else (0, 0)

        if disp.is_fullscreen:
            dw, dh = ds.get_size()
            scale_factor = min(dw / SCREEN_WIDTH, dh / SCREEN_HEIGHT)
            sw = int(SCREEN_WIDTH * scale_factor)
            sh = int(SCREEN_HEIGHT * scale_factor)
            ds.fill(BLACK)
            ds.blit(pygame.transform.smoothscale(screen, (sw, sh)),
                    ((dw - sw) // 2 + sx, (dh - sh) // 2 + sy))
        elif disp.current_scale == 1:
            ds.fill(BLACK)
            ds.blit(screen, (sx, sy))
        else:
            ds.fill(BLACK)
            ds.blit(
                pygame.transform.scale(screen, (SCREEN_WIDTH * disp.current_scale,
                                                SCREEN_HEIGHT * disp.current_scale)),
                (sx * disp.current_scale, sy * disp.current_scale))

        # Update session tracker for crash reports
        session.update(state=state, shared_state=shared_state, current_mode=current_mode, tick=tick)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


def _draw_victory(screen, shared_state, tick):
    """Victory screen with total stats."""
    from core.fonts import FONT_TITLE, FONT_SUBTITLE, FONT_HUD, FONT_HUD_SM, FONT_HUD_LG
    from core.hud import draw_panel

    t = (tick % 120) / 120
    r = int(10 + 20 * math.sin(t * math.pi * 2))
    g = int(5 + 15 * math.sin(t * math.pi * 2 + 1))
    b = int(30 + 25 * math.sin(t * math.pi * 2 + 2))
    screen.fill((r, g, b))

    # Victory banner
    pw, ph = 500, 380
    px, py = (SCREEN_WIDTH - pw) // 2, (SCREEN_HEIGHT - ph) // 2 - 20
    draw_panel(screen, pygame.Rect(px, py, pw, ph), (0, 0, 20, 220), SOLAR_YELLOW, 3)

    # Title
    for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
        glow = FONT_TITLE.render("VICTORY!", True, NEON_MAGENTA)
        screen.blit(glow, (SCREEN_WIDTH // 2 - glow.get_width() // 2 + dx, py + 15 + dy))
    title = FONT_TITLE.render("VICTORY!", True, SOLAR_YELLOW)
    screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, py + 15))

    sub = FONT_SUBTITLE.render("ALL BOSSES DEFEATED!", True, NEON_CYAN)
    screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, py + 85))

    if shared_state:
        y = py + 130
        evo_tier = getattr(shared_state, 'evolution_tier', 1)
        cycles = getattr(shared_state, 'cycle_count', 0)
        bosses_total = shared_state.bosses_defeated
        stats = [
            ("Total Score", str(shared_state.best_score)),
            ("Total Coins", str(shared_state.total_coins)),
            ("Distance", f"{shared_state.total_distance:.1f} km"),
            ("Bosses", f"{bosses_total}" + (f" ({cycles} cycles)" if cycles > 0 else "/3")),
            ("Evolution", f"V{evo_tier}" if evo_tier > 1 else "V1 (base)"),
        ]
        for label, value in stats:
            lt = FONT_HUD_SM.render(f"{label}:", True, (180, 180, 200))
            screen.blit(lt, (px + 40, y))
            vt = FONT_HUD.render(value, True, SOLAR_WHITE)
            screen.blit(vt, (px + 200, y - 2))
            y += 35

    blink = (tick // 25) % 2
    if blink:
        cont = FONT_HUD.render("SPACE = Continue    ESC = Title", True, NEON_CYAN)
        screen.blit(cont, (SCREEN_WIDTH // 2 - cont.get_width() // 2, py + ph - 45))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    preinit_heal()

    _pygame_ok = False
    try:
        _init_pygame()
        _pygame_ok = True
    except Exception as e:
        os.environ.setdefault("SDL_VIDEODRIVER", "x11")
        try:
            _init_pygame()
            _pygame_ok = True
        except Exception:
            report = generate_crash_report(type(e), e, e.__traceback__, ["tried SDL_VIDEODRIVER=x11"])
            show_crash_screen_v2(report)
            sys.exit(1)

    _heal_actions = preflight_heal()
    _retried = False
    while True:
        try:
            main()
            break
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            fixed, actions = crash_heal(exc_type, exc_value, exc_tb)
            _heal_actions.extend(actions)
            if fixed and not _retried:
                _retried = True
                continue
            report = generate_crash_report(exc_type, exc_value, exc_tb, _heal_actions)
            show_crash_screen_v2(report)
            sys.exit(1)
