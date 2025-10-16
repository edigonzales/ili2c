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
      AddressRef[0..*] : Address
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
    assert "Shade[0..1] : Color" in diagram
    assert "red, blue, green" not in diagram


def test_testsuite_model_contains_inheritance_and_association():
    td = parse(DATA_DIR / "TestSuite_mod-0.ili")

    diagram = render(td)

    assert (
        "TestSuite.Bodenbedeckung.Gebaeude2 --|> TestSuite.Bodenbedeckung.Gebaeude"
        in diagram
    )


def test_testsuite_model_renders_enumeration_domain_only():
    td = parse(DATA_DIR / "TestSuite_mod-0.ili")

    diagram = render(td)

    assert "class TestSuite.Farbe" in diagram
    assert "  <<Enumeration>>" in diagram
    assert "    rot.dunkel" in diagram
    assert "class TestSuite.Datum" not in diagram


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


def test_render_inline_enumeration_and_formatted_types(tmp_path):
    model_text = """INTERLIS 2.4;
MODEL Fancy =
  DOMAIN DateFmt = FORMAT BASED ON INTERLIS.GregorianDate (Year ":" Month ":" Day);
  DOMAIN Color = (
    rot (
      hell,
      dunkel
    ),
    blau
  );
  CLASS Example =
    Inline : (rot (hell, dunkel), blau);
    When : FORMAT DateFmt "2017:01:01" .. "2017:01:31";
  END Example;
END Fancy.
"""

    path = tmp_path / "diagram.ili"
    path.write_text(model_text, encoding="utf8")

    td = parse(path)
    diagram = render(td)

    assert "Inline[0..1] : rot.hell, rot.dunkel, blau" in diagram
    assert "When[0..1] : DateFmt" in diagram
    assert "class Fancy.Color" in diagram
    assert "    rot.hell" in diagram
    assert "    rot.dunkel" in diagram
    assert "    blau" in diagram


def test_geometry_types_render_with_builtin_names(tmp_path):
    model_text = """INTERLIS 2.4;
MODEL Geo =
  DOMAIN
    Vertex = COORD 0.0 .. 1000.0,
                    0.0 .. 1000.0;
  TOPIC T =
    CLASS Feature =
      AreaAttr : AREA WITH (STRAIGHTS, ARCS) VERTEX Vertex WITHOUT OVERLAPS > 0.10;
      SurfaceAttr : SURFACE WITH (STRAIGHTS) VERTEX Vertex;
      MultiAreaAttr : MULTIAREA WITH (STRAIGHTS) VERTEX Vertex;
      MultiSurfaceAttr : MULTISURFACE WITH (STRAIGHTS) VERTEX Vertex;
      PolyAttr : POLYLINE WITH (STRAIGHTS) VERTEX Vertex;
      MultiPolyAttr : MULTIPOLYLINE WITH (STRAIGHTS) VERTEX Vertex;
      CoordAttr : COORD 0.0 .. 10.0,
                         0.0 .. 10.0;
      MultiCoordAttr : MULTICOORD 0.0 .. 10.0,
                                0.0 .. 10.0;
    END Feature;
  END T;
END Geo.
"""

    model_path = tmp_path / "geom.ili"
    model_path.write_text(model_text, encoding="utf8")

    td = parse(model_path)
    diagram = render(td)

    assert "AreaAttr[0..1] : Area" in diagram
    assert "SurfaceAttr[0..1] : Surface" in diagram
    assert "MultiAreaAttr[0..1] : MultiArea" in diagram
    assert "MultiSurfaceAttr[0..1] : MultiSurface" in diagram
    assert "PolyAttr[0..1] : Polyline" in diagram
    assert "MultiPolyAttr[0..1] : MultiPolyline" in diagram
    assert "CoordAttr[0..1] : Coord" in diagram
    assert "MultiCoordAttr[0..1] : MultiCoord" in diagram


def test_blackbox_binary_types_render_with_label(tmp_path):
    model_text = """INTERLIS 2.4;
MODEL BinaryModel =
  TOPIC Main =
    CLASS Example =
      Payload : BLACKBOX BINARY;
    END Example;
  END Main;
END BinaryModel.
"""

    model_path = tmp_path / "binary_model.ili"
    model_path.write_text(model_text, encoding="utf8")

    td = parse(model_path)
    diagram = render(td)

    assert "Payload[0..1] : Blackbox Binary" in diagram
