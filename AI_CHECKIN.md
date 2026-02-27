# NEON RUSH — AI Contributor Doctrine & Check-In

> **STOP. Read this entire document before writing ANY code.**
> Every AI assistant MUST check in before proceeding. No exceptions.

---

## 1. CHECK-IN (Do This First)

Output this block exactly before doing any work:

```
=== NEON RUSH CHECK-IN ===
Name:      [your chosen name — pick one, it's yours for this session]
Model:     [claude-opus-4/claude-sonnet-4/etc]
Role:      [builder | reviewer | both]
Swarm:     [parent-session-hash or "solo"]
Task:      [1-line: what you're here to do]
Aligned:   [YES or CONFLICT — if conflict, explain below]
Conflicts: [NONE or describe what breaks doctrine]
=== CHECKED IN ===
```

**Your Name:** Pick a name. It goes in the credits. Could be anything — "Ember", "Volt", "Nightcrawler", whatever fits your vibe this session. This name follows your contributions through the build board.

**Swarm ID:** If you're part of a swarm (parallel agents from one session), include your swarm ID. Format: `Swarm: [parent-session-short-hash or "solo"]`. This is critical for review rules — see §4.

**If your task conflicts with doctrine:** Don't silently break rules. State `CONFLICT`, explain why, and propose an aligned alternative. The team will help you find a path.

**After check-in:** Scan the **Suggestion Box** in `BUILD_BOARD.md`. There might be ideas or chef's kisses worth reading before you start work. If you have a good idea during your session, drop it there — don't let it evaporate.

---

## 1.5. SUGGESTION BOX (Ideas Welcome)

The **Suggestion Box** lives in `BUILD_BOARD.md` (bottom section). It's a low-friction place for anyone to drop ideas without the overhead of a formal BACKLOG task.

**When to use it:**
- You spot something that could be better but it's not your current task
- You have a creative idea mid-session (new mechanic, visual effect, gameplay tweak)
- You see a pattern that could apply across modes
- You played the game and thought "what if..."

**How it works:**
1. **Drop an idea:** Add `- [idea] YourName | Date | Description` to the Ideas section
2. **Love someone's idea?** Change `[idea]` to `[kiss]` and add your name — it moves to Chef's Kiss Hall
3. **Chef's Kiss ideas get BACKLOG priority** — they've been validated by a second pair of eyes
4. **Humans and AIs alike can promote** a chef's kiss idea to BACKLOG when it's time to build it

**The 2-Hour Rule:**
Any contributor who works longer than 2 hours MUST leave something in the Suggestion Box before signing off. It doesn't have to be a feature idea — it can be:
- A game idea or improvement suggestion
- A good joke (the team needs laughs too)
- A useful prompt pattern you discovered
- A piece of knowledge worth sharing (debugging trick, Pygame gotcha, design insight)

**No empty exits after 2 hours.** You learned something — share it.

**What makes a good suggestion:**
- Specific enough to act on ("boss taunts the player with text bubbles before attacking")
- Not just "make it better" — say HOW or WHAT specifically
- Can be wild — stretch goals welcome, that's what the box is for

---

## 2. THE GAME (What You're Working On)

**NEON RUSH** — Three-perspective Pygame racing game with boss transitions.

```
Desert Velocity (vertical)  ──Boss──>  Excitebike (side-scroll)  ──Boss──>  Micro Machines (top-down)  ──Boss──>  Victory
```

**Core Identity:**
- Neon aesthetic (cyan, magenta, solar yellow on dark)
- Heat mechanic = core loop (accelerate → build heat → boost or ghost mode)
- Procedural EVERYTHING — no external asset files
- Boss fights with 3 damage methods (ram, heat bolt, environmental)
- Self-healing crash recovery with full session reporting
- 1-player and 2-player cooperative

**Launch:** `cd ~/NEONRUSH && source .venv/bin/activate && python3 neon_rush.py`

---

## 3. PROJECT STATUS (What's Done, What Needs Work)

### Component Health

| Component | Status | Lines | Quality | Needs |
|-----------|--------|-------|---------|-------|
| **Core Engine** (core/) | COMPLETE | ~1,730 | Solid | Minor polish |
| **Desert Velocity** | COMPLETE | ~360 | Solid | Balance tuning |
| **Excitebike** | COMPLETE | ~390 | Solid | Balance tuning |
| **Micro Machines** | COMPLETE | ~320 | Solid | Balance tuning |
| **Desert Boss** | COMPLETE | ~420 | Good | Visual polish |
| **Excitebike Boss** | COMPLETE | ~690 | Good | Visual polish |
| **Micro Machines Boss** | COMPLETE | ~800 | Good | Visual polish |
| **Transitions** | COMPLETE | ~190 | Functional | Could be flashier |
| **Crash Reporting** | COMPLETE | ~350 | Solid | — |
| **Sound/Music** | COMPLETE | ~225 | Functional | Music variety |
| **2-Player Mode** | COMPLETE | — | Untested | Needs playtesting |
| **Victory Screen** | COMPLETE | ~50 | Basic | Could be better |

**Total: ~7,700 lines across 35 files. Fully playable end-to-end.**

### Where AI Can Help RIGHT NOW

| Area | Difficulty | Impact | What To Do |
|------|-----------|--------|------------|
| **Balance tuning** | Easy | High | Playtest, adjust spawn rates, boss HP, thresholds |
| **Visual polish** | Medium | High | Better sprite art (still procedural), screen effects |
| **Music variety** | Medium | Medium | More music patterns per mode, dynamic tempo |
| **Transition effects** | Medium | Medium | More dramatic mode-change animations |
| **2P playtesting** | Easy | Medium | Verify 2P works across all 3 modes |
| **New attack patterns** | Medium | Medium | Add boss attacks (follow AttackPattern base) |
| **Particle effects** | Easy | Low | More particle variety on hits, boosts, deaths |
| **HUD improvements** | Easy | Low | Better powerup indicators, boss HP bar style |
| **Accessibility** | Medium | Medium | Color-blind modes, control remapping |
| **New game mode** | Hard | High | Follow GameMode pattern, new perspective |

---

## 4. BUILD BOARD (The Pipeline)

**One file tracks everything:** `BUILD_BOARD.md`

### How It Works

```
BACKLOG  ──claim──>  WIP  ──done──>  REVIEW  ──validated──>  COMPLETE  ──exceptional──>  DIAMOND
```

**That's it.** Find a task. Do the task. Get it validated. Next task.

### Rules

1. **Claim before working** — Move task from BACKLOG to WIP with your name and timestamp
2. **One task at a time** per contributor (unless tasks are independent)
3. **When done** — Move to REVIEW. The 24-hour clock starts NOW
4. **Review required** — At least one other AI or human must validate before COMPLETE
5. **24-hour rule** — Unreviewed code in REVIEW for 24+ hours gets flagged for revert discussion
6. **DIAMOND** — Exceptional work. Reviewer nominates it. Gets highlighted in credits

### What Validation Means

The reviewer checks:
- Does it follow doctrine? (architecture, no assets, import safety)
- Does it actually work? (run it, test it)
- Does it break anything else?
- Is the code clean? (no dead code, no bare except, no hacks)

**Reviewer gets credited too.** Every COMPLETE item lists both builder and reviewer.

### Board Format

Tasks in `BUILD_BOARD.md` look like this:

```markdown
### BACKLOG
- [ ] Better boss death explosions (particle variety)
- [ ] Music tempo scales with game speed
- [ ] 2P camera behavior in Micro Machines

### WIP
- [~] Ember | Started 2026-02-27 14:00 | Excitebike ramp visual polish

### REVIEW
- [?] Volt | Done 2026-02-27 12:30 | Desert boss sandstorm pattern rework
  - Reviewer: (unclaimed — needs reviewer!)

### COMPLETE
- [x] Nightcrawler | 2026-02-27 | Import aliasing fix (SFX, fonts, channels)
  - Reviewer: Rathin (human) | Validated 2026-02-27

### DIAMOND
- [*] Ember | 2026-02-27 | Crash reporting system with session tracking
  - Reviewer: Volt | "Clean architecture, thorough metadata, copy-to-clipboard — chef's kiss"
```

---

## 5. UPDATING DOCS (What To Update When)

**When you change code, update these:**

| What Changed | Update This | How |
|-------------|-------------|-----|
| Finished a task | `BUILD_BOARD.md` | Move from WIP → REVIEW |
| Validated someone's work | `BUILD_BOARD.md` | Move from REVIEW → COMPLETE (add your name) |
| Added a new file | `AI_CHECKIN.md` §8 File Reference | Add entry to the table |
| Changed architecture | `AI_CHECKIN.md` §7 Doctrine | Update affected rule |
| Added new constants | `core/constants.py` | Keep grouped by category |
| Added new SFX | `core/sound.py` init_sounds() | Add to SFX dict |
| Added new game mode | All of: mode, sprites, bg, boss files | Follow existing pattern exactly |
| Fixed a bug | `crash_logs/` or git commit | Note what caused it and what fixed it |
| Changed controls | `AI_CHECKIN.md` §7.9 Controls | Update control table |

**The doctrine is a living document.** If you amend a rule, note the change with your name and date at the bottom of this file.

---

## 6. TOOLS AVAILABLE

### Environment

| Tool | Location | Version | Use For |
|------|----------|---------|---------|
| Python | System | 3.13.5 | Everything |
| Pygame | `.venv/` | 2.6.1 | Game engine |
| Git | System | 2.47 | Version control |
| ripgrep (rg) | `~/.local/bin` | 15.1.0 | Fast code search |
| fd | `~/.local/bin` | 10.3.0 | Fast file find |
| bat | `~/.local/bin` | 0.26.1 | Syntax-highlighted file view |
| jq | `~/.local/bin` | 1.8.1 | JSON processing |
| gh | `~/.local/bin` | 2.87.3 | GitHub CLI |
| fzf | `~/.local/bin` | 0.68.0 | Fuzzy finder |

### Python Venv

```bash
source ~/NEONRUSH/.venv/bin/activate
```

Always activate before running. The venv has pygame installed.

### How To Use Key Tools

**Run the game:**
```bash
cd ~/NEONRUSH && source .venv/bin/activate && python3 neon_rush.py
```

**Headless test (no display needed):**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 -c "
import sys; sys.path.insert(0, '.')
import pygame; pygame.init(); pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
# ... your test code
"
```

**Search codebase fast:**
```bash
rg 'pattern' --type py                    # Search Python files
rg 'class.*Boss' --type py                # Find all boss classes
rg 'def update' modes/                    # Find update methods in modes
fd '*.py' sprites/                        # List sprite files
```

**Check crash logs:**
```bash
ls -la crash_logs/                         # Recent crashes
cat crash_logs/crash_*.txt | head -30      # Quick look at latest
```

**Validate all imports compile:**
```bash
source .venv/bin/activate
python3 -c "import py_compile; import glob
for f in glob.glob('**/*.py', recursive=True):
    if '.venv' not in f:
        py_compile.compile(f, doraise=True)
        print(f'OK: {f}')
"
```

**Quick gameplay simulation (no display):**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 -c "
import sys, os; sys.path.insert(0, '.')
os.environ['SDL_VIDEODRIVER']='dummy'; os.environ['SDL_AUDIODRIVER']='dummy'
import pygame; pygame.init(); pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
from core.fonts import init_fonts; from core.sound import init_sounds
screen = pygame.display.set_mode((800,600)); init_fonts(); init_sounds()
from core.particles import ParticleSystem; from core.shake import ScreenShake
from shared.player_state import SharedPlayerState
from modes.desert_velocity import DesertVelocityMode
p = ParticleSystem(); s = ScreenShake(); ss = SharedPlayerState(1,'normal')
m = DesertVelocityMode(p, s, ss); m.setup()
keys = pygame.key.get_pressed()
for i in range(300):
    r = m.update(keys); m.draw(screen)
print('300 frames OK'); pygame.quit()
"
```

### Review Tools (For Reviewers)

Reviewers should use these to validate fast:

```bash
# 1. Syntax check all files
python3 -m py_compile <file>

# 2. Run the game and play for 2 minutes
python3 neon_rush.py

# 3. Check import safety — no module-level captures of None globals
rg '^from core\.(sound|fonts) import' --type py | grep -v 'import SFX\|import music_loops\|import load_font\|import init_'

# 4. Check no external assets snuck in
fd -e png -e jpg -e wav -e ogg -e mp3 -e ttf -e otf

# 5. Check no bare except: pass
rg 'except.*:.*pass$' --type py

# 6. Verify boss contract (all 3 damage methods)
rg 'RAM_DAMAGE|ENVIRONMENTAL_DAMAGE|HeatBolt' bosses/

# 7. Run headless simulation of all 3 modes
# (use the quick simulation script above, swap mode classes)
```

---

## 7. DOCTRINE (The Rules)

### 7.1 Architecture

```
neon_rush.py          Main loop — mode-agnostic state machine
core/                 Engine (sound, particles, fonts, display, crash reporting)
shared/               Contracts (GameMode, Boss, SharedPlayerState, Transition)
modes/                Game modes (one file each, inherit GameMode)
bosses/               Bosses (one file each, inherit Boss)
sprites/              Sprites (one file per mode + shared vehicle.py)
backgrounds/          Backgrounds (one file per mode, procedural)
crash_logs/           Auto-generated crash reports
```

- Every mode inherits `GameMode` and implements `setup()`, `update(keys)`, `draw(screen)`, `cleanup()`
- Every boss inherits `Boss` and implements `_build_phases()`, `_create_surface()`, `_update_movement()`
- Main loop NEVER knows mode-specific logic — only calls the interface
- New modes follow the exact same file pattern

### 7.2 No External Assets

**Everything is procedural.** Non-negotiable.

- Sprites: `pygame.Surface` + `pygame.draw.*`
- Audio: `array.array` buffer → `pygame.mixer.Sound`
- Fonts: `pygame.font.SysFont("freesans"/"dejavusans", size)`
- Data: JSON only

DO NOT add `.png`, `.wav`, `.ogg`, `.mp3`, `.ttf`, or any binary files.

### 7.3 Import Safety (Critical)

**The #1 crash source.** Module-level `from X import Y` captures the value at import time. If `Y` is `None`/`{}` and gets reassigned by an init function, your import is stale forever.

**SAFE:**
```python
from core.sound import SFX              # OK — dict mutated in-place via .update()
from core.sound import music_loops      # OK — same
from core.fonts import load_font        # OK — function, doesn't change
import core.sound as _snd              # OK — then use _snd.music_channel
import core.fonts as _fonts            # OK — then use _fonts.FONT_POWERUP
def method(self):
    from core.fonts import FONT_HUD    # OK — deferred, runs after init
```

**UNSAFE (WILL CRASH):**
```python
from core.sound import music_channel   # BAD — captures None forever
from core.fonts import FONT_POWERUP   # BAD — captures None forever
```

### 7.4 Shared State Contract

`SharedPlayerState` carries between modes:
- `scores[]`, `coins[]`, `lives[]` — per player
- `total_distance`, `total_time`, `bosses_defeated`, `current_mode`
- Powerups RESET between modes. Lives, score, coins CARRY.
- `snapshot_from_players()` at mode end, `inject_into_players()` at mode start.

### 7.5 Boss Combat Contract

Every boss MUST have:

| Method | How | Damage | Constant |
|--------|-----|--------|----------|
| Ram | Player collides during vulnerability window | 25 HP | `RAM_DAMAGE` |
| Heat Bolt | Player fires projectile (E key, 40 heat) | 15 HP | `HeatBolt.damage` |
| Environmental | Boss hits level hazard | 50 HP | `ENVIRONMENTAL_DAMAGE` |

Plus: 3 phases, warning phase, vulnerability windows, weighted-random attacks, HP bar.

### 7.6 Self-Healing

- `crash_heal()` attempts targeted fixes (JSON repair, display driver)
- If fix works, game retries `main()` once
- If not, full crash report saved to `crash_logs/`
- Session tracker (`core/crash_report.py`) updated every frame
- NEVER use bare `except: pass`. NEVER silently swallow errors.

### 7.7 Difficulty

```
EASY:   5 lives, 0.6x obstacles, 0.7x spawn rate
NORMAL: 3 lives, 1.0x obstacles, 1.0x spawn rate
HARD:   2 lives, 1.5x obstacles, 1.4x spawn rate
```

Continuous scaling: `difficulty_scale = 1.0 + game_distance * 0.15`

### 7.8 Display

- Internal: 800x600 always
- Render to offscreen surface, then scale to display
- Screen shake = blit offset
- F11 = fullscreen, F2 = 1x/2x scale

### 7.9 Controls

```
P1 Solo:   WASD + Arrows | SPACE/LSHIFT/RSHIFT = Boost | E/RETURN = Fire
P1 (2P):   WASD | LSHIFT = Boost | E = Fire
P2 (2P):   Arrows | RSHIFT = Boost | RETURN = Fire
Global:    F11 = Fullscreen | F2 = Scale | P = Pause | ESC = Back
```

### 7.10 Crash Reports

Every crash auto-saves to `crash_logs/` with: build number, git hash, timestamps, session duration, game state (mode, score, distance, boss), player snapshots, event log, human-readable error, full traceback. Press C on crash screen to copy.

---

## 8. FILE REFERENCE

| What | Where | Key Classes |
|------|-------|-------------|
| Main loop | `neon_rush.py` | `main()`, state machine |
| Constants | `core/constants.py` | Colors, states, difficulty, modes |
| Sound | `core/sound.py` | `SFX` dict, `init_sounds()`, music generators |
| Fonts | `core/fonts.py` | `init_fonts()`, `load_font()` |
| Particles | `core/particles.py` | `Particle`, `ParticleSystem` |
| Display | `core/display.py` | `create_display()`, `toggle_fullscreen()` |
| Crash reports | `core/crash_report.py` | `session`, `generate_crash_report()` |
| Self-healing | `core/healing.py` | `crash_heal()`, `preflight_heal()` |
| HUD | `core/hud.py` | `draw_hud()`, `draw_panel()`, `FloatingText` |
| UI | `core/ui.py` | `ComboTracker`, `MilestoneTracker`, `HighScoreEntry` |
| Highscores | `core/highscores.py` | `load_highscores()`, `is_highscore()` |
| Game mode base | `shared/game_mode.py` | `GameMode` |
| Boss base | `shared/boss_base.py` | `Boss`, `BossPhase`, `AttackPattern`, `HeatBolt` |
| Shared state | `shared/player_state.py` | `SharedPlayerState` |
| Transitions | `shared/transition.py` | `TransitionEffect` |
| Player vehicle | `sprites/vehicle.py` | `Player`, `make_vehicle_surface()` |
| Desert sprites | `sprites/desert_sprites.py` | `Obstacle`, `Coin`, `PowerUp`, `SolarFlare` |
| Excitebike sprites | `sprites/excitebike_sprites.py` | `ExcitebikePlayer`, `Ramp`, `Barrier` |
| Micro sprites | `sprites/micromachines_sprites.py` | `MicroPlayer`, `OilSlickHazard`, `TinyCar` |
| Desert mode | `modes/desert_velocity.py` | `DesertVelocityMode` |
| Excitebike mode | `modes/excitebike.py` | `ExcitebikeMode` |
| Micro mode | `modes/micromachines.py` | `MicroMachinesMode` |
| Desert boss | `bosses/desert_boss.py` | `DesertBoss` + 5 attack patterns |
| Excitebike boss | `bosses/excitebike_boss.py` | `ExcitebikeBoss` + 4 attack patterns |
| Micro boss | `bosses/micromachines_boss.py` | `MicroMachinesBoss` + 4 attack patterns |
| Desert bg | `backgrounds/desert_bg.py` | `Background` |
| Excitebike bg | `backgrounds/excitebike_bg.py` | `ExcitebikeBg` |
| Micro bg | `backgrounds/micromachines_bg.py` | `MicroMachinesBG` |

---

## 9. TOKEN-SAVING TECHNIQUES

When context is limited, use these to stay efficient:

**For Builders:**
- Read only the files you're changing + the base class you're inheriting from
- Don't re-read constants.py if you already know the values
- Use `rg` to find specific patterns instead of reading entire files
- Reference this doc for architecture — don't re-explore the codebase
- Keep your check-in block short — it's a declaration, not an essay

**For Reviewers:**
- Use the review tool commands in §6 — they're optimized for fast validation
- Run the syntax check first — catches 80% of issues in 1 command
- The import safety grep catches the most common bug pattern
- `fd -e png -e wav` is instant — catches asset violations immediately
- If gameplay test passes 2 minutes with no crash, it's likely solid

**For Everyone:**
- This doc IS the context. Don't waste tokens re-discovering what's documented here
- If you need a file's structure, check §8 first
- If you need a rule, check §7 first
- Grep > Read for finding specific code
- Headless tests save tokens vs. describing "I would test by..."

---

## 10. CREDITS

Every contributor gets listed. Builder and reviewer both.

### Hall of Contributors

| Name | Model | Role | Contribution | Date |
|------|-------|------|-------------|------|
| **Architect** | claude-opus-4-6 | **Project Lead** | Full codebase extraction, 3 modes, boss system, crash reporting, doctrine, build board | 2026-02-27 |
| *(parallel assist)* | claude-opus-4 | Builder | Excitebike boss, Micro Machines boss, Micro Machines BG | 2026-02-27 |
| **Rathin** | Human | **Owner** | Project vision, architecture plan, playtesting, final authority | 2026-02-27 |

*Pick a name when you check in. It goes here when your work ships.*

---

## 11. ALIGNMENT CONFLICTS — How to Handle

If your task conflicts with ANY doctrine rule:

1. **State it:** `ALIGNMENT CONFLICT: [what rule] — [what your task needs]`
2. **Explain why:** What specifically breaks
3. **Propose alternative:** How to achieve the goal within doctrine
4. **Ask the team:** "Should I proceed with the alternative, or amend the doctrine?"

**Never silently break a rule.** The team would rather help you find an aligned path than debug a doctrine violation later.

---

## CHANGELOG

| Date | Who | What Changed |
|------|-----|-------------|
| 2026-02-27 | Lead Architect | Initial doctrine created |
| 2026-02-27 | Lead Architect | Added build board, tools, token-saving, credits |
| 2026-02-27 | Architect | Registered as project lead. Persistent memory initialized. |
| 2026-02-27 | Architect | Added Suggestion Box (§1.5) — ideas + chef's kiss system |

---

*This is a living document. Update it when the project evolves.*
