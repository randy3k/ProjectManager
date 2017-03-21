import sublime
import sublime_plugin

from . import __pkg_name__


class PmReadmeCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        v = self.view.window().new_file()
        v.set_name(__pkg_name__ + ': Readme')
        v.settings().set('gutter', False)
        v.insert(edit, 0, sublime.load_resource('Packages/' + __pkg_name__ + '/README.md'))
        v.set_syntax_file('Packages/Markdown/Markdown.sublime-syntax')
        v.set_read_only(True)
        v.set_scratch(True)


class PmChangelogCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        v = self.view.window().new_file()
        v.set_name(__pkg_name__ + ': Changelog')
        v.settings().set('gutter', False)
        v.insert(edit, 0, sublime.load_resource('Packages/' + __pkg_name__ + '/CHANGELOG.md'))
        v.set_syntax_file('Packages/Markdown/Markdown.sublime-syntax')
        v.set_read_only(True)
        v.set_scratch(True)
