"""Tests for boss phase structures — verify _build_phases() for each boss."""
import pytest

from core.constants import DIFF_NORMAL


class TestDesertBossPhases:
    def test_phase_structure(self, particles):
        from bosses.desert_boss import DesertBoss
        boss = DesertBoss(particles, difficulty=DIFF_NORMAL, evolution_tier=1)
        phases = boss.phases

        assert len(phases) == 3
        assert phases[0].hp_threshold == 1.0
        assert phases[1].hp_threshold == 0.66
        assert phases[2].hp_threshold == 0.33
        assert len(phases[0].attacks) == 3
        assert len(phases[1].attacks) == 4
        assert len(phases[2].attacks) == 5


class TestExcitebikeBossPhases:
    def test_phase_structure(self, particles):
        from bosses.excitebike_boss import ExcitebikeBoss
        boss = ExcitebikeBoss(particles, evolution_tier=1)
        phases = boss.phases

        assert len(phases) == 3
        assert phases[0].hp_threshold == 1.0
        assert phases[1].hp_threshold == 0.66
        assert phases[2].hp_threshold == 0.33
        assert len(phases[0].attacks) == 2
        assert len(phases[1].attacks) == 4
        assert len(phases[2].attacks) == 5


class TestMicromachinesBossPhases:
    def test_phase_structure(self, particles):
        from bosses.micromachines_boss import MicroMachinesBoss
        boss = MicroMachinesBoss(particles, evolution_tier=1)
        phases = boss.phases

        assert len(phases) == 3
        assert phases[0].hp_threshold == 1.0
        assert phases[1].hp_threshold == 0.66
        assert phases[2].hp_threshold == 0.33
        assert len(phases[0].attacks) == 2
        assert len(phases[1].attacks) == 4
        assert len(phases[2].attacks) == 6

    def test_max_hp_350(self, particles):
        from bosses.micromachines_boss import MicroMachinesBoss
        boss = MicroMachinesBoss(particles, evolution_tier=1)
        assert boss.max_hp == 350
