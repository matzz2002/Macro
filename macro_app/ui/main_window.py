from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QAction, QColor, QCloseEvent, QIcon, QUndoStack
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QStyle,
    QSystemTrayIcon,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from macro_app.action_tools import action_label, default_action, scale_delays
from macro_app.hotkeys import GlobalHotkeyManager, HotkeyError
from macro_app.models import ActionType, AppData, AppSettings, Macro, MacroAction, Profile, RunMode
from macro_app.player import MacroPlayer, PlaybackError
from macro_app.recorder import MacroRecorder, RecorderError
from macro_app.settings_manager import set_start_with_windows
from macro_app.storage import JsonStorage, StorageError
from macro_app.ui.commands import ActionSnapshotCommand
from macro_app.ui.theme import stylesheet
from macro_app.validation import ValidationError, find_hotkey_conflicts, normalize_hotkey, validate_macro


class UiBridge(QObject):
    recorded_action = Signal(object)
    trigger_macro = Signal(object)
    release_macro = Signal(object)
    panic = Signal()
    status = Signal(str)


class MainWindow(QMainWindow):
    def __init__(self, storage: JsonStorage | None = None) -> None:
        super().__init__()
        self.storage = storage or JsonStorage()
        self.bridge = UiBridge()
        self.undo_stack = QUndoStack(self)
        self.current_macro_id = ""
        self._loading = False
        self._syncing_drag = False
        self._action_color = "#7c3aed"

        try:
            self.data = self.storage.load_data()
            self.settings = self.storage.load_settings()
        except StorageError as exc:
            QMessageBox.warning(self, "Błąd danych", str(exc))
            self.data = AppData.default()
            self.settings = AppSettings()

        self.player = MacroPlayer(status_callback=self.bridge.status.emit)
        self.recorder = MacroRecorder(action_callback=self.bridge.recorded_action.emit, status_callback=self.bridge.status.emit)
        self.hotkeys = GlobalHotkeyManager(
            on_trigger=self.bridge.trigger_macro.emit,
            on_release=self.bridge.release_macro.emit,
            on_panic=self.bridge.panic.emit,
            on_status=self.bridge.status.emit,
        )

        self._build_ui()
        self._build_tray()
        self._connect_signals()
        self.apply_theme()
        self.populate_profiles()
        self.reload_hotkeys()

    def _build_ui(self) -> None:
        self.setWindowTitle("MacroForge - Desktop Macro Studio")
        self.resize(1320, 820)
        self.setMinimumSize(1100, 680)

        toolbar = QToolBar("Główne")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        self.undo_action = self.undo_stack.createUndoAction(self, "Cofnij")
        self.redo_action = self.undo_stack.createRedoAction(self, "Ponów")
        toolbar.addAction(self.undo_action)
        toolbar.addAction(self.redo_action)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        self.theme_combo.setCurrentText(self.settings.theme)
        toolbar.addWidget(QLabel("  Motyw: "))
        toolbar.addWidget(self.theme_combo)

        self.startup_check = QCheckBox("Start z Windows")
        self.startup_check.setChecked(self.settings.start_with_windows)
        toolbar.addWidget(self.startup_check)

        self.tray_check = QCheckBox("Minimalizuj do tray'a")
        self.tray_check.setChecked(self.settings.minimize_to_tray)
        toolbar.addWidget(self.tray_check)

        self.panic_edit = QLineEdit(self.settings.panic_hotkey)
        self.panic_edit.setMaximumWidth(120)
        toolbar.addWidget(QLabel("  Panic key: "))
        toolbar.addWidget(self.panic_edit)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._left_panel())
        splitter.addWidget(self._center_panel())
        splitter.addWidget(self._right_panel())
        splitter.setSizes([280, 700, 340])
        self.setCentralWidget(splitter)

        status = QStatusBar()
        self.profile_status = QLabel("Profil: -")
        self.run_status = QLabel("Brak aktywnego makra")
        self.save_status = QLabel("Autosave")
        status.addPermanentWidget(self.profile_status)
        status.addPermanentWidget(self.run_status)
        status.addPermanentWidget(self.save_status)
        self.setStatusBar(status)

    def _left_panel(self) -> QWidget:
        frame = self._panel()
        layout = QVBoxLayout(frame)
        layout.addWidget(QLabel("Profile"))
        self.profile_list = QListWidget()
        layout.addWidget(self.profile_list, 2)

        profile_buttons = QGridLayout()
        self.add_profile_btn = QPushButton("+ Profil")
        self.rename_profile_btn = QPushButton("Zmień nazwę")
        self.duplicate_profile_btn = QPushButton("Duplikuj")
        self.delete_profile_btn = QPushButton("Usuń")
        self.import_profile_btn = QPushButton("Import")
        self.export_profile_btn = QPushButton("Eksport")
        for index, button in enumerate(
            [
                self.add_profile_btn,
                self.rename_profile_btn,
                self.duplicate_profile_btn,
                self.delete_profile_btn,
                self.import_profile_btn,
                self.export_profile_btn,
            ]
        ):
            profile_buttons.addWidget(button, index // 2, index % 2)
        layout.addLayout(profile_buttons)

        layout.addSpacing(12)
        layout.addWidget(QLabel("Makra"))
        self.macro_search = QLineEdit()
        self.macro_search.setPlaceholderText("Szukaj makra...")
        layout.addWidget(self.macro_search)
        self.macro_list = QListWidget()
        layout.addWidget(self.macro_list, 4)

        macro_buttons = QGridLayout()
        self.add_macro_btn = QPushButton("+ Nowe makro")
        self.duplicate_macro_btn = QPushButton("Duplikuj")
        self.delete_macro_btn = QPushButton("Usuń")
        self.sort_macro_btn = QPushButton("Sortuj A-Z")
        self.import_macro_btn = QPushButton("Import")
        self.export_macro_btn = QPushButton("Eksport")
        for index, button in enumerate(
            [
                self.add_macro_btn,
                self.duplicate_macro_btn,
                self.delete_macro_btn,
                self.sort_macro_btn,
                self.import_macro_btn,
                self.export_macro_btn,
            ]
        ):
            macro_buttons.addWidget(button, index // 2, index % 2)
        layout.addLayout(macro_buttons)
        return frame

    def _center_panel(self) -> QWidget:
        frame = self._panel()
        layout = QVBoxLayout(frame)

        header = QGridLayout()
        self.macro_name_edit = QLineEdit()
        self.macro_name_edit.setPlaceholderText("Nazwa makra")
        self.hotkey_edit = QLineEdit()
        self.hotkey_edit.setPlaceholderText("np. Ctrl+Shift+X, F6, Mouse Button 4")
        self.icon_edit = QLineEdit("bolt")
        self.color_btn = QPushButton("Kolor")
        self.run_mode_combo = QComboBox()
        self.run_mode_combo.addItem("Wykonaj raz", RunMode.ONCE.value)
        self.run_mode_combo.addItem("Powtórz N razy", RunMode.REPEAT_COUNT.value)
        self.run_mode_combo.addItem("Powtarzaj do skrótu", RunMode.TOGGLE.value)
        self.run_mode_combo.addItem("Powtarzaj podczas trzymania", RunMode.HOLD.value)
        self.repeat_spin = QSpinBox()
        self.repeat_spin.setRange(1, 999999)
        self.stop_on_release_check = QCheckBox("Przerwij po zwolnieniu klawisza uruchamiającego")

        header.addWidget(QLabel("Makro"), 0, 0)
        header.addWidget(self.macro_name_edit, 0, 1, 1, 3)
        header.addWidget(QLabel("Skrót"), 1, 0)
        header.addWidget(self.hotkey_edit, 1, 1)
        header.addWidget(QLabel("Ikona"), 1, 2)
        header.addWidget(self.icon_edit, 1, 3)
        header.addWidget(self.color_btn, 1, 4)
        header.addWidget(QLabel("Tryb"), 2, 0)
        header.addWidget(self.run_mode_combo, 2, 1)
        header.addWidget(QLabel("Powtórzenia"), 2, 2)
        header.addWidget(self.repeat_spin, 2, 3)
        header.addWidget(self.stop_on_release_check, 3, 1, 1, 4)
        layout.addLayout(header)

        controls = QHBoxLayout()
        self.record_btn = QPushButton("Nagrywaj")
        self.record_btn.setObjectName("PrimaryButton")
        self.play_btn = QPushButton("Odtwórz")
        self.stop_btn = QPushButton("Zatrzymaj")
        self.stop_btn.setObjectName("DangerButton")
        self.save_btn = QPushButton("Zapisz")
        self.record_moves_check = QCheckBox("Nagrywaj ruchy myszy")
        for button in [self.record_btn, self.play_btn, self.stop_btn, self.save_btn]:
            controls.addWidget(button)
        controls.addWidget(self.record_moves_check)
        controls.addStretch(1)
        layout.addLayout(controls)

        action_bar = QHBoxLayout()
        self.add_action_btn = QPushButton("+ Dodaj akcję")
        self.copy_action_btn = QPushButton("Kopiuj zaznaczone")
        self.delete_action_btn = QPushButton("Usuń")
        self.move_up_btn = QPushButton("W górę")
        self.move_down_btn = QPushButton("W dół")
        self.scale_delay_btn = QPushButton("Zmień wszystkie opóźnienia")
        for button in [
            self.add_action_btn,
            self.copy_action_btn,
            self.delete_action_btn,
            self.move_up_btn,
            self.move_down_btn,
            self.scale_delay_btn,
        ]:
            action_bar.addWidget(button)
        action_bar.addStretch(1)
        layout.addLayout(action_bar)

        self.action_list = QListWidget()
        self.action_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.action_list.setDragDropMode(QListWidget.InternalMove)
        self.action_list.setDefaultDropAction(Qt.MoveAction)
        layout.addWidget(self.action_list, 1)
        return frame

    def _right_panel(self) -> QWidget:
        frame = self._panel()
        layout = QVBoxLayout(frame)
        layout.addWidget(QLabel("Właściwości akcji"))
        form = QFormLayout()
        self.action_type_combo = QComboBox()
        for action_type in ActionType:
            self.action_type_combo.addItem(action_type.value, action_type)
        self.key_edit = QLineEdit()
        self.hotkey_keys_edit = QLineEdit()
        self.hotkey_keys_edit.setPlaceholderText("ctrl+c lub ctrl+shift+x")
        self.mouse_button_combo = QComboBox()
        self.mouse_button_combo.addItems(["left", "right", "middle", "x1", "x2"])
        self.x_spin = QSpinBox()
        self.x_spin.setRange(-100000, 100000)
        self.y_spin = QSpinBox()
        self.y_spin.setRange(-100000, 100000)
        self.clicks_spin = QSpinBox()
        self.clicks_spin.setRange(1, 100)
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(0, 600000)
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 3600000)
        self.random_delay_check = QCheckBox("Losowy zakres")
        self.random_min_spin = QSpinBox()
        self.random_min_spin.setRange(0, 3600000)
        self.random_max_spin = QSpinBox()
        self.random_max_spin.setRange(0, 3600000)
        self.loop_count_spin = QSpinBox()
        self.loop_count_spin.setRange(1, 999999)
        self.loop_body_edit = QTextEdit()
        self.loop_body_edit.setPlaceholderText('[{"type":"delay","params":{"ms":100}}]')
        self.loop_body_edit.setMaximumHeight(120)

        form.addRow("Typ", self.action_type_combo)
        form.addRow("Klawisz", self.key_edit)
        form.addRow("Kombinacja", self.hotkey_keys_edit)
        form.addRow("Przycisk myszy", self.mouse_button_combo)
        form.addRow("X", self.x_spin)
        form.addRow("Y", self.y_spin)
        form.addRow("Kliknięcia", self.clicks_spin)
        form.addRow("Czas ruchu ms", self.duration_spin)
        form.addRow("Opóźnienie ms", self.delay_spin)
        form.addRow("", self.random_delay_check)
        form.addRow("Losowo min ms", self.random_min_spin)
        form.addRow("Losowo max ms", self.random_max_spin)
        form.addRow("Powtórzenia pętli", self.loop_count_spin)
        form.addRow("Akcje pętli JSON", self.loop_body_edit)
        layout.addLayout(form)

        self.apply_action_btn = QPushButton("Zastosuj właściwości")
        self.apply_action_btn.setObjectName("PrimaryButton")
        layout.addWidget(self.apply_action_btn)
        layout.addStretch(1)
        return frame

    def _panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Panel")
        return frame

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self.style().standardIcon(QStyle.SP_ComputerIcon), self)
        self.tray.setToolTip("MacroForge")
        tray_menu = QMenu(self)
        show_action = tray_menu.addAction("Otwórz MacroForge")
        stop_action = tray_menu.addAction("Zatrzymaj wszystkie makra")
        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("Zamknij całkowicie")
        show_action.triggered.connect(self.show_from_tray)
        stop_action.triggered.connect(self.stop_all_macros)
        quit_action.triggered.connect(self.quit_app)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(lambda reason: self.show_from_tray() if reason == QSystemTrayIcon.Trigger else None)
        self.tray.show()

    def _connect_signals(self) -> None:
        self.bridge.recorded_action.connect(self.on_recorded_action)
        self.bridge.trigger_macro.connect(self.play_macro)
        self.bridge.release_macro.connect(lambda macro: self.player.stop(macro.id))
        self.bridge.panic.connect(self.stop_all_macros)
        self.bridge.status.connect(self.set_status)
        self.profile_list.currentItemChanged.connect(lambda _current, _previous: self.on_profile_selected())
        self.macro_list.currentItemChanged.connect(lambda _current, _previous: self.on_macro_selected())
        self.macro_search.textChanged.connect(self.populate_macros)
        self.add_profile_btn.clicked.connect(self.add_profile)
        self.rename_profile_btn.clicked.connect(self.rename_profile)
        self.duplicate_profile_btn.clicked.connect(self.duplicate_profile)
        self.delete_profile_btn.clicked.connect(self.delete_profile)
        self.import_profile_btn.clicked.connect(self.import_profile)
        self.export_profile_btn.clicked.connect(self.export_profile)
        self.add_macro_btn.clicked.connect(self.add_macro)
        self.duplicate_macro_btn.clicked.connect(self.duplicate_macro)
        self.delete_macro_btn.clicked.connect(self.delete_macro)
        self.sort_macro_btn.clicked.connect(self.sort_macros)
        self.import_macro_btn.clicked.connect(self.import_macro)
        self.export_macro_btn.clicked.connect(self.export_macro)
        self.save_btn.clicked.connect(self.save_current_macro)
        self.play_btn.clicked.connect(lambda: self.play_macro(self.current_macro()))
        self.stop_btn.clicked.connect(self.stop_all_macros)
        self.record_btn.clicked.connect(self.toggle_recording)
        self.color_btn.clicked.connect(self.pick_color)
        self.add_action_btn.clicked.connect(self.add_action)
        self.copy_action_btn.clicked.connect(self.copy_actions)
        self.delete_action_btn.clicked.connect(self.delete_actions)
        self.move_up_btn.clicked.connect(lambda: self.move_selected_actions(-1))
        self.move_down_btn.clicked.connect(lambda: self.move_selected_actions(1))
        self.scale_delay_btn.clicked.connect(self.scale_all_delays)
        self.apply_action_btn.clicked.connect(self.apply_action_properties)
        self.action_list.currentItemChanged.connect(lambda _current, _previous: self.load_selected_action_properties())
        self.action_list.model().rowsMoved.connect(lambda *_args: QTimer.singleShot(0, self.sync_actions_after_drag))
        self.theme_combo.currentTextChanged.connect(self.on_settings_changed)
        self.startup_check.toggled.connect(self.on_settings_changed)
        self.tray_check.toggled.connect(self.on_settings_changed)
        self.panic_edit.editingFinished.connect(self.on_settings_changed)

    def populate_profiles(self) -> None:
        self._loading = True
        self.profile_list.clear()
        for profile in self.data.profiles:
            item = QListWidgetItem(profile.name)
            item.setData(Qt.UserRole, profile.id)
            self.profile_list.addItem(item)
            if profile.id == self.data.active_profile_id:
                self.profile_list.setCurrentItem(item)
        self._loading = False
        self.populate_macros()

    def populate_macros(self) -> None:
        profile = self.active_profile()
        query = self.macro_search.text().strip().lower() if hasattr(self, "macro_search") else ""
        selected_id = self.current_macro_id
        self._loading = True
        self.macro_list.clear()
        for macro in profile.macros:
            if query and query not in macro.name.lower():
                continue
            item = QListWidgetItem(f"{macro.name}  [{macro.hotkey or 'brak skrótu'}]")
            item.setData(Qt.UserRole, macro.id)
            item.setForeground(QColor(macro.color))
            self.macro_list.addItem(item)
            if macro.id == selected_id:
                self.macro_list.setCurrentItem(item)
        if self.macro_list.currentItem() is None and self.macro_list.count():
            self.macro_list.setCurrentRow(0)
        self._loading = False
        self.on_macro_selected()

    def on_profile_selected(self) -> None:
        if self._loading:
            return
        item = self.profile_list.currentItem()
        if item is None:
            return
        self.data.active_profile_id = item.data(Qt.UserRole)
        self.current_macro_id = ""
        self.profile_status.setText(f"Profil: {self.active_profile().name}")
        self.populate_macros()
        self.save_all()
        self.reload_hotkeys()

    def on_macro_selected(self) -> None:
        if self._loading:
            return
        item = self.macro_list.currentItem()
        if item is None:
            self.current_macro_id = ""
            self.clear_macro_form()
            return
        self.current_macro_id = item.data(Qt.UserRole)
        self.load_macro_form()

    def load_macro_form(self) -> None:
        macro = self.current_macro()
        if macro is None:
            return
        self._loading = True
        self.macro_name_edit.setText(macro.name)
        self.hotkey_edit.setText(macro.hotkey)
        self.icon_edit.setText(macro.icon)
        self._action_color = macro.color
        self.run_mode_combo.setCurrentIndex(max(0, self.run_mode_combo.findData(macro.run_mode.value)))
        self.repeat_spin.setValue(macro.repeat_count)
        self.stop_on_release_check.setChecked(macro.stop_on_hotkey_release)
        self.refresh_action_list()
        self.undo_stack.clear()
        self._loading = False

    def clear_macro_form(self) -> None:
        self.macro_name_edit.clear()
        self.hotkey_edit.clear()
        self.icon_edit.clear()
        self.action_list.clear()

    def refresh_action_list(self) -> None:
        self._syncing_drag = True
        selected_ids = {item.data(Qt.UserRole) for item in self.action_list.selectedItems()}
        self.action_list.clear()
        macro = self.current_macro()
        if macro:
            for index, action in enumerate(macro.actions, start=1):
                item = QListWidgetItem(f"{index}. {action_label(action)}")
                item.setData(Qt.UserRole, action.id)
                self.action_list.addItem(item)
                if action.id in selected_ids:
                    item.setSelected(True)
        self._syncing_drag = False

    def active_profile(self) -> Profile:
        return self.data.active_profile()

    def current_macro(self) -> Macro | None:
        profile = self.active_profile()
        for macro in profile.macros:
            if macro.id == self.current_macro_id:
                return macro
        return profile.macros[0] if profile.macros else None

    def add_profile(self) -> None:
        profile = Profile(name=self.unique_profile_name("Nowy profil"))
        self.data.profiles.append(profile)
        self.data.active_profile_id = profile.id
        self.populate_profiles()
        self.save_all()

    def rename_profile(self) -> None:
        profile = self.active_profile()
        name, ok = self.ask_text("Zmień nazwę profilu", "Nazwa profilu:", profile.name)
        if ok and name.strip():
            profile.name = name.strip()
            self.populate_profiles()
            self.save_all()

    def duplicate_profile(self) -> None:
        clone = self.active_profile().clone(self.unique_profile_name(f"{self.active_profile().name} kopia"))
        self.data.profiles.append(clone)
        self.data.active_profile_id = clone.id
        self.populate_profiles()
        self.save_all()

    def delete_profile(self) -> None:
        if len(self.data.profiles) <= 1:
            QMessageBox.information(self, "Profile", "Musi istnieć co najmniej jeden profil.")
            return
        profile = self.active_profile()
        if QMessageBox.question(self, "Usuń profil", f"Usunąć profil '{profile.name}'?") != QMessageBox.Yes:
            return
        self.data.profiles = [item for item in self.data.profiles if item.id != profile.id]
        self.data.active_profile_id = self.data.profiles[0].id
        self.populate_profiles()
        self.save_all()
        self.reload_hotkeys()

    def import_profile(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import profilu", "", "JSON (*.json)")
        if not path:
            return
        try:
            profile = self.storage.import_profile(Path(path))
            profile.name = self.unique_profile_name(profile.name)
            self.data.profiles.append(profile)
            self.data.active_profile_id = profile.id
            self.populate_profiles()
            self.save_all()
            self.reload_hotkeys()
        except StorageError as exc:
            QMessageBox.warning(self, "Import", str(exc))

    def export_profile(self) -> None:
        profile = self.active_profile()
        path, _ = QFileDialog.getSaveFileName(self, "Eksport profilu", f"{profile.name}.json", "JSON (*.json)")
        if path:
            self.storage.export_profile(profile, Path(path))

    def add_macro(self) -> None:
        macro = Macro(name=self.unique_macro_name("Nowe makro"))
        self.active_profile().macros.append(macro)
        self.current_macro_id = macro.id
        self.populate_macros()
        self.save_all()
        self.reload_hotkeys()

    def duplicate_macro(self) -> None:
        macro = self.current_macro()
        if macro is None:
            return
        clone = macro.clone(self.unique_macro_name(f"{macro.name} kopia"))
        self.active_profile().macros.append(clone)
        self.current_macro_id = clone.id
        self.populate_macros()
        self.save_all()
        self.reload_hotkeys()

    def delete_macro(self) -> None:
        macro = self.current_macro()
        if macro is None:
            return
        if QMessageBox.question(self, "Usuń makro", f"Usunąć makro '{macro.name}'?") != QMessageBox.Yes:
            return
        profile = self.active_profile()
        profile.macros = [item for item in profile.macros if item.id != macro.id]
        self.current_macro_id = profile.macros[0].id if profile.macros else ""
        self.populate_macros()
        self.save_all()
        self.reload_hotkeys()

    def sort_macros(self) -> None:
        self.active_profile().macros.sort(key=lambda macro: macro.name.lower())
        self.populate_macros()
        self.save_all()

    def import_macro(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import makra", "", "JSON (*.json)")
        if not path:
            return
        try:
            macro = self.storage.import_macro(Path(path))
            macro.name = self.unique_macro_name(macro.name)
            self.active_profile().macros.append(macro)
            self.current_macro_id = macro.id
            self.populate_macros()
            self.save_all()
            self.reload_hotkeys()
        except StorageError as exc:
            QMessageBox.warning(self, "Import", str(exc))

    def export_macro(self) -> None:
        macro = self.current_macro()
        if macro is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Eksport makra", f"{macro.name}.json", "JSON (*.json)")
        if path:
            self.storage.export_macro(macro, Path(path))

    def save_current_macro(self) -> None:
        macro = self.current_macro()
        if macro is None:
            return
        macro.name = self.macro_name_edit.text().strip() or "Nowe makro"
        macro.icon = self.icon_edit.text().strip() or "bolt"
        macro.color = self._action_color
        macro.hotkey = self.hotkey_edit.text().strip()
        if macro.hotkey:
            try:
                macro.hotkey = normalize_hotkey(macro.hotkey)
                self.hotkey_edit.setText(macro.hotkey)
            except ValidationError as exc:
                QMessageBox.warning(self, "Nieprawidłowy skrót", str(exc))
        macro.run_mode = RunMode(self.run_mode_combo.currentData())
        macro.repeat_count = self.repeat_spin.value()
        macro.stop_on_hotkey_release = self.stop_on_release_check.isChecked()
        errors = validate_macro(macro)
        if errors:
            QMessageBox.warning(self, "Walidacja makra", "\n".join(errors))
        conflicts = find_hotkey_conflicts(self.active_profile(), self.settings.panic_hotkey)
        if macro.id in conflicts:
            QMessageBox.warning(self, "Konflikt skrótu", "\n".join(conflicts[macro.id]))
        self.populate_macros()
        self.save_all()
        self.reload_hotkeys()

    def pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._action_color), self, "Kolor makra")
        if color.isValid():
            self._action_color = color.name()
            self.color_btn.setStyleSheet(f"background: {self._action_color};")
            self.save_current_macro()

    def add_action(self) -> None:
        macro = self.current_macro()
        if macro is None:
            return
        before = [action.clone() for action in macro.actions]
        action_type = self.action_type_combo.currentData()
        after = [action.clone() for action in macro.actions]
        after.append(default_action(action_type))
        self.push_action_change("Dodaj akcję", before, after)

    def copy_actions(self) -> None:
        macro = self.current_macro()
        indices = self.selected_action_indices()
        if macro is None or not indices:
            return
        before = [action.clone() for action in macro.actions]
        after = [action.clone() for action in macro.actions]
        insert_at = max(indices) + 1
        copies = [macro.actions[index].clone() for index in indices]
        after[insert_at:insert_at] = copies
        self.push_action_change("Kopiuj akcje", before, after)

    def delete_actions(self) -> None:
        macro = self.current_macro()
        indices = set(self.selected_action_indices())
        if macro is None or not indices:
            return
        before = [action.clone() for action in macro.actions]
        after = [action.clone() for index, action in enumerate(macro.actions) if index not in indices]
        self.push_action_change("Usuń akcje", before, after)

    def move_selected_actions(self, direction: int) -> None:
        macro = self.current_macro()
        indices = self.selected_action_indices()
        if macro is None or not indices:
            return
        actions = [action.clone() for action in macro.actions]
        if direction < 0:
            for index in indices:
                if index > 0:
                    actions[index - 1], actions[index] = actions[index], actions[index - 1]
        else:
            for index in reversed(indices):
                if index < len(actions) - 1:
                    actions[index + 1], actions[index] = actions[index], actions[index + 1]
        self.push_action_change("Przenieś akcje", macro.actions, actions)

    def scale_all_delays(self) -> None:
        macro = self.current_macro()
        if macro is None:
            return
        percent, ok = self.ask_int("Zmień wszystkie opóźnienia", "Procent aktualnego czasu:", 100, 0, 10000)
        if ok:
            self.push_action_change("Zmień opóźnienia", macro.actions, scale_delays(macro.actions, percent))

    def apply_action_properties(self) -> None:
        macro = self.current_macro()
        indices = self.selected_action_indices()
        if macro is None or not indices:
            return
        try:
            action = self.action_from_properties()
        except ValueError as exc:
            QMessageBox.warning(self, "Właściwości akcji", str(exc))
            return
        before = [item.clone() for item in macro.actions]
        after = [item.clone() for item in macro.actions]
        action.id = after[indices[0]].id
        after[indices[0]] = action
        self.push_action_change("Zmień akcję", before, after)

    def load_selected_action_properties(self) -> None:
        macro = self.current_macro()
        indices = self.selected_action_indices()
        if macro is None or not indices:
            return
        action = macro.actions[indices[0]]
        params = action.params
        self.action_type_combo.setCurrentIndex(max(0, self.action_type_combo.findData(action.type)))
        self.key_edit.setText(str(params.get("key", "")))
        self.hotkey_keys_edit.setText("+".join(str(key) for key in params.get("keys", [])))
        self.mouse_button_combo.setCurrentText(str(params.get("button", "left")))
        self.x_spin.setValue(int(params.get("x", 0)))
        self.y_spin.setValue(int(params.get("y", 0)))
        self.clicks_spin.setValue(int(params.get("clicks", 1)))
        self.duration_spin.setValue(int(params.get("duration_ms", 0)))
        self.delay_spin.setValue(int(params.get("ms", 100)))
        self.random_delay_check.setChecked("random_min_ms" in params and "random_max_ms" in params)
        self.random_min_spin.setValue(int(params.get("random_min_ms", 80)))
        self.random_max_spin.setValue(int(params.get("random_max_ms", 120)))
        self.loop_count_spin.setValue(int(params.get("count", 2)))
        self.loop_body_edit.setPlainText(json.dumps(params.get("actions", []), ensure_ascii=False, indent=2))

    def action_from_properties(self) -> MacroAction:
        action_type = self.action_type_combo.currentData()
        if action_type in {ActionType.KEY_DOWN, ActionType.KEY_UP, ActionType.KEY_PRESS}:
            return MacroAction(action_type, {"key": self.key_edit.text().strip() or "enter"})
        if action_type == ActionType.HOTKEY:
            parts = [part.strip() for part in self.hotkey_keys_edit.text().replace(",", "+").split("+") if part.strip()]
            if not parts:
                raise ValueError("Kombinacja musi mieć co najmniej jeden klawisz.")
            return MacroAction(action_type, {"keys": parts})
        if action_type == ActionType.MOUSE_CLICK:
            params = {"button": self.mouse_button_combo.currentText(), "clicks": self.clicks_spin.value()}
            if self.x_spin.value() or self.y_spin.value():
                params["x"] = self.x_spin.value()
                params["y"] = self.y_spin.value()
            return MacroAction(action_type, params)
        if action_type == ActionType.MOUSE_MOVE:
            return MacroAction(
                action_type,
                {"x": self.x_spin.value(), "y": self.y_spin.value(), "duration_ms": self.duration_spin.value()},
            )
        if action_type == ActionType.DELAY:
            params = {"ms": self.delay_spin.value()}
            if self.random_delay_check.isChecked():
                if self.random_max_spin.value() < self.random_min_spin.value():
                    raise ValueError("Maksymalny losowy delay musi być >= minimalnego.")
                params["random_min_ms"] = self.random_min_spin.value()
                params["random_max_ms"] = self.random_max_spin.value()
            return MacroAction(action_type, params)
        if action_type == ActionType.LOOP:
            try:
                actions = json.loads(self.loop_body_edit.toPlainText() or "[]")
            except json.JSONDecodeError as exc:
                raise ValueError(f"Nieprawidłowy JSON akcji pętli: {exc}") from exc
            return MacroAction(action_type, {"count": self.loop_count_spin.value(), "actions": actions})
        raise ValueError("Nieobsługiwany typ akcji.")

    def selected_action_indices(self) -> list[int]:
        return sorted(self.action_list.row(item) for item in self.action_list.selectedItems())

    def sync_actions_after_drag(self) -> None:
        if self._syncing_drag:
            return
        macro = self.current_macro()
        if macro is None:
            return
        order = [self.action_list.item(row).data(Qt.UserRole) for row in range(self.action_list.count())]
        if order == [action.id for action in macro.actions]:
            return
        by_id = {action.id: action.clone() for action in macro.actions}
        after = [by_id[action_id] for action_id in order if action_id in by_id]
        self.push_action_change("Przeciągnij akcje", macro.actions, after)

    def push_action_change(self, label: str, before: list[MacroAction], after: list[MacroAction]) -> None:
        self.undo_stack.push(ActionSnapshotCommand(label, self.set_actions, before, after))

    def set_actions(self, actions: list[MacroAction]) -> None:
        macro = self.current_macro()
        if macro is None:
            return
        macro.actions = [action.clone() for action in actions]
        self.refresh_action_list()
        self.save_all()

    def toggle_recording(self) -> None:
        macro = self.current_macro()
        if macro is None:
            return
        if self.recorder.is_recording():
            self.recorder.stop()
            self.record_btn.setText("Nagrywaj")
            self.save_all()
            return
        if macro.actions and QMessageBox.question(
            self,
            "Nagrywanie",
            "Rozpoczęcie nagrywania wyczyści aktualną listę akcji. Kontynuować?",
        ) != QMessageBox.Yes:
            return
        self.set_actions([])
        try:
            self.recorder.start(
                record_mouse_moves=self.record_moves_check.isChecked(),
                mouse_move_interval_ms=self.settings.mouse_move_interval_ms,
            )
            self.record_btn.setText("Zatrzymaj nagrywanie")
        except RecorderError as exc:
            QMessageBox.warning(self, "Nagrywanie", str(exc))

    def on_recorded_action(self, action: MacroAction) -> None:
        macro = self.current_macro()
        if macro is None:
            return
        macro.actions.append(action)
        self.refresh_action_list()
        self.save_all()

    def play_macro(self, macro: Macro | None) -> None:
        if macro is None:
            return
        self.save_current_macro()
        try:
            self.player.play(macro)
        except PlaybackError as exc:
            QMessageBox.warning(self, "Odtwarzanie", str(exc))

    def stop_all_macros(self) -> None:
        if self.recorder.is_recording():
            self.recorder.stop()
            self.record_btn.setText("Nagrywaj")
        self.player.stop_all()
        self.set_status("Brak aktywnego makra")

    def set_status(self, message: str) -> None:
        self.statusBar().showMessage(message, 5000)
        if any(word in message for word in ["aktywne", "Nagrywanie"]):
            self.run_status.setText(message)
        elif "zatrzymane" in message or "Brak" in message:
            self.run_status.setText(message)

    def save_all(self) -> None:
        if self._loading or not self.settings.autosave:
            return
        try:
            self.storage.save_data(self.data)
            self.storage.save_settings(self.settings)
            self.save_status.setText("Zapisano")
        except StorageError as exc:
            self.save_status.setText("Błąd zapisu")
            QMessageBox.warning(self, "Zapis", str(exc))

    def reload_hotkeys(self) -> None:
        try:
            self.hotkeys.set_panic_hotkey(self.settings.panic_hotkey)
            errors = self.hotkeys.register_macros(self.active_profile().macros)
            self.hotkeys.start()
            if errors:
                self.set_status("Konflikty skrótów: " + "; ".join(errors))
        except (HotkeyError, ValidationError) as exc:
            self.set_status(str(exc))

    def on_settings_changed(self) -> None:
        self.settings.theme = self.theme_combo.currentText()
        self.settings.minimize_to_tray = self.tray_check.isChecked()
        self.settings.start_with_windows = self.startup_check.isChecked()
        self.settings.panic_hotkey = self.panic_edit.text().strip() or "F12"
        try:
            normalize_hotkey(self.settings.panic_hotkey)
            set_start_with_windows(self.settings.start_with_windows)
            self.apply_theme()
            self.save_all()
            self.reload_hotkeys()
        except ValidationError as exc:
            QMessageBox.warning(self, "Panic key", str(exc))

    def apply_theme(self) -> None:
        QApplication.instance().setStyleSheet(stylesheet(self.settings.theme))

    def show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit_app(self) -> None:
        self.settings.minimize_to_tray = False
        self.stop_all_macros()
        self.hotkeys.stop()
        QApplication.instance().quit()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.settings.minimize_to_tray and self.tray.isVisible():
            event.ignore()
            self.hide()
            self.tray.showMessage("MacroForge", "Aplikacja działa w tle. Użyj menu tray, aby zamknąć całkowicie.")
        else:
            self.stop_all_macros()
            self.hotkeys.stop()
            event.accept()

    def ask_text(self, title: str, label: str, value: str) -> tuple[str, bool]:
        from PySide6.QtWidgets import QInputDialog

        return QInputDialog.getText(self, title, label, text=value)

    def ask_int(self, title: str, label: str, value: int, minimum: int, maximum: int) -> tuple[int, bool]:
        from PySide6.QtWidgets import QInputDialog

        return QInputDialog.getInt(self, title, label, value, minimum, maximum)

    def unique_profile_name(self, base: str) -> str:
        existing = {profile.name for profile in self.data.profiles}
        return unique_name(base, existing)

    def unique_macro_name(self, base: str) -> str:
        existing = {macro.name for macro in self.active_profile().macros}
        return unique_name(base, existing)


def unique_name(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    counter = 2
    while f"{base} {counter}" in existing:
        counter += 1
    return f"{base} {counter}"
