import hashlib
from pathlib import Path

import pytest

from ili2c.pyili2c.metamodel import Constraint, Domain, Function, ListType, Table, Type
from ili2c.pyili2c.parser import ParserSettings, parse
from ili2c.ilirepository.cache import RepositoryCache

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


def test_parse_remote_model_uses_repository(tmp_path, sample_repository):
    main_path = tmp_path / "RemoteMain.ili"
    main_path.write_text((DATA_DIR / "remote_main.ili").read_text(), encoding="utf8")

    cache = RepositoryCache(base_dir=tmp_path / "cache")
    settings = ParserSettings(repositories=[sample_repository["primary_uri"]], repository_cache=cache)

    td = parse(main_path, settings=settings)

    assert td.find_model("RepoModel") is not None


def test_parse_remote_model_traverses_connected_repository(tmp_path, sample_repository):
    main_path = tmp_path / "RemoteBFSMain.ili"
    main_path.write_text((DATA_DIR / "remote_bfs_main.ili").read_text(), encoding="utf8")

    cache = RepositoryCache(base_dir=tmp_path / "cache")
    settings = ParserSettings(repositories=[sample_repository["primary_uri"]], repository_cache=cache)

    td = parse(main_path, settings=settings)

    assert td.find_model("RepoLinkedModel") is not None


def test_parse_remote_version_specific_models(tmp_path, sample_repository):
    for filename in ["remote_version24.ili", "remote_version23.ili"]:
        (tmp_path / filename).write_text((DATA_DIR / filename).read_text(), encoding="utf8")

    cache = RepositoryCache(base_dir=tmp_path / "cache")
    settings = ParserSettings(repositories=[sample_repository["primary_uri"]], repository_cache=cache)

    td_24 = parse(tmp_path / "remote_version24.ili", settings=settings)
    assert td_24.find_model("RepoVersions").getSchemaLanguage() == "ili2_4"

    td_23 = parse(tmp_path / "remote_version23.ili", settings=settings)
    assert td_23.find_model("RepoVersions").getSchemaLanguage() == "ili2_3"


def test_parse_remote_fails_for_incompatible_schema(tmp_path, sample_repository):
    main_path = tmp_path / "RemoteLegacy.ili"
    main_path.write_text((DATA_DIR / "remote_main_v23.ili").read_text(), encoding="utf8")

    cache = RepositoryCache(base_dir=tmp_path / "cache")
    settings = ParserSettings(repositories=[sample_repository["primary_uri"]], repository_cache=cache)

    with pytest.raises(FileNotFoundError):
        parse(main_path, settings=settings)


def test_local_directory_without_index_is_checked_before_repository(tmp_path):
    main_path = tmp_path / "Main.ili"
    main_path.write_text(
        """INTERLIS 2.4;\nMODEL Main =\n  IMPORTS ModelA;\nEND Main.""",
        encoding="utf8",
    )

    local_model = tmp_path / "ModelA.ili"
    local_model.write_text(
        """INTERLIS 2.4;\nMODEL ModelA =\n  DOMAIN Identifier = TEXT;\nEND ModelA.""",
        encoding="utf8",
    )

    remote_repo = tmp_path / "remote_repo"
    remote_repo.mkdir()
    remote_model = remote_repo / "ModelA.ili"
    remote_model.write_text(
        """INTERLIS 2.4;\nMODEL ModelA =\n  DOMAIN Identifier = NUMERIC[1..10];\nEND ModelA.""",
        encoding="utf8",
    )

    (remote_repo / "ilimodels.xml").write_text(
        """<?xml version=\"1.0\" encoding=\"utf-8\"?>
<Models xmlns=\"http://www.interlis.ch/INTERLIS2.3\">
  <IliRepository20.RepositoryIndex.ModelMetadata>
    <Name>ModelA</Name>
    <SchemaLanguage>ili2_4</SchemaLanguage>
    <File>ModelA.ili</File>
    <Version>2024-01-01</Version>
    <md5>{md5}</md5>
  </IliRepository20.RepositoryIndex.ModelMetadata>
</Models>
""".format(md5=hashlib.md5(remote_model.read_bytes()).hexdigest()),
        encoding="utf8",
    )

    settings = ParserSettings(
        repositories=[str(remote_repo)],
        repository_cache=RepositoryCache(base_dir=tmp_path / "cache"),
    )

    td = parse(main_path, settings=settings)

    model_a = td.find_model("ModelA")
    assert model_a is not None

    identifier_domain = next(d for d in model_a.elements_of_type(Domain) if d.getName() == "Identifier")
    assert identifier_domain.getType().getName() == "TEXT"
