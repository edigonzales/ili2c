"""Python port of the ili2c metamodel."""
from .attribute import AttributeDef
from .cardinality import Cardinality
from .constraint import Constraint
from .domain import Domain
from .element import Container, Element
from .function import FormalArgument, Function
from .model import DataModel, Model, Topic
from .predefined import PredefinedModel
from .role import RoleDef
from .transfer import TransferDescription
from .types import (
    AreaType,
    CompositionType,
    CoordType,
    EnumerationType,
    FormattedType,
    MultiAreaType,
    MultiCoordType,
    MultiPolylineType,
    MultiSurfaceType,
    NumericType,
    NumericalType,
    ObjectType,
    PolylineType,
    ReferenceType,
    SurfaceType,
    ListType,
    TextOIDType,
    TextType,
    Type,
    TypeAlias,
)
from .viewable import AbstractClassDef, AssociationDef, Table, Viewable

# Backwards compatibility alias matching the earlier prototype naming
Class = Table

__all__ = [
    "AttributeDef",
    "Cardinality",
    "Constraint",
    "Domain",
    "Element",
    "Container",
    "Function",
    "FormalArgument",
    "Model",
    "DataModel",
    "Topic",
    "PredefinedModel",
    "TransferDescription",
    "Viewable",
    "AbstractClassDef",
    "AssociationDef",
    "Table",
    "Class",
    "RoleDef",
    "Type",
    "TypeAlias",
    "CompositionType",
    "ReferenceType",
    "ObjectType",
    "SurfaceType",
    "MultiSurfaceType",
    "ListType",
    "AreaType",
    "MultiAreaType",
    "PolylineType",
    "MultiPolylineType",
    "CoordType",
    "MultiCoordType",
    "NumericalType",
    "NumericType",
    "TextType",
    "TextOIDType",
    "EnumerationType",
    "FormattedType",
]

