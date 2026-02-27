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


def make_engine_sound():
    sample_rate = 44100
    n_samples = int(sample_rate * 0.5)
    buf = array.array("h", [0] * n_samples)
    for i in range(n_samples):
        t = i / sample_rate
        val = int(
            1500 * math.sin(2 * math.pi * 80 * t)
            + 800 * math.sin(2 * math.pi * 160 * t)
            + 400 * math.sin(2 * math.pi * 240 * t)
        )
        buf[i] = max(-32768, min(32767, val))
    return pygame.mixer.Sound(buffer=buf)


def make_desert_music():
    """Desert mode: minor pentatonic, 140 BPM chiptune."""
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
            mel = 800 * env * (1 if (math.sin(2 * math.pi * mel_freq * t) > 0) else -1)
            bass_phase = (bass_freq * t) % 1.0
            bass = 600 * env * (abs(bass_phase - 0.5) * 4 - 1)
            hat = 200 * max(0, 1.0 - i / (samples_per_beat * 0.05)) * random.uniform(-1, 1) if i < samples_per_beat * 0.05 else 0
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


# Sound channels
engine_channel = None
music_channel = None

# SFX dict - initialized after pygame.mixer.init
SFX = {}
engine_sound = None
music_loops = {}


def init_sounds():
    """Initialize all sound effects and music. Call after pygame.mixer.init()."""
    global engine_sound, engine_channel, music_channel

    engine_channel = pygame.mixer.Channel(7)
    music_channel = pygame.mixer.Channel(6)

    SFX.update({
        "coin": generate_sweep(800, 1200, 80, 0.2),
        "crash": generate_tone(120, 300, 0.4, "noise"),
        "boost": generate_sweep(300, 800, 200, 0.2),
        "powerup": generate_sweep(400, 1000, 150, 0.2),
        "shield_hit": generate_sweep(600, 200, 150, 0.25),
        "life_lost": generate_sweep(500, 100, 400, 0.3),
        "gameover": generate_sweep(400, 80, 800, 0.3),
        "select": generate_tone(600, 60, 0.15, "square"),
        "highscore": generate_sweep(500, 1500, 500, 0.2),
        "boss_warning": generate_sweep(200, 800, 600, 0.35),
        "boss_hit": generate_tone(150, 200, 0.3, "noise"),
        "boss_defeat": generate_sweep(300, 1200, 1000, 0.3),
        "heat_bolt": generate_sweep(600, 1400, 120, 0.25),
        "victory": generate_sweep(400, 1600, 800, 0.25),
        "nuke": generate_sweep(200, 1600, 350, 0.35),
        "phase": generate_sweep(1200, 400, 250, 0.2),
        "surge": generate_sweep(150, 1800, 300, 0.3),
        "evolve": generate_sweep(300, 900, 400, 0.2),
        "asteroid_hit": generate_tone(200, 150, 0.25, "noise"),
        "asteroid_destroy": generate_sweep(150, 600, 200, 0.3),
        "asteroid_warning": generate_sweep(400, 200, 300, 0.2),
    })

    engine_sound = make_engine_sound()

    music_loops.update({
        "desert": make_desert_music(),
        "excitebike": make_excitebike_music(),
        "micromachines": make_micromachines_music(),
    })
