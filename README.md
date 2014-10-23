Project Manager for Sublime Text 3
===

Dont't have any idea what `*.sublime-project` and `*.sublime-workspace` are doing? Forget where the project files are? Project Manager helps in organizing the project files by putting all files under `Packages/Users/Projects/`. It is inspired by Atom's [Project Manager](https://atom.io/packages/project-manager).

![](https://raw.githubusercontent.com/randy3k/Project-Manager/master/pm.png)

### Installation

You can install Project Manager via Package Control. To launch the Project Manager, you can either open it under the `Project` menu, via the command palette, or use the hotkey `ctrl+cmd+p` (`ctrl+alt+p` for windows/linux).

### Usage
Drag some folders into your Sublime Text window and add a project to Project Manager. The options are self-explained, enjoy!

### Optional keybind
You can additionally add the following keybind in your user keybind settings file for "Open project in new window"

```
    {
      "keys": ["super+ctrl+o"],
      "command": "project_manager_list", "args": {"action": "new"}
    }
```

### Add existing projects to Project Manager

Just put your `.sublime-project` and `.sublime-workspace` files under the directory `Packages/Users/Projects/`.