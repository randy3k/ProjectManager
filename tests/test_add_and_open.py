import sublime
import sublime_api
import sublime_plugin
from unittesting.helpers import TempDirectoryTestCase, OverridePreferencesTestCase
from ProjectManager.project_manager import Manager


import os
from unittest import skipIf
from unittest.mock import patch

from contextlib import contextmanager


SELECT_NOT_AVAILABLE = "`select` is only available in Sublime Text 4."


@contextmanager
def widget_view_finder():
    last_view_id = [0]
    original_create_text_commands = sublime_plugin.create_text_commands

    def _create_text_commands(view_id):
        view = sublime.View(view_id)
        if view and view.settings().get("is_widget"):
            last_view_id[0] = view_id

        return original_create_text_commands(view_id)

    sublime_plugin.create_text_commands = _create_text_commands

    try:
        yield lambda: sublime.View(last_view_id[0])
    finally:
        sublime_plugin.create_text_commands = original_create_text_commands


class TestBasicFeatures(TempDirectoryTestCase, OverridePreferencesTestCase):
    override_preferences = {
        "project_manager.sublime-settings": {}
    }
    project_name = None
    last_view = [None]

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
                yield lambda: cls.project_name not in cls.manager.projects_info.info()

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

    @skipIf(sublime.version() < "4000", SELECT_NOT_AVAILABLE)
    def test_add_and_open_with_select(self):

        with widget_view_finder() as for_widget_view:
            self.window.run_command("project_manager", {"action": "add_project"})
            yield for_widget_view
            self.window.run_command("select")

        yield lambda: self.window.project_file_name() is not None

        projects_info = self.manager.projects_info.info()

        self.assertTrue(self.project_name in projects_info)

        # clear sidebar
        self.window.run_command('close_workspace')

        self.assertTrue(self.window.project_file_name() is None)

        with widget_view_finder() as for_widget_view:
            self.window.run_command("project_manager", {"action": "open_project"})
            view = yield for_widget_view
            yield 100
            view.run_command("insert", {"characters": self.project_name})
            self.window.run_command("select")

        yield lambda: self.window.project_file_name() is not None

        self.assertEqual(os.path.basename(self.window.folders()[0]), self.project_name)

        with widget_view_finder() as for_widget_view, \
                patch("sublime.ok_cancel_dialog", return_value=True):
            self.window.run_command("project_manager", {"action": "remove_project"})
            view = yield for_widget_view
            yield 100
            view.run_command("insert", {"characters": self.project_name})
            self.window.run_command("select")
            yield lambda: self.window.project_file_name() is None
