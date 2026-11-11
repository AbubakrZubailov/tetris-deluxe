import json
import random
import tempfile
import unittest
from pathlib import Path

from tetris_core import (Game, SevenBag, Store, COLS, ROWS, SHAPES, DEFAULT_SETTINGS,
                         rotate_cells, try_rotate, gravity_interval)


class CoreTests(unittest.TestCase):
    def test_seven_bag_each_group_has_all_shapes(self):
        bag = SevenBag(random.Random(12))
        for _ in range(8):
            self.assertEqual(set(bag.next() for _ in range(7)), set(SHAPES))

    def test_start_is_valid_and_next_is_three(self):
        g = Game()
        self.assertFalse(g.over)
        self.assertEqual(len(g.preview), 3)
        self.assertEqual(len(g.board), ROWS)
        self.assertEqual(len(g.board[0]), COLS)

    def test_rotations_have_four_states(self):
        for name in SHAPES:
            cells = SHAPES[name]
            for _ in range(4):
                cells = rotate_cells(cells, name)
            self.assertEqual(set(cells), set(SHAPES[name]))

    def test_wall_kick_stays_inside(self):
        g = Game()
        g.current = 'I'
        g.cells = rotate_cells(SHAPES['I'], 'I')
        g.x = COLS - 2
        g.y = 4
        self.assertTrue(try_rotate(g, direction=1))
        self.assertTrue(all(0 <= g.x + x < COLS for x, _ in g.cells))

    def test_wall_rotation_does_not_overlap_board(self):
        g = Game()
        g.current = 'I'
        g.cells = rotate_cells(SHAPES['I'], 'I')
        g.x, g.y = 0, 2
        for x in range(COLS):
            for y in range(ROWS):
                g.board[y][x] = (255, 255, 255)
        for cx, cy in g.cells:
            g.board[g.y + cy][g.x + cx] = 0
        self.assertFalse(try_rotate(g, direction=1))

    def test_clear_rows(self):
        g = Game()
        g.board[-1] = [(1,2,3)] * COLS
        g.board[-2] = [(1,2,3)] * COLS
        self.assertEqual(g.full_rows(), [ROWS-2, ROWS-1])
        self.assertEqual(g.remove_full_rows(), 2)
        self.assertEqual(g.board[0], [0] * COLS)

    def test_combo_and_back_to_back_tetris(self):
        g = Game()
        first = g.award_lines(4)
        second = g.award_lines(4)
        self.assertGreater(second, first)
        self.assertEqual(g.lines, 8)
        self.assertEqual(g.tetrises, 2)
        self.assertEqual(g.combo, 1)
        g.award_lines(0)
        self.assertEqual(g.combo, -1)

    def test_mode_timeout_and_sprint_completion(self):
        g = Game('ULTRA')
        g.tick(121)
        self.assertTrue(g.over)
        self.assertEqual(g.end_reason, 'Time up')
        g = Game('SPRINT')
        g.award_lines(40)
        self.assertTrue(g.over)
        self.assertEqual(g.end_reason, 'Sprint cleared')

    def test_gravity_decreases_smoothly_and_difficulty_changes(self):
        self.assertGreater(gravity_interval(1, 'normal'), gravity_interval(2, 'normal'))
        self.assertGreater(gravity_interval(3, 'easy'), gravity_interval(3, 'hard'))
        self.assertGreater(gravity_interval(1, 'normal'), gravity_interval(10, 'normal'))

    def test_legacy_migration_and_persistence(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'highscore.json').write_text('{"high_score": 9200}')
            s = Store(p)
            self.assertEqual(s.records['CLASSIC']['score'], 9200)
            g = Game('SPRINT')
            g.score = 1200
            g.lines = 12
            g.elapsed = 48
            g.over = True
            s.record_game(g)
            self.assertEqual(Store(p).records['SPRINT']['score'], 1200)
            self.assertEqual(Store(p).records['CLASSIC']['score'], 9200)
            self.assertEqual(json.loads((p / 'highscore.json').read_text())['high_score'], 9200)

    def test_invalid_json_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'tetris_deluxe_data.json').write_text('{broken')
            (p / 'tetris_settings.json').write_text('[]')
            s = Store(p)
            self.assertEqual(s.stats['games'], 0)
            self.assertEqual(s.settings['theme'], DEFAULT_SETTINGS['theme'])

    def test_settings_saved_and_clamped(self):
        with tempfile.TemporaryDirectory() as d:
            s = Store(Path(d))
            s.settings['theme'] = 'Minimal'
            s.settings['music_volume'] = 0.25
            s.save_settings()
            self.assertEqual(Store(Path(d)).settings['theme'], 'Minimal')
            self.assertEqual(Store(Path(d)).settings['music_volume'], 0.25)

    def test_random_play_never_corrupts_board(self):
        for mode in ('CLASSIC', 'SPRINT', 'ULTRA', 'SURVIVAL'):
            rng = random.Random(43)
            g = Game(mode, rng)
            for turn in range(200):
                if g.over:
                    break
                for _ in range(rng.randint(0, 3)):
                    g.move(rng.choice([-1, 1]))
                g.rotate(rng.choice([-1, 1]))
                g.hard_drop()
                if g.pending_rows:
                    g.resolve_clear()
                g.tick(.12)
                self.assertEqual(len(g.board), ROWS)
                self.assertTrue(all(len(row) == COLS for row in g.board))
                self.assertTrue(all(cell == 0 or cell in __import__('tetris_core').COLORS.values()
                                    for row in g.board for cell in row))
                if not g.over:
                    self.assertTrue(g.valid(g.x, g.y))

    def test_returning_to_menu_can_record_abandoned_game(self):
        with tempfile.TemporaryDirectory() as folder:
            s = Store(Path(folder))
            g = Game('CLASSIC')
            g.score = 666
            g.finish('Left game')
            s.record_game(g)
            self.assertEqual(Store(Path(folder)).records['CLASSIC']['score'], 666)
            self.assertEqual(Store(Path(folder)).stats['games'], 1)

    def test_session_saved_once(self):
        with tempfile.TemporaryDirectory() as d:
            s = Store(Path(d))
            g = Game()
            g.score = 5000
            g.over = True
            s.record_game(g)
            s.record_game(g)
            self.assertEqual(s.stats['games'], 1)
            self.assertIn('first_game', s.achievements)


if __name__ == '__main__':
    unittest.main()
