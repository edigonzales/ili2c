import hashlib
import time
from pathlib import Path

import pytest

from ili2c.ilirepository import IliRepositoryManager
from ili2c.ilirepository.cache import RepositoryCache

REPOSITORY_URL = "https://models.interlis.ch/"


@pytest.fixture(scope="module")
def manager(tmp_path_factory):
    # Use a temporary cache so the tests do not pollute the user's cache.
    cache_dir = tmp_path_factory.mktemp("ilicache")
    cache = RepositoryCache(base_dir=cache_dir)
    mgr = IliRepositoryManager(repositories=[REPOSITORY_URL], cache=cache)
    return mgr


def test_find_model_metadata(manager):
    metadata = manager.find_model("AbstractSymbology", schema_language="ili2_4")
    assert metadata is not None
    assert metadata.version == "2020-02-20"
    assert metadata.relative_path.endswith("AbstractSymbology.ili")
    assert metadata.md5 is not None


def test_dependencies_are_parsed(manager):
    metadata = manager.find_model("RoadsExgm2ien", schema_language="ili2_4")
    assert metadata is not None
    assert "RoadsExdm2ben" in metadata.dependencies


def test_download_model_file_uses_cache(manager, tmp_path):
    path_str = manager.get_model_file("AbstractSymbology", schema_language="ili2_4")
    assert path_str is not None
    path = Path(path_str)
    assert path.exists()
    # Verify the checksum matches the metadata.
    metadata = manager.find_model("AbstractSymbology", schema_language="ili2_4")
    digest = hashlib.md5(path.read_bytes()).hexdigest()
    assert metadata.md5 == digest

    # Subsequent calls should reuse the same file without modifying it.
    mtime = path.stat().st_mtime
    time.sleep(1)
    path_str_2 = manager.get_model_file("AbstractSymbology", schema_language="ili2_4")
    assert path_str_2 == path_str
    assert path.stat().st_mtime == pytest.approx(mtime, rel=0, abs=1)


def test_list_models_filters_by_name(manager):
    models = manager.list_models(name="AbstractSymbology")
    assert any(m.schema_language == "ili2_4" for m in models)
    assert all(m.name == "AbstractSymbology" for m in models)
