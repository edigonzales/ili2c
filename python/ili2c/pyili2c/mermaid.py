"""Render INTERLIS transfer descriptions as Mermaid class diagrams."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List

from .metamodel import (
    Association as MetaAssociation,
    AssociationEnd,
    Attribute,
    Cardinality,
    EnumTreeValueType,
    EnumerationType,
    ListType,
    Model,
    Table,
    Topic,
    TransferDescription,
    Type,
    Viewable,
)


@dataclass
class Namespace:
    """Logical grouping of nodes (e.g. per topic)."""

    label: str
    node_order: List[str] = field(default_factory=list)


@dataclass
class Node:
    fqn: str
    display_name: str
    stereotypes: List[str] = field(default_factory=list)
    attributes: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)

    def add_stereotypes(self, labels: Iterable[str]) -> None:
        for label in labels:
            if label not in self.stereotypes:
                self.stereotypes.append(label)


@dataclass
class Inheritance:
    sub_fqn: str
    sup_fqn: str


@dataclass
class Association:
    left_fqn: str
    right_fqn: str
    left_card: str
    right_card: str
    label: str | None = None


@dataclass
class Diagram:
    namespaces: Dict[str, Namespace] = field(default_factory=dict)
    nodes: Dict[str, Node] = field(default_factory=dict)
    inheritances: List[Inheritance] = field(default_factory=list)
    associations: List[Association] = field(default_factory=list)

    def get_or_create_namespace(self, label: str) -> Namespace:
        if label not in self.namespaces:
            self.namespaces[label] = Namespace(label=label)
        return self.namespaces[label]


def render(td: TransferDescription) -> str:
    """Render ``td`` as a Mermaid class diagram string."""

    diagram = build_diagram(td)
    renderer = _MermaidRenderer()
    return renderer.render(diagram)


def build_diagram(td: TransferDescription) -> Diagram:
    diagram = Diagram()
    diagram.get_or_create_namespace("<root>")

    models: Iterable[Model]
    try:
        models = td.getModelsFromLastFile()
    except AttributeError:
        models = td.getModels()
    if not models:
        models = td.getModels()

    for model in models:
        _collect_model_level(diagram, model)
        for topic in model.getTopics():
            _collect_topic(diagram, model, topic)
    return diagram


def _collect_model_level(diagram: Diagram, model: Model) -> None:
    for table in model.getTables():
        _register_table_node(diagram, model, table, topic=None)

    for association in model.getAssociations():
        _register_association(diagram, model, association, topic=None)

    for function in model.getFunctions():
        namespace = diagram.get_or_create_namespace("<root>")
        fqn = f"{model.getName()}.{function.getName()}"
        diagram.nodes.setdefault(
            fqn,
            Node(fqn=fqn, display_name=function.getName(), stereotypes=["Function"]),
        )
        if fqn not in namespace.node_order:
            namespace.node_order.append(fqn)

    for domain in model.getDomains():
        namespace = diagram.get_or_create_namespace("<root>")
        fqn = f"{model.getName()}.{domain.getName()}"
        domain_type = domain.getType()
        if isinstance(domain_type, EnumerationType):
            node = diagram.nodes.setdefault(
                fqn,
                Node(fqn=fqn, display_name=domain.getName(), stereotypes=["Enumeration"]),
            )
            node.attributes = [literal for literal in domain_type.getLiterals()]
            if fqn not in namespace.node_order:
                namespace.node_order.append(fqn)
        elif isinstance(domain_type, EnumTreeValueType):
            node = diagram.nodes.setdefault(
                fqn,
                Node(fqn=fqn, display_name=domain.getName(), stereotypes=["Enumeration"]),
            )
            node.attributes = _enum_tree_literals(diagram, model, domain_type)
            if fqn not in namespace.node_order:
                namespace.node_order.append(fqn)


def _collect_topic(diagram: Diagram, model: Model, topic: Topic) -> None:
    for table in topic.getStructures():
        _register_table_node(diagram, model, table, topic=topic)
    for table in topic.getClasses():
        _register_table_node(diagram, model, table, topic=topic)
    for association in topic.getAssociations():
        _register_association(diagram, model, association, topic=topic)


def _enum_tree_literals(
    diagram: Diagram, model: Model, enum_tree: EnumTreeValueType
) -> List[str]:
    base_literals = _enumeration_literals(diagram, model, enum_tree.getBaseDomain())
    if not base_literals:
        return []

    values: List[str] = []
    seen: set[str] = set()
    for literal in base_literals:
        for prefix in _enumeration_prefixes(literal):
            if prefix not in seen:
                values.append(prefix)
                seen.add(prefix)
        if literal not in seen:
            values.append(literal)
            seen.add(literal)
    return values


def _enumeration_literals(diagram: Diagram, model: Model, reference: str) -> List[str]:
    base_fqn = _domain_fqn(model, reference)
    if base_fqn:
        node = diagram.nodes.get(base_fqn)
        if node is not None and node.attributes:
            return list(node.attributes)

    candidates = _candidate_domain_names(reference)
    for domain in model.getDomains():
        if domain.getName() in candidates:
            domain_type = domain.getType()
            if isinstance(domain_type, EnumerationType):
                return [literal for literal in domain_type.getLiterals()]

    node = diagram.nodes.get(reference)
    if node is not None and node.attributes:
        return list(node.attributes)
    return []


def _enumeration_prefixes(literal: str) -> List[str]:
    parts = [part for part in literal.split(".") if part]
    prefixes: List[str] = []
    for index in range(1, len(parts)):
        prefixes.append(".".join(parts[:index]))
    return prefixes


def _domain_fqn(model: Model, reference: str | None) -> str | None:
    if not reference:
        return None
    if "." in reference:
        return reference
    return f"{model.getName()}.{reference}"


def _candidate_domain_names(reference: str | None) -> List[str]:
    if not reference:
        return []
    parts = [part for part in reference.split(".") if part]
    if not parts:
        return []
    return [parts[-1]]


def _register_table_node(diagram: Diagram, model: Model, table: Table, *, topic: Topic | None) -> None:
    namespace_label = (
        f"{model.getName()}::{topic.getName()}" if topic is not None else "<root>"
    )
    namespace = diagram.get_or_create_namespace(namespace_label)

    fqn = _viewable_fqn(table)

    node = diagram.nodes.setdefault(
        fqn,
        Node(fqn=fqn, display_name=table.getName()),
    )

    stereotypes: List[str] = []
    if table.isAbstract():
        stereotypes.append("Abstract")
    if not table.isIdentifiable():
        stereotypes.append("Structure")
    if stereotypes:
        node.add_stereotypes(stereotypes)

    node.attributes = [
        _format_attribute(attr) for attr in table.getAttributes()
    ]

    node.methods = [
        _format_constraint_name(idx, constraint.getName())
        for idx, constraint in enumerate(table.getConstraints(), start=1)
    ]

    if fqn not in namespace.node_order:
        namespace.node_order.append(fqn)

    parent = table.getExtending()
    if parent is not None:
        parent_fqn = _viewable_fqn(parent)
        inheritance = Inheritance(sub_fqn=fqn, sup_fqn=parent_fqn)
        if inheritance not in diagram.inheritances:
            diagram.inheritances.append(inheritance)


def _register_association(
    diagram: Diagram,
    model: Model,
    association: MetaAssociation,
    *,
    topic: Topic | None,
) -> None:
    ends = list(association.getEnds())
    if len(ends) < 2:
        return

    left_end = ends[0]
    for right_end in ends[1:]:
        left_fqn = _association_end_target(left_end, model=model, topic=topic)
        right_fqn = _association_end_target(right_end, model=model, topic=topic)
        if not left_fqn or not right_fqn:
            continue
        left_card = _format_cardinality(left_end.getCardinality())
        right_card = _format_cardinality(right_end.getCardinality())
        edge = Association(
            left_fqn=left_fqn,
            right_fqn=right_fqn,
            left_card=left_card,
            right_card=right_card,
            label=association.getName(),
        )
        diagram.associations.append(edge)


def _format_attribute(attribute: Attribute) -> str:
    card = _format_cardinality(attribute.getCardinality())
    type_name = _attribute_type_name(attribute.getDomain())
    return f"{attribute.getName()}[{card}] : {type_name}"


def _association_end_target(
    end: AssociationEnd, *, model: Model, topic: Topic | None
) -> str | None:
    target_name = end.getTarget().getName()
    if not target_name:
        return None
    viewable = _find_viewable(model, target_name, topic)
    if viewable is not None:
        return _viewable_fqn(viewable)
    return target_name


def _find_viewable(model: Model, reference: str, current_topic: Topic | None) -> Viewable | None:
    parts = [part for part in reference.split(".") if part]
    if not parts:
        return None

    remaining = parts
    if remaining[0] == model.getName():
        remaining = remaining[1:]

    target_topic: Topic | None = None
    if remaining:
        for topic in model.getTopics():
            if topic.getName() == remaining[0]:
                target_topic = topic
                remaining = remaining[1:]
                break

    if not remaining:
        return None

    name = remaining[0]
    candidates: List[Viewable] = []
    if target_topic is not None:
        candidates.extend(target_topic.getClasses())
        candidates.extend(target_topic.getStructures())
    else:
        if current_topic is not None and "." not in reference:
            candidates.extend(current_topic.getClasses())
            candidates.extend(current_topic.getStructures())
        candidates.extend(model.getTables())
        for topic in model.getTopics():
            candidates.extend(topic.getClasses())
            candidates.extend(topic.getStructures())

    for candidate in candidates:
        if candidate.getName() == name:
            return candidate
    return None


def _viewable_fqn(viewable: Viewable) -> str:
    scoped = viewable.getScopedName()
    if scoped:
        return scoped
    name = viewable.getName()
    return name if name else "unnamed"


def _format_constraint_name(index: int, name: str | None) -> str:
    label = name if name else f"constraint{index}"
    return f"{label}()"


def _attribute_type_name(domain: Type) -> str:
    if isinstance(domain, ListType):
        return _attribute_type_name(domain.getElementType())
    if hasattr(domain, "getDisplayName"):
        return domain.getDisplayName()
    name = domain.getName()
    return name if name else "Unknown"


def _simple_name(name: str | None) -> str | None:
    if name is None:
        return None
    return name.split(".")[-1] if name else None


def _format_cardinality(cardinality: Cardinality) -> str:
    minimum = cardinality.getMinimum()
    maximum = cardinality.getMaximum()
    if maximum < 0:
        right = "*"
    else:
        right = str(maximum)
    if maximum >= 0 and minimum == maximum:
        return str(minimum)
    return f"{minimum}..{right}"


class _MermaidRenderer:
    def render(self, diagram: Diagram) -> str:
        lines: List[str] = ["classDiagram"]

        for label, namespace in diagram.namespaces.items():
            if label == "<root>":
                continue
            lines.append(f"  namespace {self._namespace_id(label)} {{")
            for fqn in namespace.node_order:
                node = diagram.nodes[fqn]
                self._append_node(lines, node, indent="    ")
            lines.append("  }")

        root_namespace = diagram.namespaces.get("<root>")
        if root_namespace:
            for fqn in root_namespace.node_order:
                node = diagram.nodes[fqn]
                self._append_node(lines, node, indent="  ")

        for inherit in diagram.inheritances:
            lines.append(
                f"  {inherit.sub_fqn} --|> {inherit.sup_fqn}"
            )

        for assoc in diagram.associations:
            label = f" : {self._escape(assoc.label)}" if assoc.label else ""
            lines.append(
                f"  {assoc.left_fqn} \"{assoc.left_card}\" -- \"{assoc.right_card}\" {assoc.right_fqn}{label}"
            )

        return "\n".join(lines) + "\n"

    @staticmethod
    def _namespace_id(label: str) -> str:
        return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in label)

    def _append_node(self, lines: List[str], node: Node, *, indent: str) -> None:
        lines.append(
            f"{indent}class {node.fqn}[\"{self._escape(node.display_name)}\"] {{"
        )
        for stereo in node.stereotypes:
            lines.append(f"{indent}  <<{stereo}>>")
        for attr in node.attributes:
            lines.append(f"{indent}  {self._escape(attr)}")
        for method in node.methods:
            lines.append(f"{indent}  {self._escape(method)}")
        lines.append(f"{indent}}}")

    @staticmethod
    def _escape(value: str | None) -> str:
        if value is None:
            return ""
        return value.replace("\"", "\\\"")

