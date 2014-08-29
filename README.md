Project Manager for Sublime Text 3
===

Dont't have any idea what `*.sublime-project` and `*.sublime-workspace` are doing? Forget where the project files are? Project Manager helps in organizing the profile files by putting all files under `Packages/Users/Projects/`.

[SideBarFolders](https://github.com/SublimeText/SideBarFolders) is a lot lighter than the bulit-in project system, but it does not have any management functionality at all. I really hate that a folder cannot be easily removed in SideBarFolders. Now, you have a new option other than SiderBarFolders. Project Manager helps in managing multiple projects with a minimal amount of effort. It is inspired by Atom's [Project Manager](https://atom.io/packages/project-manager).

![](https://raw.githubusercontent.com/randy3k/Project-Manager/master/pm.png)

### Installation

You can install Project Manager via Package Control. To launch the Project Manager, you can either open it under the `Project` menu, or use the hotkey `ctrl+cmd+p` (`ctrl+alt+p` for windows/linux).

### Usage
Drag some folders into your Sublime Text window and add a project to Project Manager. The options are self-explained, enjoy!

### Project Manager? Simple Project Manager?

A while ago, I created a similar package [Simple Project Manager](https://github.com/randy3k/Simple-Project-Manager) aiming to provide better experiences in project management. Simple Project Manager only handles the `*.sublime-project` settings and ignores the workspace settings. It was [suggested](http://www.sublimetext.com/forum/viewtopic.php?f=5&t=16683) that workspace files contain a lot of useful information such as open file history, search history, remember build system etc. For the sake of more complete coverage of the project functionality, I rewrote the package and that's how Project Manager was created. I stop developing SPM as this manager is recommended over the SPM.
