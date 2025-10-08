"""Render INTERLIS metamodels as Mermaid class diagrams."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, List, Optional

from .metamodel.attribute import AttributeDef
from .metamodel.cardinality import Cardinality
from .metamodel.constraint import Constraint
from .metamodel.domain import Domain
from .metamodel.element import Container, Element
from .metamodel.function import Function
from .metamodel.model import Model, Topic
from .metamodel.predefined import PredefinedModel
from .metamodel.role import RoleDef
from .metamodel.transfer import TransferDescription
from .metamodel.types import (
    AreaType,
    CompositionType,
    CoordType,
    EnumerationType,
    FormattedType,
    ListType,
    MultiAreaType,
    MultiCoordType,
    MultiPolylineType,
    MultiSurfaceType,
    NumericType,
    ObjectType,
    PolylineType,
    ReferenceType,
    SurfaceType,
    TextOIDType,
    TextType,
    Type,
    TypeAlias,
)
from .metamodel.viewable import AssociationDef, Table, Viewable


def render(transfer: TransferDescription) -> str:
    """Entry point mirroring the original Java ``Ili2Mermaid`` utility."""

    if transfer is None:  # pragma: no cover - guard clause
        raise TypeError("TransferDescription is null")

    adapter = _Ili2cAdapter()
    diagram = adapter.build_diagram(transfer)
    return _MermaidRenderer().render(diagram)


@dataclass
class _Diagram:
    namespaces: Dict[str, "_Namespace"] = field(default_factory=dict)
    nodes: Dict[str, "_Node"] = field(default_factory=dict)
    inheritances: List["_Inheritance"] = field(default_factory=list)
    associations: List["_Association"] = field(default_factory=list)

    def get_or_create_namespace(self, label: str) -> "_Namespace":
        namespace = self.namespaces.get(label)
        if namespace is None:
            namespace = _Namespace(label)
            self.namespaces[label] = namespace
        return namespace


@dataclass
class _Namespace:
    label: str
    node_order: List[str] = field(default_factory=list)

    def add_node(self, fqn: str) -> None:
        if fqn not in self.node_order:
            self.node_order.append(fqn)


@dataclass
class _Node:
    fqn: str
    display_name: str
    stereotypes: List[str] = field(default_factory=list)
    attributes: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)

    def add_stereotypes(self, names: Iterable[str]) -> None:
        for name in names:
            if name and name not in self.stereotypes:
                self.stereotypes.append(name)


@dataclass
class _Inheritance:
    sub_fqn: str
    sup_fqn: str


@dataclass
class _Association:
    left_fqn: str
    right_fqn: str
    left_cardinality: str
    right_cardinality: str
    label: str | None = None


class _Ili2cAdapter:
    def __init__(self) -> None:
        self._element_by_fqn: Dict[str, Element] = {}

    def build_diagram(self, transfer: TransferDescription) -> _Diagram:
        diagram = _Diagram()

        last_models = list(self._sort_by_name(transfer.getModelsFromLastFile()))
        last_model_ids = {id(model) for model in last_models}

        root = diagram.get_or_create_namespace("<root>")

        for model in last_models:
            # Topics first
            for topic in self._get_elements(model, Topic):
                namespace_label = f"{model.getName()}::{topic.getName()}"
                diagram.get_or_create_namespace(namespace_label)

                self._collect_viewables(diagram, model, topic)
                self._collect_domains(diagram, model, topic)
                self._collect_functions(diagram, model, topic)

            # Model level elements
            self._collect_viewables(diagram, model, model)
            self._collect_domains(diagram, model, model)
            self._collect_functions(diagram, model, model)

        # Inheritance edges and external placeholders
        for fqn, node in list(diagram.nodes.items()):
            element = self._element_by_fqn.get(fqn)
            if isinstance(element, Table):
                base = element.getExtending()
                if isinstance(base, Table):
                    sup_fqn = self._fqn_for_element(base)
                    if not self._belongs_to_last_file(base, last_model_ids):
                        external = diagram.nodes.get(sup_fqn)
                        if external is None:
                            external_node = _Node(sup_fqn, self._local_name(sup_fqn))
                            external_node.add_stereotypes(["External"])
                            diagram.nodes[sup_fqn] = external_node
                            root.add_node(sup_fqn)
                        else:
                            external.add_stereotypes(["External"])
                    diagram.inheritances.append(_Inheritance(fqn, sup_fqn))

        # Associations with cardinalities
        for model in last_models:
            for topic in self._get_elements(model, Topic):
                self._collect_associations(diagram, last_model_ids, model, topic)
            self._collect_associations(diagram, last_model_ids, model, model)

        diagram.inheritances.sort(key=lambda i: (i.sub_fqn, i.sup_fqn))
        diagram.associations.sort(
            key=lambda assoc: (
                assoc.left_fqn,
                assoc.right_fqn,
                assoc.label or "",
            )
        )

        return diagram

    # ------------------------------------------------------------------
    # Collection helpers
    # ------------------------------------------------------------------
    def _collect_functions(
        self, diagram: _Diagram, model: Model, container: Container
    ) -> None:
        namespace = (
            f"{model.getName()}::{container.getName()}"
            if isinstance(container, Topic)
            else "<root>"
        )
        ns = diagram.get_or_create_namespace(namespace)

        for function in self._get_elements(container, Function):
            fqn = self._fqn(model, container, function)
            node = diagram.nodes.get(fqn)
            if node is None:
                node = _Node(fqn, function.getName() or "")
                diagram.nodes[fqn] = node
            node.add_stereotypes(["Function"])
            ns.add_node(fqn)

    def _collect_viewables(
        self,
        diagram: _Diagram,
        model: Model,
        container: Container,
    ) -> None:
        namespace = (
            f"{model.getName()}::{container.getName()}"
            if isinstance(container, Topic)
            else "<root>"
        )
        ns = diagram.get_or_create_namespace(namespace)

        for viewable in self._get_elements(container, Viewable):
            if isinstance(viewable, AssociationDef):
                continue
            fqn = self._fqn(model, container, viewable)
            stereotypes: List[str] = []
            if viewable.isAbstract():
                stereotypes.append("Abstract")
            if isinstance(viewable, Table):
                if not viewable.isIdentifiable():
                    stereotypes.append("Structure")
            else:
                stereotypes.append("View")

            node = diagram.nodes.get(fqn)
            if node is None:
                node = _Node(fqn, viewable.getName() or "")
                diagram.nodes[fqn] = node
            node.add_stereotypes(stereotypes)
            ns.add_node(fqn)

            self._element_by_fqn[fqn] = viewable

            if isinstance(viewable, Table):
                for attribute in self._get_elements(viewable, AttributeDef):
                    card = self._attribute_cardinality(attribute)
                    type_name = _TypeNamer.name_of(attribute)
                    if type_name.lower() == "objecttype":
                        continue
                    attr_line = f"{attribute.getName()}[{card}] : {type_name}"
                    if attr_line not in node.attributes:
                        node.attributes.append(attr_line)

                counter = 1
                for constraint in self._get_elements(viewable, Constraint):
                    cname = constraint.getName()
                    if not cname:
                        cname = f"constraint{counter}"
                        counter += 1
                    method_line = f"{cname}()"
                    if method_line not in node.methods:
                        node.methods.append(method_line)

    def _collect_domains(
        self,
        diagram: _Diagram,
        model: Model,
        container: Container,
    ) -> None:
        namespace = (
            f"{model.getName()}::{container.getName()}"
            if isinstance(container, Topic)
            else "<root>"
        )
        ns = diagram.get_or_create_namespace(namespace)

        for domain in self._get_elements(container, Domain):
            type_ = domain.getType()
            if isinstance(type_, EnumerationType):
                fqn = self._fqn(model, container, domain)
                node = diagram.nodes.get(fqn)
                if node is None:
                    node = _Node(fqn, domain.getName() or "")
                    diagram.nodes[fqn] = node
                node.add_stereotypes(["Enumeration"])
                ns.add_node(fqn)
                self._element_by_fqn[fqn] = domain

    def _collect_associations(
        self,
        diagram: _Diagram,
        last_model_ids: set[int],
        model: Model,
        container: Container,
    ) -> None:
        for association in self._get_elements(container, AssociationDef):
            roles = association.getRoles()
            if len(roles) != 2:
                continue

            left_role, right_role = roles
            left_dest = left_role.getDestination()
            right_dest = right_role.getDestination()
            if not isinstance(left_dest, Table) or not isinstance(right_dest, Table):
                continue

            left_fqn = self._fqn_for_element(left_dest)
            right_fqn = self._fqn_for_element(right_dest)

            if not self._belongs_to_last_file(left_dest, last_model_ids):
                self._ensure_external_node(diagram, left_dest)
            if not self._belongs_to_last_file(right_dest, last_model_ids):
                self._ensure_external_node(diagram, right_dest)

            left_card = _format_cardinality(left_role.getCardinality())
            right_card = _format_cardinality(right_role.getCardinality())
            label = f"{self._role_label(left_role)}–{self._role_label(right_role)}"

            diagram.associations.append(
                _Association(left_fqn, right_fqn, left_card, right_card, label)
            )

    # ------------------------------------------------------------------
    # Helper utilities over the metamodel
    # ------------------------------------------------------------------
    @staticmethod
    def _role_label(role: RoleDef) -> str:
        name = role.getName()
        return name if name else "role"

    @staticmethod
    def _model_of(element: Element) -> Optional[Model]:
        current: Optional[Element] = element
        while current is not None and not isinstance(current, Model):
            current = current.getContainer()
        return current if isinstance(current, Model) else None

    @classmethod
    def _belongs_to_last_file(cls, element: Element, last_model_ids: set[int]) -> bool:
        model = cls._model_of(element)
        return id(model) in last_model_ids if model is not None else False

    @staticmethod
    def _container_of(element: Element) -> Optional[Container]:
        container = element.getContainer()
        return container if isinstance(container, Container) else None

    @staticmethod
    def _fqn(model: Model, container: Optional[Container], element: Element) -> str:
        if isinstance(container, Topic):
            return f"{model.getName()}.{container.getName()}.{element.getName()}"
        return f"{model.getName()}.{element.getName()}"

    @classmethod
    def _fqn_for_element(cls, element: Element) -> str:
        model = cls._model_of(element)
        container = cls._container_of(element)
        if model is None:
            return element.getName() or "<unnamed>"
        return cls._fqn(model, container, element)

    @staticmethod
    def _local_name(fqn: str) -> str:
        return fqn.rsplit(".", 1)[-1]

    def _attribute_cardinality(self, attribute: AttributeDef) -> str:
        cardinality = attribute.getCardinality()
        if cardinality is not None:
            return _format_cardinality(cardinality)

        domain = attribute.getDomain()
        domain_type: Optional[Type | Domain]

        if isinstance(domain, Domain):
            domain_type = domain.getType()
        else:
            domain_type = domain

        if isinstance(domain_type, ListType):
            list_card = Cardinality(
                domain_type.cardinality_min, domain_type.cardinality_max
            )
            return _format_cardinality(list_card)

        return "1" if attribute.isMandatory() else "0..1"

    def _ensure_external_node(self, diagram: _Diagram, table: Table) -> None:
        fqn = self._fqn_for_element(table)
        node = diagram.nodes.get(fqn)
        if node is None:
            node = _Node(fqn, table.getName() or "")
            node.add_stereotypes(["External"])
            diagram.nodes[fqn] = node
            diagram.get_or_create_namespace("<root>").add_node(fqn)
        else:
            node.add_stereotypes(["External"])

    @staticmethod
    def _sort_by_name(elements: Iterable[Element]) -> Iterator[Element]:
        return iter(
            sorted(
                elements,
                key=lambda el: (el.getName() or ""),
            )
        )

    @staticmethod
    def _get_elements(container: Container, cls: type[Element]) -> List[Element]:
        result = [element for element in container.iterator() if isinstance(element, cls)]
        result.sort(key=lambda el: el.getName() or "")
        return result


class _MermaidRenderer:
    def render(self, diagram: _Diagram) -> str:
        lines: List[str] = ["classDiagram"]

        for namespace in diagram.namespaces.values():
            if namespace.label == "<root>":
                continue
            lines.append(f"  namespace {self._namespace_id(namespace.label)} {{")
            for fqn in namespace.node_order:
                node = diagram.nodes[fqn]
                lines.extend(self._format_node(node, indent="    "))
            lines.append("  }")

        root = diagram.namespaces.get("<root>")
        if root is not None:
            for fqn in root.node_order:
                node = diagram.nodes[fqn]
                lines.extend(self._format_node(node, indent="  "))

        for inheritance in diagram.inheritances:
            lines.append(
                f"  {inheritance.sub_fqn} --|> {inheritance.sup_fqn}"
            )

        for association in diagram.associations:
            line = (
                f"  {association.left_fqn} \"{association.left_cardinality}\" -- "
                f"\"{association.right_cardinality}\" {association.right_fqn}"
            )
            if association.label:
                line += f" : {self._escape(association.label)}"
            lines.append(line)

        return "\n".join(lines) + "\n"

    @staticmethod
    def _format_node(node: _Node, indent: str) -> List[str]:
        lines = [
            f"{indent}class {node.fqn}[\"{_MermaidRenderer._escape(node.display_name)}\"] {{"
        ]
        for stereotype in node.stereotypes:
            lines.append(f"{indent}  <<{stereotype}>>")
        for attribute in node.attributes:
            lines.append(f"{indent}  {_MermaidRenderer._escape(attribute)}")
        for method in node.methods:
            lines.append(f"{indent}  {_MermaidRenderer._escape(method)}")
        lines.append(f"{indent}}}")
        return lines

    @staticmethod
    def _namespace_id(label: str) -> str:
        return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in label)

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("\"", "\\\"")


class _TypeNamer:
    @classmethod
    def name_of(cls, attribute: AttributeDef) -> str:
        domain = attribute.getDomain()
        name = cls._name_from_domain_or_type(domain, attribute)
        return name if name else "<Unknown>"

    @classmethod
    def _name_from_domain_or_type(
        cls, obj: Optional[Type | Domain], attribute: AttributeDef
    ) -> str:
        if obj is None:
            return ""
        if isinstance(obj, Domain):
            type_ = obj.getType()
            if type_ is not None:
                return cls._name_from_type(type_, attribute)
            return cls._simple_name(obj.getName())
        if isinstance(obj, Type):
            return cls._name_from_type(obj, attribute)
        return ""

    @classmethod
    def _name_from_type(cls, type_: Type, attribute: AttributeDef) -> str:
        if isinstance(type_, ObjectType):
            return "ObjectType"
        if isinstance(type_, ReferenceType):
            referred = type_.getReferred()
            if referred is not None:
                return cls._simple_name(referred.getName()) or "Object"
        if isinstance(type_, CompositionType):
            comp = type_.getComponentType()
            if comp is not None:
                return cls._simple_name(comp.getName()) or "Component"
        if isinstance(type_, ListType):
            element = type_.getElementType()
            element_name = cls._name_from_domain_or_type(element, attribute)
            return element_name or "List"
        if isinstance(type_, SurfaceType):
            return "Surface"
        if isinstance(type_, MultiSurfaceType):
            return "MultiSurface"
        if isinstance(type_, AreaType):
            return "Area"
        if isinstance(type_, MultiAreaType):
            return "MultiArea"
        if isinstance(type_, PolylineType):
            return "Polyline"
        if isinstance(type_, MultiPolylineType):
            return "MultiPolyline"
        if isinstance(type_, CoordType):
            dimensions = type_.getDimensions()
            return f"Coord{len(dimensions)}"
        if isinstance(type_, MultiCoordType):
            dimensions = type_.getDimensions()
            return f"MultiCoord{len(dimensions)}"
        if isinstance(type_, NumericType):
            return "Numeric"
        if isinstance(type_, TextType):
            return "String"
        if isinstance(type_, EnumerationType):
            if attribute.isDomainBoolean():
                return "Boolean"
            name = type_.getName()
            if name:
                return cls._simple_name(name)
            container = attribute.getContainer()
            if container is not None and container.getName():
                return cls._simple_name(container.getName())
            return "Enumeration"
        if isinstance(type_, FormattedType) and _is_date_or_time(type_):
            base = type_.getDefinedBaseDomain()
            if base is not None:
                return cls._simple_name(base.getName())
        if isinstance(type_, TextOIDType):
            oid_type = type_.getOIDType()
            if isinstance(oid_type, TypeAlias):
                aliasing = oid_type.getAliasing()
                if aliasing is not None:
                    return cls._simple_name(aliasing.getName())
            if isinstance(oid_type, Type):
                return cls._simple_name(oid_type.getName())
        if isinstance(type_, TypeAlias):
            aliasing = type_.getAliasing()
            if aliasing is not None:
                return cls._name_from_domain_or_type(aliasing, attribute)

        name = type_.getName()
        if name:
            return cls._simple_name(name)
        return type_.__class__.__name__

    @staticmethod
    def _simple_name(name: Optional[str]) -> str:
        if not name:
            return ""
        if ".." in name:
            return name
        if "." in name:
            return name.split(".")[-1]
        return name


def _is_date_or_time(formatted_type: FormattedType) -> bool:
    base_domain = formatted_type.getDefinedBaseDomain()
    predefined = PredefinedModel.getInstance()
    return base_domain in {predefined.XmlDate, predefined.XmlDateTime, predefined.XmlTime}


def _format_cardinality(cardinality: Optional[Cardinality]) -> str:
    if cardinality is None:
        return "1"

    minimum = cardinality.getMinimum()
    maximum = cardinality.getMaximum()

    left = str(minimum)

    if maximum is None or maximum < 0:
        right = "*"
    else:
        right = str(maximum)

    if maximum is not None and maximum >= 0 and minimum == maximum:
        return str(minimum)

    return f"{left}..{right}"


__all__ = ["render"]

