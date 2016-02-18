import sublime
import sublime_plugin


class ProjectManagerRefreshFolder(sublime_plugin.EventListener):

    def on_activated_async(self, view):
        sublime.active_window().run_command("refresh_folder_list")

    def on_deactivated_async(self, view):
        sublime.active_window().run_command("refresh_folder_list")
