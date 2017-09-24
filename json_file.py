import sublime
import os


class JsonFile:
    def __init__(self, fpath, encoding='utf-8'):
        self.encoding = encoding
        self.fpath = fpath

    def load(self, default=[]):
        self.fdir = os.path.dirname(self.fpath)
        if not os.path.isdir(self.fdir):
            os.makedirs(self.fdir)
        if os.path.exists(self.fpath):
            with open(self.fpath, mode='r', encoding=self.encoding) as f:
                content = f.read()
                try:
                    data = sublime.decode_value(content)
                except Exception:
                    sublime.message_dialog('%s is bad!' % self.fpath)
                    raise
                if not data:
                    data = default
        else:
            with open(self.fpath, mode='w', encoding=self.encoding, newline='\n') as f:
                data = default
                f.write(sublime.encode_value(data, True))
        return data

    def save(self, data, indent=4):
        self.fdir = os.path.dirname(self.fpath)
        if not os.path.isdir(self.fdir):
            os.makedirs(self.fdir)
        with open(self.fpath, mode='w', encoding=self.encoding, newline='\n') as f:
            f.write(sublime.encode_value(data, True))

    def remove(self):
        if os.path.exists(self.fpath):
            os.remove(self.fpath)
