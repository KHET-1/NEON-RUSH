"""RoadSpriteMixin — perspective projection for sprites on the pseudo-3D road.

Gives any sprite world-Z positioning and perspective scaling so objects
appear at the horizon and grow as they approach the camera.
"""
import logging
import pygame

log = logging.getLogger("neon_rush.road_sprite")


# Quantized scale levels to avoid per-frame smoothscale overhead
_SCALE_LEVELS = 25
_SCALE_CACHE = {}  # keyed by (id(original_surface), scale_level)


def _get_scale_level(scale):
    """Quantize scale to one of _SCALE_LEVELS discrete levels."""
    level = int(scale * _SCALE_LEVELS)
    return max(1, min(level, _SCALE_LEVELS))


def _get_scaled_surface(original, scale):
    """Return a cached scaled version of the surface."""
    level = _get_scale_level(scale)
    key = (id(original), level)
    cached = _SCALE_CACHE.get(key)
    if cached is not None:
        return cached

    actual_scale = level / _SCALE_LEVELS
    w = max(1, int(original.get_width() * actual_scale))
    h = max(1, int(original.get_height() * actual_scale))
    scaled = pygame.transform.scale(original, (w, h))
    _SCALE_CACHE[key] = scaled

    # Evict old entries if cache gets too large
    if len(_SCALE_CACHE) > 500:
        # Keep only the most recent half
        keys = list(_SCALE_CACHE.keys())
        for k in keys[:250]:
            del _SCALE_CACHE[k]

    return scaled


class RoadSpriteMixin:
    """Mixin that adds pseudo-3D road projection to a pygame Sprite.

    Usage:
        class MySprite(RoadSpriteMixin, pygame.sprite.Sprite):
            def __init__(self):
                super().__init__()
                self.init_road(world_z=500.0, lane_offset=0.3)

    The sprite must have self.image and self.rect already set.
    """

    def init_road(self, world_z, lane_offset=0.0):
        """Initialize road projection state.

        Args:
            world_z: starting distance from camera in world units
            lane_offset: -1.0 (left edge) to +1.0 (right edge)
        """
        self.world_z = world_z
        self.lane_offset = lane_offset
        self._original_image = self.image.copy()
        self._projected = False  # True once successfully projected
        self._road_scale = 1.0

    def advance_toward_camera(self, speed):
        """Move sprite closer to camera by speed amount."""
        self.world_z -= speed * 0.15  # match camera advance rate

    def project(self, road_geometry):
        """Project this sprite onto the screen using road geometry.

        Updates self.image (scaled), self.rect (positioned), and self._projected.
        Returns True if visible, False if should be killed.
        """
        result = road_geometry.get_sprite_projection(self.world_z, self.lane_offset)

        if result is None:
            self._projected = False
            # Behind camera or too far — kill
            if self.world_z <= 0:
                return False
            # Too far away — hide but keep alive
            self.rect.topleft = (-999, -999)
            return True

        screen_x, screen_y, scale, visible = result

        if not visible or scale < 0.02:
            self._projected = False
            self.rect.topleft = (-999, -999)
            return True

        self._road_scale = scale
        self._projected = True

        # Scale the sprite image
        scaled = _get_scaled_surface(self._original_image, scale)
        self.image = scaled
        self.rect = scaled.get_rect(center=(int(screen_x), int(screen_y)))

        return True
