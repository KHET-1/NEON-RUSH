# NEON RUSH — Project Instructions

## MANDATORY: Read These First

1. **[AI_CHECKIN.md](AI_CHECKIN.md)** — Project doctrine, check-in protocol, tools, rules
2. **[BUILD_BOARD.md](BUILD_BOARD.md)** — Task pipeline, what needs doing, review queue

**You MUST check in (§1 of AI_CHECKIN.md) before writing ANY code.**

## Quick Context

NEON RUSH is a three-perspective Pygame racing game:
- Desert Velocity (vertical) → Excitebike (side-scroll) → Micro Machines (top-down)
- Beat a boss to transition to the next mode. Beat all 3 → Victory.
- Procedural everything (no asset files). Self-healing crash recovery. 1P + 2P.

## Launch

```bash
cd ~/NEONRUSH && source .venv/bin/activate && python3 neon_rush.py
```

## The Pipeline

```
BACKLOG → WIP → REVIEW → COMPLETE → DIAMOND
```

Find a task in BUILD_BOARD.md. Claim it. Do it. Get it reviewed. Next.

## Critical Rules (full details in AI_CHECKIN.md §7)

1. **Check in first** — output the check-in block before coding
2. **No external assets** — synthesize everything procedurally
3. **Import safety** — never `from module import REASSIGNED_VALUE` at module level
4. **Update BUILD_BOARD.md** — when you start, finish, or review work
5. **Boss contract** — 3 damage methods, 3 phases, vulnerability windows
6. **GameMode pattern** — all modes inherit `shared/game_mode.py`
7. **Crash reports** — update `session.update()` when adding new state
