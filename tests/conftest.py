"""Shared fixtures for NEON RUSH test suite.

Provides headless pygame init, mock sound, mock particles, and mock shake
so that tests can import game modules without needing a display or audio.
"""
import sys
import os
import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Force headless SDL drivers BEFORE any pygame import
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


@pytest.fixture(scope="session", autouse=True)
def pygame_headless():
    """Initialize pygame with a tiny headless display (session-scoped).

    Many modules create Surfaces at import time, so this must run first.
    """
    import pygame
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.NOFRAME)
    yield
    pygame.quit()


@pytest.fixture(autouse=True)
def mock_sound(monkeypatch):
    """Silence all sound effects during tests."""
    import core.sound as snd
    monkeypatch.setattr(snd, "play_sfx", lambda name: None)


@pytest.fixture
def particles():
    """Mock particle system with .emit() and .burst() stubs."""
    class MockParticles:
        def emit(self, *a, **kw):
            pass

        def burst(self, *a, **kw):
            pass

    return MockParticles()


@pytest.fixture
def shake():
    """Mock screen-shake with .trigger() stub."""
    class MockShake:
        def trigger(self, *a, **kw):
            pass

    return MockShake()
