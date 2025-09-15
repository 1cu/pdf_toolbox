"""Main Qt window for the GUI (GUI-only)."""

from __future__ import annotations

import html
import inspect
import sys
import types
from importlib import metadata
from typing import Any, Literal, Union, get_args, get_origin

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pdf_toolbox.actions import Action
from pdf_toolbox.config import CONFIG_PATH, load_config, save_config
from pdf_toolbox.gui.widgets import ClickableLabel, FileEdit, QtLogHandler
from pdf_toolbox.gui.worker import Worker
from pdf_toolbox.i18n import label as tr_label
from pdf_toolbox.i18n import set_language, tr
from pdf_toolbox.renderers.pptx import get_pptx_renderer
from pdf_toolbox.utils import _load_author_info, configure_logging

RESULT_PAIR_LEN = 2


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:  # noqa: PLR0915  # pdf-toolbox: constructor sets up many widgets | issue:-
        """Initialize the main window and construct widgets."""
        super().__init__()
        self.setWindowTitle("PDF Toolbox")
        self.cfg = load_config()
        # initialize language from config
        lang = self.cfg.get("language", "system")
        set_language(None if lang == "system" else lang)
        self.current_action: Action | None = None
        self.current_widgets: dict[str, Any] = {}
        self.field_rows: dict[str, QWidget] = {}
        self.profile_help_label: QLabel | None = None
        self.profile_combo: QComboBox | None = None
        self.profile_sensitive_fields = {"image_format", "dpi", "quality"}
        self.worker: Worker | None = None
        self.resize(900, 480)
        self.base_height = self.height()

        central = QWidget()
        layout = QVBoxLayout(central)
        top_bar = QHBoxLayout()
        layout.addLayout(top_bar)
        splitter = QSplitter()
        layout.addWidget(splitter)
        bottom = QHBoxLayout()
        layout.addLayout(bottom)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setVisible(False)
        self.log.setMaximumBlockCount(10)
        self.log.setFixedHeight(self.log.fontMetrics().height() * 10 + 10)
        layout.addWidget(self.log)
        self.status_key = "ready"
        self.log_handler = QtLogHandler(
            self.log, lambda: self.update_status(tr(self.status_key), self.status_key)
        )
        configure_logging(self.cfg.get("log_level", "INFO"), self.log_handler)
        self.setCentralWidget(central)

        self.lbl_actions = QLabel(tr("actions"))
        self.info_btn = QPushButton("i")
        self.info_btn.setFixedWidth(24)
        self.info_btn.setEnabled(False)
        top_bar.addWidget(self.lbl_actions)
        top_bar.addWidget(self.info_btn)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumWidth(200)
        left_layout.addWidget(self.tree)
        splitter.addWidget(left)
        self.tree.setColumnWidth(0, 200)

        self.form_widget = QWidget()
        self.form_layout = QFormLayout(self.form_widget)
        self.form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)  # type: ignore[attr-defined]  # pdf-toolbox: PySide6 stubs miss form layout policy enum | issue:-
        splitter.addWidget(self.form_widget)
        splitter.setSizes([250, 650])

        self.run_btn = QPushButton(tr("start"))
        self.progress = QProgressBar()
        self.status = ClickableLabel("")
        bottom.addWidget(self.status)
        bottom.addWidget(self.progress, 1)
        bottom.addWidget(self.run_btn)
        self.update_status(tr("ready"), "ready")

        self.settings_btn = QToolButton()
        self.settings_btn.setText("⚙")
        settings_menu = QMenu(self)
        self.action_author = settings_menu.addAction(tr("author"), self.on_author)
        self.action_log_level = settings_menu.addAction(
            tr("log_level"), self.on_log_level
        )
        self.action_language = settings_menu.addAction(tr("language"), self.on_language)
        self.action_renderer = settings_menu.addAction(
            "PPTX Renderer", self.on_pptx_renderer
        )
        cfg_menu = settings_menu.addMenu(tr("settings_file"))
        cfg_menu.addAction(
            tr("open_folder"),
            lambda: QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(CONFIG_PATH.parent))
            ),
        )
        cfg_menu.addAction(
            tr("copy_path"), lambda: QApplication.clipboard().setText(str(CONFIG_PATH))
        )
        self.action_about = settings_menu.addAction(tr("about"), self.on_about)
        self.settings_menu = settings_menu
        self.settings_btn.setMenu(settings_menu)
        self.settings_btn.setPopupMode(QToolButton.InstantPopup)  # type: ignore[attr-defined]  # pdf-toolbox: PySide6 stubs miss tool button enum | issue:-
        top_bar.addStretch()
        top_bar.addWidget(self.settings_btn)

        self.info_btn.clicked.connect(self.on_info)
        self.run_btn.clicked.connect(self.on_run)
        self.status.clicked.connect(self.toggle_log)
        self.tree.itemClicked.connect(self.on_item_clicked)

        self._populate_actions()
        self.check_author()
        self.show()

    def update_status(self, text: str, key: str | None = None) -> None:
        """Update the status bar text and optional status key."""
        self.status_key = key or text
        arrow = "▼" if self.log.isVisible() else "▶"
        self.status.setText(f"{text} {arrow}")

    def _populate_actions(self) -> None:
        """Fill the action tree with all available actions."""
        cats: dict[str, QTreeWidgetItem] = {}
        gui_pkg = sys.modules[__package__]
        for act in gui_pkg.list_actions():
            cat_name = act.category or "General"
            cat_item = cats.get(cat_name)
            if cat_item is None:
                cat_item = QTreeWidgetItem([cat_name])
                self.tree.addTopLevelItem(cat_item)
                cats[cat_name] = cat_item
            item = QTreeWidgetItem([act.name])
            item.setData(0, Qt.UserRole, act)  # type: ignore[attr-defined]  # pdf-toolbox: PySide6 stubs miss Qt.UserRole | issue:-
            cat_item.addChild(item)
        self.tree.expandAll()

    def on_item_clicked(
        self, item: QTreeWidgetItem
    ) -> None:  # pragma: no cover  # pdf-toolbox: GUI handler | issue:-
        """Respond to tree item clicks by showing the action form."""
        act = item.data(0, Qt.UserRole)  # type: ignore[attr-defined]  # pdf-toolbox: PySide6 stubs miss Qt.UserRole | issue:-
        if act:
            self.current_action = act
            self.build_form(act)
            self.info_btn.setEnabled(bool(getattr(act, "help", "")))

    def build_form(self, action: Action) -> None:  # noqa: PLR0912, PLR0915  # pdf-toolbox: dynamic form builder is inherently complex | issue:-
        """Create input widgets for the given action parameters."""
        while self.form_layout.rowCount():
            self.form_layout.removeRow(0)
        self.current_widgets.clear()
        self.field_rows = {}
        self.profile_help_label = None
        self.profile_combo = None
        profile_initial_value: str | None = None

        for param in action.params:
            if param.name in {"cancel", "progress_callback"}:
                continue
            widget: (
                QWidget
                | tuple[QComboBox, QSpinBox]
                | QLineEdit
                | QCheckBox
                | QDoubleSpinBox
            )
            ann = param.annotation
            lower = param.name.lower()

            if param.name == "export_profile":
                combo_box = QComboBox()
                combo_box.addItem(
                    tr("gui.export.profile.standard"),
                    userData="standard",
                )
                combo_box.addItem(
                    tr("gui.export.profile.miro"),
                    userData="miro",
                )
                saved = self.cfg.get("last_export_profile", "standard")
                if saved not in {"standard", "miro"}:
                    saved = "standard"
                index = combo_box.findData(saved)
                combo_box.setCurrentIndex(max(index, 0))
                combo_box.currentIndexChanged.connect(
                    lambda _idx, combo=combo_box: self._apply_profile_ui(
                        combo.currentData() or combo.currentText()
                    )
                )
                help_label = QLabel(tr("gui.export.profile.miro.help"))
                help_label.setWordWrap(True)
                help_label.setVisible(False)
                self.form_layout.addRow(tr("gui.export.profile.label"), combo_box)
                self.form_layout.addRow("", help_label)
                self.current_widgets[param.name] = combo_box
                self.profile_help_label = help_label
                self.profile_combo = combo_box
                self._remember_field(param.name, combo_box)
                profile_initial_value = combo_box.currentData() or combo_box.currentText()
                continue

            if get_origin(ann) in (types.UnionType, Union) and int in get_args(ann):  # type: ignore[attr-defined]  # pdf-toolbox: `types.UnionType` absent from stubs | issue:-
                literal = next(
                    (
                        arg
                        for arg in get_args(ann)
                        if getattr(arg, "__origin__", None) is Literal
                    ),
                    None,
                )
                if literal:
                    combo_box = QComboBox()
                    spin_box = QSpinBox()
                    spin_box.setMinimum(0)
                    spin_box.setMaximum(10_000)
                    choices = list(get_args(literal))
                    combo_box.addItems([*choices, "Custom"])
                    if isinstance(param.default, str) and param.default in choices:
                        combo_box.setCurrentText(param.default)
                        spin_box.setVisible(False)
                    elif isinstance(param.default, int):
                        combo_box.setCurrentText("Custom")
                        spin_box.setValue(param.default)
                        spin_box.setVisible(True)
                    else:
                        spin_box.setVisible(combo_box.currentText() == "Custom")
                    combo_box.currentTextChanged.connect(
                        lambda text_value, sb=spin_box: sb.setVisible(
                            text_value == "Custom"
                        )
                    )
                    widget = (combo_box, spin_box)
                else:
                    spin_box = QSpinBox()
                    spin_box.setMinimum(0)
                    spin_box.setMaximum(10_000)
                    if isinstance(param.default, int):
                        spin_box.setValue(param.default)
                    widget = spin_box
            elif getattr(ann, "__origin__", None) is Literal:
                combo_box = QComboBox()
                choices = list(get_args(ann))
                combo_box.addItems(choices)
                if isinstance(param.default, str) and param.default in choices:
                    combo_box.setCurrentText(param.default)
                widget = combo_box
            elif lower in {
                "input_pdf",
                "input_pptx",
                "input_path",
                "pptx_path",
                "path",
            }:
                widget = FileEdit(self.cfg)
            elif lower in {"out_dir", "output_dir"}:
                widget = FileEdit(self.cfg, directory=True)
            elif lower in {"paths", "files"}:
                widget = FileEdit(self.cfg, multi=True)
            elif lower in {"max_size_mb"}:
                double_spin = QDoubleSpinBox()
                double_spin.setMinimum(0)
                double_spin.setMaximum(10_000)
                widget = double_spin
            elif lower in {"split_pages", "pages_per_file"}:
                spin_box = QSpinBox()
                spin_box.setMinimum(1)
                spin_box.setMaximum(9999)
                spin_box.setValue(int(self.cfg.get("split_pages", 1)))
                widget = spin_box
            elif isinstance(param.default, bool):
                check_box = QCheckBox()
                check_box.setChecked(bool(param.default))
                widget = check_box
            else:
                widget = QLineEdit()

            # Wrap composite/file widgets in a container with a button/row
            field_widget: QWidget
            if isinstance(widget, tuple):
                combo_box, spin_box = widget
                container = QWidget()
                layout = QHBoxLayout(container)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.addWidget(combo_box)
                layout.addWidget(spin_box)
                layout.setStretch(0, 1)
                self.form_layout.addRow(self._pretty_label(param.name), container)
                field_widget = container
            elif isinstance(widget, FileEdit):
                container = QWidget()
                layout = QHBoxLayout(container)
                layout.setContentsMargins(0, 0, 0, 0)
                widget.setMinimumWidth(400)
                layout.addWidget(widget)
                btn = QPushButton("...")
                btn.clicked.connect(widget.browse)
                layout.addWidget(btn)
                layout.setStretch(0, 1)
                self.form_layout.addRow(self._pretty_label(param.name), container)
                field_widget = container
            else:
                self.form_layout.addRow(self._pretty_label(param.name), widget)  # type: ignore[arg-type]  # pdf-toolbox: PySide6 stubs reject tuple variant | issue:-
                field_widget = widget  # type: ignore[assignment]  # pdf-toolbox: tuple already handled | issue:-
            self.current_widgets[param.name] = widget
            self._remember_field(param.name, field_widget)

        if profile_initial_value:
            self._apply_profile_ui(profile_initial_value, persist=False)

    def collect_args(self) -> dict[str, Any]:  # noqa: PLR0912  # pdf-toolbox: argument collection involves many branches | issue:-
        """Gather user input from the form into keyword arguments."""
        if not self.current_action:
            return {}
        params = {param.name: param for param in self.current_action.params}
        kwargs: dict[str, Any] = {}
        for name, widget in self.current_widgets.items():
            param = params.get(name)
            optional = False
            if param is not None:
                optional = param.default is not inspect._empty
                if not optional:
                    origin = get_origin(param.annotation)
                    if origin in (types.UnionType, Any.__class__) and type(
                        None
                    ) in get_args(param.annotation):  # type: ignore[attr-defined]  # pdf-toolbox: PySide6 stubs miss Qt enum | issue:-
                        optional = True

            if isinstance(widget, tuple):
                combo_box, spin_box = widget
                value = combo_box.currentText()
                kwargs[name] = int(spin_box.value()) if value == "Custom" else value
            elif isinstance(widget, FileEdit):
                text = widget.text().strip()
                if widget.multi:
                    paths = [file_path for file_path in text.split(";") if file_path]
                    if not paths and not optional:
                        raise ValueError(
                            tr("field_cannot_be_empty", name=tr_label(name))
                        )
                    kwargs[name] = paths
                else:
                    if not text and not optional:
                        raise ValueError(
                            tr("field_cannot_be_empty", name=tr_label(name))
                        )
                    kwargs[name] = text or None
            elif isinstance(widget, QLineEdit):
                val = widget.text().strip()
                if not val and not optional:
                    raise ValueError(tr("field_cannot_be_empty", name=tr_label(name)))
                kwargs[name] = val or None
            elif isinstance(widget, QComboBox):
                data = widget.currentData()
                kwargs[name] = data if data is not None else widget.currentText()
            elif isinstance(widget, QCheckBox):
                kwargs[name] = widget.isChecked()
            elif isinstance(widget, QSpinBox):
                val_int = int(widget.value())
                kwargs[name] = None if optional and val_int == 0 else val_int
            elif isinstance(widget, QDoubleSpinBox):
                val_float = float(widget.value())
                kwargs[name] = None if optional and val_float == 0 else val_float
        return kwargs

    def _pretty_label(self, name: str) -> str:
        """Return a user-friendly, translated label for a parameter name."""
        label = tr_label(name)
        if label == name:  # fallback prettification
            parts = name.replace("_", " ").split()
            up = {"pdf", "png", "jpeg", "tiff", "webp", "docx"}
            words: list[str] = []
            for part in parts:
                low = part.lower()
                words.append(
                    low.upper() if low in up else (part.capitalize() if part else part)
                )
            label = " ".join(words)
        return tr(label)

    def _remember_field(self, name: str, widget: QWidget) -> None:
        """Store the widget representing *name* for later visibility tweaks."""

        self.field_rows[name] = widget

    def _set_row_visible(self, name: str, visible: bool) -> None:
        """Show or hide the form row for parameter *name*."""

        widget = self.field_rows.get(name)
        if widget is None:
            return
        widget.setVisible(visible)
        label_widget = self.form_layout.labelForField(widget)
        if label_widget:
            label_widget.setVisible(visible)

    def _apply_profile_ui(self, profile_value: str, persist: bool = True) -> None:
        """Adjust form elements based on the selected export profile."""

        is_miro = profile_value == "miro"
        for field_name in self.profile_sensitive_fields:
            self._set_row_visible(field_name, not is_miro)
            widget = self.current_widgets.get(field_name)
            if isinstance(widget, tuple):
                for sub_widget in widget:
                    if isinstance(sub_widget, QWidget):
                        sub_widget.setEnabled(not is_miro)
            elif isinstance(widget, QWidget):
                widget.setEnabled(not is_miro)
        if self.profile_help_label:
            self.profile_help_label.setVisible(is_miro)
        if persist:
            self.cfg["last_export_profile"] = profile_value
            save_config(self.cfg)

    def on_info(self) -> None:  # pragma: no cover  # pdf-toolbox: GUI handler | issue:-
        """Display help text for the currently selected action."""
        if not self.current_action:
            return
        text = inspect.cleandoc(self.current_action.help or "No description available.")
        html_text = (
            "<p>"
            + "<br>".join(html.escape(line) for line in text.splitlines())
            + "</p>"
        )
        msg = QMessageBox(self)
        msg.setWindowTitle(self.current_action.name)
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(html_text)
        msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        msg.exec()

    def on_run(self) -> None:  # pragma: no cover  # pdf-toolbox: GUI handler | issue:-
        """Execute the current action or cancel the running worker."""
        if not self.current_action:
            return
        try:
            kwargs = self.collect_args()
        except ValueError as exc:
            QMessageBox.critical(self, "Error", str(exc))
            return
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            if not self.worker.wait(100):
                self.worker.terminate()
                self.worker.wait()
            self.worker = None
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
            self.update_status(tr("cancelled"), "cancelled")
            self.run_btn.setText(tr("start"))
            return

        self.progress.setRange(0, 0)
        self.update_status(tr("running"), "running")
        self.log.clear()
        self.log.setVisible(False)
        self.resize(self.width(), self.base_height)
        self.worker = Worker(self.current_action.func, kwargs)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()
        self.run_btn.setText(tr("stop") + " ❌")

    def on_finished(
        self, result: object
    ) -> None:  # pragma: no cover  # pdf-toolbox: GUI handler | issue:-
        """Handle completion of the worker thread."""
        save_config(self.cfg)
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.run_btn.setText(tr("start"))

        status = tr("done")
        text: str | None = None
        if result:
            if (
                isinstance(result, tuple)
                and len(result) == RESULT_PAIR_LEN
                and isinstance(result[1], float)
            ):
                out_path, reduction = result
                pct = abs(reduction) * 100
                if reduction > 0:
                    status = tr("optimised_reduced", pct=f"{pct:.2f}")
                elif reduction < 0:
                    status = tr("optimised_increased", pct=f"{pct:.2f}")
                else:
                    status = tr("optimised_unchanged")
                if out_path:
                    text = str(out_path)
            elif isinstance(result, list | tuple):
                text = "\n".join(map(str, result))
            else:
                text = str(result)

        self.update_status(status, status)
        if text:
            self.log.setVisible(True)
            if self.log.toPlainText():
                self.log.appendPlainText(text)
            else:
                self.log.setPlainText(text)
        self.worker = None

    def on_error(
        self, msg: str
    ) -> None:  # pragma: no cover  # pdf-toolbox: GUI handler | issue:-
        """Handle errors emitted by the worker thread."""
        self.log.setVisible(True)
        if self.log.toPlainText():
            self.log.appendPlainText(msg)
        else:
            self.log.setPlainText(msg)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.run_btn.setText(tr("start"))
        self.update_status(tr("error"), "error")
        self.resize(self.width(), self.base_height + self.log.height())
        self.worker = None

    def toggle_log(
        self,
    ) -> None:  # pragma: no cover  # pdf-toolbox: GUI handler | issue:-
        """Show or hide the log widget."""
        if self.log.isVisible():
            self.log.setVisible(False)
            self.resize(self.width(), self.base_height)
        else:
            self.log.setVisible(True)
            self.log.verticalScrollBar().setValue(
                self.log.verticalScrollBar().maximum()
            )
            self.resize(self.width(), self.base_height + self.log.height())
        self.update_status(tr(self.status_key), self.status_key)

    def on_author(
        self,
    ) -> None:  # pragma: no cover  # pdf-toolbox: GUI handler | issue:-
        """Edit author and email information in the configuration."""
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("author_email"))
        form = QFormLayout(dlg)
        author_edit = QLineEdit(self.cfg.get("author", ""))
        email_edit = QLineEdit(self.cfg.get("email", ""))
        form.addRow(tr("author"), author_edit)
        form.addRow(tr("email"), email_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)  # type: ignore[attr-defined]  # pdf-toolbox: PySide6 stubs miss dialog button enum | issue:-
        form.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:  # type: ignore[attr-defined]  # pdf-toolbox: PySide6 stubs miss dialog attribute | issue:-
            self.cfg["author"] = author_edit.text().strip()
            self.cfg["email"] = email_edit.text().strip()
            save_config(self.cfg)

    def on_log_level(
        self,
    ) -> None:  # pragma: no cover  # pdf-toolbox: GUI handler | issue:-
        """Allow the user to adjust the logging level."""
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("log_level"))
        form = QFormLayout(dlg)
        combo = QComboBox()
        combo.addItems(["ERROR", "WARNING", "INFO", "DEBUG"])
        combo.setCurrentText(self.cfg.get("log_level", "INFO"))
        form.addRow("Level", combo)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)  # type: ignore[attr-defined]  # pdf-toolbox: PySide6 stubs miss dialog button enum | issue:-
        form.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:  # type: ignore[attr-defined]  # pdf-toolbox: PySide6 stubs miss dialog attribute | issue:-
            level = combo.currentText()
            self.cfg["log_level"] = level
            save_config(self.cfg)
            configure_logging(level, self.log_handler)

    def on_language(
        self,
    ) -> None:  # pragma: no cover  # pdf-toolbox: GUI handler | issue:-
        """Allow the user to change the interface language."""
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("language"))
        form = QFormLayout(dlg)
        combo = QComboBox()
        options = [tr("system"), tr("english"), tr("german")]
        combo.addItems(options)
        current = self.cfg.get("language", "system")
        mapping = {"system": tr("system"), "en": tr("english"), "de": tr("german")}
        combo.setCurrentText(mapping.get(current, tr("system")))
        form.addRow(tr("language"), combo)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)  # type: ignore[attr-defined]  # pdf-toolbox: PySide6 stubs miss dialog button enum | issue:-
        form.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:  # type: ignore[attr-defined]  # pdf-toolbox: PySide6 stubs miss dialog attribute | issue:-
            inverse = {value: key for key, value in mapping.items()}
            choice = inverse.get(combo.currentText(), "system")
            self.cfg["language"] = choice
            save_config(self.cfg)
            set_language(None if choice == "system" else choice)
            self.lbl_actions.setText(tr("actions"))
            if self.worker and self.worker.isRunning():
                self.run_btn.setText(tr("stop") + " ❌")
            else:
                self.run_btn.setText(tr("start"))
            self.action_author.setText(tr("author"))
            self.action_log_level.setText(tr("log_level"))
            self.action_language.setText(tr("language"))
            self.action_about.setText(tr("about"))
            self.tree.clear()
            self._populate_actions()
            self.update_status(tr(self.status_key), self.status_key)

    def on_pptx_renderer(
        self,
    ) -> None:  # pragma: no cover  # pdf-toolbox: GUI handler | issue:-
        """Configure PPTX renderer and show config path."""
        cfg = self.cfg
        dlg = QDialog(self)
        dlg.setWindowTitle("PPTX Renderer")
        form = QFormLayout(dlg)
        combo = QComboBox()
        combo.addItem("System default (no Office)", "")
        combo.addItem("MS Office (PowerPoint)", "ms_office")
        current = cfg.get("pptx_renderer", "")
        index = combo.findData(current)
        combo.setCurrentIndex(max(index, 0))
        form.addRow("PPTX Renderer", combo)
        eff = QLabel(type(get_pptx_renderer()).__name__)
        form.addRow("Effective renderer", eff)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)  # type: ignore[attr-defined]  # pdf-toolbox: PySide6 stubs miss dialog button enum | issue:-
        form.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:  # type: ignore[attr-defined]  # pdf-toolbox: PySide6 stubs miss dialog attribute | issue:-
            value = combo.currentData() or ""
            if value:
                cfg["pptx_renderer"] = value
            else:
                cfg.pop("pptx_renderer", None)
            save_config(cfg)

    def on_about(
        self,
    ) -> None:  # pragma: no cover  # pdf-toolbox: GUI handler | issue:-
        """Show about dialog with version and link."""
        ver = metadata.version("pdf-toolbox")
        msg = QMessageBox(self)
        msg.setWindowTitle(tr("about"))
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(f"<b>pdf_toolbox {ver}</b>")
        msg.setInformativeText(
            "<a href='https://github.com/1cu/pdf_toolbox/'>GitHub Repository</a>"
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        msg.exec()

    def check_author(self) -> None:
        """Warn when author/email config is missing."""
        try:
            _load_author_info()
        except RuntimeError:
            QMessageBox.warning(
                self,
                tr("warning"),
                tr("config_missing_author_email"),
            )
            self.on_author()


__all__ = ["MainWindow"]
