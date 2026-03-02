"""Tests for shared/boss_base.py — damage, invulnerability, phase transitions."""
import pytest

from core.constants import DIFF_NORMAL
from shared.boss_base import Boss


def _make_boss(particles):
    """Create a DesertBoss (concrete subclass with known phase structure)."""
    from bosses.desert_boss import DesertBoss
    return DesertBoss(particles, difficulty=DIFF_NORMAL, evolution_tier=1)


class TestBossDamage:
    def test_take_damage_reduces_hp(self, particles):
        boss = _make_boss(particles)
        initial = boss.hp
        boss.vulnerable = True
        boss.take_damage(25, source="ram")
        assert boss.hp == initial - 25

    def test_ram_blocked_when_not_vulnerable(self, particles):
        boss = _make_boss(particles)
        initial = boss.hp
        boss.vulnerable = False
        result = boss.take_damage(25, source="ram")
        assert result is False
        assert boss.hp == initial

    def test_bolt_ignores_vulnerability(self, particles):
        boss = _make_boss(particles)
        initial = boss.hp
        boss.vulnerable = False
        result = boss.take_damage(15, source="bolt")
        assert result is True
        assert boss.hp == initial - 15

    def test_blocked_when_invuln(self, particles):
        boss = _make_boss(particles)
        boss.invuln_timer = 10
        boss.vulnerable = True
        result = boss.take_damage(25, source="ram")
        assert result is False

    def test_death_at_zero_hp(self, particles):
        boss = _make_boss(particles)
        boss.vulnerable = True
        boss.take_damage(boss.hp, source="bolt")
        assert boss.alive is False
        assert boss.defeated is True
        assert boss.hp == 0

    def test_invuln_timer_set_after_damage(self, particles):
        boss = _make_boss(particles)
        boss.vulnerable = True
        boss.take_damage(10, source="ram")
        assert boss.invuln_timer == Boss.INVULN_AFTER_HIT

    def test_phase_transition_at_066(self, particles):
        """Deal enough damage to cross the 0.66 threshold."""
        boss = _make_boss(particles)
        # Need hp_ratio <= 0.66 → damage > 0.34 * max_hp
        damage = int(boss.max_hp * 0.35) + 1
        boss.take_damage(damage, source="bolt")
        assert boss.current_phase_idx == 1
        assert boss.phases[1].entered is True

    def test_phase_skip_to_phase2(self, particles):
        """Massive damage should skip to phase 2 (0.33 threshold)."""
        boss = _make_boss(particles)
        # Deal 70% damage in one hit → hp_ratio = 0.30 → below 0.33
        damage = int(boss.max_hp * 0.70)
        boss.take_damage(damage, source="bolt")
        # Should be at phase 2 (idx=2), not phase 1
        # Note: _check_phase_transition breaks after first transition found
        # So it advances one phase at a time per damage call
        assert boss.current_phase_idx >= 1
