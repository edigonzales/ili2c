from pathlib import Path

from urllib.parse import urlparse

from ili2c.ilirepository.cache import RepositoryCache


def test_cache_key_ignores_scheme(tmp_path):
    cache = RepositoryCache(base_dir=tmp_path)

    key = cache._cache_key(urlparse("https://models.interlis.ch"))

    assert isinstance(key, Path)
    assert key == Path("models.interlis.ch")


def test_cache_key_includes_path_components(tmp_path):
    cache = RepositoryCache(base_dir=tmp_path)

    key = cache._cache_key(urlparse("https://geo.so.ch/models/"))

    assert isinstance(key, Path)
    assert key == Path("geo.so.ch") / "models"


def test_cache_key_hashed_mode(tmp_path):
    cache = RepositoryCache(base_dir=tmp_path, hashed_filenames=True)

    key = cache._cache_key(urlparse("https://geo.so.ch/models/"))

    assert isinstance(key, str)
    assert len(key) == 32
