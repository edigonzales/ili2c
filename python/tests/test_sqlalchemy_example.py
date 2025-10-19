from __future__ import annotations

import pytest


pytest.importorskip("sqlalchemy")

from ili2c.dataclasses.examples import sqlalchemy_example


def test_sqlalchemy_example_creates_database(tmp_path):
    db_path = tmp_path / "example.sqlite"
    buildings = sqlalchemy_example.run(db_path)

    assert db_path.exists()
    assert buildings, "expected at least one building"

    building_id, building = buildings[0]
    assert building_id > 0
    assert tuple(address.street for address in building.address_ref) == (
        "Hauptstrasse 1",
        "Nebenweg 5",
    )
