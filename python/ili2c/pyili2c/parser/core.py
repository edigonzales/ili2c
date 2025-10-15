"""Parser that produces instances of :mod:`ili2c.pyili2c.metamodel`."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence
from urllib.parse import urlparse

from antlr4 import CommonTokenStream, FileStream

from ..metamodel import (
    Association,
    AssociationEnd,
    Cardinality,
    Constraint,
    Domain,
    EnumerationType,
    Function,
    FunctionArgument,
    ListType,
    Attribute,
    Model,
    Table,
    Topic,
    TransferDescription,
    Type,
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

        stream = FileStream(str(path), encoding="utf8")
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
        names = ctx.Name()
        types = ctx.iliType()
        for idx, name_token in enumerate(names):
            type_ctx = types[idx] if idx < len(types) else None
            enumeration_value = ctx.enumeration()
            if isinstance(enumeration_value, list):
                enumeration_value = enumeration_value[0] if enumeration_value else None
            if type_ctx is None and enumeration_value is not None:
                enum_ctx = enumeration_value
                literals = [literal.getText() for literal in enum_ctx.enumElement()]
                domain_type = EnumerationType(name=None, literals=literals)
            else:
                domain_type = self._build_type_from_ili(type_ctx) if type_ctx else Type(None)
            domain = Domain(name=name_token.getText(), domain_type=domain_type)
            domains.append(domain)
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
        for definition in ctx.definitions() or []:
            if definition.classDef():
                table = self._build_table(definition.classDef(), kind="CLASS")
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
            element_name = self._restricted_ref_name(ref_ctx)
            element_type = Type(element_name)
            return ListType(element_type=element_type, is_bag=is_bag, cardinality=cardinality)
        if ctx.attrType():
            return self._build_attr_type(ctx.attrType())
        if ctx.numeric():
            return Type(ctx.numeric().getText())
        if ctx.enumeration():
            literals = [literal.getText() for literal in ctx.enumeration().enumElement()]
            return EnumerationType(name=None, literals=literals)
        if ctx.NUMERIC():
            return Type("NUMERIC")
        return Type(ctx.getText())

    def _build_attr_type(self, ctx) -> Type:
        if ctx is None:
            return Type(None)
        if ctx.domainRef():
            return Type(ctx.domainRef().getText())
        if ctx.restrictedStructureRef():
            return Type(self._restricted_ref_name(ctx.restrictedStructureRef()))
        if ctx.iliType():
            return self._build_type_from_ili(ctx.iliType())
        return Type(ctx.getText())

    def _build_type_from_ili(self, ctx) -> Type:
        if ctx is None:
            return Type(None)
        text = ctx.getText()
        if text.startswith("(") and text.endswith(")"):
            inner = text[1:-1]
            if inner:
                literals = [literal for literal in inner.replace(" ", "").split(",") if literal]
                if literals:
                    return EnumerationType(name=None, literals=literals)
        return Type(text)

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

