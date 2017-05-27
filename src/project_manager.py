import sublime
import sublime_plugin
import subprocess
import os
import platform
import re

from .json_file import JsonFile


def subl(args=[]):
    # learnt from SideBarEnhancements
    executable_path = sublime.executable_path()
    if sublime.platform() == 'osx':
        app_path = executable_path[:executable_path.rfind('.app/') + 5]
        executable_path = app_path + 'Contents/SharedSupport/bin/subl'
    subprocess.Popen([executable_path] + args)

    def focus():
        # fix focus on windows
        window = sublime.active_window()
        view = window.active_view()
        window.run_command('focus_neighboring_group')
        window.focus_view(view)

    def on_activated():
        window = sublime.active_window()
        view = window.active_view()
        sublime_plugin.on_activated(view.id())
        sublime_plugin.on_activated_async(view.id())

    if sublime.platform() == 'windows':
        sublime.set_timeout(focus, 300)

    sublime.set_timeout(on_activated, 1000)


def expand_folder(folder, project_file):
    root = os.path.dirname(project_file)
    if not os.path.isabs(folder):
        folder = os.path.abspath(os.path.join(root, folder))
    return folder


def get_node():
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
            s.set('close_windows_when_empty', close_windows_when_empty)
    return f


class Manager:
    def __init__(self, window):
        self.window = window
        s = 'project_manager.sublime-settings'
        self.settings = sublime.load_settings(s)
        default_projects_dir = os.path.join(sublime.packages_path(),
                                            'User',
                                            'Projects')
        self.projects_path = self.settings.get(
            'projects_path', [self.settings.get('projects_dir', default_projects_dir)])

        self.projects_path = [
            os.path.normpath(os.path.expanduser(d)) for d in self.projects_path]

        node = get_node()
        if self.settings.get('use_local_projects_dir', False):
            self.projects_path = \
                [d + ' - ' + node for d in self.projects_path] + self.projects_path

        self.primary_dir = self.projects_path[0]
        self.projects_info = self.get_all_projects_info()

    def list_project_files(self, folder):
        pfiles = []
        library = os.path.join(folder, 'library.json')
        if os.path.exists(library):
            j = JsonFile(library)
            for f in j.load([]):
                if os.path.exists(f) and f not in pfiles:
                    pfiles.append(os.path.normpath(f))
            pfiles.sort()
            j.save(pfiles)
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

    def get_info_from_project_file(self, pfile):
        pdir = self.which_project_dir(pfile)
        if pdir:
            pname = re.sub('\.sublime-project$',
                           '',
                           os.path.relpath(pfile, pdir))
        else:
            pname = re.sub('\.sublime-project$',
                           '',
                           os.path.basename(pfile))
        pd = JsonFile(pfile).load()
        if pd and 'folders' in pd and pd['folders']:
            folder = pd['folders'][0].get('path', '')
        else:
            folder = ''
        star = False
        for w in sublime.windows():
            if w.project_file_name() == pfile:
                star = True
                break
        return {
            pname: {
                'folder': expand_folder(folder, pfile),
                'file': pfile,
                'star': star
                }
            }

    def get_all_projects_info(self):
        ret = {}
        for pdir in self.projects_path:
            pfiles = self.list_project_files(pdir)
            for f in pfiles:
                ret.update(self.get_info_from_project_file(f))
        return ret

    def which_project_dir(self, pfile):
        for pdir in self.projects_path:
            if (os.path.realpath(os.path.dirname(pfile))+os.path.sep).startswith(
                    os.path.realpath(pdir)+os.path.sep):
                return pdir
        return None

    def display_projects(self):
        plist = [[key, key + '*' if value['star'] else key, value['folder'], value['file']]
                 for key, value in self.projects_info.items()]
        plist = sorted(plist)
        if self.settings.get('show_recent_projects_first', True):
            j = JsonFile(os.path.join(self.primary_dir, 'recent.json'))
            recent = j.load([])
            plist = sorted(plist,
                           key=lambda p: recent.index(p[3]) if p[3] in recent else -1,
                           reverse=True)

        count = 0
        for i in range(len(plist)):
            if plist[i][0] is not plist[i][1]:
                plist.insert(count, plist.pop(i))
                count = count + 1
        return [item[0] for item in plist], [[item[1], item[2]] for item in plist]

    def project_file_name(self, project):
        return self.projects_info[project]['file']

    def project_workspace(self, project):
        return re.sub('\.sublime-project$',
                      '.sublime-workspace',
                      self.project_file_name(project))

    def update_recent(self, project):
        j = JsonFile(os.path.join(self.primary_dir, 'recent.json'))
        recent = j.load([])
        pname = self.project_file_name(project)
        if pname not in recent:
            recent.append(pname)
        else:
            recent.append(recent.pop(recent.index(pname)))
        # only keep the most recent 50 records
        if len(recent) > 50:
            recent = recent[(50-len(recent)):len(recent)]
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
        elif self.settings.has('show_open_files'):
            show_open_files = self.settings.get('show_open_files', False)
            data = j.load({})
            data['show_open_files'] = show_open_files
            df = data.get('distraction_free', {})
            df['show_open_files'] = show_open_files
            data['distraction_free'] = df
            j.save(data)

    @dont_close_windows_when_empty
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
        @dont_close_windows_when_empty
        def close_all_files():
            self.window.run_command('close_all')

        def add_callback(project):
            pd = self.window.project_data()
            f = os.path.join(self.primary_dir, '%s.sublime-project' % project)
            if pd:
                JsonFile(f).save(pd)
            else:
                JsonFile(f).save({})
            JsonFile(re.sub('\.sublime-project$', '.sublime-workspace', f)).save({})
            self.close_project_by_window(self.window)
            self.window.run_command('close_project')
            close_all_files()

            # reload projects info
            self.__init__(self.window)
            self.switch_project(project)

        def show_input_panel():
            project = 'New Project'
            pd = self.window.project_data()
            pf = self.window.project_file_name()
            try:
                path = pd['folders'][0]['path']
                if pf:
                    project = os.path.basename(expand_folder(path, pf))
                else:
                    project = os.path.basename(path)
            except:
                pass

            v = self.window.show_input_panel('Project name:',
                                             project,
                                             add_callback,
                                             None,
                                             None)
            v.run_command('select_all')

        sublime.set_timeout(show_input_panel, 100)

    def import_sublime_project(self):
        pfile = self.window.project_file_name()
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
        paths = [expand_folder(f.get('path'), self.project_file_name(project))
                 for f in pd.get('folders')]
        subl(['-a'] + paths)

    def switch_project(self, project):
        self.update_recent(project)
        self.check_project(project)
        self.close_project_by_window(self.window)
        self.close_project_by_name(project)
        subl([self.project_file_name(project)])

    def open_in_new_window(self, project):
        self.update_recent(project)
        self.check_project(project)
        self.close_project_by_name(project)
        subl(['-n', self.project_file_name(project)])

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
            new_wsfile = re.sub('\.sublime-project$', '.sublime-workspace', new_pfile)

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
