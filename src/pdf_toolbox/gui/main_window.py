"""Main Qt window for the GUI (GUI-only)."""

from __future__ import annotations

import html
import inspect
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
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
from pdf_toolbox.gui.error_formatter import ErrorFormatter
from pdf_toolbox.gui.form_builder import (
    _CUSTOM_CHOICE_SENTINEL,
    ActionFormBuilder,
    ComboBoxWithSpin,
)
from pdf_toolbox.gui.widgets import ClickableLabel, FileEdit, LogDisplay, QtLogHandler
from pdf_toolbox.gui.worker import Worker
from pdf_toolbox.i18n import set_language, tr
from pdf_toolbox.renderers import registry as pptx_registry
from pdf_toolbox.renderers.pptx import (
    PPTX_PROVIDER_DOCS_URL,
)
from pdf_toolbox.renderers.pptx_base import BasePptxRenderer
from pdf_toolbox.utils import _load_author_info, configure_logging, logger

# Ensure locale integrity checks discover dynamically referenced keys.
_PPTX_ERROR_KEY_REFERENCES = (
    tr("pptx_backend_crashed"),
    tr("pptx_conflicting_options"),
    tr("pptx_corrupt"),
    tr("pptx_empty_selection"),
    tr("pptx_error_unknown"),
    tr("pptx_invalid_range"),
    tr("pptx_permission_denied"),
    tr("pptx_resource_limits"),
    tr("pptx_timeout"),
    tr("pptx_unavailable"),
    tr("pptx_unsupported_option"),
)

type WidgetValue = (
    QLineEdit | QComboBox | QCheckBox | QSpinBox | QDoubleSpinBox | FileEdit | ComboBoxWithSpin
)


@dataclass
class _HttpWidgets:
    group: QGroupBox
    type_combo: QComboBox
    endpoint: QLineEdit
    timeout: QDoubleSpinBox
    verify: QCheckBox
    header_name: QLineEdit
    header_value: QLineEdit
    original_header_key: str | None


@dataclass
class _RendererDialogState:
    dialog: QDialog
    combo: QComboBox
    http_cfg: dict[str, object]
    http_widgets: _HttpWidgets


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
        self.profile_sensitive_fields = {
            "options.image_format",
            "options.dpi",
            "options.quality",
        }
        self.worker: Worker | None = None
        self._output_targets: list[Path] = []
        self.resize(900, 480)
        self.base_height = self.height()

        central = QWidget()
        layout = QVBoxLayout(central)
        top_bar = QHBoxLayout()
        layout.addLayout(top_bar)
        self.banner = QWidget()
        self.banner.setStyleSheet(
            "color: #664400; background-color: #fff4ce; border: 1px solid #e0c97f;"
            " border-radius: 4px;"
        )
        banner_layout = QHBoxLayout(self.banner)
        banner_layout.setContentsMargins(8, 6, 8, 6)
        banner_layout.setSpacing(8)
        self.banner_label = QLabel(tr("pptx_banner_message"))
        self.banner_label.setWordWrap(True)
        self.banner_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        banner_layout.addWidget(self.banner_label, 1)
        self.banner_button = QPushButton(tr("pptx_open_docs"))
        self.banner_button.setAutoDefault(False)
        self.banner_button.setDefault(False)
        self.banner_button.clicked.connect(self._open_pptx_docs)
        banner_layout.addWidget(self.banner_button)
        self.banner.setVisible(False)
        layout.addWidget(self.banner)
        splitter = QSplitter()
        layout.addWidget(splitter)
        bottom = QHBoxLayout()
        layout.addLayout(bottom)
        self.log = LogDisplay()
        self.log.setVisible(False)
        self.log.set_maximum_entries(200)
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
        self.form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.form_builder = ActionFormBuilder(self.form_layout, self.cfg)
        splitter.addWidget(self.form_widget)
        splitter.setSizes([250, 650])

        self.run_btn = QPushButton(tr("start"))
        self.progress = QProgressBar()
        self.status = ClickableLabel("")
        self.open_output_btn = QPushButton(tr("open_output_location"))
        self.open_output_btn.setAutoDefault(False)
        self.open_output_btn.setDefault(False)
        self.open_output_btn.setEnabled(False)
        self.open_output_btn.setVisible(False)
        self.open_output_btn.clicked.connect(self.on_open_output)
        bottom.addWidget(self.open_output_btn)
        bottom.addWidget(self.status)
        bottom.addWidget(self.progress, 1)
        bottom.addWidget(self.run_btn)
        self.update_status(tr("ready"), "ready")

        self.settings_btn = QToolButton()
        self.settings_btn.setText("⚙")
        settings_menu = QMenu(self)
        self.action_author = settings_menu.addAction(tr("author"), self.on_author)
        self.action_log_level = settings_menu.addAction(tr("log_level"), self.on_log_level)
        self.action_language = settings_menu.addAction(tr("language"), self.on_language)
        self.action_renderer = settings_menu.addAction("PPTX Renderer", self.on_pptx_renderer)
        cfg_menu = settings_menu.addMenu(tr("settings_file"))
        cfg_menu.addAction(
            tr("open_folder"),
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(CONFIG_PATH.parent))),
        )
        cfg_menu.addAction(
            tr("copy_path"), lambda: QApplication.clipboard().setText(str(CONFIG_PATH))
        )
        self.action_about = settings_menu.addAction(tr("about"), self.on_about)
        self.settings_menu = settings_menu
        self.settings_btn.setMenu(settings_menu)
        self.settings_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
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
            item.setData(0, Qt.ItemDataRole.UserRole, act)
            cat_item.addChild(item)
        self.tree.expandAll()

    def on_item_clicked(self, item: QTreeWidgetItem) -> None:
        """Respond to tree item clicks by showing the action form."""
        act = item.data(0, Qt.ItemDataRole.UserRole)
        if act:
            self.current_action = act
            self.build_form(act)
            self.info_btn.setEnabled(bool(getattr(act, "help", "")))

    def build_form(self, action: Action) -> None:
        """Create input widgets for the given action parameters."""
        self.banner.setVisible(False)
        self.form_builder.reset_form()

        profile_initial_value = self.form_builder.build_form(
            action, on_profile_change=self._apply_profile_ui
        )

        if profile_initial_value:
            self._apply_profile_ui(profile_initial_value, persist=False)

        provider: BasePptxRenderer | None = None
        if action.requires_pptx_renderer:
            provider = self._select_pptx_provider()
        self._update_pptx_banner(provider)

    def collect_args(self) -> dict[str, Any]:
        """Gather user input from the form into keyword arguments."""
        if not self.current_action:
            return {}
        return self.form_builder.collect_args(self.current_action)

    def _open_pptx_docs(self) -> None:
        """Open the PPTX provider documentation in the default browser."""
        QDesktopServices.openUrl(QUrl(PPTX_PROVIDER_DOCS_URL))

    def _update_pptx_banner(self, provider: BasePptxRenderer | None) -> None:
        """Show or hide the PPTX provider warning banner."""
        action = self.current_action
        if not action or not action.requires_pptx_renderer:
            self.banner.setVisible(False)
            return
        if provider is None:
            self.banner_label.setText(tr("pptx_banner_message"))
            self.banner_button.setText(tr("pptx_open_docs"))
            self.banner.setVisible(True)
            return
        self.banner.setVisible(False)

    def _select_pptx_provider(self) -> BasePptxRenderer | None:
        """Return the configured PPTX provider for the current configuration."""
        raw = self.cfg.get("pptx_renderer", "auto")
        choice = str(raw if raw else "auto").strip() or "auto"
        return pptx_registry.select(choice)

    def _result_to_text(self, result: object) -> str | None:
        """Render *result* as plain text for the log panel."""
        if result is None:
            return None
        if isinstance(result, list | tuple | set):
            return "\n".join(map(str, result))
        return str(result)

    def _extract_output_paths(self, result: object) -> list[Path]:
        """Return filesystem paths referenced by *result*."""
        candidates: list[str] = []
        if isinstance(result, list | tuple | set):
            for item in result:
                if isinstance(item, Path):
                    candidates.append(str(item))
                elif isinstance(item, str):
                    candidates.extend(line.strip() for line in item.splitlines() if line.strip())
        elif isinstance(result, Path):
            candidates.append(str(result))
        elif isinstance(result, str):
            candidates.extend(line.strip() for line in result.splitlines() if line.strip())

        paths: list[Path] = []
        for item in candidates:
            path = Path(item)
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if resolved.exists():
                paths.append(resolved)
        return paths

    def _set_output_targets(self, paths: Iterable[Path]) -> None:
        """Show or hide the output button for *paths*."""
        valid: list[Path] = []
        for path in paths:
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if resolved.exists():
                valid.append(resolved)
        self._output_targets = valid
        has_targets = bool(valid)
        self.open_output_btn.setVisible(has_targets)
        self.open_output_btn.setEnabled(has_targets)

    def on_open_output(self) -> None:
        """Open the directory containing the rendered outputs."""
        if not self._output_targets:
            return
        target = self._output_targets[0]
        open_path = target if target.is_dir() else target.parent
        if not open_path.exists():
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(open_path)))

    def _set_row_visible(self, name: str, visible: bool) -> None:
        """Show or hide the form row for parameter *name*."""
        widget = self.form_builder.field_rows.get(name)
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
            widget = self.form_builder.current_widgets.get(field_name)
            if isinstance(widget, ComboBoxWithSpin):
                widget.combo_box.setEnabled(not is_miro)
                widget.spin_box.setEnabled(not is_miro)
            elif isinstance(widget, QWidget):
                widget.setEnabled(not is_miro)
        if self.form_builder.profile_help_label:
            self.form_builder.profile_help_label.setVisible(is_miro)
        if persist:
            self.cfg["last_export_profile"] = profile_value
            save_config(self.cfg)

    def on_info(self) -> None:
        """Display help text for the currently selected action."""
        if not self.current_action:
            return
        text = inspect.cleandoc(self.current_action.help or "No description available.")
        html_text = "<p>" + "<br>".join(html.escape(line) for line in text.splitlines()) + "</p>"
        msg = QMessageBox(self)
        msg.setWindowTitle(self.current_action.name)
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(html_text)
        msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        msg.exec()

    def on_run(self) -> None:
        """Execute the current action or cancel the running worker."""
        self._set_output_targets(())
        if not self.current_action:
            return
        self._save_current_settings()
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

        provider = (
            self._select_pptx_provider() if self.current_action.requires_pptx_renderer else None
        )
        if self.current_action.requires_pptx_renderer and provider is None:
            self._update_pptx_banner(provider)
            QMessageBox.warning(self, tr("warning"), tr("pptx.no_provider"))
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
            self.update_status(tr("error"), "error")
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

    def on_finished(self, result: object) -> None:
        """Handle completion of the worker thread."""
        save_config(self.cfg)
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.run_btn.setText(tr("start"))

        status_key = "done"
        status = tr("done")
        text = self._result_to_text(result)
        outputs = self._extract_output_paths(result)
        self._set_output_targets(outputs)

        self.update_status(status, status_key)
        if text:
            self.log.setVisible(True)
            source = self.current_action.name if self.current_action else ""
            self.log.add_entry(text, level="RESULT", source=source)
        self.worker = None

    def _extract_widget_value(self, widget: WidgetValue) -> object:  # noqa: PLR0911  # pdf-toolbox: widget type dispatch requires multiple returns | issue:-
        """Extract the current value from a widget."""
        if isinstance(widget, ComboBoxWithSpin):
            data = widget.combo_box.currentData()
            if data == _CUSTOM_CHOICE_SENTINEL:
                return int(widget.spin_box.value())
            return data if data is not None else widget.combo_box.currentText()
        if isinstance(widget, QLineEdit):
            return widget.text().strip() or None
        if isinstance(widget, QComboBox):
            data = widget.currentData()
            return data if data is not None else widget.currentText()
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        if isinstance(widget, QSpinBox):
            return int(widget.value())
        if isinstance(widget, QDoubleSpinBox):
            return float(widget.value())
        return None

    def _save_current_settings(self) -> None:
        """Persist current widget values to the configuration."""
        if not self.current_action:
            return

        # Build map of full_name -> param
        param_map = {p.full_name: p for p in self.current_action.form_params}

        for full_name, widget in self.form_builder.current_widgets.items():
            if isinstance(widget, FileEdit):
                continue

            param = param_map.get(full_name)
            if not param:
                continue

            # For nested dataclass parameters, save with the full dotted name
            # For top-level parameters, save with just the name
            config_key = full_name if param.parent else param.name

            try:
                val = self._extract_widget_value(widget)
                if val is not None:
                    self.cfg[config_key] = val
            except Exception as exc:  # noqa: BLE001, RUF100  # pdf-toolbox: GUI settings save errors should not block execution | issue:-
                logger.warning("Failed to save setting %s: %s", config_key, exc)

        save_config(self.cfg)

    def on_error(self, error: object) -> None:
        """Handle errors emitted by the worker thread."""
        self._set_output_targets(())
        message = ErrorFormatter.format(error)
        self.log.setVisible(True)
        source = self.current_action.name if self.current_action else ""
        self.log.add_entry(message, level="ERROR", source=source)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.run_btn.setText(tr("start"))
        self.update_status(tr("error"), "error")
        self.resize(self.width(), self.base_height + self.log.height())
        self.worker = None

    def closeEvent(  # noqa: N802  # pdf-toolbox: Qt requires camelCase event name | issue:-
        self, event: QCloseEvent
    ) -> None:
        """Cancel running workers before closing the window."""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(1000)
        super().closeEvent(event)

    def toggle_log(
        self,
    ) -> None:
        """Show or hide the log widget."""
        if self.log.isVisible():
            self.log.setVisible(False)
            self.resize(self.width(), self.base_height)
        else:
            self.log.setVisible(True)
            self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())
            self.resize(self.width(), self.base_height + self.log.height())
        self.update_status(tr(self.status_key), self.status_key)

    def on_author(
        self,
    ) -> None:
        """Edit author and email information in the configuration."""
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("author_email"))
        form = QFormLayout(dlg)
        author_edit = QLineEdit(self.cfg.get("author", ""))
        email_edit = QLineEdit(self.cfg.get("email", ""))
        form.addRow(tr("author"), author_edit)
        form.addRow(tr("email"), email_edit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        form.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.cfg["author"] = author_edit.text().strip()
            self.cfg["email"] = email_edit.text().strip()
            save_config(self.cfg)

    def on_log_level(
        self,
    ) -> None:
        """Allow the user to adjust the logging level."""
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("log_level"))
        form = QFormLayout(dlg)
        combo = QComboBox()
        combo.addItems(["ERROR", "WARNING", "INFO", "DEBUG"])
        combo.setCurrentText(self.cfg.get("log_level", "INFO"))
        form.addRow("Level", combo)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        form.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            level = combo.currentText()
            self.cfg["log_level"] = level
            save_config(self.cfg)
            configure_logging(level, self.log_handler)

    def on_language(
        self,
    ) -> None:
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
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        form.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.DialogCode.Accepted:
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
            self.banner_label.setText(tr("pptx_banner_message"))
            self.banner_button.setText(tr("pptx_open_docs"))
            self.open_output_btn.setText(tr("open_output_location"))
            self.tree.clear()
            self._populate_actions()
            self.update_status(tr(self.status_key), self.status_key)

    def _create_http_office_group(
        self,
        http_cfg: Mapping[str, object],
    ) -> tuple[
        QGroupBox,
        QComboBox,
        QLineEdit,
        QDoubleSpinBox,
        QCheckBox,
        QLineEdit,
        QLineEdit,
        str | None,
    ]:
        """Return the HTTP renderer configuration group and its widgets."""
        http_group = QGroupBox(tr("pptx_http_settings"))
        http_group.setObjectName("pptx_http_group")
        http_layout = QFormLayout(http_group)

        http_type = QComboBox()
        http_type.setObjectName("pptx_http_type")
        http_type.addItem(tr("pptx_http_type_auto"), "auto")
        http_type.addItem(tr("pptx_http_type_stirling"), "stirling")
        http_type.addItem(tr("pptx_http_type_gotenberg"), "gotenberg")
        current_http_mode = str(http_cfg.get("mode") or "auto")
        http_index = http_type.findData(current_http_mode)
        http_type.setCurrentIndex(max(http_index, 0))
        http_layout.addRow(tr("pptx_http_type_label"), http_type)

        http_endpoint = QLineEdit(str(http_cfg.get("endpoint") or ""))
        http_endpoint.setObjectName("pptx_http_endpoint")
        http_layout.addRow(tr("pptx_http_endpoint"), http_endpoint)

        http_timeout = QDoubleSpinBox()
        http_timeout.setObjectName("pptx_http_timeout")
        http_timeout.setRange(0.0, 600.0)
        http_timeout.setDecimals(1)
        http_timeout.setSingleStep(1.0)
        stored_timeout = http_cfg.get("timeout_s")
        http_timeout_value = (
            float(stored_timeout) if isinstance(stored_timeout, int | float) else 60.0
        )
        http_timeout.setValue(http_timeout_value)
        http_layout.addRow(tr("pptx_http_timeout"), http_timeout)

        http_verify = QCheckBox(tr("pptx_http_verify_tls"))
        http_verify.setObjectName("pptx_http_verify_tls")
        http_verify.setChecked(bool(http_cfg.get("verify_tls", True)))
        http_layout.addRow(http_verify)

        header_name_value = ""
        header_value_value = ""
        header_original_key: str | None = None
        existing_headers = http_cfg.get("headers")
        if isinstance(existing_headers, Mapping):
            for key, value in existing_headers.items():
                if key is None:
                    continue
                candidate = str(key).strip()
                if not candidate:
                    continue
                header_original_key = candidate
                header_name_value = candidate
                header_value_value = "" if value is None else str(value)
                break

        http_header_name = QLineEdit(header_name_value)
        http_header_name.setObjectName("pptx_http_header_name")
        http_layout.addRow(tr("pptx_http_header_name"), http_header_name)

        http_header_value = QLineEdit(header_value_value)
        http_header_value.setObjectName("pptx_http_header_value")
        http_layout.addRow(tr("pptx_http_header_value"), http_header_value)

        return (
            http_group,
            http_type,
            http_endpoint,
            http_timeout,
            http_verify,
            http_header_name,
            http_header_value,
            header_original_key,
        )

    def on_pptx_renderer(
        self,
    ) -> None:
        """Configure PPTX renderer and show config path."""
        state = self._create_renderer_dialog(self.cfg)
        if state.dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._apply_renderer_selection(state)

    def on_about(
        self,
    ) -> None:
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
        author, email = _load_author_info()
        if author and email:
            return
        QMessageBox.warning(
            self,
            tr("warning"),
            tr("config_missing_author_email"),
        )
        self.on_author()

    def _create_renderer_dialog(self, cfg: dict[str, object]) -> _RendererDialogState:
        """Return the dialog and widgets used to configure PPTX rendering."""
        dlg = QDialog(self)
        dlg.setWindowTitle("PPTX Renderer")
        form = QFormLayout(dlg)
        combo = QComboBox()
        options = [
            ("Automatic (detect installed providers)", "auto"),
            ("Disabled (show provider banner)", "none"),
            ("Microsoft PowerPoint (COM automation)", "ms_office"),
            (
                "Microsoft Office Online (HTTP service, e.g. Stirling or Gotenberg)",
                "http_office",
            ),
            ("Lightweight sample renderer", "lightweight"),
        ]
        for label_text, value in options:
            combo.addItem(label_text, value)
        current_value = cfg.get("pptx_renderer")
        current = current_value.strip() if isinstance(current_value, str) else "auto"
        if not current:
            current = "auto"
        index = combo.findData(current)
        combo.setCurrentIndex(max(index, 0))
        form.addRow("PPTX Renderer", combo)

        raw_http_cfg = cfg.get("http_office")
        http_cfg: dict[str, object] = dict(raw_http_cfg) if isinstance(raw_http_cfg, dict) else {}
        http_group = self._create_http_office_group(http_cfg)
        http_widgets = _HttpWidgets(*http_group)
        form.addRow(http_widgets.group)

        def _update_http_visibility() -> None:
            http_widgets.group.setVisible(combo.currentData() == "http_office")

        combo.currentIndexChanged.connect(lambda _index: _update_http_visibility())
        _update_http_visibility()

        renderer = self._select_pptx_provider()
        effective_label = QLabel(
            tr("pptx.no_provider") if renderer is None else type(renderer).__name__
        )
        form.addRow("Effective renderer", effective_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        form.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        return _RendererDialogState(
            dialog=dlg,
            combo=combo,
            http_cfg=http_cfg,
            http_widgets=http_widgets,
        )

    def _apply_renderer_selection(self, state: _RendererDialogState) -> None:
        """Persist the renderer configuration chosen in the dialog."""
        value = state.combo.currentData()
        self.cfg["pptx_renderer"] = str(value) if value else "auto"
        headers = self._build_http_headers(state.http_cfg, state.http_widgets)
        widgets = state.http_widgets
        http_payload: dict[str, object] = {
            "mode": widgets.type_combo.currentData() or "auto",
            "endpoint": widgets.endpoint.text().strip(),
            "timeout_s": float(widgets.timeout.value()),
            "verify_tls": widgets.verify.isChecked(),
            "headers": headers,
        }
        self.cfg["http_office"] = http_payload
        save_config(self.cfg)

    def _build_http_headers(
        self,
        http_cfg: dict[str, object],
        widgets: _HttpWidgets,
    ) -> dict[str, str]:
        """Merge existing HTTP headers with the values entered in the dialog."""
        headers: dict[str, str] = {}
        existing_headers = http_cfg.get("headers")
        if isinstance(existing_headers, Mapping):
            for key, value in existing_headers.items():
                if key is None:
                    continue
                candidate = str(key).strip()
                if not candidate:
                    continue
                headers[candidate] = "" if value is None else str(value)
        header_name = widgets.header_name.text().strip()
        original_key = widgets.original_header_key
        if original_key and (not header_name or header_name != original_key):
            headers.pop(original_key, None)
        if header_name:
            headers[header_name] = widgets.header_value.text()
        return headers


__all__ = ["MainWindow"]
