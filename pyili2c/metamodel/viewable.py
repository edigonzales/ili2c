"""Viewables (classes, structures, associations) from the metamodel."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .element import Container, Element


@dataclass
class Viewable(Container):
    name: str = ""
    abstract: bool = False

    def __post_init__(self) -> None:
        self.setName(self.name)

    def isAbstract(self) -> bool:
        return self.abstract


@dataclass
class AbstractClassDef(Viewable):
    extending: Optional["AbstractClassDef"] = None

    def getExtending(self) -> Optional["AbstractClassDef"]:
        return self.extending

    def setExtending(self, base: Optional["AbstractClassDef"]) -> None:
        self.extending = base


@dataclass
class Table(AbstractClassDef):
    identifiable: bool = True

    def isIdentifiable(self) -> bool:
        return self.identifiable

    def setIdentifiable(self, value: bool) -> None:
        self.identifiable = value

    def add_attribute(self, attr: "AttributeDef") -> None:
        from .attribute import AttributeDef

        if not isinstance(attr, AttributeDef):
            raise TypeError("expected AttributeDef")
        self.add(attr)

    def add_constraint(self, constraint: "Constraint") -> None:
        from .constraint import Constraint

        if not isinstance(constraint, Constraint):
            raise TypeError("expected Constraint")
        self.add(constraint)

    def addAttribute(self, attr: "AttributeDef") -> None:  # noqa: N802
        self.add_attribute(attr)

    def addConstraint(self, constraint: "Constraint") -> None:  # noqa: N802
        self.add_constraint(constraint)

    def getAttributes(self) -> list["AttributeDef"]:
        from .attribute import AttributeDef

        return self.elements_of_type(AttributeDef)

    @property
    def attributes(self) -> list["AttributeDef"]:
        return self.getAttributes()

    def getConstraints(self) -> list["Constraint"]:
        from .constraint import Constraint

        return self.elements_of_type(Constraint)


@dataclass
class AssociationDef(AbstractClassDef):
    roles: List["RoleDef"] = field(default_factory=list)

    def addRole(self, role: "RoleDef") -> None:
        from .role import RoleDef

        if not isinstance(role, RoleDef):
            raise TypeError("expected RoleDef")
        self.add(role)
        self.roles.append(role)

    def getRoles(self) -> List["RoleDef"]:
        return list(self.roles)

