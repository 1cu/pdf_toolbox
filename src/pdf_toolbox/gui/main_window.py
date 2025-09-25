"""Main Qt window for the GUI (GUI-only)."""

from __future__ import annotations

import html
import inspect
import sys
import types
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any, Literal, Union, get_args, get_origin

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

from pdf_toolbox.actions import Action, Param
from pdf_toolbox.config import CONFIG_PATH, load_config, save_config
from pdf_toolbox.gui.widgets import ClickableLabel, FileEdit, LogDisplay, QtLogHandler
from pdf_toolbox.gui.worker import Worker
from pdf_toolbox.i18n import label as tr_label
from pdf_toolbox.i18n import set_language, tr
from pdf_toolbox.renderers import registry as pptx_registry
from pdf_toolbox.renderers.pptx import (
    PPTX_PROVIDER_DOCS_URL,
    PptxProviderUnavailableError,
    PptxRenderingError,
)
from pdf_toolbox.renderers.pptx_base import BasePptxRenderer
from pdf_toolbox.utils import _load_author_info, configure_logging

_PPTX_ERROR_KEYS_BY_CODE = {
    "backend_crashed": "pptx_backend_crashed",
    "conflicting_options": "pptx_conflicting_options",
    "corrupt": "pptx_corrupt",
    "empty_selection": "pptx_empty_selection",
    "invalid_range": "pptx_invalid_range",
    "permission_denied": "pptx_permission_denied",
    "resource_limits_exceeded": "pptx_resource_limits",
    "timeout": "pptx_timeout",
    "unavailable": "pptx_unavailable",
    "unsupported_option": "pptx_unsupported_option",
}

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

_CUSTOM_CHOICE_SENTINEL = "__custom__"


@dataclass
class ComboBoxWithSpin:
    """Container for combo box widgets paired with a spin box."""

    combo_box: QComboBox
    spin_box: QSpinBox


WidgetValue = (
    QLineEdit
    | QComboBox
    | QCheckBox
    | QSpinBox
    | QDoubleSpinBox
    | FileEdit
    | ComboBoxWithSpin
)


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
        self.current_widgets: dict[str, WidgetValue] = {}
        self.field_rows: dict[str, QWidget] = {}
        self.profile_help_label: QLabel | None = None
        self.profile_combo: QComboBox | None = None
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
        self.banner_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
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
        self.form_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
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

    def build_form(self, action: Action) -> None:  # noqa: PLR0912, PLR0915  # pdf-toolbox: dynamic form builder is inherently complex | issue:-
        """Create input widgets for the given action parameters."""
        while self.form_layout.rowCount():
            self.form_layout.removeRow(0)
        self.current_widgets.clear()
        self.field_rows = {}
        self.profile_help_label = None
        self.profile_combo = None
        self.banner.setVisible(False)
        profile_initial_value: str | None = None

        for param in action.form_params:
            if param.name in {"cancel", "progress_callback"}:
                continue
            widget: WidgetValue
            ann = param.annotation
            lower = param.name.lower()

            if param.name == "export_profile":
                combo_box = QComboBox()
                combo_box.addItem(
                    tr("gui_export_profile_custom"),
                    userData="custom",
                )
                combo_box.addItem(
                    tr("gui_export_profile_miro"),
                    userData="miro",
                )
                saved = self.cfg.get("last_export_profile", "miro")
                if saved not in {"custom", "miro"}:
                    saved = "miro"
                index = combo_box.findData(saved)
                combo_box.setCurrentIndex(max(index, 0))
                combo_box.currentIndexChanged.connect(
                    lambda _idx, combo=combo_box: self._apply_profile_ui(
                        combo.currentData() or combo.currentText()
                    )
                )
                help_label = QLabel(tr("gui_export_profile_miro_help"))
                help_label.setWordWrap(True)
                help_label.setVisible(False)
                self.form_layout.addRow(tr("gui_export_profile_label"), combo_box)
                self.form_layout.addRow("", help_label)
                self.current_widgets[param.full_name] = combo_box
                self.profile_help_label = help_label
                self.profile_combo = combo_box
                self._remember_field(param.full_name, combo_box)
                profile_initial_value = (
                    combo_box.currentData() or combo_box.currentText()
                )
                continue

            union_type = getattr(types, "UnionType", None)
            if get_origin(ann) in (Union, union_type) and int in get_args(ann):
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
                    for ch in choices:
                        combo_box.addItem(str(ch), ch)
                    combo_box.addItem(tr("gui_custom"), _CUSTOM_CHOICE_SENTINEL)
                    if isinstance(param.default, str) and param.default in choices:
                        idx = combo_box.findData(param.default)
                        combo_box.setCurrentIndex(max(idx, 0))
                        spin_box.setVisible(False)
                    elif isinstance(param.default, int):
                        idx = combo_box.findData(_CUSTOM_CHOICE_SENTINEL)
                        combo_box.setCurrentIndex(max(idx, 0))
                        spin_box.setValue(param.default)
                        spin_box.setVisible(True)
                    else:
                        spin_box.setVisible(
                            combo_box.currentData() == _CUSTOM_CHOICE_SENTINEL
                        )
                    combo_box.currentIndexChanged.connect(
                        lambda _i, cb=combo_box, sb=spin_box: sb.setVisible(
                            cb.currentData() == _CUSTOM_CHOICE_SENTINEL
                        )
                    )
                    widget = ComboBoxWithSpin(combo_box=combo_box, spin_box=spin_box)
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
            if isinstance(widget, ComboBoxWithSpin):
                container = QWidget()
                layout = QHBoxLayout(container)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.addWidget(widget.combo_box)
                layout.addWidget(widget.spin_box)
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
                self.form_layout.addRow(
                    self._pretty_label(param.name),
                    widget,
                )
                field_widget = widget
            self.current_widgets[param.full_name] = widget
            self._remember_field(param.full_name, field_widget)

        if profile_initial_value:
            self._apply_profile_ui(profile_initial_value, persist=False)

        provider: BasePptxRenderer | None = None
        if self.current_action and self.current_action.requires_pptx_renderer:
            provider = self._select_pptx_provider()
        self._update_pptx_banner(provider)

    def collect_args(self) -> dict[str, Any]:
        """Gather user input from the form into keyword arguments."""
        if not self.current_action:
            return {}
        params = {param.full_name: param for param in self.current_action.form_params}
        kwargs: dict[str, Any] = {}
        dataclass_values: dict[str, dict[str, Any]] = {}
        for full_name, widget in self.current_widgets.items():
            param = params.get(full_name)
            optional = self._param_is_optional(param)
            label_key = param.name if param else full_name.rsplit(".", 1)[-1]
            target_store, target_key = self._target_store_for(
                param, full_name, dataclass_values, kwargs
            )
            self._assign_widget_value(
                widget,
                target_store=target_store,
                target_key=target_key,
                optional=optional,
                label_key=label_key,
            )
        for dc_name, dc_type in self.current_action.dataclass_params.items():
            field_values = dataclass_values.get(dc_name, {})
            kwargs[dc_name] = dc_type(**field_values)
        return kwargs

    def _param_is_optional(self, param: Param | None) -> bool:
        """Return whether *param* may be omitted by the user."""
        if param is None:
            return False
        if param.default is not inspect._empty:
            return True
        origin = get_origin(param.annotation)
        union_type = getattr(types, "UnionType", None)
        if origin in (Union, union_type):
            return type(None) in get_args(param.annotation)
        return False

    def _target_store_for(
        self,
        param: Param | None,
        full_name: str,
        dataclass_values: dict[str, dict[str, Any]],
        kwargs: dict[str, Any],
    ) -> tuple[dict[str, Any], str]:
        """Return the mapping and key that should receive the widget value."""
        if param and param.parent:
            return dataclass_values.setdefault(param.parent, {}), param.name
        if param:
            return kwargs, param.name
        return kwargs, full_name

    def _assign_widget_value(
        self,
        widget: WidgetValue,
        *,
        target_store: dict[str, Any],
        target_key: str,
        optional: bool,
        label_key: str,
    ) -> None:
        """Store the value represented by *widget* in *target_store*."""
        if isinstance(widget, ComboBoxWithSpin):
            value = self._value_from_combo_with_spin(widget)
        elif isinstance(widget, FileEdit):
            value = self._value_from_file_edit(widget, optional, label_key)
        elif isinstance(widget, QLineEdit):
            value = self._value_from_line_edit(widget, optional, label_key)
        elif isinstance(widget, QComboBox):
            value = self._value_from_combo_box(widget)
        elif isinstance(widget, QCheckBox):
            value = widget.isChecked()
        elif isinstance(widget, QSpinBox):
            value = self._value_from_spin_box(widget, optional)
        elif isinstance(widget, QDoubleSpinBox):
            value = self._value_from_double_spin(widget, optional)
        else:
            msg = f"Unsupported widget type: {type(widget)!r}"
            raise ValueError(msg)  # noqa: TRY004  # pdf-toolbox: GUI handler expects ValueError | issue:-
        target_store[target_key] = value

    def _value_from_combo_with_spin(self, widget: ComboBoxWithSpin) -> Any:
        data = widget.combo_box.currentData()
        if data == _CUSTOM_CHOICE_SENTINEL:
            return int(widget.spin_box.value())
        return data if data is not None else widget.combo_box.currentText()

    def _value_from_file_edit(
        self, widget: FileEdit, optional: bool, label_key: str
    ) -> Any:
        text = widget.text().strip()
        if widget.multi:
            paths = [file_path for file_path in text.split(";") if file_path]
            if not paths and not optional:
                raise self._field_empty_error(label_key)
            return paths
        if not text and not optional:
            raise self._field_empty_error(label_key)
        return text or None

    def _value_from_line_edit(
        self, widget: QLineEdit, optional: bool, label_key: str
    ) -> Any:
        value = widget.text().strip()
        if not value and not optional:
            raise self._field_empty_error(label_key)
        return value or None

    def _value_from_combo_box(self, widget: QComboBox) -> Any:
        data = widget.currentData()
        return data if data is not None else widget.currentText()

    def _value_from_spin_box(self, widget: QSpinBox, optional: bool) -> Any:
        val_int = int(widget.value())
        return None if optional and val_int == 0 else val_int

    def _value_from_double_spin(self, widget: QDoubleSpinBox, optional: bool) -> Any:
        val_float = float(widget.value())
        return None if optional and val_float == 0 else val_float

    def _field_empty_error(self, label_key: str) -> ValueError:
        """Return a translated error for missing required fields."""
        return ValueError(tr("field_cannot_be_empty", name=tr_label(label_key)))

    def _pretty_label(self, name: str) -> str:
        """Return a user-friendly, translated label for a parameter name."""
        label = tr_label(name)
        if label == name:  # fallback prettification
            parts = name.replace("_", " ").split()
            up = {"pdf", "png", "jpeg", "tiff", "webp"}
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
                    candidates.extend(
                        line.strip() for line in item.splitlines() if line.strip()
                    )
        elif isinstance(result, Path):
            candidates.append(str(result))
        elif isinstance(result, str):
            candidates.extend(
                line.strip() for line in result.splitlines() if line.strip()
            )

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
            if isinstance(widget, ComboBoxWithSpin):
                widget.combo_box.setEnabled(not is_miro)
                widget.spin_box.setEnabled(not is_miro)
            elif isinstance(widget, QWidget):
                widget.setEnabled(not is_miro)
        if self.profile_help_label:
            self.profile_help_label.setVisible(is_miro)
        if persist:
            self.cfg["last_export_profile"] = profile_value
            save_config(self.cfg)

    def on_info(self) -> None:
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

    def on_run(self) -> None:
        """Execute the current action or cancel the running worker."""
        self._set_output_targets(())
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

        provider = (
            self._select_pptx_provider()
            if self.current_action.requires_pptx_renderer
            else None
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

    def on_error(self, error: object) -> None:
        """Handle errors emitted by the worker thread."""
        self._set_output_targets(())
        message = self._format_error_message(error)
        self.log.setVisible(True)
        source = self.current_action.name if self.current_action else ""
        self.log.add_entry(message, level="ERROR", source=source)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.run_btn.setText(tr("start"))
        self.update_status(tr("error"), "error")
        self.resize(self.width(), self.base_height + self.log.height())
        self.worker = None

    def _format_error_message(self, error: object) -> str:
        """Return a translated, user-friendly message for *error*."""
        if isinstance(error, BaseException):
            return self._format_exception_message(error)
        return str(error)

    def _format_exception_message(self, error: BaseException) -> str:
        """Translate PPTX errors while preserving diagnostic detail."""
        if isinstance(error, PptxProviderUnavailableError):
            return tr("pptx.no_provider")
        if isinstance(error, PptxRenderingError):
            code = (error.code or "").lower()
            key = _PPTX_ERROR_KEYS_BY_CODE.get(code, "pptx_error_unknown")
            base = tr(key)
            extras: list[str] = []
            if error.detail:
                extras.append(str(error.detail))
            raw = str(error)
            if raw and raw.lower() != code and raw != base:
                extras.append(raw)
            filtered: list[str] = []
            for item in extras:
                if item and item not in filtered:
                    filtered.append(item)
            if filtered:
                return base + "\n" + "\n".join(filtered)
            return base
        return str(error)

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
            self.log.verticalScrollBar().setValue(
                self.log.verticalScrollBar().maximum()
            )
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
        cfg = self.cfg
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
        current = (cfg.get("pptx_renderer") or "auto").strip() or "auto"
        index = combo.findData(current)
        combo.setCurrentIndex(max(index, 0))
        form.addRow("PPTX Renderer", combo)

        raw_http_cfg = cfg.get("http_office")
        http_cfg: dict[str, object] = (
            dict(raw_http_cfg) if isinstance(raw_http_cfg, dict) else {}
        )

        (
            http_group,
            http_type,
            http_endpoint,
            http_timeout,
            http_verify,
            http_header_name,
            http_header_value,
            http_header_original_key,
        ) = self._create_http_office_group(http_cfg)

        form.addRow(http_group)

        def _update_http_visibility() -> None:
            http_group.setVisible(combo.currentData() == "http_office")

        combo.currentIndexChanged.connect(lambda _index: _update_http_visibility())
        _update_http_visibility()

        renderer = self._select_pptx_provider()
        if renderer is None:
            eff = QLabel(tr("pptx.no_provider"))
        else:
            eff = QLabel(type(renderer).__name__)
        form.addRow("Effective renderer", eff)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        form.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            value = combo.currentData()
            cfg["pptx_renderer"] = str(value) if value else "auto"
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
            header_name = http_header_name.text().strip()
            if http_header_original_key and (
                not header_name or header_name != http_header_original_key
            ):
                headers.pop(http_header_original_key, None)
            if header_name:
                headers[header_name] = http_header_value.text()
            http_payload: dict[str, object] = {
                "mode": http_type.currentData() or "auto",
                "endpoint": http_endpoint.text().strip(),
                "timeout_s": float(http_timeout.value()),
                "verify_tls": http_verify.isChecked(),
                "headers": headers,
            }
            cfg["http_office"] = http_payload
            save_config(cfg)

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
