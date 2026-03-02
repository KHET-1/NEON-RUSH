"""Centralized powerup collection logic shared across all 3 game modes.

Each mode calls apply_powerup() when a player picks up a powerup sprite.
Nuke behavior differs per mode — pass nukeable_groups dict for mode-specific targets.
"""
from core.constants import (
    POWERUP_SHIELD, POWERUP_MAGNET, POWERUP_SLOWMO,
    POWERUP_NUKE, POWERUP_PHASE, POWERUP_SURGE,
    POWERUP_MULTISHOT, POWERUP_ROCKETS, POWERUP_ORBIT8,
    POWERUP_COLORS, NUKE_ORANGE, SOLAR_YELLOW,
)
from core.sound import play_sfx
from core.hud import FloatingText


def apply_powerup(player, powerup, mode):
    """Activate a powerup on a player.

    Args:
        player: The player who collected the powerup.
        powerup: The PowerUp sprite (has .kind attribute).
        mode: The GameMode instance (provides .particles, .shake, .asteroids,
              .asteroids_cleared, .floating_texts, and nuke target groups).
    """
    kind = powerup.kind

    if kind == POWERUP_SHIELD:
        player.shield = True
        player.shield_timer = 600
    elif kind == POWERUP_MAGNET:
        player.magnet = True
        player.magnet_timer = 480
    elif kind == POWERUP_SLOWMO:
        player.slowmo = True
        player.slowmo_timer = 300
    elif kind == POWERUP_NUKE:
        _apply_nuke(player, mode)
    elif kind == POWERUP_PHASE:
        player.phase = True
        player.phase_timer = 360
        play_sfx("phase")
    elif kind == POWERUP_SURGE:
        player.surge = True
        player.surge_timer = 180
        player.speed = getattr(mode, '_surge_speed', 15)
        player.invincible_timer = max(player.invincible_timer, 180)
        play_sfx("surge")
    elif kind == POWERUP_MULTISHOT:
        player.multishot = True
        player.multishot_timer = 360
        play_sfx("powerup")
    elif kind == POWERUP_ROCKETS:
        player.rockets = True
        player.rockets_timer = 480
        player.rocket_fire_cd = 0
        play_sfx("rocket_launch")
    elif kind == POWERUP_ORBIT8:
        player.orbit8 = True
        player.orbit8_timer = 600
        player._orbit8_spawn_pending = True
        play_sfx("orb_hit")

    # Score + particles + floating text (all powerups)
    pts = 100 * player.score_mult
    player.score += pts
    mode.particles.burst(player.rect.centerx, player.rect.centery,
                         [POWERUP_COLORS[kind]], 6, 3, 20, 3)
    mode.floating_texts.append(
        FloatingText(player.rect.centerx, player.rect.top - 15,
                     f"+{pts}", POWERUP_COLORS[kind]))

    # Sound (nuke/phase/surge have their own)
    if kind not in (POWERUP_NUKE, POWERUP_PHASE, POWERUP_SURGE,
                     POWERUP_MULTISHOT, POWERUP_ROCKETS, POWERUP_ORBIT8):
        play_sfx("powerup")


def _apply_nuke(player, mode):
    """Screen-clear nuke — destroys mode-specific obstacle groups + asteroids."""
    # Each mode provides get_nukeable_groups() → list of sprite groups to nuke
    nuke_groups = mode.get_nukeable_groups()
    for group in nuke_groups:
        for sprite in list(group):
            mode.particles.burst(sprite.rect.centerx, sprite.rect.centery,
                                 [NUKE_ORANGE, SOLAR_YELLOW], 8, 4, 25, 2)
            player.score += 50 * player.score_mult
            sprite.kill()

    # Always nuke asteroids too
    for ast in list(mode.asteroids):
        mode.particles.burst(*ast.get_death_particles())
        player.score += ast.points * player.score_mult
        mode.asteroids_cleared += 1
        ast.kill()

    mode.shake.trigger(8, 20)
    mode.screen_flash = 20
    play_sfx("nuke")
