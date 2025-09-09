from __future__ import annotations

import json
import os
import sys
import inspect
from pathlib import Path
from typing import Any, Dict, get_args, get_origin

from .actions import Action, list_actions

APPDATA = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
CONFIG_PATH = APPDATA / "JensTools" / "pdf_toolbox" / "config.json"
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
        QDoubleSpinBox,
        QFileDialog,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QSpinBox,
        QSplitter,
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
            elif self.multi:
                paths, _ = QFileDialog.getOpenFileNames(self, "Dateien wählen", initial)
                if paths:
                    self.setText(";".join(paths))
                    self.cfg["last_open_dir"] = str(Path(paths[0]).parent)
            else:
                path, _ = QFileDialog.getOpenFileName(self, "Datei wählen", initial)
                if path:
                    self.setText(path)
                    self.cfg["last_open_dir"] = str(Path(path).parent)

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

    class MainWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("PDF Toolbox")
            self.cfg = load_config()
            self.current_action: Action | None = None
            self.current_widgets: Dict[str, QWidget] = {}
            self.resize(900, 600)

            central = QWidget()
            layout = QVBoxLayout(central)
            splitter = QSplitter()
            layout.addWidget(splitter)
            bottom = QHBoxLayout()
            layout.addLayout(bottom)
            self.setCentralWidget(central)

            self.tree = QTreeWidget()
            self.tree.setHeaderHidden(True)
            self.tree.setMinimumWidth(200)
            splitter.addWidget(self.tree)
            self.tree.setColumnWidth(0, 200)

            self.form_widget = QWidget()
            self.form_layout = QFormLayout(self.form_widget)
            splitter.addWidget(self.form_widget)
            splitter.setSizes([250, 650])

            self.info_btn = QPushButton("i")
            self.info_btn.setFixedWidth(24)
            self.info_btn.setEnabled(False)
            self.run_btn = QPushButton("Start")
            self.progress = QProgressBar()
            self.status = QLabel()
            bottom.addWidget(self.info_btn)
            bottom.addWidget(self.run_btn)
            bottom.addWidget(self.progress)
            bottom.addWidget(self.status)

            self.info_btn.clicked.connect(self.on_info)
            self.run_btn.clicked.connect(self.on_run)
            self.tree.itemClicked.connect(self.on_item_clicked)

            self._populate_actions()

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
                item.setData(0, Qt.UserRole, act)
                cat_item.addChild(item)
            self.tree.expandAll()

        def on_item_clicked(
            self, item: QTreeWidgetItem
        ) -> None:  # pragma: no cover - GUI
            act = item.data(0, Qt.UserRole)
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
                    h.addWidget(widget)
                    btn = QPushButton("...")
                    btn.clicked.connect(widget.browse)
                    h.addWidget(btn)
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

        def on_error(self, msg: str) -> None:  # pragma: no cover - GUI
            QMessageBox.critical(self, "Fehler", msg)
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
            self.status.setText("Fehler")
            self.run_btn.setEnabled(True)


def main() -> None:  # pragma: no cover - entry point
    if not QT_AVAILABLE:
        raise RuntimeError(f"PySide6 konnte nicht geladen werden: {QT_IMPORT_ERROR}")
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":  # pragma: no cover - entry point
    main()
