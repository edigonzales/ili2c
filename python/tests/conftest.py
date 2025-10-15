import hashlib
import sys
from pathlib import Path
from typing import Iterable, List

import pytest

DATA_DIR = Path(__file__).resolve().parent / "pyili2c" / "data"

# Ensure the ``python`` package directory is importable when running tests from the
# repository root.
PYTHON_DIR = Path(__file__).resolve().parents[1]
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))


def _copy_model(source_name: str, destination: Path) -> tuple[Path, str]:
    source = DATA_DIR / source_name
    data = source.read_bytes()
    target = destination / source_name
    target.write_bytes(data)
    return target, hashlib.md5(data).hexdigest()


def _write_model_index(target: Path, entries: Iterable[dict]) -> None:
    lines: List[str] = [
        "<?xml version=\"1.0\" encoding=\"utf-8\"?>",
        "<Models xmlns=\"http://www.interlis.ch/INTERLIS2.3\">",
    ]
    tag_mapping = {
        "dependencies": "dependsOnModel",
        "derived_models": "derivedModel",
        "followup_models": "followupModel",
    }
    for idx, entry in enumerate(entries, start=1):
        lines.append(
            f"  <IliRepository20.RepositoryIndex.ModelMetadata TID=\"{idx}\">"
        )
        lines.append(f"    <Name>{entry['name']}</Name>")
        lines.append(f"    <SchemaLanguage>{entry['schema_language']}</SchemaLanguage>")
        lines.append(f"    <File>{entry['relative_path']}</File>")
        lines.append(f"    <Version>{entry['version']}</Version>")
        md5 = entry.get("md5")
        if md5:
            lines.append(f"    <md5>{md5}</md5>")
        for dependency_key, tag_name in tag_mapping.items():
            values = entry.get(dependency_key) or []
            if not values:
                continue
            lines.append(f"    <{tag_name}>")
            for value in values:
                lines.append("      <ModelName_>")
                lines.append(f"        <value>{value}</value>")
                lines.append("      </ModelName_>")
            lines.append(f"    </{tag_name}>")
        lines.append("  </IliRepository20.RepositoryIndex.ModelMetadata>")
    lines.append("</Models>")
    target.write_text("\n".join(lines), encoding="utf8")


def _write_ilisite(target: Path, locations: Iterable[str]) -> None:
    locations = list(locations)
    if not locations:
        return
    lines = [
        "<?xml version=\"1.0\" encoding=\"utf-8\"?>",
        "<SiteMetadata xmlns=\"http://www.interlis.ch/INTERLIS2.3\">",
        "  <Site>",
    ]
    for idx, location in enumerate(locations, start=1):
        lines.append(f"    <RepositoryLocation_ TID=\"{idx}\">")
        lines.append(f"      <value>{_normalise_repository_uri(location)}</value>")
        lines.append("    </RepositoryLocation_>")
    lines.append("  </Site>")
    lines.append("</SiteMetadata>")
    target.write_text("\n".join(lines), encoding="utf8")


def _normalise_repository_uri(uri: str) -> str:
    if not uri:
        return uri
    return uri if uri.endswith("/") else uri + "/"


def create_sample_repository(base: Path) -> dict:
    primary = base / "primary"
    secondary = base / "secondary"
    primary.mkdir(parents=True, exist_ok=True)
    secondary.mkdir(parents=True, exist_ok=True)

    digests: dict[str, str] = {}
    _, digests["RepoModel"] = _copy_model("RepoModel.ili", primary)
    _, digests["RepoLinkedModel"] = _copy_model("RepoLinkedModel.ili", secondary)
    _, digests["RepoVersions_ili24"] = _copy_model("RepoVersions_ili24.ili", primary)
    _, digests["RepoVersions_ili23"] = _copy_model("RepoVersions_ili23.ili", secondary)

    _write_model_index(
        primary / "ilimodels.xml",
        [
            {
                "name": "RepoModel",
                "schema_language": "ili2_4",
                "relative_path": "RepoModel.ili",
                "version": "2024-01-01",
                "md5": digests["RepoModel"],
            },
            {
                "name": "RepoVersions",
                "schema_language": "ili2_4",
                "relative_path": "RepoVersions_ili24.ili",
                "version": "2024-01-01",
                "md5": digests["RepoVersions_ili24"],
            },
        ],
    )

    _write_model_index(
        secondary / "ilimodels.xml",
        [
            {
                "name": "RepoLinkedModel",
                "schema_language": "ili2_4",
                "relative_path": "RepoLinkedModel.ili",
                "version": "2024-03-01",
                "md5": digests["RepoLinkedModel"],
                "dependencies": ["RepoModel"],
            },
            {
                "name": "RepoVersions",
                "schema_language": "ili2_3",
                "relative_path": "RepoVersions_ili23.ili",
                "version": "2023-01-01",
                "md5": digests["RepoVersions_ili23"],
            },
        ],
    )

    _write_ilisite(primary / "ilisite.xml", [str(secondary)])

    return {
        "primary": primary,
        "secondary": secondary,
        "primary_uri": _normalise_repository_uri(str(primary)),
        "secondary_uri": _normalise_repository_uri(str(secondary)),
        "digests": digests,
    }


@pytest.fixture(scope="module")
def sample_repository(tmp_path_factory):
    base = tmp_path_factory.mktemp("ili_repository")
    return create_sample_repository(base)
