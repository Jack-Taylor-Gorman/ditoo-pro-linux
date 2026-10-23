"""Chiptune sound effects and music loops, synthesised at start-up.

Square and triangle waves with pitch sweeps and short envelopes, the way an
NES would make them. Output goes to the Ditoo when PULSE_SINK names it; SDL's
PulseAudio backend honours that, so nothing else on the desktop changes.
"""
import numpy as np

RATE = 22050


def _t(sec):
    return np.arange(int(RATE * sec)) / RATE


def square(freq, sec, duty=0.5):
    """freq may be a number or an array (for sweeps)."""
    t = _t(sec)
    f = np.broadcast_to(np.asarray(freq, dtype=np.float64), t.shape)
    phase = np.cumsum(f) / RATE
    return np.where((phase % 1) < duty, 1.0, -1.0)


def triangle(freq, sec):
    t = _t(sec)
    f = np.broadcast_to(np.asarray(freq, dtype=np.float64), t.shape)
    phase = np.cumsum(f) / RATE
    return 4 * np.abs((phase % 1) - 0.5) - 1


def noise(sec, seed=0):
    rng = np.random.default_rng(seed)
    # Held samples give the crunchy NES noise rather than hiss.
    raw = rng.uniform(-1, 1, int(RATE * sec) // 8 + 1)
    return np.repeat(raw, 8)[: int(RATE * sec)]


def sweep(f0, f1, sec, curve=1.0):
    x = np.linspace(0, 1, int(RATE * sec)) ** curve
    return f0 + (f1 - f0) * x


def env(sig, attack=0.002, decay=None):
    n = len(sig)
    e = np.ones(n)
    a = max(1, int(RATE * attack))
    e[:a] = np.linspace(0, 1, a)
    e[a:] = np.linspace(1, 0, n - a) ** (decay or 1.5)
    return sig * e


def seq(*parts):
    return np.concatenate(parts)


def note(n):
    """MIDI note number to Hz."""
    return 440.0 * 2 ** ((n - 69) / 12)


def build_sfx():
    s = {}
    s["move"] = env(square(880, 0.03, 0.25)) * 0.35
    s["turn"] = env(square(660, 0.02, 0.25)) * 0.25
    s["select"] = env(seq(square(660, 0.04, 0.25), square(990, 0.05, 0.25))) * 0.4
    s["start"] = env(seq(*(square(note(n), 0.06, 0.25) for n in (72, 76, 79, 84))), decay=0.6) * 0.45
    s["eat"] = env(square(sweep(500, 1400, 0.08), 0.08, 0.25)) * 0.45
    s["coin"] = env(seq(square(note(83), 0.05, 0.5), square(note(88), 0.18, 0.5))) * 0.4
    s["jump"] = env(square(sweep(300, 800, 0.12, 0.5), 0.12, 0.5)) * 0.4
    s["flap"] = env(square(sweep(400, 700, 0.06), 0.06, 0.25)) * 0.35
    s["shoot"] = env(square(sweep(1400, 300, 0.1, 0.5), 0.1, 0.25)) * 0.3
    s["laser"] = env(square(sweep(2000, 200, 0.15, 0.3), 0.15, 0.5)) * 0.3
    s["bounce"] = env(triangle(sweep(600, 400, 0.05), 0.05)) * 0.6
    s["hit"] = env(seq(square(220, 0.03), noise(0.05, 1)), decay=2) * 0.45
    s["drop"] = env(triangle(sweep(300, 90, 0.12), 0.12)) * 0.7
    s["tick"] = env(square(1200, 0.015, 0.125)) * 0.2
    s["explode"] = env(noise(0.4, 2) * np.linspace(1, 0.2, int(RATE * 0.4)), decay=1.2) * 0.6
    s["die"] = env(square(sweep(600, 60, 0.6, 0.7), 0.6, 0.5), decay=0.8) * 0.45
    s["line"] = env(seq(*(square(note(n), 0.05, 0.5) for n in (76, 79, 83, 88))), decay=0.5) * 0.4
    s["level"] = env(seq(*(square(note(n), 0.07, 0.25) for n in (67, 71, 74, 79, 83, 86))), decay=0.5) * 0.4
    s["power"] = env(square(sweep(200, 1600, 0.3, 2), 0.3, 0.25)) * 0.35
    s["record"] = env(seq(*(square(note(n), 0.09, 0.5) for n in (72, 76, 79, 84, 79, 84, 88))), decay=0.4) * 0.45
    s["near"] = env(triangle(1760, 0.04)) * 0.25
    # Simon's four pads: the original toy's notes, A major-ish and distinct.
    for i, hz in enumerate((329.63, 277.18, 440.0, 164.81)):
        s[f"tone{i}"] = env(square(hz, 0.35, 0.5), attack=0.01, decay=0.6) * 0.45
    return s


def _drum_kick(sec):
    return env(triangle(sweep(160, 40, sec, 0.4), sec), decay=1.5)


def _drum_hat(sec, seed):
    return env(noise(sec, seed), decay=3) * 0.35


def build_track(bpm, bass, lead, bars=4, kick_every=2, swing=0.0):
    """bass/lead: lists of MIDI notes per 16th (None = rest), looped over bars."""
    step = 60 / bpm / 4
    n = int(RATE * step)
    out = np.zeros(n * 16 * bars)
    for i in range(16 * bars):
        a = i * n
        b = bass[i % len(bass)]
        if b is not None:
            out[a:a + n] += env(triangle(note(b), step), decay=0.7) * 0.5
        l = lead[i % len(lead)]
        if l is not None:
            out[a:a + n] += env(square(note(l), step, 0.25), decay=1.0) * 0.18
        if i % (4 * kick_every // 2 or 1) == 0:
            out[a:a + n] += _drum_kick(step) * 0.6
        if i % 2 == 1:
            out[a:a + n] += _drum_hat(step, i)
    return out


def build_music():
    m = {}
    # Super Hexagon: fast, minor, relentless.
    bass = [45, 45, 57, 45, 45, 57, 45, 57, 41, 41, 53, 41, 43, 43, 55, 43]
    lead = [69, None, 72, 76, None, 72, 69, None, 77, None, 76, 72, 74, None, 71, None,
            69, None, 72, 76, None, 79, 81, None, 77, 76, 74, 72, 71, None, 67, None]
    m["hexagon"] = build_track(168, bass, lead, bars=4)
    # General-purpose upbeat loop for the action games.
    bass = [48, None, 48, 55, None, 55, 53, None, 53, 52, None, 50, 48, None, 43, 47]
    lead = [72, 76, 79, None, 76, None, 74, 72, None, 74, 76, None, 72, None, None, None]
    m["chase"] = build_track(132, bass, lead, bars=2)
    # Calmer loop for puzzle games.
    bass = [45, None, None, None, 41, None, None, None, 48, None, None, None, 43, None, None, None]
    lead = [76, None, 72, None, 69, None, 72, None, 74, None, 72, None, 71, None, 67, None]
    m["puzzle"] = build_track(112, bass, lead, bars=2, kick_every=4)
    return m


DEVICE = "DitooPro-Audio"


class Sound:
    def __init__(self, enabled=True, device=DEVICE):
        """device: an output's name as SDL lists it, or None for the default.
        Naming it is the only routing that sticks: SDL opens the default
        output by name, which beats PULSE_SINK and pactl move-sink-input."""
        self.enabled = enabled
        self.sfx, self.tracks, self.current = {}, {}, None
        if not enabled:
            return
        import pygame
        import pygame._sdl2.audio as sdl_audio
        self.pg = pygame
        # pygame.init() may already have opened the mixer with its defaults;
        # reopen with a small buffer, since that buffer is input-to-sound lag.
        pygame.mixer.quit()
        pygame.mixer.init()  # the device list needs the audio subsystem up
        names = sdl_audio.get_audio_device_names(False)
        pygame.mixer.quit()
        self.device = device if device in names else None
        pygame.mixer.init(RATE, -16, 1, 256, devicename=self.device)
        _, _, channels = pygame.mixer.get_init()
        pygame.mixer.set_num_channels(12)
        self.music_channel = pygame.mixer.Channel(11)
        pygame.mixer.set_reserved(1)

        def to(a):
            pcm = (np.clip(a, -1, 1) * 30000).astype(np.int16)
            if channels == 2:  # SDL can insist on stereo
                pcm = np.ascontiguousarray(np.column_stack([pcm, pcm]))
            return pygame.sndarray.make_sound(pcm)
        self.sfx = {k: to(v) for k, v in build_sfx().items()}
        self.tracks = {k: to(v * 0.7) for k, v in build_music().items()}

    def play(self, name):
        if self.enabled and name in self.sfx:
            self.sfx[name].play()

    def music(self, name):
        if not self.enabled or name == self.current:
            return
        self.current = name
        self.music_channel.stop()
        if name in self.tracks:
            self.music_channel.play(self.tracks[name], loops=-1)
