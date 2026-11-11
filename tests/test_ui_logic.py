import math
import unittest

from tetris_ui_logic import adjust_setting, rebind_control, format_time
from tetris_audio import synth_wave
from tetris_core import DEFAULT_SETTINGS


class SettingsTests(unittest.TestCase):
    def test_cycling_theme(self):
        s = DEFAULT_SETTINGS.copy()
        adjust_setting(s, 'theme', 1)
        self.assertEqual(s['theme'], 'Classic')
        adjust_setting(s, 'theme', -1)
        self.assertEqual(s['theme'], 'Neon')

    def test_cycle_difficulty_and_speed_limits(self):
        s = DEFAULT_SETTINGS.copy()
        adjust_setting(s, 'difficulty', -1)
        self.assertEqual(s['difficulty'], 'easy')
        s['speed'] = 2.0
        adjust_setting(s, 'speed', 1)
        self.assertEqual(s['speed'], 2.0)

    def test_volume_and_bool(self):
        s = DEFAULT_SETTINGS.copy()
        s['sfx_volume'] = 1.0
        adjust_setting(s, 'sfx_volume', 1)
        self.assertEqual(s['sfx_volume'], 1.0)
        adjust_setting(s, 'ghost', 1)
        self.assertFalse(s['ghost'])

    def test_rebind_swaps_conflicting_keys(self):
        s = {'controls': DEFAULT_SETTINGS['controls'].copy()}
        rebind_control(s, 'rotate', 'left')
        self.assertEqual(s['controls']['rotate'], 'left')
        self.assertEqual(s['controls']['left'], 'up')

    def test_rebind_rejects_empty_and_duplicate_unmapped(self):
        s = {'controls': DEFAULT_SETTINGS['controls'].copy()}
        self.assertFalse(rebind_control(s, 'rotate', ''))
        self.assertFalse(rebind_control(s, 'something', 'z'))
        self.assertEqual(s['controls']['rotate'], 'up')

    def test_clock_format(self):
        self.assertEqual(format_time(66.25), '01:06')

    def test_audio_buffer_is_16_bit_stereo(self):
        data = synth_wave([440], 0.1, 22050)
        self.assertEqual(len(data), 2205 * 2 * 2)
        self.assertNotEqual(data[:100], bytes(100))


if __name__ == '__main__':
    unittest.main()
