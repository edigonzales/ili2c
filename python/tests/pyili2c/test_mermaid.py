"""Tests for the Mermaid class diagram renderer."""

from __future__ import annotations

from pathlib import Path

from pyili2c import AttributeDef, Cardinality, Constraint, Domain, Model, Table, Topic, TransferDescription
from pyili2c import AssociationDef, RoleDef
from pyili2c.metamodel.types import EnumerationType, TextType
from pyili2c.mermaid import render
from pyili2c.parser import parse


def build_sample_transfer_description() -> TransferDescription:
    td = TransferDescription()

    other_model = Model("ExternalModel", file_name="external.ili")
    td.addModel(other_model)
    external_table = Table("ExternalClass")
    other_model.add(external_table)

    model = Model("ExampleModel", file_name="example.ili")
    td.addModel(model)
    topic = Topic("MainTopic")
    model.add(topic)

    base = Table("BaseClass")
    attr = AttributeDef("name")
    attr.setDomain(TextType("Text"))
    attr.setCardinality(Cardinality(1, 1))
    base.addAttribute(attr)

    enumeration_domain = Domain("ColorDomain")
    enumeration_domain.setType(EnumerationType(literals=["red", "green", "blue"]))
    topic.add(enumeration_domain)

    child = Table("ChildClass")
    child.setExtending(base)
    constraint = Constraint("childConstraint")
    child.addConstraint(constraint)

    topic.addViewable(base)
    topic.addViewable(child)

    association = AssociationDef("Rel")
    left_role = RoleDef("childRole")
    left_role.setDestination(child)
    left_role.setCardinality(Cardinality(1, 1))
    association.addRole(left_role)

    right_role = RoleDef("externalRole")
    right_role.setDestination(external_table)
    right_role.setCardinality(Cardinality(0, 1))
    association.addRole(right_role)

    topic.add(association)

    return td


def test_render_mermaid_diagram() -> None:
    td = build_sample_transfer_description()
    diagram = render(td)

    expected = """classDiagram
  namespace ExampleModel__MainTopic {
    class ExampleModel.MainTopic.BaseClass[\"BaseClass\"] {
      name[1] : String
    }
    class ExampleModel.MainTopic.ChildClass[\"ChildClass\"] {
      childConstraint()
    }
    class ExampleModel.MainTopic.ColorDomain[\"ColorDomain\"] {
      <<Enumeration>>
    }
  }
  class ExternalModel.ExternalClass[\"ExternalClass\"] {
    <<External>>
  }
  ExampleModel.MainTopic.ChildClass --|> ExampleModel.MainTopic.BaseClass
  ExampleModel.MainTopic.ChildClass \"1\" -- \"0..1\" ExternalModel.ExternalClass : childRole–externalRole
"""

    assert diagram == expected


def test_render_real_world_model() -> None:
    path = Path(__file__).parent / "data" / "SO_ARP_SEin_Konfiguration_20250115_v23.ili"
    td = parse(path)
    diagram = render(td)

    assert "Handlungsraum[0..1] : Handlungsraum" in diagram
    assert "laendlich" not in diagram
    assert "Gruppen[1..*] : Gruppe" in diagram
    assert "Objektinfos[0..*] : Objektinfo" in diagram
    assert "LayerId[0..1] : String" in diagram
    assert "GeometryCHLV95_V1.MultiSurface" not in diagram
    assert "BAG OF" not in diagram
