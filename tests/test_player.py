"""Tests for sprites/vehicle.py — Player timer decrements and shield absorption."""
import pygame
import pytest

from core.constants import DIFF_NORMAL
from sprites.vehicle import Player


def _make_player(particles):
    """Create a Player with default settings."""
    return Player(particles, player_num=1, solo=True, diff=DIFF_NORMAL, tier=1)


class TestPlayerTimers:
    def test_shield_timer_decrements(self, particles):
        p = _make_player(particles)
        p.shield = True
        p.shield_timer = 1
        keys = pygame.key.get_pressed()  # all False
        p.update(keys)
        assert p.shield is False
        assert p.shield_timer == 0

    def test_magnet_timer_decrements(self, particles):
        p = _make_player(particles)
        p.magnet = True
        p.magnet_timer = 1
        keys = pygame.key.get_pressed()
        p.update(keys)
        assert p.magnet is False
        assert p.magnet_timer == 0

    def test_shield_absorbs_hit(self, particles, shake):
        p = _make_player(particles)
        p.shield = True
        p.shield_timer = 100
        initial_lives = p.lives
        result = p.take_hit(shake)
        assert result is False  # shield absorbed
        assert p.lives == initial_lives
        assert p.shield is False

    def test_surge_maintains_speed(self, particles):
        p = _make_player(particles)
        p.surge = True
        p.surge_timer = 5
        p.speed = 2.0  # low speed
        keys = pygame.key.get_pressed()
        p.update(keys)
        assert p.speed >= 20  # surge forces speed >= 20

    def test_all_timers_clear(self, particles):
        """Set all 7 powerup timers to 1, one update should clear all flags."""
        p = _make_player(particles)
        p.shield = True
        p.shield_timer = 1
        p.magnet = True
        p.magnet_timer = 1
        p.slowmo = True
        p.slowmo_timer = 1
        p.phase = True
        p.phase_timer = 1
        p.surge = True
        p.surge_timer = 1
        p.multishot = True
        p.multishot_timer = 1
        p.orbit8 = True
        p.orbit8_timer = 1

        keys = pygame.key.get_pressed()
        p.update(keys)

        assert p.shield is False
        assert p.magnet is False
        assert p.slowmo is False
        assert p.phase is False
        assert p.surge is False
        assert p.multishot is False
        assert p.orbit8 is False
