import sublime
import sublime_plugin
import subprocess
import os
import shutil
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

        # Automatically close window if no folders nor sheets are open
        # (this happen when trying to open a workspace already opened in another window)
        if not window.folders() and not window.sheets():
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
    """Main class that takes care of everything project and workspace related"""

    def __init__(self, window):
        self.window = window
        settings_file = 'project_manager.sublime-settings'
        self.settings = sublime.load_settings(settings_file)

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

        # Clear recent projects file if it doesn't support workspaces
        json_file = JsonFile(os.path.join(self.primary_dir, 'recent.json'))
        recent_files = json_file.load([])
        if recent_files and type(recent_files[0]) != dict:
            json_file.remove()
            self.window.run_command("clear_recent_projects_and_workspaces")

        # Update file organization and reload info if needed
        if self.reorganize_files(self.projects_path):
            self.projects_info = self.get_all_projects_info()

        pname = self.window.project_file_name()
        if pname:
            self.curr_pname = os.path.basename(re.sub(r'\.sublime-project$', '', pname))
        else:
            self.curr_pname = None

    def reorganize_files(self, project_paths):
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

        Args:
            project_paths : list[str]
                The list of paths to every folder that contains projects to be managed

        Returns:
            bool: whether some files were reorganized or not
        """

        modified = False
        for pdir in project_paths:
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

                    # Move all of its existing workspaces files
                    for wfile in self.projects_info[pname]['workspaces']:
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

        return modified

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

    def is_workspace_affiliated(self, project, wfile):
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

    def get_project_workspaces(self, pfile):
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
                    and self.is_workspace_affiliated(pname, file)):
                wfiles.append(os.path.normpath(file))

        # If no workspace exists, create a default one
        if not wfiles:
            wfile = re.sub(r'\.sublime-project$', '.sublime-workspace', pfile)
            j = JsonFile(wfile)
            j.save({'project': pname})
            wfiles.append(os.path.normpath(wfile))

        return wfiles

    def get_info_from_project_file(self, pfile):
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
        info["name"] = pname
        info["folder"] = folder
        info["file"] = pfile
        info["workspaces"] = self.get_project_workspaces(pfile)
        return info

    def mark_open_projects(self, all_info):
        project_file_names = [
            os.path.realpath(w.project_file_name())
            for w in sublime.windows() if w.project_file_name()]

        for v in all_info.values():
            if os.path.realpath(v["file"]) in project_file_names:
                v["star"] = True

    def can_switch_workspaces(self):
        """Check if a project in opened in the current window and if it has more than
        one workspaces

        Returns:
            bool: whether a project with more than one workspace is currently opened
        """
        if self.curr_pname not in self.projects_info:
            return False

        pinfo = self.projects_info[self.curr_pname]
        return ("star" in pinfo and len(pinfo["workspaces"]) > 1)

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

    def nb_workspaces(self, project):
        """Returns the number of workspaces a given project has saved

        Args:
            project: str
                The name of the project for which to count workspaces
        """
        if project in self.projects_info:
            return len(self.projects_info[project]['workspaces'])
        return 0

    def render_workspace(self, wfile):
        """Given a workspace file, returns a tuplet with its file, its name and a
        prettified path to the file

        Args:
            wfile: str
                The complete path to the workspace file

        Returns:
            list[(str, str, str)]: a tuplet composed of the path of the file, the name of
                the workspace and a prettified path to the file to display to the user
        """
        wname = os.path.basename(re.sub(r'\.sublime-workspace$', '', wfile))
        wfolder = os.path.dirname(wfile)
        return [wfile, wname, pretty_path(wfolder)]

    def move_default_workspace_to_top(self, project, wlist):
        """Move the default workspace of a project to the top of the list of workspaces

        The default workspace of a project is defined as the workspace that has the same
        name of file. For example, the project `test.sublime-project` has for default
        workspace `test.sublime-workspace`.
        The default workspace corresponds to the one created by sublime-text by default.

        Args:
            project: str
                The name of the project
            wlist: list[(str, str, str)]
                A list of information of all of the project's workspaces as given by
                self.render_workspace (i.e. [(wpath, wname, pretty(wpath))])

        Returns:
            list[(str, str, str)]: the same workspace list where the default workspace,
                if found, has been moved to the top of the list
        """
        for i in range(len(wlist)):
            if wlist[i][1] == project:
                wlist.insert(0, wlist.pop(i))
                break

        return wlist

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
            wlist: list[(str, str, str)]
                A list of information of all of the project's workspaces as given by
                self.render_workspace (i.e. [(wpath, wname, pretty(wpath))])
            move_second: bool
                Whether to move the most recently opened workspace in second position

        Returns:
            list[(str, str, str)]: the sorted list of workspaces according to their
                index in the `recent.json` file
        """
        j = JsonFile(os.path.join(self.primary_dir, 'recent.json'))
        recent = j.load([])

        # We look for the project in the `recent.json` file and extract the list of its
        # workspaces (sorted by most recently opened)
        for obj in recent:
            pname = os.path.basename(re.sub(r'\.sublime-project$', '', obj["project"]))
            if pname == project:
                recent = obj["workspaces"]
                break
        else:
            return wlist

        # Sort workspaces according to their index in the recent list
        wlist.sort(key=lambda w: recent.index(w[0]) if w[0] in recent else -1,
                   reverse=True)

        # Switch first and second if the current window is in a project...
        if move_second and self.curr_pname is not None:
            # ...and this project is the one from which we want to load a workspace
            if self.curr_pname != project:
                return wlist

            if wlist[0][0] in recent:
                wlist[0], wlist[1] = wlist[1], wlist[0]

        return wlist

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
        if project not in self.projects_info:
            raise ValueError('Project not found !')

        # Load workspaces and their information, then sort them alphabetically
        wfiles = self.projects_info[project]["workspaces"]
        wlist = list(map(self.render_workspace, wfiles))
        wlist.sort(key=lambda w: w[1])

        if self.settings.get('show_recent_workspaces_first', True):
            move_second = self.settings.get('show_most_recent_workspace_second', True)
            wlist = self.move_recent_workspaces_to_top(project, wlist, move_second)

        if self.settings.get('show_default_workspace_first', False):
            wlist = self.move_default_workspace_to_top(project, wlist)

        # Change name of default workspace (cf. method `get_default_workspace`) to "(Default)"
        for i, (wpath, wname, wfolder) in enumerate(wlist):
            if wname == project:
                wlist[i] = [wpath, '(Default)', wfolder]

        return list(map(itemgetter(0), wlist)), list(map(itemgetter(1, 2), wlist))

    def move_recent_projects_to_top(self, plist):
        j = JsonFile(os.path.join(self.primary_dir, 'recent.json'))
        recent = j.load([])
        recent = [pretty_path(obj["project"]) for obj in recent]
        plist.sort(key=lambda p: recent.index(p[3]) if p[3] in recent else -1,
                   reverse=True)
        return plist

    def move_opened_projects_to_top(self, plist):
        count = 0
        for i in range(len(plist)):
            if plist[i][0] != plist[i][1]:
                plist.insert(count, plist.pop(i))
                count = count + 1
        return plist

    def display_projects(self):
        plist = list(map(self.render_display_item, self.projects_info.items()))
        plist.sort(key=lambda p: p[0])
        if self.settings.get('show_recent_projects_first', True):
            plist = self.move_recent_projects_to_top(plist)

        if self.settings.get('show_active_projects_first', True):
            plist = self.move_opened_projects_to_top(plist)
        return list(map(itemgetter(0), plist)), list(map(itemgetter(1, 2), plist))

    def project_file_name(self, project):
        return self.projects_info[project]['file']

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
        workspaces = self.projects_info[project]['workspaces']
        workspaces.sort(key=lambda wfile: os.path.basename(wfile))

        # If one of the workspace has default name, return it
        for workspace in workspaces:
            wname = os.path.basename(re.sub(r'\.sublime-workspace$', '', workspace))
            if wname == project:
                return workspace

        # Else, try to get the most recent
        recent_file = os.path.join(self.primary_dir, 'recent.json')
        if not os.path.exists(recent_file):
            return workspaces[0]

        j = JsonFile(recent_file)
        recent = j.load([])
        if project not in [pw['project'] for pw in recent]:
            return workspaces[0]
        else:
            return recent[project]["workspaces"][-1]

    def update_recent(self, project, wfile=None):
        """Update the `recent.json` file to put the given project and workspace in most
        recent spot

        Args:
            project: str
                The name of the project
            wfile: str
                The path of the workspace file
        """
        j = JsonFile(os.path.join(self.primary_dir, 'recent.json'))
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
                j = JsonFile(os.path.join(self.primary_dir, 'recent.json'))
                j.remove()
                self.window.run_command("clear_recent_projects_and_workspaces")

        sublime.set_timeout(clear_callback, 100)

    def get_project_data(self, project):
        return JsonFile(self.project_file_name(project)).load()

    def close_project_by_window(self, window):
        window.run_command('close_workspace')

    def close_project_by_name(self, project):
        pfile = os.path.realpath(self.project_file_name(project))
        closed = False
        for w in sublime.windows():
            if w.project_file_name():
                if os.path.realpath(w.project_file_name()) == pfile:
                    self.close_project_by_window(w)
                    if w.id() != sublime.active_window().id():
                        w.run_command('close_window')
                    closed = True
        return closed

    def add_project(self):
        def add_callback(project):
            pd = self.window.project_data()
            pf = self.window.project_file_name()
            pfile = os.path.join(self.primary_dir, project, '%s.sublime-project' % project)
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
            wfile = re.sub(r'\.sublime-project$', '.sublime-workspace', pfile)
            if not os.path.exists(wfile):
                JsonFile(wfile).save({"project": os.path.basename(pfile)})

            self.close_project_by_window(self.window)
            # nuke the current window by closing sidebar and all files
            self.window.run_command('close_project')
            self.window.run_command('close_all')

            # reload projects info
            self.__init__(self.window)
            self.switch_project(project, wfile)

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

    def add_workspace(self):
        def add_callback(new_workspace):
            project = self.curr_pname
            if not project:
                sublime.message_dialog("No active project")
                return

            if not new_workspace:
                new_workspace = project

            wfile = self.get_default_workspace(project)
            new_wfile = os.path.join(os.path.dirname(wfile),
                                     new_workspace + '.sublime-workspace')

            if wfile == new_wfile or os.path.exists(new_wfile):
                sublime.message_dialog("Another workspace is already named " + new_workspace)
                return

            # Trick: instead of using obscure undocumented sublime commands to create a
            # new workspace file, copy # an existing sublime-workspace file and reset
            # its data to get a new one
            shutil.copy(wfile, new_wfile)
            j = JsonFile(new_wfile)
            j.save({'project': project + ".sublime-project"})

            # Reload projects info
            self.__init__(self.window)
            self.open_in_new_window(None, new_wfile, False)

        def show_input_panel():
            workspace = 'NewWorkspace'
            v = self.window.show_input_panel('Workspace name:',
                                             workspace,
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
    def switch_project(self, project, workspace=None):
        if project is None:
            project = self.curr_pname
        if workspace is None:
            workspace = self.get_default_workspace(project)
        self.update_recent(project, workspace)
        self.close_project_by_window(self.window)
        subl('--project', workspace)

    @dont_close_windows_when_empty
    def open_in_new_window(self, project, workspace=None, close_project=True):
        if project is None:
            project = self.curr_pname
        if workspace is None:
            workspace = self.get_default_workspace(project)
        self.update_recent(project, workspace)
        if close_project:
            self.close_project_by_name(project)
        subl('-n', '--project', workspace)

    def _remove_project(self, project):
        answer = sublime.ok_cancel_dialog('Remove "%s" from Project Manager?' % project)
        if answer is True:
            pfile = self.project_file_name(project)
            if self.which_project_dir(pfile):
                self.close_project_by_name(project)
                os.remove(self.project_file_name(project))
                for workspace in self.projects_info[project]['workspaces']:
                    os.remove(workspace)
                os.removedirs(os.path.dirname(pfile))

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

    def _remove_workspace(self, wfile):
        workspace = os.path.basename(re.sub(r'\.sublime-workspace$', '', wfile))
        answer = sublime.ok_cancel_dialog('Remove workspace "%s" from this project?\n'
                                          'Warning: this will close any window opened '
                                          'containing the corresponding project' % workspace)
        if answer is True:
            project = self.curr_pname
            self.close_project_by_name(project)
            os.remove(wfile)
            self.__init__(self.window)
            sublime.status_message('Workspace "%s" is removed.' % project)
            window = sublime.active_window()
            if window.folders() == [] and window.sheets() == []:
                window.run_command('close_window')

    def remove_workspace(self, wfile):
        sublime.set_timeout(lambda: self._remove_workspace(wfile), 100)

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
            if not new_project or project == new_project:
                return

            if new_project in self.projects_info:
                sublime.message_dialog("Another project is already called like this")
                return

            pfile = self.project_file_name(project)
            pdir = self.which_project_dir(pfile)
            in_project_dir = pdir is not None
            if in_project_dir:
                pdir = os.path.join(pdir, project)
            else:
                pdir = os.path.dirname(pfile)

            new_pfile = os.path.join(pdir, '%s.sublime-project' % new_project)
            reopen = self.close_project_by_name(project)
            os.rename(pfile, new_pfile)

            for wfile in self.projects_info[project]['workspaces']:
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

                j = JsonFile(new_wfile)
                data = j.load({})
                data['project'] = '%s.sublime-project' % os.path.basename(new_project)
                j.save(data)

            if in_project_dir:
                try:
                    path = os.path.dirname(pfile)
                    new_path = os.path.join(os.path.dirname(path), new_project)
                    os.rename(path, new_path)
                except OSError:
                    pass
            else:
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
                self.open_in_new_window(new_project, None)

        def show_input_panel():
            v = self.window.show_input_panel('New project name:',
                                             project,
                                             rename_callback,
                                             None,
                                             None)
            v.run_command('select_all')

        sublime.set_timeout(show_input_panel, 100)

    def rename_workspace(self, wfile):
        def rename_callback(new_workspace):
            project = self.curr_pname
            if not new_workspace:
                new_workspace = project

            new_wfile = os.path.join(os.path.dirname(wfile),
                                     new_workspace + '.sublime-workspace')

            if wfile == new_wfile or os.path.exists(new_wfile):
                sublime.message_dialog("Another workspace is already named " + new_workspace)
                return

            self.close_project_by_name(project)
            os.rename(wfile, new_wfile)
            self.__init__(self.window)
            subl('--project', new_wfile)

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
        settings = sublime.load_settings('project_manager.sublime-settings')
        if settings.get("close_project_when_close_window", True) and \
                command_name == "close_window":
            window.run_command("project_manager_close_project")


class ProjectManager(sublime_plugin.WindowCommand):

    def show_quick_panel(self, items, on_done):
        sublime.set_timeout(
            lambda: self.window.show_quick_panel(items, on_done),
            10)

    def choose_ws(self, action, project=None):
        """Display a sublime-text quick panel to choose a workspace from a list

        Args:
            action: str
                An action from the list of basic possible actions (cf self.show_options)
            project: str
                The name of the project from which to choose the workspace
        """
        self.project = project

        try:
            self.workspaces, wdisplays = self.manager.display_workspaces(project)
        except ValueError:
            return
        callback = eval('self.on_' + action)
        self.show_quick_panel(wdisplays, callback)

    def run(self, action=None, caller=None):
        self.manager = Manager(self.window)

        can_switch_workspaces = self.manager.can_switch_workspaces()
        if action is None:
            self.show_options(can_switch_workspaces)
        elif action == 'add_project':
            self.manager.add_project()
        elif action == 'add_workspace':
            self.manager.add_workspace()
        elif action == 'import_sublime_project':
            self.manager.import_sublime_project()
        elif action == 'clear_recent_projects':
            self.manager.clear_recent_projects()
        elif action == 'remove_dead_projects':
            self.manager.clean_dead_projects()
        elif action.endswith('_ws'):
            if not can_switch_workspaces:
                sublime.status_message("No workspace to execute this action")
                return

            self.caller = caller
            self.choose_ws(action)
        else:
            self.caller = caller
            try:
                self.projects, pdisplays = self.manager.display_projects()
            except ValueError:
                return

            if not self.projects:
                sublime.message_dialog('No projects are managed currently.')
                return

            # If the `default_workspaces` option is True, the action `switch` and `new`
            # automatically asks on which one of the project's workspaces to act
            if action in ('switch', 'new') and can_switch_workspaces and \
                    self.manager.settings.get('default_workspaces', True):
                def callback(a):
                    # User cancelled at the project choice step
                    if a < 0:
                        if self.caller == 'manager':
                            sublime.set_timeout(self.run, 10)
                        return

                    project = self.projects[a]
                    # If the project only has one workspace, no need to ask the user
                    if self.manager.nb_workspaces(project) < 2:
                        eval('self.on_'+action)(a)
                    else:
                        self.choose_ws(action+'_ws', project)

                self.show_quick_panel(pdisplays, callback)

            else:
                callback = eval('self.on_' + action)
                self.show_quick_panel(pdisplays, callback)

    def show_options(self, can_switch_workspaces):
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
            ['Add New Project', 'Add current folders to Project Manager'],
            ['Add New Workspace', 'Add a new workspace to the current project'],
            ['Import Project', 'Import current .sublime-project file'],
            ['Clear Recent Projects', 'Clear Recent Projects'],
            ['Remove Dead Projects', 'Remove Dead Projects']
        ]

        actions = ['switch', 'new',
                   'switch_ws', 'new_ws',
                   'append', 'edit',
                   'rename', 'remove',
                   'rename_ws', 'remove_ws',
                   'add_project', 'add_workspace',
                   'import_sublime_project',
                   'clear_recent_projects',
                   'remove_dead_projects']

        # If the current project cannot switch workspace (either because workspace
        # management is off or because there is only one workspace), we remove the
        # actions on workspace (switch, switch in new window, rename and remove)
        if not can_switch_workspaces:
            for i in range(len(actions)-1, -1, -1):
                if actions[i].endswith('_ws'):
                    actions.pop(i)
                    items.pop(i)

        # Can't add a workspace if no project is currently opened
        if self.manager.curr_pname is None:
            index = actions.index('add_workspace')
            actions.pop(index)
            items.pop(index)

        def callback(a):
            # Invalid action, user cancelled
            if a < 0:
                return

            caller = 'manager' if a <= actions.index('add_project') - 1 else None
            self.run(action=actions[a], caller=caller)

        self.show_quick_panel(items, callback)

    @cancellable
    def on_new(self, action_id):
        self.manager.open_in_new_window(self.projects[action_id])

    @cancellable
    def on_new_ws(self, action_id):
        self.manager.open_in_new_window(self.project, self.workspaces[action_id], False)

    @cancellable
    def on_switch(self, action_id):
        self.manager.switch_project(self.projects[action_id])

    @cancellable
    def on_switch_ws(self, action_id):
        self.manager.switch_project(self.project, self.workspaces[action_id])

    @cancellable
    def on_append(self, action_id):
        self.manager.append_project(self.projects[action_id])

    @cancellable
    def on_edit(self, action_id):
        self.manager.edit_project(self.projects[action_id])

    @cancellable
    def on_rename(self, action_id):
        self.manager.rename_project(self.projects[action_id])

    @cancellable
    def on_remove(self, action_id):
        self.manager.remove_project(self.projects[action_id])

    @cancellable
    def on_rename_ws(self, action_id):
        self.manager.rename_workspace(self.workspaces[action_id])

    @cancellable
    def on_remove_ws(self, action_id):
        self.manager.remove_workspace(self.workspaces[action_id])
