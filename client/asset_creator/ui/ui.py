import sys

import ayon_api
from ayon_core.style import load_stylesheet
from ayon_core.tools.utils import get_ayon_qt_app
from qtpy import QtWidgets, QtCore, QtGui

from . import images

ASSET_TYPES = ["CHAR", "BG", "CAM", "PROP"]


class MainWindow(QtWidgets.QDialog):
    """Dialog for creating assets in an Ayon project.

    Provides a form to select a project, enter an asset name,
    choose an asset type, and pick which tasks to create
    alongside the asset folder.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("David Assethoff")
        self.setWindowIcon(
            QtGui.QIcon(f"{images.__path__[0]}/david_assethoff.png")
        )

        app_instance = get_ayon_qt_app()
        app_instance.setStyleSheet(load_stylesheet())

        self.resize(320, 360)
        self._task_checkboxes = []

        self._build_ui()
        self._populate_projects()
        self.project_changed()

    def _build_ui(self):
        """Build the dialog layout: form fields, scrollable task
        checkboxes, and create button."""
        main_layout = QtWidgets.QVBoxLayout(self)

        # Form: Project, Name, Asset Type
        form_layout = QtWidgets.QFormLayout()
        form_layout.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.projects_combo_box = QtWidgets.QComboBox()
        self.projects_combo_box.currentTextChanged.connect(
            self.project_changed
        )
        form_layout.addRow("Project", self.projects_combo_box)

        self.asset_name_line_edit = QtWidgets.QLineEdit()
        form_layout.addRow("Asset Name", self.asset_name_line_edit)

        self.type_combo_box = QtWidgets.QComboBox()
        self.type_combo_box.addItems(ASSET_TYPES)
        form_layout.addRow("Asset Type", self.type_combo_box)

        main_layout.addLayout(form_layout)

        # Tasks
        tasks_label = QtWidgets.QLabel("Tasks")
        main_layout.addWidget(tasks_label)

        self._tasks_container = QtWidgets.QWidget()
        self._tasks_layout = QtWidgets.QVBoxLayout(self._tasks_container)
        self._tasks_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self._tasks_container)
        main_layout.addWidget(scroll_area)

        # Create button
        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addStretch()
        self.add_asset_button = QtWidgets.QPushButton("Create Asset")
        self.add_asset_button.clicked.connect(self.create_asset)
        buttons_layout.addWidget(self.add_asset_button)
        main_layout.addLayout(buttons_layout)

    def _populate_projects(self):
        """Fetch project names from Ayon and populate the combo box.

        Disables the create button if no projects are available.
        """
        project_names = list(ayon_api.get_project_names())
        if project_names:
            self.projects_combo_box.addItems(project_names)
        else:
            self.add_asset_button.setEnabled(False)

    def project_changed(self):
        """Refresh the task checkboxes when the selected project changes.

        Fetches task types from the new project's settings and
        creates a checkbox for each one inside the scroll area.
        """
        project_name = self.projects_combo_box.currentText()
        if not project_name:
            return

        self._clear_tasks()

        project_settings = ayon_api.get_project(project_name)
        task_types = project_settings.get("taskTypes", [])

        for task_type in task_types:
            task_name = task_type.get("name")
            if not task_name:
                continue
            checkbox = QtWidgets.QCheckBox(task_name)
            self._tasks_layout.addWidget(checkbox)
            self._task_checkboxes.append(checkbox)

    def _clear_tasks(self):
        """Remove all task checkboxes from the layout and the
        internal tracking list."""
        for checkbox in self._task_checkboxes:
            checkbox.deleteLater()
        self._task_checkboxes.clear()

    def _get_checked_tasks(self):
        """Return the names of all currently checked task checkboxes."""
        return [
            cb.text() for cb in self._task_checkboxes if cb.isChecked()
        ]

    def create_asset(self):
        """Create an asset folder in Ayon with the selected tasks.

        Creates the folder first, then iterates over checked tasks.
        If some tasks fail, the asset is still created and a partial
        error is reported to the user.
        """
        asset_name = self.asset_name_line_edit.text().strip()
        if not asset_name:
            self._show_error("Asset name is empty")
            return

        project_name = self.projects_combo_box.currentText()
        tasks = self._get_checked_tasks()

        try:
            folder_id = ayon_api.create_folder(
                project_name=project_name,
                name=asset_name,
                folder_type="Asset",
                tags=[self.type_combo_box.currentText()],
            )
        except ayon_api.exceptions.HTTPRequestError as e:
            if e.response.status_code == 409:
                self._show_error(
                    f"Asset '{asset_name}' already exists"
                )
            else:
                self._show_error(str(e))
            return

        failed_tasks = []
        for task in tasks:
            try:
                ayon_api.create_task(
                    project_name=project_name,
                    name=task,
                    task_type=task,
                    folder_id=folder_id,
                )
            except ayon_api.exceptions.HTTPRequestError:
                failed_tasks.append(task)

        if failed_tasks:
            self._show_error(
                f"Asset '{asset_name}' created but these tasks "
                f"failed: {', '.join(failed_tasks)}"
            )
        else:
            self._show_success(
                f"Successfully created asset '{asset_name}'"
            )

    def _show_error(self, message):
        """Display an error dialog with the given message."""
        QtWidgets.QMessageBox.critical(self, "Error", message)

    def _show_success(self, message):
        """Display a success dialog with the given message."""
        QtWidgets.QMessageBox.information(self, "Success", message)


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(
        QtGui.QIcon(f"{images.__path__[0]}/david_assethoff.png")
    )
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
