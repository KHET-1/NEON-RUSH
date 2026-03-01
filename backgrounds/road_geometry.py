"""Pseudo-3D road geometry — curves, hills, and per-scanline projection.

Provides a shared track model that both the background renderer and sprites
query for perspective-correct positioning.
"""
import random
import math
import logging

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, ROAD_CENTER

log = logging.getLogger("neon_rush.road_geometry")

# --- Projection constants ---
_HORIZON_Y = int(SCREEN_HEIGHT * 0.30)   # 180
_GROUND_ROWS = SCREEN_HEIGHT - _HORIZON_Y  # 420
_PROJECTION_D = 100.0

# --- Road dimensions (V2 wider road) ---
_V2_ROAD_HALF = 350  # 700px road at bottom

# --- Track geometry ---
_NUM_SEGMENTS = 800
_CURVE_SCALE = 400.0    # low deflection — gentle sweeping curves only
_HILL_SCALE = 40.0       # subtle hills
_SEGMENT_LENGTH = 1.0    # world units per segment

# --- Track recipe definitions ---
# Very long, very gentle curves. Mostly straight. Highway feel, not rally.
# Each recipe: (name, length_range, curve_range, hill_range)
_RECIPES = [
    ("straight",     (100, 200), (0.0, 0.0),      (0.0, 0.0)),
    ("straight",     (120, 250), (0.0, 0.0),      (0.0, 0.0)),   # weighted x2
    ("straight",     (80, 180),  (0.0, 0.0),      (0.0, 0.0)),   # weighted x3
    ("gentle_left",  (100, 180), (-0.15, -0.05),   (0.0, 0.0)),
    ("gentle_right", (100, 180), (0.05, 0.15),     (0.0, 0.0)),
    ("sweep_left",   (80, 140),  (-0.25, -0.10),   (0.0, 0.0)),
    ("sweep_right",  (80, 140),  (0.10, 0.25),     (0.0, 0.0)),
    ("s_curve",      (160, 260), (-0.15, 0.15),    (0.0, 0.0)),  # special handling
    ("hill_up",      (60, 100),  (0.0, 0.0),      (0.1, 0.3)),
    ("hill_down",    (60, 100),  (0.0, 0.0),      (-0.3, -0.1)),
    ("hill_crest",   (80, 140),  (0.0, 0.0),      (0.1, 0.25)),  # special: up then down
    ("curve_hill",   (80, 130),  (-0.1, 0.1),     (0.1, 0.2)),
]


class RoadSegment:
    """One world-unit of track with curve and hill values."""
    __slots__ = ('curve', 'hill_y')

    def __init__(self, curve=0.0, hill_y=0.0):
        self.curve = curve
        self.hill_y = hill_y


class ScanlineData:
    """Pre-computed projection data for one screen scanline."""
    __slots__ = ('center_x', 'half_w', 'screen_y', 't', 'world_z', 'seg_idx')

    def __init__(self):
        self.center_x = ROAD_CENTER
        self.half_w = 0.0
        self.screen_y = 0
        self.t = 0.0
        self.world_z = 0.0
        self.seg_idx = 0


class RoadGeometry:
    """Track model with procedural generation and per-frame projection."""

    def __init__(self):
        self.segments = [RoadSegment() for _ in range(_NUM_SEGMENTS)]
        self.camera_z = 0.0  # world position of camera
        self.current_curve = 0.0  # smoothed curve value at camera (for parallax)
        self._raw_curve = 0.0    # unsmoothed curve for interpolation

        # Pre-allocate scanline data array
        self.scanline_data = [ScanlineData() for _ in range(_GROUND_ROWS)]

        # Pre-compute per-scanline t and base z (same as desert_bg)
        self._line_t = []
        self._line_z = []
        for i in range(_GROUND_ROWS):
            t = (i + 1) / max(1, _GROUND_ROWS)
            self._line_t.append(t)
            self._line_z.append(_PROJECTION_D / max(t, 0.003))

        # Track generation state
        self._gen_cursor = 0  # next segment to generate
        self._rng = random.Random(42)
        self._generate_initial_track()
        self._log_tick = 0  # rate-limit logging

        log.info("RoadGeometry init: %d segments, %d scanlines, road_half=%d",
                 _NUM_SEGMENTS, _GROUND_ROWS, _V2_ROAD_HALF)

    def _generate_initial_track(self):
        """Fill the entire segment buffer with road recipes."""
        self._gen_cursor = 0
        while self._gen_cursor < _NUM_SEGMENTS:
            self._append_recipe()

    def _append_recipe(self):
        """Generate a section of road from a random recipe."""
        name, len_range, curve_range, hill_range = self._rng.choice(_RECIPES)
        length = self._rng.randint(*len_range)

        # Don't overshoot buffer
        remaining = _NUM_SEGMENTS - self._gen_cursor
        if remaining <= 0:
            return
        length = min(length, remaining)

        if name == "s_curve":
            self._gen_s_curve(length)
        elif name == "hill_crest":
            self._gen_hill_crest(length, hill_range)
        else:
            target_curve = self._rng.uniform(*curve_range) if curve_range != (0.0, 0.0) else 0.0
            target_hill = self._rng.uniform(*hill_range) if hill_range != (0.0, 0.0) else 0.0
            self._gen_smooth_section(length, target_curve, target_hill)

    def _gen_smooth_section(self, length, target_curve, target_hill):
        """Generate a section with sine-eased transition in/out."""
        ease_len = min(length * 2 // 5, 50)  # 40% of section is easing — ultra smooth

        for i in range(length):
            if self._gen_cursor >= _NUM_SEGMENTS:
                return
            # Ease in/out
            if i < ease_len:
                factor = 0.5 * (1 - math.cos(math.pi * i / ease_len))
            elif i > length - ease_len:
                factor = 0.5 * (1 - math.cos(math.pi * (length - i) / ease_len))
            else:
                factor = 1.0

            seg = self.segments[self._gen_cursor]
            seg.curve = target_curve * factor
            seg.hill_y = target_hill * factor
            self._gen_cursor += 1

    def _gen_s_curve(self, length):
        """S-curve: left half then right half (or vice versa)."""
        intensity = self._rng.uniform(0.3, 0.7)
        flip = self._rng.choice([-1, 1])
        half = length // 2

        for i in range(length):
            if self._gen_cursor >= _NUM_SEGMENTS:
                return
            # Sine wave through the S
            t = i / max(1, length - 1)
            curve = math.sin(t * math.pi * 2) * intensity * flip

            seg = self.segments[self._gen_cursor]
            seg.curve = curve
            seg.hill_y = 0.0
            self._gen_cursor += 1

    def _gen_hill_crest(self, length, hill_range):
        """Hill that goes up then comes down."""
        peak = self._rng.uniform(*hill_range)

        for i in range(length):
            if self._gen_cursor >= _NUM_SEGMENTS:
                return
            # Sine arch
            t = i / max(1, length - 1)
            hill = math.sin(t * math.pi) * peak

            seg = self.segments[self._gen_cursor]
            seg.curve = 0.0
            seg.hill_y = hill
            self._gen_cursor += 1

    def advance(self, speed):
        """Move camera forward through the segment buffer.

        When camera passes a segment, recycle it at the end with new geometry.
        """
        self.camera_z += speed * 0.15  # match desert_bg _SCROLL_K

        # Check if we've consumed segments — wrap and regenerate
        seg_index = int(self.camera_z / _SEGMENT_LENGTH) % _NUM_SEGMENTS
        # Heavy smoothing — road feels like a highway, not a go-kart track
        self._raw_curve = self.segments[seg_index].curve
        self.current_curve += (self._raw_curve - self.current_curve) * 0.03

        # Periodic logging (every ~2 seconds at 144fps)
        self._log_tick += 1
        if self._log_tick % 288 == 0:
            sd_mid = self.scanline_data[_GROUND_ROWS // 2]
            sd_bot = self.scanline_data[_GROUND_ROWS - 1]
            log.debug("cam_z=%.1f seg=%d curve=%.3f | mid_cx=%.0f bot_cx=%.0f bot_hw=%.0f",
                      self.camera_z, seg_index, self.current_curve,
                      sd_mid.center_x, sd_bot.center_x, sd_bot.half_w)

    def compute_projection(self):
        """Fill scanline_data[] with per-scanline perspective values.

        Iterates bottom-to-top, accumulating curve deflection (dx).
        Curves deflect strongest near the horizon.
        """
        base_seg = int(self.camera_z / _SEGMENT_LENGTH)
        dx = 0.0
        prev_y = SCREEN_HEIGHT + 1  # for hill overlap detection

        for i in range(_GROUND_ROWS - 1, -1, -1):
            sd = self.scanline_data[i]
            t = self._line_t[i]
            z = self._line_z[i]

            # Which segment does this scanline map to?
            seg_offset = int(z * 0.1)  # scale z to segment index range
            seg_idx = (base_seg + seg_offset) % _NUM_SEGMENTS
            seg = self.segments[seg_idx]

            # Accumulate curve deflection (stronger near horizon where t is small)
            # We iterate bottom-to-top so dx builds up toward horizon
            curve_strength = (1.0 - t) * seg.curve
            dx += curve_strength * (_CURVE_SCALE / _GROUND_ROWS)

            # Hill offset: shifts scanline vertically
            hill_offset = seg.hill_y * (1.0 - t) * _HILL_SCALE

            # Effective screen Y with hill
            effective_y = _HORIZON_Y + i + hill_offset

            # Prevent scanline overlap from hills (skip if it would draw above previous)
            if effective_y >= prev_y:
                effective_y = prev_y - 1
            prev_y = effective_y

            # Road width tapers with perspective
            half_w = _V2_ROAD_HALF * t

            # Clamp center_x so road doesn't go fully offscreen
            center_x = ROAD_CENTER + dx
            min_cx = half_w * 0.3
            max_cx = SCREEN_WIDTH - half_w * 0.3
            center_x = max(min_cx, min(center_x, max_cx))

            sd.center_x = center_x
            sd.half_w = half_w
            sd.screen_y = effective_y
            sd.t = t
            sd.world_z = z
            sd.seg_idx = seg_idx

    def get_sprite_projection(self, world_z, lane_offset):
        """Project a world-space sprite to screen coordinates.

        Args:
            world_z: distance from camera in world units (positive = ahead)
            lane_offset: -1.0 (left edge) to +1.0 (right edge), 0.0 = center

        Returns:
            (screen_x, screen_y, scale, visible) or None if behind camera.
            scale is 0.0 (horizon) to 1.0 (bottom of screen).
        """
        if world_z <= 0:
            return None

        # Map world_z to a t value (depth ratio)
        t = _PROJECTION_D / world_z
        if t > 1.0:
            t = 1.0
        if t < 0.005:
            return None  # too far, invisible

        # Find the closest scanline index for this t
        scanline_idx = int(t * _GROUND_ROWS) - 1
        scanline_idx = max(0, min(scanline_idx, _GROUND_ROWS - 1))

        sd = self.scanline_data[scanline_idx]

        # Position sprite using the scanline's center and width
        screen_x = sd.center_x + lane_offset * sd.half_w
        screen_y = sd.screen_y

        # Scale factor: 0 at horizon, 1 at bottom
        scale = t

        return screen_x, screen_y, scale, True

    def get_road_bounds_at_bottom(self):
        """Return (left, right) road bounds at the bottom scanline (player position)."""
        sd = self.scanline_data[_GROUND_ROWS - 1]
        left = sd.center_x - sd.half_w
        right = sd.center_x + sd.half_w
        return left, right
