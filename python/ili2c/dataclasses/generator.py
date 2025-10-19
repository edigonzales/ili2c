"""Utilities to generate Python dataclasses from INTERLIS models."""

from __future__ import annotations

from dataclasses import dataclass
import keyword
import pprint
import re
from pathlib import Path
from typing import Any, Mapping

from ..pyili2c.metamodel import (
    Attribute,
    Domain,
    EnumerationType,
    ListType,
    Model,
    NumericType,
    ObjectType,
    ReferenceType,
    Table,
    TextOIDType,
    TextType,
    Type,
    TypeAlias,
)
from ..pyili2c.parser import parse


_SNAKE_CASE_REGEX_1 = re.compile("(.)([A-Z][a-z]+)")
_SNAKE_CASE_REGEX_2 = re.compile("([a-z0-9])([A-Z])")


@dataclass
class FieldSpec:
    name: str
    type_hint: str
    metadata: Mapping[str, Any]
    default: str | None
    default_factory: str | None
    imports: set[str]


@dataclass
class ClassSpec:
    name: str
    scope: str | None
    topic: str | None
    kind: str
    abstract: bool
    base: str | None
    fields: list[FieldSpec]

    @property
    def qualified_name(self) -> str:
        if self.scope:
            return f"{self.scope}.{self.name}"
        return self.name


@dataclass
class TypeInfo:
    type_hint: str
    metadata: Mapping[str, Any]
    default: str | None
    default_factory: str | None
    imports: set[str]


class DataclassGenerator:
    """Convert a parsed :class:`~ili2c.pyili2c.metamodel.Model` into dataclasses."""

    _NUMERIC_ALIASES = {
        "AxisInd": (1, 3),
        "Code": (0, 255),
        "LengthRange": (1, 2147483647),
        "MultRange": (0, 2147483647),
    }

    _TEXT_ALIASES = {
        "LanguageCode": 5,
    }

    _BOOLEAN_ALIASES = {"BOOLEAN"}

    _IDENTIFIER_ALIASES: dict[str, tuple[str, dict[str, Any]]] = {
        "ANYOID": (
            "oid",
            {
                "python_type": "str",
                "identifier_kind": "text",
            },
        ),
        "UUIDOID": (
            "oid",
            {
                "python_type": "str",
                "identifier_kind": "text",
                "max_length": 36,
            },
        ),
        "STANDARDOID": (
            "oid",
            {
                "python_type": "str",
                "identifier_kind": "text",
                "max_length": 16,
            },
        ),
        "I32OID": (
            "oid",
            {
                "python_type": "int",
                "identifier_kind": "numeric",
                "minimum": 0,
                "maximum": 2147483647,
            },
        ),
        "TID": (
            "tid",
            {
                "python_type": "str",
                "identifier_kind": "text",
            },
        ),
    }

    def __init__(self, model: Model) -> None:
        self.model = model
        self.model_name = model.getName() or ""
        self._structures: set[str] = set()
        self._classes: set[str] = set()
        self._full_names: dict[str, str] = {}
        self._domains: dict[str, Domain] = {}

        qualified_model = self.model_name
        for table in model.getTables():
            name = table.getName() or ""
            if not name:
                continue
            kind = (table.getKind() or "").lower()
            if kind == "structure":
                self._structures.add(name)
            else:
                self._classes.add(name)
            self._full_names[name] = f"{qualified_model}.{name}" if qualified_model else name

        for topic in model.getTopics():
            topic_name = topic.getName() or ""
            qualified_topic = f"{self.model_name}.{topic_name}" if topic_name else self.model_name
            for struct in topic.getStructures():
                name = struct.getName() or ""
                self._structures.add(name)
                self._full_names[name] = f"{qualified_topic}.{name}" if name else qualified_topic
            for cls in topic.getClasses():
                name = cls.getName() or ""
                self._classes.add(name)
                self._full_names[name] = f"{qualified_topic}.{name}" if name else qualified_topic

        for domain in model.elements_of_type(Domain):
            name = domain.getName() or ""
            scoped = domain.getScopedName()
            if name and name not in self._domains:
                self._domains[name] = domain
            if scoped and scoped not in self._domains:
                self._domains[scoped] = domain

    # ------------------------------------------------------------------
    def build_module(self) -> str:
        specs: list[ClassSpec] = []
        for table in self.model.getTables():
            name = table.getName() or ""
            if not name:
                continue
            kind = (table.getKind() or "").lower()
            kind_label = "structure" if kind == "structure" else "class"
            specs.append(
                self._build_class_spec(
                    table,
                    scope=self.model_name or None,
                    topic=None,
                    kind=kind_label,
                )
            )

        for topic in self.model.getTopics():
            topic_name = topic.getName() or ""
            qualified_topic = f"{self.model_name}.{topic_name}" if topic_name else self.model_name
            for struct in topic.getStructures():
                specs.append(
                    self._build_class_spec(
                        struct,
                        scope=qualified_topic or None,
                        topic=qualified_topic or None,
                        kind="structure",
                    )
                )
            for cls in topic.getClasses():
                specs.append(
                    self._build_class_spec(
                        cls,
                        scope=qualified_topic or None,
                        topic=qualified_topic or None,
                        kind="class",
                    )
                )

        imports: set[str] = set()
        for spec in specs:
            for field in spec.fields:
                imports.update(field.imports)
        import_lines: list[str] = []
        if imports:
            joined = ", ".join(sorted(imports))
            import_lines.append(f"from typing import {joined}")

        lines: list[str] = [
            "\"\"\"Dataclasses mirroring the IlisMeta16 INTERLIS metamodel.",
            "",
            "This file was generated by :mod:`ili2c.dataclasses.generator`.",
            "Do not edit manually.",
            "\"\"\"",
            "from __future__ import annotations",
            "",
            "from dataclasses import dataclass, field",
        ]
        lines.extend(import_lines)
        lines.append("")

        for spec in specs:
            lines.extend(self._render_class(spec))
            lines.append("")

        export_names = ", ".join(f'"{spec.name}"' for spec in specs)
        lines.append(f"__all__ = [{export_names}]")
        lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    def _build_class_spec(
        self,
        table: Table,
        *,
        scope: str | None,
        topic: str | None,
        kind: str,
    ) -> ClassSpec:
        base = table.getExtending().getName() if table.getExtending() else None
        abstract = table.isAbstract() if hasattr(table, "isAbstract") else False
        used_names: set[str] = set()
        fields: list[FieldSpec] = []
        tid_field = self._build_tid_field_spec(table, topic=topic, used_names=used_names)
        if tid_field:
            fields.append(tid_field)
        for attr in table.getAttributes():
            field_name = self._python_name(attr.getName() or "", used=used_names)
            type_info = self._build_type_info(attr)
            metadata = {
                "ili": {
                    "model": self.model_name,
                    "topic": topic,
                    "name": attr.getName(),
                    "mandatory": attr.isMandatory(),
                    **type_info.metadata,
                }
            }
            fields.append(
                FieldSpec(
                    name=field_name,
                    type_hint=type_info.type_hint,
                    metadata=metadata,
                    default=type_info.default,
                    default_factory=type_info.default_factory,
                    imports=type_info.imports,
                )
            )
        return ClassSpec(
            name=table.getName() or "",
            scope=scope,
            topic=topic,
            kind=kind,
            abstract=abstract,
            base=base,
            fields=fields,
        )

    # ------------------------------------------------------------------
    def _build_tid_field_spec(
        self,
        table: Table,
        *,
        topic: str | None,
        used_names: set[str],
    ) -> FieldSpec | None:
        if not hasattr(table, "getOIDType"):
            return None
        oid_type = table.getOIDType()
        if oid_type is None:
            if not table.isIdentifiable():
                return None
            oid_type = TypeAlias("INTERLIS.ANYOID")
        field_name = self._python_name("tid", used=used_names)
        type_hint, imports = self._type_expr_for_domain(oid_type, mandatory=False)
        domain_info = self._describe_domain(oid_type)
        metadata = {
            "ili": {
                "model": self.model_name,
                "topic": topic,
                "name": "TID",
                "mandatory": table.isIdentifiable(),
                "identifier": True,
                **domain_info,
            }
        }
        return FieldSpec(
            name=field_name,
            type_hint=type_hint,
            metadata=metadata,
            default="None",
            default_factory=None,
            imports=imports,
        )

    # ------------------------------------------------------------------
    def _build_type_info(self, attribute: Attribute) -> TypeInfo:
        domain = attribute.getDomain()
        metadata = self._describe_domain(domain)
        type_hint, imports = self._type_expr_for_domain(domain, mandatory=attribute.isMandatory())
        default: str | None = None
        default_factory: str | None = None
        if isinstance(domain, ListType):
            cardinality = domain.getCardinality()
            if cardinality.getMinimum() == 0:
                default_factory = "tuple"
        elif not attribute.isMandatory():
            default = "None"
        return TypeInfo(
            type_hint=type_hint,
            metadata=metadata,
            default=default,
            default_factory=default_factory,
            imports=imports,
        )

    # ------------------------------------------------------------------
    def _describe_domain(
        self, domain: Type, *, _visited_aliases: set[str] | None = None
    ) -> dict[str, Any]:
        if _visited_aliases is None:
            _visited_aliases = set()
        info: dict[str, Any] = {"ili_type": domain.__class__.__name__}
        display_name = domain.getDisplayName()
        if display_name:
            info["display_name"] = display_name
        if isinstance(domain, TextType):
            info.update(
                {
                    "text_kind": domain.getKind(),
                    "max_length": domain.getMaxLength(),
                    "normalized": domain.isNormalized(),
                }
            )
        elif isinstance(domain, EnumerationType):
            info["literals"] = list(domain.getLiterals())
        elif isinstance(domain, NumericType):
            info["minimum"] = domain.getMinimum()
            info["maximum"] = domain.getMaximum()
        elif isinstance(domain, TypeAlias):
            alias = domain.getAliasing()
            info["alias"] = alias
            info.update(self._alias_metadata(alias, _visited_aliases=_visited_aliases))
        elif isinstance(domain, ReferenceType):
            target_info = self._normalize_target(domain.getReferred())
            info.update(target_info)
        elif isinstance(domain, ListType):
            card = domain.getCardinality()
            info["is_bag"] = domain.isBag()
            info["cardinality"] = {
                "min": card.getMinimum(),
                "max": None if card.getMaximum() < 0 else card.getMaximum(),
            }
            info["items"] = self._describe_domain(
                domain.getElementType(), _visited_aliases=_visited_aliases
            )
        elif isinstance(domain, ObjectType):
            target_info = self._normalize_target(domain.getTarget())
            identifier = self._lookup_identifier_info(domain.getTarget())
            if identifier:
                kind, payload = identifier
                target_info["identifier_category"] = kind
                target_info.update(payload)
            info.update(target_info)
        elif isinstance(domain, TextOIDType):
            value_info = self._describe_domain(
                domain.getOIDType(), _visited_aliases=_visited_aliases
            )
            info.update(
                {
                    "identifier_category": "oid",
                    "identifier_kind": "text",
                    "python_type": "str",
                    "value_type": value_info,
                }
            )
            if "max_length" in value_info:
                info.setdefault("max_length", value_info["max_length"])
        return info

    def _alias_metadata(
        self, alias: str, *, _visited_aliases: set[str] | None = None
    ) -> dict[str, Any]:
        visited = _visited_aliases if _visited_aliases is not None else set()
        if alias in visited:
            return {"alias_kind": "unknown", "python_type": "Any"}
        visited.add(alias)
        try:
            if alias in self._BOOLEAN_ALIASES:
                return {"alias_kind": "boolean", "python_type": "bool"}
            if alias in self._NUMERIC_ALIASES:
                minimum, maximum = self._NUMERIC_ALIASES[alias]
                return {
                    "alias_kind": "numeric",
                    "minimum": minimum,
                    "maximum": maximum,
                    "python_type": "int",
                }
            if alias in self._TEXT_ALIASES:
                return {
                    "alias_kind": "text",
                    "max_length": self._TEXT_ALIASES[alias],
                    "python_type": "str",
                }
            identifier = self._lookup_identifier_info(alias)
            if identifier:
                kind, data = identifier
                return {"alias_kind": kind, **data}
            if alias in self._structures or alias in self._classes:
                qualified = self._full_names.get(alias, alias)
                return {
                    "alias_kind": "object",
                    "target": alias,
                    "qualified_target": qualified,
                    "python_type": alias,
                }
            domain = self._lookup_domain(alias)
            if domain is not None:
                info = self._describe_domain(
                    domain.getType(), _visited_aliases=visited
                )
                info.setdefault("alias_kind", "domain")
                info.setdefault("python_type", "Any")
                info.setdefault("domain", domain.getScopedName() or domain.getName())
                return info
            return {"alias_kind": "unknown", "python_type": "Any"}
        finally:
            visited.discard(alias)

    def _lookup_identifier_info(self, name: str | None) -> tuple[str, dict[str, Any]] | None:
        if not name:
            return None
        base = name.split(".")[-1]
        entry = self._IDENTIFIER_ALIASES.get(base)
        if not entry:
            return None
        kind, payload = entry
        info = dict(payload)
        info["identifier_category"] = kind
        return kind, info

    def _lookup_domain(self, name: str | None) -> Domain | None:
        if not name:
            return None
        domain = self._domains.get(name)
        if domain is not None:
            return domain
        base = name.split(".")[-1]
        return self._domains.get(base)

    def _normalize_target(self, raw: str | None) -> dict[str, Any]:
        if not raw:
            return {"target": None}
        text = raw.replace("(EXTERNAL)", "").strip()
        info: dict[str, Any] = {"target": text.split(".")[-1] if text else text}
        if text in self._full_names.values():
            info["qualified_target"] = text
        else:
            key = text.split(".")[-1]
            qualified = self._full_names.get(key)
            if qualified:
                info["qualified_target"] = qualified
        if "(EXTERNAL)" in (raw or ""):
            info["external"] = True
        return info

    # ------------------------------------------------------------------
    def _type_expr_for_domain(self, domain: Type, *, mandatory: bool, nested: bool = False) -> tuple[str, set[str]]:
        imports: set[str] = set()
        if isinstance(domain, TextType):
            type_hint = "str"
        elif isinstance(domain, EnumerationType):
            literals = list(domain.getLiterals())
            if literals:
                joined = ", ".join(repr(value) for value in literals)
                type_hint = f"Literal[{joined}]"
                imports.add("Literal")
            else:
                type_hint = "str"
        elif isinstance(domain, NumericType):
            type_hint = "float"
        elif isinstance(domain, TypeAlias):
            type_hint, alias_imports = self._alias_type_hint(domain.getAliasing())
            imports.update(alias_imports)
        elif isinstance(domain, ReferenceType):
            type_hint = "str"
        elif isinstance(domain, ListType):
            element_type, element_imports = self._type_expr_for_domain(
                domain.getElementType(), mandatory=True, nested=True
            )
            imports.update(element_imports)
            type_hint = f"tuple[{element_type}, ...]"
        elif isinstance(domain, ObjectType):
            target = domain.getTarget()
            identifier = self._lookup_identifier_info(target)
            if identifier:
                _, payload = identifier
                type_hint = payload.get("python_type", "str")
            else:
                type_hint = target.split(".")[-1] if target else "Any"
                if not target:
                    imports.add("Any")
        elif isinstance(domain, TextOIDType):
            type_hint = "str"
        else:
            type_hint = "Any"
            imports.add("Any")
        if not nested and not mandatory and not isinstance(domain, ListType):
            type_hint = f"{type_hint} | None"
        return type_hint, imports

    def _alias_type_hint(self, alias: str) -> tuple[str, set[str]]:
        meta = self._alias_metadata(alias)
        type_hint = meta.get("python_type", "Any")
        imports: set[str] = set()
        if type_hint == "Any":
            imports.add("Any")
        return type_hint, imports

    # ------------------------------------------------------------------
    def _render_class(self, spec: ClassSpec) -> list[str]:
        lines: list[str] = []
        decorator = "@dataclass(kw_only=True)"
        lines.append(decorator)
        base = spec.base
        header = f"class {spec.name}({base}):" if base else f"class {spec.name}:"
        lines.append(header)
        if not spec.fields and not spec.abstract:
            lines.append("    \"\"\"Auto-generated dataclass.\"\"\"")
        for field_spec in spec.fields:
            lines.extend(self._render_field(field_spec))
        lines.append("    class Meta:")
        lines.append(f"        ili_name = {repr(spec.qualified_name)}")
        lines.append(f"        topic = {repr(spec.topic)}")
        lines.append(f"        kind = {repr(spec.kind)}")
        lines.append(f"        abstract = {spec.abstract}")
        lines.append(f"        extends = {repr(spec.base)}")
        return lines

    def _render_field(self, spec: FieldSpec) -> list[str]:
        lines: list[str] = []
        header = f"    {spec.name}: {spec.type_hint} = field("
        lines.append(header)
        if spec.default is not None:
            lines.append(f"        default={spec.default},")
        if spec.default_factory is not None:
            lines.append(f"        default_factory={spec.default_factory},")
        metadata_repr = pprint.pformat(spec.metadata, width=88)
        metadata_lines = metadata_repr.splitlines()
        lines.append("        metadata=" + metadata_lines[0])
        for line in metadata_lines[1:]:
            lines.append("        " + line)
        lines[-1] += ","
        lines.append("    )")
        return lines

    # ------------------------------------------------------------------
    def _python_name(self, name: str, *, used: set[str]) -> str:
        candidate = name or "field"
        candidate = _SNAKE_CASE_REGEX_1.sub(r"\1_\2", candidate)
        candidate = _SNAKE_CASE_REGEX_2.sub(r"\1_\2", candidate)
        candidate = candidate.replace("-", "_").lower()
        if keyword.iskeyword(candidate):
            candidate += "_"
        base = candidate
        index = 1
        while candidate in used:
            candidate = f"{base}_{index}"
            index += 1
        used.add(candidate)
        return candidate


def generate_model_dataclasses(path: Path) -> str:
    """Parse ``path`` and return a dataclass module as a string."""

    model = parse(path).getModels()[0]
    generator = DataclassGenerator(model)
    return generator.build_module()
