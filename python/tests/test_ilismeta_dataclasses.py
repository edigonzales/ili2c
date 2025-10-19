from __future__ import annotations

from pathlib import Path

from ili2c.dataclasses.generator import generate_model_dataclasses
from ili2c.dataclasses.ilismeta16 import MetaElement, UniqueConstraint


DATA_DIR = Path(__file__).resolve().parent / "pyili2c" / "data"


def test_ilismeta16_snapshot(tmp_path):
    ili_path = Path(__file__).resolve().parents[2] / "standard" / "IlisMeta16.ili"
    generated = generate_model_dataclasses(ili_path)
    stored = Path(__file__).resolve().parents[1] / "ili2c" / "dataclasses" / "ilismeta16.py"
    assert stored.read_text() == generated + "\n"


def test_metaelement_metadata():
    documentation_field = MetaElement.__dataclass_fields__["documentation"]
    info = documentation_field.metadata["ili"]
    assert info["ili_type"] == "ListType"
    assert info["items"]["target"] == "DocText"
    assert info["cardinality"] == {"min": 0, "max": None}


def test_metaelement_tid_field():
    tid_field = MetaElement.__dataclass_fields__["tid"]
    assert tid_field.type == "str | None"
    assert tid_field.default is None
    info = tid_field.metadata["ili"]
    assert info["name"] == "TID"
    assert info["identifier"] is True
    assert info["identifier_category"] == "oid"
    assert info["alias"] == "IlisMeta16.MetaElemOID"


def test_unique_constraint_literals():
    kind_field = UniqueConstraint.__dataclass_fields__["kind"]
    assert kind_field.type == "Literal['GlobalU', 'BasketU', 'LocalU']"
    kind_info = kind_field.metadata["ili"]
    assert kind_info["literals"] == ["GlobalU", "BasketU", "LocalU"]


def test_generate_empty_model_module_header_only():
    module_text = generate_model_dataclasses(DATA_DIR / "Foo.ili")
    assert "__all__ = []" in module_text
    assert "@dataclass" not in module_text


def test_generate_model_level_tables_included():
    module_text = generate_model_dataclasses(DATA_DIR / "simple.ili")
    assert "class Address:" in module_text
    assert "class Road:" in module_text
    assert "'qualified_target': 'SimpleModel.Address'" in module_text


def test_generate_model_level_default_tid():
    module_text = generate_model_dataclasses(DATA_DIR / "simple.ili")
    assert "tid: str | None" in module_text
    assert "'alias': 'INTERLIS.ANYOID'" in module_text
    assert "'identifier_kind': 'text'" in module_text


def test_model_level_structure_topic_none():
    module_text = generate_model_dataclasses(DATA_DIR / "modelA.ili")
    assert "class StructA:" in module_text
    assert "topic = None" in module_text
    assert "'topic': None" in module_text


def test_generate_testsuite_literals_and_bag_metadata():
    module_text = generate_model_dataclasses(DATA_DIR / "TestSuite_mod-0.ili")
    assert "Literal['A', 'B', 'C']" in module_text
    assert "'is_bag': True" in module_text


def test_identifier_fields_render_as_strings():
    module_text = generate_model_dataclasses(DATA_DIR / "TestSuite_mod-0.ili")
    assert "art_uuid: str | None" in module_text
    assert "art_standard_id: str | None" in module_text
    assert "text_id: str | None" in module_text
    assert "'alias_kind': 'oid'" in module_text
    assert "'identifier_category': 'oid'" in module_text
    assert "'identifier_kind': 'text'" in module_text


def test_generate_so_arp_reference_metadata():
    module_text = generate_model_dataclasses(
        DATA_DIR / "SO_ARP_SEin_Konfiguration_20250115.ili"
    )
    assert "SO_ARP_SEin_Konfiguration_20250115.Grundlagen.Objektinfo" in module_text
    assert "Literal['rot', 'gruen']" in module_text
