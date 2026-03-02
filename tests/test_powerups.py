"""Tests for shared/powerup_handler.py — apply_powerup() effects."""
import pytest

from core.constants import (
    POWERUP_SHIELD, POWERUP_MAGNET, POWERUP_SLOWMO,
    POWERUP_PHASE, POWERUP_SURGE, POWERUP_COLORS,
)
from shared.powerup_handler import apply_powerup


class MockPowerup:
    """Mock powerup sprite with .kind and .rect."""
    def __init__(self, kind):
        self.kind = kind


class MockPlayer:
    """Mock player with all powerup-related attributes."""
    def __init__(self):
        self.shield = False
        self.shield_timer = 0
        self.magnet = False
        self.magnet_timer = 0
        self.slowmo = False
        self.slowmo_timer = 0
        self.phase = False
        self.phase_timer = 0
        self.surge = False
        self.surge_timer = 0
        self.invincible_timer = 0
        self.speed = 5.0
        self.score = 0
        self.score_mult = 1

        import pygame
        self.rect = pygame.Rect(100, 100, 40, 60)


class MockMode:
    """Mock game mode with particles, shake, floating_texts."""
    def __init__(self):
        self.floating_texts = []
        self._surge_speed = 15

    class particles:
        @staticmethod
        def burst(*a, **kw):
            pass

    class shake:
        @staticmethod
        def trigger(*a, **kw):
            pass


class TestApplyPowerup:
    def test_shield(self):
        player = MockPlayer()
        mode = MockMode()
        apply_powerup(player, MockPowerup(POWERUP_SHIELD), mode)
        assert player.shield is True
        assert player.shield_timer == 600

    def test_magnet(self):
        player = MockPlayer()
        mode = MockMode()
        apply_powerup(player, MockPowerup(POWERUP_MAGNET), mode)
        assert player.magnet is True
        assert player.magnet_timer == 480

    def test_slowmo(self):
        player = MockPlayer()
        mode = MockMode()
        apply_powerup(player, MockPowerup(POWERUP_SLOWMO), mode)
        assert player.slowmo is True
        assert player.slowmo_timer == 300

    def test_phase(self):
        player = MockPlayer()
        mode = MockMode()
        apply_powerup(player, MockPowerup(POWERUP_PHASE), mode)
        assert player.phase is True
        assert player.phase_timer == 360

    def test_surge(self):
        player = MockPlayer()
        mode = MockMode()
        apply_powerup(player, MockPowerup(POWERUP_SURGE), mode)
        assert player.surge is True
        assert player.surge_timer == 180
        assert player.speed == 15

    def test_score_always_added(self):
        player = MockPlayer()
        player.score_mult = 2
        mode = MockMode()
        apply_powerup(player, MockPowerup(POWERUP_SHIELD), mode)
        assert player.score == 200  # 100 * score_mult(2)
