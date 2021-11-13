import sublime
import sublime_plugin
from unittesting.helpers import TempDirectoryTestCase
from ProjectManager.project_manager import Manager


import os
import shutil
import imp

SETTINGS_FILENAME = 'project_manager.sublime-settings'


class TestBasicFeatures(TempDirectoryTestCase):
    pm_settings_path = None
    new_pm_settings_path = None
    project_name = None

    @classmethod
    def setUpClass(cls):
        yield from super().setUpClass()
        # need to remove my own preference for local testing
        cls.pm_settings_path = os.path.join(sublime.packages_path(), "User", SETTINGS_FILENAME)
        cls.new_pm_settings_path = os.path.join(
            sublime.packages_path(), "User", SETTINGS_FILENAME + ".bak")
        if os.path.exists(cls.pm_settings_path):
            shutil.move(cls.pm_settings_path, cls.new_pm_settings_path)
            with open(cls.pm_settings_path, "w") as f:
                f.write("{}")
            yield lambda: sublime.load_settings(SETTINGS_FILENAME).get("projects") == "$default"
        cls.project_name = os.path.basename(cls._temp_dir)
        cls.manager = Manager(cls.window)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.new_pm_settings_path):
            shutil.move(cls.new_pm_settings_path, cls.pm_settings_path)
        super().tearDownClass()

    def test_add_and_open(self):
        last_view = [None]
        capture_widget = type(
            "capture_widget",
            (sublime_plugin.EventListener,),
            {"on_activated": lambda self, view: last_view.__setitem__(0, view)})
        m = imp.new_module("capture_widget")
        m.capture_widget = capture_widget
        sublime_plugin.load_module(m)

        self.window.run_command("project_manager", {"action": "add_project"})
        yield lambda: last_view[0] and last_view[0].settings().get("is_widget")
        self.window.run_command("select")

        yield lambda: self.window.project_file_name() is not None

        projects_info = self.manager.projects_info.info()

        self.assertTrue(self.project_name in projects_info)

        # clear sidebar
        self.window.run_command('close_workspace')

        self.assertTrue(self.window.project_file_name() is None)

        self.window.run_command("project_manager", {"action": "switch"})
        yield lambda: last_view[0] and last_view[0].settings().get("is_widget")
        last_view[0].run_command("insert", {"characters": self.project_name})
        self.window.run_command("select")

        yield lambda: self.window.project_file_name() is not None

        self.assertEqual(os.path.basename(self.window.folders()[0]), self.project_name)

        original_ok_cancel_dialog = sublime.ok_cancel_dialog
        sublime.ok_cancel_dialog = lambda _: True

        self.window.run_command("project_manager", {"action": "remove"})
        yield lambda: last_view[0] and last_view[0].settings().get("is_widget")
        last_view[0].run_command("insert", {"characters": self.project_name})
        self.window.run_command("select")

        yield lambda: self.window.project_file_name() is None

        sublime.ok_cancel_dialog = original_ok_cancel_dialog
        sublime_plugin.unload_module(m)
