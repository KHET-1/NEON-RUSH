import os
import sys
import json
import traceback
import pygame

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVOLVE_FILE = os.path.join(_BASE_DIR, ".neon_rush_evolve.json")
HIGHSCORE_FILE = os.path.join(_BASE_DIR, "highscores.json")


def evolve_load():
    try:
        with open(EVOLVE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"heals": {}, "last_run": None}


def evolve_record(heal_id, success):
    data = evolve_load()
    data["heals"] = data.get("heals", {})
    data["heals"][heal_id] = data["heals"].get(heal_id, {"ok": 0, "fail": 0})
    data["heals"][heal_id]["ok" if success else "fail"] += 1
    data["last_run"] = __import__("time").time()
    try:
        with open(EVOLVE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def heal_highscores():
    try:
        with open(HIGHSCORE_FILE, "r") as f:
            data = json.load(f)
        if not isinstance(data, list) or any(
            not isinstance(s, dict) or "name" not in s or "score" not in s for s in data
        ):
            raise ValueError("Invalid structure")
        return True, "ok"
    except (FileNotFoundError, json.JSONDecodeError, ValueError, KeyError):
        try:
            with open(HIGHSCORE_FILE, "w") as f:
                json.dump([], f)
            evolve_record("highscores_reset", True)
            return True, "reset"
        except Exception:
            return False, "write_failed"


def heal_pygame_display():
    if not os.environ.get("SDL_VIDEODRIVER"):
        os.environ["SDL_VIDEODRIVER"] = "x11"
        return True, "x11_set"
    return True, "already_set"


def preflight_heal():
    actions = []
    ok, msg = heal_highscores()
    if msg == "reset":
        actions.append("highscores reset (was corrupt)")
    return actions


def crash_heal(exc_type, exc_value, exc_tb):
    actions = []
    err_text = str(exc_value) if exc_value else ""
    full = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

    if "json" in err_text.lower() or "JSONDecodeError" in full or "highscores" in full:
        ok, msg = heal_highscores()
        if ok and msg == "reset":
            actions.append("highscores repaired")
            evolve_record("crash_highscores", True)
            return True, actions

    if "pygame.error" in str(exc_type) or "display" in err_text.lower() or "video" in err_text.lower():
        ok, msg = heal_pygame_display()
        if ok:
            actions.append("SDL_VIDEODRIVER=x11 set for next run — restart the game")
            evolve_record("crash_display", True)
        return False, actions

    return False, actions


def show_crash_screen(exc_type, exc_value, exc_tb, heal_actions=None):
    heal_actions = heal_actions or []
    lines = traceback.format_exception(exc_type, exc_value, exc_tb)
    err_text = "".join(lines).strip()
    err_short = f"{exc_type.__name__}: {exc_value}" if exc_value else str(exc_type)

    FIX_HINTS = {
        "pygame.error": "Pygame display/audio failed. Try: close other fullscreen apps, update GPU drivers, or run with SDL_VIDEODRIVER=x11",
        "ModuleNotFoundError": "Missing dependency. Run: pip install -r requirements.txt",
        "FileNotFoundError": "Missing file or asset. Check the file path and that you're running from the project root.",
        "PermissionError": "No write access. Run from a directory you own, or fix highscores.json permissions.",
        "json.JSONDecodeError": "Corrupt highscores.json. Delete or fix the file.",
        "MemoryError": "Out of memory. Close other apps or reduce PARTICLE_CAP in the code.",
        "KeyError": "Missing key in config or data. Check your game data files.",
        "TypeError": "Wrong data type. Often from bad config or save file.",
        "AttributeError": "Object missing attribute. Possible version mismatch or corrupt state.",
        "IndexError": "List/array index out of range. May indicate empty/corrupt data.",
    }
    hint = "Check the traceback below and fix the reported line."
    for key, msg in FIX_HINTS.items():
        if key in err_short or key in err_text:
            hint = msg
            break
    if heal_actions:
        hint = "We tried: " + "; ".join(heal_actions) + ". " + hint

    try:
        try:
            pygame.init()
        except Exception:
            pass
        win = pygame.display.set_mode((700, 420))
        pygame.display.set_caption("NEON RUSH - Error")
        font = pygame.font.SysFont("freesans", 16)
        font_b = pygame.font.SysFont("freesans", 18, bold=True)

        running = True
        line_h = 18
        while running:
            for e in pygame.event.get():
                if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                    running = False

            win.fill((30, 15, 20))
            pygame.draw.rect(win, (80, 30, 40), (0, 0, 700, 80))
            pygame.draw.line(win, (255, 80, 100), (0, 80), (700, 80), 2)

            title = font_b.render("NEON RUSH crashed", True, (255, 150, 150))
            win.blit(title, (20, 20))
            sub = font.render("Here's what went wrong and how to fix it:", True, (200, 150, 150))
            win.blit(sub, (20, 48))

            hint_surf = font.render("FIX: " + hint, True, (100, 255, 150))
            win.blit(hint_surf, (20, 95))

            y = 125
            for line in err_text.splitlines()[:18]:
                surf = font.render(line[:95] + (".." if len(line) > 95 else ""), True, (230, 200, 200))
                win.blit(surf, (20, y))
                y += line_h

            footer = font.render("ESC or close window to exit", True, (120, 100, 100))
            win.blit(footer, (20, 398))
            pygame.display.flip()

        pygame.quit()
    except Exception:
        pass

    print("\n" + "=" * 60)
    print("NEON RUSH - CRASH REPORT")
    print("=" * 60)
    if heal_actions:
        print("AUTO-FIX ATTEMPTED:", "; ".join(heal_actions))
    print("FIX:", hint)
    print("-" * 60)
    print(err_text)
    print("=" * 60)


def preinit_heal():
    heal_highscores()
    ev = evolve_load()
    if ev.get("heals", {}).get("crash_display", {}).get("ok", 0) > 0:
        os.environ.setdefault("SDL_VIDEODRIVER", "x11")
