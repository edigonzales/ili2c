"""Parser entry point that builds the Python INTERLIS metamodel."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple
from urllib.parse import urlparse

from antlr4 import CommonTokenStream, FileStream, ParseTreeWalker
from antlr4.error.ErrorListener import ErrorListener

from ...ilirepository import IliRepositoryManager
from ...ilirepository.cache import RepositoryCache
from ..metamodel import (
    AbstractClassDef,
    AssociationDef,
    AttributeDef,
    Cardinality,
    Constraint,
    Domain,
    EnumerationType,
    FormalArgument,
    Function,
    ListType,
    Model,
    RoleDef,
    Table,
    TextType,
    Topic,
    TransferDescription,
    Type,
)
from ..metamodel.element import Container, Element
from .generated.grammars_antlr4.Interlis24Lexer import Interlis24Lexer
from .generated.grammars_antlr4.Interlis24Parser import Interlis24Parser
from .generated.grammars_antlr4.Interlis24ParserListener import Interlis24ParserListener


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def _schema_language_preferences(version: Optional[str]) -> List[str]:
    """Return repository schema language preferences for an INTERLIS version."""

    if not version:
        return []
    parts = version.split(".")
    if len(parts) != 2:
        return []
    major, minor = parts
    try:
        major_int = int(major)
        minor_int = int(minor)
    except ValueError:
        return []

    if major_int != 2:
        return []
    if minor_int == 4:
        return ["ili2_4"]
    if minor_int == 3:
        return ["ili2_3"]
    return []


@dataclass
class ParserSettings:
    """Configuration container influencing how models are resolved."""

    DEFAULT_ILIDIRS = "%ILI_DIR;https://models.interlis.ch"

    ilidirs: str = DEFAULT_ILIDIRS
    repository_cache: Optional[RepositoryCache] = None

    def set_ilidirs(self, ilidirs: str) -> None:
        """Set the semicolon separated list of model directories and repositories."""

        self.ilidirs = ilidirs

    def get_ilidirs(self) -> str:
        """Return the configured ILIDIRS string."""

        return self.ilidirs

    def create_repository_manager(self, repositories: Sequence[str]) -> IliRepositoryManager:
        """Create a repository manager for the provided repository URIs."""

        return IliRepositoryManager(repositories=repositories, cache=self.repository_cache)


class _MetamodelBuilder(Interlis24ParserListener):
    """Parse-tree listener that instantiates metamodel objects."""

    def __init__(
        self,
        td: TransferDescription,
        file_name: str | None,
        tokens: CommonTokenStream | None,
    ):
        self.td = td
        self.file_name = file_name
        self._container_stack: List[Container] = [td]
        self._function_stack: List[Function] = []
        self._domains_by_name: Dict[str, Domain] = {}
        self._viewables_by_scoped: Dict[str, AbstractClassDef] = {}
        self._viewables_by_simple: Dict[str, List[AbstractClassDef]] = {}
        self._pending_extends: List[Tuple[AbstractClassDef, str]] = []
        self._pending_role_targets: List[Tuple[RoleDef, str]] = []
        self._tokens = tokens
        self._pending_inline_enum: Optional[AttributeDef] = None
        self._pending_inline_enum_type: Optional[EnumerationType] = None
        self.imports: List[str] = []
        self.import_relations: List[Tuple[Optional[str], str]] = []
        self.schema_version: Optional[str] = None
        self.schema_language: Optional[str] = None
        self._schema_languages: List[str] = []
        self._register_existing_domains(td)

    # ------------------------------------------------------------------
    # Stack helpers
    # ------------------------------------------------------------------
    def _push(self, container: Container) -> None:
        self._container_stack.append(container)

    def _pop(self) -> None:
        self._container_stack.pop()

    def _current_container(self) -> Container:
        return self._container_stack[-1]

    def _current_model(self) -> Optional[Model]:
        for container in reversed(self._container_stack):
            if isinstance(container, Model):
                return container
        return None

    @property
    def schema_languages(self) -> List[str]:
        return list(self._schema_languages)

    def _register_existing_domains(self, container: Container) -> None:
        for element in container.iterator():
            if isinstance(element, Domain):
                self._register_domain(element)
            if isinstance(element, AbstractClassDef):
                self._register_viewable(element)
            if isinstance(element, Container):
                self._register_existing_domains(element)

    def _register_domain(self, domain: Domain) -> None:
        if domain.getName():
            self._domains_by_name[domain.getName()] = domain
        scoped = domain.getScopedName()
        if scoped:
            self._domains_by_name[scoped] = domain

    def _register_viewable(self, viewable: AbstractClassDef) -> None:
        scoped = viewable.getScopedName()
        if scoped:
            self._viewables_by_scoped[scoped] = viewable
        name = viewable.getName()
        if name:
            self._viewables_by_simple.setdefault(name, []).append(viewable)

    # ------------------------------------------------------------------
    # Listener callbacks
    # ------------------------------------------------------------------
    def enterVersion(self, ctx: Interlis24Parser.VersionContext) -> None:  # noqa: N802
        numbers = ctx.NUMBER()
        if len(numbers) < 2:
            return
        try:
            major = int(numbers[0].getText())
            minor = int(numbers[1].getText())
        except ValueError:
            return
        self.schema_version = f"{major}.{minor}"
        self._schema_languages = _schema_language_preferences(self.schema_version)
        self.schema_language = self._schema_languages[0] if self._schema_languages else None

    def enterModel(self, ctx: Interlis24Parser.ModelContext) -> None:  # noqa: N802
        name = ctx.ID(0).getText()
        model = Model(name)
        model.setFileName(self.file_name)
        if self.schema_version is not None:
            model.setSchemaVersion(self.schema_version)
        if self.schema_language is not None:
            model.setSchemaLanguage(self.schema_language)
        self.td.add_model(model)
        self._push(model)

    def exitModel(self, ctx: Interlis24Parser.ModelContext) -> None:  # noqa: N802
        self._pop()

    def enterTopic(self, ctx: Interlis24Parser.TopicContext) -> None:  # noqa: N802
        name = ctx.ID(0).getText()
        topic = Topic(name)
        container = self._current_container()
        if isinstance(container, Model):
            container.add_topic(topic)
        else:
            container.add(topic)
        self._push(topic)

    def exitTopic(self, ctx: Interlis24Parser.TopicContext) -> None:  # noqa: N802
        self._pop()

    def enterClassDef(self, ctx: Interlis24Parser.ClassDefContext) -> None:  # noqa: N802
        abstract = ctx.classModifiers() is not None
        table = self._create_viewable(ctx.ID(0).getText(), identifiable=True, abstract=abstract)
        if ctx.qualifiedName() is not None:
            base_name = self._qualified_name(ctx.qualifiedName())
            self._pending_extends.append((table, base_name))

    def exitClassDef(self, ctx: Interlis24Parser.ClassDefContext) -> None:  # noqa: N802
        self._pop()

    def enterStructureDef(self, ctx: Interlis24Parser.StructureDefContext) -> None:  # noqa: N802
        abstract = ctx.classModifiers() is not None
        table = self._create_viewable(ctx.ID(0).getText(), identifiable=False, abstract=abstract)
        if ctx.qualifiedName() is not None:
            base_name = self._qualified_name(ctx.qualifiedName())
            self._pending_extends.append((table, base_name))

    def exitStructureDef(self, ctx: Interlis24Parser.StructureDefContext) -> None:  # noqa: N802
        self._pop()

    def enterImportsStmt(self, ctx: Interlis24Parser.ImportsStmtContext) -> None:  # noqa: N802
        current_model = self._current_model()
        importer_name = current_model.getName() if current_model is not None else None
        if self._tokens is None:
            for qname in ctx.qualifiedName():
                name = self._qualified_name(qname)
                if name:
                    self.imports.append(name)
                    self.import_relations.append((importer_name, name))
            return

        tokens = self._tokens.tokens
        start = ctx.start.tokenIndex
        stop = ctx.stop.tokenIndex
        index = start + 1  # skip IMPORTS keyword

        while index <= stop:
            token = tokens[index]
            token_type = token.type

            if token_type == Interlis24Parser.SEMICOLON:
                break
            if token_type == Interlis24Parser.COMMA:
                index += 1
                continue

            if token_type == Interlis24Parser.ID and (token.text or "").upper() == "UNQUALIFIED":
                index += 1
                if index > stop:
                    break
                token = tokens[index]
                token_type = token.type

            name_parts: List[str] = []
            while index <= stop:
                token = tokens[index]
                token_type = token.type
                if token_type in (Interlis24Parser.ID, Interlis24Parser.INTERLIS):
                    name_parts.append(token.text or "")
                    index += 1
                    if index <= stop and tokens[index].type == Interlis24Parser.DOT:
                        name_parts.append(".")
                        index += 1
                        continue
                    break
                else:
                    break

            name = "".join(name_parts).strip()
            if name:
                self.imports.append(name)
                self.import_relations.append((importer_name, name))
            else:
                index += 1

    def enterAssociationDef(self, ctx: Interlis24Parser.AssociationDefContext) -> None:  # noqa: N802
        association = AssociationDef(ctx.ID(0).getText())
        container = self._current_container()
        if isinstance(container, Topic):
            container.add_viewable(association)
        else:
            container.add(association)
        self._register_viewable(association)
        self._push(association)

    def exitAssociationDef(self, ctx: Interlis24Parser.AssociationDefContext) -> None:  # noqa: N802
        self._pop()

    def _create_viewable(self, name: str, identifiable: bool, abstract: bool = False) -> Table:
        table = Table(name=name, identifiable=identifiable, abstract=abstract)
        container = self._current_container()
        if isinstance(container, Topic):
            container.add_class(table)
        else:
            container.add(table)
        self._register_viewable(table)
        self._push(table)
        return table

    def enterRoleDef(self, ctx: Interlis24Parser.RoleDefContext) -> None:  # noqa: N802
        container = self._current_container()
        if not isinstance(container, AssociationDef):
            return
        role = RoleDef(ctx.ID().getText())
        if ctx.roleModifier() is not None:
            role.setExternal(True)
        card_ctx = ctx.roleCardinality()
        if card_ctx is not None:
            minimum = int(card_ctx.NUMBER(0).getText())
            if card_ctx.STAR() is not None:
                maximum = -1
            elif card_ctx.RANGE() is not None:
                maximum = int(card_ctx.NUMBER(1).getText())
            else:
                maximum = minimum
            role.setCardinality(Cardinality(minimum, maximum))
        target_name = self._qualified_name(ctx.qualifiedName())
        self._pending_role_targets.append((role, target_name))
        container.addRole(role)

    def enterAttrDef(self, ctx: Interlis24Parser.AttrDefContext) -> None:  # noqa: N802
        if ctx.COLON() is None:
            name_token = ctx.ID()
            if name_token is not None and self._pending_inline_enum_type is not None:
                name = name_token.getText()
                if name:
                    self._pending_inline_enum_type.literals.append(name)
            return

        table = self._current_container()
        attr = AttributeDef(ctx.ID().getText())
        self._pending_inline_enum = None
        self._pending_inline_enum_type = None
        card_ctx = ctx.cardinality()
        if card_ctx is not None:
            minimum = int(card_ctx.NUMBER(0).getText())
            if card_ctx.STAR() is not None:
                maximum = -1
            elif card_ctx.RANGE() is not None:
                maximum = int(card_ctx.NUMBER(1).getText())
            else:
                maximum = minimum
            attr.setCardinality(Cardinality(minimum, maximum))
        if ctx.mandatoryAttr() is not None:
            attr.setMandatory(True)
            if attr.getCardinality() is None:
                attr.setCardinality(Cardinality(1, 1))
        attr.setDomain(self._build_type(ctx.typeRef()))
        self._apply_inline_enumeration(ctx, attr)
        if isinstance(table, Table):
            table.add_attribute(attr)
        else:
            table.add(attr)

    def enterDomainStatement(self, ctx: Interlis24Parser.DomainStatementContext) -> None:  # noqa: N802
        domain = Domain(ctx.ID().getText())
        container = self._current_container()
        container.add(domain)
        domain_type = ctx.domainType()
        if domain_type.enumerationType() is not None:
            enum_type = EnumerationType(domain.getName())
            enum_type.literals.extend(
                self._enum_literal(item) for item in domain_type.enumerationType().enumItem()
            )
            enum_type.setName(domain.getName())
            domain.setType(enum_type)
        else:
            domain.setType(self._build_type(domain_type.typeRef()))
        self._register_domain(domain)

    def enterFunctionDef(self, ctx: Interlis24Parser.FunctionDefContext) -> None:  # noqa: N802
        function = Function(ctx.ID().getText())
        container = self._current_container()
        container.add(function)
        self._function_stack.append(function)

    def exitFunctionDef(self, ctx: Interlis24Parser.FunctionDefContext) -> None:  # noqa: N802
        function = self._function_stack.pop()
        if ctx.typeRef() is not None:
            function.setReturnType(self._build_type(ctx.typeRef()))

    def enterParam(self, ctx: Interlis24Parser.ParamContext) -> None:  # noqa: N802
        if not self._function_stack:
            return
        argument = FormalArgument(ctx.ID().getText())
        argument.setType(self._build_type(ctx.typeRef()))
        self._function_stack[-1].addArgument(argument)

    def enterConstraintDef(self, ctx: Interlis24Parser.ConstraintDefContext) -> None:  # noqa: N802
        expression = ""
        expr_ctx = ctx.constraintExpression()
        if expr_ctx is not None:
            expression = expr_ctx.getText()
        constraint = Constraint(None)
        if expression:
            constraint.expression = expression
        constraint.mandatory = ctx.MANDATORY() is not None
        container = self._current_container()
        if isinstance(container, Table):
            container.add_constraint(constraint)
        else:
            container.add(constraint)

    def enterUniqueDef(self, ctx: Interlis24Parser.UniqueDefContext) -> None:  # noqa: N802
        container = self._current_container()
        if not isinstance(container, Table):
            return
        exprs = [self._qualified_name(expr.qualifiedName()) for expr in ctx.uniqueExprList().uniqueExpr()]
        constraint = Constraint(None)
        constraint.expression = "UNIQUE " + ", ".join(exprs)
        container.add_constraint(constraint)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def finalize(self) -> None:
        for viewable, target_name in self._pending_extends:
            base = self._resolve_viewable(target_name, viewable)
            if base is not None:
                viewable.setExtending(base)
        for role, target_name in self._pending_role_targets:
            destination = self._resolve_viewable(target_name, role)
            if destination is not None:
                role.setDestination(destination)

    def _enum_literal(self, item_ctx: Interlis24Parser.EnumItemContext) -> str:
        text = item_ctx.getText()
        if text.startswith('"') and text.endswith('"'):
            return text[1:-1]
        return text

    def _build_list_type(self, ctx: Interlis24Parser.TypeRefContext, is_bag: bool) -> ListType:
        name = "BAG" if is_bag else "LIST"
        list_type = ListType(name)
        list_type.setIsBag(is_bag)
        card_ctx = ctx.listCardinality()
        if card_ctx is not None:
            minimum = int(card_ctx.NUMBER(0).getText())
            if card_ctx.STAR() is not None:
                maximum = -1
            else:
                maximum = int(card_ctx.NUMBER(1).getText())
            list_type.setCardinality(minimum, maximum)
        element_method = getattr(ctx, "typeRef", None)
        element_ctx = None
        if element_method is not None:
            try:
                element_ctx = element_method(0)
            except TypeError:  # pragma: no cover - defensive
                element_ctx = element_method()
        if isinstance(element_ctx, list):
            element_ctx = element_ctx[0] if element_ctx else None
        if element_ctx is None and element_method is not None:
            maybe_list = element_method()
            if isinstance(maybe_list, list):
                element_ctx = maybe_list[0] if maybe_list else None
            else:
                element_ctx = maybe_list
        element_type = self._build_type(element_ctx)
        list_type.setElementType(element_type)
        if element_type is not None and element_type.getName():
            list_type.setName(f"{name} OF {element_type.getName()}")
        return list_type

    def _build_type(self, ctx: Optional[Interlis24Parser.TypeRefContext]):
        if ctx is None:
            return None
        if getattr(ctx, "BAG", None) and ctx.BAG() is not None:
            return self._build_list_type(ctx, is_bag=True)
        if ctx.LIST() is not None:
            return self._build_list_type(ctx, is_bag=False)
        enum_method = getattr(ctx, "enumerationType", None)
        if enum_method is not None:
            enum_ctx = enum_method()
            if enum_ctx is not None:
                enum_type = EnumerationType(None)
                enum_type.literals.extend(
                    self._enum_literal(item) for item in enum_ctx.enumItem()
                )
                return enum_type
        if hasattr(ctx, "numericRange") and ctx.numericRange() is not None:
            text = ctx.numericRange().getText()
            type_obj = Type(text)
            type_obj.setName(text)
            return type_obj
        qualified_ctx = ctx.qualifiedName()
        if qualified_ctx is None:
            return None
        base_name = self._qualified_name(qualified_ctx)
        domain = self._resolve_domain(base_name)
        if domain is not None:
            return domain
        type_obj: Type
        if base_name.upper() == "TEXT":
            type_obj = TextType(base_name)
        else:
            type_obj = Type(base_name)
        suffix_method = getattr(ctx, "typeSuffix", None)
        suffixes = []
        if suffix_method is not None:
            maybe_suffixes = suffix_method()
            if isinstance(maybe_suffixes, list):
                suffixes = maybe_suffixes
            elif maybe_suffixes is not None:
                suffixes = [maybe_suffixes]
        suffix_text = ""
        for suffix in suffixes:
            suffix_text += suffix.getText()
            if isinstance(type_obj, TextType) and suffix.STAR() is not None:
                type_obj.setLength(int(suffix.NUMBER().getText()))
        name = base_name + suffix_text if suffix_text else base_name
        type_obj.setName(name)
        return type_obj

    def _qualified_name(self, ctx: Interlis24Parser.QualifiedNameContext) -> str:
        return ctx.getText()

    def _resolve_domain(self, name: str) -> Optional[Domain]:
        if name in self._domains_by_name:
            return self._domains_by_name[name]
        model = self._current_model()
        if model is not None:
            scoped = f"{model.getName()}.{name}"
            if scoped in self._domains_by_name:
                return self._domains_by_name[scoped]
        return self._domains_by_name.get(name)

    def _resolve_viewable(self, name: str, element: Optional[Element]) -> Optional[AbstractClassDef]:
        if not name:
            return None
        if name in self._viewables_by_scoped:
            return self._viewables_by_scoped[name]
        scoped_candidate = self.td.getElement(name)
        if isinstance(scoped_candidate, AbstractClassDef):
            return scoped_candidate
        simple_name = name.split(".")[-1]
        candidates = self._viewables_by_simple.get(simple_name, [])
        if len(candidates) == 1:
            return candidates[0]
        container = element.getContainer() if isinstance(element, Element) else None
        while isinstance(container, Element):
            prefix = container.getScopedName()
            if prefix:
                scoped = f"{prefix}.{simple_name}"
                candidate = self._viewables_by_scoped.get(scoped)
                if candidate is not None:
                    return candidate
            container = container.getContainer() if isinstance(container, Element) else None
        return candidates[0] if candidates else None


    def _apply_inline_enumeration(
        self, ctx: Interlis24Parser.AttrDefContext, attr: AttributeDef
    ) -> None:
        literals = self._extract_inline_enum_literals(ctx)
        if not literals:
            return

        enum_type = EnumerationType(attr.getName())
        enum_type.literals.extend(literals)
        enum_type.setName(attr.getName())
        attr.setDomain(enum_type)
        self._pending_inline_enum = attr
        self._pending_inline_enum_type = enum_type

    def _extract_inline_enum_literals(
        self, ctx: Interlis24Parser.AttrDefContext
    ) -> Optional[List[str]]:
        if self._tokens is None:
            return None

        start = ctx.start.tokenIndex
        stop = ctx.stop.tokenIndex
        if start is None or stop is None:
            return None

        literals: List[str] = []
        inside = False
        for token in self._tokens.tokens[start : stop + 1]:
            ttype = token.type
            if ttype == Interlis24Parser.LPAREN:
                inside = True
                continue
            if not inside:
                continue
            if ttype == Interlis24Parser.RPAREN:
                break
            if ttype == Interlis24Parser.COMMA:
                continue
            if ttype == Interlis24Parser.ID or ttype == Interlis24Parser.STRING:
                text = token.text or ""
                if ttype == Interlis24Parser.STRING and len(text) >= 2:
                    text = text[1:-1]
                literals.append(text)

        return literals if literals else None


class _SilentErrorListener(ErrorListener):
    """Error listener that suppresses syntax messages."""

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):  # noqa: D401
        return


def parse(path: str | Path, settings: Optional[ParserSettings] = None) -> TransferDescription:
    """Parse an INTERLIS model file and return a populated TransferDescription.

    The parser follows ``IMPORTS`` statements by locating additional ``.ili``
    files using the directories and repositories configured in ``settings``.
    Each imported file is parsed exactly once.
    """

    root_path = Path(path).resolve()
    logger.info("Starting INTERLIS parse of '%s'", root_path)
    td = TransferDescription()

    parser_settings = settings or ParserSettings()
    search_dirs, repositories = _resolve_search_sources(root_path, parser_settings)
    if search_dirs:
        logger.info(
            "Using search directories: %s",
            ", ".join(str(path) for path in search_dirs),
        )
    repository_manager: Optional[IliRepositoryManager] = None
    if repositories:
        repository_manager = parser_settings.create_repository_manager(repositories)
        logger.info(
            "Configured repository manager with sources: %s",
            ", ".join(repositories),
        )

    to_parse: List[Path] = [root_path]
    parsed_files: Set[Path] = set()
    all_import_relations: List[Tuple[Optional[str], str]] = []

    while to_parse:
        current = to_parse.pop()
        current = current.resolve()
        if current in parsed_files or not current.exists():
            continue

        logger.info("Parsing INTERLIS file '%s'", current)
        builder = _parse_single_file(current, td)
        parsed_files.add(current)
        schema_languages = builder.schema_languages
        all_import_relations.extend(builder.import_relations)

        for import_name in builder.imports:
            model_name = import_name.split(".")[0]
            if not model_name:
                continue
            if model_name.upper() == "INTERLIS":
                continue
            if td.find_model(model_name) is not None:
                continue
            logger.info(
                "Resolving import '%s' referenced from '%s'", model_name, current
            )
            import_path = _resolve_import_path(
                model_name,
                current.parent,
                search_dirs,
                repository_manager,
                schema_languages,
            )
            if import_path is None:
                lookup_dirs = _format_directories([current.parent, *search_dirs])
                repo_info = ", ".join(repositories) if repositories else "(none)"
                logger.error(
                    "Failed to resolve import '%s'. Searched directories: %s. Repositories: %s",
                    model_name,
                    lookup_dirs,
                    repo_info,
                )
                raise FileNotFoundError(
                    f"Unable to locate INTERLIS model '{model_name}' while resolving import."
                )
            resolved = import_path.resolve()
            logger.info(
                "Resolved import '%s' to '%s'", model_name, resolved
            )
            if resolved not in parsed_files and resolved not in to_parse:
                to_parse.append(resolved)

    root_models = [model for model in td.getModels() if model.getFileName() == root_path.name]
    for model in root_models:
        td.remove(model)
        td.add_model(model)

    _validate_import_versions(td, all_import_relations)

    return td


def _validate_import_versions(
    td: TransferDescription, import_relations: Iterable[Tuple[Optional[str], str]]
) -> None:
    """Ensure imported models share the same INTERLIS schema version as their importers."""

    for importer_name, import_name in import_relations:
        if not importer_name:
            continue
        importer_model = td.find_model(importer_name)
        if importer_model is None:
            continue
        importer_version = importer_model.getSchemaVersion()
        if not importer_version:
            continue
        base_name = import_name.split(".")[0]
        if not base_name:
            continue
        imported_model = td.find_model(base_name)
        if imported_model is None:
            continue
        imported_version = imported_model.getSchemaVersion()
        if not imported_version:
            continue
        if importer_version != imported_version:
            raise ValueError(
                "Model '%s' (INTERLIS %s) cannot import model '%s' (INTERLIS %s)."
                % (importer_name, importer_version, base_name, imported_version)
            )


def _parse_single_file(file_path: Path, td: TransferDescription) -> _MetamodelBuilder:
    input_stream = FileStream(str(file_path), encoding="utf8")
    lexer = Interlis24Lexer(input_stream)
    tokens = CommonTokenStream(lexer)
    parser = Interlis24Parser(tokens)
    parser.removeErrorListeners()
    parser.addErrorListener(_SilentErrorListener())
    tree = parser.iliFile()

    builder = _MetamodelBuilder(td, file_path.name, tokens)
    walker = ParseTreeWalker()
    walker.walk(builder, tree)
    builder.finalize()
    return builder


def _resolve_import_path(
    model_name: str,
    current_dir: Path,
    search_dirs: Iterable[Path],
    repository_manager: Optional[IliRepositoryManager],
    schema_languages: Sequence[str] | None,
) -> Optional[Path]:
    base_name = model_name.split(".")[0]
    if not base_name:
        return None

    directories: List[Path] = []
    seen: Set[Path] = set()
    for directory in [current_dir, *search_dirs]:
        if directory is None:
            continue
        directory = directory.resolve()
        if directory in seen:
            continue
        seen.add(directory)
        directories.append(directory)

    target_lower = base_name.lower()
    for directory in directories:
        exact = directory / f"{base_name}.ili"
        if exact.exists():
            logger.info(
                "Located model '%s' directly in directory '%s'", base_name, directory
            )
            return exact
        try:
            for candidate in directory.glob("*.ili"):
                if candidate.stem.lower() == target_lower:
                    logger.info(
                        "Located model '%s' by case-insensitive match in directory '%s'",
                        base_name,
                        directory,
                    )
                    return candidate
        except FileNotFoundError:  # pragma: no cover - defensive
            continue
    if repository_manager is not None:
        preferences = list(schema_languages or [])
        if not preferences:
            preferences = [None]
        seen_langs: Set[Optional[str]] = set()
        for language in preferences:
            if language in seen_langs:
                continue
            seen_langs.add(language)
            logger.info(
                "Searching repositories for model '%s' (schema_language=%s)",
                base_name,
                language or "any",
            )
            if language is None:
                metadata = repository_manager.find_model(base_name)
            else:
                metadata = repository_manager.find_model(
                    base_name, schema_language=language
                )
            if metadata is None:
                logger.info(
                    "No repository entry found for model '%s' (schema_language=%s)",
                    base_name,
                    language or "any",
                )
                continue
            logger.info(
                "Found model '%s' in repository '%s' (schema_language=%s)",
                base_name,
                metadata.repository_uri,
                metadata.schema_language,
            )
            path = repository_manager.access.fetch_model_file(
                metadata, repository_manager.model_ttl
            )
            if path is None:
                logger.error(
                    "Failed to download model '%s' from repository '%s'",
                    base_name,
                    metadata.repository_uri,
                )
                continue
            return path
    return None


def _resolve_search_sources(
    root_path: Path, settings: ParserSettings
) -> Tuple[List[Path], List[str]]:
    search_dirs: List[Path] = []
    repositories: List[str] = []
    seen_dirs: Set[Path] = set()
    seen_repos: Set[str] = set()

    def add_directory(candidate: Path) -> None:
        try:
            resolved = candidate.resolve()
        except OSError:  # pragma: no cover - defensive guard
            resolved = candidate
        if resolved in seen_dirs:
            return
        seen_dirs.add(resolved)
        search_dirs.append(resolved)

    def add_repository(uri: str) -> None:
        normalized = uri.rstrip("/") + "/" if uri else uri
        if normalized in seen_repos:
            return
        seen_repos.add(normalized)
        repositories.append(normalized)

    add_directory(root_path.parent)

    ilidirs = settings.get_ilidirs()
    for part in ilidirs.split(";"):
        entry = part.strip()
        if not entry:
            continue
        entry = entry.replace("%ILI_DIR", str(root_path.parent))

        parsed = urlparse(entry)
        scheme = parsed.scheme.lower()
        if scheme in {"http", "https"}:
            add_repository(parsed.geturl())
            continue
        if scheme == "file":
            path = Path(parsed.path)
            add_directory(path)
            add_repository(parsed.geturl())
            continue

        add_directory(Path(entry))

    return search_dirs, repositories


def _format_directories(directories: Iterable[Path]) -> str:
    unique: List[str] = []
    seen: Set[str] = set()
    for directory in directories:
        resolved = str(directory.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(resolved)
    return ", ".join(unique)
