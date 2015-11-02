import sublime
import sublime_plugin
import subprocess
import os
import codecs
import platform


class JsonFile:
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
            try:
                data = sublime.decode_value(content)
            except:
                sublime.message_dialog("%s is bad!" % self.fpath)
                raise
            if not data:
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
        f.write(sublime.encode_value(data, True))
        f.close()

    def remove(self):
        if os.path.exists(self.fpath):
            os.remove(self.fpath)


def subl(args=[]):
    # learnt from SideBarEnhancements
    executable_path = sublime.executable_path()
    if sublime.platform() == 'osx':
        app_path = executable_path[:executable_path.rfind(".app/") + 5]
        executable_path = app_path + "Contents/SharedSupport/bin/subl"
    subprocess.Popen([executable_path] + args)


def pabs(folder, project_file):
    root = os.path.dirname(project_file)
    if not os.path.isabs(folder):
        folder = os.path.abspath(os.path.join(root, folder))
    return folder


def get_node():
    if sublime.platform() == "osx":
        node = subprocess.check_output(["scutil", "--get", "ComputerName"]).decode().strip()
    else:
        node = platform.node().split(".")[0]
    return node


class Manager:
    def __init__(self, window):
        self.window = window
        settings_file = 'pm.sublime-settings'
        self.settings = sublime.load_settings(settings_file)
        default_projects_dir = os.path.join(sublime.packages_path(), "User", "Projects")
        self.projects_fpath = self.settings.get(
            "projects_fpath", [self.settings.get("projects_dir", default_projects_dir)])

        self.projects_fpath = [os.path.expanduser(d) for d in self.projects_fpath]

        node = get_node()
        if self.settings.get("use_local_projects_dir", False):
            self.projects_fpath = \
                [d + " - " + node for d in self.projects_fpath] + self.projects_fpath

        self.primary_dir = self.projects_fpath[0]
        self.projects_info = self.get_projects_info()

    def get_projects_info(self):
        ret = {}
        for pdir in self.projects_fpath:
            pfiles = []
            j = JsonFile(os.path.join(pdir, "library.json"))
            for f in j.load([]):
                if os.path.exists(f) and f not in pfiles:
                    pfiles.append(f)
            pfiles.sort()
            j.save(pfiles)
            for path, dirs, files in os.walk(pdir, followlinks=True):
                for f in files:
                    f = os.path.join(path, f)
                    if f.endswith(".sublime-project") and f not in pfiles:
                        pfiles.append(f)
                # remove empty directories
                for d in dirs:
                    d = os.path.join(path, d)
                    if len(os.listdir(d)) == 0:
                        os.rmdir(d)

            for f in pfiles:
                pdir = self.which_projects_dir(f)
                if pdir:
                    pname = os.path.relpath(f, pdir).replace(".sublime-project", "")
                else:
                    pname = os.path.basename(f).replace(".sublime-project", "")
                pd = JsonFile(f).load()
                if pd and "folders" in pd and pd["folders"]:
                    folder = pd["folders"][0].get("path", "")
                else:
                    folder = ""
                star = False
                for w in sublime.windows():
                    if w.project_file_name() == f:
                        star = True
                        break
                ret[pname] = {
                    "folder": pabs(folder, f),
                    "file": f,
                    "star": star
                }
        return ret

    def which_projects_dir(self, pfile):
        for pdir in self.projects_fpath:
            if (os.path.dirname(pfile)+os.path.sep).startswith(pdir+os.path.sep):
                return pdir
        return None

    def display_projects(self):
        ret = [[key, key + "*" if value["star"] else key, value["folder"]]
               for key, value in self.projects_info.items()]
        ret = sorted(ret)
        count = 0
        for i in range(len(ret)):
            if ret[i][0] is not ret[i][1]:
                ret.insert(count, ret.pop(i))
                count = count + 1
        return [[item[0] for item in ret], [[item[1], item[2]] for item in ret]]

    def project_file_name(self, project):
        return self.projects_info[project]["file"]

    def project_workspace(self, project):
        return self.project_file_name(project).replace(".sublime-project", ".sublime-workspace")

    def add_project(self):
        def on_add(project):
            pd = self.window.project_data()
            f = os.path.join(self.primary_dir, "%s.sublime-project" % project)
            if pd:
                JsonFile(f).save(pd)
            else:
                JsonFile(f).save({})
            JsonFile(f.replace(".sublime-project", ".sublime-workspace")).save({})
            self.window.run_command("close_workspace")
            self.window.run_command("close_project")
            for v in self.window.views():
                if not v.is_dirty():
                    self.window.focus_view(v)
                    self.window.run_command("close")

            # reload projects info
            self.__init__(self.window)
            self.switch_project(project)

        def show_input_panel():
            pd = self.window.project_data()
            pf = self.window.project_file_name()
            if pd:
                if pf:
                    project = os.path.basename(pabs(pd["folders"][0]["path"], pf))
                else:
                    project = os.path.basename(pd["folders"][0]["path"])
            else:
                project = "New Project"
            v = self.window.show_input_panel("Project name:", project, on_add, None, None)
            v.run_command("select_all")

        sublime.set_timeout(show_input_panel, 100)

    def import_sublime_project(self):
        pfile = self.window.project_file_name()
        if not pfile:
            sublime.message_dialog("Project file not found!")
            return
        if self.which_projects_dir(pfile):
            sublime.message_dialog("This project was created by Project Manager!")
            return
        ok = sublime.ok_cancel_dialog("Import %s?" % os.path.basename(pfile))
        if ok:
            j = JsonFile(os.path.join(self.primary_dir, "library.json"))
            data = j.load([])
            if pfile not in data:
                data.append(pfile)
                j.save(data)

    def get_project_data(self, project):
        return JsonFile(self.project_file_name(project)).load()

    def check_project(self, project):
        wsfile = self.project_workspace(project)
        j = JsonFile(wsfile)
        if not os.path.exists(wsfile):
            j.save({})
        else:
            show_open_files = self.settings.get("show_open_files", False)
            data = j.load({})
            data["show_open_files"] = show_open_files
            df = data.get("distraction_free", {})
            df["show_open_files"] = show_open_files
            data["distraction_free"] = df
            j.save(data)

    def close_project(self, project):
        for w in sublime.windows():
            if w.project_file_name() == self.project_file_name(project):
                w.run_command("close_workspace")
                w.run_command("close_window")
                return True
        return False

    def append_project(self, project):
        pd = self.get_project_data(project)
        paths = [pabs(f.get("path"), self.project_file_name(project)) for f in pd.get("folders")]
        subl(["-a"] + paths)

    def switch_project(self, project):
        settings = sublime.load_settings("Preferences.sublime-settings")
        close_windows_when_empty = settings.get("close_windows_when_empty")
        settings.set("close_windows_when_empty", False)
        self.window.run_command("close_workspace")
        self.window.run_command("close_workspace")
        self.check_project(project)
        if self.close_project(project) or len(self.window.views()) == 0:
            sublime.set_timeout_async(lambda: subl([self.project_file_name(project)]), 500)
        else:
            sublime.set_timeout_async(lambda: subl(["-n", self.project_file_name(project)]), 500)
        if close_windows_when_empty:
            sublime.set_timeout_async(lambda: settings.set("close_windows_when_empty", True), 1000)

    def open_in_new_window(self, project):
        self.check_project(project)
        self.close_project(project)
        sublime.set_timeout_async(lambda: subl(["-n", self.project_file_name(project)]), 500)

    def remove_project(self, project):
        ok = sublime.ok_cancel_dialog("Remove project %s from Project Manager?" % project)
        if ok:
            pfile = self.project_file_name(project)
            if self.which_projects_dir(pfile):
                self.close_project(project)
                os.unlink(self.project_file_name(project))
                os.unlink(self.project_workspace(project))
            else:
                for pdir in self.projects_fpath:
                    j = JsonFile(os.path.join(pdir, "library.json"))
                    data = j.load([])
                    if pfile in data:
                        data.remove(pfile)
                        j.save(data)

    def edit_project(self, project):
        def on_open():
            self.window.open_file(self.project_file_name(project))
        sublime.set_timeout_async(on_open, 100)

    def rename_project(self, project):
        def on_rename(new_project):
            if project == new_project:
                return
            pfile = self.project_file_name(project)
            wsfile = self.project_workspace(project)
            pdir = self.which_projects_dir(pfile)
            if not pdir:
                pdir = os.path.dirname(pfile)
            new_pfile = os.path.join(pdir, "%s.sublime-project" % new_project)
            new_wsfile = new_pfile.replace(".sublime-project", ".sublime-workspace")

            reopen = self.close_project(project)
            os.rename(pfile, new_pfile)
            os.rename(wsfile, new_wsfile)

            j = JsonFile(new_wsfile)
            data = j.load({})
            if "project" in data:
                data["project"] = "%s.sublime-project" % os.path.basename(new_project)
            j.save(data)

            if not self.which_projects_dir(pfile):
                for pdir in self.projects_fpath:
                    j = JsonFile(os.path.join(pdir, "library.json"))
                    data = j.load([])
                    if pfile in data:
                        data.remove(pfile)
                        data.append(new_pfile)
                        j.save(data)

            if reopen:
                # reload projects info
                self.__init__(self.window)
                self.open_in_new_window(new_project)

        v = self.window.show_input_panel("New project name:", project, on_rename, None, None)
        v.run_command("select_all")


class ProjectManager(sublime_plugin.WindowCommand):

    def show_quick_panel(self, items, on_done):
        sublime.set_timeout(
            lambda: self.window.show_quick_panel(items, on_done),
            10)

    def run(self, action=None):
        self.manager = Manager(self.window)
        self.projects, display = self.manager.display_projects()
        self.options = [
            ["[-] Project Manager", "More options"],
            ["[-] Add Project", "Add Project to Project Manager"],
            ["[-] Import .sublime-project", "Import .sublime-project file"]
        ]
        if action is not None:
            sublime.set_timeout(lambda: self.on_open(action), 10)
        else:
            self.show_quick_panel(self.options + display, self.on_open)

    def on_open(self, action):
        if action < 0:
            return

        elif action == 0:
            items = [
                ["Open Project in New Window", "Open project in a new window"],
                ["Append Project", "Append project to current window"],
                ["Edit Project", "Edit project settings"],
                ['Rename Project', "Rename project"],
                ["Remove Project", "Remove from Project Manager"]
            ]

            def callback(a):
                if a < 0:
                    sublime.set_timeout(self.run, 10)
                    return
                else:
                    actions = ["new", "append", "edit", "rename", "remove"]
                    self.window.run_command(
                        "project_manager_list",
                        args={"action": actions[a], "caller": "manager"}
                    )

            self.show_quick_panel(items, callback)

        elif action == 1:
            self.manager.add_project()

        elif action == 2:
            self.manager.import_sublime_project()

        elif action >= len(self.options):
            action = action-len(self.options)
            pdata = self.manager.get_project_data(self.projects[action])
            if pdata.get('workspaces'):
                workspace_items = [[w['name'],w['path']] for w in pdata['workspaces']]
                self.show_quick_panel(workspace_items, lambda a: subl([workspace_items[a][1]]))
            else:
                self.manager.switch_project(self.projects[action])


class ProjectManagerAddProject(sublime_plugin.WindowCommand):

    def run(self):
        self.manager = Manager(self.window)
        self.manager.add_project()


class ProjectManagerImportProject(sublime_plugin.WindowCommand):

    def run(self):
        self.manager = Manager(self.window)
        self.manager.import_sublime_project()


class ProjectManagerList(sublime_plugin.WindowCommand):

    def show_quick_panel(self, items, on_done):
        sublime.set_timeout(
            lambda: self.window.show_quick_panel(items, on_done),
            10)

    def run(self, action, caller=None):
        self.caller = caller
        callback = eval("self.on_" + action)
        self.manager = Manager(self.window)
        self.projects, display = self.manager.display_projects()
        self.show_quick_panel(display, callback)

    def on_new(self, action):
        if action >= 0:
            self.manager.open_in_new_window(self.projects[action])
        elif action < 0:
            sublime.set_timeout(self.on_cancel, 10)

    def on_switch(self, action):
        if action >= 0:
            self.manager.switch_project(self.projects[action])
        elif action < 0:
            self.on_cancel()

    def on_append(self, action):
        if action >= 0:
            self.manager.append_project(self.projects[action])
        elif action < 0:
            self.on_cancel()

    def on_remove(self, action):
        if action >= 0:
            sublime.set_timeout(lambda: self.manager.remove_project(self.projects[action]),
                                10)
        elif action < 0:
            self.on_cancel()

    def on_edit(self, action):
        if action >= 0:
            self.manager.edit_project(self.projects[action])
        elif action < 0:
            self.on_cancel()

    def on_rename(self, action):
        if action >= 0:
            sublime.set_timeout(lambda: self.manager.rename_project(self.projects[action]),
                                10)
        elif action < 0:
            self.on_cancel()

    def on_cancel(self):
        if self.caller == "manager":
            self.window.run_command("project_manager", args={"action": 0})
