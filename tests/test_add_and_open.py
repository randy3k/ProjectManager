import sublime
import sublime_api
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
        yield from TempDirectoryTestCase.setUpClass.__func__(cls)
        yield from OverridePreferencesTestCase.setUpClass.__func__(cls)
        cls.project_name = os.path.basename(cls._temp_dir)
        cls.manager = Manager(cls.window)

    @classmethod
    def tearDownClass(cls):
        TempDirectoryTestCase.tearDownClass.__func__(cls)
        OverridePreferencesTestCase.tearDownClass.__func__(cls)

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

        with patch.object(sublime_api, "window_show_input_panel", _window_show_input_panel):
            self.window.run_command("project_manager", {"action": "add_project"})

            yield lambda: self.window.project_file_name() is not None

        projects_info = self.manager.projects_info.info()

        self.assertTrue(self.project_name in projects_info)

        # clear sidebar
        self.window.run_command('close_workspace')

        self.assertTrue(self.window.project_file_name() is None)

        if sublime.version() >= '4000':
            def _window_show_quick_panel(wid, items, on_done, *args, **kwargs):
                index = next(i for i, item in enumerate(items)
                             if item[0].startswith(self.project_name))
                sublime.set_timeout(lambda: on_done(index), 100)
                return 0
        else:
            def _window_show_quick_panel(wid, items, items_per_row, on_done, *args, **kwargs):
                index = next(int(i / items_per_row) for i, item in enumerate(items)
                             if i % items_per_row == 0 and item.startswith(self.project_name))
                sublime.set_timeout(lambda: on_done(index), 100)
                return 0

        with patch.object(sublime_api, "window_show_quick_panel", _window_show_quick_panel):
            self.window.run_command("project_manager", {"action": "open_project"})
            yield lambda: self.window.project_file_name() is not None

        self.assertEqual(os.path.basename(self.window.folders()[0]), self.project_name)

        with patch.object(sublime_api, "window_show_quick_panel", _window_show_quick_panel):
            with patch("sublime.ok_cancel_dialog", return_value=True):
                self.window.run_command("project_manager", {"action": "remove_project"})
                yield lambda: self.window.project_file_name() is None
