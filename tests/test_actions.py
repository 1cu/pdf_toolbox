from pdf_toolbox.actions import list_actions


def test_registry_filters_internal_functions():
    actions = list_actions()
    fqnames = {a.fqname for a in actions}
    assert "pdf_toolbox.actions.list_actions" not in fqnames
    assert "pdf_toolbox.gui.load_config" not in fqnames


def test_decorator_preserves_category():
    actions = list_actions()
    jpeg = next(a for a in actions if a.fqname == "pdf_toolbox.jpeg.pdf_to_jpegs")
    assert jpeg.category == "PDF"
