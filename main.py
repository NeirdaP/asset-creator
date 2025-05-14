import sys
from qtpy import QtWidgets, QtCore, QtGui
import ayon_api

import icons

ASSET_TYPES = ["CHAR", "BG", "CAM", "PROP"]


class MainWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("David Assethoff")
        print(icons.__path__)
        self.resize(QtCore.QSize(320, 360))
        self.setLayout(QtWidgets.QVBoxLayout())
        self.connection = ayon_api.ServerAPI(
            "http://ayon.supamonks.lan",
        )
        self.connection.login(
            "raphael.bandet",
            "supamonk09,"
        )

        # Project
        project_names = self.connection.get_project_names()

        projects_widget = QtWidgets.QWidget()
        projects_widget.setLayout(QtWidgets.QHBoxLayout())

        projects_label = QtWidgets.QLabel("Project")
        projects_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.projects_combo_box = QtWidgets.QComboBox()
        self.projects_combo_box.addItems(project_names)
        self.projects_combo_box.currentTextChanged.connect(self.project_changed)
        projects_widget.layout().addWidget(projects_label)
        projects_widget.layout().addWidget(self.projects_combo_box)

        # Asset Name
        asset_name_widget = QtWidgets.QWidget()
        asset_name_widget.setLayout(QtWidgets.QHBoxLayout())
        asset_name_label = QtWidgets.QLabel("Name")
        asset_name_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.asset_name_line_edit = QtWidgets.QLineEdit()
        self.asset_name_line_edit.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        asset_name_widget.layout().addWidget(asset_name_label)
        asset_name_widget.layout().addWidget(self.asset_name_line_edit)

        # Asset Type
        type_widget = QtWidgets.QWidget()
        type_widget.setLayout(QtWidgets.QHBoxLayout())
        type_label = QtWidgets.QLabel("Asset Type")
        type_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.type_combo_box = QtWidgets.QComboBox()
        self.type_combo_box.addItems(ASSET_TYPES)

        type_widget.layout().addWidget(type_label)
        type_widget.layout().addWidget(self.type_combo_box)

        # Tasks
        self.tasks_group = QtWidgets.QGroupBox("Tasks")
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.tasks_group)
        self.tasks_group.setLayout(QtWidgets.QVBoxLayout())
        self.project_changed()

        # Buttons
        buttons_widget = QtWidgets.QWidget()
        buttons_widget.setLayout(QtWidgets.QHBoxLayout())
        buttons_widget.layout().addStretch()
        self.add_asset_button = QtWidgets.QPushButton("Create Asset")
        self.add_asset_button.clicked.connect(self.create_asset)
        self.add_asset_button.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
        buttons_widget.layout().addWidget(self.add_asset_button)

        self.layout().addWidget(projects_widget)
        self.layout().addWidget(asset_name_widget)
        self.layout().addWidget(type_widget)
        self.layout().addWidget(scroll_area)
        self.layout().addWidget(buttons_widget)

    def show_error_dialog(self, message):
        """
        Shows an error dialog with the given message
        Args:
            message (str): message displayed in the dialog
        """
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setIcon(QtWidgets.QMessageBox.Critical)
        msg_box.setWindowTitle("Error")
        msg_box.setText(message)
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msg_box.exec()

    def show_success_dialog(self, message):
        """
        Shows a success dialog with the given message
        Args:
            message (str): message displayed in the dialog
        """
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setIcon(QtWidgets.QMessageBox.Information)
        msg_box.setWindowTitle("Success")
        msg_box.setText(message)
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msg_box.exec()

    def project_changed(self):
        """
        Triggered when current project in the project's combo box is changed
        Updates the ui to remove old tasks and display available tasks from the new project
        """
        self.clear_task_types_widgets()
        project_name = self.projects_combo_box.currentText()
        project_settings = self.connection.get_project(project_name)
        task_names = [task_type.get("name") for task_type in project_settings.get("taskTypes")]
        for task_name in task_names:
            task_widget = QtWidgets.QWidget()
            task_widget.setLayout(QtWidgets.QHBoxLayout())
            task_check_box = QtWidgets.QCheckBox()
            task_check_box.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
            task_label = QtWidgets.QLabel(task_name)
            task_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
            task_label.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
            task_widget.layout().addWidget(task_check_box)
            task_widget.layout().addWidget(task_label)
            self.tasks_group.layout().addWidget(task_widget)

    def clear_task_types_widgets(self):
        """
        Removes every widget under the task group box
        """
        while self.tasks_group.layout().count():
            child = self.tasks_group.layout().takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def create_asset(self):
        """
        Creates asset in ayon, with all checked tasks
        Shows a dialog to display if it was a success or a failure
        """
        asset_name = self.asset_name_line_edit.text()
        if not asset_name:
            self.show_error_dialog("Asset name is empty")
            return
        tasks = self.get_checked_tasks()
        try:
            folder_id = self.connection.create_folder(
                project_name=self.projects_combo_box.currentText(),
                name=asset_name,
                folder_type="Asset",
                tags=[self.type_combo_box.currentText()]
            )
        except ayon_api.exceptions.HTTPRequestError as e:
            # Handle all exceptions here with the status code
            message = str(e)
            status_code = e.response.status_code

            if status_code == 409:
                message = f"Asset '{asset_name}' already exists"

            self.show_error_dialog(message)
            return
        for task in tasks:
            self.connection.create_task(
                project_name=self.projects_combo_box.currentText(),
                name=task,
                task_type=task,
                folder_id=folder_id
            )
        self.show_success_dialog(f"Successfully created asset '{asset_name}'")

    def get_checked_tasks(self):
        """
        Gets all checked tasks in the tasks group box

        Returns:
            list(str): Names of checked tasks
        """
        tasks = []
        for i in range(self.tasks_group.layout().count()):
            item = self.tasks_group.layout().itemAt(i)
            widget = item.widget()
            if widget:
                checkbox_item = widget.layout().itemAt(0)
                label_item = widget.layout().itemAt(1)
                if checkbox_item.widget().isChecked():
                    tasks.append(label_item.widget().text())
        return tasks


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(f"{icons.__path__[0]}/david_assethoff.png"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
