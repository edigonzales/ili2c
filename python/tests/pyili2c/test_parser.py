import threading
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from ili2c.pyili2c.metamodel import (
    AssociationDef,
    Constraint,
    Domain,
    EnumerationType,
    Function,
    ListType,
    Table,
    Type,
)
from ili2c.pyili2c.parser import ParserSettings, parse
from ili2c.ilirepository.cache import RepositoryCache


DATA_DIR = Path(__file__).parent / "data"


class _SilentHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A003 - match signature
        return


@contextmanager
def _serve_directory(directory: Path):
    handler = partial(_SilentHandler, directory=str(directory))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        thread.join()


def test_parse_simple_model():
    path = Path(__file__).parent / "data" / "simple.ili"
    td = parse(path)

    models = [m for m in td.getModels() if m.getName() != "INTERLIS"]
    assert [m.getName() for m in models] == ["SimpleModel"]

    model = models[0]
    assert model.getSchemaVersion() == "2.4"
    assert model.getSchemaLanguage() == "ili2_4"
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


def test_parse_model_with_inline_enumeration():
    path = Path(__file__).parent / "data" / "SO_ARP_SEin_Konfiguration_20250115_v23.ili"
    td = parse(path)

    model = td.find_model("SO_ARP_SEin_Konfiguration_20250115")
    assert model is not None
    assert model.getSchemaVersion() == "2.3"
    assert model.getSchemaLanguage() == "ili2_3"

    gemeinde = next(c for c in model.elements_of_type(Table) if c.getName() == "Gemeinde")
    attr = next(a for a in gemeinde.getAttributes() if a.getName() == "Handlungsraum")
    domain = attr.getDomain()
    assert isinstance(domain, EnumerationType)
    assert domain.getLiterals() == [
        "urban",
        "laendlich",
        "agglomerationsgepraegt",
    ]


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


def test_parse_model_with_unqualified_interlis_import(tmp_path):
    data_dir = Path(__file__).parent / "data"
    for name in ["GeometryCHLV95_V1.ili", "Units.ili", "CoordSys.ili"]:
        (tmp_path / name).write_text((data_dir / name).read_text(), encoding="utf8")

    settings = ParserSettings()
    settings.set_ilidirs("%ILI_DIR")
    td = parse(tmp_path / "GeometryCHLV95_V1.ili", settings=settings)

    model = td.find_model("GeometryCHLV95_V1")
    assert model is not None

    domain_names = {domain.getName() for domain in model.elements_of_type(Domain)}
    assert "MultiSurface" in domain_names


@pytest.fixture
def http_repository(tmp_path_factory):
    repo_dir = tmp_path_factory.mktemp("ilirepo")
    (repo_dir / "RepoModel.ili").write_text(
        (DATA_DIR / "RepoModel.ili").read_text(),
        encoding="utf8",
    )
    (repo_dir / "ilimodels.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<IliRepository09.RepositoryIndex xmlns="http://www.interlis.ch/INTERLIS2.3">
  <IliRepository09.RepositoryIndex.ModelMetadata>
    <Name>RepoModel</Name>
    <SchemaLanguage>ili2_4</SchemaLanguage>
    <File>RepoModel.ili</File>
    <Version>2024-01-01</Version>
  </IliRepository09.RepositoryIndex.ModelMetadata>
</IliRepository09.RepositoryIndex>
""",
        encoding="utf8",
    )

    with _serve_directory(repo_dir) as base_url:
        yield base_url


@pytest.fixture
def http_repository_graph(tmp_path_factory):
    root_dir = tmp_path_factory.mktemp("ilirepo_graph")
    primary = root_dir / "primary"
    secondary = root_dir / "secondary"
    primary.mkdir()
    secondary.mkdir()

    (secondary / "RepoLinkedModel.ili").write_text(
        (DATA_DIR / "RepoLinkedModel.ili").read_text(),
        encoding="utf8",
    )
    (secondary / "ilimodels.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<IliRepository09.RepositoryIndex xmlns="http://www.interlis.ch/INTERLIS2.3">
  <IliRepository09.RepositoryIndex.ModelMetadata>
    <Name>RepoLinkedModel</Name>
    <SchemaLanguage>ili2_4</SchemaLanguage>
    <File>RepoLinkedModel.ili</File>
    <Version>2024-03-01</Version>
  </IliRepository09.RepositoryIndex.ModelMetadata>
</IliRepository09.RepositoryIndex>
""",
        encoding="utf8",
    )
    (primary / "ilimodels.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<IliRepository09.RepositoryIndex xmlns="http://www.interlis.ch/INTERLIS2.3"/>
""",
        encoding="utf8",
    )

    with _serve_directory(root_dir) as base_url:
        secondary_url = f"{base_url}/secondary"
        (primary / "ilisite.xml").write_text(
            f"""<?xml version="1.0" encoding="UTF-8"?>
<IliSite09.RepositoryIndex xmlns="http://www.interlis.ch/INTERLIS2.3">
  <RepositoryLocation_>
    <value>{secondary_url}</value>
  </RepositoryLocation_>
</IliSite09.RepositoryIndex>
""",
            encoding="utf8",
        )
        yield f"{base_url}/primary"


@pytest.fixture
def http_repository_versions(tmp_path_factory):
    repo_dir = tmp_path_factory.mktemp("ilirepo_versions")
    for filename in ("RepoVersions_ili23.ili", "RepoVersions_ili24.ili"):
        (repo_dir / filename).write_text(
            (DATA_DIR / filename).read_text(),
            encoding="utf8",
        )
    (repo_dir / "ilimodels.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<IliRepository09.RepositoryIndex xmlns="http://www.interlis.ch/INTERLIS2.3">
  <IliRepository09.RepositoryIndex.ModelMetadata>
    <Name>RepoVersions</Name>
    <SchemaLanguage>ili2_3</SchemaLanguage>
    <File>RepoVersions_ili23.ili</File>
    <Version>2023-01-01</Version>
  </IliRepository09.RepositoryIndex.ModelMetadata>
  <IliRepository09.RepositoryIndex.ModelMetadata>
    <Name>RepoVersions</Name>
    <SchemaLanguage>ili2_4</SchemaLanguage>
    <File>RepoVersions_ili24.ili</File>
    <Version>2024-01-01</Version>
  </IliRepository09.RepositoryIndex.ModelMetadata>
</IliRepository09.RepositoryIndex>
""",
        encoding="utf8",
    )

    with _serve_directory(repo_dir) as base_url:
        yield base_url


def test_parse_import_from_repository(http_repository, tmp_path):
    cache = RepositoryCache(base_dir=tmp_path / "ilicache")
    settings = ParserSettings(repository_cache=cache)
    settings.set_ilidirs(f"%ILI_DIR;{http_repository}")

    path = tmp_path / "remote_main.ili"
    path.write_text((DATA_DIR / "remote_main.ili").read_text(), encoding="utf8")
    td = parse(path, settings=settings)

    assert td.find_model("RemoteMain") is not None
    repo_model = td.find_model("RepoModel")
    assert repo_model is not None
    domain = next(d for d in repo_model.elements_of_type(Domain) if d.getName() == "MyText")
    assert domain.getType().getName() == "TEXT*20"

    cache_dir = cache.base_dir
    repo_cache = list(cache_dir.rglob("RepoModel.ili"))
    assert repo_cache
    assert not any(p.name == "remote_main.ili" for p in cache_dir.rglob("remote_main.ili"))
    assert list(cache_dir.rglob("ilimodels.xml"))


def test_parse_import_from_repository_mismatched_version_errors(http_repository, tmp_path):
    cache = RepositoryCache(base_dir=tmp_path / "ilicache_v23")
    settings = ParserSettings(repository_cache=cache)
    settings.set_ilidirs(f"%ILI_DIR;{http_repository}")

    path = tmp_path / "remote_main_v23.ili"
    path.write_text((DATA_DIR / "remote_main_v23.ili").read_text(), encoding="utf8")

    with pytest.raises(FileNotFoundError, match="RepoModel"):
        parse(path, settings=settings)


def test_parse_import_from_connected_repository(http_repository_graph, tmp_path):
    cache = RepositoryCache(base_dir=tmp_path / "ilicache")
    settings = ParserSettings(repository_cache=cache)
    settings.set_ilidirs(f"%ILI_DIR;{http_repository_graph}")

    path = tmp_path / "remote_bfs_main.ili"
    path.write_text((DATA_DIR / "remote_bfs_main.ili").read_text(), encoding="utf8")
    td = parse(path, settings=settings)

    assert td.find_model("RemoteBFSMain") is not None
    linked_model = td.find_model("RepoLinkedModel")
    assert linked_model is not None
    domain = next(
        d for d in linked_model.elements_of_type(Domain) if d.getName() == "LinkedText"
    )
    assert domain.getType().getName() == "TEXT*10"

    cache_dir = cache.base_dir
    linked_cache = list(cache_dir.rglob("RepoLinkedModel.ili"))
    assert linked_cache
    assert all(p.is_file() for p in linked_cache)
    assert list(cache_dir.rglob("ilisite.xml"))


def test_parse_import_prefers_matching_schema(http_repository_versions, tmp_path):
    cache = RepositoryCache(base_dir=tmp_path / "ilicache_versions")
    settings = ParserSettings(repository_cache=cache)
    settings.set_ilidirs(f"%ILI_DIR;{http_repository_versions}")

    path24 = tmp_path / "remote_version24.ili"
    path24.write_text((DATA_DIR / "remote_version24.ili").read_text(), encoding="utf8")
    td24 = parse(path24, settings=settings)

    repo_model_24 = td24.find_model("RepoVersions")
    assert repo_model_24 is not None
    assert repo_model_24.getSchemaLanguage() == "ili2_4"
    domain_24 = next(
        d for d in repo_model_24.elements_of_type(Domain) if d.getName() == "RepoText"
    )
    assert domain_24.getType().getName() == "TEXT*40"

    path23 = tmp_path / "remote_version23.ili"
    path23.write_text((DATA_DIR / "remote_version23.ili").read_text(), encoding="utf8")
    td23 = parse(path23, settings=settings)

    repo_model_23 = td23.find_model("RepoVersions")
    assert repo_model_23 is not None
    assert repo_model_23.getSchemaLanguage() == "ili2_3"
    domain_23 = next(
        d for d in repo_model_23.elements_of_type(Domain) if d.getName() == "RepoText"
    )
    assert domain_23.getType().getName() == "TEXT*30"


def test_parse_import_with_local_version_mismatch_raises(tmp_path):
    path = tmp_path / "remote_main_v23.ili"
    path.write_text((DATA_DIR / "remote_main_v23.ili").read_text(), encoding="utf8")
    (tmp_path / "RepoModel.ili").write_text(
        (DATA_DIR / "RepoModel.ili").read_text(),
        encoding="utf8",
    )

    settings = ParserSettings()
    settings.set_ilidirs("%ILI_DIR")

    with pytest.raises(ValueError, match="RemoteMainLegacy"):  # importer name
        parse(path, settings=settings)


def test_parse_missing_import_raises(tmp_path):
    settings = ParserSettings()
    settings.set_ilidirs("%ILI_DIR")
    path = Path(__file__).parent / "data" / "missing_import.ili"

    with pytest.raises(FileNotFoundError, match="UnknownModel"):
        parse(path, settings=settings)
