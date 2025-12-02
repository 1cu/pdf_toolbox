"""Dynamic form building for action parameters."""

from __future__ import annotations

import inspect
import types
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal, Union, get_args, get_origin

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

from pdf_toolbox.actions import Action, Param
from pdf_toolbox.gui.widgets import FileEdit
from pdf_toolbox.i18n import label as tr_label
from pdf_toolbox.i18n import tr

_CUSTOM_CHOICE_SENTINEL = object()


@dataclass
class ComboBoxWithSpin:
    """Container for combined ComboBox + SpinBox widgets."""

    combo_box: QComboBox
    spin_box: QSpinBox


type WidgetValue = QWidget | QLineEdit | QComboBox | QSpinBox | QDoubleSpinBox | ComboBoxWithSpin


class ActionFormBuilder:
    """Build dynamic forms for action parameters."""

    def __init__(
        self,
        form_layout: QFormLayout,
        cfg: Mapping[str, object],
    ) -> None:
        """Initialize form builder with layout and configuration.

        Args:
            form_layout: The Qt form layout to add widgets to
            cfg: Configuration dictionary for default values
        """
        self.form_layout = form_layout
        self.cfg = cfg
        self.current_widgets: dict[str, WidgetValue] = {}
        self.field_rows: dict[str, QWidget] = {}
        self.profile_help_label: QLabel | None = None
        self.profile_combo: QComboBox | None = None

    def reset_form(self) -> None:
        """Clear previously rendered widgets before rebuilding the form."""
        while self.form_layout.rowCount():
            self.form_layout.removeRow(0)
        self.current_widgets.clear()
        self.field_rows = {}
        self.profile_help_label = None
        self.profile_combo = None

    def build_form(
        self, action: Action, on_profile_change: Callable[[str], None] | None = None
    ) -> str | None:
        """Create input widgets for the given action parameters.

        Args:
            action: The action to build a form for
            on_profile_change: Optional callback for profile combo changes

        Returns:
            Initial profile value if a profile parameter was found, None otherwise
        """
        profile_initial_value: str | None = None

        for param in self._iter_form_params(action):
            profile_value = self._handle_profile_param(param, on_profile_change)
            if profile_value is not None:
                profile_initial_value = profile_value
                continue
            widget = self._create_widget_for_param(param)
            field_widget = self._add_field_to_layout(param, widget)
            self.current_widgets[param.full_name] = widget
            self._remember_field(param.full_name, field_widget)

        return profile_initial_value

    def _iter_form_params(self, action: Action) -> list[Param]:
        """Yield form parameters excluding control arguments."""
        return [p for p in action.form_params if p.name not in {"cancel", "progress_callback"}]

    def _handle_profile_param(
        self, param: Param, on_profile_change: Callable[[str], None] | None
    ) -> str | None:
        """Render the export profile selector if applicable."""
        if param.name != "export_profile":
            return None
        combo_box = QComboBox()
        combo_box.addItem(tr("gui_export_profile_custom"), userData="custom")
        combo_box.addItem(tr("gui_export_profile_miro"), userData="miro")
        saved = self.cfg.get("last_export_profile", "miro")
        if saved not in {"custom", "miro"}:
            saved = "miro"
        index = combo_box.findData(saved)
        combo_box.setCurrentIndex(max(index, 0))
        if on_profile_change:
            combo_box.currentIndexChanged.connect(
                lambda _idx, combo=combo_box: on_profile_change(
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
        return combo_box.currentData() or combo_box.currentText()

    def _create_widget_for_param(self, param: Param) -> WidgetValue:
        """Return the most appropriate widget for ``param``."""
        for factory in (
            self._maybe_create_union_widget,
            self._maybe_create_literal_widget,
            self._maybe_create_file_widget,
            self._maybe_create_numeric_widget,
            self._maybe_create_bool_widget,
        ):
            widget = factory(param)
            if widget is not None:
                return widget
        widget = QLineEdit()
        config_key = param.full_name if param.parent else param.name
        effective_default = self.cfg.get(config_key, param.default)
        if effective_default is not inspect._empty and effective_default is not None:
            widget.setText(str(effective_default))
        return widget

    def _maybe_create_union_widget(self, param: Param) -> WidgetValue | None:
        ann = param.annotation
        union_type = getattr(types, "UnionType", None)
        if get_origin(ann) not in (Union, union_type) or int not in get_args(ann):
            return None
        literal = next(
            (arg for arg in get_args(ann) if getattr(arg, "__origin__", None) is Literal),
            None,
        )
        if literal is None:
            spin_box = QSpinBox()
            spin_box.setMinimum(0)
            spin_box.setMaximum(10_000)
            config_key = param.full_name if param.parent else param.name
            effective_default = self.cfg.get(config_key, param.default)
            if isinstance(effective_default, int):
                spin_box.setValue(effective_default)
            return spin_box

        config_key = param.full_name if param.parent else param.name
        effective_default = self.cfg.get(config_key, param.default)
        if effective_default is inspect._empty:
            effective_default = None

        combo_box = QComboBox()
        spin_box = QSpinBox()
        spin_box.setMinimum(0)
        spin_box.setMaximum(10_000)
        choices = list(get_args(literal))
        for choice in choices:
            combo_box.addItem(str(choice), choice)
        combo_box.addItem(tr("gui_custom"), _CUSTOM_CHOICE_SENTINEL)
        if isinstance(effective_default, str) and effective_default in choices:
            idx = combo_box.findData(effective_default)
            combo_box.setCurrentIndex(max(idx, 0))
            spin_box.setVisible(False)
        elif isinstance(effective_default, int):
            idx = combo_box.findData(_CUSTOM_CHOICE_SENTINEL)
            combo_box.setCurrentIndex(max(idx, 0))
            spin_box.setValue(effective_default)
            spin_box.setVisible(True)
        else:
            spin_box.setVisible(combo_box.currentData() == _CUSTOM_CHOICE_SENTINEL)
        combo_box.currentIndexChanged.connect(
            lambda _i, cb=combo_box, sb=spin_box: sb.setVisible(
                cb.currentData() == _CUSTOM_CHOICE_SENTINEL
            )
        )
        return ComboBoxWithSpin(combo_box=combo_box, spin_box=spin_box)

    def _maybe_create_literal_widget(self, param: Param) -> WidgetValue | None:
        ann = param.annotation
        if getattr(ann, "__origin__", None) is not Literal:
            return None
        combo_box = QComboBox()
        choices = list(get_args(ann))
        combo_box.addItems(choices)
        config_key = param.full_name if param.parent else param.name
        effective_default = self.cfg.get(config_key, param.default)
        if isinstance(effective_default, str) and effective_default in choices:
            combo_box.setCurrentText(effective_default)
        return combo_box

    def _maybe_create_file_widget(self, param: Param) -> WidgetValue | None:
        lower = param.name.lower()
        cfg_dict = dict(self.cfg)
        if lower in {"input_pdf", "input_pptx", "input_path", "pptx_path", "path"}:
            return FileEdit(cfg_dict)
        if lower in {"out_dir", "output_dir"}:
            return FileEdit(cfg_dict, directory=True)
        if lower in {"paths", "files"}:
            return FileEdit(cfg_dict, multi=True)
        return None

    def _maybe_create_numeric_widget(self, param: Param) -> WidgetValue | None:
        lower = param.name.lower()
        if lower == "max_size_mb":
            double_spin = QDoubleSpinBox()
            double_spin.setMinimum(0)
            double_spin.setMaximum(10_000)
            return double_spin
        if lower in {"split_pages", "pages_per_file"}:
            spin_box = QSpinBox()
            spin_box.setMinimum(1)
            spin_box.setMaximum(9999)
            config_key = param.full_name if param.parent else param.name
            default = self.cfg.get(config_key, param.default)
            if isinstance(default, int):
                spin_box.setValue(default)
            return spin_box
        return None

    def _maybe_create_bool_widget(self, param: Param) -> WidgetValue | None:
        config_key = param.full_name if param.parent else param.name
        effective_default = self.cfg.get(config_key, param.default)
        if isinstance(effective_default, bool):
            check_box = QCheckBox()
            check_box.setChecked(effective_default)
            return check_box
        return None

    def _add_field_to_layout(self, param: Param, widget: WidgetValue) -> QWidget:
        """Insert ``widget`` into the form layout and return the visible QWidget."""
        if isinstance(widget, ComboBoxWithSpin):
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(widget.combo_box)
            layout.addWidget(widget.spin_box)
            layout.setStretch(0, 1)
            self.form_layout.addRow(self._pretty_label(param.name), container)
            return container
        if isinstance(widget, FileEdit):
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
            return container
        self.form_layout.addRow(self._pretty_label(param.name), widget)
        return widget

    def _pretty_label(self, name: str) -> str:
        """Return a user-friendly label for a parameter name."""
        words: list[str] = []
        for part in name.split("_"):
            if part.upper() in {"PDF", "PPTX", "PNG", "DPI", "MB"}:
                words.append(part.upper())
            elif words:
                words.append(part)
            else:
                words.append(part.capitalize())
        return " ".join(words)

    def _remember_field(self, full_name: str, widget: QWidget) -> None:
        """Track the widget for the given parameter."""
        self.field_rows[full_name] = widget

    def collect_args(self, action: Action) -> dict[str, Any]:
        """Gather user input from the form into keyword arguments."""
        params = {param.full_name: param for param in action.form_params}
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
        for dc_name, dc_type in action.dataclass_params.items():
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
        """Return the dictionary and key where this parameter's value should be stored."""
        if param and param.parent:
            if param.parent not in dataclass_values:
                dataclass_values[param.parent] = {}
            return dataclass_values[param.parent], param.name
        key = param.name if param else full_name
        return kwargs, key

    def _extract_combo_with_spin_value(self, widget: ComboBoxWithSpin) -> Any:
        """Extract value from ComboBoxWithSpin widget."""
        data = widget.combo_box.currentData()
        return widget.spin_box.value() if data == _CUSTOM_CHOICE_SENTINEL else data

    def _extract_combo_value(self, widget: QComboBox, optional: bool) -> Any:
        """Extract value from QComboBox widget."""
        data = widget.currentData()
        if data is not None:
            return data
        text = widget.currentText()
        return text if (text or not optional) else None

    def _extract_file_edit_value(self, widget: FileEdit, optional: bool, label_key: str) -> Any:
        """Extract value from FileEdit widget."""
        value = widget.text().strip()
        if widget.multi:
            paths = [p for p in value.split(";") if p]
            if not paths and not optional:
                raise ValueError(tr("field_cannot_be_empty", field=tr_label(label_key)))
            return paths if paths else None
        if not value and not optional:
            raise ValueError(tr("field_cannot_be_empty", field=tr_label(label_key)))
        return value if value else None

    def _assign_widget_value(
        self,
        widget: WidgetValue,
        *,
        target_store: dict[str, Any],
        target_key: str,
        optional: bool,
        label_key: str,
    ) -> None:
        """Extract value from widget and assign to target_store[target_key]."""
        value: Any
        if isinstance(widget, ComboBoxWithSpin):
            value = self._extract_combo_with_spin_value(widget)
        elif isinstance(widget, QComboBox):
            value = self._extract_combo_value(widget, optional)
        elif isinstance(widget, FileEdit):
            value = self._extract_file_edit_value(widget, optional, label_key)
        elif isinstance(widget, QCheckBox):
            value = widget.isChecked()
        elif isinstance(widget, QSpinBox):
            val_int = int(widget.value())
            value = None if (optional and val_int == 0) else val_int
        elif isinstance(widget, QDoubleSpinBox):
            val_float = float(widget.value())
            value = None if (optional and val_float == 0) else val_float
        elif isinstance(widget, QLineEdit):
            text = widget.text().strip()
            value = text if (text or not optional) else None
        else:
            text = str(widget.property("text") or "").strip()
            value = text if (text or not optional) else None

        target_store[target_key] = value


__all__ = ["ActionFormBuilder", "ComboBoxWithSpin", "_CUSTOM_CHOICE_SENTINEL"]
