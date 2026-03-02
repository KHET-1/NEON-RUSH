"""Micro Machines Background — Top-down procedural track renderer.

Generates a scrolling top-down race track with:
  - Connected segments: straights, gentle curves, sharp curves, chicanes
  - Neon-edged road with dashed center line and rumble strips
  - Checkpoints every ~1000px
  - Two parallax off-track layers (grass/gravel and darker ground)

Usage:
    bg = MicroMachinesBG()
    bg.update(scroll_speed)
    bg.draw(screen)
"""

import pygame
import random
import math

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    ROAD_COLOR, ROAD_EDGE_COLOR, NEON_CYAN,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TRACK_WIDTH = 200
HALF_TRACK = TRACK_WIDTH // 2

# Segment types
SEG_STRAIGHT = "straight"
SEG_GENTLE_LEFT = "gentle_left"
SEG_GENTLE_RIGHT = "gentle_right"
SEG_SHARP_LEFT = "sharp_left"
SEG_SHARP_RIGHT = "sharp_right"
SEG_CHICANE_LR = "chicane_lr"
SEG_CHICANE_RL = "chicane_rl"

# Segment length range
MIN_SEG_LENGTH = 200
MAX_SEG_LENGTH = 400

# Off-track colors
GRASS_GREEN = (35, 65, 25)
GRAVEL_BROWN = (55, 45, 30)
DARK_GROUND = (22, 22, 28)

# Rumble strip colors
RUMBLE_RED = (200, 40, 40)
RUMBLE_WHITE = (220, 220, 220)

# Center line
CENTER_DASH_LEN = 20
CENTER_GAP_LEN = 15
CENTER_LINE_COLOR = (200, 180, 40)

# Checkpoint
CHECKPOINT_INTERVAL = 1000  # pixels of total scroll distance


# ---------------------------------------------------------------------------
# Track Segment
# ---------------------------------------------------------------------------

class TrackSegment:
    """A single track segment with center-line control points.

    Attributes:
        seg_type: one of the SEG_* constants
        length: pixel length of this segment
        center_x_start: x-center of track at segment top
        center_x_end: x-center of track at segment bottom
        y_start: world-y of segment top edge
        curve_amplitude: max lateral offset for curved segments
        rumble_side: 'left', 'right', or None for rumble strips on curves
    """

    def __init__(self, seg_type, length, center_x_start, y_start):
        self.seg_type = seg_type
        self.length = length
        self.center_x_start = center_x_start
        self.y_start = y_start
        self.y_end = y_start + length

        # Calculate curve offset
        if seg_type == SEG_STRAIGHT:
            self.curve_amplitude = 0
            self.rumble_side = None
        elif seg_type == SEG_GENTLE_LEFT:
            self.curve_amplitude = -random.randint(30, 60)
            self.rumble_side = "left"
        elif seg_type == SEG_GENTLE_RIGHT:
            self.curve_amplitude = random.randint(30, 60)
            self.rumble_side = "right"
        elif seg_type == SEG_SHARP_LEFT:
            self.curve_amplitude = -random.randint(70, 120)
            self.rumble_side = "left"
        elif seg_type == SEG_SHARP_RIGHT:
            self.curve_amplitude = random.randint(70, 120)
            self.rumble_side = "right"
        elif seg_type == SEG_CHICANE_LR:
            self.curve_amplitude = random.randint(50, 90)
            self.rumble_side = "both"
        elif seg_type == SEG_CHICANE_RL:
            self.curve_amplitude = -random.randint(50, 90)
            self.rumble_side = "both"
        else:
            self.curve_amplitude = 0
            self.rumble_side = None

        if seg_type in (SEG_CHICANE_LR, SEG_CHICANE_RL):
            # S-curve returns to starting X at t=1.0, so next segment
            # must also start at center_x_start to avoid a visual jump.
            self.center_x_end = center_x_start
        else:
            self.center_x_end = center_x_start + self.curve_amplitude

    def get_center_x(self, local_t):
        """Get track center x at local_t (0 = top, 1 = bottom).

        Uses sine interpolation for smooth curves. Chicanes use a full
        sine wave (S-bend), while other curves use a half-sine.
        """
        if self.seg_type in (SEG_CHICANE_LR, SEG_CHICANE_RL):
            # S-curve: full sine wave
            return self.center_x_start + self.curve_amplitude * math.sin(local_t * 2 * math.pi)
        else:
            # Half-sine for smooth entry/exit
            t_smooth = 0.5 * (1 - math.cos(math.pi * local_t))
            return self.center_x_start + (self.center_x_end - self.center_x_start) * t_smooth


# ---------------------------------------------------------------------------
# Parallax Decoration Layer
# ---------------------------------------------------------------------------

class OffTrackLayer:
    """Parallax off-track decoration layer with random dots and details.

    Generates a static field of random colored dots that scrolls at
    a fraction of the main track speed.
    """

    def __init__(self, parallax_factor, base_color, detail_colors, dot_density=200):
        self.parallax_factor = parallax_factor
        self.base_color = base_color
        self.detail_colors = detail_colors
        self.offset = 0.0

        # Pre-generate a tile of random dots (tiled vertically)
        self.tile_height = SCREEN_HEIGHT * 2
        self.tile = pygame.Surface((SCREEN_WIDTH, self.tile_height), pygame.SRCALPHA)
        self.tile.fill((*base_color, 255))

        # Scatter random dots
        for _ in range(dot_density):
            x = random.randint(0, SCREEN_WIDTH - 1)
            y = random.randint(0, self.tile_height - 1)
            color = random.choice(detail_colors)
            size = random.randint(1, 3)
            pygame.draw.circle(self.tile, color, (x, y), size)

    def update(self, scroll_speed):
        """Advance parallax offset."""
        self.offset = (self.offset + scroll_speed * self.parallax_factor) % self.tile_height

    def draw(self, screen):
        """Draw the tiled parallax layer."""
        y = -int(self.offset)
        while y < SCREEN_HEIGHT:
            screen.blit(self.tile, (0, y))
            y += self.tile_height


# ---------------------------------------------------------------------------
# Micro Machines Background
# ---------------------------------------------------------------------------

class MicroMachinesBG:
    """Top-down procedural track renderer for Micro Machines mode.

    Standalone class with no game state dependencies beyond scroll speed.

    Usage:
        bg = MicroMachinesBG()
        # Each frame:
        bg.update(scroll_speed)
        bg.draw(screen)
    """

    def __init__(self, tier=1):
        self.tier = tier
        # Segment pool and scroll state
        self.segments = []
        self.scroll_offset = 0.0  # total world-y scrolled
        self.total_distance = 0.0  # for checkpoint tracking

        # Track generation state
        self.current_center_x = SCREEN_WIDTH // 2
        self.next_segment_y = 0.0  # world-y where next segment starts

        # V2+ atmosphere state
        if tier >= 2:
            self._haze_phase = 0.0
            self._tire_marks = self._gen_tire_marks()
            # Pre-allocate fog surface (PERF FIX: was creating new 800x600 SRCALPHA every frame)
            self._haze_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        # Parallax off-track layers
        self.layer_close = OffTrackLayer(
            parallax_factor=0.6,
            base_color=GRASS_GREEN,
            detail_colors=[
                (45, 75, 30), (30, 55, 20), (50, 80, 35),
                (60, 50, 30), (40, 40, 25),
            ],
            dot_density=300,
        )
        self.layer_far = OffTrackLayer(
            parallax_factor=0.3,
            base_color=DARK_GROUND,
            detail_colors=[
                (28, 28, 34), (18, 18, 22), (35, 30, 25),
                (25, 20, 18),
            ],
            dot_density=150,
        )

        # Tire marks on far layer
        for _ in range(20):
            x = random.randint(0, SCREEN_WIDTH - 1)
            y = random.randint(0, self.layer_far.tile_height - 1)
            length = random.randint(20, 60)
            angle = random.uniform(-0.3, 0.3)
            color = (30, 28, 25)
            ex = x + int(math.sin(angle) * length)
            ey = y + int(math.cos(angle) * length)
            pygame.draw.line(self.layer_far.tile, color, (x, y), (ex, ey), 2)

        # V2+: Bake cyberpunk grid lines onto far tile (zero runtime cost)
        if tier >= 2:
            grid_color = (0, 180, 200, 25)
            grid_spacing = 40
            for gx in range(0, SCREEN_WIDTH, grid_spacing):
                pygame.draw.line(self.layer_far.tile, grid_color,
                                 (gx, 0), (gx, self.layer_far.tile_height), 1)
            for gy in range(0, self.layer_far.tile_height, grid_spacing):
                pygame.draw.line(self.layer_far.tile, grid_color,
                                 (0, gy), (SCREEN_WIDTH, gy), 1)

            # Bake environment details onto close tile (zero runtime cost)
            env_rng = random.Random(99)
            for _ in range(25):
                ex = env_rng.randint(10, SCREEN_WIDTH - 10)
                ey = env_rng.randint(10, self.layer_close.tile_height - 10)
                detail_type = env_rng.choice(['building', 'lamp', 'crate'])
                if detail_type == 'building':
                    bw = env_rng.randint(12, 30)
                    bh = env_rng.randint(15, 35)
                    pygame.draw.rect(self.layer_close.tile, (30, 28, 38),
                                     (ex, ey, bw, bh))
                    pygame.draw.rect(self.layer_close.tile, (45, 42, 55),
                                     (ex, ey, bw, bh), 1)
                    # Lit windows
                    for wx in range(ex + 3, ex + bw - 3, 6):
                        for wy in range(ey + 3, ey + bh - 3, 6):
                            if env_rng.random() < 0.6:
                                wc = env_rng.choice([
                                    (255, 220, 100, 80), (100, 200, 255, 60),
                                    (255, 150, 50, 70),
                                ])
                                pygame.draw.rect(self.layer_close.tile, wc,
                                                 (wx, wy, 3, 3))
                elif detail_type == 'lamp':
                    # Thin line + glow dot
                    pygame.draw.line(self.layer_close.tile, (50, 50, 55),
                                     (ex, ey), (ex, ey + 10), 1)
                    pygame.draw.circle(self.layer_close.tile, (200, 200, 150, 100),
                                       (ex, ey), 3)
                else:  # crate
                    cw = env_rng.randint(6, 12)
                    pygame.draw.rect(self.layer_close.tile, (50, 40, 30),
                                     (ex, ey, cw, cw))
                    pygame.draw.rect(self.layer_close.tile, (70, 55, 40),
                                     (ex, ey, cw, cw), 1)

        # --- V3 Holographic Wireframe Upgrades ---
        if tier >= 3:
            from core.vfx import HOLO_PALETTE

            self._holo = HOLO_PALETTE

            # Override far layer to void-black with bright grid
            self.layer_far.tile.fill((2, 3, 8))
            grid_color = (0, 255, 180, 35)
            grid_spacing = 30
            for gx in range(0, SCREEN_WIDTH, grid_spacing):
                pygame.draw.line(self.layer_far.tile, grid_color,
                                 (gx, 0), (gx, self.layer_far.tile_height), 1)
            for gy in range(0, self.layer_far.tile_height, grid_spacing):
                pygame.draw.line(self.layer_far.tile, grid_color,
                                 (0, gy), (SCREEN_WIDTH, gy), 1)
            # Bright intersection dots
            for gx in range(0, SCREEN_WIDTH, grid_spacing):
                for gy in range(0, self.layer_far.tile_height, grid_spacing):
                    pygame.draw.circle(self.layer_far.tile, (0, 255, 220, 60), (gx, gy), 2)

            # Override close layer to darker void
            self.layer_close.tile.fill((4, 5, 12))
            grid_dim = (0, 120, 90, 25)
            for gx in range(0, SCREEN_WIDTH, grid_spacing * 2):
                pygame.draw.line(self.layer_close.tile, grid_dim,
                                 (gx, 0), (gx, self.layer_close.tile_height), 1)
            for gy in range(0, self.layer_close.tile_height, grid_spacing * 2):
                pygame.draw.line(self.layer_close.tile, grid_dim,
                                 (0, gy), (SCREEN_WIDTH, gy), 1)

            # Pre-baked holographic grid tile for road (200x200)
            self._holo_tile = self._make_holo_tile()

            # Pre-baked edge glow strip (replaces per-scanline Surface alloc — perf fix!)
            self._edge_glow_strip = pygame.Surface((8, 1), pygame.SRCALPHA)
            self._edge_glow_strip.fill((0, 255, 200, 50))
            self._edge_glow_wide = pygame.Surface((14, 1), pygame.SRCALPHA)
            self._edge_glow_wide.fill((0, 255, 200, 20))

            # Data wave state (max 3 active)
            self._data_waves = []
            self._data_wave_cooldown = 0

        # Center dash state
        self.dash_offset = 0.0

        # Generate initial segments to fill screen + buffer
        self._generate_initial_segments()

        # Pre-rendered checkpoint stripe surface
        self.checkpoint_surf = self._make_checkpoint_surface()

    def _make_holo_tile(self):
        """Pre-bake 200x200 holographic grid tile for road surface."""
        size = 200
        tile = pygame.Surface((size, size), pygame.SRCALPHA)
        tile.fill((2, 3, 8))
        # Thin cyan grid lines
        spacing = 20
        for x in range(0, size, spacing):
            thick = 2 if x % (spacing * 2) == 0 else 1
            pygame.draw.line(tile, (0, 200, 160, 40), (x, 0), (x, size), thick)
        for y in range(0, size, spacing):
            thick = 2 if y % (spacing * 2) == 0 else 1
            pygame.draw.line(tile, (0, 200, 160, 40), (0, y), (size, y), thick)
        # Intersection dots on primary lines
        for x in range(0, size, spacing * 2):
            for y in range(0, size, spacing * 2):
                pygame.draw.circle(tile, (0, 255, 220, 80), (x, y), 2)
        return tile

    def _gen_tire_marks(self):
        """Pre-generate tire mark positions for V2+ road surface."""
        rng = random.Random(88)
        marks = []
        for _ in range(15):
            marks.append((
                rng.uniform(-0.3, 0.3),   # lateral offset ratio from center
                rng.randint(30, 80),        # length
                rng.uniform(-0.2, 0.2),     # angle
            ))
        return marks

    def _make_checkpoint_surface(self):
        """Create a reusable checkpoint stripe surface."""
        surf = pygame.Surface((TRACK_WIDTH + 20, 8), pygame.SRCALPHA)
        stripe_w = 10
        num_stripes = (TRACK_WIDTH + 20) // stripe_w
        for i in range(num_stripes):
            color = (220, 220, 220) if i % 2 == 0 else (30, 30, 30)
            pygame.draw.rect(surf, color, (i * stripe_w, 0, stripe_w, 8))
        return surf

    def _pick_segment_type(self):
        """Weighted random selection of next segment type."""
        weights = {
            SEG_STRAIGHT: 3.0,
            SEG_GENTLE_LEFT: 2.0,
            SEG_GENTLE_RIGHT: 2.0,
            SEG_SHARP_LEFT: 1.0,
            SEG_SHARP_RIGHT: 1.0,
            SEG_CHICANE_LR: 0.8,
            SEG_CHICANE_RL: 0.8,
        }

        # Bias toward straightening if track center drifted too far
        drift = self.current_center_x - SCREEN_WIDTH // 2
        if drift > 80:
            weights[SEG_GENTLE_LEFT] += 2.0
            weights[SEG_SHARP_LEFT] += 1.5
        elif drift < -80:
            weights[SEG_GENTLE_RIGHT] += 2.0
            weights[SEG_SHARP_RIGHT] += 1.5

        total = sum(weights.values())
        roll = random.random() * total
        cumulative = 0
        for seg_type, w in weights.items():
            cumulative += w
            if roll <= cumulative:
                return seg_type
        return SEG_STRAIGHT

    def _generate_segment(self):
        """Generate one new segment at the current frontier."""
        seg_type = self._pick_segment_type()
        length = random.randint(MIN_SEG_LENGTH, MAX_SEG_LENGTH)
        seg = TrackSegment(seg_type, length, self.current_center_x, self.next_segment_y)

        # Clamp end center to keep track on screen
        seg.center_x_end = max(HALF_TRACK + 20, min(SCREEN_WIDTH - HALF_TRACK - 20,
                                                      seg.center_x_end))

        self.segments.append(seg)
        self.current_center_x = seg.center_x_end
        self.next_segment_y = seg.y_end

    def _generate_initial_segments(self):
        """Fill the screen + a generous buffer ahead with segments."""
        buffer_y = SCREEN_HEIGHT * 3
        while self.next_segment_y < buffer_y:
            self._generate_segment()

    def update(self, scroll_speed):
        """Advance track scroll, generate new segments, cull old ones.

        Args:
            scroll_speed: pixels per frame to scroll the track downward.
        """
        self.scroll_offset += scroll_speed
        self.total_distance += scroll_speed
        self.dash_offset = (self.dash_offset + scroll_speed) % (CENTER_DASH_LEN + CENTER_GAP_LEN)

        # V2+/V3 haze animation
        if self.tier >= 2 and hasattr(self, '_haze_phase'):
            self._haze_phase += scroll_speed * 0.005

        # Update parallax layers
        self.layer_close.update(scroll_speed)
        self.layer_far.update(scroll_speed)

        # Generate ahead: ensure segments extend well past the screen bottom
        visible_bottom = self.scroll_offset + SCREEN_HEIGHT + 400
        while self.next_segment_y < visible_bottom:
            self._generate_segment()

        # Cull segments fully above the screen
        visible_top = self.scroll_offset - 100
        while self.segments and self.segments[0].y_end < visible_top:
            self.segments.pop(0)

    def draw(self, screen):
        """Render the complete track scene to the given surface.

        Draw order:
          1. Far parallax layer (darkest ground)
          2. Close parallax layer (grass/gravel)
          3. Road surface + edges + markings
          4. Rumble strips on curves
          5. Center dashed line
          6. Checkpoints
          7. V2+ overlays
        """
        # 1 & 2: Parallax background layers
        self.layer_far.draw(screen)
        self.layer_close.draw(screen)

        # 3-6: Draw each visible segment
        for seg in self.segments:
            self._draw_segment(screen, seg)

        # 7: V3 holographic overlay or V2 atmosphere overlay
        if self.tier >= 3:
            self._draw_v3_overlay(screen)
        elif self.tier >= 2:
            self._draw_v2_overlay(screen)

    def _draw_segment(self, screen, seg):
        """Draw a single track segment with all its details."""
        # Convert world-y to screen-y
        screen_y_start = seg.y_start - self.scroll_offset
        screen_y_end = seg.y_end - self.scroll_offset

        # Skip if fully off-screen
        if screen_y_end < -10 or screen_y_start > SCREEN_HEIGHT + 10:
            return

        # Draw the segment line by line for smooth curves
        step = 3  # pixel step for scanline rendering
        prev_cx = None

        y = max(0, int(screen_y_start))
        y_end_clamped = min(SCREEN_HEIGHT, int(screen_y_end))

        while y < y_end_clamped:
            # Local parametric position within segment
            if seg.length > 0:
                local_t = (y - screen_y_start) / (screen_y_end - screen_y_start)
                local_t = max(0.0, min(1.0, local_t))
            else:
                local_t = 0.0

            cx = seg.get_center_x(local_t)

            left = int(cx - HALF_TRACK)
            right = int(cx + HALF_TRACK)

            # Road surface — V3: deep black holo base; V2: alternate shades
            if self.tier >= 3:
                pygame.draw.line(screen, (2, 3, 8), (left, y), (right, y))
            elif self.tier >= 2:
                world_y = y + self.scroll_offset
                if int(world_y) % 6 < 3:
                    road_col = (30, 28, 42)
                else:
                    road_col = (38, 35, 50)
                pygame.draw.line(screen, road_col, (left, y), (right, y))
            else:
                pygame.draw.line(screen, ROAD_COLOR, (left, y), (right, y))

            # Road edges (neon cyan lines)
            pygame.draw.line(screen, ROAD_EDGE_COLOR, (left, y), (left + 2, y), 3)
            pygame.draw.line(screen, ROAD_EDGE_COLOR, (right - 2, y), (right, y), 3)

            # V2+: Edge glow (every 2nd scanline)
            if self.tier >= 2 and y % 2 == 0:
                if self.tier >= 3 and hasattr(self, '_edge_glow_strip'):
                    # V3: pre-baked strips (perf fix: no per-scanline Surface alloc)
                    screen.blit(self._edge_glow_strip, (left - 4, y))
                    screen.blit(self._edge_glow_strip, (right - 4, y))
                    screen.blit(self._edge_glow_wide, (left - 7, y))
                    screen.blit(self._edge_glow_wide, (right - 7, y))
                else:
                    edge_s = pygame.Surface((6, 1), pygame.SRCALPHA)
                    edge_s.fill((*ROAD_EDGE_COLOR[:3], 40))
                    screen.blit(edge_s, (left - 3, y))
                    screen.blit(edge_s, (right - 3, y))
                    edge_s2 = pygame.Surface((10, 1), pygame.SRCALPHA)
                    edge_s2.fill((*ROAD_EDGE_COLOR[:3], 15))
                    screen.blit(edge_s2, (left - 5, y))
                    screen.blit(edge_s2, (right - 5, y))

            # Rumble strips on outside of curves
            if seg.rumble_side and seg.seg_type not in (SEG_STRAIGHT,):
                rumble_block = 6
                world_y = y + self.scroll_offset
                rumble_idx = int(world_y / rumble_block) % 2
                rumble_color = RUMBLE_RED if rumble_idx == 0 else RUMBLE_WHITE

                if seg.rumble_side in ("left", "both"):
                    pygame.draw.line(screen, rumble_color, (left - 6, y), (left, y), 6)
                if seg.rumble_side in ("right", "both"):
                    pygame.draw.line(screen, rumble_color, (right, y), (right + 6, y), 6)

            # Center dashed line
            world_y = y + self.scroll_offset
            dash_pos = (world_y + self.dash_offset) % (CENTER_DASH_LEN + CENTER_GAP_LEN)
            if dash_pos < CENTER_DASH_LEN:
                icx = int(cx)
                pygame.draw.line(screen, CENTER_LINE_COLOR, (icx - 1, y), (icx + 1, y), 2)

            # V2+: Track edge pulse flash every ~200 world-px
            if self.tier >= 2:
                world_y = y + self.scroll_offset
                pulse_phase = world_y % 200
                if pulse_phase < 30:
                    flash_a = int(60 * (1 - pulse_phase / 30))
                    fs = pygame.Surface((4, 1), pygame.SRCALPHA)
                    fs.fill((255, 0, 120, flash_a))
                    screen.blit(fs, (left - 2, y))
                    screen.blit(fs, (right - 2, y))

            prev_cx = cx
            y += step

        # Checkpoints: draw at every CHECKPOINT_INTERVAL within this segment
        first_cp = int(math.ceil(seg.y_start / CHECKPOINT_INTERVAL)) * CHECKPOINT_INTERVAL
        cp_y = first_cp
        while cp_y < seg.y_end:
            cp_screen_y = cp_y - self.scroll_offset
            if 0 <= cp_screen_y < SCREEN_HEIGHT:
                if seg.length > 0:
                    local_t = (cp_y - seg.y_start) / seg.length
                    local_t = max(0.0, min(1.0, local_t))
                else:
                    local_t = 0.0
                cp_cx = seg.get_center_x(local_t)
                cp_left = int(cp_cx - HALF_TRACK - 10)
                screen.blit(self.checkpoint_surf, (cp_left, int(cp_screen_y) - 4))
            cp_y += CHECKPOINT_INTERVAL

    def _draw_v2_overlay(self, screen):
        """V2+ visual enhancements: atmosphere fog, oil stains, tire marks, enhanced rumble."""
        # Pulsing atmosphere fog overlay — PERF FIX: reuse pre-allocated surface
        haze_alpha = int(10 + 6 * math.sin(self._haze_phase))
        self._haze_surf.fill((18, 15, 22, haze_alpha))
        screen.blit(self._haze_surf, (0, 0))

        # Oil stains + tire marks on visible road segments
        mark_color = (35, 33, 30)
        oil_color = (25, 22, 28)
        rng = random.Random(42)  # deterministic per draw for stability
        for seg in self.segments:
            sy_start = seg.y_start - self.scroll_offset
            sy_end = seg.y_end - self.scroll_offset
            if sy_end < 0 or sy_start > SCREEN_HEIGHT:
                continue

            # Oil stains: 3-5 dark circles per segment (seeded by segment y_start)
            seg_rng = random.Random(int(seg.y_start) ^ 0xDEAD)
            num_stains = seg_rng.randint(3, 5)
            for _ in range(num_stains):
                local_t = seg_rng.uniform(0.1, 0.9)
                cx = seg.get_center_x(local_t)
                oy = sy_start + local_t * (sy_end - sy_start)
                if 0 <= oy < SCREEN_HEIGHT:
                    ox = int(cx + seg_rng.randint(-HALF_TRACK + 15, HALF_TRACK - 15))
                    r = seg_rng.randint(4, 10)
                    oil_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                    pygame.draw.ellipse(oil_surf, (*oil_color, 60),
                                        (0, 0, r * 2, r * 2))
                    screen.blit(oil_surf, (ox - r, int(oy) - r))

            # Tire marks
            for offset_ratio, length, angle in self._tire_marks:
                local_t = 0.5
                cx = seg.get_center_x(local_t)
                mx = int(cx + offset_ratio * HALF_TRACK)
                my = int((sy_start + sy_end) / 2)
                if 0 <= my < SCREEN_HEIGHT:
                    ex = mx + int(math.sin(angle) * length)
                    ey = my + int(math.cos(angle) * length)
                    pygame.draw.line(screen, mark_color, (mx, my), (ex, ey), 2)

            # Enhanced rumble strips on curves: inner highlight line
            if seg.rumble_side and seg.seg_type not in (SEG_STRAIGHT,):
                step = 6
                for y in range(max(0, int(sy_start)), min(SCREEN_HEIGHT, int(sy_end)), step):
                    if seg.length > 0:
                        lt = (y - sy_start) / (sy_end - sy_start)
                        lt = max(0.0, min(1.0, lt))
                    else:
                        lt = 0.0
                    cx = seg.get_center_x(lt)
                    left = int(cx - HALF_TRACK)
                    right = int(cx + HALF_TRACK)
                    # Color-cycle at 2x speed
                    world_y = y + self.scroll_offset
                    ridx = int(world_y / 3) % 2
                    hl_color = (255, 80, 80) if ridx == 0 else (255, 255, 255)
                    if seg.rumble_side in ("left", "both"):
                        pygame.draw.line(screen, (*hl_color[:3],), (left - 4, y), (left - 3, y), 1)
                    if seg.rumble_side in ("right", "both"):
                        pygame.draw.line(screen, (*hl_color[:3],), (right + 3, y), (right + 4, y), 1)

    def _draw_v3_overlay(self, screen):
        """V3 holographic overlay: grid blit per road segment, data wave sweeps."""
        # Holo grid tile blit over each visible road segment
        if hasattr(self, '_holo_tile'):
            tile_h = self._holo_tile.get_height()
            tile_w = self._holo_tile.get_width()
            for seg in self.segments:
                sy_start = seg.y_start - self.scroll_offset
                sy_end = seg.y_end - self.scroll_offset
                if sy_end < 0 or sy_start > SCREEN_HEIGHT:
                    continue
                # Blit grid tile at segment midpoint
                mid_t = 0.5
                cx = seg.get_center_x(mid_t)
                mid_y = (sy_start + sy_end) / 2
                left = int(cx - HALF_TRACK)
                for ty in range(max(0, int(sy_start)), min(SCREEN_HEIGHT, int(sy_end)), tile_h):
                    lt = (ty - sy_start) / max(1, sy_end - sy_start)
                    lt = max(0.0, min(1.0, lt))
                    seg_cx = seg.get_center_x(lt)
                    seg_left = int(seg_cx - HALF_TRACK)
                    # Clip to road width
                    clip_w = min(tile_w, TRACK_WIDTH)
                    screen.blit(self._holo_tile, (seg_left, ty),
                                (0, 0, clip_w, min(tile_h, int(sy_end) - ty)),
                                special_flags=pygame.BLEND_RGB_ADD)

        # Data wave sweeps (max 3 active, horizontal bright lines)
        if hasattr(self, '_data_waves'):
            self._data_wave_cooldown = max(0, self._data_wave_cooldown - 1)
            if len(self._data_waves) < 3 and random.random() < 0.01 and self._data_wave_cooldown <= 0:
                self._data_waves.append({
                    'y': -5,
                    'speed': random.uniform(3, 6),
                    'color': random.choice([(0, 200, 255), (0, 255, 180), (100, 200, 255)]),
                })
                self._data_wave_cooldown = 60

            alive_waves = []
            for wave in self._data_waves:
                wave['y'] += wave['speed']
                if wave['y'] < SCREEN_HEIGHT:
                    alive_waves.append(wave)
                    wy = int(wave['y'])
                    # Draw sweep line across all visible road segments
                    for seg in self.segments:
                        sy_start = seg.y_start - self.scroll_offset
                        sy_end = seg.y_end - self.scroll_offset
                        if sy_start <= wy <= sy_end and seg.length > 0:
                            lt = (wy - sy_start) / max(1, sy_end - sy_start)
                            lt = max(0.0, min(1.0, lt))
                            seg_cx = seg.get_center_x(lt)
                            left = int(seg_cx - HALF_TRACK)
                            right = int(seg_cx + HALF_TRACK)
                            pygame.draw.line(screen, wave['color'], (left, wy), (right, wy), 2)
                            # Fainter echo lines
                            for offset in [2, 4]:
                                a_line = max(0, wy - offset)
                                if a_line >= 0:
                                    pygame.draw.line(screen, (*wave['color'][:3],),
                                                     (left, a_line), (right, a_line), 1)
                            break
            self._data_waves = alive_waves

        # Subtle V3 atmosphere (no fog — just faint haze)
        if hasattr(self, '_haze_surf'):
            self._haze_surf.fill((0, 8, 12, 6))
            screen.blit(self._haze_surf, (0, 0))
