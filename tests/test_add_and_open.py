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
        if cls.project_name in cls.manager.projects_info.info:
            with patch("sublime.ok_cancel_dialog", return_value=True) as mocked:
                cls.manager.remove_project(cls.project_name)
                yield lambda: mocked.called

    def setUp(self):
        yield from self.__class__.setWindowFolder()

    def get_new_window(self, wids):
        for window in sublime.windows():
            if window.id() not in wids:
                return window

    def get_ws_names(self):
        wfiles = self.manager.projects_info.info[self.project_name]["workspaces"]
        return map(lambda wfile: os.path.basename(wfile)[:-18], wfiles)

    def get_wfile(self, wname):
        for wfile in self.manager.projects_info.info[self.project_name]["workspaces"]:
            if os.path.basename(wfile)[:-18] == wname:
                return wfile

    def test_add_and_open_with_mock(self):
        self.window.run_command("close_project")

        # Create project
        self.window.run_command("project_manager", {"action": "create_project",
                                                    "value": self.project_name})
        yield lambda: self.project_name in self.manager.projects_info.info

        # Open project in new window
        wids = set(map(lambda w: w.id(), sublime.windows()))
        self.window.run_command("project_manager", {"action": "open_project",
                                                    "project": self.project_name})
        yield lambda: len(sublime.windows()) == len(wids) + 1

        # Close current window and switch to newly open project
        self.window.run_command("close_window")
        self.window = self.get_new_window(wids)
        yield lambda: self.window.project_file_name() is not None

        # Edit project
        self.window.run_command("project_manager", {"action": "edit_project",
                                                    "project": self.project_name})
        pfile = self.manager.projects_info.info[self.project_name]["file"]
        yield lambda: len(self.window.views()) > 0
        yield lambda: self.window.views()[0].file_name() == pfile
        self.window.run_command("close_file")

        # Add a description to the project
        desc = "This is a test project"
        self.window.run_command("project_manager", {"action": "set_description",
                                                    "project": self.project_name,
                                                    "value": desc})
        yield lambda: os.path.exists(self.manager.desc_path)
        yield lambda: desc in open(self.manager.desc_path).read()

        # Rename project...
        self.window.run_command("project_manager", {"action": "rename_project",
                                                    "project": self.project_name,
                                                    "value": "123tmp_proj890"})
        yield os.path.exists(self.manager.projects_info.info["123tmp_proj890"]["file"])

        # ...and undo
        self.window.run_command("project_manager", {"action": "rename_project",
                                                    "project": "123tmp_proj890",
                                                    "value": self.project_name})
        yield os.path.exists(self.manager.projects_info.info[self.project_name]["file"])

        # Add a new workspace
        new_wname = "test_ws"
        wids = set(map(lambda w: w.id(), sublime.windows()))
        self.window.run_command("project_manager", {"action": "add_workspace",
                                                    "project": self.project_name,
                                                    "value": new_wname})
        yield lambda: len(self.manager.projects_info.info[self.project_name]["workspaces"]) == 2
        yield lambda: len(sublime.windows()) == len(wids) + 1

        # Close this new workspace
        new_ws_window = self.get_new_window(wids)
        new_ws_window.run_command("close_window")
        yield lambda: len(sublime.windows()) == len(wids)

        # Next set of tests only seems to work locally, not on github

        # if sublime.version() > '4050':      # Need to get workspace file name to work
        #     # Switch to this workspace via `open_project` cmd
        #     self.window.run_command("project_manager", {"action": "open_project",
        #                                                 "workspace": new_wname})
        #     yield lambda: self.manager.is_workspace_open(self.get_wfile(new_wname))

        #     # Switch back to default workspace via `open_workspace` cmd
        #     self.window.run_command("project_manager", {"action": "open_workspace",
        #                                                 "workspace": self.project_name})
        #     yield lambda: self.manager.is_workspace_open(self.get_wfile(self.project_name))

        # # Rename the workspace
        # self.window.run_command("project_manager", {"action": "rename_workspace",
        #                                             "workspace": new_wname,
        #                                             "value": "renamed_ws"})
        # yield lambda: len(self.manager.projects_info.info[self.project_name]["workspaces"]) == 2
        # new_wname = "renamed_ws"
        # yield lambda: new_wname in self.get_ws_names()

        # # Remove the renamed workspace
        # with patch("sublime.ok_cancel_dialog", return_value=True):
        #     self.window.run_command("project_manager", {"action": "remove_workspace",
        #                                                 "workspace": new_wname})
        #     yield lambda: len(self.manager.projects_info.info[self.project_name]["workspaces"]) == 1

        # Remove the project
        with patch("sublime.ok_cancel_dialog", return_value=True):
            self.window.run_command("project_manager", {"action": "remove_project",
                                                        "project": self.project_name})
            yield lambda: self.project_name not in self.manager.projects_info.info

        # Close testing window
        self.window.run_command("close_window")
