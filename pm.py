import sublime, sublime_plugin
import subprocess, os
import json, codecs, re
import copy

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
            content = f.read()
            content = re.sub(r'^\s*//.*?$|^\s*/\*(?:.|\n)*?\*/', '', content, flags=re.MULTILINE)
            try:
                data = json.loads(content)
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

    def sublime_project(self, project):
        return os.path.join(self.projects_dir, "%s.sublime-project" % project)

    def sublime_workspace(self, project):
        return os.path.join(self.projects_dir, "%s.sublime-workspace" % project)

    def add_project(self):
        pd = self.window.project_data()
        if not pd:
            self.window.run_command("prompt_add_folder")
            delay = 300
        else:
            delay = 1

        def on_add(project):
            pd = self.window.project_data()
            Jfile(self.sublime_project(project)).save(pd)
            Jfile(self.sublime_workspace(project)).save({})
            self.window.run_command("close_workspace")
            self.window.run_command("close_project")
            for v in self.window.views():
                if not v.is_dirty():
                    self.window.focus_view(v)
                    self.window.run_command("close")
            self.switch_project(project)

        def show_input_panel():
            pd = self.window.project_data()
            if pd:
                project = os.path.basename(pd["folders"][0]["path"])
                v = self.window.show_input_panel("Project name:", project, on_add, None, None)
                v.run_command("select_all")

        sublime.set_timeout(show_input_panel, delay)


    def list_projects(self):
        if os.path.exists(self.projects_dir):
            ret = []
            for f in os.listdir(self.projects_dir):
                if f.endswith(".sublime-project"):
                    pd = Jfile(os.path.join(self.projects_dir,f)).load()
                    if pd and "folders" in pd and pd["folders"]:
                        ret.append([f.replace(".sublime-project",""), pd["folders"][0].get("path", "")])
                    else:
                        ret.append([f.replace(".sublime-project",""),""])
            return ret
        else:
            return []

    def get_project_data(self, project):
        return Jfile(self.sublime_project(project)).load()

    def check_project(self, project):
        if not os.path.exists(self.sublime_workspace(project)):
            Jfile(self.sublime_workspace).save({})

    def close_project(self, project):
        for w in sublime.windows():
            if w.project_file_name() == self.sublime_project(project):
                w.run_command("close_workspace")
                w.run_command("close_window")
                return True
        return False

    def append_project(self, project):
        pd = self.get_project_data(project)
        paths = [f.get("path") for f in pd.get("folders")]
        subl(["-a"] + paths)

    def switch_project(self, project):
        self.window.run_command("close_workspace")
        self.check_project(project)
        if self.close_project(project):
            sublime.set_timeout_async(lambda: subl(["-n", self.sublime_project(project)]), 300)
            return

        if len(self.window.views())==0:
            sublime.set_timeout_async(lambda: subl([self.sublime_project(project)]), 300)
        else:
            sublime.set_timeout_async(lambda: subl(["-n", self.sublime_project(project)]), 300)

    def open_in_new_window(self, project):
        self.check_project(project)
        self.close_project(project)
        sublime.set_timeout_async(lambda: subl(["-n", self.sublime_project(project)]), 300)

    def remove_project(self, project):
        ok = sublime.ok_cancel_dialog("Remove Project %s?" % project)
        if ok:
            self.close_project(project)
            os.unlink(self.sublime_project(project))
            os.unlink(self.sublime_workspace(project))

    def edit_project(self, project):
        self.window.open_file(self.sublime_project(project))

    def rename_project(self, project):
        def on_rename(new_project):
            sublime_project = self.sublime_project(project)
            new_sublime_project = self.sublime_project(new_project)
            sublime_workspace = self.sublime_workspace(project)
            new_sublime_workspace = self.sublime_workspace(new_project)
            if self.close_project(project):
                reopen = True
            else:
                reopen = False
            os.rename(sublime_project, new_sublime_project)
            os.rename(sublime_workspace, new_sublime_workspace)
            try:
                j = Jfile(new_sublime_workspace)
                data = j.load({})
                data["project"] = "%s.sublime-project" % new_project
                j.save(data)
            except:
                pass
            if reopen:
                self.open_in_new_window(new_project)
        self.window.show_input_panel("New project name:", project, on_rename, None, None)


class ProjectManager(sublime_plugin.WindowCommand):

    def show_quick_panel(self, items, on_done):
        sublime.set_timeout(
            lambda: self.window.show_quick_panel(items, on_done),
            10)

    def run(self, action=None):
        self.manager = Manager(self.window)
        self.project_list = self.manager.list_projects()
        self.options = [
                ["[-] Project Manager", "More options"],
                ["[-] Add Project", "Add project to Project Manager"]
            ]
        display = copy.deepcopy(self.project_list)
        for i, item in enumerate(self.project_list):
            pfn = self.manager.sublime_project(item[0])
            for w in sublime.windows():
                if w.project_file_name() == pfn:
                    display[i][0] = display[i][0] + "*"
        if action is not None:
            sublime.set_timeout(lambda: self.on_open(action), 10)
        else:
            self.show_quick_panel(self.options + display, self.on_open)

    def on_open(self, action):
        if action<0:
            return

        elif action==0:
            items = [
                ["Open Project in New Window", "Open project in a new window"],
                ["Append Project", "Append project to current window"],
                ["Edit Project", "Edit project settings"],
                ['Rename Project', "Rename project"],
                ["Remove Project", "Remove from Project Manager"]
            ]
            def callback(a):
                if a==0:
                    self.window.run_command("project_manager_list", args={"action": "new", "caller" : "manager"})
                elif a==1:
                    self.window.run_command("project_manager_list", args={"action": "append", "caller" : "manager"})
                elif a==2:
                    self.window.run_command("project_manager_list", args={"action": "edit", "caller" : "manager"})
                elif a==3:
                    self.window.run_command("project_manager_list", args={"action": "rename", "caller" : "manager"})
                elif a==4:
                    self.window.run_command("project_manager_list", args={"action": "remove", "caller" : "manager"})
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

    def run(self, action, caller=None):
        self.caller = caller
        callback = eval("self.on_" + action)
        self.manager = Manager(self.window)
        self.project_list = self.manager.list_projects()
        display = copy.deepcopy(self.project_list)
        for i, item in enumerate(self.project_list):
            pfn = self.manager.sublime_project(item[0])
            for w in sublime.windows():
                if w.project_file_name() == pfn:
                    display[i][0] = display[i][0] + "*"
        self.show_quick_panel(display, callback)

    def on_new(self, action):
        if action>=0:
            self.manager.open_in_new_window(self.project_list[action][0])
        elif action<0:
            sublime.set_timeout(self.on_cancel, 10)

    def on_switch(self, action):
        if action>=0:
            self.manager.switch_project(self.project_list[action][0])
        elif action<0:
            self.on_cancel()

    def on_append(self, action):
        if action>=0:
            self.manager.append_project(self.project_list[action][0])
        elif action<0:
            self.on_cancel()

    def on_remove(self, action):
        if action>=0:
            sublime.set_timeout(lambda:
                self.manager.remove_project(self.project_list[action][0]),
                10)
        elif action<0:
            self.on_cancel()

    def on_edit(self, action):
        if action>=0:
            self.manager.edit_project(self.project_list[action][0])
        elif action<0:
            self.on_cancel()

    def on_rename(self, action):
        if action>=0:
            sublime.set_timeout(lambda:
                self.manager.rename_project(self.project_list[action][0]),
                10)
        elif action<0:
            self.on_cancel()

    def on_cancel(self):
        if self.caller == "manager":
            self.window.run_command("project_manager", args={"action": 0})
