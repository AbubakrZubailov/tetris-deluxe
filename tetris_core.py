"""Tetris Deluxe: engine and progress storage, independent from pygame."""
from __future__ import annotations

import copy
import json
import math
import random
from pathlib import Path

COLS, ROWS = 12, 24  # The original game's board dimensions.
SHAPES = {
    'O': [(0, 0), (1, 0), (0, 1), (1, 1)],
    'I': [(0, 0), (1, 0), (2, 0), (3, 0)],
    'T': [(1, 0), (0, 1), (1, 1), (2, 1)],
    'S': [(1, 0), (2, 0), (0, 1), (1, 1)],
    'Z': [(0, 0), (1, 0), (1, 1), (2, 1)],
    'J': [(0, 0), (0, 1), (1, 1), (2, 1)],
    'L': [(2, 0), (0, 1), (1, 1), (2, 1)],
}
COLORS = {
    'O': (255, 215, 0), 'I': (0, 213, 232), 'T': (176, 107, 241),
    'S': (70, 210, 110), 'Z': (240, 82, 96), 'J': (83, 135, 237),
    'L': (255, 163, 60),
}
MODES = {
    'CLASSIC': ('CLASSIC', 'Play for the highest score'),
    'SPRINT': ('SPRINT 40', 'Clear 40 lines as fast as you can'),
    'ULTRA': ('ULTRA 2:00', 'Score as much as possible in 2 minutes'),
    'SURVIVAL': ('SURVIVAL', 'Gravity speeds up every 22 seconds'),
}
POINTS = {1: 100, 2: 300, 3: 500, 4: 800}
DEFAULT_CONTROLS = {
    'left': 'left', 'right': 'right', 'rotate': 'up',
    'soft_drop': 'down', 'hard_drop': 'space', 'pause': 'p',
    'back': 'escape', 'restart': 'r',
}
DEFAULT_SETTINGS = {
    'theme': 'Neon', 'music_volume': 0.22, 'sfx_volume': 0.55,
    'difficulty': 'normal', 'speed': 1.0, 'ghost': True, 'grid': True,
    'effects': True, 'fullscreen': False, 'controls': DEFAULT_CONTROLS,
}
ACHIEVEMENTS = {
    'first_game': ('FIRST STEPS', 'Finish your first game'),
    'score_1000': ('GETTING WARM', 'Score 1,000 in a single game'),
    'score_10000': ('TEN THOUSAND', 'Score 10,000 in a single game'),
    'first_tetris': ('FOUR AT ONCE', 'Clear four lines with one piece'),
    'combo_3': ('CHAIN REACTION', 'Reach a 3-combo'),
    'lines_100': ('LINE MASTER', 'Clear 100 lines in total'),
    'level_10': ('HIGH GEAR', 'Reach level 10'),
    'ten_games': ('DEDICATED', 'Finish 10 games'),
    'sprint_win': ('SPEEDRUNNER', 'Complete Sprint 40'),
    'ultra_5000': ('TIME ATTACK', 'Score 5,000 in Ultra mode'),
}


def rotate_cells(cells, name='T', direction=1):
    if name == 'O':
        return list(cells)
    result = [(-y, x) if direction == 1 else (y, -x) for x, y in cells]
    min_x = min(x for x, _ in result)
    min_y = min(y for _, y in result)
    return [(x - min_x, y - min_y) for x, y in result]


def try_rotate(game, direction=1):
    if game.current == 'O' or game.over or game.pending_rows:
        return False
    new = rotate_cells(game.cells, game.current, direction)
    # A small selection of wall and floor kicks, with two-cell kicks for I.
    kicks = [(0, 0), (-1, 0), (1, 0), (-2, 0), (2, 0),
             (0, -1), (-1, -1), (1, -1), (0, -2), (-2, -1), (2, -1)]
    for dx, dy in kicks:
        if game.valid(game.x + dx, game.y + dy, new):
            game.x += dx
            game.y += dy
            game.cells = new
            game.events.append(('rotate', {}))
            return True
    return False


def gravity_interval(level, difficulty='normal', speed=1.0):
    """Continuous gravity curve; enough time to react at low levels."""
    difficulty_factor = {'easy': 1.4, 'normal': 1.0, 'hard': 0.7}.get(difficulty, 1.0)
    try:
        speed = max(0.5, min(2.0, float(speed)))
    except (TypeError, ValueError):
        speed = 1.0
    return max(0.055, .72 * math.exp(-.15 * (max(1, level) - 1)) * difficulty_factor / speed)


class SevenBag:
    def __init__(self, rng=None):
        self.rng = rng if rng is not None else random.Random()
        self.bag = []

    def next(self):
        if not self.bag:
            self.bag = list(SHAPES)
            self.rng.shuffle(self.bag)
        return self.bag.pop()


class Game:
    def __init__(self, mode='CLASSIC', rng=None):
        if mode not in MODES:
            raise ValueError(f'Unknown game mode: {mode}')
        self.mode = mode
        self.board = [[0] * COLS for _ in range(ROWS)]
        self.bag = SevenBag(rng)
        self.preview = [self.bag.next() for _ in range(3)]
        self.current = ''
        self.cells = []
        self.x = self.y = 0
        self.score = self.lines = self.tetrises = 0
        self.combo = -1
        self.best_combo = 0
        self.back_to_back = False
        self.level = 1
        self.elapsed = 0.0
        self.over = False
        self.end_reason = ''
        self._recorded = False
        self.pending_rows = []
        self.events = []
        self.spawn()

    def spawn(self):
        if self.over:
            return
        self.current = self.preview.pop(0)
        self.preview.append(self.bag.next())
        self.cells = list(SHAPES[self.current])
        self.x, self.y = COLS // 2 - 2, 0
        if not self.valid(self.x, self.y, self.cells):
            self.finish('Stack reached the top')
        else:
            self.events.append(('spawn', {}))

    def valid(self, x, y, cells=None):
        for cx, cy in (cells if cells is not None else self.cells):
            px, py = x + cx, y + cy
            if not (0 <= px < COLS and 0 <= py < ROWS):
                return False
            if self.board[py][px]:
                return False
        return True

    def move(self, dx):
        if self.over or self.pending_rows or not self.valid(self.x + dx, self.y):
            return False
        self.x += dx
        self.events.append(('move', {}))
        return True

    def rotate(self, direction=1):
        return try_rotate(self, direction)

    def ghost_y(self):
        gy = self.y
        while self.valid(self.x, gy + 1):
            gy += 1
        return gy

    def down(self, soft=False):
        if self.over or self.pending_rows:
            return False
        if self.valid(self.x, self.y + 1):
            self.y += 1
            if soft:
                self.score += 1
            return True
        self.lock()
        return False

    def hard_drop(self):
        if self.over or self.pending_rows:
            return 0
        gy = self.ghost_y()
        distance = gy - self.y
        self.y = gy
        self.score += distance * 2
        self.events.append(('drop', {'distance': distance}))
        self.lock()
        return distance

    def lock(self):
        if self.over or self.pending_rows:
            return
        color = COLORS[self.current]
        for cx, cy in self.cells:
            self.board[self.y + cy][self.x + cx] = color
        self.events.append(('lock', {}))
        rows = self.full_rows()
        if rows:
            self.pending_rows = rows
            self.events.append(('clear_start', {'rows': rows[:]}))
        else:
            self.award_lines(0)
            self.spawn()

    def full_rows(self):
        return [i for i, row in enumerate(self.board) if all(row)]

    def remove_full_rows(self):
        full = self.full_rows()
        if full:
            self.board = [[0] * COLS for _ in full] + [row for row in self.board if not all(row)]
        return len(full)

    def resolve_clear(self):
        if not self.pending_rows:
            return 0
        n = self.remove_full_rows()
        self.pending_rows = []
        points = self.award_lines(n)
        self.events.append(('clear', {'count': n, 'points': points}))
        if n == 4:
            self.events.append(('tetris', {}))
        if not self.over:
            self.spawn()
        return n

    def award_lines(self, n):
        if n <= 0:
            self.combo = -1
            return 0
        self.combo += 1
        self.best_combo = max(self.best_combo, self.combo)
        multiplier = self.level
        base = POINTS.get(min(4, n), 800) * multiplier
        b2b_bonus = base // 2 if n == 4 and self.back_to_back else 0
        combo_bonus = 50 * self.combo * multiplier
        points = base + b2b_bonus + combo_bonus
        self.score += points
        self.lines += n
        if n == 4:
            self.tetrises += 1
            self.back_to_back = True
        else:
            self.back_to_back = False
        old_level = self.level
        self.level = max(1, 1 + self.lines // 10)
        if self.mode == 'SURVIVAL':
            self.level = max(self.level, 1 + int(self.elapsed // 22))
        if self.level > old_level:
            self.events.append(('level', {'level': self.level}))
        if self.mode == 'SPRINT' and self.lines >= 40:
            self.finish('Sprint cleared')
        return points

    def tick(self, dt):
        if self.over:
            return
        self.elapsed += max(0.0, dt)
        if self.mode == 'SURVIVAL':
            new_level = max(1 + self.lines // 10, 1 + int(self.elapsed // 22))
            if new_level > self.level:
                self.level = new_level
                self.events.append(('level', {'level': self.level}))
        if self.mode == 'ULTRA' and self.elapsed >= 120.0:
            self.elapsed = 120.0
            self.finish('Time up')

    def finish(self, reason='Game over'):
        if not self.over:
            self.over = True
            self.end_reason = reason
            self.events.append(('finish', {'reason': reason}))

    def take_events(self):
        events, self.events = self.events, []
        return events


def _dict_from(path):
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _natural_int(value, default=0):
    try:
        return max(0, int(value))
    except (ValueError, TypeError, OverflowError):
        return default


class Store:
    """Versioned progress; reads but never modifies the original highscore.json."""
    def __init__(self, folder=None):
        self.folder = Path(folder) if folder is not None else Path(__file__).resolve().parent
        self.progress_path = self.folder / 'tetris_deluxe_data.json'
        self.settings_path = self.folder / 'tetris_settings.json'
        old = _dict_from(self.folder / 'highscore.json')
        data = _dict_from(self.progress_path)
        rec = data.get('records', {})
        rec = rec if isinstance(rec, dict) else {}
        self.records = {}
        for mode in MODES:
            record = rec.get(mode, {})
            record = record if isinstance(record, dict) else {}
            self.records[mode] = {
                'score': _natural_int(record.get('score')),
                'lines': _natural_int(record.get('lines')),
                'best_time': record.get('best_time') if isinstance(record.get('best_time'), (int, float)) and record['best_time'] > 0 else None,
            }
        self.records['CLASSIC']['score'] = max(
            self.records['CLASSIC']['score'], _natural_int(old.get('high_score')))
        stats = data.get('stats', {})
        stats = stats if isinstance(stats, dict) else {}
        self.stats = {k: _natural_int(stats.get(k)) for k in
                      ('games', 'time', 'lines', 'tetrises', 'points', 'best_combo')}
        achievements = data.get('achievements', [])
        self.achievements = set(a for a in achievements if a in ACHIEVEMENTS) if isinstance(achievements, list) else set()
        settings = _dict_from(self.settings_path)
        self.settings = copy.deepcopy(DEFAULT_SETTINGS)
        for key, default in DEFAULT_SETTINGS.items():
            value = settings.get(key)
            if key == 'controls':
                if isinstance(value, dict):
                    for action, name in value.items():
                        if action in self.settings['controls'] and isinstance(name, str) and name:
                            self.settings['controls'][action] = name
            elif isinstance(default, bool) and type(value) is bool:
                self.settings[key] = value
            elif key == 'theme' and value in ('Neon', 'Classic', 'Minimal'):
                self.settings[key] = value
            elif key == 'difficulty' and value in ('easy', 'normal', 'hard'):
                self.settings[key] = value
            elif key in ('music_volume', 'sfx_volume') and isinstance(value, (int, float)) and math.isfinite(value):
                self.settings[key] = round(max(0., min(1., value)), 2)
            elif key == 'speed' and isinstance(value, (int, float)) and math.isfinite(value):
                self.settings[key] = round(max(0.5, min(2.0, value)), 2)

    def _save(self, path, value):
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix('.tmp')
            tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
            tmp.replace(path)
            return True
        except OSError:
            return False

    def save_settings(self):
        return self._save(self.settings_path, self.settings)

    def save_progress(self):
        return self._save(self.progress_path, {
            'version': 1,
            'records': self.records,
            'stats': self.stats,
            'achievements': sorted(self.achievements),
        })

    def record_game(self, game):
        if game._recorded:
            return []
        game._recorded = True
        r = self.records[game.mode]
        r['score'] = max(r['score'], game.score)
        r['lines'] = max(r['lines'], game.lines)
        if game.mode == 'SPRINT' and game.end_reason == 'Sprint cleared':
            if r['best_time'] is None or game.elapsed < r['best_time']:
                r['best_time'] = round(game.elapsed, 2)
        s = self.stats
        s['games'] += 1
        s['time'] += int(game.elapsed)
        s['lines'] += game.lines
        s['tetrises'] += game.tetrises
        s['points'] += game.score
        s['best_combo'] = max(s['best_combo'], game.best_combo)
        earned = set()
        if s['games'] >= 1: earned.add('first_game')
        if game.score >= 1000: earned.add('score_1000')
        if game.score >= 10000: earned.add('score_10000')
        if game.tetrises: earned.add('first_tetris')
        if game.best_combo >= 3: earned.add('combo_3')
        if s['lines'] >= 100: earned.add('lines_100')
        if game.level >= 10: earned.add('level_10')
        if s['games'] >= 10: earned.add('ten_games')
        if game.mode == 'SPRINT' and game.end_reason == 'Sprint cleared': earned.add('sprint_win')
        if game.mode == 'ULTRA' and game.score >= 5000: earned.add('ultra_5000')
        newly_earned = earned - self.achievements
        self.achievements.update(newly_earned)
        self.save_progress()
        return sorted(newly_earned)
