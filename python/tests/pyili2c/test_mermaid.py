from pathlib import Path

from ili2c.pyili2c.mermaid import render
from ili2c.pyili2c.parser import parse


DATA_DIR = Path(__file__).parent / "data"


def test_render_simple_model_mermaid_output():
    td = parse(DATA_DIR / "simple.ili")

    diagram = render(td)

    expected = """classDiagram
  namespace SimpleModel__SimpleTopic {
    class SimpleModel.SimpleTopic.Building[\"Building\"] {
      AddressRef[0..*] : List<SimpleModel.Address>
    }
  }
  class SimpleModel.Address[\"Address\"] {
    <<Structure>>
    Street[0..1] : TEXT
  }
  class SimpleModel.Road[\"Road\"] {
    <<Abstract>>
    Name[0..1] : TEXT
    constraint1()
  }
  class SimpleModel.NameLength[\"NameLength\"] {
    <<Function>>
  }
"""

    assert diagram == expected


def test_render_includes_enumerations(tmp_path):
    model_text = """INTERLIS 2.4;
MODEL EnumModel =
  DOMAIN Color = (red, blue, green);
  CLASS Thing =
    Shade: Color;
  END Thing;
END EnumModel.
"""

    model_path = tmp_path / "enum_test.ili"
    model_path.write_text(model_text, encoding="utf8")

    td = parse(model_path)
    diagram = render(td)

    assert "class EnumModel.Color" in diagram
    assert "red, blue, green" in diagram


def test_testsuite_model_contains_inheritance_and_association():
    td = parse(DATA_DIR / "TestSuite_mod-0.ili")

    diagram = render(td)

    assert "TestSuite.Gebaeude2 --|> TestSuite.Gebaeude" in diagram


def test_so_arp_model_diagram_has_expected_relationships():
    td = parse(DATA_DIR / "SO_ARP_SEin_Konfiguration_20250115.ili")

    diagram = render(td)

    assert (
        "SO_ARP_SEin_Konfiguration_20250115.Grundlagen.GemeindeYYYY --|> SO_ARP_SEin_Konfiguration_20250115.GemeindeXXXX"
        in diagram
    )
    assert (
        'SO_ARP_SEin_Konfiguration_20250115.Auswertung.Fubar "0..*" -- "0..*" SO_ARP_SEin_Konfiguration_20250115.Grundlagen.GemeindeYYYY'
        in diagram
    )
