"""Enhanced crash reporting with session tracking, auto-save, and clipboard copy.

Usage:
    from core.crash_report import session, generate_crash_report, show_crash_screen_v2

    # At game start:
    session.start()

    # During gameplay (update each frame or on state changes):
    session.update(state=..., mode=..., shared_state=..., current_mode=..., tick=...)

    # On crash (replaces old show_crash_screen):
    report = generate_crash_report(exc_type, exc_value, exc_tb, heal_actions)
    show_crash_screen_v2(report)
"""

import os
import sys
import json
import time
import traceback
import subprocess
import platform

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRASH_LOG_DIR = os.path.join(_BASE_DIR, "crash_logs")
BUILD_FILE = os.path.join(_BASE_DIR, ".neon_rush_build.json")

# Build number management
def _load_build_info():
    try:
        with open(BUILD_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"build": 0, "git_hash": "unknown"}


def _save_build_info(info):
    try:
        with open(BUILD_FILE, "w") as f:
            json.dump(info, f, indent=2)
    except Exception:
        pass


def get_build_number():
    info = _load_build_info()
    # Try to get git hash
    git_hash = "unknown"
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=3,
            cwd=_BASE_DIR
        )
        if result.returncode == 0:
            git_hash = result.stdout.strip()
    except Exception:
        pass

    info["build"] = info.get("build", 0) + 1
    info["git_hash"] = git_hash
    _save_build_info(info)
    return info["build"], git_hash


def _fmt_duration(seconds):
    """Human-readable duration like '2 min 34 sec' or '45 sec'."""
    if seconds < 0:
        return "0 sec"
    m = int(seconds) // 60
    s = int(seconds) % 60
    if m > 0:
        return f"{m} min {s} sec"
    return f"{s} sec"


def _fmt_timestamp(t):
    """Format a time.time() value as 'HH:MM:SS'."""
    return time.strftime("%H:%M:%S", time.localtime(t))


def _fmt_datetime(t):
    """Format as 'YYYY-MM-DD HH:MM:SS'."""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))


class SessionTracker:
    """Tracks game session metadata for crash reporting.

    Updated by the main loop. Read by crash handler.
    Lives at module level so it survives main() scope.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.session_start = None
        self.build_number = 0
        self.git_hash = "unknown"
        self.state = "uninitialized"
        self.difficulty = "normal"
        self.num_players = 1
        self.tick = 0
        self.fps_samples = []

        # Mode tracking
        self.current_mode_name = None
        self.current_mode_index = -1
        self.mode_start_time = None
        self.modes_visited = []

        # Player snapshot (updated periodically)
        self.player_snapshots = []

        # Game metrics
        self.game_distance = 0.0
        self.total_score = 0
        self.total_coins = 0
        self.bosses_defeated = 0

        # Boss state
        self.boss_active = False
        self.boss_hp = 0
        self.boss_max_hp = 0
        self.boss_phase = 0

        # Event log (ring buffer, last 20 events)
        self.events = []
        self.MAX_EVENTS = 20

        # Sequences (transitions, boss fights, etc.)
        self.active_sequences = []
        self.completed_sequences = []

    def start(self):
        """Call at session start."""
        self.reset()
        self.session_start = time.time()
        self.build_number, self.git_hash = get_build_number()
        self._log_event("session_start")

    def _log_event(self, event_type, detail=""):
        entry = {
            "time": time.time(),
            "tick": self.tick,
            "type": event_type,
            "detail": detail,
        }
        self.events.append(entry)
        if len(self.events) > self.MAX_EVENTS:
            self.events.pop(0)

    def update(self, state=None, shared_state=None, current_mode=None, tick=None):
        """Called from main loop to update session state."""
        if tick is not None:
            self.tick = tick

        if state and state != self.state:
            old_state = self.state
            self.state = state
            self._log_event("state_change", f"{old_state} -> {state}")

        if shared_state:
            self.difficulty = shared_state.difficulty
            self.num_players = shared_state.num_players
            self.total_score = shared_state.best_score
            self.total_coins = shared_state.total_coins
            self.bosses_defeated = shared_state.bosses_defeated

        if current_mode:
            mode_name = getattr(current_mode, 'MODE_NAME', 'unknown')
            mode_idx = getattr(current_mode, 'MODE_INDEX', -1)

            if mode_name != self.current_mode_name:
                if self.current_mode_name:
                    self._log_event("mode_end", self.current_mode_name)
                    self.completed_sequences.append({
                        "type": "mode",
                        "name": self.current_mode_name,
                        "duration": time.time() - (self.mode_start_time or time.time()),
                    })
                self.current_mode_name = mode_name
                self.current_mode_index = mode_idx
                self.mode_start_time = time.time()
                if mode_name not in self.modes_visited:
                    self.modes_visited.append(mode_name)
                self._log_event("mode_start", mode_name)

            self.game_distance = getattr(current_mode, 'game_distance', 0.0)

            # Boss state
            boss = getattr(current_mode, 'boss', None)
            boss_active = getattr(current_mode, 'boss_active', False)
            if boss_active and not self.boss_active:
                self._log_event("boss_spawn", mode_name)
                self.active_sequences.append({"type": "boss_fight", "mode": mode_name, "start": time.time()})
            elif not boss_active and self.boss_active:
                self._log_event("boss_end", mode_name)
                # Close active boss sequence
                for seq in self.active_sequences:
                    if seq["type"] == "boss_fight" and "end" not in seq:
                        seq["end"] = time.time()
                        self.completed_sequences.append(seq)
                self.active_sequences = [s for s in self.active_sequences if "end" not in s]

            self.boss_active = boss_active
            if boss:
                self.boss_hp = getattr(boss, 'hp', 0)
                self.boss_max_hp = getattr(boss, 'max_hp', 0)
                self.boss_phase = getattr(boss, 'current_phase_idx', 0)

            # Player snapshots (every 60 ticks to avoid overhead)
            if self.tick % 60 == 0:
                players = getattr(current_mode, 'players', [])
                self.player_snapshots = []
                for p in players:
                    self.player_snapshots.append({
                        "name": getattr(p, 'name', '?'),
                        "alive": getattr(p, 'alive', False),
                        "lives": getattr(p, 'lives', 0),
                        "score": getattr(p, 'score', 0),
                        "coins": getattr(p, 'coins', 0),
                        "distance": round(getattr(p, 'distance', 0.0), 2),
                        "heat": round(getattr(p, 'heat', 0.0), 1),
                        "speed": round(getattr(p, 'speed', 0.0), 1),
                        "shield": getattr(p, 'shield', False),
                        "ghost": getattr(p, 'ghost_mode', False),
                        "pos": (getattr(p, 'rect', None) and (p.rect.centerx, p.rect.centery)) or (0, 0),
                    })

    def update_transition(self, style, target_mode):
        """Called when a transition starts."""
        self._log_event("transition_start", f"{style} -> {target_mode}")
        self.active_sequences.append({"type": "transition", "style": style, "target": target_mode, "start": time.time()})

    def update_transition_end(self):
        """Called when a transition completes."""
        self._log_event("transition_end")
        for seq in self.active_sequences:
            if seq["type"] == "transition" and "end" not in seq:
                seq["end"] = time.time()
                self.completed_sequences.append(seq)
        self.active_sequences = [s for s in self.active_sequences if "end" not in s]


# Module-level singleton
session = SessionTracker()


# ── Crash Report Generation ──────────────────────────────────────────

FIX_HINTS = {
    "pygame.error": "Pygame display/audio failed. Try: close other fullscreen apps, update GPU drivers, or run with SDL_VIDEODRIVER=x11",
    "ModuleNotFoundError": "Missing dependency. Run: pip install -r requirements.txt",
    "FileNotFoundError": "Missing file or asset. Check the file path and that you're running from the project root.",
    "PermissionError": "No write access. Run from a directory you own, or fix highscores.json permissions.",
    "json.JSONDecodeError": "Corrupt highscores.json. Delete or fix the file.",
    "MemoryError": "Out of memory. Close other apps or reduce PARTICLE_CAP in the code.",
    "KeyError": "Missing key — a required value wasn't found in a dictionary. Check game data or config files.",
    "TypeError": "Wrong data type passed to a function. Often from bad config, uninitialized state, or save file corruption.",
    "AttributeError": "Tried to use a method on an object that doesn't have it. Usually from uninitialized module or version mismatch.",
    "IndexError": "List/array index out of range. May indicate empty or corrupt data.",
    "ZeroDivisionError": "Division by zero — a game value was unexpectedly 0.",
}


def _get_human_error(exc_type, exc_value, tb_lines):
    """Generate a human-readable error explanation."""
    err_name = exc_type.__name__
    err_msg = str(exc_value) if exc_value else ""

    # Find the crash location
    crash_file = "unknown"
    crash_line = 0
    crash_code = ""
    for line in reversed(tb_lines):
        line = line.strip()
        if line.startswith("File "):
            parts = line.split('"')
            if len(parts) >= 2:
                crash_file = os.path.basename(parts[1])
            try:
                crash_line = int(line.split("line ")[1].split(",")[0])
            except (IndexError, ValueError):
                pass
            break
        elif not line.startswith("^") and not line.startswith("~") and line and not line.startswith("Traceback"):
            crash_code = line

    # Build human explanation
    explanation = f"The game crashed in {crash_file} at line {crash_line}."

    if err_name == "AttributeError" and "'NoneType'" in err_msg:
        obj = err_msg.split("'NoneType'")[0].strip()
        attr = err_msg.split("attribute '")[-1].rstrip("'") if "attribute '" in err_msg else "?"
        explanation += f"\nA variable was None (empty/uninitialized) when the game tried to call .{attr}() on it."
        explanation += "\nThis usually means something wasn't set up yet or was cleared too early."
    elif err_name == "KeyError":
        explanation += f"\nTried to look up '{err_msg}' but it doesn't exist in the dictionary."
        explanation += "\nThis could mean a sound, font, or config wasn't loaded properly."
    elif err_name == "TypeError":
        explanation += f"\n{err_msg}"
        explanation += "\nA function received the wrong type of argument."
    elif err_name == "IndexError":
        explanation += f"\nTried to access an item that doesn't exist in a list. The list may be empty."
    else:
        if err_msg:
            explanation += f"\n{err_msg}"

    return explanation, crash_file, crash_line


def generate_crash_report(exc_type, exc_value, exc_tb, heal_actions=None):
    """Generate a comprehensive crash report dict."""
    heal_actions = heal_actions or []
    now = time.time()
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
    tb_text = "".join(tb_lines).strip()
    err_short = f"{exc_type.__name__}: {exc_value}" if exc_value else str(exc_type)

    # Human-readable error
    human_error, crash_file, crash_line = _get_human_error(exc_type, exc_value, tb_text.splitlines())

    # Fix hint
    hint = "Check the traceback below and fix the reported line."
    for key, msg in FIX_HINTS.items():
        if key in err_short or key in tb_text:
            hint = msg
            break
    if heal_actions:
        hint = "Auto-fix attempted: " + "; ".join(heal_actions) + ". " + hint

    # Session timing
    session_start = session.session_start or now
    elapsed = now - session_start
    mode_elapsed = (now - session.mode_start_time) if session.mode_start_time else 0

    # Active sequences summary
    active_seq_summary = []
    for seq in session.active_sequences:
        dur = now - seq.get("start", now)
        active_seq_summary.append(f"{seq['type']}({_fmt_duration(dur)})")

    completed_seq_summary = []
    for seq in session.completed_sequences[-10:]:
        dur = seq.get("end", now) - seq.get("start", now)
        completed_seq_summary.append(f"{seq['type']}:{seq.get('name', seq.get('style', '?'))}({_fmt_duration(dur)})")

    report = {
        # Header
        "build": f"#{session.build_number}",
        "git_hash": session.git_hash,
        "platform": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),

        # Timestamps
        "session_start": _fmt_datetime(session_start),
        "crash_time": _fmt_datetime(now),
        "session_duration": _fmt_duration(elapsed),
        "session_seconds": round(elapsed, 2),
        "mode_duration": _fmt_duration(mode_elapsed),

        # Game state
        "state": session.state,
        "difficulty": session.difficulty,
        "num_players": session.num_players,
        "tick": session.tick,
        "fps": f"{session.tick / max(1, elapsed):.1f} avg" if elapsed > 1 else "N/A",

        # Mode
        "current_mode": session.current_mode_name or "none",
        "mode_index": session.current_mode_index,
        "modes_visited": session.modes_visited,
        "game_distance": f"{session.game_distance:.2f} km",

        # Scores
        "total_score": session.total_score,
        "total_coins": session.total_coins,
        "bosses_defeated": session.bosses_defeated,

        # Boss
        "boss_active": session.boss_active,
        "boss_hp": f"{session.boss_hp}/{session.boss_max_hp}" if session.boss_active else "N/A",
        "boss_phase": session.boss_phase if session.boss_active else "N/A",

        # Players
        "players": session.player_snapshots,

        # Sequences
        "active_sequences": active_seq_summary,
        "completed_sequences": completed_seq_summary,

        # Event log
        "recent_events": [
            {
                "time": _fmt_timestamp(e["time"]),
                "tick": e["tick"],
                "event": f"{e['type']}: {e['detail']}" if e['detail'] else e['type'],
            }
            for e in session.events[-15:]
        ],

        # Error
        "error_short": err_short,
        "human_error": human_error,
        "crash_file": crash_file,
        "crash_line": crash_line,
        "fix_hint": hint,
        "heal_actions": heal_actions,
        "traceback": tb_text,
    }

    # Save to file
    _save_crash_report(report)

    return report


def _save_crash_report(report):
    """Save crash report to crash_logs/ directory."""
    os.makedirs(CRASH_LOG_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    build = report["build"].lstrip("#")
    filename = f"crash_{ts}_b{build}.txt"
    filepath = os.path.join(CRASH_LOG_DIR, filename)

    lines = []
    lines.append("=" * 70)
    lines.append("  NEON RUSH — CRASH REPORT")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"  Build:      {report['build']}  ({report['git_hash']})")
    lines.append(f"  Platform:   {report['platform']}  Python {report['python']}")
    lines.append(f"  Session:    {report['session_start']} → {report['crash_time']}")
    lines.append(f"  Duration:   {report['session_duration']}  (crashed ~{report['session_duration']} into session)")
    lines.append(f"  Frame:      {report['tick']}")
    lines.append("")
    lines.append("-" * 70)
    lines.append("  WHAT HAPPENED (Human Readable)")
    lines.append("-" * 70)
    lines.append("")
    for line in report["human_error"].splitlines():
        lines.append(f"  {line}")
    lines.append("")
    lines.append(f"  Suggested Fix: {report['fix_hint']}")
    lines.append("")
    lines.append("-" * 70)
    lines.append("  GAME STATE AT CRASH")
    lines.append("-" * 70)
    lines.append("")
    lines.append(f"  State:        {report['state']}")
    lines.append(f"  Mode:         {report['current_mode']} (index {report['mode_index']})")
    lines.append(f"  In mode for:  {report['mode_duration']}")
    lines.append(f"  Difficulty:   {report['difficulty']}")
    lines.append(f"  Players:      {report['num_players']}")
    lines.append(f"  Distance:     {report['game_distance']}")
    lines.append(f"  Score:        {report['total_score']}")
    lines.append(f"  Coins:        {report['total_coins']}")
    lines.append(f"  Bosses:       {report['bosses_defeated']}/3")
    lines.append(f"  Boss active:  {report['boss_active']}")
    if report['boss_active']:
        lines.append(f"  Boss HP:      {report['boss_hp']}")
        lines.append(f"  Boss phase:   {report['boss_phase']}")
    lines.append(f"  Modes played: {' → '.join(report['modes_visited']) or 'none'}")
    lines.append("")

    if report["players"]:
        lines.append("  Players:")
        for p in report["players"]:
            status = "ALIVE" if p["alive"] else "DEAD"
            pw = f"Shield" if p["shield"] else ""
            pw += f" Ghost" if p["ghost"] else ""
            pw = pw.strip() or "none"
            lines.append(f"    {p['name']}: {status} | Lives: {p['lives']} | Score: {p['score']} | "
                         f"Coins: {p['coins']} | Heat: {p['heat']} | Speed: {p['speed']} | Powerups: {pw}")
        lines.append("")

    if report["active_sequences"]:
        lines.append(f"  Active sequences: {', '.join(report['active_sequences'])}")
    if report["completed_sequences"]:
        lines.append(f"  Completed:        {', '.join(report['completed_sequences'][-5:])}")
    lines.append("")

    lines.append("-" * 70)
    lines.append("  EVENT LOG (recent)")
    lines.append("-" * 70)
    lines.append("")
    for ev in report["recent_events"]:
        lines.append(f"  [{ev['time']}] tick {ev['tick']:>6}  {ev['event']}")
    lines.append("")

    if report["heal_actions"]:
        lines.append("-" * 70)
        lines.append("  AUTO-REPAIR ATTEMPTED")
        lines.append("-" * 70)
        for a in report["heal_actions"]:
            lines.append(f"  - {a}")
        lines.append("")

    lines.append("-" * 70)
    lines.append("  FULL TRACEBACK")
    lines.append("-" * 70)
    lines.append("")
    for line in report["traceback"].splitlines():
        lines.append(f"  {line}")
    lines.append("")
    lines.append("=" * 70)

    text = "\n".join(lines)
    try:
        with open(filepath, "w") as f:
            f.write(text)
        report["_saved_to"] = filepath
    except Exception:
        report["_saved_to"] = None

    return text


def _copy_to_clipboard(text):
    """Try to copy text to system clipboard."""
    methods = [
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
        ["wl-copy"],
    ]
    for cmd in methods:
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            proc.communicate(text.encode("utf-8"), timeout=3)
            if proc.returncode == 0:
                return True
        except Exception:
            continue
    return False


def _format_screen_report(report):
    """Format a compact version for the crash screen display."""
    lines = []
    lines.append(f"Build {report['build']}  |  {report['crash_time']}  |  Session: {report['session_duration']}")
    lines.append("")
    for line in report["human_error"].splitlines():
        lines.append(line)
    lines.append("")
    lines.append(f"Mode: {report['current_mode']}  |  State: {report['state']}  |  Tick: {report['tick']}")
    lines.append(f"Score: {report['total_score']}  |  Distance: {report['game_distance']}  |  Bosses: {report['bosses_defeated']}/3")
    if report["players"]:
        p = report["players"][0]
        lines.append(f"Player: {p['name']} {'ALIVE' if p['alive'] else 'DEAD'} | Lives: {p['lives']} | Heat: {p['heat']}")
    if report["boss_active"]:
        lines.append(f"Boss: HP {report['boss_hp']}  Phase {report['boss_phase']}")
    lines.append("")
    lines.append(f"Fix: {report['fix_hint'][:90]}")
    return lines


def show_crash_screen_v2(report):
    """Enhanced crash screen with copy button, metadata, and auto-saved report."""
    import pygame

    saved_path = report.get("_saved_to")

    # Build the full clipboard text
    full_text = _save_crash_report(report)  # reuse formatter
    screen_lines = _format_screen_report(report)

    tb_lines = report["traceback"].splitlines()

    copied = False
    scroll_offset = 0
    max_tb_visible = 12

    try:
        try:
            pygame.init()
        except Exception:
            pass

        win = pygame.display.set_mode((780, 540))
        pygame.display.set_caption("NEON RUSH - Crash Report")
        font = pygame.font.SysFont("freesans", 15)
        font_b = pygame.font.SysFont("freesans", 17, bold=True)
        font_sm = pygame.font.SysFont("freesans", 13)
        font_title = pygame.font.SysFont("freesans", 22, bold=True)

        running = True
        while running:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        running = False
                    elif e.key == pygame.K_c:
                        if _copy_to_clipboard(full_text):
                            copied = True
                    elif e.key == pygame.K_UP:
                        scroll_offset = max(0, scroll_offset - 1)
                    elif e.key == pygame.K_DOWN:
                        scroll_offset = min(max(0, len(tb_lines) - max_tb_visible), scroll_offset + 1)
                if e.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = e.pos
                    # Copy button area
                    if 580 <= mx <= 760 and 490 <= my <= 520:
                        if _copy_to_clipboard(full_text):
                            copied = True

            win.fill((25, 12, 18))

            # Header bar
            pygame.draw.rect(win, (70, 25, 35), (0, 0, 780, 55))
            pygame.draw.line(win, (255, 80, 100), (0, 55), (780, 55), 2)

            title = font_title.render("NEON RUSH — Crash Report", True, (255, 150, 150))
            win.blit(title, (16, 14))

            build_t = font_sm.render(f"Build {report['build']}  |  {report['git_hash']}", True, (180, 120, 120))
            win.blit(build_t, (780 - build_t.get_width() - 16, 20))

            # Summary section
            y = 65
            for line in screen_lines:
                color = (100, 255, 150) if line.startswith("Fix:") else (220, 200, 200)
                if "DEAD" in line:
                    color = (255, 100, 100)
                elif "Boss:" in line:
                    color = (255, 200, 80)
                surf = font.render(line[:100], True, color)
                win.blit(surf, (16, y))
                y += 18
                if y > 240:
                    break

            # Traceback section
            pygame.draw.line(win, (80, 60, 70), (16, 250), (764, 250), 1)
            tb_label = font_b.render("Traceback:", True, (200, 160, 160))
            win.blit(tb_label, (16, 256))

            y = 278
            visible_lines = tb_lines[scroll_offset:scroll_offset + max_tb_visible]
            for line in visible_lines:
                display_line = line[:105] + (".." if len(line) > 105 else "")
                color = (255, 120, 120) if "Error" in line or "Exception" in line else (200, 180, 180)
                if line.strip().startswith("File "):
                    color = (180, 180, 220)
                surf = font_sm.render(display_line, True, color)
                win.blit(surf, (20, y))
                y += 16

            # Scroll indicator
            if len(tb_lines) > max_tb_visible:
                scroll_text = font_sm.render(f"↑↓ scroll ({scroll_offset + 1}-{min(scroll_offset + max_tb_visible, len(tb_lines))}/{len(tb_lines)})", True, (120, 100, 100))
                win.blit(scroll_text, (16, y + 4))

            # Footer
            pygame.draw.line(win, (80, 60, 70), (16, 480), (764, 480), 1)

            # Saved location
            if saved_path:
                saved_t = font_sm.render(f"Saved: {os.path.basename(saved_path)}", True, (100, 180, 100))
                win.blit(saved_t, (16, 490))
                dir_t = font_sm.render(f"({CRASH_LOG_DIR}/)", True, (80, 140, 80))
                win.blit(dir_t, (16, 506))

            # Copy button
            btn_color = (40, 120, 60) if copied else (60, 50, 70)
            btn_border = (100, 255, 150) if copied else (150, 120, 140)
            pygame.draw.rect(win, btn_color, (580, 490, 180, 30), border_radius=4)
            pygame.draw.rect(win, btn_border, (580, 490, 180, 30), 2, border_radius=4)
            btn_text = "Copied!" if copied else "Press C to Copy"
            btn_surf = font_b.render(btn_text, True, (200, 255, 200) if copied else (200, 180, 200))
            win.blit(btn_surf, (580 + 90 - btn_surf.get_width() // 2, 494))

            # ESC hint
            esc_t = font_sm.render("ESC to exit", True, (100, 80, 80))
            win.blit(esc_t, (780 - esc_t.get_width() - 16, 524))

            pygame.display.flip()

        pygame.quit()
    except Exception:
        pass

    # Console fallback
    print()
    print(full_text)
