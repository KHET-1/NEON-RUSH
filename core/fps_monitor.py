"""FPS Monitor — tiered performance alerts during gameplay.

Thresholds (gameplay only):
  INFO   : <130 FPS sustained >3 seconds
  RED    : <30 FPS sustained >2 seconds
  CRITICAL: <5 FPS sustained >2 seconds
"""
import time
import logging

import pygame

from core.constants import SCREEN_WIDTH

log = logging.getLogger("neon_rush.fps")

# Alert tiers: (threshold_fps, hold_seconds, label, color, log_level)
_TIERS = [
    (5,   2.0, "CRITICAL: RENDERER STALLED", (255, 30, 30),   logging.CRITICAL),
    (30,  2.0, "LOW FPS",                    (255, 60, 40),   logging.ERROR),
    (130, 3.0, "FPS WARNING",                (255, 200, 50),  logging.WARNING),
]


class FPSMonitor:
    """Lightweight, non-blocking FPS tracker with tiered alerts."""

    __slots__ = (
        "_clock", "_samples", "_fps", "_alert", "_alert_timer",
        "_tier_starts", "_last_logged", "_target_fps",
        "_track_snapshots", "_track_accum", "_track_count",
        "_track_start", "_track_last_snap", "_track_total_frames",
    )

    def __init__(self, clock):
        self._clock = clock
        self._fps = 144.0
        self._alert = None          # (label, color) or None
        self._alert_timer = 0.0     # seconds the alert has been shown
        # Per-tier: timestamp when FPS first dropped below threshold (0 = not active)
        self._tier_starts = [0.0] * len(_TIERS)
        self._last_logged = [0.0] * len(_TIERS)   # rate-limit logs to 1 per 10s
        self._target_fps = 144
        # Tracking state (for end-of-game graph)
        self._track_snapshots = []
        self._track_accum = 0.0
        self._track_count = 0
        self._track_start = 0.0
        self._track_last_snap = 0.0
        self._track_total_frames = 0

    @property
    def target_fps(self):
        return self._target_fps

    @target_fps.setter
    def target_fps(self, value):
        self._target_fps = value

    def start_tracking(self):
        """Reset tracking state for a new game session."""
        self._track_snapshots = []
        self._track_accum = 0.0
        self._track_count = 0
        self._track_start = time.monotonic()
        self._track_last_snap = self._track_start
        self._track_total_frames = 0

    def record_frame(self):
        """Call each gameplay frame to accumulate FPS for graphing."""
        now = time.monotonic()
        self._track_total_frames += 1
        self._track_accum += self._fps
        self._track_count += 1
        if now - self._track_last_snap >= 10.0 and self._track_count > 0:
            avg = self._track_accum / self._track_count
            elapsed = now - self._track_start
            self._track_snapshots.append((elapsed, avg))
            self._track_accum = 0.0
            self._track_count = 0
            self._track_last_snap = now

    def get_snapshots(self):
        """Return list of (elapsed_sec, avg_fps) snapshots."""
        # Flush any remaining accumulation as final snapshot
        result = list(self._track_snapshots)
        if self._track_count > 0:
            avg = self._track_accum / self._track_count
            elapsed = time.monotonic() - self._track_start if self._track_start else 0
            result.append((elapsed, avg))
        return result

    def get_total_frames(self):
        return self._track_total_frames

    def update(self, gameplay_active):
        """Call once per frame. Only triggers alerts when gameplay_active is True."""
        self._fps = self._clock.get_fps()

        if not gameplay_active:
            # Reset all tier timers when not in gameplay
            self._tier_starts = [0.0] * len(_TIERS)
            self._alert = None
            self._alert_timer = 0.0
            return

        now = time.monotonic()
        active_alert = None

        for i, (threshold, hold, label, color, lvl) in enumerate(_TIERS):
            if self._fps < threshold:
                if self._tier_starts[i] == 0.0:
                    self._tier_starts[i] = now
                elapsed = now - self._tier_starts[i]
                if elapsed >= hold:
                    active_alert = (label, color)
                    # Log at most once every 10 seconds per tier
                    if now - self._last_logged[i] > 10.0:
                        log.log(lvl, "%s — %.0f FPS for %.1fs", label, self._fps, elapsed)
                        self._last_logged[i] = now
                    break  # highest-severity tier wins
            else:
                self._tier_starts[i] = 0.0

        self._alert = active_alert
        if active_alert:
            self._alert_timer += self._clock.get_time() / 1000.0
        else:
            self._alert_timer = 0.0

    @property
    def fps(self):
        return self._fps

    def draw(self, screen):
        """Draw FPS counter (always) and alert banner (when active) to game surface."""
        from core.fonts import FONT_HUD_SM

        # Always show FPS in top-right corner (small, unobtrusive)
        fps_val = int(self._fps)
        target = self._target_fps
        target_str = "UNL" if target == 0 else str(target)
        if fps_val >= 130:
            fps_color = (60, 200, 60)
        elif fps_val >= 30:
            fps_color = (255, 200, 50)
        else:
            fps_color = (255, 50, 40)
        fps_text = FONT_HUD_SM.render(f"{fps_val}/{target_str} FPS", True, fps_color)
        screen.blit(fps_text, (SCREEN_WIDTH - fps_text.get_width() - 8, SCREEN_WIDTH > 600 and 94 or 8))

        # Alert banner (pulsing)
        if self._alert:
            label, color = self._alert
            # Pulse alpha for visibility without blocking
            pulse = 0.6 + 0.4 * (1.0 if int(self._alert_timer * 3) % 2 == 0 else 0.4)
            alert_surf = pygame.Surface((SCREEN_WIDTH, 22), pygame.SRCALPHA)
            alert_surf.fill((*color[:3], int(40 * pulse)))
            screen.blit(alert_surf, (0, 0))
            txt = FONT_HUD_SM.render(f"{label}: {int(self._fps)} FPS", True, color)
            screen.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2, 3))
