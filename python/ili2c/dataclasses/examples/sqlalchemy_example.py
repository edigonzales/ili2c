"""Runnable SQLAlchemy example for generated INTERLIS dataclasses."""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, fields
from pathlib import Path
from types import ModuleType
from typing import Iterable

from ...pyili2c.parser import parse
from ..generator import DataclassGenerator

try:  # pragma: no cover - exercised indirectly via tests
    from sqlalchemy import (
        Boolean,
        Column,
        Float,
        ForeignKey,
        Integer,
        MetaData,
        String,
        Table,
        Text,
        create_engine,
        select,
    )
    from sqlalchemy.engine import URL
except ImportError:  # pragma: no cover - handled in ``_require_sqlalchemy``
    SQLALCHEMY_AVAILABLE = False
else:
    SQLALCHEMY_AVAILABLE = True


def _require_sqlalchemy() -> None:
    """Ensure SQLAlchemy is available before running the example."""

    if not SQLALCHEMY_AVAILABLE:
        raise RuntimeError(
            "SQLAlchemy is required for this example. "
            "Install it with `pip install ili2c-python[examples]` or `pip install sqlalchemy`."
        )


DATA_DIR = Path(__file__).resolve().parent / "data"
MODEL_PATH = DATA_DIR / "simple.ili"


@dataclass(frozen=True)
class AssociationMapping:
    """Description of a LIST attribute stored in a separate association table."""

    table: Table
    target_cls: type


def _load_dataclass_module(model_path: Path) -> ModuleType:
    """Parse *model_path* and return an in-memory module with generated dataclasses."""

    model = parse(model_path).getModels()[0]
    source = DataclassGenerator(model).build_module()
    module = ModuleType("generated_model")
    sys.modules[module.__name__] = module
    exec(source, module.__dict__)
    return module


def _python_type_to_sqlalchemy(field_info: dict) -> type:
    """Return a SQLAlchemy column type that matches the INTERLIS field description."""

    python_type = field_info.get("python_type")
    if python_type == "int":
        return Integer
    if python_type == "float":
        return Float

    if field_info.get("alias_kind") == "boolean":
        return Boolean

    max_length = field_info.get("max_length")
    if max_length:
        return String(max_length)
    return Text


def _build_sqlalchemy_metadata(module: ModuleType) -> tuple[MetaData, dict[type, Table], dict[tuple[type, str], AssociationMapping]]:
    """Create SQLAlchemy ``MetaData`` objects for all non-abstract classes."""

    _require_sqlalchemy()

    metadata = MetaData()
    tables: dict[type, Table] = {}
    bag_specs: dict[tuple[type, str], dict] = {}
    classes_by_ili_name: dict[str, type] = {}

    for class_name in getattr(module, "__all__", []):
        cls = getattr(module, class_name)
        meta = getattr(cls, "Meta")
        classes_by_ili_name[meta.ili_name] = cls

    for class_name in getattr(module, "__all__", []):
        cls = getattr(module, class_name)
        meta = getattr(cls, "Meta")
        if meta.abstract:
            continue

        columns = [Column("id", Integer, primary_key=True)]
        for field in fields(cls):
            info = field.metadata["ili"]
            if info["ili_type"] == "ListType":
                bag_specs[(cls, field.name)] = info
                continue

            column_type = _python_type_to_sqlalchemy(info)
            columns.append(Column(field.name, column_type, nullable=not info["mandatory"]))

        table_name = meta.ili_name.replace(".", "_").lower()
        table = Table(table_name, metadata, *columns)
        tables[cls] = table

    bag_tables: dict[tuple[type, str], AssociationMapping] = {}
    for (cls, field_name), info in bag_specs.items():
        parent_table = tables[cls]
        target_cls = classes_by_ili_name[info["items"]["qualified_target"]]
        target_table = tables[target_cls]
        association_name = f"{parent_table.name}_{field_name}"
        association_table = Table(
            association_name,
            metadata,
            Column("parent_id", ForeignKey(parent_table.c.id), primary_key=True),
            Column("position", Integer, primary_key=True),
            Column("target_id", ForeignKey(target_table.c.id), nullable=False),
        )
        bag_tables[(cls, field_name)] = AssociationMapping(table=association_table, target_cls=target_cls)

    return metadata, tables, bag_tables


def _seed_sample_data(engine, module: ModuleType, tables: dict[type, Table], bag_tables: dict[tuple[type, str], AssociationMapping]) -> None:
    """Populate the SQLite database with a single building and two addresses."""

    _require_sqlalchemy()

    address_cls = getattr(module, "Address")
    building_cls = getattr(module, "Building")

    building = building_cls(
        address_ref=(
            address_cls(street="Hauptstrasse 1"),
            address_cls(street="Nebenweg 5"),
        )
    )

    address_table = tables[address_cls]
    building_table = tables[building_cls]
    association = bag_tables[(building_cls, "address_ref")].table

    with engine.begin() as conn:
        address_ids: list[int] = []
        for address in building.address_ref:
            result = conn.execute(address_table.insert().values(street=address.street))
            address_ids.append(result.inserted_primary_key[0])

        result = conn.execute(building_table.insert())
        building_id = result.inserted_primary_key[0]

        for position, address_id in enumerate(address_ids):
            conn.execute(
                association.insert().values(
                    parent_id=building_id,
                    position=position,
                    target_id=address_id,
                )
            )


def _load_buildings(engine, module: ModuleType, tables: dict[type, Table], bag_tables: dict[tuple[type, str], AssociationMapping]) -> list[tuple[int, object]]:
    """Return the stored buildings together with their ``Address`` dataclasses."""

    _require_sqlalchemy()

    building_cls = getattr(module, "Building")
    address_cls = getattr(module, "Address")

    building_table = tables[building_cls]
    address_table = tables[address_cls]
    association = bag_tables[(building_cls, "address_ref")].table

    stmt = (
        select(
            building_table.c.id.label("building_id"),
            association.c.position,
            address_table.c.street,
        )
        .join(association, association.c.parent_id == building_table.c.id)
        .join(address_table, association.c.target_id == address_table.c.id)
        .order_by("building_id", association.c.position)
    )

    buildings: list[tuple[int, object]] = []
    current_id: int | None = None
    current_addresses: list[object] = []

    with engine.connect() as conn:
        for row in conn.execute(stmt).mappings():
            building_id = row["building_id"]
            if current_id is None:
                current_id = building_id
            if building_id != current_id:
                buildings.append((current_id, building_cls(address_ref=tuple(current_addresses))))
                current_addresses = []
                current_id = building_id

            current_addresses.append(address_cls(street=row["street"]))

    if current_id is not None:
        buildings.append((current_id, building_cls(address_ref=tuple(current_addresses))))

    return buildings


def run(database_path: str | Path = Path("sqlalchemy_example.sqlite")) -> list[tuple[int, object]]:
    """Create ``database_path`` and return persisted buildings.

    The function generates dataclasses for :mod:`SimpleModel` on the fly,
    reflects them into SQLAlchemy metadata, seeds a single building, and
    finally returns the building together with its addresses as dataclasses.
    """

    _require_sqlalchemy()

    module = _load_dataclass_module(MODEL_PATH)
    metadata, tables, bag_tables = _build_sqlalchemy_metadata(module)

    db_path = Path(database_path).resolve()
    engine = create_engine(URL.create("sqlite+pysqlite", database=str(db_path)))

    metadata.create_all(engine)
    _seed_sample_data(engine, module, tables, bag_tables)
    return _load_buildings(engine, module, tables, bag_tables)


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("sqlalchemy_example.sqlite"),
        help="Path to the SQLite database that should be created",
    )
    args = parser.parse_args(argv)

    buildings = run(args.database)
    print(f"Created {len(buildings)} building(s) in {args.database}")
    for building_id, building in buildings:
        streets = ", ".join(address.street for address in building.address_ref)
        print(f"  Building #{building_id}: {streets}")


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    main()
