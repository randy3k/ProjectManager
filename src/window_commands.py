import sublime
import sublime_plugin
from .project_manager import Manager


def cancellable(func):
    def _ret(self, action):
        if action >= 0:
            func(self, action)
        elif action < 0 and self.caller == 'manager':
            sublime.set_timeout(self.run, 10)
    return _ret


class ProjectManagerCloseWindow(sublime_plugin.WindowCommand):
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
        # close the window
        self.window.run_command('close_window')


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
