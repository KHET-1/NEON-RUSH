# NEON RUSH: Desert Velocity

Futuristic Phoenix desert racing demo — Heat Sync, obstacles, solar flares, particle physics.

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python neon_rush_demo.py
```

## Controls

| Key | Action |
|-----|--------|
| ↑ | Accelerate (builds heat) |
| ↓ | Brake |
| ←→ | Steer |
| Double-tap ← or → | Quick leap (dodge obstacles) |
| Space | Heat Sync boost (requires 50%+ heat) |

**Heat Sync:** Aggressive driving builds heat → Space at 50%+ for boost. Over 100% = **Ghost Mode** (5 sec, invulnerable).

**Solar Flares:** Yellow zones spawn at bottom ~15–30s. Drive into one → massive vertical launch + 5s speed boost.

**Obstacles:** Yellow squares from above. Hit → crash (speed/heat reset).

## If It Crashes

The game shows a crash dialog with a **FIX** hint. Common fixes:

| Error | Fix |
|-------|-----|
| **pygame.error** | Display/audio failed. Close other fullscreen apps, update GPU drivers, or run `SDL_VIDEODRIVER=x11 .venv/bin/python neon_rush_demo.py` |
| **ModuleNotFoundError** | `pip install -r requirements.txt` |
| **FileNotFoundError** | Run from project root (`/path/to/NEONRUSH`) |
| **PermissionError** | Fix write access for `highscores.json` (or delete it) |
| **json.JSONDecodeError** | Corrupt `highscores.json` — delete the file |
| **MemoryError** | Close other apps or edit `PARTICLE_CAP` (line ~40) to 400 |

If no window appears, check the console — the same report is printed there.

**Self-healing:** Corrupt `highscores.json` is auto-reset to `[]`. After a display crash, `SDL_VIDEODRIVER=x11` is stored; next run applies it before init. See `.neon_rush_evolve.json` for heal history.

## v4 Changelog

- **Particle system:** Exhaust, ghost trails, crash debris, sand, flare fountains
- **Vertical physics:** Gravity, flare launches (vel_y = -22)
- **Solar flares:** Ground zones with fountain + radial burst particles
- **Flare boost:** 5s sustained high speed after flare hit
