"""Simplified Python implementation of the INTERLIS metamodel.

The original ili2c project exposes a rich Java metamodel.  Reimplementing the
entire hierarchy would be a multi-stage effort.  This module focuses on the
subset that is required by the tests in this kata while mimicking the Java API
as closely as is practical.  The goal is that higher level code can treat these
Python classes very similar to their Java counterparts when working with simple
models.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple, Type as TypingType


class Element:
    """Base element that stores common metadata."""

    def __init__(self, name: Optional[str] = None) -> None:
        self._name = name
        self._container: Optional[Element] = None
        self._children: List[Element] = []

    # ------------------------------------------------------------------
    # Basic metadata helpers
    # ------------------------------------------------------------------
    def getName(self) -> Optional[str]:
        return self._name

    def setName(self, name: Optional[str]) -> None:
        self._name = name

    def getContainer(self) -> Optional[Element]:
        return self._container

    def _set_container(self, container: Optional[Element]) -> None:
        self._container = container

    def getScopedName(self) -> Optional[str]:
        if not self._name:
            return self._container.getScopedName() if self._container else None
        if not self._container or not self._container.getScopedName():
            return self._name
        return f"{self._container.getScopedName()}.{self._name}"

    # ------------------------------------------------------------------
    # Child management helpers
    # ------------------------------------------------------------------
    def _register_child(self, child: Optional[Element]) -> Optional[Element]:
        if child is None:
            return None
        child._set_container(self)
        self._children.append(child)
        return child

    def _extend_children(self, children: Iterable[Element]) -> None:
        for child in children:
            self._register_child(child)

    def elements_of_type(self, element_type: TypingType[Element]) -> List[Element]:
        """Return all descendants that are instances of ``element_type``."""

        matches: List[Element] = []
        for child in self._children:
            if isinstance(child, element_type):
                matches.append(child)
            matches.extend(child.elements_of_type(element_type))
        return matches


class ContainerElement(Element):
    """Base class for elements that collect typed children."""

    def __init__(self, name: Optional[str] = None) -> None:
        super().__init__(name=name)

    def add_element(self, element: Element) -> Element:
        return self._register_child(element)  # type: ignore[return-value]


class TransferDescription(ContainerElement):
    """Top-level container that holds all parsed models."""

    def __init__(self) -> None:
        super().__init__(name=None)
        self._models: List[Model] = []
        self._primary_source: Optional[Path] = None

    def add_model(self, model: "Model") -> None:
        self._models.append(model)
        self.add_element(model)

    def getModels(self) -> Sequence["Model"]:
        return tuple(self._models)

    def setPrimarySource(self, source: Optional[Path]) -> None:
        self._primary_source = source

    def getModelsFromLastFile(self) -> Sequence["Model"]:
        if not self._models:
            return ()

        last_model = self._models[-1]
        source = getattr(last_model, "_source", None)
        target_sources: List[Path] = []
        if self._primary_source is not None:
            target_sources.append(self._primary_source)
        if isinstance(source, Path) and source not in target_sources:
            target_sources.append(source)

        for candidate in target_sources:
            matches = [
                model
                for model in self._models
                if getattr(model, "_source", None) == candidate
            ]
            if matches:
                return tuple(matches)

        return (last_model,)

    def find_model(self, name: str) -> Optional["Model"]:
        for model in self._models:
            if model.getName() == name:
                return model
        return None


class Model(ContainerElement):
    """Representation of an INTERLIS model."""

    def __init__(self, name: str, schema_language: Optional[str], schema_version: Optional[str]) -> None:
        super().__init__(name=name)
        self._schema_language = schema_language
        self._schema_version = schema_version
        self._topics: List[Topic] = []
        self._domains: List[Domain] = []
        self._functions: List[Function] = []
        self._tables: List[Table] = []
        self._associations: List["Association"] = []
        self._imports: List[str] = []

    # ------------------------------------------------------------------
    def getSchemaLanguage(self) -> Optional[str]:
        return self._schema_language

    def getSchemaVersion(self) -> Optional[str]:
        return self._schema_version

    # ------------------------------------------------------------------
    def add_topic(self, topic: "Topic") -> "Topic":
        self._topics.append(topic)
        return self.add_element(topic)  # type: ignore[return-value]

    def getTopics(self) -> Sequence["Topic"]:
        return tuple(self._topics)

    def add_domain(self, domain: "Domain") -> "Domain":
        self._domains.append(domain)
        return self.add_element(domain)  # type: ignore[return-value]

    def add_function(self, function: "Function") -> "Function":
        self._functions.append(function)
        return self.add_element(function)  # type: ignore[return-value]

    def add_table(self, table: "Table") -> "Table":
        self._tables.append(table)
        return self.add_element(table)  # type: ignore[return-value]

    def getTables(self) -> Sequence["Table"]:
        return tuple(self._tables)

    def getDomains(self) -> Sequence[Domain]:
        return tuple(self._domains)

    def getFunctions(self) -> Sequence[Function]:
        return tuple(self._functions)

    def add_association(self, association: "Association") -> "Association":
        self._associations.append(association)
        return self.add_element(association)  # type: ignore[return-value]

    def getAssociations(self) -> Sequence["Association"]:
        return tuple(self._associations)

    def elements_of_type(self, element_type: TypingType[Element]) -> List[Element]:  # noqa: D401
        return super().elements_of_type(element_type)

    def add_import(self, model_name: str) -> None:
        if model_name not in self._imports:
            self._imports.append(model_name)

    def getImports(self) -> Sequence[str]:
        return tuple(self._imports)


class Topic(ContainerElement):
    def __init__(self, name: str) -> None:
        super().__init__(name=name)
        self._classes: List[Table] = []
        self._structures: List[Table] = []
        self._associations: List["Association"] = []
        self._oid_type: Optional[Type] = None
        self._basket_oid_type: Optional[Type] = None

    def add_class(self, table: "Table") -> "Table":
        self._classes.append(table)
        return self.add_element(table)  # type: ignore[return-value]

    def add_structure(self, table: "Table") -> "Table":
        self._structures.append(table)
        return self.add_element(table)  # type: ignore[return-value]

    def getClasses(self) -> Sequence["Table"]:
        return tuple(self._classes)

    def getStructures(self) -> Sequence["Table"]:
        return tuple(self._structures)

    def add_association(self, association: "Association") -> "Association":
        self._associations.append(association)
        return self.add_element(association)  # type: ignore[return-value]

    def getAssociations(self) -> Sequence["Association"]:
        return tuple(self._associations)

    def setOIDType(self, oid_type: Optional[Type]) -> None:
        self._oid_type = oid_type
        if oid_type is not None:
            self._register_child(oid_type)

    def getOIDType(self) -> Optional[Type]:
        return self._oid_type

    def setBasketOIDType(self, oid_type: Optional[Type]) -> None:
        self._basket_oid_type = oid_type
        if oid_type is not None:
            self._register_child(oid_type)

    def getBasketOIDType(self) -> Optional[Type]:
        return self._basket_oid_type


class Type(Element):
    """Representation of a type reference or built-in type."""

    def __init__(self, name: Optional[str]) -> None:
        super().__init__(name=name)

    # ------------------------------------------------------------------
    def getDisplayName(self) -> str:
        name = self.getName()
        return name if name else "Unknown"


class TextType(Type):
    def __init__(
        self,
        *,
        kind: str,
        max_length: Optional[int] = None,
        normalized: bool = True,
        name: Optional[str] = None,
    ) -> None:
        super().__init__(name=name or kind)
        self._kind = kind
        self._max_length = max_length
        self._normalized = normalized

    def getKind(self) -> str:
        return self._kind

    def getMaxLength(self) -> Optional[int]:
        return self._max_length

    def isNormalized(self) -> bool:
        return self._normalized

    def getDisplayName(self) -> str:
        label = self._kind
        if self._kind.upper() in {"TEXT", "MTEXT"} and self._max_length:
            label = f"{label}*{self._max_length}"
        return label


class NumericType(Type):
    def __init__(
        self,
        *,
        minimum: Optional[str] = None,
        maximum: Optional[str] = None,
        name: Optional[str] = None,
    ) -> None:
        super().__init__(name=name)
        self._minimum = minimum
        self._maximum = maximum

    def getMinimum(self) -> Optional[str]:
        return self._minimum

    def getMaximum(self) -> Optional[str]:
        return self._maximum

    def getDisplayName(self) -> str:
        name = super().getName()
        if name:
            return name
        if self._minimum is not None or self._maximum is not None:
            left = self._minimum if self._minimum is not None else ""
            right = self._maximum if self._maximum is not None else ""
            if left and right:
                return f"{left}..{right}"
            return left or right or "NUMERIC"
        return "NUMERIC"


class BlackboxType(Type):
    """Representation of ``BLACKBOX`` types."""

    KIND_XML = "XML"
    KIND_BINARY = "BINARY"

    def __init__(self, *, kind: str, name: Optional[str] = None) -> None:
        kind_value = kind.upper()
        super().__init__(name=name or f"BLACKBOX {kind_value}".strip())
        self._kind = kind_value

    def getKind(self) -> str:
        return self._kind

    def getDisplayName(self) -> str:
        if self._kind == self.KIND_BINARY:
            return "Blackbox Binary"
        if self._kind == self.KIND_XML:
            return "Blackbox Xml"
        label = self._kind.title() if self._kind else ""
        return f"Blackbox {label}".strip()


class GeometryType(Type):
    def __init__(self, *, kind: str, definition: str, name: Optional[str] = None) -> None:
        super().__init__(name=name or kind.upper())
        self._kind = kind
        self._definition = definition

    def getKind(self) -> str:
        return self._kind

    def getDefinition(self) -> str:
        return self._definition

    def getDisplayName(self) -> str:
        return self._kind


class AreaType(GeometryType):
    def __init__(self, *, definition: str, name: Optional[str] = None) -> None:
        super().__init__(kind="Area", definition=definition, name=name)


class SurfaceType(GeometryType):
    def __init__(self, *, definition: str, name: Optional[str] = None) -> None:
        super().__init__(kind="Surface", definition=definition, name=name)


class MultiSurfaceType(GeometryType):
    def __init__(self, *, definition: str, name: Optional[str] = None) -> None:
        super().__init__(kind="MultiSurface", definition=definition, name=name)


class MultiAreaType(GeometryType):
    def __init__(self, *, definition: str, name: Optional[str] = None) -> None:
        super().__init__(kind="MultiArea", definition=definition, name=name)


class PolylineType(GeometryType):
    def __init__(self, *, definition: str, name: Optional[str] = None) -> None:
        super().__init__(kind="Polyline", definition=definition, name=name)


class MultiPolylineType(GeometryType):
    def __init__(self, *, definition: str, name: Optional[str] = None) -> None:
        super().__init__(kind="MultiPolyline", definition=definition, name=name)


class CoordType(GeometryType):
    def __init__(self, *, definition: str, name: Optional[str] = None) -> None:
        super().__init__(kind="Coord", definition=definition, name=name)


class MultiCoordType(GeometryType):
    def __init__(self, *, definition: str, name: Optional[str] = None) -> None:
        super().__init__(kind="MultiCoord", definition=definition, name=name)


class EnumerationType(Type):
    def __init__(self, name: Optional[str], literals: Sequence[str]) -> None:
        super().__init__(name=name)
        self._literals = list(literals)

    def getLiterals(self) -> Sequence[str]:
        return tuple(self._literals)

    def getDisplayName(self) -> str:
        name = self.getName()
        if name:
            return name.split(".")[-1]
        return ", ".join(self._literals) if self._literals else "Enumeration"


class EnumTreeValueType(Type):
    def __init__(self, base_domain: str, name: Optional[str] = None) -> None:
        super().__init__(name=name)
        self._base_domain = base_domain

    def getBaseDomain(self) -> str:
        return self._base_domain

    def getDisplayName(self) -> str:
        return self._base_domain.split(".")[-1] if self._base_domain else "Enumeration"


class FormattedType(Type):
    def __init__(
        self,
        *,
        base_domain: str,
        picture: Optional[str] = None,
        minimum: Optional[str] = None,
        maximum: Optional[str] = None,
        name: Optional[str] = None,
    ) -> None:
        super().__init__(name=name)
        self._base_domain = base_domain
        self._picture = picture
        self._minimum = minimum
        self._maximum = maximum

    def getBaseDomain(self) -> str:
        return self._base_domain

    def getPicture(self) -> Optional[str]:
        return self._picture

    def getMinimum(self) -> Optional[str]:
        return self._minimum

    def getMaximum(self) -> Optional[str]:
        return self._maximum

    def getDisplayName(self) -> str:
        base = self._base_domain or self.getName()
        if not base:
            return "FORMAT"
        return base.split(".")[-1]


class TextOIDType(Type):
    def __init__(self, oid_type: Type, name: Optional[str] = None) -> None:
        super().__init__(name=name)
        self._oid_type = oid_type
        self._register_child(oid_type)

    def getOIDType(self) -> Type:
        return self._oid_type

    def getDisplayName(self) -> str:
        return f"OID {self._oid_type.getDisplayName()}".strip()


class TypeAlias(Type):
    def __init__(self, target: str) -> None:
        super().__init__(name=target)
        self._target = target

    def getAliasing(self) -> str:
        return self._target

    def getDisplayName(self) -> str:
        return self._target.split(".")[-1] if self._target else "Unknown"


class ReferenceType(Type):
    def __init__(self, target: str, name: Optional[str] = None) -> None:
        super().__init__(name=name)
        self._target = target

    def getReferred(self) -> str:
        return self._target

    def getDisplayName(self) -> str:
        target = self._target.split(".")[-1] if self._target else "Unknown"
        return target


class ObjectType(Type):
    def __init__(self, target: str, name: Optional[str] = None) -> None:
        super().__init__(name=name or target)
        self._target = target

    def getTarget(self) -> str:
        return self._target

    def getDisplayName(self) -> str:
        return self._target.split(".")[-1] if self._target else "Unknown"


class Cardinality:
    def __init__(self, minimum: int, maximum: int) -> None:
        self._minimum = minimum
        self._maximum = maximum

    def getMinimum(self) -> int:
        return self._minimum

    def getMaximum(self) -> int:
        return self._maximum


class ListType(Type):
    def __init__(
        self,
        element_type: Type,
        *,
        is_bag: bool,
        cardinality: Optional[Cardinality] = None,
    ) -> None:
        super().__init__(name=None)
        self._element_type = element_type
        self._is_bag = is_bag
        self._cardinality = cardinality or Cardinality(0, -1)
        self._register_child(element_type)

    def getElementType(self) -> Type:
        return self._element_type

    def isBag(self) -> bool:
        return self._is_bag

    @property
    def cardinality_min(self) -> int:
        return self._cardinality.getMinimum()

    @property
    def cardinality_max(self) -> int:
        return self._cardinality.getMaximum()

    def getCardinality(self) -> Cardinality:
        return self._cardinality


class Domain(Element):
    def __init__(self, name: str, domain_type: Type) -> None:
        super().__init__(name=name)
        self._type = domain_type
        self._register_child(domain_type)

    def getType(self) -> Type:
        return self._type


class FunctionArgument(Element):
    def __init__(self, name: str, arg_type: Type) -> None:
        super().__init__(name=name)
        self._type = arg_type
        self._register_child(arg_type)

    def getType(self) -> Type:
        return self._type


class Function(ContainerElement):
    def __init__(self, name: str) -> None:
        super().__init__(name=name)
        self._arguments: List[FunctionArgument] = []
        self._return_type: Optional[Type] = None

    def add_argument(self, argument: FunctionArgument) -> FunctionArgument:
        self._arguments.append(argument)
        return self.add_element(argument)  # type: ignore[return-value]

    def setReturnType(self, return_type: Type) -> None:
        self._return_type = return_type
        self.add_element(return_type)

    def getArguments(self) -> Sequence[FunctionArgument]:
        return tuple(self._arguments)

    def getReturnType(self) -> Optional[Type]:
        return self._return_type


class Attribute(Element):
    def __init__(self, name: str, domain: Type, *, mandatory: bool = False) -> None:
        super().__init__(name=name)
        self._domain = domain
        self._mandatory = mandatory
        self._register_child(domain)

    def getDomain(self) -> Type:
        return self._domain

    def isMandatory(self) -> bool:
        return self._mandatory

    def getCardinality(self) -> Cardinality:
        if isinstance(self._domain, ListType):
            return self._domain.getCardinality()
        return Cardinality(1, 1) if self._mandatory else Cardinality(0, 1)


class Constraint(Element):
    def __init__(self, name: Optional[str], expression: str, *, mandatory: bool = False) -> None:
        super().__init__(name=name)
        self.expression = expression
        self._mandatory = mandatory

    def isMandatory(self) -> bool:
        return self._mandatory


class Viewable(ContainerElement):
    """Abstract base for INTERLIS classes, structures and views."""

    def __init__(self, name: str, *, abstract: bool = False) -> None:
        super().__init__(name=name)
        self._abstract = abstract
        self._attributes: List[Attribute] = []
        self._constraints: List[Constraint] = []
        self._extending: Optional["Viewable"] = None

    def getAttributes(self) -> Sequence[Attribute]:
        return tuple(self._attributes)

    def add_attribute(self, attribute: Attribute) -> Attribute:
        self._attributes.append(attribute)
        return self.add_element(attribute)  # type: ignore[return-value]

    def getConstraints(self) -> Sequence[Constraint]:
        return tuple(self._constraints)

    def add_constraint(self, constraint: Constraint) -> Constraint:
        self._constraints.append(constraint)
        return self.add_element(constraint)  # type: ignore[return-value]

    def isAbstract(self) -> bool:
        return self._abstract

    def setExtending(self, parent: "Viewable") -> None:
        self._extending = parent

    def getExtending(self) -> Optional["Viewable"]:
        return self._extending


class Table(Viewable):
    def __init__(
        self,
        name: str,
        *,
        kind: str,
        abstract: bool = False,
        identifiable: bool = True,
    ) -> None:
        super().__init__(name=name, abstract=abstract)
        self._kind = kind
        self._identifiable = identifiable
        self._oid_type: Optional[Type] = None

    def isIdentifiable(self) -> bool:
        return self._identifiable

    def getKind(self) -> str:
        return self._kind

    def setOIDType(self, oid_type: Optional[Type]) -> None:
        self._oid_type = oid_type
        if oid_type is not None:
            self._register_child(oid_type)

    def getOIDType(self) -> Optional[Type]:
        return self._oid_type


class Association(ContainerElement):
    def __init__(self, name: Optional[str]) -> None:
        super().__init__(name=name)
        self._ends: List["AssociationEnd"] = []
        self._attributes: List[Attribute] = []
        self._constraints: List[Constraint] = []
        self._extending: Optional["Association"] = None

    def add_end(self, end: "AssociationEnd") -> "AssociationEnd":
        self._ends.append(end)
        return self.add_element(end)  # type: ignore[return-value]

    def getEnds(self) -> Sequence["AssociationEnd"]:
        return tuple(self._ends)

    def add_attribute(self, attribute: Attribute) -> Attribute:
        self._attributes.append(attribute)
        return self.add_element(attribute)  # type: ignore[return-value]

    def getAttributes(self) -> Sequence[Attribute]:
        return tuple(self._attributes)

    def add_constraint(self, constraint: Constraint) -> Constraint:
        self._constraints.append(constraint)
        return self.add_element(constraint)  # type: ignore[return-value]

    def getConstraints(self) -> Sequence[Constraint]:
        return tuple(self._constraints)

    def setExtending(self, parent: "Association") -> None:
        self._extending = parent

    def getExtending(self) -> Optional["Association"]:
        return self._extending


class AssociationEnd(Element):
    def __init__(
        self,
        name: str,
        target: Type,
        *,
        cardinality: Optional[Cardinality] = None,
        role_kind: str = "--",
        is_external: bool = False,
    ) -> None:
        super().__init__(name=name)
        self._target = target
        self._cardinality = cardinality or Cardinality(0, 1)
        self._role_kind = role_kind or "--"
        self._is_external = is_external
        self._register_child(target)

    def getTarget(self) -> Type:
        return self._target

    def getCardinality(self) -> Cardinality:
        return self._cardinality

    def getRoleKind(self) -> str:
        return self._role_kind

    def isExternal(self) -> bool:
        return self._is_external

