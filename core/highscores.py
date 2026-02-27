import json
import os

from core.healing import HIGHSCORE_FILE, heal_highscores

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_highscores():
    try:
        with open(HIGHSCORE_FILE, "r") as f:
            data = json.load(f)
        if isinstance(data, list) and all(
            isinstance(s, dict) and "name" in s and "score" in s for s in data
        ):
            return data
        raise ValueError("Invalid structure")
    except (FileNotFoundError, json.JSONDecodeError, ValueError, KeyError):
        heal_highscores()
        return []


def save_highscores(scores):
    safe = [{"name": str(s.get("name", "???")[:3]), "score": int(s.get("score", 0))} for s in scores[:5]]
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            json.dump(safe, f)
    except (PermissionError, OSError):
        try:
            alt = os.path.join(_BASE_DIR, "highscores_backup.json")
            with open(alt, "w") as f:
                json.dump(safe, f)
        except Exception:
            pass


def is_highscore(score):
    scores = load_highscores()
    return len(scores) < 5 or score > min(s["score"] for s in scores)
