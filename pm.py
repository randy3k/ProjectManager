import sublime, sublime_plugin
import subprocess, os
import codecs, re
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
            try:
                data = sublime.decode_value(content)
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
        f.write(sublime.encode_value(data, True))
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

def pabs(root, folder):
    if not os.path.isabs(folder):
        folder = os.path.abspath(os.path.join(root, folder))
    return folder

class Manager:
    def __init__(self, window):
        self.window = window
        settings_file = 'pm.sublime-settings'
        self.settings = sublime.load_settings(settings_file)
        default_projects_dir = os.path.join(sublime.packages_path(), "User", "Projects")
        self.projects_dir = self.settings.get("projects_dir", default_projects_dir)
        self.library_json = os.path.join(self.projects_dir, "library.json")
        self.projects_info = self.get_projects_info()

    def get_library(self):
        paths = []
        j = Jfile(self.library_json)
        for f in j.load([]):
            if os.path.exists(f) and f not in paths:
                paths.append(f)
        for f in os.listdir(self.projects_dir):
            f = os.path.join(self.projects_dir, f)
            if f.endswith(".sublime-project") and f not in paths:
                paths.append(f)
        j.save(paths)
        return paths

    def get_projects_info(self):
        ret = {}
        library = self.get_library()
        for f in library:
            pname = os.path.basename(f).replace(".sublime-project","")
            root = os.path.dirname(f)
            pd = Jfile(f).load()
            if pd and "folders" in pd and pd["folders"]:
                folder = pd["folders"][0].get("path", "")
            else:
                folder = ""
            opened = False
            for w in sublime.windows():
                if w.project_file_name() == f:
                    opened = True
                    break
            ret[pname] = {
                            "folder": pabs(root, folder),
                            "file": f,
                            "opened": opened
                        }
        return ret

    def display_projects(self):
        ret = [[key, key+"*" if value["opened"] else key, value["folder"]] for key, value in self.projects_info.items()]
        ret = sorted(ret)
        count = 0
        for i in range(len(ret)):
            if ret[i][0] is not ret[i][1]:
                ret.insert(count, ret.pop(i))
                count = count + 1
        return [[item[0] for item in ret], [[item[1], item[2]] for item in ret]]

    def sublime_project(self, project):
        return self.projects_info[project]["file"]

    def sublime_workspace(self, project):
        return self.sublime_project(project).replace(".sublime-project", ".sublime-workspace")

    def add_folder(self):
        pd = self.window.project_data()
        if not pd:
            self.window.run_command("prompt_add_folder")
            delay = 300
        else:
            delay = 1

        def on_add(project):
            pd = self.window.project_data()
            f = os.path.join(self.projects_dir, "%s.sublime-project" % project)
            Jfile(f).save(pd)
            Jfile(f.replace(".sublime-project", ".sublime-workspace")).save({})
            self.window.run_command("close_workspace")
            self.window.run_command("close_project")
            for v in self.window.views():
                if not v.is_dirty():
                    self.window.focus_view(v)
                    self.window.run_command("close")

            # reload projects info
            self.projects_info = self.get_projects_info()
            self.switch_project(project)

        def show_input_panel():
            pd = self.window.project_data()
            if pd:
                project = os.path.basename(pd["folders"][0]["path"])
                v = self.window.show_input_panel("Project name:", project, on_add, None, None)
                v.run_command("select_all")

        sublime.set_timeout(show_input_panel, delay)

    def import_sublime_project(self):
        project = self.window.project_file_name()
        if not project:
            sublime.message_dialog("Project file *.sublime-project not found!")
            return
        ok = sublime.ok_cancel_dialog("Import %s?" % os.path.basename(project))
        if ok:
            j = Jfile(self.library_json)
            data = j.load([])
            if project not in data:
                data.append(project)
                j.save(data)

    def get_project_data(self, project):
        return Jfile(self.sublime_project(project)).load()

    def check_project(self, project):
        if not os.path.exists(self.sublime_workspace(project)):
            Jfile(self.sublime_workspace(project)).save({})
        pass

    def close_project(self, project):
        for w in sublime.windows():
            if w.project_file_name() == self.sublime_project(project):
                w.run_command("close_workspace")
                w.run_command("close_window")
                return True
        return False

    def append_project(self, project):
        pd = self.get_project_data(project)
        root = os.path.dirname(self.sublime_project(project))
        paths = [pabs(root, f.get("path")) for f in pd.get("folders")]
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
        ok = sublime.ok_cancel_dialog("Remove Project %s from Project Manager?" % project)
        if ok:
            pfile = self.sublime_project(project)
            root = os.path.dirname(pfile)
            if re.match(self.projects_dir, root):
                self.close_project(project)
                os.unlink(self.sublime_project(project))
                os.unlink(self.sublime_workspace(project))
            else:
                j = Jfile(self.library_json)
                data = j.load([])
                if pfile in data:
                    data.remove(pfile)
                j.save(data)

    def edit_project(self, project):
        self.window.open_file(self.sublime_project(project))

    def rename_project(self, project):
        def on_rename(new_project):
            sublime_project = self.sublime_project(project)
            new_sublime_project = os.path.join(os.path.dirname(sublime_project),
                                    "%s.sublime-project" % new_project)
            sublime_workspace = self.sublime_workspace(project)
            new_sublime_workspace = new_sublime_project.replace(".sublime-project", ".sublime-workspace")
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
            j = Jfile(self.library_json)
            data = j.load([])
            if sublime_project in data: data.remove(sublime_project)
            data.append(new_sublime_project)
            j.save(data)

            if reopen:
                # reload projects info
                self.projects_info = self.get_projects_info()
                self.open_in_new_window(new_project)
        self.window.show_input_panel("New project name:", project, on_rename, None, None)


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
                ["[-] Add Folder", "Add folder to Project Manager"],
                ["[-] Import .sublime-project", "Import .sublime_project file"]
            ]
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
                if a<0:
                    sublime.set_timeout(self.run, 10)
                    return
                else:
                    actions = ["new", "append", "edit", "rename", "remove"]
                    self.window.run_command("project_manager_list",
                            args={"action": actions[a], "caller" : "manager"})

            self.show_quick_panel(items, callback)

        elif action==1:
            self.manager.add_folder()

        elif action==2:
            self.manager.import_sublime_project()

        elif action>=len(self.options):
            action = action-len(self.options)
            self.manager.switch_project(self.projects[action])

class ProjectManagerAdd(sublime_plugin.WindowCommand):
    def run(self):
        self.manager = Manager(self.window)
        self.manager.add_folder()

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
        if action>=0:
            self.manager.open_in_new_window(self.projects[action])
        elif action<0:
            sublime.set_timeout(self.on_cancel, 10)

    def on_switch(self, action):
        if action>=0:
            self.manager.switch_project(self.projects[action])
        elif action<0:
            self.on_cancel()

    def on_append(self, action):
        if action>=0:
            self.manager.append_project(self.projects[action])
        elif action<0:
            self.on_cancel()

    def on_remove(self, action):
        if action>=0:
            sublime.set_timeout(lambda:
                self.manager.remove_project(self.projects[action]),
                10)
        elif action<0:
            self.on_cancel()

    def on_edit(self, action):
        if action>=0:
            self.manager.edit_project(self.projects[action])
        elif action<0:
            self.on_cancel()

    def on_rename(self, action):
        if action>=0:
            sublime.set_timeout(lambda:
                self.manager.rename_project(self.projects[action]),
                10)
        elif action<0:
            self.on_cancel()

    def on_cancel(self):
        if self.caller == "manager":
            self.window.run_command("project_manager", args={"action": 0})
