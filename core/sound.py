import pygame
import math
import random
import array


def generate_tone(frequency, duration_ms, volume=0.3, wave="square"):
    sample_rate = 44100
    n_samples = int(sample_rate * duration_ms / 1000)
    buf = array.array("h", [0] * n_samples)
    max_amp = int(32767 * volume)
    fade_start = int(n_samples * 0.8)
    for i in range(n_samples):
        t = i / sample_rate
        if wave == "square":
            val = max_amp if math.sin(2 * math.pi * frequency * t) > 0 else -max_amp
        elif wave == "sine":
            val = int(max_amp * math.sin(2 * math.pi * frequency * t))
        elif wave == "noise":
            val = random.randint(-max_amp, max_amp)
        else:
            val = 0
        if i > fade_start:
            val = int(val * (n_samples - i) / (n_samples - fade_start))
        buf[i] = max(-32768, min(32767, val))
    return pygame.mixer.Sound(buffer=buf)


def generate_sweep(freq_start, freq_end, duration_ms, volume=0.3):
    sample_rate = 44100
    n_samples = int(sample_rate * duration_ms / 1000)
    buf = array.array("h", [0] * n_samples)
    max_amp = int(32767 * volume)
    fade_start = int(n_samples * 0.7)
    for i in range(n_samples):
        t = i / sample_rate
        progress = i / n_samples
        freq = freq_start + (freq_end - freq_start) * progress
        val = int(max_amp * math.sin(2 * math.pi * freq * t))
        if i > fade_start:
            val = int(val * (n_samples - i) / (n_samples - fade_start))
        buf[i] = max(-32768, min(32767, val))
    return pygame.mixer.Sound(buffer=buf)


def generate_sub_bass(freq=40, duration_ms=300, volume=0.20, harmonics=2):
    """Generate sub-bass tone with harmonic series. freq=30-60Hz for chest rumble."""
    sample_rate = 44100
    n_samples = int(sample_rate * duration_ms / 1000)
    buf = array.array("h", [0] * n_samples)
    fade_start = int(n_samples * 0.6)
    for i in range(n_samples):
        t = i / sample_rate
        val = 0.0
        for h in range(harmonics):
            amp = 1.0 / (h + 1)
            val += amp * math.sin(2 * math.pi * freq * (h + 1) * t)
        val = int(32767 * volume * val / harmonics)
        if i > fade_start:
            val = int(val * (n_samples - i) / (n_samples - fade_start))
        buf[i] = max(-32768, min(32767, val))
    return pygame.mixer.Sound(buffer=buf)


def generate_bass_drop(freq_start=60, freq_end=25, duration_ms=500, volume=0.22):
    """Descending sub-bass sweep — the 'drop' feeling."""
    sample_rate = 44100
    n_samples = int(sample_rate * duration_ms / 1000)
    buf = array.array("h", [0] * n_samples)
    fade_start = int(n_samples * 0.7)
    for i in range(n_samples):
        t = i / sample_rate
        progress = i / n_samples
        freq = freq_start + (freq_end - freq_start) * progress
        val = int(32767 * volume * math.sin(2 * math.pi * freq * t))
        if i > fade_start:
            val = int(val * (n_samples - i) / (n_samples - fade_start))
        buf[i] = max(-32768, min(32767, val))
    return pygame.mixer.Sound(buffer=buf)


def make_engine_sound():
    sample_rate = 44100
    n_samples = int(sample_rate * 0.5)
    buf = array.array("h", [0] * n_samples)
    for i in range(n_samples):
        t = i / sample_rate
        val = int(
            800 * math.sin(2 * math.pi * 80 * t)
            + 400 * math.sin(2 * math.pi * 160 * t)
            + 200 * math.sin(2 * math.pi * 240 * t)
        )
        buf[i] = max(-32768, min(32767, val))
    return pygame.mixer.Sound(buffer=buf)


def make_desert_music():
    """Desert mode: minor pentatonic, 140 BPM — smooth sine melody (no beeping)."""
    sample_rate = 44100
    bpm = 140
    beat = 60 / bpm
    notes = [
        220, 261, 293, 349, 392,
        440, 523, 587, 698, 784,
    ]
    melody = [0, 2, 4, 5, 4, 2, 3, 1, 0, 4, 5, 9, 7, 5, 4, 2]
    bass_pattern = [0, 0, 3, 3, 5, 5, 2, 2, 0, 0, 3, 3, 5, 5, 4, 4]
    total_beats = len(melody)
    n_samples = int(sample_rate * beat * total_beats)
    buf = array.array("h", [0] * n_samples)
    samples_per_beat = int(sample_rate * beat)

    for beat_idx in range(total_beats):
        mel_freq = notes[melody[beat_idx]]
        bass_freq = notes[bass_pattern[beat_idx]] / 2
        start = beat_idx * samples_per_beat
        for i in range(samples_per_beat):
            t = i / sample_rate
            env = max(0, 1.0 - (i / samples_per_beat) * 0.7)
            # Sine wave melody — smooth, no beeping
            mel = 500 * env * math.sin(2 * math.pi * mel_freq * t)
            # Soft triangle bass
            bass_phase = (bass_freq * t) % 1.0
            bass = 400 * env * (abs(bass_phase - 0.5) * 4 - 1)
            # Quieter hi-hat
            hat = 120 * max(0, 1.0 - i / (samples_per_beat * 0.04)) * random.uniform(-1, 1) if i < samples_per_beat * 0.04 else 0
            val = int(mel + bass + hat)
            idx = start + i
            if idx < n_samples:
                buf[idx] = max(-32768, min(32767, val))
    return pygame.mixer.Sound(buffer=buf)


def make_excitebike_music():
    """Excitebike mode: major pentatonic, 160 BPM, upbeat arcade feel."""
    sample_rate = 44100
    bpm = 160
    beat = 60 / bpm
    # C major pentatonic
    notes = [
        262, 294, 330, 392, 440,
        523, 587, 659, 784, 880,
    ]
    melody = [0, 4, 5, 7, 5, 4, 2, 0, 4, 7, 9, 7, 5, 4, 2, 0]
    bass_pattern = [0, 0, 2, 2, 4, 4, 0, 0, 2, 2, 4, 4, 5, 5, 0, 0]
    total_beats = len(melody)
    n_samples = int(sample_rate * beat * total_beats)
    buf = array.array("h", [0] * n_samples)
    samples_per_beat = int(sample_rate * beat)

    for beat_idx in range(total_beats):
        mel_freq = notes[melody[beat_idx]]
        bass_freq = notes[bass_pattern[beat_idx]] / 2
        start = beat_idx * samples_per_beat
        for i in range(samples_per_beat):
            t = i / sample_rate
            env = max(0, 1.0 - (i / samples_per_beat) * 0.6)
            # Bright saw wave for melody
            mel_phase = (mel_freq * t) % 1.0
            mel = 700 * env * (mel_phase * 2 - 1)
            # Punchy bass
            bass_phase = (bass_freq * t) % 1.0
            bass = 500 * env * (1 if bass_phase < 0.5 else -1)
            # Snappier hi-hat
            hat = 300 * max(0, 1.0 - i / (samples_per_beat * 0.04)) * random.uniform(-1, 1) if i < samples_per_beat * 0.04 else 0
            # Kick on every other beat
            kick = 0
            if beat_idx % 2 == 0 and i < samples_per_beat * 0.08:
                kick_env = max(0, 1.0 - i / (samples_per_beat * 0.08))
                kick = 600 * kick_env * math.sin(2 * math.pi * (120 - 80 * (i / (samples_per_beat * 0.08))) * t)
            val = int(mel + bass + hat + kick)
            idx = start + i
            if idx < n_samples:
                buf[idx] = max(-32768, min(32767, val))
    return pygame.mixer.Sound(buffer=buf)


def make_micromachines_music():
    """Micro Machines mode: chromatic, 180 BPM, intense chiptune."""
    sample_rate = 44100
    bpm = 180
    beat = 60 / bpm
    # Chromatic tension scale
    notes = [
        247, 262, 277, 294, 311, 330, 349, 370, 392, 415, 440, 466,
        494, 523, 554, 587,
    ]
    melody = [0, 3, 5, 8, 11, 8, 5, 3, 12, 11, 8, 5, 3, 5, 8, 0]
    bass_pattern = [0, 0, 5, 5, 8, 8, 3, 3, 0, 0, 5, 5, 8, 8, 11, 11]
    total_beats = len(melody)
    n_samples = int(sample_rate * beat * total_beats)
    buf = array.array("h", [0] * n_samples)
    samples_per_beat = int(sample_rate * beat)

    for beat_idx in range(total_beats):
        mel_freq = notes[melody[beat_idx]]
        bass_freq = notes[bass_pattern[beat_idx]] / 2
        start = beat_idx * samples_per_beat
        for i in range(samples_per_beat):
            t = i / sample_rate
            env = max(0, 1.0 - (i / samples_per_beat) * 0.5)
            # Aggressive pulse wave
            duty = 0.3 + 0.2 * math.sin(beat_idx * 0.5)
            mel_phase = (mel_freq * t) % 1.0
            mel = 650 * env * (1 if mel_phase < duty else -1)
            # Distorted bass
            bass = 550 * env * math.sin(2 * math.pi * bass_freq * t)
            bass = max(-550, min(550, bass * 1.5))  # Clip for grit
            # Fast hi-hat
            hat = 250 * max(0, 1.0 - i / (samples_per_beat * 0.03)) * random.uniform(-1, 1) if i < samples_per_beat * 0.03 else 0
            # Kick every beat
            kick = 0
            if i < samples_per_beat * 0.06:
                kick_env = max(0, 1.0 - i / (samples_per_beat * 0.06))
                kick = 500 * kick_env * math.sin(2 * math.pi * (150 - 100 * (i / (samples_per_beat * 0.06))) * t)
            val = int(mel + bass + hat + kick)
            idx = start + i
            if idx < n_samples:
                buf[idx] = max(-32768, min(32767, val))
    return pygame.mixer.Sound(buffer=buf)


def make_boss_desert_music():
    """Boss desert: 160 BPM, darker minor key, sub-bass kick every beat."""
    sample_rate = 44100
    bpm = 160
    beat = 60 / bpm
    notes = [196, 233, 261, 311, 349, 392, 466, 523, 622, 698]
    melody = [0, 4, 6, 8, 6, 4, 2, 0, 4, 8, 9, 6, 4, 2, 0, 4]
    bass_pattern = [0, 0, 2, 2, 4, 4, 2, 2, 0, 0, 4, 4, 6, 6, 2, 2]
    total_beats = len(melody)
    n_samples = int(sample_rate * beat * total_beats)
    buf = array.array("h", [0] * n_samples)
    samples_per_beat = int(sample_rate * beat)
    for beat_idx in range(total_beats):
        mel_freq = notes[melody[beat_idx]]
        bass_freq = notes[bass_pattern[beat_idx]] / 2
        start = beat_idx * samples_per_beat
        for i in range(samples_per_beat):
            t = i / sample_rate
            env = max(0, 1.0 - (i / samples_per_beat) * 0.6)
            mel = 600 * env * math.sin(2 * math.pi * mel_freq * t)
            bass_phase = (bass_freq * t) % 1.0
            bass = 500 * env * (abs(bass_phase - 0.5) * 4 - 1)
            hat = 180 * max(0, 1.0 - i / (samples_per_beat * 0.03)) * random.uniform(-1, 1) if i < samples_per_beat * 0.03 else 0
            kick = 0
            if i < samples_per_beat * 0.08:
                kick_env = max(0, 1.0 - i / (samples_per_beat * 0.08))
                kick = 700 * kick_env * math.sin(2 * math.pi * (50 - 25 * (i / (samples_per_beat * 0.08))) * t)
            val = int(mel + bass + hat + kick)
            idx = start + i
            if idx < n_samples:
                buf[idx] = max(-32768, min(32767, val))
    return pygame.mixer.Sound(buffer=buf)


def make_boss_excitebike_music():
    """Boss excitebike: 180 BPM, aggressive saw lead, heavy kick+sub."""
    sample_rate = 44100
    bpm = 180
    beat = 60 / bpm
    notes = [262, 294, 330, 392, 440, 523, 587, 659, 784, 880]
    melody = [4, 7, 9, 7, 5, 4, 2, 0, 5, 9, 7, 5, 4, 2, 0, 4]
    bass_pattern = [0, 0, 4, 4, 5, 5, 2, 2, 0, 0, 4, 4, 7, 7, 5, 5]
    total_beats = len(melody)
    n_samples = int(sample_rate * beat * total_beats)
    buf = array.array("h", [0] * n_samples)
    samples_per_beat = int(sample_rate * beat)
    for beat_idx in range(total_beats):
        mel_freq = notes[melody[beat_idx]]
        bass_freq = notes[bass_pattern[beat_idx]] / 2
        start = beat_idx * samples_per_beat
        for i in range(samples_per_beat):
            t = i / sample_rate
            env = max(0, 1.0 - (i / samples_per_beat) * 0.5)
            mel_phase = (mel_freq * t) % 1.0
            mel = 800 * env * (mel_phase * 2 - 1)
            bass = 600 * env * (1 if (bass_freq * t) % 1.0 < 0.5 else -1)
            hat = 350 * max(0, 1.0 - i / (samples_per_beat * 0.03)) * random.uniform(-1, 1) if i < samples_per_beat * 0.03 else 0
            kick = 0
            if i < samples_per_beat * 0.07:
                kick_env = max(0, 1.0 - i / (samples_per_beat * 0.07))
                kick = 800 * kick_env * math.sin(2 * math.pi * (60 - 35 * (i / (samples_per_beat * 0.07))) * t)
            val = int(mel + bass + hat + kick)
            idx = start + i
            if idx < n_samples:
                buf[idx] = max(-32768, min(32767, val))
    return pygame.mixer.Sound(buffer=buf)


def make_boss_micromachines_music():
    """Boss micro machines: 200 BPM, distorted pulse + sub-bass drops."""
    sample_rate = 44100
    bpm = 200
    beat = 60 / bpm
    notes = [247, 262, 277, 294, 311, 330, 349, 370, 392, 415, 440, 466, 494, 523, 554, 587]
    melody = [12, 11, 8, 5, 3, 5, 8, 12, 0, 3, 5, 8, 11, 8, 5, 0]
    bass_pattern = [0, 0, 5, 5, 8, 8, 3, 3, 0, 0, 8, 8, 11, 11, 5, 5]
    total_beats = len(melody)
    n_samples = int(sample_rate * beat * total_beats)
    buf = array.array("h", [0] * n_samples)
    samples_per_beat = int(sample_rate * beat)
    for beat_idx in range(total_beats):
        mel_freq = notes[melody[beat_idx]]
        bass_freq = notes[bass_pattern[beat_idx]] / 2
        start = beat_idx * samples_per_beat
        for i in range(samples_per_beat):
            t = i / sample_rate
            env = max(0, 1.0 - (i / samples_per_beat) * 0.4)
            duty = 0.25 + 0.15 * math.sin(beat_idx * 0.5)
            mel_phase = (mel_freq * t) % 1.0
            mel = 750 * env * (1 if mel_phase < duty else -1)
            bass = 650 * env * math.sin(2 * math.pi * bass_freq * t)
            bass = max(-650, min(650, bass * 1.8))
            hat = 300 * max(0, 1.0 - i / (samples_per_beat * 0.025)) * random.uniform(-1, 1) if i < samples_per_beat * 0.025 else 0
            kick = 0
            if i < samples_per_beat * 0.06:
                kick_env = max(0, 1.0 - i / (samples_per_beat * 0.06))
                kick = 700 * kick_env * math.sin(2 * math.pi * (55 - 30 * (i / (samples_per_beat * 0.06))) * t)
            val = int(mel + bass + hat + kick)
            idx = start + i
            if idx < n_samples:
                buf[idx] = max(-32768, min(32767, val))
    return pygame.mixer.Sound(buffer=buf)


# Sound channels
engine_channel = None
music_channel = None

# Global mute flag
sound_enabled = True

# SFX dict - initialized after pygame.mixer.init
SFX = {}
engine_sound = None
music_loops = {}


def set_sound_enabled(enabled):
    """Toggle global sound on/off. Stops all audio immediately when muting."""
    global sound_enabled
    sound_enabled = enabled
    if not enabled:
        pygame.mixer.stop()


def play_sfx(name):
    """Play a sound effect by name, respecting the global mute flag."""
    if sound_enabled and name in SFX:
        SFX[name].play()


def init_sounds():
    """Initialize all sound effects and music. Call after pygame.mixer.init()."""
    global engine_sound, engine_channel, music_channel

    engine_channel = pygame.mixer.Channel(7)
    music_channel = pygame.mixer.Channel(6)

    SFX.update({
        "coin": generate_sweep(800, 1200, 80, 0.08),       # subtle pickup chime
        "crash": generate_tone(120, 200, 0.15, "noise"),    # brief crunch
        "boost": generate_sweep(300, 800, 150, 0.08),       # soft whoosh
        "powerup": generate_sweep(400, 1000, 120, 0.10),    # gentle pickup
        "shield_hit": generate_sweep(600, 200, 120, 0.10),  # shield ping
        "life_lost": generate_sweep(500, 100, 300, 0.15),   # significant — keep audible
        "gameover": generate_sweep(400, 80, 600, 0.15),     # longer/important
        "select": generate_sweep(500, 700, 40, 0.05),       # very soft tick (sine sweep, not square beep)
        "highscore": generate_sweep(500, 1500, 400, 0.10),  # celebratory
        "boss_warning": generate_sweep(200, 800, 500, 0.18),  # dramatic entry
        "boss_hit": generate_tone(150, 150, 0.12, "noise"),   # impact thud
        "boss_defeat": generate_sweep(300, 1200, 800, 0.15),  # big moment
        "heat_bolt": generate_tone(400, 35, 0.008, "noise"),    # soft percussive thump
        "victory": generate_sweep(400, 1600, 800, 0.15),      # earned fanfare
        "nuke": generate_sweep(200, 1600, 350, 0.18),         # screen-clear boom
        "phase": generate_sweep(1200, 400, 200, 0.08),        # phase shift
        "surge": generate_sweep(150, 1800, 250, 0.12),        # surge rush
        "evolve": generate_sweep(300, 900, 400, 0.10),        # evolution whoosh
        "asteroid_hit": generate_tone(200, 100, 0.10, "noise"),  # brief chip
        "asteroid_destroy": generate_sweep(150, 600, 150, 0.12), # satisfying pop
        "asteroid_split": generate_sweep(300, 100, 200, 0.12),   # crack
        "asteroid_warning": generate_sweep(400, 200, 250, 0.08), # subtle alarm
        # Boss combat SFX
        "boss_phase_drop": generate_bass_drop(60, 25, 500, 0.22),    # phase 2/3 transition sub-drop
        "boss_enter": generate_bass_drop(80, 30, 800, 0.20),         # boss entrance warning
        "boss_slam": generate_sub_bass(35, 250, 0.25, 3),            # ground slam / shockwave impact
        "boss_rumble": generate_sub_bass(30, 400, 0.15, 2),          # sustained rumble (charge telegraph)
        "missile_launch": generate_sweep(200, 800, 100, 0.10),       # missile fire
        "missile_hit": generate_tone(100, 120, 0.12, "noise"),       # missile explosion on player
        "boulder_drop": generate_sub_bass(50, 150, 0.12, 2),         # boulder spawn thud
        "sandstorm_wind": generate_tone(150, 300, 0.06, "noise"),    # sandstorm whoosh
        "beam_hum": generate_tone(220, 200, 0.06, "sine"),           # solar beam active
        "ring_pulse": generate_sweep(100, 400, 150, 0.08),           # heat wave / shockwave ring emit
        "oil_splat": generate_tone(80, 100, 0.10, "noise"),          # oil slick drop
        "tire_launch": generate_tone(150, 80, 0.08, "noise"),        # tire barrage fire
        "tire_bounce": generate_sweep(200, 400, 50, 0.06),           # tire wall bounce
        "boss_death_rumble": generate_sub_bass(25, 600, 0.20, 3),    # death animation low rumble
        "charge_whoosh": generate_sweep(100, 600, 200, 0.12),        # boss charge across screen
        "rocket_launch": generate_sweep(150, 400, 120, 0.10),        # homing rocket fire
        "orb_hit": generate_sweep(300, 600, 60, 0.08),               # orbit orb impact
    })

    engine_sound = make_engine_sound()

    music_loops.update({
        "desert": make_desert_music(),
        "excitebike": make_excitebike_music(),
        "micromachines": make_micromachines_music(),
        "boss_desert": make_boss_desert_music(),
        "boss_excitebike": make_boss_excitebike_music(),
        "boss_micromachines": make_boss_micromachines_music(),
    })
