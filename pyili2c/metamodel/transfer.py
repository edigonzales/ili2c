"""TransferDescription implementation mirroring the ili2c Java API."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, List, Optional

from .element import Container, Element
from .predefined import PredefinedModel


@dataclass
class TransferDescription(Container):
    """Root container holding models loaded from INTERLIS files."""

    name: str = ""

    def __post_init__(self) -> None:
        super().setName(self.name or "")
        # add predefined INTERLIS model like the Java implementation
        self.add_model(PredefinedModel.getInstance())

    def add_model(self, model: "Model") -> None:
        self.add(model)

    def addModel(self, model: "Model") -> None:  # noqa: N802
        self.add_model(model)

    def getModels(self) -> List["Model"]:
        from .model import Model

        return [m for m in self.elements_of_type(Model)]

    @property
    def models(self) -> List["Model"]:
        return self.getModels()

    def find_model(self, name: str) -> Optional["Model"]:
        for model in self.getModels():
            if model.getName() == name:
                return model
        return None

    def iterator(self) -> Iterator[Element]:
        return super().iterator()

    def getLastModel(self) -> Optional["Model"]:
        models = self.getModels()
        return models[-1] if models else None

    def getModelsFromLastFile(self) -> List["Model"]:
        last = self.getLastModel()
        if last is None or last.getFileName() is None:
            return []
        file_name = last.getFileName()
        return [m for m in self.getModels() if m.getFileName() == file_name]

    def getElement(self, scoped_name: str) -> Optional[Element]:
        for element in self.iterator():
            if isinstance(element, Element) and element.getScopedName() == scoped_name:
                return element
            if isinstance(element, Container):
                result = self._find_in_container(element, scoped_name)
                if result is not None:
                    return result
        return None

    def _find_in_container(self, container: Container, scoped_name: str) -> Optional[Element]:
        for element in container.iterator():
            if element.getScopedName() == scoped_name:
                return element
            if isinstance(element, Container):
                nested = self._find_in_container(element, scoped_name)
                if nested is not None:
                    return nested
        return None

