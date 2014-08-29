Project Manager for Sublime Text 3
===

Dont't have any idea what `*.sublime-project` and `*.sublime-workspace` are doing? Forget where the project files are? Project Manager helps in organizing the project files by putting all files under `Packages/Users/Projects/`. It is inspired by Atom's [Project Manager](https://atom.io/packages/project-manager).

![](https://raw.githubusercontent.com/randy3k/Project-Manager/master/pm.png)

### Installation

You can install Project Manager via Package Control. To launch the Project Manager, you can either open it under the `Project` menu, via the command palette, or use the hotkey `ctrl+cmd+p` (`ctrl+alt+p` for windows/linux).

### Usage
Drag some folders into your Sublime Text window and add a project to Project Manager. The options are self-explained, enjoy!

### Project Manager? Simple Project Manager?

A while ago, I created a similar package [Simple Project Manager](https://github.com/randy3k/Simple-Project-Manager) aiming to provide better experiences in project management. Simple Project Manager only handles the `*.sublime-project` settings and ignores the workspace settings. It was [suggested](http://www.sublimetext.com/forum/viewtopic.php?f=5&t=16683) that workspace files contain a lot of useful information such as open file history, search history, remember build system etc. For the sake of a more complete coverage, I rewrote the package and Project Manager was born. Development of SPM has been stopped as this manager is recommended over SPM.

### Add existing projects to Project Manager

Just put your `.sublime-project` and `.sublime-workspace` files under the directory `Packages/Users/Projects/`.