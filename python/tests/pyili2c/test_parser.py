from pathlib import Path

import pytest

from ili2c.pyili2c.metamodel import Constraint, Domain, Function, ListType, Table, Type
from ili2c.pyili2c.parser import ParserSettings, parse

DATA_DIR = Path(__file__).parent / "data"


def test_parse_simple_model():
    td = parse(DATA_DIR / "simple.ili")

    models = [m for m in td.getModels() if m.getName() != "INTERLIS"]
    assert [m.getName() for m in models] == ["SimpleModel"]

    model = models[0]
    assert model.getSchemaVersion() == "2.4"
    assert model.getSchemaLanguage() == "ili2_4"

    domains = model.elements_of_type(Domain)
    assert [d.getName() for d in domains] == ["Identifier"]
    assert isinstance(domains[0].getType(), Type)
    assert domains[0].getType().getName() == "TEXT"

    functions = model.elements_of_type(Function)
    assert [f.getName() for f in functions] == ["NameLength"]
    function = functions[0]
    assert [(arg.getName(), arg.getType().getName()) for arg in function.getArguments()] == [("input", "TEXT")]
    assert function.getReturnType().getName() == "NUMERIC"

    structures = [t for t in model.elements_of_type(Table) if t.isIdentifiable() is False]
    assert [s.getName() for s in structures] == ["Address"]

    classes = [t for t in model.elements_of_type(Table) if t.isIdentifiable() is True]
    road = next(c for c in classes if c.getName() == "Road")
    assert road.isAbstract() is True
    constraints = road.elements_of_type(Constraint)
    assert len(constraints) == 1
    assert constraints[0].isMandatory() is True
    assert constraints[0].expression == "NameLength(Name)>5"

    topic = model.getTopics()[0]
    building = topic.getClasses()[0]
    attr = building.getAttributes()[0]
    domain = attr.getDomain()
    assert isinstance(domain, ListType)
    assert domain.cardinality_min == 0
    assert domain.cardinality_max == -1
    assert domain.getElementType().getName() == "SimpleModel.Address"


def test_parse_model_with_imports(tmp_path):
    for name in ["modelA.ili", "modelB.ili"]:
        (tmp_path / name).write_text((DATA_DIR / name).read_text(), encoding="utf8")

    td = parse(tmp_path / "modelB.ili")

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


def test_parse_missing_import_raises(tmp_path):
    (tmp_path / "missing.ili").write_text(
        """INTERLIS 2.4;\nMODEL Missing =\n  IMPORTS DoesNotExist;\nEND Missing.""",
        encoding="utf8",
    )

    with pytest.raises(FileNotFoundError):
        parse(tmp_path / "missing.ili")


def test_parser_settings_support_ilidirs(tmp_path):
    (tmp_path / "ModelA.ili").write_text((DATA_DIR / "modelA.ili").read_text(), encoding="utf8")
    (tmp_path / "Main.ili").write_text(
        """INTERLIS 2.4;\nMODEL Main =\n  IMPORTS ModelA;\nEND Main.""",
        encoding="utf8",
    )

    settings = ParserSettings()
    settings.set_ilidirs(str(tmp_path))

    td = parse(tmp_path / "Main.ili", settings=settings)
    assert td.find_model("ModelA") is not None
