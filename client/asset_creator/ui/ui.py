import sys

import ayon_api
from ayon_core.style import load_stylesheet
from qtpy import QtWidgets, QtCore, QtGui

from . import images

DEFAULT_FOLDER_TYPES = {"Folder", "Library", "Asset", "Episode", "Sequence", "Shot"}


class TreeSelectorButton(QtWidgets.QPushButton):
    """Button that opens a popup with a QTreeWidget for folder selection.

    Displays the selected folder name on the button. Clicking opens
    a dropdown-like popup with the full folder hierarchy.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_id = None
        self._selected_name = "/ (root)"
        self.setText(self._selected_name)
        self.clicked.connect(self._show_popup)

        self._popup = QtWidgets.QFrame(
            self, QtCore.Qt.WindowType.Popup
        )
        self._popup.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        popup_layout = QtWidgets.QVBoxLayout(self._popup)
        popup_layout.setContentsMargins(0, 0, 0, 0)

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(True)
        self.tree.itemClicked.connect(self._on_item_clicked)
        popup_layout.addWidget(self.tree)

        self._popup.setMaximumHeight(300)

    def _show_popup(self):
        """Show the tree popup below the button, matching its width."""
        pos = self.mapToGlobal(self.rect().bottomLeft())
        self._popup.move(pos)
        self._popup.setFixedWidth(self.width())
        self._popup.show()

    def _on_item_clicked(self, item, column):
        """Select the clicked item and close the popup."""
        self._selected_id = item.data(
            0, QtCore.Qt.ItemDataRole.UserRole
        )
        self._selected_name = item.text(0)
        self.setText(self._selected_name)
        self._popup.hide()

    def selected_folder_id(self):
        """Return the folder ID of the currently selected item."""
        return self._selected_id

    def set_selected(self, folder_id, name):
        """Set the currently selected folder."""
        self._selected_id = folder_id
        self._selected_name = name
        self.setText(name)

    def select_by_id(self, folder_id):
        """Select the tree item matching the given folder ID.

        Args:
            folder_id: The folder ID to select, or None for root.
        """
        if folder_id is None:
            self.set_selected(None, "/ (root)")
            return

        iterator = QtWidgets.QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            if item.data(0, QtCore.Qt.ItemDataRole.UserRole) == folder_id:
                self.set_selected(folder_id, item.text(0))
                self.tree.setCurrentItem(item)
                return
            iterator += 1

        self.set_selected(None, "/ (root)")


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
        # Maps folder_type -> parent_id (deduced from existing project structure)
        self._parent_ids_by_type = {}

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
        self.type_combo_box.currentTextChanged.connect(
            self._on_type_changed
        )
        form_layout.addRow("Asset Type", self.type_combo_box)

        self.parent_folder_combo = TreeSelectorButton()
        form_layout.addRow("Parent Folder", self.parent_folder_combo)

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

        # Notification label above the create button
        self.notification_label = QtWidgets.QLabel()
        self.notification_label.setWordWrap(True)
        self.notification_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.notification_label.setStyleSheet(
            "QLabel {"
            "  color: rgb(255, 150, 50);"
            "  font-size: 11px;"
            "  padding: 6px 10px;"
            "  background-color: rgba(255, 150, 50, 30);"
            "  border: 1px solid rgb(255, 150, 50);"
            "  border-radius: 4px;"
            "}"
        )
        self.notification_label.hide()
        main_layout.addWidget(self.notification_label)

        # Refresh and Create buttons
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

        # Refresh asset types from project folder types, excluding defaults
        folder_types = project_settings.get("folderTypes", [])
        self.type_combo_box.clear()
        for folder_type in sorted(folder_types, key=lambda f: f.get("name", "")):
            name = folder_type.get("name")
            if name and name not in DEFAULT_FOLDER_TYPES:
                self.type_combo_box.addItem(name)

        if self.type_combo_box.count() == 0:
            self.type_combo_box.addItem("No asset types found")
            self.type_combo_box.setEnabled(False)
            self.add_asset_button.setEnabled(False)
            self.notification_label.setText(
                "No custom asset types found for this project. "
                "Please add asset types in the project settings."
            )
            self.notification_label.show()
        else:
            self.type_combo_box.setEnabled(True)
            self.add_asset_button.setEnabled(True)
            self.notification_label.hide()

        # Fetch all folders with attribs to read containedAssetType
        all_folders = list(ayon_api.get_folders(
            project_name=project_name,
            fields=["id", "name", "folderType", "parentId",
                     "attrib.containedAssetType"],
        ))
        self._parent_ids_by_type = self._detect_parent_folders(all_folders)
        self._populate_parent_folders(all_folders)
        self._on_type_changed()

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

    @staticmethod
    def _detect_parent_folders(all_folders):
        """Detect parent folders using the 'containedAssetType' custom attribute.

        Looks for folders that declare which asset types they contain.
        If no folder declares a given type, the asset will default to root.

        Args:
            all_folders: List of folder dicts from ayon_api.get_folders.

        Returns:
            Dict mapping folder_type (str) -> parent_id (str).
        """
        result = {}
        for folder in all_folders:
            attrib = folder.get("attrib") or {}
            contained_type = attrib.get("containedAssetType")
            if contained_type and contained_type not in result:
                result[contained_type] = folder["id"]

        return result

    def _populate_parent_folders(self, all_folders):
        """Populate the parent folder tree with the project's folder hierarchy.

        Builds a tree structure matching the Ayon folder hierarchy.
        Each item stores the folder ID as UserRole data.
        """
        tree = self.parent_folder_combo.tree
        tree.clear()

        # Add root item
        root_item = QtWidgets.QTreeWidgetItem(["/ (root)"])
        root_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, None)
        tree.addTopLevelItem(root_item)

        # Build tree from folder hierarchy
        id_to_widget = {}
        sorted_folders = sorted(all_folders, key=lambda f: f["name"])

        for folder in sorted_folders:
            folder_id = folder["id"]
            name = folder["name"]
            folder_type = folder.get("folderType", "")
            display = f"{name}  ({folder_type})" if folder_type else name

            item = QtWidgets.QTreeWidgetItem([display])
            item.setData(0, QtCore.Qt.ItemDataRole.UserRole, folder_id)
            id_to_widget[folder_id] = item

        # Parent each item under its parent widget
        for folder in sorted_folders:
            folder_id = folder["id"]
            parent_id = folder.get("parentId")
            item = id_to_widget[folder_id]

            parent_widget = id_to_widget.get(parent_id)
            if parent_widget:
                parent_widget.addChild(item)
            else:
                root_item.addChild(item)

        root_item.setExpanded(True)
        self.parent_folder_combo.set_selected(None, "/ (root)")

    def _on_type_changed(self):
        """Pre-select the detected parent folder when the asset type changes."""
        folder_type = self.type_combo_box.currentText()
        parent_id = self._parent_ids_by_type.get(folder_type)
        self.parent_folder_combo.select_by_id(parent_id)

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

        # Get parent folder from tree combo (user may have changed it)
        folder_type = self.type_combo_box.currentText()
        parent_id = self.parent_folder_combo.selected_folder_id()

        try:
            folder_id = ayon_api.create_folder(
                project_name=project_name,
                name=asset_name,
                folder_type=folder_type,
                parent_id=parent_id,
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

        # Notify parent that an asset was created (even if some tasks failed)
        self.asset_created.emit()

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
