# NEON RUSH — Game Design Document

**Engine:** Python 3.13 + Pygame 2.6.1 | **Simulation:** 36 Hz fixed timestep | **Render:** up to 144 FPS
**Screen:** 800x600 | **Codebase:** ~17,000 lines, 51 files | **Assets:** 100% procedural (no external files)

---

## Table of Contents

1. [Game Overview](#1-game-overview)
2. [Level Structure](#2-level-structure)
3. [The Three Modes](#3-the-three-modes)
4. [Task System (Boss Rush)](#4-task-system-boss-rush)
5. [Boss Fights](#5-boss-fights)
6. [Powerup System](#6-powerup-system)
7. [Scoring & Combos](#7-scoring--combos)
8. [Difficulty Settings](#8-difficulty-settings)
9. [Tier Visual Progression](#9-tier-visual-progression)
10. [Controls](#10-controls)
11. [Architecture](#11-architecture)

---

## 1. Game Overview

NEON RUSH is a **boss rush racing game** with three distinct perspectives. You play through three modes back-to-back, each ending with a boss fight. Beat all three bosses to advance to the next tier with evolved visuals and harder challenges.

**Design philosophy:** "Challenging but fair" — bosses require pattern learning, not luck. Bosses are designed to kill you the first time. Learn the patterns, beat them the second.

**Core loop:**
```
Start Level -> Complete 2 Tasks -> Boss Appears -> Defeat Boss -> Next Mode
```

**Mode cycle:**
```
Desert Velocity (vertical) -> Excitebike (side-scroll) -> Micro Machines (top-down)
```

Beat all 3 bosses = one full cycle. The game then evolves to the next tier and you do it again with harder bosses, tighter windows, and upgraded visuals.

---

## 2. Level Structure

### Level Labeling: `{Tier}-{Mode}`

| Level | Mode | Tier | Visual Era |
|-------|------|------|------------|
| **1-1** | Desert Velocity | 1 | NES |
| **1-2** | Excitebike | 1 | NES |
| **1-3** | Micro Machines | 1 | NES |
| **2-1** | Desert Velocity | 2 | SNES |
| **2-2** | Excitebike | 2 | SNES |
| **2-3** | Micro Machines | 2 | SNES |
| **3-1** | Desert Velocity | 3 | N64+ |
| **3-2** | Excitebike | 3 | N64+ |
| **3-3** | Micro Machines | 3 | N64+ |

- **First digit** = Evolution Tier (world). Visuals, boss HP, and attack intensity scale up.
- **Second digit** = Mode within that tier. 1=Desert, 2=Excitebike, 3=Micro Machines.

### Persistent State Between Modes

Score, coins, and lives carry over between modes via `SharedPlayerState`. You keep what you earn. At least 1 life is guaranteed when entering a new mode.

---

## 3. The Three Modes

### Mode 1: Desert Velocity (Vertical Scroller)

**Perspective:** Top-down, scrolling upward. Tier 2+ adds pseudo-3D road geometry (curves, hills).

| Stat | Value |
|------|-------|
| Player speed range | 0-16 (20 with surge) |
| Lateral move | 6.5 px/frame |
| Leap dodge | Double-tap left/right = instant 90px dash |
| Heat bolt direction | UP |
| Obstacles | Rocks, debris — spawn interval accelerates with distance |
| Unique mechanic | **SolarFlare** — environmental hazard that damages the boss for 50 HP |
| Boss defeat reward | +2000 pts |

**Spawning (Normal difficulty):**
- Obstacles: ~45 frame intervals (accelerates with distance: `difficulty_scale = 1.0 + distance * 0.15`)
- Coins: every 40 frames
- Powerups: every 300 frames (~8.3 seconds)
- SolarFlares: every 600-1200 frames

### Mode 2: Excitebike (Side-Scroller)

**Perspective:** Side-scrolling with 3 vertical lanes.

| Stat | Value |
|------|-------|
| Player speed range | 1.3-16 |
| Lane system | 3 lanes, smooth transition (~13 frames to switch) |
| Heat bolt direction | RIGHT |
| Obstacles | Barriers (60%), MudPatches (40%) |
| Unique mechanics | **Ramp launch** (+150 pts), **MudPatch** (speed x0.95), **SideRacers** |
| Boss defeat reward | +3000 pts |

**Spawning (Normal difficulty):**
- Obstacles: ~60 frame intervals (accelerates: `difficulty_scale = 1.0 + distance * 0.12`)
- Ramps: every 300 frames
- Coins: every 35 frames
- Powerups: every 250 frames

**Key mechanic:** Launching off ramps makes you airborne — you skip barrier collisions AND can deal environmental damage to the boss.

### Mode 3: Micro Machines (Top-Down Free-Roam)

**Perspective:** True top-down with free 2D movement and steering.

| Stat | Value |
|------|-------|
| Player speed range | -2.6 (reverse) to 8 |
| Turn speed | 0.065 rad/frame |
| Friction | speed x0.98/frame |
| Heat bolt direction | UP |
| Obstacles | Oil slicks, tiny cars |
| Unique mechanics | **Drift** (turning at speed>2 = extra heat), **Oil slick** (angular deflection) |
| Boss defeat reward | +5000 pts |

**Spawning (Normal difficulty):**
- Obstacles: ~70 frame intervals (accelerates: `difficulty_scale = 1.0 + distance * 0.1`)
- Oil slicks: every 200 frames
- Tiny cars: every 120 frames
- Coins: every 30 frames
- Powerups: every 200 frames

---

## 4. Task System (Boss Rush)

Each level assigns **2 random tasks** from a pool of 12. Complete both tasks to trigger the boss fight. Tasks are scaled by mode pace, difficulty, and evolution tier.

### Task Pool

| Task | Display Name | Tier 1 / 2 / 3 Targets | Type | Mode Filter |
|------|-------------|------------------------|------|-------------|
| coin_rush | COIN RUSH | 8 / 12 / 18 coins | Event | All |
| score_target | SCORE TARGET | 800 / 1500 / 2500 pts | Tick | All |
| distance_run | DISTANCE RUN | 0.5 / 0.8 / 1.2 km | Tick | All |
| heat_kills | HEAT KILLS | 5 / 8 / 12 kills | Event | All |
| combo_chain | COMBO CHAIN | x2 / x3 / x4 combo | Tick | All |
| powerup_grab | POWER SURGE | 2 / 3 / 4 pickups | Event | All |
| speed_demon | SPEED DEMON | 3s at speed 6/8/10 | Tick | All |
| survivor | SURVIVOR | 10 / 15 / 20s no-hit | Tick | All |
| near_miss | NEAR MISS | 6 / 10 / 15 dodges | Event | All |
| coin_combo | COIN COMBO | x4 / x6 / x8 chain | Event | All |
| ramp_master | RAMP MASTER | 2 / 3 / 4 launches | Event | Excitebike only |
| drift_king | DRIFT KING | 60 / 100 / 150 frames | Tick | Micro Machines only |

### Target Scaling

Targets are modified by two multipliers:

- **Mode pace:** Desert x0.7, Excitebike x1.0, Micro Machines x1.3
- **Difficulty:** Easy x0.7, Normal x1.0, Hard x1.4

Example: COIN RUSH tier 1 in Desert on Normal = `8 * 0.7 * 1.0 = 6 coins`
Example: HEAT KILLS tier 2 in Micro on Hard = `8 * 1.3 * 1.4 = 15 kills`

### Assignment Rules

- 2 tasks per level, no duplicates
- Max 1 mode-specific task per level (40% chance if available)
- Pool filtered by current mode (ramp_master only in Excitebike, drift_king only in Micro)

### Boss Trigger Flow

```
Tasks assigned at level start
  -> Player completes Task 1 (progress bar fills, flash + SFX)
  -> Player completes Task 2 (progress bar fills, flash + SFX)
  -> "BOSS INCOMING!" flashes for 2 seconds + boss_warning SFX
  -> Boss spawns
```

The HUD shows task progress bars at bottom-center with the level label (e.g., "LEVEL 1-1").

**--boss-rush CLI flag:** Auto-completes all tasks immediately, boss spawns in ~5 seconds. For testing.

---

## 5. Boss Fights

All bosses follow a **3-phase contract**: full HP -> 66% -> 33% -> dead. Each phase adds new attacks and tightens vulnerability windows.

### Universal Boss Mechanics

- **3 damage methods:** Ram (collide during vulnerability), Heat bolt (projectile), Environmental (mode-specific)
- **Vulnerability windows:** Boss becomes vulnerable after completing an attack pattern. Window shrinks each phase.
- **Invulnerability after hit:** 30 frames between damage instances
- **HP scaling:** `Base HP * difficulty_mult * (1.0 + (tier - 1) * 0.3)`
- **Warning:** 3-second warning before boss becomes active
- **Death animation:** 120 frames of flashing before mode transition
- **Auto-fire during boss:** Heat bolts fire every 12 frames at no heat cost — player focuses on dodging

### Desert Boss — Sandstone Golem

**Base HP:** 300 | **Size:** 100x90px | **Movement:** Horizontal drift, bouncing between road edges (+0.5 speed per phase)

| Phase | HP Range | Vuln Window | Key Attacks |
|-------|----------|-------------|-------------|
| 1 | 100%-66% | ~1.5s (54f) | Sandstorm columns, Boulder barrage, Dive attack |
| 2 | 66%-33% | ~1.1s (40f) | + Quicksand vortex (pulls players in), Homing boulders, Heat wave |
| 3 | 33%-0% | ~0.83s (30f) | + Solar beam, Sandstorm sweep with gap, Counter-sweeps |

**Attack details:**
- **Sandstorm:** 3+ columns of damaging wind; Phase 2+ columns drift sideways
- **Boulder Barrage:** Falling rocks, spawn rate increases per phase (25f -> 17f -> 9f intervals); 30% homing
- **Dive:** Boss dives at player (speed 8/10/12 per phase); creates 160px-wide shockwave on landing
- **Quicksand Vortex:** 2-3 vortices pull players toward core (120px radius, 0.8 strength); Phase 2+ only
- **Solar Beam:** Wide beam sweeps screen (width 50/60/70px per phase); Phase 3 only
- **Sandstorm Sweep:** Wall with gap (80px gap in 60px-wide wall); Phase 3 counter-sweeps

**Environmental damage:** SolarFlares hit boss for 50 HP each

**Effective HP by tier (Normal):** T1: 300 | T2: 390 | T3: 480

### Excitebike Boss — Armored Motorcycle

**Base HP:** 300 | **Size:** 120x80px | **Movement:** Sinusoidal bob; drifts lower when vulnerable (easier to ram)

| Phase | HP Range | Vuln Window | Key Attacks |
|-------|----------|-------------|-------------|
| 1 | 100%-66% | ~1.4s (50f) | Shockwave, Missile barrage (4 missiles) |
| 2 | 66%-33% | ~1.0s (36f) | + Charge attack, Ramp barrage, 5 missiles |
| 3 | 33%-0% | ~0.7s (25f) | + Exhaust trail, Combo attacks, Double charge, 6 missiles |

**Attack details:**
- **Shockwave:** Expanding wave from boss (speed 5/7/9 per phase); Phase 3: double wave
- **Missiles:** Homing missiles (turn_rate 0.10+phase*0.02, speed 4.0+, 180f life); count increases per phase
- **Charge:** Boss charges horizontally at 12/15/18 speed; Phase 3: double charge with 30f pause
- **Ramp Barrage:** 3-5 ramps fly at player; airborne player = env damage to boss
- **Exhaust Trail:** Boss leaves damaging flame segments (30x16px, 120f life); Phase 3 only

**Environmental damage:** Boss colliding with ramps = 50 HP

### Micro Machines Boss — Monster Truck

**Base HP:** 350 (highest) | **Movement:** Patrols screen perimeter in rounded rectangle; slows to 50% when vulnerable

| Phase | HP Range | Vuln Window | Key Attacks |
|-------|----------|-------------|-------------|
| 1 | 100%-66% | ~1.4s (50f) | Oil slick drops, Shockwave rings |
| 2 | 66%-33% | ~1.0s (36f) | + Homing missiles (3-4), Oil self-damage mechanic |
| 3 | 33%-0% | ~0.7s (25f) | + Tire barrage (bouncing), DriveBy chase, 4-5 missiles |

**Attack details:**
- **Oil Slick Drop:** 3-6 slicks placed on ground; Phase 2+: boss places slicks on own patrol path (self-damage!)
- **Shockwave Ring:** Expanding rings from boss center; Phase 3: double-ring
- **Tire Barrage:** Bouncing projectile tires that ricochet off screen edges; Phase 3 only
- **DriveBy:** Boss breaks patrol to chase nearest player at high speed; Phase 3 only

**Environmental damage:** Boss drives over its own oil slicks = 50 HP

**Effective HP by tier (Normal):** T1: 350 | T2: 455 | T3: 560

---

## 6. Powerup System

All powerups award **+100 pts** on pickup. Random drops from `POWERUP_ALL` pool (9 types).

**Magnetism:** In tiers 1-2 (levels 1-1 through 2-3), all powerups auto-attract toward the nearest player within 250px at 4px/frame. Tier 3 has **no magnetism** — harder, faster gameplay.

### Powerup Catalog

| Powerup | Label | Color | Duration | Effect |
|---------|-------|-------|----------|--------|
| **SHIELD** | S | Blue | 16.7s (600f) | Absorbs 1 hit without life loss; 30f post-shield invincibility |
| **MAGNET** | M | Purple | 13.3s (480f) | Attracts nearby collectibles toward player |
| **SLOWMO** | ~ | Green | 8.3s (300f) | Everything at 50% speed (physics + scroll) |
| **NUKE** | ! | Orange | Instant | Destroys all on-screen obstacles; screen flash + shake |
| **PHASE** | G | Cyan | 10s (360f) | Ghost mode — pass through obstacles, barriers, boss hazards |
| **SURGE** | N | Pink | 5s (180f) | Max speed (15 or 8 in Micro) + invincible for duration |
| **MULTISHOT** | W | Gold | 10s (360f) | 3-bolt fan spread at +/-15 degrees instead of single bolt |
| **ROCKETS** | R | Red | 13.3s (480f) | Auto-fire homing rockets every 60 frames toward boss/enemies |
| **ORBIT8** | 8 | Purple | 16.7s (600f) | 8 orbs orbit in figure-8 lemniscate; damage enemies + absorb boss attacks |

### Nuke Targets by Mode
- Desert: clears all obstacles
- Excitebike: clears barriers + mud patches
- Micro Machines: clears oil slicks + tiny cars

### Spawn Rates

| Difficulty | Desert | Excitebike | Micro Machines |
|-----------|--------|------------|----------------|
| Easy | ~5.6s (200f) | ~6.9s (250f) | ~5.6s (200f) |
| Normal | ~8.3s (300f) | ~6.9s (250f) | ~5.6s (200f) |
| Hard | ~12.5s (450f) | ~6.9s (250f) | ~5.6s (200f) |

### Powerup Visuals

- Rainbow shimmer ring (rotating hue cycle)
- Sparkle rays (6 rays tier 2+, 4 rays tier 1)
- Bright center highlight glow
- Particle trail every 4 frames
- Tier 1-2: Magnetism pull effect (visible attraction toward player)

---

## 7. Scoring & Combos

### Score Sources

| Source | Points |
|--------|--------|
| Coin (base) | 50 x combo multiplier |
| Powerup pickup | 100 |
| Obstacle destroyed (heat bolt) | 30 |
| Obstacle destroyed (nuke, per sprite) | 50 |
| Ramp launch (Excitebike) | 150 |
| SolarFlare collected (Desert) | 200 |
| Boss defeated — Desert | 2000 |
| Boss defeated — Excitebike | 3000 |
| Boss defeated — Micro Machines | 5000 |
| Passive speed — Desert/Excitebike | `int(speed * 0.5)` per sim tick |
| Passive speed — Micro Machines | `int(abs(speed) * 0.3)` per sim tick |

### Combo System

Consecutive coin pickups within **2.5 seconds** build a combo chain:

| Combo Count | Multiplier | Color |
|-------------|------------|-------|
| 1-2 | x1 | (no display) |
| 3-4 | x2 | Yellow |
| 5-9 | x3 | Orange |
| 10+ | x4 | Magenta |

Animated floating text at player position, fades over 90 frames with pulsing scale. Miss the 2.5s window and the chain resets.

---

## 8. Difficulty Settings

| Parameter | Easy | Normal | Hard |
|-----------|------|--------|------|
| Starting lives | 5 | 3 | 2 |
| Obstacle density | 0.6x | 1.0x | 1.5x |
| Boss HP | 0.75x | 1.0x | 1.4x |
| Boss vulnerability windows | 1.4x wider | 1.0x | 0.7x tighter |
| Coin frequency | Every 30f | Every 40f | Every 50f |
| Powerup frequency | Every 200f | Every 300f | Every 450f |
| Obstacle spawn during boss | 15% rate | 30% rate | 50% rate |
| Task target scaling | 0.7x | 1.0x | 1.4x |

### Evolution Tier Scaling

| Tier | Boss HP Multiplier | Example: Desert Boss (Normal) | Example: Micro Boss (Normal) |
|------|-------------------|-------------------------------|------------------------------|
| 1 | 1.0x | 300 HP | 350 HP |
| 2 | 1.3x | 390 HP | 455 HP |
| 3 | 1.6x | 480 HP | 560 HP |

Boss attack speed also increases per tier, vulnerability windows tighten, and new attack combos may appear.

---

## 9. Tier Visual Progression

The game's visuals evolve dramatically across tiers, inspired by real console generations:

### Tier 1 — NES Era (Levels 1-1, 1-2, 1-3)

- **Palette:** Limited, high-contrast neon on black
- **Sprites:** Flat, blocky, single-color with simple outlines
- **Effects:** Basic — single-frame flashes, simple rectangles for projectiles
- **HUD:** Flat panels with solid color fills, no gradients
- **Background:** Solid color fills, simple dashed road lines
- **Particles:** Minimal — basic square particles, low count
- **Powerup glow:** 4 sparkle rays, simple shimmer
- **Auto-magnetism:** YES — powerups attract toward player (250px range)

### Tier 2 — SNES Era (Levels 2-1, 2-2, 2-3)

- **Palette:** Richer, more colors, gradient-capable
- **Sprites:** Multi-color with shading, more detail
- **Effects:** Layered glows, alpha blending, smooth animations
- **HUD:** Gradient panels, neon borders with outer glow
- **Background:** Pseudo-3D road geometry (curves, hills in Desert), parallax layers
- **Particles:** More particles, varied sizes, glow effects
- **Powerup glow:** 6 sparkle rays, rainbow shimmer ring, particle trails
- **Road:** Curve physics, center-pull drift mechanic (Desert V2)
- **Auto-magnetism:** YES — powerups attract toward player (250px range)

### Tier 3 — N64+ Era (Levels 3-1, 3-2, 3-3)

- **Palette:** Full spectrum, smooth gradients everywhere
- **Sprites:** Detailed with multiple shading passes, pseudo-3D depth
- **Effects:** Multi-layer compositing, screen-space effects, bloom-like glows
- **HUD:** Animated elements, pulsing indicators, dynamic color shifts
- **Background:** Full perspective rendering, atmospheric haze, multi-layer scrolling
- **Particles:** High-density particle systems, trailing effects, persistent particles
- **Powerup glow:** Maximum visual flair
- **Boss attacks:** More visually elaborate telegraph animations
- **Auto-magnetism:** NO — no powerup attraction (harder, faster gameplay)
- **Overall:** The "wow" tier — everything should look noticeably better than tier 2

### Planned Tier 3 Themes

| Mode | Tier 3 Theme |
|------|-------------|
| Desert V3 | Crimson sandstorm, blood-red sky, lightning |
| Excitebike V3 | Night mode, neon signs, rain/puddles |
| Micro Machines V3 | Holographic grid, glitch effects, digital rain |

---

## 10. Controls

### Universal Controls

| Key | Action |
|-----|--------|
| UP / W | Accelerate |
| DOWN / S | Brake / Reverse (Micro) |
| LEFT / A | Steer left |
| RIGHT / D | Steer right |
| SPACE | Fire heat bolt (manual, costs 40 heat, 30f cooldown) |
| ESC / P | Pause |

### Mode-Specific

| Mode | Special |
|------|---------|
| Desert | Double-tap left/right = Leap dodge (instant 90px dash, 30f cooldown) |
| Excitebike | Up/Down = Lane change (3 lanes, smooth transition) |
| Micro Machines | Left/Right = Continuous steering rotation |

### Heat System (All Modes)

- **Builds** by accelerating (+1.0-1.5/frame depending on mode)
- **Decays** passively (-0.2 to -0.4/frame)
- **Overflow at 100** = Ghost mode (180 frames of invincibility + visual effect)
- **Boost** at heat>50 = consume all heat for a speed burst (+4-5 speed)
- During boss fights, heat bolts auto-fire every 12 frames at no heat cost

---

## 11. Architecture

```
neon_rush.py              Main loop, state machine, mode switching
core/
  constants.py            All game constants, colors, difficulty tables
  hud.py                  HUD rendering (score, lives, powerups, level label)
  tasks.py                Task system — 12 task types, TaskManager, HUD bars
  sound.py                38 procedural SFX + 6 music tracks (all synthesized)
  fonts.py                Font loading
  ui.py                   ComboTracker, floating text
  healing.py              Crash recovery (auto-retry with degraded state)
  crash_report.py         Auto crash reports to crash_logs/
shared/
  game_mode.py            Base class for all modes (boss, asteroid, weapon helpers)
  player_state.py         Persistent state across modes (SharedPlayerState)
  powerup_handler.py      Powerup application logic (9 types)
  projectiles.py          MultishotBolt, HomingRocket, OrbitOrb
  boss_base.py            Boss contract base class (3 phases, vulnerability, attacks)
modes/
  desert_velocity.py      Mode 1 — vertical scroller
  excitebike.py           Mode 2 — side-scroller with lanes
  micromachines.py        Mode 3 — top-down free-roam
bosses/
  desert_boss.py          Sandstone Golem — 7 attack types
  excitebike_boss.py      Armored Motorcycle — 6 attack types
  micromachines_boss.py   Monster Truck — 6 attack types
sprites/
  vehicle.py              Desert player vehicle
  excitebike_sprites.py   Excitebike player + barriers + ramps + mud
  micromachines_sprites.py Micro player + oil slicks + tiny cars
  desert_sprites.py       Desert obstacles + coins + powerups
```

### CLI Flags

```bash
python3 neon_rush.py                  # Normal start
python3 neon_rush.py --god            # Invincible mode
python3 neon_rush.py --boss-rush      # Boss spawns in ~5 seconds (skip tasks)
python3 neon_rush.py -m excitebike    # Start at Excitebike
python3 neon_rush.py -t 2             # Start at tier 2
python3 neon_rush.py -m micro -t 3    # Micro Machines tier 3
```

### Key Design Patterns

- **Fixed timestep:** 36 Hz simulation decoupled from render (max 8 sim steps per frame to prevent spiral-of-death)
- **GameMode base class:** All 3 modes inherit shared boss/asteroid/weapon helpers
- **Import safety:** Never `from X import REASSIGNED_VALUE` at module level (stale None capture bug)
- **Atomic saves:** tempfile -> fsync -> os.replace for highscores
- **Crash recovery:** `core/healing.py` wraps main() in retry loop with auto crash reports
- **Procedural everything:** All sprites, effects, music, and SFX generated via code — zero external assets
