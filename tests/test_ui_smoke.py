"""Headless interaction checks without requiring SDL or a display on the CI host."""
import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock
from tetris_core import Store


class Rect:
    def __init__(self, *args):
        if len(args) == 1:
            args = args[0]
        self.x, self.y, self.w, self.h = map(int, args)

    @property
    def centerx(self): return self.x + self.w//2
    @property
    def centery(self): return self.y + self.h//2
    @property
    def topleft(self): return self.x, self.y
    @topleft.setter
    def topleft(self, xy): self.x, self.y = xy
    @property
    def topright(self): return self.x+self.w, self.y
    @topright.setter
    def topright(self, xy): self.x, self.y = xy[0]-self.w, xy[1]
    @property
    def center(self): return self.centerx, self.centery
    @center.setter
    def center(self, xy): self.x, self.y = xy[0]-self.w//2, xy[1]-self.h//2
    def collidepoint(self, point):
        return self.x <= point[0] < self.x+self.w and self.y <= point[1] < self.y+self.h
    def inflate(self, w, h):
        return Rect(self.x-w//2, self.y-h//2, self.w+w, self.h+h)


class Surface:
    def __init__(self, size, *_args):
        self.w, self.h = size
    def convert(self): return self
    def fill(self, *args): pass
    def blit(self, *args): pass
    def get_size(self): return (self.w, self.h)
    def get_rect(self, **kwargs):
        obj = Rect(0, 0, self.w, self.h)
        if 'center' in kwargs:
            cx, cy = kwargs['center']; obj.x = cx-self.w//2; obj.y = cy-self.h//2
        if 'topleft' in kwargs:
            obj.x, obj.y = kwargs['topleft']
        return obj


class Font:
    def __init__(self, size): self.size = size
    def render(self, string, *_): return Surface((max(1, len(string)*self.size//2), self.size))


def fake_pygame():
    stub = types.ModuleType('pygame')
    stub.init = lambda: None
    stub.Rect = Rect
    stub.Surface = Surface
    stub.RESIZABLE = 1
    stub.FULLSCREEN = 2
    stub.SRCALPHA = 4
    stub.QUIT = 10
    stub.VIDEORESIZE = 11
    stub.MOUSEMOTION = 12
    stub.MOUSEBUTTONDOWN = 13
    stub.KEYDOWN = 14
    stub.KEYUP = 15
    stub.error = RuntimeError
    stub.display = types.SimpleNamespace(set_mode=lambda size, *_: Surface(size if size != (0,0) else (1024,768)),
                                         set_caption=lambda _: None, flip=lambda: None)
    stub.draw = types.SimpleNamespace(rect=lambda *a,**k: None, line=lambda *a,**k: None, circle=lambda *a,**k: None)
    stub.font = types.SimpleNamespace(SysFont=lambda _name, size, **k: Font(size))
    stub.key = types.SimpleNamespace(name=lambda key: key)
    stub.event = types.SimpleNamespace(get=lambda: [])
    stub.time = types.SimpleNamespace(Clock=lambda: types.SimpleNamespace(tick=lambda _: 16))
    stub.transform = types.SimpleNamespace(smoothscale=lambda _src, size: Surface(size))
    stub.quit = lambda: None
    return stub


class NoAudio:
    def __init__(self): pass
    def play(self, *args): pass
    def update(self, *args, **kwargs): pass


class UISmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with mock.patch.dict(sys.modules, {'pygame': fake_pygame()}):
            cls.module = importlib.import_module('tetris')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.patcher1 = mock.patch.object(self.module, 'Store', lambda: Store(self.folder))
        self.patcher2 = mock.patch.object(self.module, 'SoundManager', NoAudio)
        self.patcher1.start(); self.patcher2.start()
        self.addCleanup(self.patcher1.stop); self.addCleanup(self.patcher2.stop)
        self.app = self.module.DeluxeApp()

    def key(self, name):
        self.app.handle_key(types.SimpleNamespace(key=name))

    def test_every_screen_draws_and_settings_have_functional_keys(self):
        a = self.app
        for state in ('menu','modes','settings','stats','achievements'):
            a.state = state
            a.render()
            self.assertGreater(len(a.buttons), 0)
        a.state = 'settings'
        for tab in self.module.SETTINGS_TABS:
            a.change_tab(tab)
            a.render()
        a.change_tab('VISUAL')
        theme = a.settings['theme']
        self.key('right')
        self.assertNotEqual(theme, a.settings['theme'])
        a.change_tab('CONTROLS')
        self.key('return')
        self.assertEqual(a.capture_action, 'left')
        self.key('a')
        self.assertEqual(a.settings['controls']['left'], 'a')
        self.assertEqual(Store(self.folder).settings['controls']['left'], 'a')
        self.key('escape')
        self.assertEqual(a.state, 'menu')

    def test_game_to_pause_settings_and_result(self):
        a = self.app
        a.start('CLASSIC')
        a.render()
        self.key('p')
        self.assertEqual(a.state, 'paused')
        a.render()
        a.open_settings()
        a.render()
        a.settings_back()
        self.assertEqual(a.state, 'paused')
        a.go('playing')
        a.game.score = 800
        a.game.finish('Stack reached the top')
        a.consume_events()
        self.assertEqual(a.state, 'result')
        a.render()
        self.assertEqual(a.store.stats['games'], 1)
        self.assertEqual(a.store.records['CLASSIC']['score'], 800)
        a.go('menu')
        a.render()

    def test_navigation_and_abandon_stats(self):
        a = self.app
        self.key('down')
        self.assertEqual(a.menu_selected, 1)
        self.key('return')
        self.assertEqual(a.state, 'settings')
        self.key('escape')
        self.assertEqual(a.state, 'menu')
        a.start('ULTRA')
        a.game.score = 456
        a.abandon()
        self.assertEqual(a.state, 'menu')
        self.assertEqual(a.store.records['ULTRA']['score'], 456)
        self.assertEqual(a.store.stats['games'], 1)


if __name__ == '__main__':
    unittest.main()
