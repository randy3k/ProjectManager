import sublime
import sublime_plugin
import subprocess
import os
import platform
import re
import operator

from .json_file import JsonFile


def subl(*args):
    executable_path = sublime.executable_path()
    if sublime.platform() == 'osx':
        app_path = executable_path[:executable_path.rfind('.app/') + 5]
        executable_path = app_path + 'Contents/SharedSupport/bin/subl'

    subprocess.Popen([executable_path] + list(args))

    def on_activated():
        window = sublime.active_window()
        view = window.active_view()

        if sublime.platform() == 'windows':
            # fix focus on windows
            window.run_command('focus_neighboring_group')
            window.focus_view(view)

        sublime_plugin.on_activated(view.id())
        sublime.set_timeout_async(lambda: sublime_plugin.on_activated_async(view.id()))

    sublime.set_timeout(on_activated, 300)


def expand_path(path, relative_to=None):
    root = None
    if relative_to:
        if os.path.isfile(relative_to):
            root = os.path.dirname(relative_to)
        elif os.path.isdir(relative_to):
            root = relative_to

    if path:
        path = os.path.expanduser(path)
        if path.endswith(os.sep):
            path = path[:-1]
        if root and not os.path.isabs(path):
            path = os.path.normpath(os.path.join(root, path))
    return path


def pretty_path(path):
    user_home = os.path.expanduser('~') + os.sep
    if path and path.startswith(user_home):
        path = os.path.join("~", path[len(user_home):])
    return path


def itemgetter(*index):
    """
    A version of itemgetter returning a list
    """
    def _itemgetter(a):
        _ret = operator.itemgetter(*index)(a)
        if len(index) > 1:
            _ret = list(_ret)
        return _ret
    return _itemgetter


def computer_name():
    if sublime.platform() == 'osx':
        node = subprocess.check_output(['scutil', '--get', 'ComputerName']).decode().strip()
    else:
        node = platform.node().split('.')[0]
    return node


def dont_close_windows_when_empty(func):
    def f(*args, **kwargs):
        s = sublime.load_settings('Preferences.sublime-settings')
        close_windows_when_empty = s.get('close_windows_when_empty')
        s.set('close_windows_when_empty', False)
        func(*args, **kwargs)
        if close_windows_when_empty:
            sublime.set_timeout(
                lambda: s.set('close_windows_when_empty', close_windows_when_empty),
                1000)
    return f


class Manager:
    def __init__(self, window):
        self.window = window
        s = 'project_manager.sublime-settings'
        self.settings = sublime.load_settings(s)

        default_projects_dir = os.path.join(
            sublime.packages_path(), 'User', 'Projects')
        user_projects_dirs = self.settings.get('projects_path')

        self.projects_path = []
        for folder in user_projects_dirs:
            if os.path.isdir(os.path.expanduser(folder)):
                self.projects_path.append(folder)

        if not self.projects_path:
            self.projects_path = [default_projects_dir]

        self.projects_path = [
            os.path.normpath(os.path.expanduser(d)) for d in self.projects_path]

        node = computer_name()
        if self.settings.get('use_local_projects_dir', False):
            self.projects_path = \
                [d + ' - ' + node for d in self.projects_path] + self.projects_path

        self.primary_dir = self.projects_path[0]

        if not os.path.isdir(self.primary_dir):
            os.makedirs(self.primary_dir)

        self.projects_info = self.get_all_projects_info()

    def load_sublime_project_files(self, folder):
        pfiles = []
        for path, dirs, files in os.walk(folder, followlinks=True):
            for f in files:
                f = os.path.join(path, f)
                if f.endswith('.sublime-project') and f not in pfiles:
                    pfiles.append(os.path.normpath(f))
            # remove empty directories
            for d in dirs:
                d = os.path.join(path, d)
                if len(os.listdir(d)) == 0:
                    os.rmdir(d)
        return pfiles

    def load_library(self, folder):
        pfiles = []
        library = os.path.join(folder, 'library.json')
        if os.path.exists(library):
            j = JsonFile(library)
            for f in j.load([]):
                pfile = expand_path(f)
                if os.path.exists(pfile) and pfile not in pfiles:
                    pfiles.append(os.path.normpath(pfile))
            pfiles.sort()
            j.save(pfiles)
        return pfiles

    def get_info_from_project_file(self, pfile):
        pdir = self.which_project_dir(pfile)
        info = {}

        basename = os.path.relpath(pfile, pdir) if pdir else os.path.basename(pfile)
        pname = re.sub(r'\.sublime-project$', '', basename)

        pd = JsonFile(pfile).load()
        if pd and 'folders' in pd and pd['folders']:
            folder = expand_path(pd['folders'][0].get('path', ''), relative_to=pfile)
        else:
            folder = ''
        info["name"] = pname
        info["folder"] = folder
        info["file"] = pfile
        return info

    def mark_open_projects(self, all_info):
        project_file_names = [
            os.path.realpath(w.project_file_name())
            for w in sublime.windows() if w.project_file_name()]

        for v in all_info.values():
            if os.path.realpath(v["file"]) in project_file_names:
                v["star"] = True

    def get_all_projects_info(self):
        all_info = {}
        for pdir in self.projects_path:
            for f in self.load_library(pdir):
                info = self.get_info_from_project_file(f)
                info["type"] = "library"
                all_info[info["name"]] = info

            for f in self.load_sublime_project_files(pdir):
                info = self.get_info_from_project_file(f)
                info["type"] = "sublime-project"
                all_info[info["name"]] = info

        self.mark_open_projects(all_info)
        return all_info

    def which_project_dir(self, pfile):
        for pdir in self.projects_path:
            if (os.path.realpath(os.path.dirname(pfile)) + os.path.sep).startswith(
                    os.path.realpath(pdir) + os.path.sep):
                return pdir
        return None

    def render_display_item(self, item):
        project_name, info = item
        active_project_indicator = str(self.settings.get('active_project_indicator', '*'))
        display_format = str(self.settings.get(
            'project_display_format', '{project_name}{active_project_indicator}'))
        if "star" in info:
            display_name = display_format.format(
                project_name=project_name, active_project_indicator=active_project_indicator)
        else:
            display_name = display_format.format(
                project_name=project_name, active_project_indicator='')
        return [
            project_name,
            display_name.strip(),
            pretty_path(info['folder']),
            pretty_path(info['file'])]

    def display_projects(self):
        plist = list(map(self.render_display_item, self.projects_info.items()))
        plist.sort(key=lambda p: p[0])
        if self.settings.get('show_recent_projects_first', True):
            self.move_recent_projects_to_top(plist)

        if self.settings.get('show_active_projects_first', True):
            self.move_openning_projects_to_top(plist)
        return list(map(itemgetter(0), plist)), list(map(itemgetter(1, 2), plist))

    def move_recent_projects_to_top(self, plist):
        j = JsonFile(os.path.join(self.primary_dir, 'recent.json'))
        recent = j.load([])
        # TODO: it is not needed
        recent = [pretty_path(p) for p in recent]
        return plist.sort(
            key=lambda p: recent.index(p[3]) if p[3] in recent else -1,
            reverse=True)

    def move_openning_projects_to_top(self, plist):
        count = 0
        for i in range(len(plist)):
            if plist[i][0] != plist[i][1]:
                plist.insert(count, plist.pop(i))
                count = count + 1

    def project_file_name(self, project):
        return self.projects_info[project]['file']

    def project_workspace(self, project):
        return re.sub(r'\.sublime-project$',
                      '.sublime-workspace',
                      self.project_file_name(project))

    def update_recent(self, project):
        j = JsonFile(os.path.join(self.primary_dir, 'recent.json'))
        recent = j.load([])
        # TODO: it is not needed
        recent = [pretty_path(p) for p in recent]
        pname = pretty_path(self.project_file_name(project))
        if pname not in recent:
            recent.append(pname)
        else:
            recent.append(recent.pop(recent.index(pname)))
        # only keep the most recent 50 records
        if len(recent) > 50:
            recent = recent[(50 - len(recent)):len(recent)]
        j.save(recent)

    def clear_recent_projects(self):
        def clear_callback():
            answer = sublime.ok_cancel_dialog('Clear Recent Projects?')
            if answer is True:
                j = JsonFile(os.path.join(self.primary_dir, 'recent.json'))
                j.remove()
                self.window.run_command("clear_recent_projects_and_workspaces")

        sublime.set_timeout(clear_callback, 100)

    def get_project_data(self, project):
        return JsonFile(self.project_file_name(project)).load()

    def check_project(self, project):
        wsfile = self.project_workspace(project)
        j = JsonFile(wsfile)
        if not os.path.exists(wsfile):
            j.save({})

    def close_project_by_window(self, window):
        window.run_command('close_workspace')

    def close_project_by_name(self, project):
        pfile = os.path.realpath(self.project_file_name(project))
        for w in sublime.windows():
            if w.project_file_name():
                if os.path.realpath(w.project_file_name()) == pfile:
                    self.close_project_by_window(w)
                    if w.id() != sublime.active_window().id():
                        w.run_command('close_window')
                    return True
        return False

    def add_project(self):
        def add_callback(project):
            pd = self.window.project_data()
            pf = self.window.project_file_name()
            pfile = os.path.join(self.primary_dir, '%s.sublime-project' % project)
            if pd:
                if "folders" in pd:
                    for folder in pd["folders"]:
                        if "path" in folder:
                            folder["name"] = project
                            folder["file_exclude_patterns"] = list()
                            folder["folder_exclude_patterns"] = list()
                            folder["binary_file_patterns"] = list()
                            path = folder["path"]
                            if sublime.platform() == "windows":
                                folder["path"] = expand_path(path, relative_to=pf)
                            else:
                                folder["path"] = pretty_path(
                                    expand_path(path, relative_to=pf))
                JsonFile(pfile).save(pd)
            else:
                JsonFile(pfile).save({})

            # create workspace file
            wsfile = re.sub(r'\.sublime-project$', '.sublime-workspace', pfile)
            if not os.path.exists(wsfile):
                JsonFile(wsfile).save({})

            self.close_project_by_window(self.window)
            # nuke the current window by closing sidebar and all files
            self.window.run_command('close_project')
            self.window.run_command('close_all')

            # reload projects info
            self.__init__(self.window)
            self.switch_project(project)

        def show_input_panel():
            project = 'New Project'
            pd = self.window.project_data()
            pf = self.window.project_file_name()
            try:
                path = pd['folders'][0]['path']
                project = os.path.basename(expand_path(path, relative_to=pf))
            except Exception:
                pass

            v = self.window.show_input_panel('Project name:',
                                             project,
                                             add_callback,
                                             None,
                                             None)
            v.run_command('select_all')

        sublime.set_timeout(show_input_panel, 100)

    def import_sublime_project(self):
        pfile = pretty_path(self.window.project_file_name())
        if not pfile:
            sublime.message_dialog('Project file not found!')
            return
        if self.which_project_dir(pfile):
            sublime.message_dialog('This project was created by Project Manager!')
            return
        answer = sublime.ok_cancel_dialog('Import %s?' % os.path.basename(pfile))
        if answer is True:
            j = JsonFile(os.path.join(self.primary_dir, 'library.json'))
            data = j.load([])
            if pfile not in data:
                data.append(pfile)
                j.save(data)

    def append_project(self, project):
        self.update_recent(project)
        pd = self.get_project_data(project)
        paths = [expand_path(f.get('path'), self.project_file_name(project))
                 for f in pd.get('folders')]
        subl('-a', *paths)

    @dont_close_windows_when_empty
    def switch_project(self, project):
        self.update_recent(project)
        self.check_project(project)
        self.close_project_by_window(self.window)
        self.close_project_by_name(project)
        subl('--project', self.project_workspace(project))

    @dont_close_windows_when_empty
    def open_in_new_window(self, project):
        self.update_recent(project)
        self.check_project(project)
        self.close_project_by_name(project)
        subl('-n', '--project', self.project_workspace(project))

    def _remove_project(self, project):
        answer = sublime.ok_cancel_dialog('Remove "%s" from Project Manager?' % project)
        if answer is True:
            pfile = self.project_file_name(project)
            if self.which_project_dir(pfile):
                self.close_project_by_name(project)
                os.remove(self.project_file_name(project))
                os.remove(self.project_workspace(project))
            else:
                for pdir in self.projects_path:
                    j = JsonFile(os.path.join(pdir, 'library.json'))
                    data = j.load([])
                    if pfile in data:
                        data.remove(pfile)
                        j.save(data)
            sublime.status_message('Project "%s" is removed.' % project)

    def remove_project(self, project):
        sublime.set_timeout(lambda: self._remove_project(project), 100)

    def clean_dead_projects(self):
        projects_to_remove = []
        for pname, pi in self.projects_info.items():
            folder = pi['folder']
            if not os.path.exists(folder):
                projects_to_remove.append(pname)

        def remove_projects_iteratively():
            pname = projects_to_remove[0]
            self._remove_project(pname)
            projects_to_remove.remove(pname)
            if len(projects_to_remove) > 0:
                sublime.set_timeout(remove_projects_iteratively, 100)

        if len(projects_to_remove) > 0:
            sublime.set_timeout(remove_projects_iteratively, 100)
        else:
            sublime.message_dialog('No Dead Projects.')

    def edit_project(self, project):
        def on_open():
            self.window.open_file(self.project_file_name(project))
        sublime.set_timeout_async(on_open, 100)

    def rename_project(self, project):
        def rename_callback(new_project):
            if project == new_project:
                return
            pfile = self.project_file_name(project)
            wsfile = self.project_workspace(project)
            pdir = self.which_project_dir(pfile)
            if not pdir:
                pdir = os.path.dirname(pfile)
            new_pfile = os.path.join(pdir, '%s.sublime-project' % new_project)
            new_wsfile = re.sub(r'\.sublime-project$', '.sublime-workspace', new_pfile)

            reopen = self.close_project_by_name(project)
            os.rename(pfile, new_pfile)
            os.rename(wsfile, new_wsfile)

            j = JsonFile(new_wsfile)
            data = j.load({})
            if 'project' in data:
                data['project'] = '%s.sublime-project' % os.path.basename(new_project)
            j.save(data)

            if not self.which_project_dir(pfile):
                for pdir in self.projects_path:
                    library = os.path.join(pdir, 'library.json')
                    if os.path.exists(library):
                        j = JsonFile(library)
                        data = j.load([])
                        if pfile in data:
                            data.remove(pfile)
                            data.append(new_pfile)
                            j.save(data)

            if reopen:
                # reload projects info
                self.__init__(self.window)
                self.open_in_new_window(new_project)

        def show_input_panel():
            v = self.window.show_input_panel('New project name:',
                                             project,
                                             rename_callback,
                                             None,
                                             None)
            v.run_command('select_all')

        sublime.set_timeout(show_input_panel, 100)


def cancellable(func):
    def _ret(self, action):
        if action >= 0:
            func(self, action)
        elif action < 0 and self.caller == 'manager':
            sublime.set_timeout(self.run, 10)
    return _ret


class ProjectManagerCloseProject(sublime_plugin.WindowCommand):
    def run(self):
        if self.window.project_file_name():
            # if it is a project, close the project
            self.window.run_command('close_workspace')
        else:
            self.window.run_command('close_all')
            # exit if there are dirty views
            for v in self.window.views():
                if v.is_dirty():
                    return
            # close the sidebar
            self.window.run_command('close_project')


class ProjectManagerEventHandler(sublime_plugin.EventListener):

    def on_window_command(self, window, command_name, args):
        if sublime.platform() == "osx":
            return
        settings = sublime.load_settings('project_manager.sublime-settings')
        if settings.get("close_project_when_close_window", True) and \
                command_name == "close_window":
            window.run_command("project_manager_close_project")


class ProjectManager(sublime_plugin.WindowCommand):

    def show_quick_panel(self, items, on_done):
        sublime.set_timeout(
            lambda: self.window.show_quick_panel(items, on_done),
            10)

    def run(self, action=None, caller=None):
        self.manager = Manager(self.window)

        if action is None:
            self.show_options()
        elif action == 'add_project':
            self.manager.add_project()
        elif action == 'import_sublime_project':
            self.manager.import_sublime_project()
        elif action == 'clear_recent_projects':
            self.manager.clear_recent_projects()
        elif action == 'remove_dead_projects':
            self.manager.clean_dead_projects()
        else:
            self.caller = caller
            callback = eval('self.on_' + action)
            self.projects, display = self.manager.display_projects()
            if not self.projects:
                sublime.message_dialog('Project list is empty.')
                return
            self.show_quick_panel(display, callback)

    def show_options(self):
        items = [
            ['Open Project', 'Open project in the current window'],
            ['Open Project in New Window', 'Open project in a new window'],
            ['Append Project', 'Append project to current window'],
            ['Edit Project', 'Edit project settings'],
            ['Rename Project', 'Rename project'],
            ['Remove Project', 'Remove from Project Manager'],
            ['Add New Project', 'Add current folders to Project Manager'],
            ['Import Project', 'Import current .sublime-project file'],
            ['Clear Recent Projects', 'Clear Recent Projects'],
            ['Remove Dead Projects', 'Remove Dead Projects']
        ]

        def callback(a):
            if a < 0:
                return
            elif a <= 5:
                actions = ['switch', 'new', 'append', 'edit', 'rename', 'remove']
                self.run(action=actions[a], caller='manager')
            elif a == 6:
                self.run(action='add_project')
            elif a == 7:
                self.run(action='import_sublime_project')
            elif a == 8:
                self.run(action='clear_recent_projects')
            elif a == 9:
                self.run(action='remove_dead_projects')

        self.show_quick_panel(items, callback)

    @cancellable
    def on_new(self, action):
        self.manager.open_in_new_window(self.projects[action])

    @cancellable
    def on_switch(self, action):
        self.manager.switch_project(self.projects[action])

    @cancellable
    def on_append(self, action):
        self.manager.append_project(self.projects[action])

    @cancellable
    def on_remove(self, action):
        self.manager.remove_project(self.projects[action])

    @cancellable
    def on_edit(self, action):
        self.manager.edit_project(self.projects[action])

    @cancellable
    def on_rename(self, action):
        self.manager.rename_project(self.projects[action])
