Project Manager for Sublime Text 3
===

Dont't have any idea what `*.sublime-project` and `*.sublime-workspace` are doing? Forget where the project files are? Project Manager will help organizing the project files for you. It is inspired by Atom's [Project Manager](https://atom.io/packages/project-manager).

Project Manager also improves the shortcut <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>W</kbd> on Windows and Linux so that it will close the project when the window is closed. On OSX, it is the default behaviour.

![](https://raw.githubusercontent.com/randy3k/Project-Manager/master/pm.png)

If you like it, you could send me some tips via [paypal](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=YAPVT8VB6RR9C&lc=US&item_name=tips&currency_code=USD&bn=PP%2dDonationsBF%3abtn_donateCC_LG%2egif%3aNonHosted) or [gratipay](https://gratipay.com/~randy3k/).

### Installation

You can install Project Manager via Package Control. To launch the Project Manager, you can either open it under the `Project` menu, via the command palette, or use the hotkey <kbd>Ctrl</kbd>+<kbd>Cmd</kbd>+<kbd>P</kbd> (<kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>P</kbd> for windows/linux).

### Usage
Options are self-explained, enjoy!

#### Create new project

Just drag some folders to Sublime Text and then "Add Folder". The project files will be created in `Packages/Users/Projects/`.

#### Add existing projects to Project Manager

There are two ways to add existing projects to Project Manager. 
If you want to keep the project files (`.sublime-project` and `sublime-workspace`) in your project directory, you should follow the first method. If you want Project Manager manages the project files, follow the second method.

1. Open your project file `.sublime-project`, and then use the import option of Project Manager. This tells Project Manager where `.sublime-project` is located and Project Manager will know where to look when the project is opened. In other words, you can put the `.sublime-project` file in any places.
2. Move your `.sublime-project` and `.sublime-workspace` files in the project directory `Packages/Users/Projects/`.


#### Custom Projects directory

To use a different directory for your projects rather than `Packages/Users/Projects/`, edit the following in package settings: Preferences -> Package Settings -> Project Manager

```
{
    "projects_fpath": ["path/to/custom/projects_dir"],
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

### Show Open Files

It is know that Subliem Text has a [bug](https://github.com/SublimeTextIssues/Core/issues/62) in showing open files. Project Manager includes a fix to this issue.

The default value of  `show_open_files ` in Project Manager is `false`. It will make sure that the all the Projects will hide the open file. However, if your view setting is not consistent with the default value (i.e. the view is showing open files), you will still get the issue. 

It is not always necessary to set `show_open_files` to `true`. It depends on your view setting: `View -> Side Bar -> Show/Hide Open File`. The easier solution is to do `View -> Side Bar -> Hide Open File`. However, if you really want to show open files, Then you have to do
```
{
"show_open_files": true,
}
```
in Project Managet settings.

### License

Project Manager is MIT licensed.
