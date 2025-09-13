"""Main Qt window for the GUI (GUI-only)."""

from __future__ import annotations

import html
import inspect
import types
from importlib import metadata
from typing import Any, Literal, get_args, get_origin

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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
from pdf_toolbox.gui.config import load_config, save_config
from pdf_toolbox.gui.widgets import ClickableLabel, FileEdit, QtLogHandler
from pdf_toolbox.gui.worker import Worker
from pdf_toolbox.i18n import label as tr_label
from pdf_toolbox.i18n import set_language, tr
from pdf_toolbox.utils import configure_logging


class MainWindow(QMainWindow):  # pragma: no cover - exercised in GUI tests
    """Main application window."""

    def __init__(self) -> None:  # noqa: PLR0915
        super().__init__()
        self.setWindowTitle("PDF Toolbox")
        self.cfg = load_config()
        # initialize language from config
        lang = self.cfg.get("language", "system")
        set_language(None if lang == "system" else lang)
        self.current_action: Action | None = None
        self.current_widgets: dict[str, Any] = {}
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
        self.status_text = "Ready"
        self.log_handler = QtLogHandler(
            self.log, lambda: self.update_status(self.status_text)
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
        self.form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)  # type: ignore[attr-defined]
        splitter.addWidget(self.form_widget)
        splitter.setSizes([250, 650])

        self.run_btn = QPushButton(tr("start"))
        self.progress = QProgressBar()
        self.status = ClickableLabel("")
        bottom.addWidget(self.status)
        bottom.addWidget(self.progress, 1)
        bottom.addWidget(self.run_btn)
        self.update_status(self.status_text)

        self.settings_btn = QToolButton()
        self.settings_btn.setText("⚙")
        settings_menu = QMenu(self)
        settings_menu.addAction(tr("author"), self.on_author)
        settings_menu.addAction(tr("log_level"), self.on_log_level)
        settings_menu.addAction(tr("language"), self.on_language)
        settings_menu.addAction(tr("about"), self.on_about)
        self.settings_btn.setMenu(settings_menu)
        self.settings_btn.setPopupMode(QToolButton.InstantPopup)  # type: ignore[attr-defined]
        top_bar.addStretch()
        top_bar.addWidget(self.settings_btn)

        self.info_btn.clicked.connect(self.on_info)
        self.run_btn.clicked.connect(self.on_run)
        self.status.clicked.connect(self.toggle_log)
        self.tree.itemClicked.connect(self.on_item_clicked)

        self._populate_actions()
        self.check_author()
        self.show()

    def update_status(self, text: str) -> None:
        self.status_text = text
        arrow = "▼" if self.log.isVisible() else "▶"
        self.status.setText(f"{text} {arrow}")

    def _populate_actions(self) -> None:
        cats: dict[str, QTreeWidgetItem] = {}
        from pdf_toolbox.gui import list_actions as _list_actions

        for act in _list_actions():
            cat_name = act.category or "General"
            cat_item = cats.get(cat_name)
            if cat_item is None:
                cat_item = QTreeWidgetItem([cat_name])
                self.tree.addTopLevelItem(cat_item)
                cats[cat_name] = cat_item
            item = QTreeWidgetItem([act.name])
            item.setData(0, Qt.UserRole, act)  # type: ignore[attr-defined]
            cat_item.addChild(item)
        self.tree.expandAll()

    def on_item_clicked(self, item: QTreeWidgetItem) -> None:  # pragma: no cover - GUI
        act = item.data(0, Qt.UserRole)  # type: ignore[attr-defined]
        if isinstance(act, Action):
            self.current_action = act
            self.build_form(act)
            self.info_btn.setEnabled(bool(act.help))

    def build_form(self, action: Action) -> None:  # noqa: PLR0912, PLR0915
        while self.form_layout.rowCount():
            self.form_layout.removeRow(0)
        self.current_widgets.clear()

        for param in action.params:
            if param.name == "cancel":
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

            from typing import Union

            if get_origin(ann) in (types.UnionType, Union) and int in get_args(ann):  # type: ignore[attr-defined]
                # Union of int and Literal[...] -> (combo presets, custom spin)
                combo = QComboBox()
                spin = QSpinBox()
                # Extract Literal choices
                lit = next(
                    (
                        a
                        for a in get_args(ann)
                        if getattr(a, "__origin__", None) is Literal
                    ),
                    None,
                )
                choices = list(get_args(lit)) if lit else []
                combo.addItems([*choices, "Custom"])
                if isinstance(param.default, str) and param.default in choices:
                    combo.setCurrentText(param.default)
                # default index 0 otherwise
                spin.setVisible(combo.currentText() == "Custom")
                combo.currentTextChanged.connect(
                    lambda t, s=spin: s.setVisible(t == "Custom")
                )
                widget = (combo, spin)
            elif lower in {"input_pdf", "input_path", "pptx_path", "path"}:
                widget = FileEdit(self.cfg)
            elif lower in {"out_dir", "output_dir"}:
                widget = FileEdit(self.cfg, directory=True)
            elif lower in {"paths", "files"}:
                widget = FileEdit(self.cfg, multi=True)
            elif lower in {"quality", "image_format", "dpi"}:
                combo = QComboBox()
                combo.setEditable(False)
                # options populated by default; tests don't depend on exact values here
                widget = combo
            elif lower in {"max_size_mb"}:
                ds = QDoubleSpinBox()
                ds.setMinimum(0)
                ds.setMaximum(10_000)
                widget = ds
            elif lower in {"split_pages", "pages_per_file"}:
                s = QSpinBox()
                s.setMinimum(1)
                s.setMaximum(9999)
                s.setValue(int(self.cfg.get("split_pages", 1)))
                widget = s
            elif isinstance(param.default, bool):
                cb = QCheckBox()
                cb.setChecked(bool(param.default))
                widget = cb
            else:
                widget = QLineEdit()

            # Wrap composite/file widgets in a container with a button/row
            if isinstance(widget, tuple):
                combo, spin = widget
                container = QWidget()
                h = QHBoxLayout(container)
                h.setContentsMargins(0, 0, 0, 0)
                h.addWidget(combo)
                h.addWidget(spin)
                h.setStretch(0, 1)
                self.form_layout.addRow(self._pretty_label(param.name), container)
            elif isinstance(widget, FileEdit):
                container = QWidget()
                h = QHBoxLayout(container)
                h.setContentsMargins(0, 0, 0, 0)
                widget.setMinimumWidth(400)
                h.addWidget(widget)
                btn = QPushButton("...")
                btn.clicked.connect(widget.browse)
                h.addWidget(btn)
                h.setStretch(0, 1)
                self.form_layout.addRow(self._pretty_label(param.name), container)
            else:
                self.form_layout.addRow(self._pretty_label(param.name), widget)  # type: ignore[arg-type]
            self.current_widgets[param.name] = widget

    def collect_args(self) -> dict[str, Any]:  # noqa: PLR0912
        if not self.current_action:
            return {}
        params = {p.name: p for p in self.current_action.params}
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
                    ) in get_args(param.annotation):  # type: ignore[attr-defined]
                        optional = True
            from PySide6.QtWidgets import (
                QCheckBox,
                QComboBox,
                QDoubleSpinBox,
                QLineEdit,
                QSpinBox,
            )

            if isinstance(widget, tuple):
                combo, spin = widget
                val = combo.currentText()
                kwargs[name] = int(spin.value()) if val == "Custom" else val
            elif isinstance(widget, FileEdit):
                text = widget.text().strip()
                if widget.multi:
                    paths = [p for p in text.split(";") if p]
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
                kwargs[name] = widget.currentText()
            elif isinstance(widget, QCheckBox):
                kwargs[name] = widget.isChecked()
            elif isinstance(widget, QSpinBox):
                val = int(widget.value())
                kwargs[name] = None if optional and val == 0 else val
            elif isinstance(widget, QDoubleSpinBox):
                val = float(widget.value())
                kwargs[name] = None if optional and val == 0 else val
        return kwargs

    def _pretty_label(self, name: str) -> str:
        """Return a user-friendly, translated label for a parameter name."""
        label = tr_label(name)
        if label == name:  # fallback prettification
            parts = name.replace("_", " ").split()
            up = {"pdf", "png", "jpeg", "tiff", "webp", "docx"}
            words: list[str] = []
            for p in parts:
                low = p.lower()
                words.append(low.upper() if low in up else (p.capitalize() if p else p))
            label = " ".join(words)
        return tr(label)

    def on_info(self) -> None:  # pragma: no cover - GUI
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

    def on_run(self) -> None:  # pragma: no cover - GUI
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
            self.update_status(tr("cancelled"))
            self.run_btn.setText(tr("start"))
            return

        self.progress.setRange(0, 0)
        self.update_status(tr("running"))
        self.log.clear()
        self.log.setVisible(False)
        self.resize(self.width(), self.base_height)
        self.worker = Worker(self.current_action.func, kwargs)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()
        self.run_btn.setText(tr("stop") + " ❌")

    def on_finished(self, result: object) -> None:  # pragma: no cover - GUI
        save_config(self.cfg)
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.run_btn.setText(tr("start"))
        self.update_status(tr("done"))
        if result:
            if isinstance(result, list | tuple):
                text = "\n".join(map(str, result))
            else:
                text = str(result)
            self.log.setVisible(True)
            if self.log.toPlainText():
                self.log.appendPlainText(text)
            else:
                self.log.setPlainText(text)
        self.worker = None

    def on_error(self, msg: str) -> None:  # pragma: no cover - GUI
        self.log.setVisible(True)
        if self.log.toPlainText():
            self.log.appendPlainText(msg)
        else:
            self.log.setPlainText(msg)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.run_btn.setText(tr("start"))
        self.update_status(tr("error"))
        self.resize(self.width(), self.base_height + self.log.height())
        self.worker = None

    def toggle_log(self) -> None:  # pragma: no cover - GUI
        if self.log.isVisible():
            self.log.setVisible(False)
            self.resize(self.width(), self.base_height)
        else:
            self.log.setVisible(True)
            self.log.verticalScrollBar().setValue(
                self.log.verticalScrollBar().maximum()
            )
            self.resize(self.width(), self.base_height + self.log.height())
        self.update_status(self.status_text)

    def on_author(self) -> None:  # pragma: no cover - GUI
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("author_email"))
        form = QFormLayout(dlg)
        author_edit = QLineEdit(self.cfg.get("author", ""))
        email_edit = QLineEdit(self.cfg.get("email", ""))
        form.addRow(tr("author"), author_edit)
        form.addRow(tr("email"), email_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)  # type: ignore[attr-defined]
        form.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:  # type: ignore[attr-defined]
            self.cfg["author"] = author_edit.text().strip()
            self.cfg["email"] = email_edit.text().strip()
            save_config(self.cfg)

    def on_log_level(self) -> None:  # pragma: no cover - GUI
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("log_level"))
        form = QFormLayout(dlg)
        combo = QComboBox()
        combo.addItems(["ERROR", "WARNING", "INFO", "DEBUG"])
        combo.setCurrentText(self.cfg.get("log_level", "INFO"))
        form.addRow("Level", combo)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)  # type: ignore[attr-defined]
        form.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:  # type: ignore[attr-defined]
            level = combo.currentText()
            self.cfg["log_level"] = level
            save_config(self.cfg)
            from pdf_toolbox import utils

            utils.configure_logging(level, self.log_handler)

    def on_language(self) -> None:  # pragma: no cover - GUI
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
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)  # type: ignore[attr-defined]
        form.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.Accepted:  # type: ignore[attr-defined]
            inv = {v: k for k, v in mapping.items()}
            choice = inv.get(combo.currentText(), "system")
            self.cfg["language"] = choice
            save_config(self.cfg)
            set_language(None if choice == "system" else choice)
            self.lbl_actions.setText(tr("actions"))
            self.run_btn.setText(tr("start"))
            self.update_status(self.status_text)

    def on_about(self) -> None:  # pragma: no cover - GUI
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
            from pdf_toolbox.utils import _load_author_info

            _load_author_info()
        except RuntimeError:
            QMessageBox.warning(
                self,
                tr("warning"),
                tr("config_missing_author_email"),
            )
            self.on_author()


__all__ = ["MainWindow"]
