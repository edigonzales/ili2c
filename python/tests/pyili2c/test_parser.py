from pathlib import Path

from pyili2c.metamodel import (
    AssociationDef,
    Constraint,
    Domain,
    EnumerationType,
    Function,
    ListType,
    Table,
    Type,
)
from pyili2c.parser import parse


def test_parse_simple_model():
    path = Path(__file__).parent / "data" / "simple.ili"
    td = parse(path)

    models = [m for m in td.getModels() if m.getName() != "INTERLIS"]
    assert [m.getName() for m in models] == ["SimpleModel"]

    model = models[0]
    topics = model.getTopics()
    assert [t.getName() for t in topics] == ["SimpleTopic"]

    # Domains at model level
    domains = model.elements_of_type(Domain)
    assert [d.getName() for d in domains] == ["Identifier"]
    assert isinstance(domains[0].getType(), Type)

    # Functions with arguments and return types
    functions = model.elements_of_type(Function)
    assert [f.getName() for f in functions] == ["NameLength"]
    function = functions[0]
    assert [(arg.getName(), isinstance(arg.getType(), Type)) for arg in function.getArguments()] == [
        ("input", True)
    ]
    assert isinstance(function.getReturnType(), Type)
    assert function.getReturnType().getName() == "NUMERIC"

    # Root-level viewables
    root_viewables = model.elements_of_type(Table)
    assert [v.getName() for v in root_viewables] == ["Address", "Road"]
    structure = root_viewables[0]
    road = root_viewables[1]
    assert structure.isIdentifiable() is False
    assert road.isIdentifiable() is True
    assert road.isAbstract() is True

    constraints = road.elements_of_type(Constraint)
    assert [c.getName() for c in constraints] == [None]
    assert constraints[0].isMandatory() is True
    assert constraints[0].expression == "NameLength(Name)>5"

    topic = topics[0]
    classes = topic.getClasses()
    assert [c.getName() for c in classes] == ["Building"]

    building = classes[0]
    attrs = building.getAttributes()
    assert len(attrs) == 1
    attr = attrs[0]
    domain = attr.getDomain()
    assert isinstance(domain, ListType)
    element_type = domain.getElementType()
    assert isinstance(element_type, Type)
    assert element_type.getName() == "SimpleModel.Address"
    assert (domain.cardinality_min, domain.cardinality_max) == (0, -1)


def test_parse_complex_model():
    path = Path(__file__).parent / "data" / "SO_ARP_SEin_Konfiguration_20250115.ili"
    td = parse(path)

    model = td.find_model("SO_ARP_SEin_Konfiguration_20250115")
    assert model is not None

    domains = {d.getName(): d for d in model.elements_of_type(Domain)}
    assert "Status_Geschaeft" in domains
    enum_domain = domains["Status_Geschaeft"]
    enum_type = enum_domain.getType()
    assert isinstance(enum_type, EnumerationType)
    assert enum_type.getLiterals() == ["foo", "bar"]

    root_classes = {c.getName(): c for c in model.elements_of_type(Table)}
    mybase = root_classes["MyBase"]
    assert mybase.isAbstract() is True
    gemeinde = root_classes["Gemeinde"]
    assert gemeinde.getExtending() is mybase
    bfs_attr = next(a for a in gemeinde.getAttributes() if a.getName() == "BFSNr")
    assert bfs_attr.isMandatory() is True
    assert bfs_attr.getDomain().getName() == "2000..3000"

    grundlagen = next(t for t in model.getTopics() if t.getName() == "Grundlagen")
    grund_gemeinde = next(c for c in grundlagen.getClasses() if c.getName() == "Gemeinde")
    assert grund_gemeinde.getExtending() is gemeinde
    unique_exprs = sorted(c.expression for c in grund_gemeinde.getConstraints())
    assert unique_exprs == ["UNIQUE BFSNr", "UNIQUE Name"]

    assoc = next(v for v in grundlagen.elements_of_type(AssociationDef) if v.getName() == "Gemeinde_Objektinfo")
    roles = {role.getName(): role for role in assoc.getRoles()}
    assert set(roles) == {"Gemeinde_R", "Objektinfo_R"}
    gemeinde_role = roles["Gemeinde_R"]
    assert gemeinde_role.getCardinality().getMinimum() == 0
    assert gemeinde_role.getCardinality().getMaximum() == -1
    assert gemeinde_role.getDestination().getName() == "Gemeinde"

    auswertung = next(t for t in model.getTopics() if t.getName() == "Auswertung")
    gruppe = next(c for c in auswertung.getClasses() if c.getName() == "Gruppe")
    themen_attr = next(a for a in gruppe.getAttributes() if a.getName() == "Themen")
    assert isinstance(themen_attr.getDomain(), ListType)
    bag_type = themen_attr.getDomain()
    assert bag_type.isBag() is True
    assert (bag_type.cardinality_min, bag_type.cardinality_max) == (1, -1)
    element_type = bag_type.getElementType()
    assert isinstance(element_type, Type)
    assert element_type.getName().endswith("Auswertung.Thema")

    fubar_assoc = next(v for v in auswertung.elements_of_type(AssociationDef) if v.getName() == "Fubar__Gemeinde")
    gemeinde_ext_role = next(r for r in fubar_assoc.getRoles() if r.getName() == "Gemeinde_R")
    assert gemeinde_ext_role.isExternal() is True
    assert (
        gemeinde_ext_role.getDestination().getScopedName()
        == "SO_ARP_SEin_Konfiguration_20250115.Grundlagen.Gemeinde"
    )


def test_parse_model_with_imports():
    data_dir = Path(__file__).parent / "data"
    td = parse(data_dir / "modelB.ili")

    model_a = td.find_model("ModelA")
    model_b = td.find_model("ModelB")

    assert model_a is not None
    assert model_b is not None

    struct_a = next(v for v in model_a.elements_of_type(Table) if v.getName() == "StructA")
    assert struct_a.isIdentifiable() is False

    topic_b = next(t for t in model_b.getTopics() if t.getName() == "TopicB")
    class_b = next(c for c in topic_b.getClasses() if c.getName() == "ClassB")

    attr = class_b.getAttributes()[0]
    assert attr.getDomain().getName() == "ModelA.StructA"
