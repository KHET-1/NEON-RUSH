# REFACTOR_SYNC — Opus A/B Coordination

## Status

| Instance | Section | Status | Started | Completed |
|----------|---------|--------|---------|-----------|
| Opus A | Foundation Layer | DONE | 2026-03-01 | 2026-03-01 |
| Opus B | Content Layer | DONE | 2026-03-01 | 2026-03-01 |

## Opus A Changes (Foundation Layer)

### A1: Consolidated Constants
- Added to `core/constants.py`: V2 desert bg palette, anti-camp constants, SIM_MAX_CATCHUP
- Background files now import from constants instead of defining locally
- `neon_rush.py` imports ANTI_CAMP_RADIUS, ANTI_CAMP_TIME, SIM_MAX_CATCHUP

### A2: Split draw_hud()
- `core/hud.py`: draw_hud() split into `_draw_player_panel()`, `_draw_powerup_indicators()`, `_draw_game_info()`
- draw_hud() is now a ~40 line orchestrator

### A3: Extracted ComboTracker + MilestoneTracker
- New file: `core/combo.py` — ComboTracker + MilestoneTracker moved from `core/ui.py`
- `core/ui.py` re-exports both for backward compat: `from core.combo import ComboTracker, MilestoneTracker`
- Mode files can import from either location

### A4: GameMode Base Class Expansion
- `shared/game_mode.py` now has:
  - `_spawn_boss_now()` — common boss spawn (calls `_create_boss()`)
  - `_create_boss()` — abstract, override per mode to return boss instance
  - `_on_boss_defeated(alive_players, boss_points)` — common defeat handling
  - `_update_boss_bolts(keys, alive_players)` — bolt firing + boss collision
  - `_check_boss_ram(alive_players)` — ram damage during vulnerability
  - `_check_boss_attack_hazards(alive_players)` — player hazard collision
  - Common sprite group init: coins_group, powerups_group, heat_bolts
  - Common state: floating_texts, screen_flash, milestone, ai_controllers, difficulty_scale

### A5+A6: Tier Naming + Boss Base
- `shared/boss_base.py`: Boss.__init__() takes `tier=1` param, sets `self.tier`
- All boss files: `self._evolution_tier` → `self.tier` (set via super().__init__)
- All `getattr(self, '_evolution_tier', 1)` → `self.tier`

## Opus A Verification Results
- `python3 -c "import neon_rush"` — PASS
- 60-frame headless test: tier 1/2/3 × desert/excitebike/micro — ALL PASS (9/9)
- `test_evolution.py` — 13/13 passed
- `grep -r "_evolution_tier" .` — 0 results (CLEAN)

## What Opus A Already Did to Mode/Boss Files
Opus A went ahead and applied many of the B tasks since they were needed for testing:
1. All 3 modes now use `_create_boss()` instead of `_spawn_boss_now()` (B1 partial)
2. All 3 modes use `self._check_boss_defeat()` / `self._on_boss_defeated()` (B1 partial)
3. Desert + Micro use `self._update_boss_bolts()` + `self._check_boss_ram()` + `self._check_boss_attack_hazards()` (B1 partial)
4. All 3 bosses pass `tier=evolution_tier` to `Boss.__init__()` (B2 DONE)
5. All `getattr(self, '_evolution_tier', 1)` replaced with `self.tier` in bosses (B2 DONE)
6. Duplicate sprite group init removed from all 3 modes (B1 partial)

## Opus B Changes (Content Layer)

### B1: Mode Cleanup — All 3 Modes Using Base Class Methods
- All 3 modes use `_update_phase_logic()` for boss/asteroid/normal dispatch
- All 3 modes use `_collect_coins()` / `_collect_powerups()` with hook overrides
- All 3 modes use `_draw_powerup_effects()` / `_draw_common_overlay()`
- All 3 modes use `_check_near_misses()` with `_get_near_miss_obstacles()` override
- Desert uses `_check_environmental_boss_damage()` via `_get_boss_hazard_group()` override
- Desert: `_filter_projected()`, `_coin_text_color()`, `_update_normal_phase()` hooks
- Desert: Asteroid hooks — `_asteroid_spawn_pos()`, `_asteroid_prep_fragment()`, `_asteroid_update()`, `_asteroid_hit_valid()`
- Excitebike: Horizontal bolt hooks — `_asteroid_update_bolt()`, `_asteroid_bolt_offscreen()`, `_bolt_direction()`
- Micro Machines: Top-down hooks — `COIN_PARTICLE_COUNT=0`, `SHIELD_SHAPE='circle'`
- Mode line counts: Desert 569→434, Excitebike 553→371, Micro 475→292

### B2: Boss Tier Standardization — DONE (by Opus A)

### B3: Split autoplay.py — DONE (fully split)
- `ai/autoplay.py` (380L) — parse_args + run_grid + run_single + main
- `ai/learning_brain.py` (476L) — LearningBrain + SmartKeys + FakeKeys
- `ai/run_stats.py` (48L) — RunStats
- `ai/game_instance.py` (187L) — GameInstance
- `autoplay.py` (16L) — thin wrapper → `from ai.autoplay import main`

### B4: neon_rush.py Constants — DONE (by Opus A)

### B5: Sprite Tier-Branching Consistency — VERIFIED
- All sprites use consistent `if tier >= 3: ... elif tier >= 2: ... else:` pattern
- 15 uses of `tier >= 3`, 25 uses of `tier >= 2`, zero uses of `tier == 1` or `tier == 2`

## Opus B Verification Results
- `python3 -c "import neon_rush"` — PASS
- 60-frame headless test: tier 1/2/3 × desert/excitebike/micro — ALL PASS (9/9)
- `test_evolution.py` — 13/13 passed
- ai/ module imports — PASS (LearningBrain, SmartKeys, FakeKeys, RunStats, GameInstance)
- autoplay.py entry point — PASS (parse_args, all re-exports accessible)
