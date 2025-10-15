"""Simplified Python implementation of the INTERLIS metamodel.

The original ili2c project exposes a rich Java metamodel.  Reimplementing the
entire hierarchy would be a multi-stage effort.  This module focuses on the
subset that is required by the tests in this kata while mimicking the Java API
as closely as is practical.  The goal is that higher level code can treat these
Python classes very similar to their Java counterparts when working with simple
models.
"""

from __future__ import annotations

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

    def add_model(self, model: "Model") -> None:
        self._models.append(model)
        self.add_element(model)

    def getModels(self) -> Sequence["Model"]:
        return tuple(self._models)

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


class Type(Element):
    """Representation of a type reference or built-in type."""

    def __init__(self, name: Optional[str]) -> None:
        super().__init__(name=name)


class EnumerationType(Type):
    def __init__(self, name: Optional[str], literals: Sequence[str]) -> None:
        super().__init__(name=name)
        self._literals = list(literals)

    def getLiterals(self) -> Sequence[str]:
        return tuple(self._literals)


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

    def isIdentifiable(self) -> bool:
        return self._identifiable

    def getKind(self) -> str:
        return self._kind


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

