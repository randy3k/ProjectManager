import sublime
import sublime_plugin

import os
import platform
import subprocess


computer_name = None


def get_computer_name():
    global computer_name

    if not computer_name:
        if sublime.platform() == 'osx':
            computer_name = subprocess.check_output(['scutil', '--get', 'ComputerName']).decode().strip()
        else:
            computer_name = platform.node().split('.')[0]

    return computer_name


def pretty_path(path):
    """Function to replace the content of '$HOME' in strings by '~/' """

    user_home = os.path.expanduser('~') + os.sep
    if path and path.startswith(user_home):
        path = os.path.join("~", path[len(user_home):])
    return path


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


def run_sublime(*args):
    """Run sublime executable as a subprocess, as it would be run in a terminal"""

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
