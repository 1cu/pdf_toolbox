from __future__ import annotations

import json
import sys
import inspect
import tempfile
from pathlib import Path
from typing import Any, Dict, Literal, get_args, get_origin

from .actions import Action, list_actions
from . import utils

CONFIG_PATH = Path(tempfile.gettempdir()) / "pdf_toolbox_config.json"
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
DEFAULT_CONFIG = {
    "last_open_dir": str(Path.home()),
    "last_save_dir": str(Path.home()),
    "jpeg_quality": 95,
    "pptx_width": 1920,
    "pptx_height": 1080,
    "opt_quality": "default",
    "opt_compress_images": False,
    "split_pages": 1,
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


try:  # pragma: no cover - optional import
    from PySide6.QtCore import Qt, QThread, Signal
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QDialog,
        QDialogButtonBox,
        QDoubleSpinBox,
        QComboBox,
        QFileDialog,
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

    QT_AVAILABLE = True
except Exception as exc:  # pragma: no cover - headless
    QT_AVAILABLE = False
    QT_IMPORT_ERROR = exc


if QT_AVAILABLE:

    class FileEdit(QLineEdit):
        def __init__(self, cfg: dict, directory: bool = False, multi: bool = False):
            super().__init__()
            self.cfg = cfg
            self.directory = directory
            self.multi = multi
            self.setAcceptDrops(True)

        def browse(self) -> None:
            initial = self.cfg.get("last_open_dir", str(Path.home()))
            if self.directory:
                path = QFileDialog.getExistingDirectory(self, "Ordner wählen", initial)
                if path:
                    self.setText(path)
                    self.cfg["last_open_dir"] = path
                    save_config(self.cfg)
            elif self.multi:
                paths, _ = QFileDialog.getOpenFileNames(self, "Dateien wählen", initial)
                if paths:
                    self.setText(";".join(paths))
                    self.cfg["last_open_dir"] = str(Path(paths[0]).parent)
                    save_config(self.cfg)
            else:
                path, _ = QFileDialog.getOpenFileName(self, "Datei wählen", initial)
                if path:
                    self.setText(path)
                    self.cfg["last_open_dir"] = str(Path(path).parent)
                    save_config(self.cfg)

        def dragEnterEvent(self, e):  # pragma: no cover - GUI
            if e.mimeData().hasUrls():
                e.acceptProposedAction()

        def dropEvent(self, e):  # pragma: no cover - GUI
            paths = [url.toLocalFile() for url in e.mimeData().urls()]
            if not paths:
                return
            if self.multi:
                self.setText(";".join(paths))
            else:
                self.setText(paths[0])
            self.cfg["last_open_dir"] = str(Path(paths[0]).parent)
            save_config(self.cfg)

    class Worker(QThread):
        finished = Signal(object)
        error = Signal(str)

        def __init__(self, func, kwargs: Dict[str, Any]):
            super().__init__()
            self.func = func
            self.kwargs = kwargs

        def run(self) -> None:  # pragma: no cover - thread
            try:
                result = self.func(**self.kwargs)
                self.finished.emit(result)
            except Exception as exc:  # pragma: no cover - thread
                self.error.emit(str(exc))

    class ClickableLabel(QLabel):
        clicked = Signal()

        def mousePressEvent(self, event):  # pragma: no cover - GUI
            self.clicked.emit()
            super().mousePressEvent(event)

    class MainWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("PDF Toolbox")
            self.cfg = load_config()
            self.current_action: Action | None = None
            self.current_widgets: Dict[str, QWidget] = {}
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
            layout.addWidget(self.log)
            self.setCentralWidget(central)

            lbl = QLabel("Aktionen")
            self.info_btn = QPushButton("i")
            self.info_btn.setFixedWidth(24)
            self.info_btn.setEnabled(False)
            top_bar.addWidget(lbl)
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

            self.run_btn = QPushButton("Start")
            self.progress = QProgressBar()
            self.status = ClickableLabel("Bereit")
            bottom.addWidget(self.status)
            bottom.addWidget(self.progress, 1)
            bottom.addWidget(self.run_btn)

            self.settings_btn = QToolButton()
            self.settings_btn.setText("⚙")
            settings_menu = QMenu(self)
            settings_menu.addAction("Autor", self.on_author)
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

        def _populate_actions(self) -> None:
            cats: dict[str, QTreeWidgetItem] = {}
            for act in list_actions():
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

        def on_item_clicked(
            self, item: QTreeWidgetItem
        ) -> None:  # pragma: no cover - GUI
            act = item.data(0, Qt.UserRole)  # type: ignore[attr-defined]
            if isinstance(act, Action):
                self.current_action = act
                self.build_form(act)
                self.info_btn.setEnabled(bool(act.help))

        def build_form(self, action: Action) -> None:
            while self.form_layout.rowCount():
                self.form_layout.removeRow(0)
            self.current_widgets.clear()

            for param in action.params:
                widget: QWidget
                ann = param.annotation
                origin = get_origin(ann)
                lower = param.name.lower()
                if ann is bool:
                    widget = QCheckBox()
                    if param.default is True:
                        widget.setChecked(True)
                elif ann is int:
                    widget = QSpinBox()
                    if param.default not in (inspect._empty, None):
                        widget.setValue(int(param.default))
                elif ann is float:
                    widget = QDoubleSpinBox()
                    if param.default not in (inspect._empty, None):
                        widget.setValue(float(param.default))
                elif origin is Literal:
                    widget = QComboBox()
                    choices = [str(x) for x in get_args(ann)]
                    widget.addItems(choices)
                    if param.default not in (inspect._empty, None):
                        widget.setCurrentText(str(param.default))
                elif origin is list and get_args(ann) == (str,):
                    widget = FileEdit(self.cfg, multi=True)
                else:
                    if any(k in lower for k in ["dir", "folder"]):
                        widget = FileEdit(self.cfg, directory=True)
                    elif any(k in lower for k in ["file", "path", "input", "source"]):
                        widget = FileEdit(self.cfg)
                    else:
                        widget = QLineEdit()
                        if param.default not in (inspect._empty, None):
                            widget.setText(str(param.default))

                if isinstance(widget, FileEdit):
                    container = QWidget()
                    h = QHBoxLayout(container)
                    h.setContentsMargins(0, 0, 0, 0)
                    widget.setMinimumWidth(400)
                    h.addWidget(widget)
                    btn = QPushButton("...")
                    btn.clicked.connect(widget.browse)
                    h.addWidget(btn)
                    h.setStretch(0, 1)
                    self.form_layout.addRow(param.name, container)
                else:
                    self.form_layout.addRow(param.name, widget)
                self.current_widgets[param.name] = widget

        def collect_args(self) -> Dict[str, Any]:
            kwargs: Dict[str, Any] = {}
            for name, widget in self.current_widgets.items():
                if isinstance(widget, FileEdit):
                    text = widget.text().strip()
                    if widget.multi:
                        kwargs[name] = [p for p in text.split(";") if p]
                    else:
                        kwargs[name] = text
                elif isinstance(widget, QLineEdit):
                    val = widget.text().strip()
                    kwargs[name] = val if val else None
                elif isinstance(widget, QComboBox):
                    kwargs[name] = widget.currentText()
                elif isinstance(widget, QCheckBox):
                    kwargs[name] = widget.isChecked()
                elif isinstance(widget, QSpinBox):
                    kwargs[name] = int(widget.value())
                elif isinstance(widget, QDoubleSpinBox):
                    kwargs[name] = float(widget.value())
            return kwargs

        def on_info(self) -> None:  # pragma: no cover - GUI
            if not self.current_action:
                return
            text = self.current_action.help or "Keine Beschreibung vorhanden."
            QMessageBox.information(self, self.current_action.name, text)

        def on_run(self) -> None:  # pragma: no cover - GUI
            if not self.current_action:
                return
            kwargs = self.collect_args()
            self.run_btn.setEnabled(False)
            self.progress.setRange(0, 0)
            self.status.setText("Läuft...")
            self.log.clear()
            self.log.setVisible(False)
            self.resize(self.width(), self.base_height)
            self.worker = Worker(self.current_action.func, kwargs)
            self.worker.finished.connect(self.on_finished)
            self.worker.error.connect(self.on_error)
            self.worker.start()

        def on_finished(self, result: object) -> None:  # pragma: no cover - GUI
            save_config(self.cfg)
            self.progress.setRange(0, 1)
            self.progress.setValue(1)
            self.status.setText("Fertig")
            self.run_btn.setEnabled(True)
            if result:
                if isinstance(result, (list, tuple)):
                    text = "\n".join(map(str, result))
                else:
                    text = str(result)
                self.log.setPlainText(text)
                self.log.setVisible(True)
                self.resize(
                    self.width(), self.base_height + self.log.sizeHint().height()
                )
            else:
                self.log.setVisible(False)
                self.resize(self.width(), self.base_height)

        def on_error(self, msg: str) -> None:  # pragma: no cover - GUI
            self.log.setPlainText(msg)
            self.log.setVisible(True)
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
            self.status.setText("Fehler")
            self.run_btn.setEnabled(True)
            self.resize(self.width(), self.base_height + self.log.sizeHint().height())

        def toggle_log(self) -> None:  # pragma: no cover - GUI
            if self.log.isVisible():
                self.log.setVisible(False)
                self.resize(self.width(), self.base_height)
            else:
                self.log.setVisible(True)
                self.log.verticalScrollBar().setValue(
                    self.log.verticalScrollBar().maximum()
                )
                self.resize(
                    self.width(), self.base_height + self.log.sizeHint().height()
                )

        def on_author(self) -> None:  # pragma: no cover - GUI
            dlg = QDialog(self)
            dlg.setWindowTitle("Autor/E-Mail")
            form = QFormLayout(dlg)
            try:
                data = json.loads(utils.CONFIG_FILE.read_text())
            except Exception:
                data = {}
            author_edit = QLineEdit(data.get("author", ""))
            email_edit = QLineEdit(data.get("email", ""))
            form.addRow("Autor", author_edit)
            form.addRow("E-Mail", email_edit)
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)  # type: ignore[attr-defined]
            form.addWidget(buttons)
            buttons.accepted.connect(dlg.accept)
            buttons.rejected.connect(dlg.reject)
            if dlg.exec() == QDialog.Accepted:  # type: ignore[attr-defined]
                utils.CONFIG_FILE.write_text(
                    json.dumps(
                        {
                            "author": author_edit.text().strip(),
                            "email": email_edit.text().strip(),
                        },
                        indent=2,
                    )
                )

        def check_author(self) -> None:
            try:
                utils._load_author_info()
            except RuntimeError:
                QMessageBox.warning(
                    self,
                    "Hinweis",
                    "pdf_toolbox_config.json muss 'author' und 'email' enthalten.",
                )
                self.on_author()


def main() -> None:  # pragma: no cover - entry point
    if not QT_AVAILABLE:
        raise RuntimeError(f"PySide6 konnte nicht geladen werden: {QT_IMPORT_ERROR}")
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":  # pragma: no cover - entry point
    main()
