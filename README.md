# [`ProjectManager`](https://github.com/randy3k/ProjectManager) for [Sublime Text](https://www.sublimetext.com)

[![License](https://img.shields.io/github/license/randy3k/ProjectManager.svg?style=flat-square)](https://github.com/randy3k/ProjectManager/blob/master/LICENSE.txt)
[![Downloads Package Control](https://img.shields.io/packagecontrol/dt/ProjectManager.svg?style=flat-square)](https://packagecontrol.io/packages/ProjectManager)
[![Latest release](https://img.shields.io/github/tag/randy3k/ProjectManager.svg?style=flat-square)](https://github.com/randy3k/ProjectManager/releases/latest)
[![Donate via PayPal](https://img.shields.io/badge/paypal-donate-009cde.svg?style=flat-square)](https://www.paypal.me/randy3k/5usd)
[![Donate via Gratipay](https://img.shields.io/badge/gratipay-donate-yellow.svg?style=flat-square)](https://gratipay.com/~randy3k/)

Dont't have any idea what `*.sublime-project` and `*.sublime-workspace` are doing? Forget where the project files are? Don't worry, Project Manager will help organizing the project files by putting them in a centralized location. (It is inspired by Atom's [Project Manager](https://atom.io/packages/project-manager), but Atom's Project Manager is inspired by the built-in Sublime Text Project Manager, so there is a circular reasoning here).

![Screenshot](https://cloud.githubusercontent.com/assets/1690993/20858319/7f12a6ec-b911-11e6-8fc5-f4cbf6b6f12b.png)

## Requirements

ProjectManager targets and is tested against the **latest Build** of Sublime Text.

* [ST3 (stable)](https://www.sublimetext.com/3)
* [ST3 (dev)](https://www.sublimetext.com/3dev)

## Installation

Using **Package Control** is not required, but recommended as it keeps your packages (with their dependencies) up-to-date!

### Installation via Package Control

* [Install Package Control](https://packagecontrol.io/installation#st3)
  * Close and reopen Sublime Text after having installed Package Control.
* Open the Command Palette (`Tools > Command Palette`).
* Choose `Package Control: Install Package`.
* Search for [`ProjectManager` on Package Control](https://packagecontrol.io/packages/ProjectManager) and select to install.

## Usage

To launch ProjectManager, use the main menu (`Project > Project Manager`) or the command palette (`Project Manager: ...`).

To quickly switch between projects, use the hotkey <kbd>Ctrl</kbd><kbd>Cmd</kbd><kbd>P</kbd> on macOS (<kbd>Ctrl</kbd><kbd>Alt</kbd><kbd>P</kbd> on Windows / Linux).

ProjectManager also improves the shortcut <kbd>Ctrl</kbd><kbd>Shift</kbd><kbd>W</kbd> on Windows / Linux so that it will close the project when the window is closed. On OSX, this is the default behaviour.

![](https://cloud.githubusercontent.com/assets/1690993/20858332/9f6508ea-b911-11e6-93b9-3cccca1d663e.png)
![](https://cloud.githubusercontent.com/assets/1690993/20858333/a7a16a1c-b911-11e6-938c-0fe77e2cf405.png)

Options are self-explanatory, enjoy!

### Create new project

Just drag some folders to Sublime Text and then "Add Project". The project files will be created in `Packages/User/Projects/`.

### Add existing projects to Project Manager

There are two ways to add existing projects to Project Manager. If you want to keep the project files (`*.sublime-project` and `*.sublime-workspace`) in your project directory,

- Open your project file `*.sublime-project`, and then use the import option of Project Manager. This tells Project Manager where `*.sublime-project` is located and Project Manager will know where to look when the project is opened. In other words, you can put the `*.sublime-project` file in any places.

If you want Project Manager manages the project files

- Move your `*.sublime-project` and `*.sublime-workspace` files in the project directory `Packages/User/Projects/`. You may need to update the project's folder information of the files.

### FAQ

- _How to open project in a new window with a shortcut?_
It can be done by adding the following keybind in your user keybind settings file:

```
{
    "keys": ["super+ctrl+o"], // or ["ctrl+alt+o"] for Windows/Linux
    "command": "project_manager", "args": {"action": "new"}
}
```


- _How to use a different project directory?_

To use a different directory for your projects rather than `Packages/User/Projects/`, edit the following in package settings: `Preferences > Package Settings > Project Manager`

```
{
    "projects_path": ["path/to/custom/projects_dir"],
}
```

## Source code

[github.com/randy3k/ProjectManager](https://www.github.com/randy3k/ProjectManager)

### License

Project Manager is MIT licensed.
