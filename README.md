# Project Manager for Sublime Text 3

<a href="https://packagecontrol.io/packages/ProjectManager"><img src="https://packagecontrol.herokuapp.com/downloads/ProjectManager.svg"></a>
<a href="https://www.paypal.com/cgi-bin/webscr?cmd=_donations&amp;business=Randy%2ecs%2elai%40gmail%2ecom&amp;lc=US&amp;item_name=Package&amp;currency_code=USD&amp;bn=PP%2dDonationsBF%3apaypal%2ddonate%2dyellow%2esvg%3aNonHosted" title="Donate to this project using Paypal"><img src="https://img.shields.io/badge/paypal-donate-blue.svg" /></a>
<a href="https://gratipay.com/~randy3k/" title="Donate to this project using Gratipay"><img src="https://img.shields.io/badge/gratipay-donate-yellow.svg" /></a>

Dont't have any idea what `*.sublime-project` and `*.sublime-workspace` are doing? Forget where the project files are? Don't worry, Project Manager will help organizing the project files by putting them in a centralized location. (It is inspired by Atom's [Project Manager](https://atom.io/packages/project-manager), but Atom's Project Manager is inspired by the built-in Sublime Text Project Manager,
so there is a circular reasoning here).

![](https://cloud.githubusercontent.com/assets/1690993/20858319/7f12a6ec-b911-11e6-8fc5-f4cbf6b6f12b.png)


### Installation

You can install Project Manager via Package Control.

You can additionally add the following keybind in your user keybind settings file for "Open project in new window"

```
{
    "keys": ["super+ctrl+o"], // or ["ctrl+alt+o"] for Windows/Linux
    "command": "project_manager", "args": {"action": "new"}
}
```

### Usage

To launch the Project Manager, you can either open it under the `Project` menu or via the command palette: `Project Manager: ...`.

To quick switch between projects, use the hotkey <kbd>Ctrl</kbd>+<kbd>Cmd</kbd>+<kbd>P</kbd> (<kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>P</kbd> for windows/linux).

Project Manager also improves the shortcut <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>W</kbd> on Windows and Linux so that it will close the project when the window is closed. On OSX, it is the default behaviour.


![](https://cloud.githubusercontent.com/assets/1690993/20858332/9f6508ea-b911-11e6-93b9-3cccca1d663e.png)
![](https://cloud.githubusercontent.com/assets/1690993/20858333/a7a16a1c-b911-11e6-938c-0fe77e2cf405.png)


Options are self-explained, enjoy!


#### Create new project

Just drag some folders to Sublime Text and then "Add Project". The project files will be created in `Packages/User/Projects/`.

#### Add existing projects to Project Manager

There are two ways to add existing projects to Project Manager. 
If you want to keep the project files (`.sublime-project` and `sublime-workspace`) in your project directory,

- Open your project file `.sublime-project`, and then use the import option of Project Manager. This tells Project Manager where `.sublime-project` is located and Project Manager will know where to look when the project is opened. In other words, you can put the `.sublime-project` file in any places.

If you want Project Manager manages the project files

- Move your `.sublime-project` and `.sublime-workspace` files in the project directory `Packages/User/Projects/`. You may need to update the project's folder information of the files.


#### Custom Projects directory

To use a different directory for your projects rather than `Packages/User/Projects/`, edit the following in package settings: Preferences -> Package Settings -> Project Manager

```
{
    "projects_path": ["path/to/custom/projects_dir"],
}
```


### License

Project Manager is MIT licensed.
