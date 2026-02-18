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
| Space | Heat Sync boost (requires 50%+ heat) |

**Heat Sync:** Aggressive driving builds heat → Space at 50%+ for boost. Over 100% = **Ghost Mode** (5 sec, invulnerable).

**Solar Flares:** Yellow zones spawn at bottom ~15–30s. Drive into one → massive vertical launch + 5s speed boost.

**Obstacles:** Yellow squares from above. Hit → crash (speed/heat reset).

## v4 Changelog

- **Particle system:** Exhaust, ghost trails, crash debris, sand, flare fountains
- **Vertical physics:** Gravity, flare launches (vel_y = -22)
- **Solar flares:** Ground zones with fountain + radial burst particles
- **Flare boost:** 5s sustained high speed after flare hit
