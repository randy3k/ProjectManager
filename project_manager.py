import sublime
import sublime_plugin
import subprocess
import os
import shutil
import platform
import re
import copy
from functools import partial

from .json_file import JsonFile

SETTINGS_FILENAME = 'project_manager.sublime-settings'
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

    # Run with timeout so that `window.run_command("close_workspace")` works
    sublime.set_timeout(projects_info.workspace_version_migrator, 0)
    pm_settings.add_on_change("refresh_projects", projects_info.refresh_projects)

    if pm_settings.get("display_in_status_bar", False):
        for window in sublime.windows():
            for view in window.views():
                show_project_status_bar(view)


def plugin_unloaded():
    pm_settings.clear_on_change("refresh_projects")


def subl(*args):
    executable_path = sublime.executable_path()
    if sublime.platform() == 'osx':
        app_path = executable_path[:executable_path.rfind('.app/') + 5]
        executable_path = app_path + 'Contents/SharedSupport/bin/subl'

    subprocess.Popen([executable_path] + list(args))

    def on_activated():
        window = sublime.active_window()
        view = window.active_view()

        # Automatically close window if no folders nor sheets are open BUT there is
        # still project data -> that means the workspace was opened elsewhere
        # (this happens when trying to open a workspace already opened in another window)
        if window.project_data() and not window.folders() and not window.sheets():
            window.run_command('close_window')

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
            '<a href=\'subl:open_dir {"dir": "%s"}\'>%s</a>' % (
                folder, pretty_path(folder)))
    else:
        return [item, pretty_path(folder)]


def format_files(item, paths):
    if hasattr(sublime, "QuickPanelItem"):
        length = 0
        details = ""
        for i, path in enumerate(paths):
            name = path.rsplit(os.sep, 1)[1]
            if length + len(name) > 85:
                name = name[:85-length-len(name)]
            details += '<a href=\'subl:open_file {"file": "%s"}\'>%s</a>' % (path, name)
            length += len(name)

            if length >= 80:
                details += " [...] (" + str(len(paths) - i) + " more)"
                break
            elif i < len(paths)-1:
                details += " / "
                length += 3

        return sublime.QuickPanelItem(item, details)

    else:
        names = [path.rsplit(os.sep, 1)[1] for path in paths]
        details = " / ".join(names)
        if len(details) > 85:
            details = details[:85] + " [...] (" + str(details[80:].count('/')) + " more)"
        return [item, details]


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


def show_project_status_bar(view):
    if not pm_settings.get("display_in_status_bar", False):
        return

    project_file = view.window().project_file_name()
    if not project_file:
        return

    projects_info = ProjectsInfo.get_instance()
    project_name = os.path.splitext(os.path.basename(project_file))[0]
    project_info = projects_info.info()[project_name]
    project_group = project_info.get("group", "")

    display_name = '['
    display_name += project_group
    display_name += project_name

    if sublime.version() >= '4050':
        workspace_file = view.window().workspace_file_name()
        workspace_name = os.path.splitext(os.path.basename(workspace_file))[0]
        if project_name != workspace_name:
            display_name += ':' + workspace_name

    display_name += ']'

    view.set_status("00ProjectManager_project_name", display_name)


# Display the current project name in the status bar
class ProjectInStatusbar(sublime_plugin.EventListener):
    # When opening sublime text
    def on_init(self, views):
        for view in views:
            show_project_status_bar(view)

    # When you create a new empty file
    def on_new(self, view):
        show_project_status_bar(view)

    # When you load an existing file
    def on_load(self, view):
        show_project_status_bar(view)

    # When you use File > New view into file on an existing file
    def on_clone(self, view):
        show_project_status_bar(view)

    # Remove project name when closing view
    def on_close(self, view):
        view.erase_status("00ProjectManager_project_name")


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
            raise Exception("Directory \"{}\" does not exist.".format(self._primary_dir))

        self._info = self._get_all_projects_info()

    def workspace_version_migrator(self):
        # Clear recent projects file if it doesn't support workspaces
        json_file = JsonFile(os.path.join(self._primary_dir, 'recent.json'))
        recent_files = json_file.load([])
        if recent_files and type(recent_files[0]) != dict:
            json_file.remove()
            sublime.run_command("clear_recent_projects_and_workspaces")

        # Update file organization and reload info if needed
        if self._reorganize_files():
            self._info = self._get_all_projects_info()

    def _reorganize_files(self):
        """Reorganize files in project directories (for compatibility)

        This method reorganize the files in every project directories from
        ProjectDirectory
        |  project1.sublime-project
        |  project1.sublime-workspace
        |  project2.sublime-project
        |  project2.sublime-workspace

        to
        ProjectDirectory
        |  project1
        |  |  project1.sublime-project
        |  |  project1.sublime-workspace
        |
        |  project2
        |  |  project2.sublime-project
        |  |  project2.sublime-workspace

        This allow one project to have several workspaces that are all placed in the
        same directory.
        This function is used for compatibility reasons: as the previous version of
        ProjectManager organized files differently, we need to automatically update the
        folder structure to be transparent for the user.

        Returns:
            bool: whether some files were reorganized or not
        """

        active_window = sublime.active_window()
        modified = False
        for pdir in self._projects_path:
            if not os.path.exists(pdir):
                continue

            for file in os.listdir(pdir):

                # If there are sublime-project files in a directory, move it into its
                # folder with all of its workspaces
                if file.endswith('.sublime-project'):
                    modified = True

                    # Create project folder
                    pname = re.sub(r'\.sublime-project$', '', file)
                    directory = os.path.join(pdir, pname)
                    if not os.path.exists(directory):
                        os.mkdir(directory)

                    # If one of the workspace is open, we must close it before moving
                    # the workspace file
                    to_reopen = None
                    pfile = os.path.join(pdir, file)
                    if active_window.project_file_name() == pfile:
                        if sublime.version() >= '4050':
                            wfile = os.path.basename(active_window.workspace_file_name())
                            to_reopen = os.path.join(directory, wfile)
                        else:
                            to_reopen = pfile
                        active_window.run_command("close_workspace")

                    # Move all of its existing workspaces files
                    for wfile in self._info[pname]['workspaces']:
                        try:
                            shutil.move(wfile, directory)
                        except Exception:
                            sublime.message_dialog('Please remove the existing file %s to be able to load projects.' % wfile)
                            raise

                    # Move the sublime-project file itself
                    pfile = os.path.join(pdir, file)
                    try:
                        shutil.move(pfile, directory)
                    except Exception:
                        sublime.message_dialog('Please remove the existing file %s to be able to load projects.' % pfile)

                    if to_reopen:
                        subl("--project", to_reopen)

        return modified

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

    def _get_info_from_project_file(self, pfile):
        pdir = self.which_project_dir(pfile)
        info = {}

        if pdir:
            basename = os.path.basename(os.path.relpath(pfile, pdir))
        else:
            basename = os.path.basename(pfile)
        pname = os.path.basename(re.sub(r'\.sublime-project$', '', basename))

        pd = JsonFile(pfile).load()
        if pd and 'folders' in pd and pd['folders']:
            folder = expand_path(pd['folders'][0].get('path', ''), relative_to=pfile)
        else:
            folder = ''

        if pdir:
            pfolder = os.path.dirname(pfile)
            pfolder = pfolder.rsplit(os.sep, 1)[0] + os.sep
            group = pfolder.replace(pdir + os.sep, '')
        else:
            group = ''

        info["name"] = pname
        info["folder"] = folder
        info["file"] = pfile
        info["workspaces"] = self._get_project_workspaces(pfile)
        info["group"] = group
        return info

    def _get_project_workspaces(self, pfile):
        """Get list of every workspaces of a given project

        Args:
            pfile: str
                The path of the .sublime-project file from which to load workspaces

        Returns:
            list: the list of .sublime-workspace files associated with the given project
        """
        folder = os.path.dirname(pfile)
        pname = os.path.basename(pfile)
        wfiles = []

        # Check every file in the same folder as the project file
        for file in map(lambda file: os.path.join(folder, file), os.listdir(folder)):
            if (file.endswith('.sublime-workspace')
                    and self._is_workspace_affiliated(pname, file)):
                wfiles.append(os.path.normpath(file))

        # If no workspace exists, create a default one
        if not wfiles:
            wfile = re.sub(r'\.sublime-project$', '.sublime-workspace', pfile)
            j = JsonFile(wfile)
            j.save({'project': pname})
            wfiles.append(os.path.normpath(wfile))

        return wfiles

    def _is_workspace_affiliated(self, project, wfile):
        """Check if a workspace corresponds to a workspace of `project`

        Args:
            project: str
                The name of the project file
            wfile: str
                The workspace file to check

        Returns:
            bool: whether the workspace is indeed affiliated with the given project
        """
        j = JsonFile(wfile).load()
        if "project" not in j:
            return False
        return os.path.basename(j["project"]) == project


class Manager:
    """Main class that takes care of everything project and workspace related"""

    def __init__(self, window):
        self.window = window
        self.projects_info = ProjectsInfo.get_instance()

    def refresh_curr_project(self):
        pname = self.window.project_file_name()
        if pname:
            self.curr_pname = os.path.basename(re.sub(r'\.sublime-project$', '', pname))
        else:
            self.curr_pname = None

    def can_switch_workspaces(self):
        """Check if a project is opened in the current window and if it has more than
        one workspace

        Returns:
            bool: whether a project with more than one workspace is currently opened
        """
        if self.curr_pname not in self.projects_info.info():
            return False

        info = copy.deepcopy(self.projects_info.info())
        self.mark_open_projects(info)

        pinfo = info[self.curr_pname]
        return ("star" in pinfo and len(pinfo["workspaces"]) > 1)

    def nb_workspaces(self, project):
        """Returns the number of workspaces a given project has saved

        Args:
            project: str
                The name of the project for which to count workspaces
        """
        if project is None:
            project = self.curr_pname
        if project in self.projects_info.info():
            return len(self.projects_info.info()[project]['workspaces'])
        return 0

    def get_default_workspace(self, project):
        """Get the default workspace of a project

        In order, given a project "Example" the default workspace is:
        - the one with the same name as the project, i.e. Example.sublime-workspace
        - the one opened the most recently
        - the first one which exists, in alphabetical order

        Args:
            project: str
                The name of the project

        Returns:
            str: the path of the default workspace file
        """
        # Load workspaces and sort them alphabetically
        workspaces = self.projects_info.info()[project]['workspaces']
        workspaces.sort(key=lambda wfile: os.path.basename(wfile))

        # If one of the workspace has default name, return it
        for workspace in workspaces:
            wname = os.path.basename(re.sub(r'\.sublime-workspace$', '', workspace))
            if wname == project:
                return workspace

        # Else, try to get the most recent
        recent_file = os.path.join(self.projects_info.primary_dir(), 'recent.json')
        if not os.path.exists(recent_file):
            return workspaces[0]

        j = JsonFile(recent_file)
        recent = j.load([])
        if project not in [pw['project'] for pw in recent]:
            return workspaces[0]
        else:
            return recent[project]["workspaces"][-1]

    def is_workspace_open(self, ws_file):
        if sublime.version() < '4050':
            return False

        open_workspaces = [
            os.path.realpath(w.workspace_file_name())
            for w in sublime.windows() if w.workspace_file_name()]

        return ws_file in open_workspaces

    def display_projects(self):
        info = copy.deepcopy(self.projects_info.info())
        self.mark_open_projects(info)
        plist = list(map(self.render_display_item, info.items()))
        plist.sort(key=lambda p: p[0])
        if pm_settings.get('show_recent_projects_first', True):
            self.move_recent_projects_to_top(plist)

        if pm_settings.get('show_active_projects_first', True):
            self.move_opened_projects_to_top(plist)

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
            'project_display_format', '{project_group}{project_name}{active_project_indicator}'))
        if "star" not in info:
            active_project_indicator = ''

        display_name = display_format.format(project_name=project_name,
                                             project_group=info["group"],
                                             active_project_indicator=active_project_indicator)
        return [
            project_name,
            display_name.strip(),
            info['folder'],
            pretty_path(info['file'])]

    def move_recent_projects_to_top(self, plist):
        j = JsonFile(os.path.join(self.projects_info.primary_dir(), 'recent.json'))
        recent = j.load([])
        recent = [pretty_path(obj["project"]) for obj in recent]
        plist.sort(key=lambda p: recent.index(p[3]) if p[3] in recent else -1,
                   reverse=True)

    def move_opened_projects_to_top(self, plist):
        count = 0
        active_project_indicator = str(pm_settings.get('active_project_indicator', '*'))
        for i in range(len(plist)):
            if plist[i][1].endswith(active_project_indicator):
                plist.insert(count, plist.pop(i))
                count = count + 1

    def project_file_name(self, project):
        return self.projects_info.info()[project]['file']

    def display_workspaces(self, project):
        """Return a list of path to project's workspaces and a list of display elements
        for each of these workspaces.

        Args:
            project: str
                The name of the project from which to list and display workspaces
                If None, the project opened in the current window (if any) is used

        Returns:
            (list[str], list[(str, str)]): returns a pair with:
                - in first element, a list of path to every workspaces belonging to
                    project
                - in second element, a list of pair of strings corresponding to the main
                    display names and the sub-display in the sublime-text selection menu

        Raises:
            ValueError if the given project is not in the list of managed projects.

        Example:
            self.display_workspaces("TestProject") = \
                    (["/home/test/Projects/TestA.sublime-workspace",
                        "/home/text/Projects/TestB.sublime-workspace"],
                     [("TestA", "~/Projects/TestA"),
                        ("TestB", "~/Projects/TestB")]
                    )
        """
        if project is None:
            project = self.curr_pname
        if project not in self.projects_info.info():
            raise ValueError('Project not found !')

        # Load workspaces and their information, then sort them alphabetically
        wfiles = self.projects_info.info()[project]["workspaces"]
        wlist = list(map(self.render_workspace, wfiles))
        wlist.sort(key=lambda w: w[1])

        if pm_settings.get('show_recent_workspaces_first', True):
            move_second = pm_settings.get('show_most_recent_workspace_second', True)
            self.move_recent_workspaces_to_top(project, wlist, move_second)

        if pm_settings.get('show_default_workspace_first', False):
            self.move_default_workspace_to_top(project, wlist)

        # Change name of default workspace (cf. method `get_default_workspace`) to
        # "(Default)" ; and mark open workspaces
        workspaces_file_names = []
        if sublime.version() >= '4050':
            workspaces_file_names = [os.path.realpath(w.workspace_file_name())
                                     for w in sublime.windows() if w.workspace_file_name()]

        active_workspace_indicator = str(pm_settings.get('active_workspace_indicator', '*'))
        for i, (wpath, wname, wbuffers) in enumerate(wlist):
            if wname == project:
                wname = '(Default)'
            if wpath in workspaces_file_names:
                wname += active_workspace_indicator
            wlist[i] = [wpath, wname, wbuffers]

        return [w[0] for w in wlist], [format_files(w[1], w[2]) for w in wlist]

    def render_workspace(self, wfile):
        """Given a workspace file, returns a tuplet with its file, its name,
        a prettified path to its files and the real path to its files

        Args:
            wfile: str
                The complete path to the workspace file

        Returns:
            list[(str, str, str, str)]: a tuplet composed of the path of the file,
                the name of the workspace, a prettified path to the file to display
                to the user and the real path to these files
        """
        wname = os.path.basename(re.sub(r'\.sublime-workspace$', '', wfile))
        winfo = JsonFile(wfile).load()
        if "buffers" not in winfo:
            return [wfile, wname, []]

        wbuffer_info = winfo["buffers"]
        wbuffers = [buffer['file'] for buffer in wbuffer_info if 'file' in buffer]

        return [wfile, wname, wbuffers]

    def move_recent_workspaces_to_top(self, project, wlist, move_second):
        """Sort a list of workspaces according to their date and time of last opening

        This method sort workspaces according to their index in the `recent.json` file,
        placing the most recent ones on top of the list.
        If `move_second` is True, check if this most recent workspace belongs to
        the project opened in the current window. If it's the case, then switch the
        first and second items in the list. This is to make sure that when switching
        workspaces after having opened one, the one opened (and so the most recent one)
        is not in first position.

        Args:
            project: str
                The name of the project from which to sort the workspaces
            wlist: list[(str, str, list[str]]
                A list of information of all of the project's workspaces as given by
                self.render_workspace (i.e. [(wpath, wname, wbuffers)])
            move_second: bool
                Whether to move the most recently opened workspace in second position
        """
        j = JsonFile(os.path.join(self.projects_info.primary_dir(), 'recent.json'))
        recent = j.load([])

        # We look for the project in the `recent.json` file and extract the list of its
        # workspaces (sorted by most recently opened)
        for obj in recent:
            pname = os.path.basename(re.sub(r'\.sublime-project$', '', obj["project"]))
            if pname == project:
                recent = obj["workspaces"]
                break
        else:
            return

        # Sort workspaces according to their index in the recent list
        wlist.sort(key=lambda w: recent.index(w[0]) if w[0] in recent else -1,
                   reverse=True)

        # Switch first and second if the current window is in a project...
        if move_second and self.curr_pname is not None:
            # ...and this project is the one from which we want to load a workspace
            if self.curr_pname != project:
                return

            if wlist[0][0] in recent:
                wlist[0], wlist[1] = wlist[1], wlist[0]

    def move_default_workspace_to_top(self, project, wlist):
        """Move the default workspace of a project to the top of the list of workspaces

        The default workspace of a project is defined as the workspace that has the same
        name of file. For example, the project `test.sublime-project` has for default
        workspace `test.sublime-workspace`.
        The default workspace corresponds to the one created by sublime-text by default.

        Args:
            project: str
                The name of the project
            wlist: list[(str, str, list[str])]
                A list of information of all of the project's workspaces as given by
                self.render_workspace (i.e. [(wpath, wname, wbuffers])
        """
        for i in range(len(wlist)):
            if wlist[i][1] == project:
                wlist.insert(0, wlist.pop(i))
                break

    def update_recent(self, project, wfile=None):
        """Update the `recent.json` file to put the given project and workspace in most
        recent spot

        Args:
            project: str
                The name of the project
            wfile: str
                The path of the workspace file
        """
        j = JsonFile(os.path.join(self.projects_info.primary_dir(), 'recent.json'))
        recent = j.load([])
        pfile = pretty_path(self.project_file_name(project))

        # If no workspace is given, take the default one
        if wfile is None:
            wfile = re.sub(r'\.sublime-project$', '.sublime-workspace', pfile)

        # Run through the recent file to find the given project and move the given
        # workspace to the end of the wlist
        for i, pobject in enumerate(recent):
            if pfile == pobject["project"]:
                wlist = pobject["workspaces"]
                if wfile in wlist:
                    wlist.remove(wfile)
                wlist.append(wfile)
                recent.pop(i)
                break
        else:
            wlist = [wfile]

        # Move the project to the end of the recent list
        recent.append({"project": pfile, "workspaces": wlist})

        # Only keep the most recent 50 records
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

    def close_project_by_window(self, window):
        window.run_command('close_workspace')

    def close_project_by_name(self, project):
        pfile = os.path.realpath(self.project_file_name(project))
        closed_workspaces = set()
        for w in sublime.windows():
            if w.project_file_name():
                if os.path.realpath(w.project_file_name()) == pfile:
                    closed_workspaces.add(w.workspace_file_name())
                    self.close_project_by_window(w)
                    if w.id() != sublime.active_window().id():
                        w.run_command('close_window')

        return closed_workspaces

    def close_window(self, window):
        window.run_command('close')

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

    def create_project(self, on_cancel=None):
        def add_callback(project, pdir):
            existing_projects = self.projects_info.info().keys()
            if project in existing_projects:
                sublime.message_dialog("Another project is already named "+ project)
                return
            pd = self.window.project_data()
            pf = self.window.project_file_name()
            if os.sep in project:
                groups, project = project.rsplit(os.sep, 1)
            else:
                groups = ''
            pfile = os.path.join(pdir, groups, project,
                                 '%s.sublime-project' % project)
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
            wfile = re.sub(r'\.sublime-project$', '.sublime-workspace', pfile)
            if not os.path.exists(wfile):
                JsonFile(wfile).save({"project": os.path.basename(pfile)})

            # reload projects info
            self.projects_info.refresh_projects()
            self.open_in_new_window(project, wfile)

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

    def add_workspace(self):
        if not self.curr_pname:
            sublime.message_dialog("No active project")
            return

        def add_callback(new_workspace):
            project = self.curr_pname

            if not new_workspace:
                new_workspace = project
            elif '/' in new_workspace:
                sublime.message_dialog("Invalid name: can't contain a '\\'")
                return

            wfile = self.get_default_workspace(project)
            new_wfile = os.path.join(os.path.dirname(wfile),
                                     new_workspace + '.sublime-workspace')

            if wfile == new_wfile or os.path.exists(new_wfile):
                sublime.message_dialog("Another workspace is already named " + new_workspace)
                return

            # Trick: instead of using obscure undocumented sublime commands to create a
            # new workspace file, copy an existing sublime-workspace file and reset
            # its data to get a new one
            try:
                shutil.copy(wfile, new_wfile)
            except OSError as err:
                sublime.message_dialog(str(err))
                return
            j = JsonFile(new_wfile)
            j.save({'project': project + ".sublime-project"})

            # Reload projects info
            self.projects_info.refresh_projects()
            self.open_in_new_window(None, new_wfile, False)

        def _ask_workspace_name():
            workspace = 'New Workspace'
            v = self.window.show_input_panel('Workspace name:',
                                             workspace,
                                             add_callback,
                                             None,
                                             None)
            v.run_command('select_all')

        sublime.set_timeout(_ask_workspace_name, 100)

    def add_folder(self):
        self.window.run_command("prompt_add_folder")

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

        self.prompt_directory(_import_sublime_project, on_cancel=on_cancel)

    def prompt_project(self, callback, on_cancel=None):
        try:
            projects, display = self.display_projects()
        except ValueError:
            return

        if not projects:
            sublime.message_dialog("No projects are managed currently")
            return

        def _(i):
            if i >= 0:
                callback(projects[i])
            elif on_cancel:
                on_cancel()

        sublime.set_timeout(lambda: self.window.show_quick_panel(display, _), 100)

    def prompt_workspace(self, project, callback, on_cancel=None):
        if self.nb_workspaces(project) < 2:
            callback()
            return

        try:
            workspaces, wdisplay = self.display_workspaces(project)
        except ValueError:
            return

        def _(i):
            if i >= 0:
                callback(workspaces[i])
            elif on_cancel:
                on_cancel()

        sublime.set_timeout(lambda: self.window.show_quick_panel(wdisplay, _), 100)

    def append_project(self, project):
        self.update_recent(project)
        pd = self.get_project_data(project)
        paths = [expand_path(f.get('path'), self.project_file_name(project))
                 for f in pd.get('folders')]
        subl('-a', *paths)

    @dont_close_windows_when_empty
    def switch_project(self, project, workspace=None):
        if project is None:
            project = self.curr_pname
        if workspace is None:
            workspace = self.get_default_workspace(project)
        self.update_recent(project, workspace)
        self.close_project_by_window(self.window)
        if self.is_workspace_open(workspace):
            self.close_window(self.window)
        subl('--project', workspace)
        self.projects_info.refresh_projects()

    @dont_close_windows_when_empty
    def open_in_new_window(self, project, workspace=None, close_project=True):
        if project is None:
            project = self.curr_pname
        if workspace is None:
            workspace = self.get_default_workspace(project)
        self.update_recent(project, workspace)
        if self.is_workspace_open(workspace):
            sublime.status_message("Can't open the same workspace in several windows!")
            subl('--project', workspace)

        else:
            if close_project:
                self.close_project_by_name(project)
            subl('-n', '--project', workspace)

        self.projects_info.refresh_projects()

    def _remove_project(self, project):
        answer = sublime.ok_cancel_dialog('Remove "%s" from Project Manager?' % project)
        if answer is True:
            pfile = self.project_file_name(project)
            if self.projects_info.which_project_dir(pfile):
                self.close_project_by_name(project)
                os.remove(self.project_file_name(project))
                for workspace in self.projects_info.info()[project]['workspaces']:
                    os.remove(workspace)
                if not os.listdir(os.path.dirname(pfile)):
                    os.removedirs(os.path.dirname(pfile))

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

    def _remove_workspace(self, wfile):
        workspace = os.path.basename(re.sub(r'\.sublime-workspace$', '', wfile))
        answer = sublime.ok_cancel_dialog('Remove workspace "%s" from this project?\n'
                                          'Warning: this will close any window opened '
                                          'containing the corresponding project' % workspace)
        if answer is True:
            project = self.curr_pname
            self.close_project_by_name(project)
            os.remove(wfile)
            self.projects_info.refresh_projects()
            sublime.status_message('Workspace "%s" is removed.' % project)
            window = sublime.active_window()
            if window.folders() == [] and window.sheets() == []:
                window.run_command('close_window')

    def remove_workspace(self, wfile):
        sublime.set_timeout(lambda: self._remove_workspace(wfile), 100)

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

    def is_valid_name(self, project_name):
        for char in project_name:
            if not (char.isalnum() or char in '.,_- '):
                return False
        return True

    def rename_project(self, project):
        def rename_callback(new_project):
            if not new_project or project == new_project:
                sublime.status_message("Aborted")
                return

            if not self.is_valid_name(new_project):
                sublime.message_dialog("Invalid name: the only character authorized are [a-zA-Z.,_- ]")
                return

            if new_project in self.projects_info.info():
                sublime.message_dialog("Another project is already called like this")
                return

            pfile = os.path.realpath(self.project_file_name(project))
            pdir = os.path.dirname(pfile)

            close_curr_window = (self.window.project_file_name() == pfile)
            new_pfile = os.path.join(pdir, '%s.sublime-project' % new_project)
            closed_workspaces = self.close_project_by_name(project)
            reopen_workspaces = []
            os.rename(pfile, new_pfile)

            for wfile in self.projects_info.info()[project]['workspaces']:
                if wfile.endswith(os.sep + '%s.sublime-workspace' % project):
                    new_wfile = re.sub(project + r'\.sublime-workspace$',
                                       new_project + '.sublime-workspace',
                                       wfile)
                    if os.path.exists(new_wfile):
                        new_wfile = re.sub(project + r'\.sublime-workspace$',
                                           'Workspace.sublime-workspace',
                                           wfile)
                        i = 1
                        while os.path.exists(new_wfile):
                            new_wfile = re.sub(project + r'\.sublime-workspace$',
                                               'Workspace_' + str(i) + '.sublime-workspace',
                                               wfile)
                            i += 1

                    os.rename(wfile, new_wfile)

                else:
                    new_wfile = wfile

                if wfile in closed_workspaces:
                    beg, mid, end = new_wfile.rpartition('/' + project + '/')
                    reopen_workspaces.append(beg + '/' + new_project + '/' + end)

                j = JsonFile(new_wfile)
                data = j.load({})
                data['project'] = '%s.sublime-project' % os.path.basename(new_project)
                j.save(data)

            if self.projects_info.which_project_dir(pfile) is not None:
                try:
                    path = os.path.dirname(pfile)
                    new_path = os.path.join(os.path.dirname(path), new_project)
                    os.rename(path, new_path)
                except OSError:
                    pass
            else:
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

            for wfile in reopen_workspaces:
                self.open_in_new_window(new_project, wfile, False)

            if close_curr_window:
                self.window.run_command('close_window')

        def _ask_project_name():
            v = self.window.show_input_panel('New project name:',
                                             project,
                                             rename_callback,
                                             None,
                                             None)
            v.run_command('select_all')

        sublime.set_timeout(_ask_project_name, 100)

    def rename_workspace(self, wfile=None):
        if wfile is None:
            wfile = self.get_default_workspace(self.curr_pname)

        def rename_callback(new_workspace):
            project = self.curr_pname
            if not new_workspace:
                new_workspace = project

            if not self.is_valid_name(new_workspace):
                sublime.message_dialog("Invalid name: the only character authorized are [a-zA-Z.,_- ]")
                return

            new_wfile = os.path.join(os.path.dirname(wfile),
                                     new_workspace + '.sublime-workspace')

            if wfile == new_wfile or os.path.exists(new_wfile):
                sublime.message_dialog("Another workspace is already named " + new_workspace)
                return

            if sublime.version() > '4050':
                focused_wfile = self.window.workspace_file_name()
                project_ws = self.projects_info.info()[project]["workspaces"]
                if focused_wfile != wfile and focused_wfile in project_ws:
                    wfile_to_reopen = focused_wfile
                else:
                    wfile_to_reopen = new_wfile
            else:
                wfile_to_reopen = new_wfile

            self.close_project_by_name(project)
            os.rename(wfile, new_wfile)
            self.projects_info.refresh_projects()
            subl('--project', wfile_to_reopen)

        workspace = os.path.basename(re.sub(r'\.sublime-workspace$', '', wfile))

        def show_input_panel():
            v = self.window.show_input_panel('New workspace name:',
                                             workspace,
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
        settings = sublime.load_settings(SETTINGS_FILENAME)
        if settings.get("close_project_when_close_window", True) and \
                command_name == "close_window":
            window.run_command("project_manager_close_project")


class ProjectManagerCommand(sublime_plugin.WindowCommand):
    manager = None

    def run(self, action=None, caller=None, project=None, workspace=None):
        self.caller = caller

        if not self.manager:
            self.manager = Manager(self.window)
        self.manager.refresh_curr_project()

        if project is not None:
            pinfos = self.manager.projects_info.info()
            if project not in pinfos:
                sublime.status_message("Project '{}' does not exist".format(project))
                return

            if workspace is None:
                self.manager.open_in_new_window(project)
                return

            wfiles = pinfos[project]["workspaces"]
            wnames = [os.path.basename(re.sub(r'\.sublime-workspace$', '', wfile))
                      for wfile in wfiles]
            if workspace in wnames:
                self.manager.open_in_new_window(project, wfiles[wnames.index(workspace)])
            else:
                sublime.status_message("Workspace '{}' does not exist in project '{}'"
                                       .format(workspace, project))
            return

        if action is None:
            self.show_options()
            return

        getattr(self, action)()

    def show_options(self):
        items = [
            ['Open Project', 'Open project in the current window'],
            ['Open Project in New Window', 'Open project in a new window'],
            ['Open Workspace', 'Open new workspace in the current window'],
            ['Open Workspace in New Window', 'Open new workspace in a new window'],
            ['Append Project', 'Append project to current window'],
            ['Edit Project', 'Edit project settings'],
            ['Rename Project', 'Rename project'],
            ['Remove Project', 'Remove from Project Manager'],
            ['Rename Workspace', 'Rename Workspace'],
            ['Remove Workspace', 'Remove workspace from Project Manager'],
            ['Create New Project', 'Create a new project and add current folders to it'],
            ['Add New Workspace', 'Add a new workspace to the current project'],
            ['Add Folder to Project', 'Add a folder to the current project'],
            ['Import Project', 'Import current .sublime-project file'],
            ['Refresh Projects', 'Refresh Projects'],
            ['Clear Recent Projects', 'Clear Recent Projects'],
            ['Remove Dead Projects', 'Remove Dead Projects']
        ]

        actions = [
            'open_project',
            'open_project_in_new_window',
            'open_workspace',
            'open_workspace_in_new_window',
            'append_project',
            'edit_project',
            'rename_project',
            'remove_project',
            'rename_workspace',
            'remove_workspace',
            'create_project',
            'add_workspace',
            'add_folder',
            'import_sublime_project',
            'refresh_projects',
            'clear_recent_projects',
            'remove_dead_projects'
        ]

        # If the current project cannot switch workspace (either because workspace
        # management is off or because there is only one workspace), we remove the
        # actions on workspace (open, open in new window, rename and remove)
        if not self.manager.can_switch_workspaces():
            for workspace_action_index in sorted([2, 3, 8, 9], reverse=True):
                actions.pop(workspace_action_index)
                items.pop(workspace_action_index)

        # Can't add a workspace if no project is currently opened
        if self.manager.curr_pname is None:
            index = actions.index('add_workspace')
            actions.pop(index)
            items.pop(index)

        def callback(i):
            if i < 0:
                return
            self.run(action=actions[i], caller="manager")

        sublime.set_timeout(
            lambda: self.window.show_quick_panel(items, callback),
            100)

    def _prompt_project(self, callback):
        self.manager.prompt_project(callback, on_cancel=self._on_cancel)

    def _prompt_workspace(self, project, callback, default):
        if not default and not self.manager.can_switch_workspaces():
            sublime.status_message("No workspace to execute this action")
            return
        self.manager.prompt_workspace(project, callback, on_cancel=self._on_cancel)

    def _on_cancel(self):
        if self.caller == "manager":
            sublime.set_timeout(self.run, 100)

    def open_project(self):
        # If the `activate_workspaces` option is True, the action `open_project`
        # and `open_project_in_new_window` automatically asks on which one
        # of the project's workspaces to act
        if pm_settings.get('activate_workspaces', True):
            callback = partial(self.open_workspace, default=True)
            self._prompt_project(callback)
        else:
            self._prompt_project(self.manager.switch_project)

    def open_project_in_new_window(self):
        if pm_settings.get('activate_workspaces', True):
            callback = partial(self.open_workspace_in_new_window, default=True)
            self._prompt_project(callback)
        else:
            self._prompt_project(self.manager.open_in_new_window)

    def open_workspace(self, project=None, default=False):
        callback = partial(self.manager.switch_project, project)
        self._prompt_workspace(project, callback, default)

    def open_workspace_in_new_window(self, project=None, default=False):
        callback = partial(self.manager.open_in_new_window, project, close_project=False)
        self._prompt_workspace(project, callback, default)

    def append_project(self):
        self._prompt_project(self.manager.append_project)

    def edit_project(self):
        self._prompt_project(self.manager.edit_project)

    def rename_project(self):
        self._prompt_project(self.manager.rename_project)

    def rename_workspace(self):
        self._prompt_workspace(None, self.manager.rename_workspace, True)

    def remove_project(self):
        self._prompt_project(self.manager.remove_project)

    def remove_workspace(self):
        self._prompt_workspace(None, self.manager.remove_workspace, False)

    def create_project(self):
        self.manager.create_project(on_cancel=self._on_cancel)

    def add_workspace(self):
        self.manager.add_workspace()

    def add_folder(self):
        self.manager.add_folder()

    def import_sublime_project(self):
        self.manager.import_sublime_project(on_cancel=self._on_cancel)

    def refresh_projects(self):
        self.manager.projects_info.refresh_projects()
        sublime.status_message("Projects refreshed !")

    def clear_recent_projects(self):
        self.manager.clear_recent_projects()

    def remove_dead_projects(self):
        self.manager.clean_dead_projects()
