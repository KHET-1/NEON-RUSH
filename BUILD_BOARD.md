# NEON RUSH — Build Board

> **Pipeline:** BACKLOG → WIP → REVIEW → COMPLETE → DIAMOND
>
> **Rules:**
> - Claim before working (add your name + timestamp to WIP)
> - One task at a time per contributor
> - REVIEW needs validation from another AI or human within 24 hours
> - Reviewer gets credited alongside builder
> - DIAMOND = exceptional quality, nominated by reviewer

---

## BACKLOG

*Grab one. Move it to WIP with your name and start time.*

### High Impact
- [ ] Balance pass — playtest all 3 modes on all 3 difficulties, adjust spawn rates and boss HP
- [ ] 2-player playtest — verify 2P works across all modes + boss fights
- [ ] Music variety — add 2-3 more procedural music patterns per mode (dynamic tempo)
- [ ] Transition polish — more dramatic mode-change animations (particles, screen warp)

### Medium Impact
- [ ] Boss visual polish — better procedural sprite art for all 3 bosses
- [ ] New attack patterns — add 1-2 more attacks per boss (follow AttackPattern base)
- [ ] Powerup visual feedback — screen-edge glow when shield/magnet/slowmo active
- [ ] HUD redesign — modernize score display, better boss HP bar, powerup timers
- [ ] Accessibility — color-blind mode toggle, control remapping

### Low Impact / Polish
- [ ] Particle variety — different burst shapes for hits, boosts, deaths, coin pickup
- [ ] Victory screen — animated stats, mode replay highlights
- [ ] Title screen — animated background, mode preview
- [ ] Engine sound per mode — different engine tones for bike vs car vs top-down
- [ ] Combo system polish — bigger visual feedback for high combos

### Stretch Goals
- [ ] New game mode (Mode 4) — follow GameMode pattern, new perspective
- [ ] Leaderboard per mode — separate highscores for each mode
- [ ] Replay system — record/playback inputs
- [ ] Settings menu — volume, difficulty, controls

---

## WIP

*Format: `[~] Name | Started YYYY-MM-DD HH:MM | Task description`*

- [~] Specter (Swarm: solo) | Started 2026-02-27 22:00 | Balance pass — Desert Velocity mode (all 3 difficulties, spawn rates, boss HP)
- [~] Architect | Started 2026-03-01 | Boss Rush Redesign — V3 visuals (13 files need `if tier >= 3:` branches) — PLANNED ONLY, not implemented

---

## REVIEW

*Format: `[?] Name | Done YYYY-MM-DD HH:MM | Task description`*
*Add: `Reviewer: (unclaimed)` until someone picks it up.*
*24-hour clock starts when task enters REVIEW.*

*(empty)*

---

## COMPLETE

*Format: `[x] Builder (Swarm) | Date | Task description`*
*Add: `Reviewer: Name (Swarm or human) | Validated Date`*
*Reviewer MUST be from a different swarm or be human.*

- [x] Architect (Swarm: founding) | 2026-02-27 | Full codebase extraction from monolith to 35-file modular architecture
  - Reviewer: Rathin (human) | Validated 2026-02-27
- [x] Parallel Assist (Swarm: parallel-01) | 2026-02-27 | Excitebike boss, Micro Machines boss, Micro Machines background
  - Reviewer: Architect (Swarm: founding) | Validated 2026-02-27 (integrated + tested)
- [x] Architect (Swarm: founding) | 2026-02-27 | Import aliasing bug fix (SFX, fonts, channels)
  - Reviewer: Rathin (human) | Validated 2026-02-27 (game runs clean)
- [x] Architect (Swarm: founding) | 2026-02-27 | FONT_POWERUP crash fix (module-level import capture)
  - Reviewer: Rathin (human) | Validated 2026-02-27 (confirmed PowerUp renders)
- [x] Specter (Swarm: solo) | 2026-02-27 | Doctrine audit of parallel-01 boss/bg files — added missing get_attack_hazards(), removed 3x except:pass violations (Rule 7.6), 600-frame headless validation
  - Reviewer: Rathin (human) | Pending
- [x] Architect | 2026-03-01 | Boss Rush Redesign — task system, level grid, GAME_DESIGN.md, balance_metrics.py
  - Created: core/tasks.py (~430 lines), tools/balance_metrics.py, GAME_DESIGN.md
  - Edited: core/constants.py, shared/game_mode.py, all 3 modes, neon_rush.py, shared/boss_base.py
  - Fixed: MicroMachinesBoss crash, road disconnect, excitebike ramp damage, coin_combo, milestones
  - Added: --windowed, --ai CLI flags, display.py RESIZABLE windowed mode
  - Reviewer: Rathin (human) | Pending

---

## DIAMOND

*Exceptional work. Reviewer nominates. Gets highlighted in credits.*

*Format: `[*] Builder | Date | Task description`*
*Add: `Reviewer: Name | "Why this is diamond"`*

- [*] Lead Architect | 2026-02-27 | Crash reporting system with full session tracking
  - Reviewer: Rathin (human) | "Auto-save to crash_logs, event log, player snapshots, copy button, human-readable errors — production quality"

---

## SWARM & REVIEW RULES

### Opus Swarm Protocol

Every Opus session that does build work MUST also spawn a review capability:

1. **Builder swarm** — works on tasks from BACKLOG
2. **Review sentinel** — one agent always watching the REVIEW section

Both agents share the same **Swarm ID** (the parent session hash). This ID is declared in check-in.

### The Independence Rule (Non-Negotiable)

**A review CANNOT come from the same swarm as the builder.**

```
Swarm "abc123" builds a feature   →  Swarm "abc123" CANNOT review it
Swarm "def456" or Human           →  CAN review it
```

**Why:** Self-review is worthless. The same context that produced the code has the same blind spots. Fresh eyes catch what the builder missed.

**How to enforce:**
- Every REVIEW entry includes the builder's Swarm ID
- Reviewer must have a DIFFERENT Swarm ID (or be human)
- If no other swarm is available, the task waits for the next session or human review

**What this means in practice:**
- Session A spawns builders + a sentinel. Builders build. The sentinel reviews work from PREVIOUS sessions.
- Session B spawns builders + a sentinel. Session B's sentinel reviews Session A's work. Session A's sentinel reviews Session B's work.
- Humans can review anything from any swarm.

### Review Entry Format

```markdown
- [?] Volt (Swarm: abc123) | Done 2026-02-27 12:30 | Task description
  - Reviewer: (needs reviewer from different swarm or human)
```

When claiming a review:
```markdown
- [?] Volt (Swarm: abc123) | Done 2026-02-27 12:30 | Task description
  - Reviewer: Ember (Swarm: def456) | Reviewing...
```

---

## REVIEW PROTOCOL

### For the Reviewer

Every Opus session MUST have **one agent watching the REVIEW section**. This is the review sentinel. It reviews work from OTHER swarms only.

**Review Sentinel Checklist** (run these in order — fast rejection saves everyone's time):

```bash
# 1. INSTANT: Syntax check (5 sec)
python3 -m py_compile <changed_file>

# 2. INSTANT: No external assets (2 sec)
fd -e png -e jpg -e wav -e ogg -e mp3 -e ttf -e otf

# 3. INSTANT: Import safety (3 sec)
rg '^from core\.(sound|fonts) import' --type py | grep -v 'import SFX\|import music_loops\|import load_font\|import init_'

# 4. INSTANT: No bare except:pass (2 sec)
rg 'except.*:.*pass$' --type py

# 5. INSTANT: Boss contract intact (3 sec)
rg 'RAM_DAMAGE|ENVIRONMENTAL_DAMAGE' bosses/

# 6. QUICK: Full import test (10 sec)
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 -c "
import sys; sys.path.insert(0,'.')
import pygame; pygame.init(); pygame.mixer.init(frequency=44100,size=-16,channels=1,buffer=512)
from core.fonts import init_fonts; from core.sound import init_sounds
pygame.display.set_mode((800,600)); init_fonts(); init_sounds()
from modes.desert_velocity import DesertVelocityMode
from modes.excitebike import ExcitebikeMode
from modes.micromachines import MicroMachinesMode
print('All imports OK')
"

# 7. GAMEPLAY: Run 300 frames of affected mode (15 sec)
# (use headless simulation from AI_CHECKIN.md §6)

# 8. HUMAN: Play for 2 minutes if available
python3 neon_rush.py
```

**Steps 1-5 take under 15 seconds total.** If any fail, reject immediately with the specific failure.

**Validation verdict:**
- **APPROVE** → Move to COMPLETE, add your name as reviewer
- **REJECT** → Comment what failed, move back to WIP for the builder to fix
- **DIAMOND** → Approve + nominate: move to DIAMOND with your review quote

### Reviewer Credit

Reviewers get listed in COMPLETE/DIAMOND entries AND in the Credits table in `AI_CHECKIN.md` §10. Good reviews are valued — catching a bug before it ships is as important as writing the code.

---

## SUGGESTION BOX

*Got an idea? Drop it here. Good ideas get promoted to BACKLOG. Great ones get a chef's kiss.*

**Format:** `- [idea] Name | Date | Your idea`
**Chef's Kiss:** `- [kiss] Name | Date | Your idea` *(Nominated by someone who loved it)*

**Rules:**
- Anyone can add ideas — builders, reviewers, humans, drive-by visitors
- No idea is too small or too wild. "What if the boss had a taunt?" counts.
- If you see an idea you love, add a chef's kiss nomination: change `[idea]` to `[kiss]` and add your name
- Ideas with a chef's kiss get priority when moving to BACKLOG
- Check this box when you check in — there might be something brilliant waiting
- **2-HOUR RULE:** Worked 2+ hours? You MUST drop something here before signing off — an idea, a joke, a useful prompt, a lesson learned. No empty exits.

### Ideas

*(Drop yours below. Newest at the top.)*

- [idea] Architect | 2026-03-01 | **V3 Visuals** — 13 files need `if tier >= 3:` branches. Desert V3: crimson sandstorm, lightning. Excitebike V3: night mode, neon signs, rain. Micro V3: holographic grid, glitch effects. See plan in `~/.claude/plans/kind-sparking-bumblebee.md` §7.
- [idea] Architect | 2026-03-01 | **"Micro Machines backwards" report** — user said steering feels backwards. Top-down mode uses heading-based rotation where up on stick = forward relative to car heading, not screen-up. May need a "relative vs absolute steering" option or just make it screen-relative for accessibility.
- [idea] Architect | 2026-03-01 | **--windowed still fullscreen bug** — user reported --windowed didn't work. Code verified correct via headless test. Possible causes: stale __pycache__ (cleared), or user ran without the flag. Added print confirmations + RESIZABLE flag. Needs live verification.
- [idea] Architect | 2026-03-01 | **tools/balance_metrics.py** — created but not run yet. Needs `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 tools/balance_metrics.py` to baseline current pacing.

### Chef's Kiss Hall

*Ideas so good someone couldn't help themselves.*

*(empty — be the first to nominate one)*

---

## NOTES

- Tasks can be split. If "Balance pass" is too big, break it into "Balance — Desert mode", "Balance — Excitebike", etc.
- If you find a bug while working on something else, add it to BACKLOG (don't scope-creep your current task)
- DIAMOND is rare. Most good work is COMPLETE. DIAMOND means it made someone say "wow"
- The 24-hour review window is a guideline for humans. AI reviewers should process the queue immediately when they check in
- **Check the Suggestion Box** — there may be ideas or chef's kisses worth reading before you pick a task
