import pygame
import random
import math
from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, DIFFICULTY_SETTINGS, DIFF_NORMAL,
    ASTEROID_GLOW, SOLAR_YELLOW, SOLAR_WHITE, NEON_CYAN, NEON_MAGENTA,
    COIN_GOLD, SHIELD_BLUE, PHASE_CYAN, SURGE_PINK,
)
import core.sound as _snd
from core.sound import music_loops
from core.tasks import TaskManager, level_label
from core.combo import MilestoneTracker


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
    BOSS_DISTANCE_THRESHOLD = 1.2   # km
    BOSS_SCORE_THRESHOLD = 1200
    BOSS_TIME_THRESHOLD = 2700      # frames (~45s at 60fps)
    BOSS_POINTS = 2000              # score bonus per player on boss defeat

    # Godmode — players are invincible
    GOD_MODE = False

    # Coin collection particle settings (set COIN_PARTICLE_COUNT=0 to disable)
    COIN_PARTICLE_COLORS = (COIN_GOLD, SOLAR_YELLOW)
    COIN_PARTICLE_COUNT = 6
    COIN_PARTICLE_SIZE = 3
    COIN_PARTICLE_SPEED = 20
    COIN_PARTICLE_LIFE = 2
    COIN_PARTICLE_OFFSET_Y = -10

    # Powerup effect rendering — override per mode for different shapes/sizes
    SHIELD_DIMS = (54, 76)        # (width, height) of shield/phase surface
    SHIELD_OFFSET = (-27, -38)    # blit offset from player center
    SHIELD_SHAPE = 'ellipse'      # 'ellipse' or 'circle'

    # Asteroid phase spawn interval (frames)
    ASTEROID_SPAWN_INTERVAL = 40

    # Environmental boss damage particle burst args (count, size, speed, life)
    ENV_DAMAGE_PARTICLE_ARGS = (20, 6, 40, 4)

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
        self.ASTEROID_CLEAR_TARGET = 10

        # Task system (initialized in init_tasks())
        self.task_mgr = None

        # Common sprite groups — modes can add more
        self.all_sprites = pygame.sprite.Group()
        self.coins_group = pygame.sprite.Group()
        self.powerups_group = pygame.sprite.Group()
        self.heat_bolts = pygame.sprite.Group()

        # New weapon sprite groups
        self.homing_rockets = pygame.sprite.Group()
        self.orbit_orbs = pygame.sprite.Group()

        # Common mode state
        self.ai_controllers = []
        self.floating_texts = []
        self.screen_flash = 0
        self.difficulty_scale = 1.0
        self.milestone = MilestoneTracker()

        # Near-miss chain state
        self.near_miss_chain = 0
        self.near_miss_cooldown = 0

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

        # Auto-resume music if sound was re-enabled mid-game
        if _snd.sound_enabled and _snd.music_channel and not _snd.music_channel.get_busy():
            key = f"boss_{self.MUSIC_KEY}" if self.boss_active else self.MUSIC_KEY
            track = music_loops.get(key)
            if track:
                _snd.music_channel.play(track, loops=-1)
                _snd.music_channel.set_volume(0.08 if self.boss_active else 0.06)

        # Set speed_mult_factor on all players each frame for distance scoring
        for p in self.players:
            p.speed_mult_factor = self._speed_multiplier(p)

        # Godmode: keep all players invincible and alive
        if self.GOD_MODE:
            for p in self.players:
                p.invincible_timer = max(p.invincible_timer, 10)
                p.lives = max(p.lives, 3)

        return None

    def draw(self, screen):
        """Render current frame."""
        raise NotImplementedError

    def configure_ai_players(self, rebuild_sprite_fn=None):
        """Set up AI controllers for designated AI players.

        Args:
            rebuild_sprite_fn: Optional callable(player) to rebuild the player's
                sprite after color changes. If None, no sprite rebuild is done.
        """
        from ai.controller import AIController, BrainController

        ai_cfg = self.shared_state.ai_config
        ai_indices = ai_cfg.get("ai_players", [])
        score_mult = ai_cfg.get("score_mult", 1)
        use_brains = self.shared_state.brain_config.get("use_brains", False)
        brain_map = self.shared_state.brain_config.get("brain_map", {})
        self.ai_controllers = []

        for idx in ai_indices:
            if idx >= len(self.players):
                continue
            p = self.players[idx]
            p.is_ai = True
            p.score_mult = score_mult

            brain = brain_map.get(idx)
            if use_brains and brain is not None:
                p.color_main = BrainController.COLOR_MAIN
                p.color_accent = BrainController.COLOR_ACCENT
                if rebuild_sprite_fn:
                    rebuild_sprite_fn(p)
                p.name = brain.name[:10]
                brain.start_episode(p)
                self.ai_controllers.append(
                    BrainController(brain, p, self.MODE_INDEX))
            else:
                p.color_main = AIController.COLOR_MAIN
                p.color_accent = AIController.COLOR_ACCENT
                if rebuild_sprite_fn:
                    rebuild_sprite_fn(p)
                p.name = f"AI{idx + 1}"
                self.ai_controllers.append(
                    AIController(p, self.MODE_INDEX))

    def cleanup(self):
        """Called when leaving this mode. Clean up sprites."""
        for a in list(self.asteroids):
            a.kill()
        for r in list(self.homing_rockets):
            r.kill()
        for o in list(self.orbit_orbs):
            o.kill()
        for b in list(self.heat_bolts):
            b.kill()
        for s in list(self.all_sprites):
            s.kill()
        self.particles.clear()

    # --- Boss spawn / defeat (shared across all 3 modes) ---

    def _create_boss(self):
        """Override: create and return the boss sprite for this mode."""
        raise NotImplementedError

    def _spawn_boss_now(self):
        """Spawn boss directly — bypass asteroid phase (task system trigger).
        Calls _create_boss() to get mode-specific boss instance."""
        self.start_boss_phase()
        self.boss = self._create_boss()
        self.boss_active = True
        self.all_sprites.add(self.boss)
        _snd.play_sfx("boss_warning")
        if _snd.sound_enabled and _snd.music_channel:
            track = music_loops.get(f"boss_{self.MUSIC_KEY}")
            if track:
                _snd.music_channel.play(track, loops=-1)
                _snd.music_channel.set_volume(0.08)

    def _on_boss_defeated(self, alive_players, boss_points=None):
        """Common boss defeat handling: restore music, award points, advance mode.
        Returns 'boss_defeated' for the mode's update() to return."""
        from core.hud import FloatingText
        if boss_points is None:
            boss_points = self.BOSS_POINTS
        self.boss_active = False
        # Restore normal music
        if _snd.sound_enabled and _snd.music_channel:
            track = music_loops.get(self.MUSIC_KEY)
            if track:
                _snd.music_channel.play(track, loops=-1)
                _snd.music_channel.set_volume(0.06)
        self.shared_state.snapshot_from_players(self.players)
        self.shared_state.advance_mode()
        label = "BOSS!" if boss_points <= 3000 else "FINAL BOSS!"
        for p in alive_players:
            pts = boss_points * p.score_mult
            p.score += pts
            self.floating_texts.append(
                FloatingText(p.rect.centerx, p.rect.top - 40,
                             f"+{pts} {label}", SOLAR_YELLOW, 28))
        return 'boss_defeated'

    def _update_boss_bolts(self, keys, alive_players):
        """Fire heat bolts + check bolt-boss collisions. Common vertical version."""
        has_target = self.boss and self.boss.alive
        for p in alive_players:
            fired, bx, by = p.try_fire_heat_bolt(keys, auto_fire=has_target)
            if fired:
                self._create_bolts_for_player(p, bx, by, self.heat_bolts)

        for bolt in list(self.heat_bolts):
            bolt.update()
            if not bolt.alive:
                continue
            if self.boss and self.boss.alive and bolt.rect.colliderect(self.boss.rect):
                self.boss.take_damage(bolt.damage, "heat_bolt")
                self.particles.burst(bolt.rect.centerx, bolt.rect.centery,
                                     [SOLAR_YELLOW, SOLAR_WHITE], 6, 3, 20, 2)
                bolt.kill()

    def _check_boss_ram(self, alive_players):
        """Check ram damage — player colliding with boss during vulnerability."""
        if not (self.boss and self.boss.alive and self.boss.vulnerable):
            return
        for p in alive_players:
            if p.rect.colliderect(self.boss.rect) and p.invincible_timer <= 0:
                self.boss.take_damage(self.boss.RAM_DAMAGE, "ram")
                p.invincible_timer = 30
                self.shake.trigger(6, 15)
                self.particles.burst(p.rect.centerx, p.rect.top,
                                     [NEON_CYAN, SOLAR_YELLOW], 10, 4, 25, 3)

    def _check_boss_attack_hazards(self, alive_players):
        """Check boss attack hazards hitting players. Returns 'gameover' or None."""
        if not (self.boss and self.boss.alive):
            return None
        hazards = self.boss.get_attack_hazards()
        for p in alive_players:
            if p.invincible_timer > 0 or p.ghost_mode:
                continue
            for htype, hdata in hazards:
                hit = False
                if htype == 'rect' and isinstance(hdata, pygame.Rect):
                    hit = p.rect.colliderect(hdata)
                elif htype == 'ring':
                    cx, cy, radius, thickness = hdata
                    dx = p.rect.centerx - cx
                    dy = p.rect.centery - cy
                    dist = math.sqrt(dx * dx + dy * dy)
                    hit = abs(dist - radius) < thickness
                if hit:
                    p.take_hit(self.shake)
                    if not p.alive and not any(pl.alive for pl in self.players):
                        return 'gameover'
                    break
        return None

    def _check_boss_defeat(self, alive_players, boss_points=None):
        """Check if boss is defeated and handle it. Returns 'boss_defeated' or None."""
        if self.boss and self.boss.defeated and self.boss.death_timer <= 0:
            return self._on_boss_defeated(alive_players, boss_points)
        return None

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

    # --- Task system methods ---

    def init_tasks(self, boss_rush=False):
        """Create TaskManager for this level. Call after player setup."""
        self.task_mgr = TaskManager(
            self.MODE_INDEX,
            self.shared_state.evolution_tier,
            self.difficulty,
            boss_rush=boss_rush,
        )
        # Update level label in shared_state to use task-system format
        self.shared_state._task_level_label = level_label(
            self.MODE_INDEX, self.shared_state.evolution_tier)

    def check_task_boss_trigger(self):
        """Return True when task manager says boss should spawn."""
        if self.task_mgr is None:
            return False
        return self.task_mgr.all_complete()

    def spawn_boss(self):
        """Override in subclass to create and return the boss."""
        raise NotImplementedError

    def get_alive_players(self):
        return [p for p in self.players if p.alive]

    # --- Helpers ---

    def _notify_task(self, event):
        """Notify task manager of an event (no-op if no task_mgr)."""
        if self.task_mgr:
            self.task_mgr.notify(event)

    def _check_all_dead(self):
        """Return True if no players are alive."""
        return not any(p.alive for p in self.players)

    def _filter_projected(self, sprites):
        """Filter sprites to only projected ones. Desert V2 overrides this."""
        return sprites

    def _coin_text_color(self, player):
        """Color for coin floating text. Desert overrides for combo coloring."""
        return COIN_GOLD

    # --- Speed multiplier ---

    def _speed_multiplier(self, player):
        """1.0x at speed 0, 2.5x at max speed. Linear interpolation."""
        max_speed = getattr(player, 'max_speed', 16)
        t = min(abs(getattr(player, 'speed', 0)) / max(max_speed, 1), 1.0)
        return 1.0 + t * 1.5  # 1.0 → 2.5

    # --- Collection methods ---

    def _collect_coins(self, player, coins):
        """Handle coin collection: combo, score, particles, sfx, task notify."""
        from core.hud import FloatingText
        coins = self._filter_projected(coins)
        for c in coins:
            player.coins += 1
            player.combo.hit()
            base = 100 if getattr(c, 'hazard', False) else 50
            pts = int(player.combo.get_bonus(base) * player.score_mult * self._speed_multiplier(player))
            player.score += pts
            is_hazard = getattr(c, 'hazard', False)
            particle_colors = [(255, 140, 0), (255, 200, 80)] if is_hazard else list(self.COIN_PARTICLE_COLORS)
            if self.COIN_PARTICLE_COUNT > 0:
                self.particles.burst(
                    player.rect.centerx,
                    player.rect.centery + self.COIN_PARTICLE_OFFSET_Y,
                    particle_colors,
                    self.COIN_PARTICLE_COUNT, self.COIN_PARTICLE_SIZE,
                    self.COIN_PARTICLE_SPEED, self.COIN_PARTICLE_LIFE)
            color = (255, 140, 0) if is_hazard else self._coin_text_color(player)
            label = f"+{pts} RISK!" if is_hazard else f"+{pts}"
            self.floating_texts.append(
                FloatingText(player.rect.centerx, player.rect.top - 15,
                             label, color))
            _snd.play_sfx("coin")
            self._notify_task('coin_collected')

    def _collect_powerups(self, player, powerups):
        """Handle powerup collection: apply + task notify."""
        from shared.powerup_handler import apply_powerup
        powerups = self._filter_projected(powerups)
        for pu in powerups:
            apply_powerup(player, pu, self)
            self._notify_task('powerup_collected')

    # --- Powerup effect drawing ---

    def _draw_powerup_effects(self, screen, players):
        """Draw shield bubble, phase ghost, and surge lines for alive players."""
        w, h = self.SHIELD_DIMS
        ox, oy = self.SHIELD_OFFSET

        for p in players:
            if p.shield:
                if not hasattr(self, '_shield_surf') or self._shield_surf.get_size() != (w, h):
                    self._shield_surf = pygame.Surface((w, h), pygame.SRCALPHA)
                self._shield_surf.fill((0, 0, 0, 0))
                pulse = 0.65 + 0.35 * math.sin(self.tick * 0.08)
                if self.SHIELD_SHAPE == 'circle':
                    r = w // 2
                    pygame.draw.circle(self._shield_surf,
                                       (*SHIELD_BLUE, int(50 * pulse)),
                                       (r, r), r - 1, 2)
                else:
                    pygame.draw.ellipse(self._shield_surf,
                                        (*SHIELD_BLUE, int(50 * pulse)),
                                        (0, 0, w, h), 2)
                screen.blit(self._shield_surf, (p.rect.centerx + ox, p.rect.centery + oy))

            if p.phase:
                if not hasattr(self, '_phase_surf') or self._phase_surf.get_size() != (w, h):
                    self._phase_surf = pygame.Surface((w, h), pygame.SRCALPHA)
                    if self.SHIELD_SHAPE == 'circle':
                        r = w // 2
                        pygame.draw.circle(self._phase_surf,
                                           (*PHASE_CYAN, 60), (r, r), r)
                    else:
                        pygame.draw.ellipse(self._phase_surf,
                                            (*PHASE_CYAN, 60), (0, 0, w, h))
                    self._phase_surf.set_alpha(100)
                screen.blit(self._phase_surf, (p.rect.centerx + ox, p.rect.centery + oy))

            if p.surge:
                for _i in range(4):
                    y = random.randint(0, SCREEN_HEIGHT)
                    pygame.draw.line(screen, SURGE_PINK,
                                     (0, y), (12, y + random.randint(-8, 8)), 2)
                    pygame.draw.line(screen, SURGE_PINK,
                                     (SCREEN_WIDTH - 12, y),
                                     (SCREEN_WIDTH, y + random.randint(-8, 8)), 2)

    # --- Phase dispatch ---

    def _check_phase_triggers(self):
        """Check if boss or asteroid phase should trigger."""
        if self.task_mgr and self.check_task_boss_trigger():
            self._spawn_boss_now()
        elif not self.task_mgr and self.check_asteroid_trigger():
            self.start_asteroid_phase()
            _snd.play_sfx("asteroid_warning")

    def _update_phase_logic(self, keys, alive_players, scroll_speed, diff_s):
        """Dispatch boss/asteroid/normal phase. Returns result or None."""
        if self.boss_active and self.boss:
            return self._update_boss_phase(keys, alive_players, scroll_speed)
        elif self.phase == 'asteroids':
            return self._update_asteroid_phase(keys, alive_players,
                                               scroll_speed, diff_s)
        else:
            self._update_normal_phase(keys, alive_players, scroll_speed, diff_s)
            self._check_phase_triggers()
            return None

    def _update_boss_phase(self, keys, alive_players, scroll_speed):
        """Boss phase: update, bolts, ram, hazards, env damage, defeat check."""
        self.boss.update(alive_players, scroll_speed)
        self._update_boss_bolts(keys, alive_players)
        self._check_boss_ram(alive_players)
        result = self._check_boss_attack_hazards(alive_players)
        if result:
            return result
        self._check_environmental_boss_damage()
        return self._check_boss_defeat(alive_players)

    def _update_normal_phase(self, keys, alive_players, scroll_speed, diff_s):
        """Normal phase: mode-specific gameplay. Override in subclass."""
        pass

    # --- Asteroid phase (common) ---

    def _update_asteroid_phase(self, keys, alive_players, scroll_speed,
                               diff_s=None):
        """Common asteroid phase: fire bolts, collide, spawn, player-hit."""
        from core.hud import FloatingText
        from sprites.asteroid import Asteroid

        # Fire heat bolts (auto-fire when asteroids on screen)
        has_target = len(self.asteroids) > 0
        for p in alive_players:
            fired, bx, by = p.try_fire_heat_bolt(keys, auto_fire=has_target)
            if fired:
                self._create_bolts_for_player(p, bx, by, self.heat_bolts)

        # Update heat bolts — check asteroid collisions
        for bolt in list(self.heat_bolts):
            self._asteroid_update_bolt(bolt)
            if not bolt.alive:
                continue
            if self._asteroid_bolt_offscreen(bolt):
                bolt.kill()
                continue
            for ast in list(self.asteroids):
                if bolt.rect.colliderect(ast.rect):
                    destroyed = ast.take_hit(bolt.damage)
                    self.particles.burst(bolt.rect.centerx, bolt.rect.centery,
                                         [SOLAR_YELLOW, SOLAR_WHITE], 6, 3, 20, 2)
                    bolt.kill()
                    if destroyed:
                        for p in alive_players:
                            pts = ast.points * p.score_mult
                            p.score += pts
                            self.floating_texts.append(
                                FloatingText(ast.rect.centerx, ast.rect.top - 10,
                                             f"+{pts}", SOLAR_YELLOW))
                        if destroyed['terminal']:
                            self.particles.burst(*ast.get_death_particles())
                            self.asteroids_cleared += 1
                            _snd.play_sfx("asteroid_destroy")
                        else:
                            self.particles.burst(*ast.get_split_particles())
                            self.shake.trigger(3, 8)
                            _snd.play_sfx("asteroid_split")
                            for frag_info in destroyed['fragments']:
                                self._asteroid_prep_fragment(ast, frag_info)
                                child = Asteroid.spawn_fragment(frag_info)
                                self.asteroids.add(child)
                                self.all_sprites.add(child)
                    else:
                        _snd.play_sfx("asteroid_hit")
                    break

        # Spawn asteroids
        self.asteroid_timer += 1
        if self.asteroid_timer > self._asteroid_spawn_interval():
            x, y, direction, kwargs = self._asteroid_spawn_pos()
            ast = Asteroid(x, y, direction=direction, **kwargs)
            self.asteroids.add(ast)
            self.all_sprites.add(ast)
            self.asteroid_timer = 0

        # Update asteroids
        for ast in list(self.asteroids):
            self._asteroid_update(ast, scroll_speed)

        # Asteroid-player collision
        for p in alive_players:
            if p.invincible_timer <= 0 and not p.ghost_mode and not p.phase:
                hit = pygame.sprite.spritecollideany(p, self.asteroids)
                if hit and not self._asteroid_hit_valid(hit):
                    hit = None
                if hit:
                    hit.kill()
                    p.take_hit(self.shake)
                    if self._check_all_dead():
                        return 'gameover'

        # Check boss trigger
        if self.check_boss_trigger():
            self._spawn_boss_now()

        return None

    # --- Asteroid phase hooks (override per mode) ---

    def _asteroid_spawn_interval(self):
        """Frames between asteroid spawns."""
        return self.ASTEROID_SPAWN_INTERVAL

    def _asteroid_spawn_pos(self):
        """Return (x, y, direction, extra_kwargs) for asteroid spawn."""
        from sprites.asteroid import DIR_DOWN
        ax = random.randint(80, SCREEN_WIDTH - 80)
        return (ax, -50, DIR_DOWN, {})

    def _asteroid_update_bolt(self, bolt):
        """Update a bolt during asteroid phase. Override for horizontal."""
        bolt.update()

    def _asteroid_bolt_offscreen(self, bolt):
        """Check if bolt is offscreen. Default False (vertical bolts auto-kill)."""
        return False

    def _asteroid_prep_fragment(self, parent_ast, frag_info):
        """Modify fragment info before spawning. Override for V2 tier."""
        pass

    def _asteroid_update(self, ast, scroll_speed):
        """Update a single asteroid. Override to pass road_geometry."""
        ast.update(scroll_speed)

    def _asteroid_hit_valid(self, hit):
        """Validate asteroid-player collision. Override for V2 projected guard."""
        return True

    # --- Environmental boss damage ---

    def _check_environmental_boss_damage(self):
        """Check mode-specific hazards damaging the boss."""
        group = self._get_boss_hazard_group()
        if group is None or not (self.boss and self.boss.alive):
            return
        for hazard in list(group):
            if hasattr(hazard, 'active') and not hazard.active:
                continue
            if hazard.rect.colliderect(self.boss.rect):
                self.boss.take_damage(self.boss.ENVIRONMENTAL_DAMAGE,
                                      "environmental")
                self.particles.burst(
                    hazard.rect.centerx, hazard.rect.centery,
                    [SOLAR_YELLOW, SOLAR_WHITE],
                    *self.ENV_DAMAGE_PARTICLE_ARGS)
                if hasattr(hazard, 'active'):
                    hazard.active = False
                hazard.kill()

    def _get_boss_hazard_group(self):
        """Sprite group whose members can damage the boss. None = none."""
        return None

    # --- Near-miss detection ---

    def _check_near_misses(self):
        """Real-time proximity detection with escalating chain rewards."""
        from core.hud import FloatingText
        group, offscreen_fn = self._get_near_miss_obstacles()
        if group is None:
            return
        if self.near_miss_cooldown > 0:
            self.near_miss_cooldown -= 1
        alive_players = self.get_alive_players()
        NEAR_MISS_DIST = 35
        triggered = False
        for obs in list(group):
            if offscreen_fn(obs):
                continue
            for p in alive_players:
                if p.invincible_timer > 0 or p.ghost_mode or p.phase:
                    continue
                dist = math.hypot(p.rect.centerx - obs.rect.centerx,
                                  p.rect.centery - obs.rect.centery)
                if dist < NEAR_MISS_DIST and self.near_miss_cooldown <= 0:
                    self.near_miss_chain += 1
                    chain_bonus = min(self.near_miss_chain, 5)
                    pts = int(75 * chain_bonus * p.score_mult * self._speed_multiplier(p))
                    p.score += pts
                    p.heat = min(p.heat + 8, 100)
                    self.floating_texts.append(
                        FloatingText(p.rect.centerx, p.rect.top - 25,
                                     f"NEAR MISS x{chain_bonus}! +{pts}",
                                     NEON_CYAN, size=16))
                    self.particles.burst(
                        obs.rect.centerx, obs.rect.centery,
                        [NEON_CYAN, (255, 255, 255)], 6, 2, 15, 2)
                    self.near_miss_cooldown = 12
                    _snd.play_sfx("select")
                    self._notify_task('near_miss')
                    triggered = True
                    break
        # Decay chain if no near-miss recently
        if not triggered and self.near_miss_cooldown <= 0 and self.near_miss_chain > 0:
            self.near_miss_chain = max(0, self.near_miss_chain - 1)

    def _get_near_miss_obstacles(self):
        """Return (group, offscreen_fn) for near-miss detection. None = none."""
        return None, None

    # --- Common overlay drawing ---

    def _draw_common_overlay(self, screen):
        """Draw floating texts, milestone, task/asteroid HUD, and boss."""
        for ft in self.floating_texts:
            ft.draw(screen)
        self.milestone.draw(screen)
        if self.task_mgr:
            self.task_mgr.draw_hud(screen,
                                   level_label=self.shared_state.level_label)
        else:
            self.draw_asteroid_hud(screen)
        if self.boss:
            self.boss.draw(screen)

    # --- New weapon helpers (shared across all 3 modes) ---

    def _bolt_direction(self):
        """Direction bolts travel. Override in Excitebike → 'right'."""
        return "up"

    def _create_bolts_for_player(self, p, bx, by, heat_bolts_group):
        """Create normal or multishot bolts for player. Adds to heat_bolts group."""
        from shared.boss_base import HeatBolt
        from shared.projectiles import MultishotBolt

        direction = self._bolt_direction()

        if p.multishot:
            # 3-bolt fan spread at ±0.26 rad (~15°)
            for offset in [-0.26, 0.0, 0.26]:
                bolt = MultishotBolt(bx, by, offset, p.color_accent, direction)
                heat_bolts_group.add(bolt)
        else:
            bolt = HeatBolt(bx, by, p.color_accent)
            if direction == "right":
                bolt.speed = 10
                bolt.rect.centery = by
            heat_bolts_group.add(bolt)

    def get_rocket_targets(self):
        """Return list of sprites rockets can home toward. Override per mode."""
        targets = []
        if self.boss and self.boss.alive:
            targets.append(self.boss)
        targets.extend(list(self.asteroids))
        return targets

    def _update_homing_rockets(self, alive_players):
        """Spawn rockets from players with active powerup, update, check collisions."""
        from shared.projectiles import HomingRocket
        from core.sound import play_sfx

        # Spawn rockets every 60 frames from players with active rockets
        for p in alive_players:
            if p.rockets and p.rocket_fire_cd <= 0:
                rx, ry = p.rect.centerx, p.rect.top
                rocket = HomingRocket(rx, ry, p.color_accent)
                self.homing_rockets.add(rocket)
                p.rocket_fire_cd = 60
                play_sfx("rocket_launch")

        # Update rockets with targets
        targets = self.get_rocket_targets()
        for rocket in list(self.homing_rockets):
            rocket.update(targets)
            if not rocket.alive:
                continue

            # Check collision with boss
            if self.boss and self.boss.alive and rocket.rect.colliderect(self.boss.rect):
                self.boss.take_damage(rocket.damage, "rocket")
                self.particles.burst(rocket.rect.centerx, rocket.rect.centery,
                                     [SOLAR_YELLOW, SOLAR_WHITE], 10, 5, 30, 3)
                self.shake.trigger(4, 12)
                rocket.kill()
                continue

            # Check collision with asteroids
            hit_something = False
            for ast in list(self.asteroids):
                if rocket.rect.colliderect(ast.rect):
                    destroyed = ast.take_hit(rocket.damage)
                    self.particles.burst(rocket.rect.centerx, rocket.rect.centery,
                                         [SOLAR_YELLOW, SOLAR_WHITE], 8, 4, 25, 3)
                    rocket.kill()
                    hit_something = True
                    if destroyed:
                        for p in alive_players:
                            pts = ast.points * p.score_mult
                            p.score += pts
                        if destroyed['terminal']:
                            self.particles.burst(*ast.get_death_particles())
                            self.asteroids_cleared += 1
                            _snd.play_sfx("asteroid_destroy")
                        else:
                            self.particles.burst(*ast.get_split_particles())
                            self.shake.trigger(3, 8)
                            _snd.play_sfx("asteroid_split")
                            for frag_info in destroyed['fragments']:
                                from sprites.asteroid import Asteroid
                                child = Asteroid.spawn_fragment(frag_info)
                                self.asteroids.add(child)
                                self.all_sprites.add(child)
                    break

            if hit_something:
                continue

            # Check collision with mode-specific obstacles (from get_rocket_targets)
            for target in targets:
                if target is self.boss:
                    continue  # already handled above
                if target in self.asteroids:
                    continue  # already handled above
                if hasattr(target, 'rect') and rocket.rect.colliderect(target.rect):
                    self.particles.burst(rocket.rect.centerx, rocket.rect.centery,
                                         [SOLAR_YELLOW, SOLAR_WHITE], 8, 4, 25, 3)
                    for p in alive_players:
                        p.score += 30 * p.score_mult
                    target.kill()
                    rocket.kill()
                    break

    def _spawn_orbit_orbs(self, player):
        """Create 8 OrbitOrbs for a player."""
        from shared.projectiles import OrbitOrb
        # Kill existing orbs for this player
        for orb in list(self.orbit_orbs):
            if orb.owner is player:
                orb.kill()
        # Spawn 8 new orbs
        for i in range(8):
            orb = OrbitOrb(player, i, 8, player.color_accent)
            self.orbit_orbs.add(orb)

    def _update_orbit_orbs(self, alive_players):
        """Check spawn pending, update positions, check collisions."""
        from core.sound import play_sfx

        # Check for pending orbit spawns
        for p in alive_players:
            if getattr(p, '_orbit8_spawn_pending', False) and p.orbit8:
                self._spawn_orbit_orbs(p)
                p._orbit8_spawn_pending = False

        # Update orbs
        for orb in list(self.orbit_orbs):
            orb.update()
            if not orb.alive:
                continue

            # Check collision with boss (absorb boss attack hazards)
            if self.boss and self.boss.alive:
                hazards = self.boss.get_attack_hazards()
                for htype, hdata in hazards:
                    hit = False
                    if htype == 'rect' and isinstance(hdata, pygame.Rect):
                        hit = orb.rect.colliderect(hdata)
                    elif htype == 'ring':
                        cx, cy, radius, thickness = hdata
                        dx = orb.rect.centerx - cx
                        dy = orb.rect.centery - cy
                        dist = math.sqrt(dx * dx + dy * dy)
                        hit = abs(dist - radius) < thickness
                    if hit:
                        self.particles.burst(orb.rect.centerx, orb.rect.centery,
                                             [orb.color, SOLAR_WHITE], 6, 3, 15, 2)
                        play_sfx("orb_hit")
                        orb.kill()
                        break

                if not orb.alive:
                    continue

            # Check collision with asteroids
            for ast in list(self.asteroids):
                if orb.rect.colliderect(ast.rect):
                    destroyed = ast.take_hit(orb.damage)
                    self.particles.burst(orb.rect.centerx, orb.rect.centery,
                                         [orb.color, SOLAR_WHITE], 6, 3, 15, 2)
                    play_sfx("orb_hit")
                    orb.kill()
                    if destroyed:
                        for p in alive_players:
                            pts = ast.points * p.score_mult
                            p.score += pts
                        if destroyed['terminal']:
                            self.particles.burst(*ast.get_death_particles())
                            self.asteroids_cleared += 1
                            _snd.play_sfx("asteroid_destroy")
                        else:
                            self.particles.burst(*ast.get_split_particles())
                            for frag_info in destroyed['fragments']:
                                from sprites.asteroid import Asteroid
                                child = Asteroid.spawn_fragment(frag_info)
                                self.asteroids.add(child)
                                self.all_sprites.add(child)
                    break

        # Clean up orbs for dead/deactivated players
        for orb in list(self.orbit_orbs):
            if not orb.owner or not orb.owner.alive or not orb.owner.orbit8:
                orb.kill()
