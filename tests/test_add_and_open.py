import sublime
import sublime_api
import sublime_plugin
from unittesting.helpers import TempDirectoryTestCase, OverridePreferencesTestCase
from ProjectManager.project_manager import Manager


import os
import imp
from unittest import skipIf
from unittest.mock import patch


SELECT_NOT_AVAILABLE = "`select` is only available in Sublime Text 4."


class TestBasicFeatures(TempDirectoryTestCase, OverridePreferencesTestCase):
    override_preferences = {
        "project_manager.sublime-settings": {}
    }
    project_name = None
    last_view = [None]

    @classmethod
    def setUpClass(cls):
        capture_event_listener = type(
            "capture_event_listener",
            (sublime_plugin.EventListener,),
            {"on_activated": lambda self, view: cls.last_view.__setitem__(0, view)})
        capture_module = imp.new_module("capture")
        capture_module.capture_event_listener = capture_event_listener
        sublime_plugin.load_module(capture_module)
        cls.capture_module = capture_module
        yield 100
        yield from TempDirectoryTestCase.setUpClass.__func__(cls)
        yield from OverridePreferencesTestCase.setUpClass.__func__(cls)
        cls.project_name = os.path.basename(cls._temp_dir)
        cls.manager = Manager(cls.window)

    @classmethod
    def tearDownClass(cls):
        sublime_plugin.unload_module(cls.capture_module)
        TempDirectoryTestCase.tearDownClass.__func__(cls)
        OverridePreferencesTestCase.tearDownClass.__func__(cls)

        if cls.project_name in cls.manager.projects_info.info():
            with patch("sublime.ok_cancel_dialog", return_value=True):
                cls.manager.remove_project(cls.project_name)
                yield cls.project_name not in cls.manager.projects_info.info()

    def setUp(self):
        yield from self.__class__.setWindowFolder()

    def active_widget_view(self):
        yield lambda: self.last_view[0] and self.last_view[0].settings().get("is_widget")
        return self.last_view[0]

    @skipIf(sublime.version() < "4000", SELECT_NOT_AVAILABLE)
    def test_add_and_open(self):
        self.window.run_command("project_manager", {"action": "add_project"})
        yield from self.active_widget_view()
        self.window.run_command("select")

        yield lambda: self.window.project_file_name() is not None

        projects_info = self.manager.projects_info.info()

        self.assertTrue(self.project_name in projects_info)

        # clear sidebar
        self.window.run_command('close_workspace')

        self.assertTrue(self.window.project_file_name() is None)

        self.window.run_command("project_manager", {"action": "open_project"})
        view = yield from self.active_widget_view()
        view.run_command("insert", {"characters": self.project_name})
        self.window.run_command("select")

        yield lambda: self.window.project_file_name() is not None

        self.assertEqual(os.path.basename(self.window.folders()[0]), self.project_name)

        with patch("sublime.ok_cancel_dialog", return_value=True):
            self.window.run_command("project_manager", {"action": "remove_project"})
            view = yield from self.active_widget_view()
            view.run_command("insert", {"characters": self.project_name})
            self.window.run_command("select")
            yield lambda: self.window.project_file_name() is None

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
