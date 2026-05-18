from qtpy import QtWidgets, QtCore, QtGui


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


class ColorPickerButton(QtWidgets.QPushButton):
    """Round button that displays a color and opens a color dialog when
    clicked.
    Emits`color_changed` when the user picks a new color."""

    color_changed = QtCore.Signal(QtGui.QColor)

    def __init__(self, color: QtGui.QColor, parent=None):
        super().__init__(parent)
        self._color = QtGui.QColor(color)
        self.setObjectName("ColorPickerButton")
        self.setFixedSize(18, 18)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Pick a color")
        self.clicked.connect(self._pick_color)
        self._refresh_style()

    def color(self) -> QtGui.QColor:
        return QtGui.QColor(self._color)

    def set_color(self, color: QtGui.QColor):
        self._color = QtGui.QColor(color)
        self._refresh_style()
        self.color_changed.emit(self._color)

    def _refresh_style(self):
        self.setStyleSheet(
            "QPushButton#ColorPickerButton {"
            f"  background: {self._color.name()};"
            "  border: 1px solid rgba(0, 0, 0, 80);"
            "  border-radius: 9px;"
            "}"
            "QPushButton#ColorPickerButton:hover {"
            "  border: 1px solid white;"
            "}"
        )

    def _pick_color(self):
        color = QtWidgets.QColorDialog.getColor(
            self._color, self, "Pick tag color"
        )
        if color.isValid():
            self.set_color(color)


class TagWidget(QtWidgets.QWidget):
    """A removable tag displayed as a colored rounded label, with a
    color picker to change its color and a button to remove it."""

    removed = QtCore.Signal(str)

    def __init__(self, text, color: QtGui.QColor, parent=None):
        super().__init__(parent)

        self.text = text

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.tag_label = QtWidgets.QLabel(text)
        self.tag_label.setObjectName("TagLabel")

        self.tag_label.setContentsMargins(8, 2, 8, 2)

        self.color_picker = ColorPickerButton(color)
        self.color_picker.color_changed.connect(self._apply_color)

        remove_button = QtWidgets.QPushButton("✕")
        remove_button.setObjectName("TagRemoveButton")
        remove_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        remove_button.setStyleSheet(
            "QPushButton#TagRemoveButton { background-color: none; }"
        )
        remove_button.clicked.connect(self._on_remove_clicked)

        layout.addWidget(self.tag_label)
        layout.addStretch()
        layout.addWidget(self.color_picker)
        layout.addWidget(remove_button)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )

        self._apply_color(color)

    def _apply_color(self, color: QtGui.QColor):
        self.tag_label.setStyleSheet(
            "QLabel#TagLabel {"
            f"  background: {color.name()};"
            "  border-radius: 10px;"
            "  color: white;"
            "  padding: 2px 8px;"
            "}"
        )

    def color(self) -> QtGui.QColor:
        return self.color_picker.color()

    def _on_remove_clicked(self):
        self.removed.emit(self.text)
        self.deleteLater()


class TagLineEdit(QtWidgets.QLineEdit):
    """Line edit that opens its completer popup with all entries on
    focus-in and on mouse press, so the user can browse suggestions
    without having to type first."""

    def show_all_completions(self):
        if self.completer():
            self.completer().setCompletionPrefix("")
            self.completer().complete()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.show_all_completions()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.show_all_completions()


class TagsWidget(QtWidgets.QWidget):
    """Input field with auto-completion that lets the user build a list
    of colored tags. Each tag is displayed on its own row with a color
    picker and a remove button. Suggestions and preselected colors come
    from the project tags passed via update_project_tags method."""

    DEFAULT_COLOR = "#4a90e2"  # light blue

    def __init__(self, project_tags):
        super().__init__()
        self.project_tags = {}  # name -> hex color from project anatomy
        self.active_tags = {}  # name -> TagWidget currently displayed

        main_layout = QtWidgets.QVBoxLayout(self)

        self.tags_layout = QtWidgets.QVBoxLayout()
        self.tags_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        main_layout.addLayout(self.tags_layout)

        self.tag_line_edit = TagLineEdit()
        self.tag_line_edit.setPlaceholderText("Add a tag...")
        main_layout.addWidget(self.tag_line_edit)

        self.completer_model = QtCore.QStringListModel()
        self.completer = QtWidgets.QCompleter()
        self.completer.setModel(self.completer_model)
        self.completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(QtCore.Qt.MatchFlag.MatchContains)
        self.completer.activated.connect(self.completer_pressed)

        self.tag_line_edit.setCompleter(self.completer)
        self.tag_line_edit.returnPressed.connect(self.add_current_tag)

        self.update_project_tags(project_tags)

    def completer_pressed(self, text):
        self.add_tag(text, self.project_tags.get(text))
        # Clear after Qt finished to complete the line edit
        QtCore.QTimer.singleShot(0, self.tag_line_edit.clear)

    def add_current_tag(self):
        text = self.tag_line_edit.text().strip()
        if text:
            self.add_tag(text=text, color=self.project_tags.get(text))
        self.tag_line_edit.clear()

    def add_tag(self, text, color=None):
        text = text.strip()
        if not text or text in self.active_tags:
            return
        if color is None:
            color = self.DEFAULT_COLOR

        tag_widget = TagWidget(text, QtGui.QColor(color))
        tag_widget.removed.connect(self._on_tag_removed)
        self.active_tags[text] = tag_widget
        self.tags_layout.addWidget(tag_widget)

    def _on_tag_removed(self, text):
        self.active_tags.pop(text, None)

    def get_active_tags(self):
        """Return a fresh dict of the active tags as {name: hex_color},
        reading the current color from each widget so changes made via
        the color picker are reflected."""
        return {
            name: widget.color().name()
            for name, widget in self.active_tags.items()
        }

    def update_project_tags(self, project_tags):
        self.project_tags = {
            tag["name"]: tag.get("color")
            for tag in project_tags
        }
        self.completer_model.setStringList(list(self.project_tags.keys()))

    def clear_active_tags(self):
        for tag_widget in list(self.active_tags.values()):
            tag_widget.deleteLater()
        self.active_tags.clear()
