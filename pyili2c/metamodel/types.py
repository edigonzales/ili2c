"""INTERLIS type hierarchy."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .element import Element


@dataclass
class Type(Element):
    extending: Optional["Type"] = None
    cardinality_min: int = 0
    cardinality_max: int = 1

    def getExtending(self) -> Optional["Type"]:
        return self.extending

    def setExtending(self, base: Optional["Type"]) -> None:
        self.extending = base

    def setCardinality(self, minimum: int, maximum: int) -> None:
        self.cardinality_min = minimum
        self.cardinality_max = maximum

    def isBoolean(self) -> bool:
        return False


@dataclass
class TypeAlias(Type):
    aliasing: Optional["Domain"] = None

    def getAliasing(self) -> Optional["Domain"]:
        return self.aliasing

    def setAliasing(self, domain: Optional["Domain"]) -> None:
        self.aliasing = domain

    def isBoolean(self) -> bool:
        if self.aliasing is not None:
            return self.aliasing.isBoolean()
        return False


@dataclass
class ObjectType(Type):
    pass


@dataclass
class ReferenceType(Type):
    referred: Optional["AbstractClassDef"] = None

    def getReferred(self) -> Optional["AbstractClassDef"]:
        return self.referred

    def setReferred(self, target: Optional["AbstractClassDef"]) -> None:
        self.referred = target


@dataclass
class CompositionType(Type):
    component_type: Optional["AbstractClassDef"] = None

    def getComponentType(self) -> Optional["AbstractClassDef"]:
        return self.component_type

    def setComponentType(self, target: Optional["AbstractClassDef"]) -> None:
        self.component_type = target


@dataclass
class SurfaceType(Type):
    pass


@dataclass
class MultiSurfaceType(SurfaceType):
    pass


@dataclass
class AreaType(Type):
    pass


@dataclass
class MultiAreaType(AreaType):
    pass


@dataclass
class PolylineType(Type):
    pass


@dataclass
class MultiPolylineType(PolylineType):
    pass


@dataclass
class NumericalType(Type):
    pass


@dataclass
class NumericType(NumericalType):
    pass


@dataclass
class CoordType(Type):
    dimensions: List[NumericalType] = None

    def __post_init__(self) -> None:
        if self.dimensions is None:
            self.dimensions = []

    def getDimensions(self) -> List[NumericalType]:
        return list(self.dimensions)

    def setDimensions(self, dimensions: List[NumericalType]) -> None:
        self.dimensions = list(dimensions)


@dataclass
class MultiCoordType(CoordType):
    pass


@dataclass
class TextType(Type):
    length: Optional[int] = None

    def getLength(self) -> Optional[int]:
        return self.length

    def setLength(self, length: Optional[int]) -> None:
        self.length = length


@dataclass
class TextOIDType(Type):
    oid_type: Optional[Type] = None

    def getOIDType(self) -> Optional[Type]:
        return self.oid_type

    def setOIDType(self, type_: Optional[Type]) -> None:
        self.oid_type = type_


@dataclass
class EnumerationType(Type):
    is_boolean: bool = False
    literals: List[str] = field(default_factory=list)

    def isBoolean(self) -> bool:
        return self.is_boolean

    def setBoolean(self, value: bool) -> None:
        self.is_boolean = value

    def getLiterals(self) -> List[str]:
        return list(self.literals)


@dataclass
class FormattedType(Type):
    defined_base_domain: Optional["Domain"] = None

    def getDefinedBaseDomain(self) -> Optional["Domain"]:
        return self.defined_base_domain

    def setDefinedBaseDomain(self, domain: Optional["Domain"]) -> None:
        self.defined_base_domain = domain


@dataclass
class ListType(Type):
    element_type: Optional[Type | "Domain"] = None
    is_bag: bool = False

    def getElementType(self) -> Optional[Type | "Domain"]:
        return self.element_type

    def setElementType(self, element_type: Optional[Type | "Domain"]) -> None:
        self.element_type = element_type

    def isBag(self) -> bool:
        return self.is_bag

    def setIsBag(self, is_bag: bool) -> None:
        self.is_bag = is_bag


# Circular imports
from .domain import Domain  # noqa: E402  pylint: disable=wrong-import-position
from .viewable import AbstractClassDef  # noqa: E402  pylint: disable=wrong-import-position

