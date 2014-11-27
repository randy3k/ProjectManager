Project Manager for Sublime Text 3
===

Dont't have any idea what `*.sublime-project` and `*.sublime-workspace` are doing? Forget where the project files are? Project Manager helps in organizing the project files by putting all files under `Packages/Users/Projects/`. It is inspired by Atom's [Project Manager](https://atom.io/packages/project-manager).

![](https://raw.githubusercontent.com/randy3k/Project-Manager/master/pm.png)

### Installation

You can install Project Manager via Package Control. To launch the Project Manager, you can either open it under the `Project` menu, via the command palette, or use the hotkey `ctrl+cmd+p` (`ctrl+alt+p` for windows/linux).

### Usage
If you want Project Manager to manage the `*.sublime-project` and `*.sublime-workspace` files, you should open the project folder and use the "Add Folder" option of Project Manager. On the other hand, if you want to keep the project files where they are, you can use the "Import" option.

Other options are self-explained, enjoy!

### Add existing projects to Project Manager

There are two ways to add existing projects to Project Manager.

1. Put your `.sublime-project` and `.sublime-workspace` files in the project directory `Packages/Users/Projects/`.
2. Open your project, and then use the import option of Project Manager. Project Manager will memorize where the corresponding `.sublime-project` is located and open it accordingly. In other words, you can put the `.sublime-project` file in any places.

### Custom Projects directory

To use a different directory for your projects rather than `Packages/Users/Projects/`, edit the following in package settings: Preferences -> Package Settings -> Project Manager

```
{
    "projects_dir": "path/to/custom/projects_dir",
}
```

### Optional keybind
You can additionally add the following keybind in your user keybind settings file for "Open project in new window"

```
    {
      "keys": ["super+ctrl+o"],
      "command": "project_manager_list", "args": {"action": "new"}
    }
```
