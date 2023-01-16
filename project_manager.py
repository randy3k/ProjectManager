import sublime
import sublime_plugin
import subprocess
import os
import platform
import re
import copy

from .json_file import JsonFile

SETTINGS_FILENAME = 'project_manager.sublime-settings'
REPODIRS = ('.git', '.svn', '.hg')
pm_settings = None


def preferences_migrator():
    projects_path = pm_settings.get("projects_path", [])

    if pm_settings.get("use_local_projects_dir", False):
        if projects_path:
            pm_settings.set(
                "projects",
                [p + " - $hostname" for p in projects_path] + projects_path +
                ["$default - $hostname", "$default"])
        else:
            pm_settings.set("projects", "$default - $hostname")
    elif projects_path:
        if len(projects_path) > 1:
            pm_settings.set("projects", projects_path)
        else:
            pm_settings.set("projects", projects_path[0])

    pm_settings.erase("projects_path")
    pm_settings.erase("use_local_projects_dir")
    sublime.save_settings(SETTINGS_FILENAME)


def plugin_loaded():
    global pm_settings
    pm_settings = sublime.load_settings(SETTINGS_FILENAME)
    if pm_settings.has("projects_path") and pm_settings.get("projects") == "$default":
        preferences_migrator()
    projects_info = ProjectsInfo.get_instance()
    pm_settings.add_on_change("refresh_projects", projects_info.refresh_projects)


def plugin_unloaded():
    pm_settings.clear_on_change("refresh_projects")


def subl(*args):
    print(args)
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


def format_directory(item, folder):
    if hasattr(sublime, "QuickPanelItem"):
        return sublime.QuickPanelItem(
            item,
            '<a href="%s">%s</a>' % (
                sublime.command_url('open_dir', {'dir': folder}),
                pretty_path(folder)))
    else:
        return [item, pretty_path(folder)]


def safe_remove(path):
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass


_computer_name = []


def computer_name():
    if _computer_name:
        node = _computer_name[0]
    else:
        if sublime.platform() == 'osx':
            node = subprocess.check_output(['scutil', '--get', 'ComputerName']).decode().strip()
        else:
            node = platform.node().split('.')[0]
        _computer_name.append(node)

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


def find_repos(basedir, max_level=1, ignores=None):
    """ os.walk with max depth. https://stackoverflow.com/a/234329 """
    ignores = [i.lower() for i in (ignores or [])]
    basedir = basedir.rstrip(os.path.sep)
    assert os.path.isdir(basedir)
    num_sep = basedir.count(os.path.sep)
    for root, dirs, files in os.walk(basedir):
        for dirname in dirs:
            if not _is_ignored(root, ignores) and dirname in REPODIRS:
                yield root, dirname
        # yield root, dirs, files
        num_sep_this = root.count(os.path.sep)
        if num_sep + max_level <= num_sep_this:
            del dirs[:]


def _is_ignored(dirname, ignores):
    parts = dirname.split(os.path.sep)
    for ignore in ignores:
        for part in parts:
            if ignore == part.lower():
                return True
    return False


class ProjectsInfo:
    _instance = None

    def __init__(self):
        self.refresh_projects()

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def projects_path(self):
        return self._projects_path

    def primary_dir(self):
        return self._primary_dir

    def default_dir(self):
        return self._default_dir

    def info(self):
        return self._info

    def which_project_dir(self, pfile):
        pfile = expand_path(pfile)
        for pdir in self._projects_path:
            if (os.path.realpath(os.path.dirname(pfile)) + os.path.sep).startswith(
                    os.path.realpath(pdir) + os.path.sep):
                return pdir
        return None

    def refresh_projects(self):
        self._default_dir = os.path.join(
            sublime.packages_path(), 'User', 'Projects')

        self._projects_path = []

        user_projects_dirs = pm_settings.get('projects')
        node = computer_name()

        if isinstance(user_projects_dirs, dict):
            if node in user_projects_dirs:
                user_projects_dirs = user_projects_dirs[node]
            else:
                user_projects_dirs = []

        if isinstance(user_projects_dirs, str):
            user_projects_dirs = [user_projects_dirs]

        for folder in user_projects_dirs:
            p = expand_path(folder)
            p = p.replace("$default", self._default_dir)
            p = p.replace("$hostname", node)
            self._projects_path.append(p)

        if self._default_dir not in self._projects_path:
            self._projects_path.append(self._default_dir)

        self._projects_path = [expand_path(d) for d in self._projects_path]

        self._primary_dir = self._projects_path[0]

        if not os.path.isdir(self._default_dir):
            os.makedirs(self._default_dir)

        if not os.path.isdir(self._primary_dir):
            raise Exception("Directory \"{}\" does not exists.".format(self._primary_dir))

        self._info = self._get_all_projects_info()
        self._auto_discover_repos()

    def _get_all_projects_info(self):
        all_projects_info = {}
        for pdir in self._projects_path:
            for f in self._load_library(pdir):
                info = self._get_info_from_project_file(f)
                info["type"] = "library"
                all_projects_info[info["name"]] = info

            for f in self._load_sublime_project_files(pdir):
                info = self._get_info_from_project_file(f)
                info["type"] = "sublime-project"
                all_projects_info[info["name"]] = info

        return all_projects_info

    def _load_library(self, folder):
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

    def _get_info_from_project_file(self, pfile):
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

    def _load_sublime_project_files(self, folder):
        pfiles = []
        for path, dirs, files in os.walk(folder, followlinks=True):
            for f in files:
                f = os.path.join(path, f)
                if f.endswith('.sublime-project') and f not in pfiles:
                    pfiles.append(os.path.normpath(f))
            # remove empty directories
            for d in dirs:
                d = os.path.join(path, d)
                if os.path.exists(d) and len(os.listdir(d)) == 0:
                    os.rmdir(d)
        return pfiles

    def _auto_discover_repos(self):
        try:
            user_discover_dirs = pm_settings.get('auto_discover_base_directories')

            # Get a list of discover_dirs to search for projects
            node = computer_name()
            if isinstance(user_discover_dirs, dict):
                if node in user_discover_dirs:
                    user_discover_dirs = user_discover_dirs[node]
                else:
                    user_discover_dirs = []
            if isinstance(user_discover_dirs, str):
                user_discover_dirs = [user_discover_dirs]

            discover_dirs = []
            for folder in user_discover_dirs:
                p = expand_path(folder)
                p = p.replace("$hostname", node)
                discover_dirs.append(p)

            # Convert existing project info to dict for easy lookup
            existing = {info['folder']:key for key,info in self._info.items()}

            # Find new repo directories
            max_depth = pm_settings.get('auto_discover_max_recursion_depth', 1)
            ignores = pm_settings.get('auto_discover_ignored_folders', [])
            for basedir in discover_dirs:
                if not os.path.isdir(basedir):
                    print('ProjectManager: {} is not a valid path'.format(basedir))
                for folder, repodir in find_repos(basedir, max_depth, ignores):
                    if folder not in existing:
                        project_name = os.path.basename(folder)
                        self._create_new_project(project_name, folder)
        except Exception as err:
            print(err)

    def _create_new_project(self, project_name, folder):
        data = {"folders": [{
            "binary_file_patterns": [],
            "file_exclude_patterns": [],
            "folder_exclude_patterns": [],
            "name": project_name,
            "path": folder,
        }]}
        
        filename = '{}.sublime-project'.format(project_name)
        filepath = os.path.join(self.primary_dir(), filename)
        print('ProjectManager: Creating {} -> {}'.format(filename, folder))
        JsonFile(filepath).save(data)


class Manager:
    def __init__(self, window):
        self.window = window
        self.projects_info = ProjectsInfo.get_instance()

    def display_projects(self):
        info = copy.deepcopy(self.projects_info.info())
        self.mark_open_projects(info)
        plist = list(map(self.render_display_item, info.items()))
        plist.sort(key=lambda p: p[0])
        if pm_settings.get('show_recent_projects_first', True):
            self.move_recent_projects_to_top(plist)

        if pm_settings.get('show_active_projects_first', True):
            self.move_openning_projects_to_top(plist)

        return [p[0] for p in plist], [format_directory(p[1], p[2]) for p in plist]

    def mark_open_projects(self, info):
        project_file_names = [
            os.path.realpath(w.project_file_name())
            for w in sublime.windows() if w.project_file_name()]

        for v in info.values():
            if os.path.realpath(v["file"]) in project_file_names:
                v["star"] = True

    def render_display_item(self, item):
        project_name, info = item
        active_project_indicator = str(pm_settings.get('active_project_indicator', '*'))
        display_format = str(pm_settings.get(
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
            info['folder'],
            pretty_path(info['file'])]

    def move_recent_projects_to_top(self, plist):
        j = JsonFile(os.path.join(self.projects_info.primary_dir(), 'recent.json'))
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
        return self.projects_info.info()[project]['file']

    def project_workspace(self, project):
        return re.sub(r'\.sublime-project$',
                      '.sublime-workspace',
                      self.project_file_name(project))

    def update_recent(self, project):
        j = JsonFile(os.path.join(self.projects_info.primary_dir(), 'recent.json'))
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
                j = JsonFile(os.path.join(self.projects_info.primary_dir(), 'recent.json'))
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

    def prompt_directory(self, callback, on_cancel=None):
        primary_dir = self.projects_info.primary_dir()
        default_dir = self.projects_info.default_dir()
        remaining_path = self.projects_info.projects_path()
        if primary_dir in remaining_path:
            remaining_path.remove(primary_dir)
        if default_dir in remaining_path:
            remaining_path.remove(default_dir)

        if pm_settings.get("prompt_project_location", True):
            if primary_dir != default_dir:
                items = [
                        format_directory("Primary Directory", primary_dir),
                        format_directory("Default Directory", default_dir)
                    ] + [
                        format_directory(os.path.basename(p), p)
                        for p in remaining_path
                    ]

                def _on_select(index):
                    if index < 0:
                        if on_cancel:
                            on_cancel()
                    elif index == 0:
                        sublime.set_timeout(lambda: callback(primary_dir), 100)
                    elif index == 1:
                        sublime.set_timeout(lambda: callback(default_dir), 100)
                    elif index >= 2:
                        sublime.set_timeout(lambda: callback(remaining_path[index - 2]), 100)

                self.window.show_quick_panel(items, _on_select)
                return

        # fallback
        sublime.set_timeout(lambda: callback(primary_dir), 100)

    def add_project(self, on_cancel=None):
        def add_callback(project, pdir):
            pd = self.window.project_data()
            pf = self.window.project_file_name()
            pfile = os.path.join(pdir, '%s.sublime-project' % project)
            if pd:
                if "folders" in pd:
                    for folder in pd["folders"]:
                        if "path" in folder:
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

            self.projects_info.refresh_projects()
            self.switch_project(project)

        def _ask_project_name(pdir):
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
                                             lambda x: add_callback(x, pdir),
                                             None,
                                             None)
            v.run_command('select_all')

        self.prompt_directory(_ask_project_name, on_cancel=on_cancel)

    def import_sublime_project(self, on_cancel=None):
        def _import_sublime_project(pdir):
            pfile = pretty_path(self.window.project_file_name())
            if not pfile:
                sublime.message_dialog('Project file not found!')
                return
            if self.projects_info.which_project_dir(pfile):
                sublime.message_dialog('This project was created by Project Manager!')
                return
            answer = sublime.ok_cancel_dialog('Import %s?' % os.path.basename(pfile))
            if answer is True:
                j = JsonFile(os.path.join(pdir, 'library.json'))
                data = j.load([])
                if pfile not in data:
                    data.append(pfile)
                    j.save(data)

                self.projects_info.refresh_projects()

        self.prompt_directory(_import_sublime_project, on_cancel=on_cancel)

    def prompt_project(self, callback, on_cancel=None):
        projects, display = self.display_projects()

        def _(i):
            if i >= 0:
                callback(projects[i])
            elif on_cancel:
                on_cancel()

        sublime.set_timeout(lambda: self.window.show_quick_panel(display, _), 100)

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
        subl('--project', self.project_file_name(project))
        self.projects_info.refresh_projects()

    @dont_close_windows_when_empty
    def open_in_new_window(self, project):
        self.update_recent(project)
        self.check_project(project)
        self.close_project_by_name(project)
        subl('-n', '--project', self.project_file_name(project))
        self.projects_info.refresh_projects()

    def _remove_project(self, project):
        answer = sublime.ok_cancel_dialog('Remove "%s" from Project Manager?' % project)
        if answer is True:
            pfile = self.project_file_name(project)
            if self.projects_info.which_project_dir(pfile):
                self.close_project_by_name(project)
                safe_remove(self.project_file_name(project))
                safe_remove(self.project_workspace(project))
            else:
                for pdir in self.projects_info.projects_path():
                    j = JsonFile(os.path.join(pdir, 'library.json'))
                    data = j.load([])
                    if pfile in data:
                        data.remove(pfile)
                        j.save(data)
            sublime.status_message('Project "%s" is removed.' % project)

    def remove_project(self, project):
        def _():
            self._remove_project(project)
            self.projects_info.refresh_projects()

        sublime.set_timeout(_, 100)

    def clean_dead_projects(self):
        projects_to_remove = []
        for pname, pi in self.projects_info.info().items():
            folder = pi['folder']
            if not os.path.exists(folder):
                projects_to_remove.append(pname)

        def remove_projects_iteratively():
            pname = projects_to_remove[0]
            self._remove_project(pname)
            projects_to_remove.remove(pname)
            if len(projects_to_remove) > 0:
                sublime.set_timeout(remove_projects_iteratively, 100)
            else:
                self.projects_info.refresh_projects()

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
            pdir = self.projects_info.which_project_dir(pfile)
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

            if not self.projects_info.which_project_dir(pfile):
                for pdir in self.projects_info.projects_path():
                    library = os.path.join(pdir, 'library.json')
                    if os.path.exists(library):
                        j = JsonFile(library)
                        data = j.load([])
                        if pfile in data:
                            data.remove(pfile)
                            data.append(new_pfile)
                            j.save(data)

            self.projects_info.refresh_projects()

            if reopen:
                self.open_in_new_window(new_project)

        def _ask_project_name():
            v = self.window.show_input_panel('New project name:',
                                             project,
                                             rename_callback,
                                             None,
                                             None)
            v.run_command('select_all')

        sublime.set_timeout(_ask_project_name, 100)


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
        settings = sublime.load_settings(SETTINGS_FILENAME)
        if settings.get("close_project_when_close_window", True) and \
                command_name == "close_window":
            window.run_command("project_manager_close_project")


class ProjectManagerCommand(sublime_plugin.WindowCommand):
    manager = None

    def run(self, action=None, caller=None):
        self.caller = caller
        if action is None:
            self.show_options()
            return

        if not self.manager:
            self.manager = Manager(self.window)

        old_action_mapping = {
            "switch": "open_project",
            "new": "open_project_in_new_window",
            "append": "append_project",
            "edit": "edit_project",
            "rename": "rename_project",
            "remove": "remove_project"
        }
        try:
            action = old_action_mapping[action]
        except KeyError:
            pass

        getattr(self, action)()

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
            ['Refresh Projects', 'Refresh Projects'],
            ['Clear Recent Projects', 'Clear Recent Projects'],
            ['Remove Dead Projects', 'Remove Dead Projects']
        ]

        actions = [
            "open_project",
            "open_in_new_window",
            "append_project",
            "edit_project",
            "rename_project",
            "remove_project",
            "add_project",
            "import_sublime_project",
            "refresh_projects",
            "clear_recent_projects",
            "remove_dead_projects"
        ]

        def callback(i):
            if i < 0:
                return
            self.run(action=actions[i], caller="manager")

        sublime.set_timeout(
            lambda: self.window.show_quick_panel(items, callback),
            100)

    def _prompt_project(self, callback):
        self.manager.prompt_project(callback, on_cancel=self._on_cancel)

    def _on_cancel(self):
        if self.caller == "manager":
            sublime.set_timeout(self.run, 100)

    def open_project(self):
        self._prompt_project(self.manager.switch_project)

    def open_project_in_new_window(self):
        self._prompt_project(self.manager.open_in_new_window)

    def append_project(self):
        self._prompt_project(self.manager.append_project)

    def edit_project(self):
        self._prompt_project(self.manager.edit_project)

    def rename_project(self):
        self._prompt_project(self.manager.rename_project)

    def remove_project(self):
        self._prompt_project(self.manager.remove_project)

    def add_project(self):
        self.manager.add_project(on_cancel=self._on_cancel)

    def import_sublime_project(self):
        self.manager.import_sublime_project(on_cancel=self._on_cancel)

    def refresh_projects(self):
        self.manager.projects_info.refresh_projects()

    def clear_recent_projects(self):
        self.manager.clear_recent_projects()

    def remove_dead_projects(self):
        self.manager.clean_dead_projects()
