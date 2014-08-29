import sublime, sublime_plugin
import subprocess, os
import json, codecs
import random, string

class Jfile:
    def __init__(self, fpath, encoding="utf-8"):
        self.encoding = encoding
        self.fpath = fpath

    def load(self, default=[]):
        self.fdir = os.path.dirname(self.fpath)
        if not os.path.isdir(self.fdir):
            os.makedirs(self.fdir)
        if os.path.exists(self.fpath):
            f = codecs.open(self.fpath, "r+", encoding=self.encoding)
            try:
                data = json.load(f)
            except:
                data = default
            f.close()
        else:
            f = codecs.open(self.fpath, "w+", encoding=self.encoding)
            data = default
            f.close()
        return data

    def save(self, data, indent=4):
        self.fdir = os.path.dirname(self.fpath)
        if not os.path.isdir(self.fdir):
            os.makedirs(self.fdir)
        f = codecs.open(self.fpath, "w+", encoding=self.encoding)
        f.write(json.dumps(data, ensure_ascii=False, indent=indent))
        f.close()

    def remove(self):
        if os.path.exists(self.fpath): os.remove(self.fpath)

def subl(args=[]):
    # learnt from SideBarEnhancements
    executable_path = sublime.executable_path()
    if sublime.platform() == 'osx':
        app_path = executable_path[:executable_path.rfind(".app/")+5]
        executable_path = app_path+"Contents/SharedSupport/bin/subl"
    subprocess.Popen([executable_path]+args)

class Manager:
    def __init__(self, window):
        self.window = window
        self.projects_dir = os.path.join(sublime.packages_path(), "User", "Projects")

    def add_project(self):
        pd = self.window.project_data()
        if not pd:
            self.window.run_command("prompt_add_folder")

        def on_add(project):
            pd = self.window.project_data()

            sublime_project = os.path.join(self.projects_dir, "%s.sublime-project" % project)
            Jfile(sublime_project).save(pd)

            sublime_workspace = os.path.join(self.projects_dir, "%s.sublime-workspace" % project)
            Jfile(sublime_workspace).save({})
            self.switch_project(project)

        try:
            project = os.path.basename(pd["folders"][0]["path"])
        except:
            project = ""
        sublime.set_timeout(
            lambda: self.window.show_input_panel("Project name:", project, on_add, None, None),
            300)

    def list_projects(self):
        if os.path.exists(self.projects_dir):
            ret = []
            for f in os.listdir(self.projects_dir):
                if f.endswith(".sublime-project"):
                    pd = Jfile(os.path.join(self.projects_dir,f)).load()
                    if pd and "folders" in pd:
                        ret.append([f.replace(".sublime-project",""), pd["folders"][0]["path"]])
                    else:
                        ret.append([f.replace(".sublime-project",""),""])
            return ret
        else:
            return []

    def get_project_data(self, project):
        sublime_project = os.path.join(self.projects_dir, "%s.sublime-project" % project)
        return Jfile(sublime_project).load()

    def append_project(self, project):
        pd = self.get_project_data(project)
        paths = [f.get("path") for f in pd.get("folders")]
        subl(["-a"] + paths)

    def switch_project(self, project):
        self.window.run_command("close_workspace")
        sublime_project = os.path.join(self.projects_dir, "%s.sublime-project" % project)
        sublime.set_timeout_async(lambda: subl(["-a", "--project", sublime_project]), 300)

    def open_in_new_window(self, project):
        sublime_project = os.path.join(self.projects_dir, "%s.sublime-project" % project)
        subl(["-n", "--project", sublime_project])

    def remove_project(self, project):
        ok = sublime.ok_cancel_dialog("Remove Project %s?" % project)
        if ok:
            sublime_project = os.path.join(self.projects_dir, "%s.sublime-project" % project)
            sublime_workspace = os.path.join(self.projects_dir, "%s.sublime-workspace" % project)
            if self.window.project_file_name() == sublime_project:
                self.window.run_command("close_workspace")
            os.unlink(sublime_project)
            os.unlink(sublime_workspace)

    def edit_project(self, project):
        sublime_project = os.path.join(self.projects_dir, "%s.sublime-project" % project)
        self.window.open_file(sublime_project)

    def rename_project(self, project):
        def on_rename(new_project):
            sublime_project = os.path.join(self.projects_dir, "%s.sublime-project" % project)
            new_sublime_project = os.path.join(self.projects_dir, "%s.sublime-project" % new_project)
            sublime_workspace = os.path.join(self.projects_dir, "%s.sublime-workspace" % project)
            new_sublime_workspace = os.path.join(self.projects_dir, "%s.sublime-workspace" % new_project)
            if self.window.project_file_name() == sublime_project:
                reopen = True
                self.window.run_command("close_workspace")
            else:
                reopen = False
            os.rename(sublime_project, new_sublime_project)
            os.rename(sublime_workspace, new_sublime_workspace)
            try:
                j = Jfile(new_sublime_workspace)
                data = j.load()
                data["project"] = "%s.sublime-project" % new_project
                j.save(data)
            except:
                pass
            if reopen:
                self.switch_project(new_project)
        self.window.show_input_panel("New project name:", project, on_rename, None, None)


class ProjectManager(sublime_plugin.WindowCommand):

    def show_quick_panel(self, items, on_done):
        sublime.set_timeout(
            lambda: self.window.show_quick_panel(items, on_done),
            10)

    def run(self):
        self.manager = Manager(self.window)
        self.project_list = self.manager.list_projects()
        self.options = [
                ["[-] Project Manager", "More options"],
                ["[-] Add Project", "Add project to Project Manager"]
            ]

        self.show_quick_panel(self.options + self.project_list, self.on_open)

    def on_open(self, action):
        if action<0:
            return

        elif action==0:
            items = [
                ["Open Project", "Open project in current window"],
                ["Open Project in New Window", "Open project in a new window"],
                ["Append Project", "Append project to current window"],
                ["Edit Project", "Edit project settings"],
                ['Rename Project', "Rename project"],
                ["Remove Project", "Remove from Project Manager"]
            ]
            def callback(a):
                if a==0:
                    self.window.run_command("project_manager_list", args={"action": "switch"})
                elif a==1:
                    self.window.run_command("project_manager_list", args={"action": "new"})
                elif a==2:
                    self.window.run_command("project_manager_list", args={"action": "append"})
                elif a==3:
                    self.window.run_command("project_manager_list", args={"action": "edit"})
                elif a==4:
                    self.window.run_command("project_manager_list", args={"action": "rename"})
                elif a==5:
                    self.window.run_command("project_manager_list", args={"action": "remove"})
                else:
                    sublime.set_timeout(self.run, 10)

            self.show_quick_panel(items, callback)

        elif action==1:
            self.manager.add_project()

        elif action>=len(self.options):
            action = action-len(self.options)
            self.manager.switch_project(self.project_list[action][0])

class ProjectManagerAdd(sublime_plugin.WindowCommand):
    def run(self):
        self.manager = Manager(self.window)
        self.manager.add_project()

class ProjectManagerList(sublime_plugin.WindowCommand):

    def show_quick_panel(self, items, on_done):
        sublime.set_timeout(
            lambda: self.window.show_quick_panel(items, on_done),
            10)

    def run(self, action):
        self.manager = Manager(self.window)
        self.project_list = self.manager.list_projects()
        callback = eval("self.on_" + action)
        self.show_quick_panel(self.project_list, callback)

    def on_new(self, action):
        if action>=0:
            self.manager.open_in_new_window(self.project_list[action][0])

    def on_switch(self, action):
        if action>=0:
            self.manager.switch_project(self.project_list[action][0])

    def on_append(self, action):
        if action>=0:
            self.manager.append_project(self.project_list[action][0])

    def on_remove(self, action):
        if action>=0:
            self.manager.remove_project(self.project_list[action][0])

    def on_edit(self, action):
        if action>=0:
            self.manager.edit_project(self.project_list[action][0])

    def on_rename(self, action):
        if action>=0:
            self.manager.rename_project(self.project_list[action][0])
