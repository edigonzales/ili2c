from __future__ import annotations

from ili2c.dataclasses.examples import ui_scaffolding_example


def test_ui_scaffolding_example_creates_html(tmp_path):
    output = tmp_path / "ui.html"
    html = ui_scaffolding_example.run(output)

    assert output.exists()
    assert "INTERLIS UI scaffolding" in html
    assert "Building" in html
    assert "data-field=\"address_ref\"" in html
