"""End-to-end GUI test for extracting images from a PDF."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt

from pdf_toolbox import gui

pytest_plugins = ("tests.gui.conftest_qt",)

pytestmark = [
    pytest.mark.gui,
    pytest.mark.usefixtures("force_lang_en", "temp_config_dir", "no_file_dialogs"),
]


def _find_action_item(window: gui.MainWindow, fqname: str):
    """Return the tree item associated with ``fqname``."""
    tree = window.tree
    user_role = int(Qt.ItemDataRole.UserRole)

    for index in range(tree.topLevelItemCount()):
        category = tree.topLevelItem(index)
        if category is None:
            continue
        for child_index in range(category.childCount()):
            item = category.child(child_index)
            if item is None:
                continue
            action = item.data(0, user_role)
            if action and getattr(action, "fqname", None) == fqname:
                return item
    pytest.fail(f"Action {fqname} not found in tree")


def test_pdf_to_images_via_ui(
    qtbot,
    pdf_with_image: str,
    tmp_path,
    stub_worker,
) -> None:
    """Drive the GUI to extract images from a PDF via the pdf_to_images action."""
    window = gui.MainWindow()
    qtbot.addWidget(window)
    window.show()
    try:
        item = _find_action_item(
            window,
            "pdf_toolbox.actions.pdf_images.pdf_to_images",
        )
        window.tree.setCurrentItem(item)
        rect = window.tree.visualItemRect(item)
        qtbot.mouseClick(
            window.tree.viewport(),
            Qt.MouseButton.LeftButton,
            pos=rect.center(),
        )
        assert window.current_action is not None

        input_edit = window.current_widgets["input_pdf"]
        out_dir_edit = window.current_widgets["options.out_dir"]
        assert hasattr(input_edit, "setText")
        assert hasattr(out_dir_edit, "setText")

        output_dir = tmp_path / "exported-images"
        input_edit.setText(pdf_with_image)
        out_dir_edit.setText(str(output_dir))

        window.on_run()
        qtbot.waitUntil(lambda: window.worker is None)
        qtbot.waitUntil(
            lambda: window.status_key == "done" and bool(window.log.entries()),
            timeout=3000,
        )

        assert stub_worker.starts
        assert window.log.isVisible()
        assert window.status_key == "done"
        assert window.progress.maximum() == 1
        assert window.progress.value() == 1

        log_lines = [
            line.strip()
            for entry in window.log.entries()
            for line in entry.message.splitlines()
            if line.strip()
        ]
        extracted_paths: list[Path] = []
        for line in log_lines:
            candidate = Path(line)
            if candidate.is_absolute() and candidate.exists():
                extracted_paths.append(candidate)
        assert extracted_paths, log_lines
        for path in extracted_paths:
            assert path.parent == output_dir
            assert path.stat().st_size > 0
    finally:
        window.close()
