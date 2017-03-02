import sublime
import sublime_plugin
import os

def plugin_loaded():
    t = sublime.load_settings('Project Manager.sublime-settings')
    s = sublime.load_settings('project_manager.sublime-settings')
    keys = [
        'projects_path',
        'use_local_projects_dir',
        'show_open_files',
        'show_recent_projects_first'
    ]
    d = {}
    for k in keys:
        if t.has(k) and not s.has(k):
            d.update({k: t.get(k)})
    for key, value in d.items():
        s.set(key, value)
    if d:
        sublime.save_settings('project_manager.sublime-settings')

    old_file = os.path.join(sublime.packages_path(), 'User', 'Project Manager.sublime-settings')
    if os.path.exists(old_file):
        os.remove(old_file)
