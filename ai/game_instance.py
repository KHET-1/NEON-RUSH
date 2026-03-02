"""GameInstance — self-contained game for grid mode autoplay."""
import random
import time

import pygame

from ai.learning_brain import SmartKeys, FakeKeys
from ai.run_stats import RunStats


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

    def sim_step(self):
        """One fixed-timestep simulation step (no rendering)."""
        if self.finished:
            return False

        from core.constants import STATE_PLAY, STATE_TRANSITION, STATE_VICTORY

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
                elif result == 'boss_defeated':
                    # Reward for boss kill
                    if self.brain and self.brain._prev_state is not None:
                        self.brain.learn(self.brain._prev_state, self.brain._prev_action,
                                         500, self.brain._prev_state, False)
                    self._advance_to_next_mode()

        elif self.state == STATE_TRANSITION:
            if self.transition:
                self.transition.update()
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

        self.stats.frames += 1
        return not self.finished

    def draw(self):
        """Render current state to self.screen (once per display frame)."""
        from core.constants import STATE_PLAY, STATE_TRANSITION, STATE_VICTORY

        if self.state == STATE_PLAY:
            if self.current_mode:
                self.current_mode.draw(self.screen)
            if self.finished:
                self._draw_overlay("GAME OVER")
        elif self.state == STATE_TRANSITION:
            if self.transition:
                self.transition.draw(self.screen)
        elif self.state == STATE_VICTORY:
            if self.current_mode:
                self.current_mode.draw(self.screen)
            if self.finished:
                self._draw_overlay("VICTORY!")

    def tick(self):
        """Convenience: sim_step + draw (backwards compat)."""
        alive = self.sim_step()
        self.draw()
        return alive

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
