"""Pure settings and text helpers used by the Pygame UI."""
from __future__ import annotations

CHOICES = {
    'theme': ['Neon', 'Classic', 'Minimal'],
    'difficulty': ['easy', 'normal', 'hard'],
}
NUMBERS = {
    'speed': (0.5, 2.0, 0.25),
    'music_volume': (0.0, 1.0, 0.1),
    'sfx_volume': (0.0, 1.0, 0.1),
}
TOGGLES = {'ghost', 'grid', 'effects', 'fullscreen'}


def adjust_setting(settings: dict, name: str, delta: int = 1):
    if name in CHOICES:
        options = CHOICES[name]
        current = settings.get(name, options[0])
        index = options.index(current) if current in options else 0
        settings[name] = options[(index + (1 if delta >= 0 else -1)) % len(options)]
    elif name in NUMBERS:
        lo, hi, step = NUMBERS[name]
        current = float(settings.get(name, lo))
        settings[name] = round(min(hi, max(lo, current + step * (1 if delta >= 0 else -1))), 2)
    elif name in TOGGLES:
        settings[name] = not settings.get(name, False)
    else:
        raise KeyError(name)
    return settings[name]


def rebind_control(settings: dict, action: str, new_key: str) -> bool:
    """Swap rather than duplicate an already-used key."""
    bindings = settings['controls']
    if action not in bindings or not isinstance(new_key, str) or not new_key.strip():
        return False
    new_key = new_key.lower().strip()
    previous = bindings[action]
    for other, old_key in bindings.items():
        if other != action and old_key == new_key:
            bindings[other] = previous
            break
    bindings[action] = new_key
    return True


def format_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f'{seconds // 60:02d}:{seconds % 60:02d}'
