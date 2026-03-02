"""Run statistics tracker for autoplay sessions."""
import time


class RunStats:
    def __init__(self, run_num):
        self.run_num = run_num
        self.frames = 0
        self.start_time = time.time()
        self.end_time = None
        self.result = "running"
        self.modes_played = []
        self.final_score = 0
        self.final_distance = 0.0
        self.bosses_defeated = 0
        self.deaths = 0
        self.transitions = 0

    def finish(self, result, shared_state=None, current_mode=None):
        self.end_time = time.time()
        self.result = result
        if shared_state:
            self.bosses_defeated = shared_state.bosses_defeated
            self.final_score = shared_state.best_score
            self.final_distance = shared_state.total_distance
        if current_mode:
            live_score = max((p.score for p in current_mode.players), default=0)
            live_dist = current_mode.game_distance
            if live_score > self.final_score:
                self.final_score = live_score
            if live_dist > self.final_distance:
                self.final_distance = live_dist

    @property
    def elapsed(self):
        end = self.end_time or time.time()
        return end - self.start_time

    def summary_line(self):
        elapsed = self.elapsed
        return (f"  Run {self.run_num}: {self.result:<12} | "
                f"{self.frames:>7} frames | "
                f"{elapsed:>6.1f}s wall | "
                f"Score {self.final_score:>8} | "
                f"Dist {self.final_distance:>6.1f}km | "
                f"Bosses {self.bosses_defeated}/3 | "
                f"Modes: {', '.join(self.modes_played) or 'none'}")
