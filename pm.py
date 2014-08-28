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

class Manager:
    def __init__(self, window):
        self.window = window
        self.projects_dir = os.path.join(sublime.packages_path(), "User", "Projects")

    def add_project(self):
        pd = self.window.project_data()
        if not pd:
            sublime.message_dialog("Add some folders!")
            return

        def on_add(project):
            sublime_project = os.path.join(self.projects_dir, "%s.sublime-project" % project)
            Jfile(sublime_project).save(pd)

            sublime_workspace = os.path.join(self.projects_dir, "%s.sublime-workspace" % project)
            Jfile(sublime_workspace).save({})
            self.switch_project(project, close=False)

        self.window.show_input_panel("Project name:", "", on_add, None, None)


    def list_projects(self):
        if os.path.exists(self.projects_dir):
            ret = []
            for f in os.listdir(self.projects_dir):
                if f.endswith(".sublime-project"):
                    pd = Jfile(os.path.join(self.projects_dir,f)).load()
                    if "folders" in pd:
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
        # learnt from SideBarEnhancements
        executable_path = sublime.executable_path()
        if sublime.platform() == 'osx':
            app_path = executable_path[:executable_path.rfind(".app/")+5]
            executable_path = app_path+"Contents/SharedSupport/bin/subl"

        pd = self.get_project_data(project)
        paths = [f.get("path") for f in pd.get("folders")]
        subprocess.Popen([executable_path, "-a"] + paths, cwd=paths[0])

    def switch_project(self, project, close=True):
        # learnt from SideBarEnhancements
        if close:
            self.window.run_command("close_workspace")
            # self.window.run_command("close_project")
        def on_switch():
            executable_path = sublime.executable_path()
            if sublime.platform() == 'osx':
                app_path = executable_path[:executable_path.rfind(".app/")+5]
                executable_path = app_path+"Contents/SharedSupport/bin/subl"

            sublime_project = os.path.join(self.projects_dir, "%s.sublime-project" % project)
            subprocess.Popen([executable_path, "-a", "--project", sublime_project])

        sublime.set_timeout(on_switch, 100)


    def open_in_new_window(self, project):
        executable_path = sublime.executable_path()
        if sublime.platform() == 'osx':
            app_path = executable_path[:executable_path.rfind(".app/")+5]
            executable_path = app_path+"Contents/SharedSupport/bin/subl"

        sublime_project = os.path.join(self.projects_dir, "%s.sublime-project" % project)
        subprocess.Popen([executable_path, "-n", "--project", sublime_project])

    def remove_project(self, project):
        ok = sublime.ok_cancel_dialog("Remove Project %s?" % project)
        if ok:
            sublime_project = os.path.join(self.projects_dir, "%s.sublime-project" % project)
            sublime_workspace = os.path.join(self.projects_dir, "%s.sublime-workspace" % project)
            if self.window.project_file_name() == sublime_project:
                self.window.run_command("close_all")
                self.window.run_command("close_workspace")
                self.window.run_command("close_project")
            os.unlink(sublime_project)
            os.unlink(sublime_workspace)

    def edit_project(self, project):
        sublime_project = os.path.join(self.projects_dir, "%s.sublime-project" % project)
        self.window.open_file(sublime_project)

class ProjectManager(sublime_plugin.WindowCommand):

    def show_quick_panel(self, items, on_done):
        sublime.set_timeout(
            lambda: self.window.show_quick_panel(items, on_done),
            100)

    def run(self, action=None):
        self.manager = Manager(self.window)
        self.callback_on_cancel = action is None
        self.project_list = self.manager.list_projects()
        self.options = [
                ["[-] List Projects", "List all projects"],
                ["[-] Add Project", "Add project to Project Manager"],
                ["[-] Append Project", "Append a project in current window"],
                ["[-] Edit Project", "Edit project settings"],
                ["[-] Remove Project", "Remove a project from Project Manager"]
            ]

        if action is not None:
            self.on_open(action)
        else:
            self.show_quick_panel(self.options + self.project_list, self.on_open)

    def on_open(self, action):
        if action<0:
            return

        elif action==0:
            self.show_quick_panel(self.project_list, self.on_list)

        elif action==1:
            self.manager.add_project()

        elif action==2:
            self.show_quick_panel(self.project_list, self.on_append)

        elif action==3:
            self.show_quick_panel(self.project_list, self.on_edit)

        elif action==4:
            self.show_quick_panel(self.project_list, self.on_remove)

        elif action>=len(self.options):
            action = action-len(self.options)
            self.manager.switch_project(self.project_list[action][0])

    def on_append(self, action):
        if action>=0:
            self.manager.append_project(self.project_list[action][0])
        elif self.callback_on_cancel:
            sublime.set_timeout(self.run, 100)

    def on_remove(self, action):
        if action>=0:
            self.manager.remove_project(self.project_list[action][0])
        elif self.callback_on_cancel:
            sublime.set_timeout(self.run, 100)

    def on_edit(self, action):
        if action>=0:
            self.manager.edit_project(self.project_list[action][0])
        elif self.callback_on_cancel:
            sublime.set_timeout(self.run, 100)

    def on_list(self, action):
        if action>=0:
            items = [
                ["Open", "Open in current window"],
                ["Open in new window", "Open in a new window"],
                ["Append", "Append to current window"],
                ["Edit", "Edit project settings"],
                ["Remove", "Remove from Project Manager"]
            ]
            project = self.project_list[action][0]
            def callback(a):
                if a==0:
                    self.manager.switch_project(project)
                elif a==1:
                    self.manager.open_in_new_window(project)
                elif a==2:
                    self.manager.append_project(project)
                elif a==3:
                    self.manager.edit_project(project)
                elif a==4:
                    self.manager.remove_project(project)
                else:
                    self.show_quick_panel(self.project_list, self.on_list)

            self.show_quick_panel(items, callback)

        elif self.callback_on_cancel:
            sublime.set_timeout(self.run, 100)
