import sys

import ayon_api
from ayon_core.style import load_stylesheet
from ayon_core.settings import get_project_settings
from qtpy import QtWidgets, QtCore, QtGui

from . import images


class ImageDropZone(QtWidgets.QLabel):
    """Drop zone widget that accepts image files via drag & drop or click.

    Displays a preview of the dropped image or a placeholder message.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._image_path = None
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(100)
        self.setMaximumHeight(120)
        self.setAcceptDrops(True)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            "QLabel {"
            "  border: 2px dashed rgb(120, 130, 140);"
            "  border-radius: 5px;"
            "  color: rgb(160, 170, 180);"
            "  font-size: 11px;"
            "}"
        )
        self._set_placeholder()

    def _set_placeholder(self):
        """Display the default placeholder text."""
        self.setText("Drop an image here\nor click to browse")
        self._image_path = None

    def image_path(self):
        """Return the path of the currently loaded image, or None."""
        return self._image_path

    def _load_image(self, path):
        """Load and display an image from the given file path."""
        pixmap = QtGui.QPixmap(path)
        if pixmap.isNull():
            return
        self._image_path = path
        scaled = pixmap.scaled(
            self.size(),
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)

    def mousePressEvent(self, event):
        """Open a file dialog to select an image on click."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        if path:
            self._load_image(path)

    def dragEnterEvent(self, event):
        """Accept the drag if it contains image file URLs."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Load the first dropped image file."""
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                self._load_image(path)
                event.acceptProposedAction()
                return
        event.ignore()

    def clear(self):
        """Reset the drop zone to its placeholder state."""
        super().clear()
        self._set_placeholder()


class MainWindow(QtWidgets.QDialog):
    """Dialog for creating assets in an Ayon project.

    Provides a form to select a project, enter an asset name,
    choose an asset type, and pick which tasks to create
    alongside the asset folder.

    Signals:
        asset_created: Emitted when an asset is successfully created.
    """

    asset_created = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("David Assethoff")
        self.setWindowIcon(
            QtGui.QIcon(f"{images.__path__[0]}/david_assethoff.png")
        )

        self.setStyleSheet(load_stylesheet())

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
        self.asset_name_line_edit.setPlaceholderText("Name of the asset...")
        form_layout.addRow("Asset Name", self.asset_name_line_edit)

        self.type_combo_box = QtWidgets.QComboBox()
        self.type_combo_box.currentTextChanged.connect(self.folder_type_changed)
        form_layout.addRow("Asset Type", self.type_combo_box)

        self.tasks_template_combo_box = QtWidgets.QComboBox()
        self.tasks_template_combo_box.currentTextChanged.connect(self.tasks_template_changed)
        form_layout.addRow("Tasks Template", self.tasks_template_combo_box)

        self.description_text_edit = QtWidgets.QTextEdit()
        self.description_text_edit.setPlaceholderText("Optional description...")
        self.description_text_edit.setMaximumHeight(60)
        form_layout.addRow("Description", self.description_text_edit)

        self.image_drop_zone = ImageDropZone()
        form_layout.addRow("Thumbnail", self.image_drop_zone)

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
        self.refresh_button = QtWidgets.QPushButton()
        self.refresh_button.setIcon(
            QtGui.QIcon(f"{images.__path__[0]}/refresh.png")
        )
        self.refresh_button.setToolTip("Refresh")
        self.refresh_button.setFlat(True)
        self.refresh_button.setCursor(
            QtCore.Qt.CursorShape.PointingHandCursor
        )
        self.refresh_button.clicked.connect(self.project_changed)
        buttons_layout.addWidget(self.refresh_button)
        buttons_layout.addStretch()
        self.add_asset_button = QtWidgets.QPushButton("Create Asset")
        self.add_asset_button.clicked.connect(self.create_asset)

        self.create_more_checkbox = QtWidgets.QCheckBox("Create more")
        buttons_layout.addWidget(self.create_more_checkbox)
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

    def folder_type_changed(self):
        """
        Select default task types for the new folder type found in the project settings
        """
        tasks_templates_names = self._get_tasks_templates_names_for_selected_folder_type()
        self.tasks_template_combo_box.clear()
        self.tasks_template_combo_box.addItems(tasks_templates_names)

    def tasks_template_changed(self):
        """

        """
        selected_tasks_template_data = self._get_selected_tasks_template_project_settings()

        for check_box in self._task_checkboxes:
            check_box.setChecked(False)
            if check_box.text() in selected_tasks_template_data.get("default_task_types", []):
                check_box.setChecked(True)
        return

    def _get_selected_folder_type_project_settings(self):
        settings = get_project_settings(self.projects_combo_box.currentText()).get("asset_creator") or {}
        selected_folder_type = self.type_combo_box.currentText()

        folder_types_data = settings.get("folder_types", [])
        folder_type_data = next(
            (item for item in folder_types_data if item["name"] == selected_folder_type), {}
        )
        return folder_type_data

    def _get_selected_tasks_template_project_settings(self):
        selected_tasks_template = self.tasks_template_combo_box.currentText()
        folder_type_data = self._get_selected_folder_type_project_settings()
        tasks_templates_data = folder_type_data.get("tasks_templates", [])
        task_template_data = next(
            (item for item in tasks_templates_data if item["name"] == selected_tasks_template), {}
        )

        return task_template_data

    def _get_tasks_templates_names_for_selected_folder_type(self):
        folder_type_data = self._get_selected_folder_type_project_settings()
        return [item["name"] for item in folder_type_data.get("tasks_templates", {})]

    def project_changed(self):
        """Refresh the task checkboxes when the selected project changes.

        Fetches task types from the new project's settings and
        creates a checkbox for each one inside the scroll area.
        """
        project_name = self.projects_combo_box.currentText()
        if not project_name:
            return

        self._clear_user_inputs()
        self._clear_tasks()

        project_anatomy = ayon_api.get_project(project_name)

        # Prevent crash if we try to fetch an anatomy from a project that the user can't access
        if not project_anatomy:
            projects = ayon_api.get_projects()
            project_anatomy = next(projects)
            self.projects_combo_box.setCurrentText(project_anatomy.get("name"))

        asset_creator_settings = get_project_settings(project_name).get("asset_creator")

        # Refresh asset types from project folder types
        self.type_combo_box.clear()
        available_folder_types = [item["name"] for item in asset_creator_settings.get("folder_types")]
        for folder_type in available_folder_types:
            self.type_combo_box.addItem(folder_type)

        task_types = project_anatomy.get("taskTypes", [])

        for task_type in task_types:
            task_name = task_type.get("name")
            if not task_name:
                continue
            checkbox = QtWidgets.QCheckBox(task_name)
            self._tasks_layout.addWidget(checkbox)
            self._task_checkboxes.append(checkbox)
        self.folder_type_changed()

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

    def _get_parent_id_by_folder_type(self, folder_type: str):
        """Get parent id from correspondance defined in project settings
        """
        project_name = self.projects_combo_box.currentText()
        folder_types = get_project_settings(project_name).get("asset_creator").get("folder_types")

        parent_folder_path = next(iter([
                    folder["parent_folder"]
                    for folder in folder_types
                    if folder["name"] == folder_type
            ]),None
        )
        if not parent_folder_path:
            self._show_error(
                (f"Can't find corresponding folder path for folders of type '{folder_type}'."
                "Please check that this addon's projects settings are correctly defined.")
            )
            raise Exception

        parent_folder = ayon_api.get_folder_by_path(project_name, parent_folder_path, fields=["id"])
        if not parent_folder:
            self._show_error(
                (f"Can't find folder at path '{parent_folder_path}'."
                 "Please check that this addon's projects settings are correctly defined.")
            )
            raise Exception

        return parent_folder.get('id')

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
        description = self.description_text_edit.toPlainText().strip()

        attrib = {}
        if description:
            attrib["description"] = description

        # Upload thumbnail first to get its ID
        thumbnail_id = None
        thumbnail_path = self.image_drop_zone.image_path()
        if thumbnail_path:
            try:
                thumbnail_id = ayon_api.create_thumbnail(
                    project_name=project_name,
                    src_filepath =thumbnail_path,
                )
            except Exception as e:
                self._show_error(f"Failed to upload thumbnail: {e}")

        folder_type = self.type_combo_box.currentText()
        try:
            folder_id = ayon_api.create_folder(
                project_name=project_name,
                name=asset_name,
                folder_type=folder_type,
                parent_id=self._get_parent_id_by_folder_type(folder_type),
                attrib=attrib,
                thumbnail_id=thumbnail_id,
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
            self._clear_user_inputs()

        # Notify parent that an asset was created (even if some tasks failed)
        self.asset_created.emit()
        if not self.create_more_checkbox.isChecked():
            self.close()

    def _show_error(self, message):
        """Display an error dialog with the given message."""
        QtWidgets.QMessageBox.critical(self, "Error", message)

    def _show_success(self, message):
        """Display a success dialog with the given message."""
        QtWidgets.QMessageBox.information(self, "Success", message)

    def _clear_user_inputs(self):
        """Clear user-entered data"""
        self.asset_name_line_edit.clear()
        self.description_text_edit.clear()
        self.type_combo_box.clearEditText()
        self.image_drop_zone.clear()
        self.folder_type_changed()

    def showEvent(self, event):
        super().showEvent(event)
        self._clear_user_inputs()


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
