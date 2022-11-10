import sublime
from unittesting.helpers import TempDirectoryTestCase, OverridePreferencesTestCase
from ProjectManager.project_manager import Manager


import os
from unittest.mock import patch


class TestBasicFeatures(TempDirectoryTestCase, OverridePreferencesTestCase):
    override_preferences = {
        "project_manager.sublime-settings": {}
    }
    project_name = None

    @classmethod
    def setUpClass(cls):
        yield from super().setUpClass()
        cls.project_name = os.path.basename(cls._temp_dir)
        cls.manager = Manager(cls.window)

    @classmethod
    def tearDownClass(cls):
        yield from super().tearDownClass()
        if cls.project_name in cls.manager.projects_info.info():
            with patch("sublime.ok_cancel_dialog", return_value=True) as mocked:
                cls.manager.remove_project(cls.project_name)
                yield lambda: mocked.called

    def setUp(self):
        yield from self.__class__.setWindowFolder()

    def test_add_and_open_with_mock(self):
        def _window_show_input_panel(wid, caption, initial_text, on_done, on_change, on_cancel):
            sublime.set_timeout(lambda: on_done(initial_text), 100)
            return 0

        with patch("sublime_api.window_show_input_panel", _window_show_input_panel):
            self.window.run_command("project_manager", {"action": "create_project"})
            yield lambda: self.project_name in self.manager.projects_info.info()

        projects_info = self.manager.projects_info.info()

        self.assertTrue(self.project_name in projects_info)

        if sublime.version() >= '4000':
            def _window_show_quick_panel(wid, items, on_done, *args, **kwargs):
                index = next(i for i, item in enumerate(items)
                             if item[0].startswith(self.project_name))
                sublime.set_timeout(lambda: on_done(index), 100)
        else:
            def _window_show_quick_panel(wid, items, items_per_row, on_done, *args, **kwargs):
                index = next(int(i / items_per_row) for i, item in enumerate(items)
                             if i % items_per_row == 0 and item.startswith(self.project_name))
                sublime.set_timeout(lambda: on_done(index), 100)

        with patch("sublime_api.window_show_quick_panel", _window_show_quick_panel):
            with patch("sublime.ok_cancel_dialog", return_value=True):
                self.window.run_command("project_manager", {"action": "remove_project"})
                yield lambda: self.project_name not in self.manager.projects_info.info()
