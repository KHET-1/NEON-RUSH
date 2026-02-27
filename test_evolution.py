#!/usr/bin/env python3
"""Evolution System — 2×6 Test Container.

Row A: Evolution OFF (6 tests)
Row B: Evolution ON  (6 tests)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import tempfile

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
results = []

def test(row, col, name, condition, detail=""):
    tag = f"{row}{col}"
    status = PASS if condition else FAIL
    results.append((tag, name, condition))
    print(f"  [{tag}] {status}  {name}" + (f"  ({detail})" if detail else ""))
    return condition

def fresh_mgr(tmpdir):
    """Create an EvolutionManager isolated from real game state."""
    mgr = EvolutionManager()
    mgr._state_file = os.path.join(tmpdir, f'evo_{id(mgr)}.json')
    mgr.max_tier = 1
    mgr.current_tier = 1
    mgr.cycle_count = 0
    return mgr


print("\n\033[96m╔══════════════════════════════════════════════╗")
print("║   NEON RUSH — Evolution 2×6 Test Container   ║")
print("╚══════════════════════════════════════════════╝\033[0m\n")

# ═══════════════════════════════════════════════════
# Setup: import all modules under test
# ═══════════════════════════════════════════════════
from core.evolution import EvolutionManager
from shared.player_state import SharedPlayerState
from shared.transition import TransitionEffect
from backgrounds.desert_bg import Background as DesertBG
from backgrounds.excitebike_bg import ExcitebikeBg
from backgrounds.micromachines_bg import MicroMachinesBG

# Stub out pygame for boss imports
import pygame
pygame.init()
pygame.display.set_mode((1, 1), pygame.NOFRAME)

from core.particles import ParticleSystem
particles = ParticleSystem()

# Use a temp dir so tests don't touch real game state
_tmpdir = tempfile.mkdtemp(prefix='neonrush_test_')

# ═══════════════════════════════════════════════════
# ROW A: Evolution OFF (default behavior preserved)
# ═══════════════════════════════════════════════════
print("\033[93m── Row A: Evolution OFF ──\033[0m")

# A1: EvolutionManager defaults (isolated)
mgr = fresh_mgr(_tmpdir)
mgr.enabled = False
test("A", 1, "Manager defaults",
     mgr.enabled == False and mgr.current_tier == 1 and mgr.cycle_count == 0,
     f"enabled={mgr.enabled}, tier={mgr.current_tier}, cycles={mgr.cycle_count}")

# A2: SharedPlayerState defaults (no evolution_tier disruption)
ss = SharedPlayerState(1, "normal")
test("A", 2, "PlayerState defaults",
     ss.evolution_tier == 1 and ss.current_mode == 0 and ss.bosses_defeated == 0,
     f"evo_tier={ss.evolution_tier}")

# A3: advance_mode works normally (no cycling)
ss.advance_mode()
ss.advance_mode()
ss.advance_mode()
test("A", 3, "3 advances → mode=3, bosses=3",
     ss.current_mode == 3 and ss.bosses_defeated == 3,
     f"mode={ss.current_mode}, bosses={ss.bosses_defeated}")

# A4: Transition without tier badge
tr = TransitionEffect('glitch', 'TEST MODE')
test("A", 4, "Transition default tier=1",
     tr.evolution_tier == 1 and tr.mode_name == 'TEST MODE')

# A5: Desert BG tier=1 (no V2 layers)
bg1 = DesertBG(particles, tier=1)
test("A", 5, "Desert BG V1 (no V2 attrs)",
     bg1.tier == 1 and not hasattr(bg1, '_stars'),
     f"tier={bg1.tier}")

# A6: Boss HP unscaled at tier=1
from bosses.desert_boss import DesertBoss
from bosses.excitebike_boss import ExcitebikeBoss
from bosses.micromachines_boss import MicroMachinesBoss

db1 = DesertBoss(particles, evolution_tier=1)
eb1 = ExcitebikeBoss(particles, evolution_tier=1)
mb1 = MicroMachinesBoss(particles, evolution_tier=1)
test("A", 6, "Boss HP at tier=1 (300/300/350)",
     db1.MAX_HP == 300 and eb1.MAX_HP == 300 and mb1.MAX_HP == 350,
     f"desert={db1.MAX_HP}, excite={eb1.MAX_HP}, micro={mb1.MAX_HP}")

# ═══════════════════════════════════════════════════
# ROW B: Evolution ON (cycling + scaling)
# ═══════════════════════════════════════════════════
print("\n\033[93m── Row B: Evolution ON ──\033[0m")

# B1: start_run resets from clean state, advance_cycle → tier 2
mgr2 = fresh_mgr(_tmpdir)
mgr2.enabled = True
mgr2.start_run()  # max_tier=1, so starts at tier 1
tier = mgr2.advance_cycle()
test("B", 1, "advance_cycle → tier=2",
     tier == 2 and mgr2.current_tier == 2 and mgr2.cycle_count == 1,
     f"tier={tier}, cycles={mgr2.cycle_count}")

# B2: Scaling formulas correct at tier 2
test("B", 2, "HP scale=1.3, speed=1.1 at tier 2",
     abs(mgr2.hp_scale() - 1.3) < 0.01 and abs(mgr2.speed_scale() - 1.1) < 0.01,
     f"hp={mgr2.hp_scale():.2f}, speed={mgr2.speed_scale():.2f}")

# B3: reset_for_cycle on SharedPlayerState
ss2 = SharedPlayerState(1, "normal", evolution_tier=1)
ss2.scores = [5000]
ss2.coins = [42]
ss2.lives = [2]
ss2.bosses_defeated = 3
ss2.current_mode = 3
ss2.reset_for_cycle(2)
test("B", 3, "reset_for_cycle keeps score/lives, resets mode",
     ss2.current_mode == 0 and ss2.evolution_tier == 2 and
     ss2.scores == [5000] and ss2.lives == [2] and ss2.bosses_defeated == 3,
     f"mode={ss2.current_mode}, tier={ss2.evolution_tier}, score={ss2.scores}")

# B4: Transition with tier badge
tr2 = TransitionEffect('glitch', 'EVOLUTION V2!', evolution_tier=2)
test("B", 4, "Transition carries tier=2",
     tr2.evolution_tier == 2 and 'V2' in tr2.mode_name,
     f"tier={tr2.evolution_tier}, name={tr2.mode_name}")

# B5: V2 backgrounds have extra layers
bg2_desert = DesertBG(particles, tier=2)
bg2_excite = ExcitebikeBg(tier=2)
bg2_micro = MicroMachinesBG(tier=2)
test("B", 5, "V2 backgrounds have extra layers",
     hasattr(bg2_desert, '_stars') and hasattr(bg2_desert, '_mesas') and
     hasattr(bg2_excite, 'mountains_deep') and hasattr(bg2_excite, '_grass_tufts') and
     hasattr(bg2_micro, '_haze_phase') and hasattr(bg2_micro, '_tire_marks'),
     "stars, mesas, mountains_deep, grass_tufts, haze, tire_marks")

# B6: Boss HP scales at tier 2 and tier 3
db2 = DesertBoss(particles, evolution_tier=2)
eb2 = ExcitebikeBoss(particles, evolution_tier=2)
mb2 = MicroMachinesBoss(particles, evolution_tier=2)
db3 = DesertBoss(particles, evolution_tier=3)
mb3 = MicroMachinesBoss(particles, evolution_tier=3)
test("B", 6, "Boss HP scales: T2 (+30%), T3 (+60%)",
     db2.MAX_HP == 390 and eb2.MAX_HP == 390 and mb2.MAX_HP == 455 and
     db3.MAX_HP == 480 and mb3.MAX_HP == 560,
     f"T2: d={db2.MAX_HP} e={eb2.MAX_HP} m={mb2.MAX_HP} | T3: d={db3.MAX_HP} m={mb3.MAX_HP}")

# ═══════════════════════════════════════════════════
# Persistence test (bonus — verifies save/load)
# ═══════════════════════════════════════════════════
print("\n\033[93m── Persistence ──\033[0m")
mgr3 = fresh_mgr(_tmpdir)
mgr3.enabled = True
mgr3.start_run()  # fresh: max_tier=1, starts at tier 1
mgr3.advance_cycle()  # tier 2
mgr3.advance_cycle()  # tier 3
mgr3.save()

mgr4 = fresh_mgr(_tmpdir)
mgr4._state_file = mgr3._state_file  # read from same file
mgr4.load()
print(f"  [P1] {PASS if mgr4.max_tier == 3 else FAIL}  "
      f"Persist max_tier=3 across load  (loaded={mgr4.max_tier})")
results.append(("P1", "Persistence", mgr4.max_tier == 3))

# ═══════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════
total = len(results)
passed = sum(1 for _, _, ok in results if ok)
failed = total - passed

print(f"\n\033[96m{'═' * 48}")
print(f"  Results: {passed}/{total} passed", end="")
if failed:
    print(f"  ({failed} FAILED)", end="")
print(f"\n{'═' * 48}\033[0m\n")

pygame.quit()
sys.exit(0 if failed == 0 else 1)
