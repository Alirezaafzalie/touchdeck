import ctypes
import json
import os
import shlex
import subprocess
import sys

from PyQt6 import QtCore, QtGui, QtWidgets


APP_TITLE = "TouchDeck"
STANDARD_SHORTCUTS = {
    "Undo": "Ctrl+Z",
    "Redo": "Ctrl+Y",
    "Copy": "Ctrl+C",
    "Paste": "Ctrl+V",
    "Cut": "Ctrl+X",
    "SelectAll": "Ctrl+A",
}


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(path, config):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def parse_args(text):
    if not text.strip():
        return []
    return shlex.split(text, posix=False)


def normalize_shortcut(text):
    text = (text or "").strip()
    return STANDARD_SHORTCUTS.get(text, text)


def key_part_to_vk(key_part):
    if not key_part:
        return None
    key_map = {
        "TAB": 0x09,
        "ENTER": 0x0D,
        "RETURN": 0x0D,
        "ESC": 0x1B,
        "ESCAPE": 0x1B,
        "SPACE": 0x20,
        "SPACEBAR": 0x20,
        "BACKSPACE": 0x08,
        "BACK": 0x08,
        "DELETE": 0x2E,
        "DEL": 0x2E,
        "INSERT": 0x2D,
        "INS": 0x2D,
        "HOME": 0x24,
        "END": 0x23,
        "PAGEUP": 0x21,
        "PGUP": 0x21,
        "PAGEDOWN": 0x22,
        "PGDOWN": 0x22,
        "LEFT": 0x25,
        "UP": 0x26,
        "RIGHT": 0x27,
        "DOWN": 0x28,
    }
    upper = key_part.upper()
    if upper in key_map:
        return key_map[upper]
    if upper.startswith("F") and upper[1:].isdigit():
        num = int(upper[1:])
        if 1 <= num <= 24:
            return 0x70 + num - 1
    if len(key_part) == 1:
        ch = key_part.upper()
        if "A" <= ch <= "Z" or "0" <= ch <= "9":
            return ord(ch)
        vk = ctypes.windll.user32.VkKeyScanW(ord(key_part))
        if vk == -1:
            return None
        return vk & 0xFF
    return None


def parse_shortcut(text):
    text = normalize_shortcut(text)
    if not text:
        return [], None
    parts = [p.strip() for p in text.split("+") if p.strip()]
    if not parts:
        return [], None
    modifiers = []
    for part in parts[:-1]:
        part_lower = part.lower()
        if part_lower in ("ctrl", "control", "ctl"):
            modifiers.append(0x11)
        elif part_lower == "shift":
            modifiers.append(0x10)
        elif part_lower == "alt":
            modifiers.append(0x12)
        elif part_lower in ("meta", "win", "windows"):
            modifiers.append(0x5B)
    key_part = parts[-1]
    return modifiers, key_part


def send_shortcut(text):
    modifiers, key_part = parse_shortcut(text)
    vk = key_part_to_vk(key_part)
    if vk is None:
        return False
    user32 = ctypes.windll.user32
    key_up = 0x0002

    for mod in modifiers:
        user32.keybd_event(mod, 0, 0, 0)
    user32.keybd_event(vk, 0, 0, 0)
    user32.keybd_event(vk, 0, key_up, 0)
    for mod in reversed(modifiers):
        user32.keybd_event(mod, 0, key_up, 0)
    return True


def open_command(entry, parent=None):
    command = entry.get("command")
    args = entry.get("args", [])
    cwd = entry.get("cwd")
    if not command:
        shortcut = entry.get("shortcut")
        if shortcut and send_shortcut(shortcut):
            return
        QtWidgets.QMessageBox.critical(parent, APP_TITLE, "Missing command in config.")
        return

    try:
        if isinstance(command, str) and os.path.exists(command) and not args:
            os.startfile(command)  # type: ignore[attr-defined]
            return
        if isinstance(command, list):
            cmd = command
        else:
            cmd = [command]
        cmd.extend(args)
        subprocess.Popen(cmd, cwd=cwd or None)
    except Exception as exc:
        QtWidgets.QMessageBox.critical(parent, APP_TITLE, f"Failed to launch:\n{exc}")


class EditDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, entry=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Button" if entry else "Add Button")
        self.setModal(True)
        self.entry = entry or {}

        self.label_input = QtWidgets.QLineEdit(self.entry.get("label", ""))
        self.command_input = QtWidgets.QLineEdit(self.entry.get("command", ""))
        self.args_input = QtWidgets.QLineEdit(" ".join(self.entry.get("args", [])))
        self.cwd_input = QtWidgets.QLineEdit(self.entry.get("cwd", ""))
        self.color_input = QtWidgets.QLineEdit(self.entry.get("color", ""))
        self.text_color_input = QtWidgets.QLineEdit(self.entry.get("text_color", ""))
        self.shortcut_input = QtWidgets.QLineEdit(self.entry.get("shortcut", ""))
        self.icon_input = QtWidgets.QLineEdit(self.entry.get("icon", ""))

        form = QtWidgets.QFormLayout()
        form.addRow("Label", self.label_input)
        form.addRow(
            "Command",
            self._with_browse_pair(
                self.command_input,
                "Browse",
                self.browse_exe,
                "Folder",
                self.browse_command_folder,
            ),
        )
        form.addRow("Args", self.args_input)
        form.addRow("Shortcut", self._with_browse(self.shortcut_input, "Record", self.record_shortcut))
        form.addRow("CWD", self._with_browse(self.cwd_input, "Folder", self.browse_folder))
        form.addRow("Icon", self._with_browse(self.icon_input, "Browse", self.browse_icon))
        form.addRow("Color", self._with_browse(self.color_input, "Pick", self.pick_color))
        form.addRow(
            "Text",
            self._with_browse(self.text_color_input, "Pick", self.pick_text_color),
        )

        self.delete_btn = QtWidgets.QPushButton("Delete")
        self.delete_btn.clicked.connect(self.on_delete)
        self.delete_btn.setVisible(entry is not None)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Save
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        bottom = QtWidgets.QHBoxLayout()
        bottom.addWidget(self.delete_btn)
        bottom.addStretch(1)
        bottom.addWidget(buttons)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(bottom)

        self._deleted = False

    def _with_browse(self, line_edit, text, handler):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(line_edit, 1)
        button = QtWidgets.QPushButton(text)
        button.clicked.connect(handler)
        layout.addWidget(button)
        return container

    def _with_browse_pair(self, line_edit, text_left, handler_left, text_right, handler_right):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(line_edit, 1)
        left = QtWidgets.QPushButton(text_left)
        left.clicked.connect(handler_left)
        right = QtWidgets.QPushButton(text_right)
        right.clicked.connect(handler_right)
        layout.addWidget(left)
        layout.addWidget(right)
        return container

    def browse_exe(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select app", "", "Applications (*.exe);;All files (*.*)"
        )
        if path:
            self.command_input.setText(path)

    def browse_command_folder(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select folder")
        if path:
            self.command_input.setText(path)

    def browse_folder(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select folder")
        if path:
            self.cwd_input.setText(path)

    def on_delete(self):
        self._deleted = True
        self.accept()

    def pick_color(self):
        color = QtWidgets.QColorDialog.getColor(
            QtGui.QColor(self.color_input.text() or "#1B2230"), self, "Pick color"
        )
        if color.isValid():
            self.color_input.setText(color.name())

    def pick_text_color(self):
        color = QtWidgets.QColorDialog.getColor(
            QtGui.QColor(self.text_color_input.text() or "#F4F7FA"),
            self,
            "Pick text color",
        )
        if color.isValid():
            self.text_color_input.setText(color.name())

    def browse_icon(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select icon",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.ico);;All files (*.*)",
        )
        if path:
            self.icon_input.setText(path)

    def record_shortcut(self):
        dialog = ShortcutCaptureDialog(self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            if dialog.sequence_text:
                self.shortcut_input.setText(dialog.sequence_text)

    def result_entry(self):
        if self._deleted:
            return "DELETE"
        command = self.command_input.text().strip()
        cwd = self.cwd_input.text().strip() or None
        if not command:
            if cwd:
                command = cwd
                cwd = None
            else:
                shortcut_only = self.shortcut_input.text().strip()
                if not shortcut_only:
                    return None
                command = None
        return {
            "label": self.label_input.text().strip() or "App",
            "command": command,
            "args": parse_args(self.args_input.text()),
            "shortcut": self.shortcut_input.text().strip() or None,
            "cwd": cwd,
            "icon": self.icon_input.text().strip() or None,
            "color": self.color_input.text().strip() or None,
            "text_color": self.text_color_input.text().strip() or None,
        }


class ShortcutCaptureDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Press shortcut")
        self.setModal(True)
        self.sequence_text = ""

        label = QtWidgets.QLabel("Press the key combo now. Esc cancels.")
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(label)
        self.resize(320, 120)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_Escape:
            self.reject()
            return
        if event.key() in (
            QtCore.Qt.Key.Key_Control,
            QtCore.Qt.Key.Key_Shift,
            QtCore.Qt.Key.Key_Alt,
            QtCore.Qt.Key.Key_Meta,
        ):
            return
        combo = event.modifiers().value | int(event.key())
        sequence = QtGui.QKeySequence(combo)
        text = sequence.toString()
        if not text:
            text = QtGui.QKeySequence(int(event.key())).toString()
        if not text:
            text = event.text().strip()
        if text:
            self.sequence_text = text
            self.accept()


class TouchDeck(QtWidgets.QMainWindow):
    def __init__(self, config_path):
        super().__init__()
        self.config_path = config_path
        self.config = load_config(config_path)
        self.modes = self.config.get("modes")
        if not isinstance(self.modes, list) or not self.modes:
            default_buttons = self.config.get("buttons", [])
            default_name = self.config.get("default_mode", "Default")
            self.modes = [{"name": default_name, "buttons": default_buttons}]
        self.current_mode_index = int(self.config.get("current_mode_index", 0))
        if self.current_mode_index < 0 or self.current_mode_index >= len(self.modes):
            self.current_mode_index = 0
        self.buttons = self.current_mode().get("buttons", [])
        self.edit_mode = False
        self._press_pos = None
        self._shortcuts = []

        self.setWindowTitle(APP_TITLE)
        self.setStyleSheet(self.build_style())
        self.init_ui()

    def build_style(self):
        bg = self.config.get("background", "#0E1014")
        btn_bg = self.config.get("button_color", "#1B2230")
        btn_bg_active = self.config.get("button_active_color", "#2B364A")
        btn_fg = self.config.get("button_text_color", "#F4F7FA")
        header_bg = self.config.get("header_background", "#0B0E14")
        header_fg = self.config.get("header_text_color", "#E7EBF0")
        return f"""
            QMainWindow {{
                background: {bg};
            }}
            QWidget#Header {{
                background: {header_bg};
            }}
            QLabel#HeaderTitle {{
                color: {header_fg};
                font-weight: 700;
            }}
            QPushButton#Tile {{
                background: {btn_bg};
                color: {btn_fg};
                border-radius: 0px;
                padding: 6px;
                font-weight: 700;
            }}
            QPushButton#Tile:hover {{
                background: {btn_bg_active};
            }}
            QPushButton#EditToggle {{
                background: {btn_bg};
                color: {btn_fg};
                border-radius: 10px;
                padding: 6px 12px;
                font-weight: 700;
            }}
        """

    def init_ui(self):
        fullscreen = bool(self.config.get("fullscreen", True))
        self.is_fullscreen = fullscreen
        if fullscreen:
            self.showFullScreen()
        else:
            width = int(self.config.get("window_width", 1000))
            height = int(self.config.get("window_height", 650))
            self.setGeometry(0, 0, width, height)

        root = QtWidgets.QWidget()
        root_layout = QtWidgets.QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.header = None
        if bool(self.config.get("show_header", True)):
            self.header = self.build_header()
            root_layout.addWidget(self.header)

        self.grid_container = QtWidgets.QWidget()
        self.grid_layout = QtWidgets.QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setHorizontalSpacing(0)
        self.grid_layout.setVerticalSpacing(0)

        root_layout.addWidget(self.grid_container, 1)
        self.setCentralWidget(root)

        root.installEventFilter(self)
        self.grid_container.installEventFilter(self)
        if self.header:
            self.header.installEventFilter(self)

        self.update_mode_title()
        self.render_buttons()
        self.bind_shortcuts()

    def build_header(self):
        header = QtWidgets.QWidget()
        header.setObjectName("Header")
        layout = QtWidgets.QHBoxLayout(header)
        layout.setContentsMargins(16, 8, 16, 8)

        title = QtWidgets.QLabel(self.config.get("header_text", APP_TITLE))
        title.setObjectName("HeaderTitle")
        title_font = QtGui.QFont()
        title_font.setFamily(self.config.get("header_font", "Segoe UI").split()[0])
        title_font.setPointSize(16)
        title.setFont(title_font)
        self.header_title = title

        self.add_mode_btn = QtWidgets.QPushButton("Add Mode")
        self.add_mode_btn.setObjectName("EditToggle")
        self.add_mode_btn.setVisible(False)
        self.add_mode_btn.clicked.connect(self.add_mode)

        self.edit_btn = QtWidgets.QPushButton("Edit")
        self.edit_btn.setObjectName("EditToggle")
        self.edit_btn.clicked.connect(self.toggle_edit)

        layout.addWidget(title, 1)
        layout.addWidget(self.add_mode_btn, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.edit_btn, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        return header

    def clear_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def render_buttons(self):
        self.clear_grid()

        columns = int(self.config.get("grid_columns", self.config.get("columns", 4)))
        rows = self.config.get("grid_rows")
        rows = int(rows) if rows is not None else None
        button_w = int(self.config.get("button_width", 220))
        button_h = int(self.config.get("button_height", 130))
        font_text = self.config.get("font", "Segoe UI 18 bold")
        font = QtGui.QFont()
        font.setFamily(font_text.split()[0])
        size = [p for p in font_text.split() if p.isdigit()]
        font.setPointSize(int(size[0]) if size else 18)
        font.setBold("bold" in font_text.lower())

        self.buttons = self.current_mode().get("buttons", [])
        visible_buttons = list(self.buttons)
        if self.edit_mode:
            visible_buttons.append({"label": "+ Add", "_add": True})

        for idx, entry in enumerate(visible_buttons):
            row = idx // columns
            col = idx % columns

            btn = QtWidgets.QPushButton(entry.get("label", f"Button {idx + 1}"))
            btn.setObjectName("Tile")
            btn.setFont(font)
            btn.setMinimumSize(button_w, button_h)
            btn.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Expanding,
            )
            btn.installEventFilter(self)
            if entry.get("color") or entry.get("text_color"):
                bg_color = entry.get("color") or "transparent"
                text_color = entry.get("text_color")
                text_rule = f"color: {text_color};" if text_color else ""
                btn.setStyleSheet(
                    "QPushButton {"
                    f"background: {bg_color};"
                    f"{text_rule}"
                    "}"
                    "QPushButton:hover {"
                    f"background: {bg_color};"
                    f"{text_rule}"
                    "}"
                )
            icon_path = entry.get("icon")
            if icon_path:
                icon = QtGui.QIcon(icon_path)
                if not icon.isNull():
                    icon_size = int(
                        self.config.get(
                            "icon_size", min(button_w, button_h) * 0.4
                        )
                    )
                    btn.setIcon(icon)
                    btn.setIconSize(QtCore.QSize(icon_size, icon_size))
            if entry.get("_add"):
                btn.clicked.connect(self.add_button)
            else:
                btn.clicked.connect(lambda _, e=entry, i=idx: self.on_button(e, i))

            self.grid_layout.addWidget(btn, row, col)

        row_count = rows if rows is not None else max(1, (len(visible_buttons) + columns - 1) // columns)
        for r in range(row_count):
            self.grid_layout.setRowStretch(r, 1)
        for c in range(columns):
            self.grid_layout.setColumnStretch(c, 1)
        self.rebuild_shortcuts()

    def on_button(self, entry, index):
        if not self.edit_mode:
            open_command(entry, self)
            return

        dialog = EditDialog(self, entry=entry)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            updated = dialog.result_entry()
            if updated == "DELETE":
                del self.buttons[index]
            elif isinstance(updated, dict):
                self.buttons[index] = updated
            else:
                return
            self.persist_config()
            self.render_buttons()

    def add_button(self):
        dialog = EditDialog(self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            updated = dialog.result_entry()
            if isinstance(updated, dict):
                self.buttons.append(updated)
                self.persist_config()
                self.render_buttons()

    def toggle_edit(self):
        self.edit_mode = not self.edit_mode
        if hasattr(self, "edit_btn"):
            self.edit_btn.setText("Done" if self.edit_mode else "Edit")
        if hasattr(self, "add_mode_btn"):
            self.add_mode_btn.setVisible(self.edit_mode)
        self.render_buttons()

    def bind_shortcuts(self):
        esc = QtGui.QShortcut(QtGui.QKeySequence("Esc"), self)
        esc.activated.connect(self.exit_fullscreen)

        f11 = QtGui.QShortcut(QtGui.QKeySequence("F11"), self)
        f11.activated.connect(self.toggle_fullscreen)

        prev_seq = self.config.get("prev_mode_shortcut", "Ctrl+Left")
        if prev_seq:
            prev = QtGui.QShortcut(QtGui.QKeySequence(prev_seq), self)
            prev.setContext(QtCore.Qt.ShortcutContext.ApplicationShortcut)
            prev.activated.connect(self.prev_mode)

        next_seq = self.config.get("next_mode_shortcut", "Ctrl+Right")
        if next_seq:
            next_sc = QtGui.QShortcut(QtGui.QKeySequence(next_seq), self)
            next_sc.setContext(QtCore.Qt.ShortcutContext.ApplicationShortcut)
            next_sc.activated.connect(self.next_mode)

    def exit_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
            self.is_fullscreen = False

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
            self.is_fullscreen = False
        else:
            self.showFullScreen()
            self.is_fullscreen = True

    def current_mode(self):
        return self.modes[self.current_mode_index]

    def update_mode_title(self):
        name = self.current_mode().get("name", f"Mode {self.current_mode_index + 1}")
        header_text = self.config.get("header_text", APP_TITLE)
        title_text = f"{header_text} - {name}" if name else header_text
        if hasattr(self, "header_title"):
            self.header_title.setText(title_text)
        self.setWindowTitle(title_text)

    def rebuild_shortcuts(self):
        self._shortcuts = []
        for entry in self.buttons:
            shortcut = entry.get("shortcut")
            if not shortcut:
                continue
            sc = QtGui.QShortcut(QtGui.QKeySequence(shortcut), self)
            sc.setContext(QtCore.Qt.ShortcutContext.ApplicationShortcut)
            sc.activated.connect(lambda e=entry: self.launch_shortcut(e))
            self._shortcuts.append(sc)

    def launch_shortcut(self, entry):
        if self.edit_mode:
            return
        open_command(entry, self)

    def persist_config(self):
        self.config["modes"] = self.modes
        self.config["current_mode_index"] = self.current_mode_index
        self.config.pop("buttons", None)
        save_config(self.config_path, self.config)

    def add_mode(self):
        name, ok = QtWidgets.QInputDialog.getText(self, APP_TITLE, "Mode name")
        if not ok:
            return
        name = name.strip() or f"Mode {len(self.modes) + 1}"
        self.modes.append({"name": name, "buttons": []})
        self.current_mode_index = len(self.modes) - 1
        self.persist_config()
        self.update_mode_title()
        self.render_buttons()

    def next_mode(self):
        if len(self.modes) <= 1:
            return
        self.current_mode_index = (self.current_mode_index + 1) % len(self.modes)
        self.update_mode_title()
        self.render_buttons()

    def prev_mode(self):
        if len(self.modes) <= 1:
            return
        self.current_mode_index = (self.current_mode_index - 1) % len(self.modes)
        self.update_mode_title()
        self.render_buttons()

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.MouseButtonPress:
            self._press_pos = event.globalPosition().toPoint()
        elif event.type() == QtCore.QEvent.Type.MouseButtonRelease:
            if self._press_pos is not None:
                release_pos = event.globalPosition().toPoint()
                dx = release_pos.x() - self._press_pos.x()
                dy = release_pos.y() - self._press_pos.y()
                threshold = int(self.config.get("swipe_threshold", 80))
                max_vertical = int(self.config.get("swipe_vertical_tolerance", 60))
                if abs(dx) >= threshold and abs(dy) <= max_vertical:
                    if dx < 0:
                        self.next_mode()
                    else:
                        self.prev_mode()
                self._press_pos = None
                if abs(dx) >= threshold and abs(dy) <= max_vertical:
                    return True
        return super().eventFilter(obj, event)


def main():
    app = QtWidgets.QApplication(sys.argv)
    config_name = "touchdeck.json"
    config_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.getcwd()), APP_TITLE)
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, config_name)

    if not os.path.exists(config_path):
        bundled_base = getattr(sys, "_MEIPASS", None)
        if bundled_base:
            bundled_config = os.path.join(bundled_base, config_name)
            if os.path.exists(bundled_config):
                with open(bundled_config, "rb") as src, open(config_path, "wb") as dst:
                    dst.write(src.read())
        else:
            exe_dir = os.path.dirname(
                sys.executable if getattr(sys, "frozen", False) else __file__
            )
            fallback_config = os.path.join(exe_dir, config_name)
            if os.path.exists(fallback_config):
                with open(fallback_config, "rb") as src, open(config_path, "wb") as dst:
                    dst.write(src.read())

    window = TouchDeck(config_path)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
