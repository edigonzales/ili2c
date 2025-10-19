"""Parser that produces instances of :mod:`ili2c.pyili2c.metamodel`."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from antlr4 import CommonTokenStream, InputStream
from antlr4.tree.Tree import TerminalNodeImpl

from ..metamodel import (
    AreaType,
    Association,
    AssociationEnd,
    BlackboxType,
    Cardinality,
    Constraint,
    CoordType,
    Domain,
    EnumTreeValueType,
    EnumerationType,
    FormattedType,
    Function,
    FunctionArgument,
    ListType,
    Attribute,
    Model,
    MultiAreaType,
    MultiCoordType,
    MultiPolylineType,
    MultiSurfaceType,
    NumericType,
    ObjectType,
    PolylineType,
    ReferenceType,
    SurfaceType,
    Table,
    TextOIDType,
    TextType,
    Topic,
    TransferDescription,
    Type,
    TypeAlias,
    Viewable,
)
from .generated.grammars_antlr4.InterlisLexer import InterlisLexer
from .generated.grammars_antlr4.InterlisParserPy import InterlisParserPy


class ParserSettings:
    """Settings that influence how models are located."""

    def __init__(
        self,
        ilidirs: Optional[Iterable[str]] = None,
        repository_cache=None,
        repositories: Optional[Iterable[str]] = None,
        repository_manager=None,
        repository_meta_ttl: float = 86400.0,
        repository_model_ttl: float = 7 * 24 * 3600.0,
    ) -> None:
        self._raw_ilidirs: List[str] = []
        self._directory_ilidirs: List[str] = []
        self._ilidir_repositories: List[str] = []
        self.repository_cache = repository_cache
        self.repository_meta_ttl = repository_meta_ttl
        self.repository_model_ttl = repository_model_ttl
        self._explicit_repository_manager = repository_manager is not None
        self._repository_manager = repository_manager
        self._repositories: List[str] = []
        if repositories is not None:
            for repository in repositories:
                self.add_repository(repository)
        if ilidirs is not None:
            self.set_ilidirs(ilidirs)

    def set_ilidirs(self, value: Iterable[str] | str) -> None:
        if isinstance(value, str):
            parts = [p for p in value.split(";") if p]
        else:
            parts = [p for p in value if p]
        self._raw_ilidirs = parts
        self._directory_ilidirs = []
        self._ilidir_repositories = []
        for entry in parts:
            if entry == "%ILI_DIR":
                self._directory_ilidirs.append(entry)
                continue
            parsed = urlparse(entry)
            if parsed.scheme in {"http", "https", "file"}:
                repository_uri = _normalise_repository_uri(entry)
                if repository_uri:
                    self._ilidir_repositories.append(repository_uri)
                continue
            self._directory_ilidirs.append(entry)
        if not self._explicit_repository_manager:
            self._repository_manager = None

    def get_ilidirs(self) -> Sequence[str]:
        return tuple(self._raw_ilidirs)

    def iter_directory_ilidirs(self) -> Sequence[str]:
        return tuple(self._directory_ilidirs)

    def add_repository(self, uri: str) -> None:
        uri = _normalise_repository_uri(uri)
        if not uri:
            return
        if uri not in self._repositories:
            self._repositories.append(uri)
            if not self._explicit_repository_manager:
                self._repository_manager = None

    def set_repository_manager(self, manager) -> None:
        self._repository_manager = manager
        self._explicit_repository_manager = manager is not None

    def get_repository_manager(self):
        if self._repository_manager is not None:
            return self._repository_manager
        repositories: List[str] = []
        seen: set[str] = set()
        for uri in (*self._repositories, *self._ilidir_repositories):
            if uri and uri not in seen:
                seen.add(uri)
                repositories.append(uri)
        from ...ilirepository import IliRepositoryManager
        if not repositories:
            repositories = list(IliRepositoryManager.DEFAULT_REPOSITORIES)
        from ...ilirepository.cache import RepositoryCache

        cache = self.repository_cache or RepositoryCache()
        self.repository_cache = cache
        self._repository_manager = IliRepositoryManager(
            repositories=repositories,
            cache=cache,
            meta_ttl=self.repository_meta_ttl,
            model_ttl=self.repository_model_ttl,
        )
        return self._repository_manager


def _collapse_ws_outside_strings(text: str) -> str:
    result: List[str] = []
    in_string = False
    escape = False
    quote_char = ""
    for ch in text:
        if in_string:
            result.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote_char:
                in_string = False
        else:
            if ch in {"'", '"'}:
                in_string = True
                quote_char = ch
                result.append(ch)
            elif ch.isspace():
                continue
            else:
                result.append(ch)
    return "".join(result)


def _find_char_outside_groups(
    text: str, start: int, target: str, *, end: Optional[int] = None
) -> int:
    depth = 0
    in_string = False
    escape = False
    quote_char = ""
    limit = len(text) if end is None else min(len(text), end)
    i = start
    while i < limit:
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote_char:
                in_string = False
        else:
            if ch in {"'", '"'}:
                in_string = True
                quote_char = ch
            elif ch in "([{":
                depth += 1
            elif ch in ")]}":
                if depth > 0:
                    depth -= 1
            elif depth == 0 and ch == target:
                return i
        i += 1
    return -1


def _is_identifier_char(ch: str) -> bool:
    return ch.isalnum() or ch in {"_", "."}


def _find_keyword_outside_groups(
    text: str, start: int, keyword: str, *, end: Optional[int] = None
) -> int:
    depth = 0
    in_string = False
    escape = False
    quote_char = ""
    limit = len(text) if end is None else min(len(text), end)
    i = start
    klen = len(keyword)

    while i < limit:
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote_char:
                in_string = False
        else:
            if ch in {"'", '"'}:
                in_string = True
                quote_char = ch
            elif ch in "([{":
                depth += 1
            elif ch in ")]}":
                if depth > 0:
                    depth -= 1
            elif depth == 0 and text.startswith(keyword, i):
                before_idx = i - 1
                after_idx = i + klen
                before_valid = before_idx >= 0 and _is_identifier_char(text[before_idx])
                after_valid = after_idx < limit and _is_identifier_char(text[after_idx])
                if not before_valid and not after_valid:
                    return i
        i += 1
    return -1


def _preprocess_unique_where(text: str) -> Tuple[str, Dict[str, str]]:
    placeholders: Dict[str, str] = {}
    parts: List[str] = []
    idx = 0
    token = "UNIQUE"
    length = len(text)

    while idx < length:
        pos = text.find(token, idx)
        if pos == -1:
            parts.append(text[idx:])
            break

        parts.append(text[idx:pos])
        constraint_end = _find_char_outside_groups(text, pos, ";")
        if constraint_end == -1:
            parts.append(text[pos:])
            break

        segment = text[pos:constraint_end]
        where_idx = _find_keyword_outside_groups(segment, len(token), "WHERE")
        if where_idx != -1:
            colon_idx = _find_char_outside_groups(
                segment, where_idx + len("WHERE"), ":", end=len(segment)
            )
            if colon_idx != -1:
                placeholder = f"UniqueWherePlaceholder{len(placeholders)}"
                condition_raw = segment[where_idx + len("WHERE") : colon_idx]
                condition = _collapse_ws_outside_strings(condition_raw)
                placeholders[placeholder] = condition
                segment = segment[:where_idx] + placeholder + segment[colon_idx:]

        parts.append(segment)
        parts.append(";")
        idx = constraint_end + 1

    return ("".join(parts), placeholders)


class _ParseContext:
    def __init__(self, settings: ParserSettings) -> None:
        self.settings = settings
        self.models: dict[str, Model] = {}
        self._parsed_files: set[Path] = set()
        self._repository_manager = settings.get_repository_manager()

    def parse_file(self, path: Path, td: TransferDescription) -> Model:
        path = path.resolve()
        if path in self._parsed_files:
            # Return existing model if already loaded
            for model in td.getModels():
                if getattr(model, "_source", None) == path:
                    return model
            raise ValueError(f"File {path} already parsed but model not registered")

        self._parsed_files.add(path)

        original_text = path.read_text(encoding="utf8")
        processed_text, unique_where_mapping = _preprocess_unique_where(original_text)
        stream = InputStream(processed_text)
        stream.name = str(path)
        lexer = InterlisLexer(stream)
        tokens = CommonTokenStream(lexer)
        parser = InterlisParserPy(tokens)
        tree = parser.interlis2def()

        schema_version = tree.Dec().getText() if tree.Dec() else None
        schema_language = None
        if schema_version:
            schema_language = f"ili{schema_version.replace('.', '_')}"

        model_ctx = tree.modeldef()
        if model_ctx is None:
            raise ValueError(f"No model definition found in {path}")

        builder = _ModelBuilder(
            schema_language=schema_language,
            schema_version=schema_version,
            context=self,
            source_path=path,
            unique_where_mapping=unique_where_mapping,
        )
        model = builder.build_model(model_ctx)
        model._source = path  # type: ignore[attr-defined]
        td.add_model(model)
        self.models[model.getName()] = model

        # Resolve imports
        for import_name in model.getImports():
            if import_name in self.models:
                continue
            import_path = self._resolve_import(import_name, path)
            if import_path is None:
                raise FileNotFoundError(f"Model '{import_name}' referenced from {model.getName()} not found")
            self.parse_file(import_path, td)

        return model

    # ------------------------------------------------------------------
    def _resolve_import(self, name: str, base_path: Path) -> Optional[Path]:
        candidates: List[Path] = []
        seen: set[Path] = set()

        def add_candidate(candidate: Path) -> None:
            candidate = candidate.resolve()
            if candidate not in seen and candidate.exists():
                seen.add(candidate)
                candidates.append(candidate)

        def add_directory(directory: Path) -> None:
            base_name = f"{name}.ili"
            variations = {base_name, base_name.lower(), base_name.upper()}
            if name:
                mixed_case = f"{name[0].lower()}{name[1:]}"
                variations.add(f"{mixed_case}.ili")
            for variant in variations:
                add_candidate(directory / variant)

        add_directory(base_path.parent)

        for entry in self.settings.iter_directory_ilidirs():
            candidate_dir = base_path.parent if entry == "%ILI_DIR" else Path(entry)
            add_directory(candidate_dir)

        manager = self._repository_manager
        if manager is not None:
            schema_language = None
            for model in self.models.values():
                if getattr(model, "_source", None) == base_path:
                    schema_language = model.getSchemaLanguage()
                    break
            path_str = manager.get_model_file(name, schema_language=schema_language)
            if path_str:
                remote_path = Path(path_str)
                if remote_path.exists():
                    add_candidate(remote_path)

        return candidates[0] if candidates else None


def parse(path: str | Path, settings: Optional[ParserSettings] = None) -> TransferDescription:
    """Parse ``path`` and return a :class:`TransferDescription`."""

    settings = settings or ParserSettings()
    context = _ParseContext(settings=settings)
    primary_path = Path(path).resolve()
    td = TransferDescription()
    td.setPrimarySource(primary_path)
    context.parse_file(primary_path, td)
    return td


def _normalise_repository_uri(uri: str) -> str:
    if not uri:
        return uri
    if not uri.endswith("/"):
        return uri + "/"
    return uri


# =============================================================================
# Helpers that convert ANTLR contexts into metamodel objects
# =============================================================================


@dataclass
class _ModelBuilder:
    schema_language: Optional[str]
    schema_version: Optional[str]
    context: _ParseContext
    source_path: Path
    unique_where_mapping: Dict[str, str] = field(default_factory=dict)
    pending_extends: List[tuple[Viewable, str]] = field(default_factory=list)
    active_model: Optional[Model] = None

    def build_model(self, ctx) -> Model:  # type: ignore[override]
        name_tokens = ctx.Name()
        name = name_tokens[0].getText() if name_tokens else ""
        model = Model(name=name, schema_language=self.schema_language, schema_version=self.schema_version)
        self.active_model = model
        self.context.models[name] = model

        for import_name in self._extract_imports(ctx):
            model.add_import(import_name)

        for domain_ctx in ctx.domainDef() or []:
            for domain in self._build_domains(domain_ctx):
                model.add_domain(domain)

        for fn_ctx in ctx.functionDecl() or []:
            function = self._build_function(fn_ctx)
            model.add_function(function)

        for struct_ctx in ctx.structureDef() or []:
            table = self._build_table(struct_ctx, kind="STRUCTURE")
            table._identifiable = False
            model.add_table(table)

        for class_ctx in ctx.classDef() or []:
            table = self._build_table(class_ctx, kind="CLASS")
            model.add_table(table)

        for topic_ctx in ctx.topicDef() or []:
            topic = self._build_topic(topic_ctx)
            model.add_topic(topic)

        self._resolve_pending_extends(model)
        self.active_model = None
        return model

    # ------------------------------------------------------------------
    def _extract_imports(self, ctx) -> List[str]:
        imports: List[str] = []
        collecting = False
        for child in ctx.getChildren():
            text = child.getText()
            if text == "IMPORTS":
                collecting = True
                continue
            if collecting:
                if text == ";":
                    collecting = False
                    continue
                if text in {",", "UNQUALIFIED", "INTERLIS"}:
                    continue
                imports.append(text)
        return imports

    # ------------------------------------------------------------------
    def _build_domains(self, ctx) -> List[Domain]:
        domains: List[Domain] = []
        children = list(ctx.getChildren())

        idx = 0
        while idx < len(children):
            child = children[idx]

            # Skip optional leading DOMAIN keyword and stray semicolons
            if isinstance(child, TerminalNodeImpl):
                token_type = child.symbol.type
                if token_type == InterlisParserPy.DOMAIN or token_type == InterlisParserPy.SEMI:
                    idx += 1
                    continue

            if not isinstance(child, TerminalNodeImpl) or child.symbol.type != InterlisParserPy.Name:
                idx += 1
                continue

            domain_name = child.getText()
            idx += 1

            # Skip optional generic parameters "(<ABSTRACT|FINAL|GENERIC>)"
            if idx < len(children) and isinstance(children[idx], TerminalNodeImpl) and children[idx].symbol.type == InterlisParserPy.LPAR:
                depth = 0
                while idx < len(children):
                    nested = children[idx]
                    if isinstance(nested, TerminalNodeImpl):
                        if nested.symbol.type == InterlisParserPy.LPAR:
                            depth += 1
                        elif nested.symbol.type == InterlisParserPy.RPAR:
                            depth -= 1
                            if depth == 0:
                                idx += 1
                                break
                    idx += 1

            # Skip optional "EXTENDS <DomainRef>"
            if idx < len(children) and isinstance(children[idx], TerminalNodeImpl) and children[idx].symbol.type == InterlisParserPy.EXTENDS:
                idx += 1  # EXTENDS
                if idx < len(children):
                    idx += 1  # DomainRefContext

            # Advance to '=' token
            while idx < len(children):
                node = children[idx]
                if isinstance(node, TerminalNodeImpl) and node.symbol.type == InterlisParserPy.EQ:
                    idx += 1
                    break
                idx += 1
            else:
                break

            # Skip optional MANDATORY keyword
            if idx < len(children) and isinstance(children[idx], TerminalNodeImpl) and children[idx].symbol.type == InterlisParserPy.MANDATORY:
                idx += 1

            expr_parts: List[str] = []
            while idx < len(children):
                node = children[idx]
                if isinstance(node, TerminalNodeImpl):
                    token_type = node.symbol.type
                    if token_type == InterlisParserPy.SEMI:
                        idx += 1
                        break
                    if token_type == InterlisParserPy.CONSTRAINTS:
                        # Skip constraint specification until ';'
                        idx += 1
                        while idx < len(children):
                            skip_node = children[idx]
                            if isinstance(skip_node, TerminalNodeImpl) and skip_node.symbol.type == InterlisParserPy.SEMI:
                                break
                            idx += 1
                        continue
                expr_parts.append(node.getText())
                idx += 1

            expr_text = "".join(expr_parts).strip()
            if expr_text:
                domain_type = self._type_from_text(expr_text)
                if isinstance(domain_type, EnumerationType) and not domain_type.getName():
                    domain_type.setName(domain_name)
            else:
                domain_type = Type(None)

            domains.append(Domain(name=domain_name, domain_type=domain_type))

        return domains

    def _build_function(self, ctx) -> Function:
        name = ctx.Name()[0].getText()
        function = Function(name=name)

        for arg_ctx in ctx.argumentDef() or []:
            arg_type_ctx = arg_ctx.argumentType()
            arg_type = self._build_attr_type_def(arg_type_ctx.attrTypeDef()) if arg_type_ctx else Type(None)
            argument = FunctionArgument(arg_ctx.Name().getText(), arg_type)
            function.add_argument(argument)

        if ctx.BOOLEAN():
            return_type = Type("BOOLEAN")
        elif ctx.attrTypeDef():
            return_type = self._build_attr_type_def(ctx.attrTypeDef())
        else:
            names = ctx.Name()
            return_type = Type(names[1].getText()) if len(names) > 1 else Type(None)
        function.setReturnType(return_type)
        return function

    def _build_topic(self, ctx) -> Topic:
        name = ctx.Name()[0].getText()
        topic = Topic(name)
        topic_oid_text: Optional[str] = None
        for basket, domain_text in self._iter_oid_domains(ctx):
            oid_type = self._type_from_text(domain_text)
            if basket:
                topic.setBasketOIDType(oid_type)
            else:
                topic.setOIDType(oid_type)
                topic_oid_text = domain_text
        for definition in ctx.definitions() or []:
            if definition.classDef():
                table = self._build_table(definition.classDef(), kind="CLASS")
                if (
                    topic_oid_text
                    and table.getOIDType() is None
                    and table.isIdentifiable()
                ):
                    table.setOIDType(self._type_from_text(topic_oid_text))
                topic.add_class(table)
            elif definition.structureDef():
                table = self._build_table(definition.structureDef(), kind="STRUCTURE")
                table._identifiable = False
                topic.add_structure(table)
            elif definition.associationDef():
                association = self._build_association(definition.associationDef())
                topic.add_association(association)
        return topic

    def _build_table(self, ctx, *, kind: str) -> Table:
        name = ctx.Name()[0].getText()
        abstract = bool(ctx.ABSTRACT())
        identifiable = kind == "CLASS" and ctx.NO() is None
        table = Table(name=name, kind=kind, abstract=abstract, identifiable=identifiable)

        oid_type = self._extract_oid_type(ctx)
        if oid_type is not None:
            table.setOIDType(oid_type)

        ref_ctx = None
        if hasattr(ctx, "classOrStructureRef"):
            ref_ctx = ctx.classOrStructureRef()
        if not ref_ctx and hasattr(ctx, "structureRef"):
            ref_ctx = ctx.structureRef()
        if isinstance(ref_ctx, list):
            ref_ctx = ref_ctx[0] if ref_ctx else None
        if ref_ctx is not None:
            ref_name = ref_ctx.getText()
            if ref_name:
                self.pending_extends.append((table, ref_name))

        body = ctx.classOrStructureDef()
        if body:
            for attr_ctx in body.attributeDef() or []:
                attribute = self._build_attribute(attr_ctx)
                table.add_attribute(attribute)
            for constraint_ctx in body.constraintDef() or []:
                constraint = self._build_constraint(constraint_ctx)
                table.add_constraint(constraint)
        return table

    def _extract_oid_type(self, ctx) -> Optional[Type]:
        for basket, domain_text in self._iter_oid_domains(ctx):
            if not basket:
                return self._type_from_text(domain_text)
        return None

    def _iter_oid_domains(self, ctx) -> Iterable[tuple[bool, str]]:
        children = list(ctx.getChildren()) if hasattr(ctx, "getChildren") else []
        idx = 0
        while idx < len(children):
            child = children[idx]
            if not isinstance(child, TerminalNodeImpl) or child.symbol.type != InterlisParserPy.OID:
                idx += 1
                continue
            if idx > 0:
                prev = children[idx - 1]
                if isinstance(prev, TerminalNodeImpl) and prev.symbol.type == InterlisParserPy.NO:
                    idx += 1
                    continue
            basket = False
            if idx > 0:
                prev = children[idx - 1]
                if isinstance(prev, TerminalNodeImpl) and prev.symbol.type == InterlisParserPy.BASKET:
                    basket = True
            domain_text, next_idx = self._collect_oid_domain(children, idx)
            if domain_text:
                yield basket, domain_text
            idx = next_idx

    def _collect_oid_domain(self, children: List, start_idx: int) -> tuple[str, int]:
        parts: List[str] = []
        saw_as = False
        idx = start_idx + 1
        while idx < len(children):
            node = children[idx]
            if isinstance(node, TerminalNodeImpl):
                token_type = node.symbol.type
                if token_type == InterlisParserPy.SEMI:
                    idx += 1
                    break
                if token_type == InterlisParserPy.AS:
                    saw_as = True
                    idx += 1
                    continue
            if saw_as:
                parts.append(node.getText())
            idx += 1
        return "".join(parts).strip(), idx

    def _build_attribute(self, ctx) -> Attribute:
        attr_type_ctx = ctx.attrTypeDef()
        attr_type = self._build_attr_type_def(attr_type_ctx) if attr_type_ctx else Type(None)
        mandatory = bool(attr_type_ctx and attr_type_ctx.MANDATORY())
        attribute = Attribute(ctx.Name().getText(), attr_type, mandatory=mandatory)
        return attribute

    def _build_constraint(self, ctx) -> Constraint:
        name: Optional[str] = None
        expression_text = ctx.getText()
        mandatory = False

        if ctx.mandatoryConstraint():
            mctx = ctx.mandatoryConstraint()
            mandatory = True
            if mctx.Name():
                name = mctx.Name().getText()
            expression_text = mctx.expression().getText()
        elif ctx.expression():
            expression_text = ctx.expression().getText()

        for placeholder, condition in list(self.unique_where_mapping.items()):
            if placeholder in expression_text:
                expression_text = expression_text.replace(placeholder, f"WHERE{condition}")
                del self.unique_where_mapping[placeholder]

        return Constraint(name=name, expression=expression_text, mandatory=mandatory)

    def _resolve_pending_extends(self, model: Model) -> None:
        for viewable, ref_name in list(self.pending_extends):
            target = self._lookup_viewable(ref_name, model)
            if target is not None:
                if isinstance(viewable, Table):
                    viewable.setExtending(target)  # type: ignore[arg-type]
                elif isinstance(viewable, Association):
                    viewable.setExtending(target)  # type: ignore[arg-type]
        self.pending_extends.clear()

    def _lookup_viewable(self, ref_name: str, default_model: Model) -> Optional[Viewable]:
        parts = [part for part in ref_name.split(".") if part]
        if not parts:
            return None

        model = default_model
        if parts[0] in self.context.models:
            model = self.context.models[parts[0]]
            parts = parts[1:]
        elif parts[0] == default_model.getName():
            parts = parts[1:]

        topic: Optional[Topic] = None
        if parts:
            for candidate in model.getTopics():
                if candidate.getName() == parts[0]:
                    topic = candidate
                    parts = parts[1:]
                    break

        if not parts:
            return None

        viewable_name = parts[0]
        candidates: List[Viewable] = []
        if topic is not None:
            candidates.extend(topic.getClasses())
            candidates.extend(topic.getStructures())
        else:
            candidates.extend(model.getTables())
            for candidate_topic in model.getTopics():
                candidates.extend(candidate_topic.getClasses())
                candidates.extend(candidate_topic.getStructures())

        for candidate in candidates:
            if candidate.getName() == viewable_name:
                return candidate
        return None

    def _build_association(self, ctx) -> Association:
        name_tokens = ctx.Name() or []
        name = name_tokens[0].getText() if name_tokens else None
        association = Association(name=name)

        for role_ctx in ctx.roleDef() or []:
            role_name = role_ctx.Name().getText()
            refs = role_ctx.restrictedClassOrAssRef()
            if isinstance(refs, list):
                refs = refs[-1] if refs else None
            target_name = refs.getText() if refs is not None else None
            target_type = Type(target_name)
            cardinality = self._build_cardinality(role_ctx.cardinality()) or Cardinality(0, 1)
            connector = self._extract_role_connector(role_ctx)
            is_external = bool(role_ctx.EXTERNAL())
            end = AssociationEnd(
                role_name,
                target_type,
                cardinality=cardinality,
                role_kind=connector,
                is_external=is_external,
            )
            association.add_end(end)

        for attr_ctx in ctx.attributeDef() or []:
            attribute = self._build_attribute(attr_ctx)
            association.add_attribute(attribute)

        for constraint_ctx in ctx.constraintDef() or []:
            constraint = self._build_constraint(constraint_ctx)
            association.add_constraint(constraint)

        return association

    def _extract_role_connector(self, ctx) -> str:
        minus_tokens = ctx.MINUS() or []
        connector = "".join(token.getText() for token in minus_tokens if hasattr(token, "getText"))
        lt_token = ctx.LT()
        gt_token = ctx.GT()
        if lt_token:
            connector += "<"
        if gt_token:
            connector += ">"
        return connector or "--"

    # ------------------------------------------------------------------
    def _build_attr_type_def(self, ctx) -> Type:
        if ctx is None:
            return Type(None)
        if ctx.LIST() or ctx.BAG():
            is_bag = ctx.BAG() is not None
            cardinality = self._build_cardinality(ctx.cardinality())
            ref_ctx = ctx.restrictedStructureRef()
            element_type = self._build_object_type_from_ctx(ref_ctx)
            return ListType(element_type=element_type, is_bag=is_bag, cardinality=cardinality)
        if ctx.attrType():
            return self._build_attr_type(ctx.attrType())
        if ctx.numeric():
            return self._parse_numeric_type(ctx.numeric().getText())
        enumeration_ctx = ctx.enumeration()
        if isinstance(enumeration_ctx, list):
            enumeration_ctx = enumeration_ctx[0] if enumeration_ctx else None
        if enumeration_ctx is not None:
            return self._build_enumeration_type(enumeration_ctx.getText())
        if ctx.NUMERIC():
            return NumericType(name="NUMERIC")
        return self._type_from_text(ctx.getText())

    def _build_attr_type(self, ctx) -> Type:
        if ctx is None:
            return Type(None)
        if ctx.domainRef():
            ref_text = self._context_text(ctx.domainRef())
            return TypeAlias(ref_text) if ref_text else Type(None)
        if ctx.restrictedStructureRef():
            return self._build_object_type_from_ctx(ctx.restrictedStructureRef())
        if ctx.iliType():
            return self._build_type_from_ili(ctx.iliType())
        return self._type_from_text(ctx.getText())

    def _build_type_from_ili(self, ctx) -> Type:
        if ctx is None:
            return Type(None)
        text = ctx.getText()
        return self._type_from_text(text)

    def _build_cardinality(self, ctx) -> Optional[Cardinality]:
        if ctx is None:
            return None
        numbers = [int(token.getText()) for token in ctx.PosNumber()]
        minimum = numbers[0] if numbers else 0
        maximum: int
        if len(numbers) >= 2:
            maximum = numbers[1]
        elif ctx.MUL():
            maximum = -1
        else:
            maximum = minimum
        if ctx.MUL() and len(numbers) >= 2:
            maximum = -1
        elif ctx.MUL() and not numbers:
            minimum = 0
            maximum = -1
        return Cardinality(minimum, maximum)

    def _build_enumeration_type(self, text: str, *, name: Optional[str] = None) -> EnumerationType:
        literals = self._flatten_enumeration_literals(text)
        return EnumerationType(name=name, literals=literals)

    def _flatten_enumeration_literals(self, text: str) -> List[str]:
        if not text:
            return []
        value = text.strip()
        if value.startswith("(") and value.endswith(")"):
            value = value[1:-1]
        stack: List[str] = []
        token = ""
        literals: List[str] = []
        i = 0
        while i < len(value):
            ch = value[i]
            if ch == "(":
                prefix = token.strip()
                if prefix:
                    stack.append(prefix)
                token = ""
                i += 1
                continue
            if ch == ")":
                if token.strip():
                    literals.append(self._combine_enum_parts(stack, token.strip()))
                    token = ""
                if stack:
                    stack.pop()
                i += 1
                continue
            if ch == ",":
                if token.strip():
                    literals.append(self._combine_enum_parts(stack, token.strip()))
                    token = ""
                i += 1
                continue
            token += ch
            i += 1
        if token.strip():
            literals.append(self._combine_enum_parts(stack, token.strip()))
        return [literal for literal in literals if literal]

    @staticmethod
    def _combine_enum_parts(stack: List[str], token: str) -> str:
        parts = [part for part in stack if part]
        clean_token = token.strip()
        if clean_token:
            parts.append(clean_token)
        return ".".join(parts)

    def _type_from_text(self, text: Optional[str]) -> Type:
        if not text:
            return Type(None)
        value = text.strip()
        if not value:
            return Type(None)
        upper = value.upper()

        if value.startswith("(") and ")" in value:
            return self._build_enumeration_type(value)

        if upper.startswith("FORMAT"):
            return self._parse_formatted_type(value)

        if upper.startswith("ALLOF"):
            base = value[len("ALLOF") :].strip()
            return EnumTreeValueType(base)

        if upper.startswith("BLACKBOX"):
            remainder = value[len("BLACKBOX") :].strip()
            kind = remainder.split()[0] if remainder else ""
            return BlackboxType(kind=kind.upper())

        if upper.startswith("OID"):
            remainder = value[len("OID") :]
            base_type = self._type_from_text(remainder)
            return TextOIDType(base_type)

        if upper.startswith("MTEXT") or upper.startswith("TEXT"):
            return self._parse_text_type(value)

        if upper.startswith("NAME"):
            return TextType(kind="NAME")

        if upper.startswith("URI"):
            return TextType(kind="URI")

        if upper.startswith("NUMERIC"):
            range_text = value[len("NUMERIC") :]
            minimum, maximum = self._split_range(range_text.strip("[]")) if range_text else (None, None)
            return NumericType(name="NUMERIC", minimum=minimum, maximum=maximum)

        geometry_type = self._parse_geometry_type(value)
        if geometry_type is not None:
            return geometry_type

        if re.match(r"^-?\d", value):
            minimum, maximum = self._split_range(value)
            if minimum is not None or maximum is not None:
                return NumericType(minimum=minimum, maximum=maximum)

        if "REFERENCETO" in upper:
            return self._parse_reference_type(value)

        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", value):
            return TypeAlias(value)

        return Type(value)

    def _parse_text_type(self, text: str) -> TextType:
        match = re.match(r"^(?P<kind>M?TEXT)(?:\*(?P<length>\d+))?$", text, flags=re.IGNORECASE)
        if match:
            kind = match.group("kind") or "TEXT"
            length_text = match.group("length")
            length = int(length_text) if length_text else None
            normalized = kind.upper() != "MTEXT"
            return TextType(kind=kind.upper(), max_length=length, normalized=normalized)
        return TextType(kind=text.upper())

    def _parse_numeric_type(self, text: str) -> NumericType:
        minimum, maximum = self._split_range(text)
        return NumericType(minimum=minimum, maximum=maximum)

    def _split_range(self, text: str) -> tuple[Optional[str], Optional[str]]:
        if not text:
            return (None, None)
        value = text.strip()
        if not value:
            return (None, None)
        if ".." in value:
            left, _, right = value.partition("..")
            left = left.strip()
            right = right.strip()
            return (left or None, right or None)
        value = value.strip()
        return (value or None, value or None)

    def _parse_formatted_type(self, text: str) -> Type:
        upper = text.upper()
        remainder = text[len("FORMAT") :]
        remainder = remainder.lstrip()
        if upper.replace(" ", "").startswith("FORMATBASEDON"):
            rest = remainder
            if rest.upper().startswith("BASED"):
                rest = rest[len("BASED") :].lstrip()
            if rest.upper().startswith("ON"):
                rest = rest[len("ON") :].lstrip()
            base, _, picture = rest.partition("(")
            base = base.strip()
            picture = picture[:-1] if picture.endswith(")") else picture
            return FormattedType(base_domain=base, picture=picture or None)
        idx = 0
        while idx < len(remainder) and (remainder[idx].isalnum() or remainder[idx] in "._"):
            idx += 1
        base_domain = remainder[:idx].strip()
        range_text = remainder[idx:]
        minimum = maximum = None
        if range_text:
            if ".." in range_text:
                left, _, right = range_text.partition("..")
                minimum = self._strip_quotes(left)
                maximum = self._strip_quotes(right)
            else:
                minimum = self._strip_quotes(range_text)
        return FormattedType(base_domain=base_domain, minimum=minimum, maximum=maximum)

    def _parse_reference_type(self, text: str) -> ReferenceType:
        upper = text.upper()
        index = upper.find("REFERENCETO")
        if index >= 0:
            target = text[index + len("REFERENCETO") :].strip()
            return ReferenceType(target=target)
        return ReferenceType(target=text)

    @staticmethod
    def _strip_quotes(value: str) -> Optional[str]:
        if not value:
            return None
        stripped = value.strip()
        if stripped.startswith("\"") and stripped.endswith("\""):
            return stripped[1:-1]
        if stripped.startswith("'") and stripped.endswith("'"):
            return stripped[1:-1]
        return stripped or None

    def _build_object_type_from_ctx(self, ctx) -> Type:
        name = self._restricted_ref_name(ctx)
        return ObjectType(target=name) if name else Type(None)

    def _parse_geometry_type(self, text: str) -> Type | None:
        upper = text.upper().strip()

        if self._matches_geometry_prefix(upper, "MULTISURFACE"):
            return MultiSurfaceType(definition=text)
        if self._matches_geometry_prefix(upper, "MULTIAREA"):
            return MultiAreaType(definition=text)
        if self._matches_geometry_prefix(upper, "MULTIPOLYLINE"):
            return MultiPolylineType(definition=text)
        if self._matches_geometry_prefix(upper, "MULTICOORD"):
            return MultiCoordType(definition=text)
        if self._matches_geometry_prefix(upper, "SURFACE"):
            return SurfaceType(definition=text)
        if self._matches_geometry_prefix(upper, "AREA"):
            return AreaType(definition=text)
        if self._matches_geometry_prefix(upper, "POLYLINE"):
            return PolylineType(definition=text)
        if self._matches_geometry_prefix(upper, "COORD"):
            return CoordType(definition=text)
        return None

    @staticmethod
    def _matches_geometry_prefix(value: str, prefix: str) -> bool:
        if not value.startswith(prefix):
            return False
        if len(value) == len(prefix):
            return True
        next_part = value[len(prefix) :]
        next_char = next_part[0]
        if not next_char.isalpha():
            return True
        return next_part.startswith("WITH") or next_part.startswith("WITHOUT")

    def _context_text(self, ctx) -> Optional[str]:
        if ctx is None:
            return None
        if isinstance(ctx, list):
            ctx = ctx[0] if ctx else None
        if ctx is None:
            return None
        return ctx.getText()

    def _restricted_ref_name(self, ctx) -> Optional[str]:
        if ctx is None:
            return None
        if ctx.structureRef():
            ref = ctx.structureRef()
            if isinstance(ref, list):
                ref = ref[0]
            return ref.getText()
        if ctx.classOrStructureRef():
            ref = ctx.classOrStructureRef()
            if isinstance(ref, list):
                ref = ref[0]
            return ref.getText()
        return ctx.getText()

