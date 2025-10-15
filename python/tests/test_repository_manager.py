import hashlib
from pathlib import Path

import pytest

from ili2c.ilirepository import IliRepositoryManager
from ili2c.ilirepository.cache import RepositoryCache
from ili2c.ilirepository.models import ModelMetadata, _normalise_repository_uri


@pytest.fixture(scope="module")
def manager(sample_repository, tmp_path_factory):
    cache_dir = tmp_path_factory.mktemp("ilicache")
    cache = RepositoryCache(base_dir=cache_dir)
    repositories = [sample_repository["primary_uri"]]
    return IliRepositoryManager(repositories=repositories, cache=cache, meta_ttl=0, model_ttl=0)


def test_find_model_metadata(manager, sample_repository):
    metadata = manager.find_model("RepoModel", schema_language="ili2_4")
    assert metadata is not None
    assert metadata.repository_uri == sample_repository["primary_uri"]
    assert metadata.version == "2024-01-01"


def test_dependencies_are_parsed(manager):
    metadata = manager.find_model("RepoLinkedModel", schema_language="ili2_4")
    assert metadata is not None
    assert metadata.dependencies == ["RepoModel"]


def test_get_model_file_returns_path(manager, sample_repository):
    path_str = manager.get_model_file("RepoModel", schema_language="ili2_4")
    assert path_str is not None
    path = Path(path_str)
    assert path.exists()
    digest = hashlib.md5(path.read_bytes()).hexdigest()
    assert digest == sample_repository["digests"]["RepoModel"]


def test_list_models_filters_by_name(manager):
    models = manager.list_models(name="RepoModel")
    assert len(models) == 1
    assert models[0].name == "RepoModel"


def test_find_model_across_connected_repositories(manager, sample_repository):
    metadata = manager.find_model("RepoLinkedModel", schema_language="ili2_4")
    assert metadata is not None
    assert metadata.repository_uri == sample_repository["secondary_uri"]


def test_get_model_file_from_connected_repository(manager, sample_repository):
    path = manager.get_model_file("RepoLinkedModel", schema_language="ili2_4")
    assert path is not None
    assert Path(path).exists()
    digest = hashlib.md5(Path(path).read_bytes()).hexdigest()
    assert digest == sample_repository["digests"]["RepoLinkedModel"]


def test_schema_specific_lookup_returns_correct_version(manager, sample_repository):
    latest = manager.find_model("RepoVersions")
    assert latest is not None
    assert latest.schema_language == "ili2_4"

    legacy = manager.find_model("RepoVersions", schema_language="ili2_3")
    assert legacy is not None
    assert legacy.repository_uri == sample_repository["secondary_uri"]


def test_find_model_short_circuits_when_schema_is_known():
    class DummyAccess:
        def __init__(self):
            self.calls = []
            self._graph = {
                _normalise_repository_uri("https://root.example/"): [
                    "https://first.example/",
                    "https://second.example/",
                ],
                _normalise_repository_uri("https://first.example/"): [],
                _normalise_repository_uri("https://second.example/"): [],
            }
            self._models = {
                _normalise_repository_uri("https://root.example/"): [],
                _normalise_repository_uri("https://first.example/"): [
                    ModelMetadata(
                        name="Demo",
                        schema_language="ili2_4",
                        relative_path="Demo.ili",
                        version="2024-01-01",
                        repository_uri="https://first.example/",
                    )
                ],
                _normalise_repository_uri("https://second.example/"): [
                    ModelMetadata(
                        name="Demo",
                        schema_language="ili2_4",
                        relative_path="Demo.ili",
                        version="2024-01-02",
                        repository_uri="https://second.example/",
                    )
                ],
            }

        def get_models(self, repository_uri):
            uri = _normalise_repository_uri(repository_uri)
            self.calls.append(uri)
            return list(self._models.get(uri, []))

        def get_connected_repositories(self, repository_uri):
            uri = _normalise_repository_uri(repository_uri)
            return list(self._graph.get(uri, []))

    manager = IliRepositoryManager(repositories=["https://root.example/"])
    dummy_access = DummyAccess()
    manager.access = dummy_access

    metadata = manager.find_model("Demo", schema_language="ili2_4")

    assert metadata is not None
    assert metadata.repository_uri == _normalise_repository_uri("https://first.example/")
    assert dummy_access.calls == [
        _normalise_repository_uri("https://root.example/"),
        _normalise_repository_uri("https://first.example/"),
    ]


@pytest.mark.network
def test_find_dmav_model_from_default_repository(tmp_path):
    cache = RepositoryCache(base_dir=tmp_path / "ilicache")
    manager = IliRepositoryManager(cache=cache, meta_ttl=0, model_ttl=0)

    metadata = manager.find_model("DMAV_Grundstuecke_V1_0", schema_language="ili2_4")

    assert metadata is not None
    assert metadata.repository_uri.rstrip("/") in {
        "http://models.geo.admin.ch",
        "https://models.geo.admin.ch",
    }
