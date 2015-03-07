import sublime


def plugin_loaded():
    settings_file = 'pm.sublime-settings'
    settings = sublime.load_settings(settings_file)
    if settings.get("use_machine_projects_dir", False):
        settings.set('use_local_projects_dir', True)
        settings.erase("use_machine_projects_dir")
        sublime.save_settings(settings_file)
