## CHANGELOG

### [0.7.3](https://github.com/randy3k/ProjectManager/compare/0.7.2...0.7.3)

Changes since 0.7.2:

Other:
 - Refactor python code

Contributors:
 - Randy Lai
 - Johannes Rappen


### [0.7.2](https://github.com/randy3k/ProjectManager/compare/0.7.1...0.7.2)

* update README
* add key bindings for windows and linux
* use realpath for detecting window to close
* better name the command as "Add New Project"

### [0.7.1](https://github.com/randy3k/ProjectManager/compare/0.7.0...0.7.1)

* fix #55

### [0.7.0](https://github.com/randy3k/ProjectManager/compare/0.6.11...0.7.0)

* fix typo
* remove show_open_files settings as the bug was fixed
* use re.sub instead of replace to fix #54
* use relative link
* rename as ProjectManager

### [0.6.11](https://github.com/randy3k/ProjectManager/compare/0.6.10...0.6.11)

* redundant caption
* feature: remove dead projects
* change default order of projects list

### [0.6.10](https://github.com/randy3k/ProjectManager/compare/0.6.9...0.6.10)

* cannonicalize projects directories
* update menus and screenshots
* use close_all instead

### [0.6.9](https://github.com/randy3k/ProjectManager/compare/0.6.8...0.6.9)

* close project by window or name

### [0.6.8](https://github.com/randy3k/ProjectManager/compare/0.6.7...0.6.8)

* use try-catch errors
* only when library exists
* no long check close_windows_when_empty
* rename to get_info_from_project_file
* cannonicalize paths to fix #47

### [0.6.7](https://github.com/randy3k/ProjectManager/compare/0.6.6...0.6.7)

* use set_timeout instead of set_timeout_async
* only check library file if it exists
* rename functions for better readability
* only close non-active window

### [0.6.6](https://github.com/randy3k/ProjectManager/compare/0.6.5...0.6.6)

* focus on the original view

### [0.6.5](https://github.com/randy3k/ProjectManager/compare/0.6.4...0.6.5)

* auto refresh folder list
* various updates
* update README
* confirm to clear recent projects
* remove refresh folder functionality
* add emptylink in before / after code block
* fix #2

### [0.6.4](https://github.com/randy3k/ProjectManager/compare/0.6.3...0.6.4)

* show message when project list is empty

### [0.6.3](https://github.com/randy3k/ProjectManager/compare/0.6.2...0.6.3)

* fix window closing behaviour
* fix which_project_dir bug again

### [0.6.2](https://github.com/randy3k/ProjectManager/compare/0.6.1...0.6.2)

* bootstrap manager run function
* resolve symlink
* rename function to expand_folder
* fix which_project_dir

### [0.6.1](https://github.com/randy3k/ProjectManager/compare/0.6.0...0.6.1)

* add `get_project_files()`
* add `get_project_info()`
* don't use timeoout_async
* pep8 fix

### 0.6.0

* first release
