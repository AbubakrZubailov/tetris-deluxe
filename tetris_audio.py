"""Procedural original soundtrack and SFX; works without separate assets.

Pygame is imported lazily so tests can exercise the wave synthesizer without SDL.
"""
from array import array
import math

SAMPLE_RATE = 22050


def synth_wave(frequencies, duration, sample_rate=SAMPLE_RATE, gain=.20, kind='sine'):
    length = max(1, int(sample_rate * duration))
    pcm = array('h')
    freq = tuple(float(f) for f in frequencies if f > 0)
    for i in range(length):
        t = i / sample_rate
        tail = min(1., (length - i) / max(1, sample_rate * .05))
        attack = min(1., i / max(1, sample_rate * .007))
        envelope = tail * attack
        waves = []
        for f in freq:
            phase = t * f
            wave = math.sin(2 * math.pi * phase)
            if kind == 'sparkle':
                wave = .75 * wave + .25 * math.sin(2 * math.pi * phase * 2)
            waves.append(wave)
        v = sum(waves) / max(1, len(waves))
        amp = int(max(-32767, min(32767, v * envelope * gain * 32767)))
        pcm.extend((amp, amp))
    if pcm.itemsize != 2:
        raise RuntimeError('Requires 16-bit audio array')
    return pcm.tobytes()


def create_music():
    # Original short motif, not derived from existing commercial music.
    melody = [261.63, 329.63, 392, 523.25, 392, 329.63, 293.66, 349.23,
              440, 349.23, 293.66, 261.63, 329.63, 392, 293.66, 246.94]
    loop = []
    for i, pitch in enumerate(melody):
        bass = [130.81, 146.83, 110, 123.47][i // 4]
        loop.append(synth_wave((pitch, bass), .31, gain=.125, kind='sparkle'))
    return b''.join(loop)


class SoundManager:
    def __init__(self):
        self.ready = False
        self.sounds = {}
        self.music = None
        self.channel = None
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)
            self.channel = pygame.mixer.Channel(0)
            self.music = pygame.mixer.Sound(buffer=create_music())
            patterns = {
                'move': (330, .045), 'rotate': (460, .085), 'drop': (170, .145),
                'lock': (225, .060), 'clear': (670, .15), 'tetris': (930, .30),
                'level': (780, .25), 'select': (490, .06), 'finish': (180, .35),
            }
            self.sounds = {k: pygame.mixer.Sound(buffer=synth_wave([freq], sec,
                                        gain=.18, kind='sparkle')) for k, (freq, sec) in patterns.items()}
            self.ready = True
        except Exception:
            # Missing audio device/driver is allowed. The game remains playable.
            self.ready = False

    def update(self, settings, playing=True):
        if not self.ready:
            return
        volume = float(settings['music_volume']) if playing else 0.
        self.channel.set_volume(volume)
        if volume > 0 and not self.channel.get_busy():
            self.channel.play(self.music, loops=-1)

    def play(self, name, settings):
        if not self.ready:
            return
        volume = float(settings['sfx_volume'])
        sound = self.sounds.get(name)
        if sound and volume > 0:
            sound.set_volume(volume)
            sound.play()
