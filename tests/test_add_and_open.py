import sublime
import sublime_plugin
from unittesting.helpers import TempDirectoryTestCase, OverridePreferencesTestCase
from ProjectManager.project_manager import Manager


import os
import imp
import unittest
import unittest.mock


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_view[0] = None

    def active_widget_view(self):
        yield lambda: self.last_view[0] and self.last_view[0].settings().get("is_widget")
        return self.last_view[0]

    @unittest.skipIf(
        sublime.version() < "4000",
        "The `select` command is only avaiable in Sublime Text 4.")
    def test_add_and_open(self):
        yield 4000  # some warm up time
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

        with unittest.mock.patch("sublime.ok_cancel_dialog", return_value=True):

            self.window.run_command("project_manager", {"action": "remove_project"})
            view = yield from self.active_widget_view()
            view.run_command("insert", {"characters": self.project_name})
            self.window.run_command("select")

            yield lambda: self.window.project_file_name() is None



    def test_empty(self):
        self.assertTrue(True)
