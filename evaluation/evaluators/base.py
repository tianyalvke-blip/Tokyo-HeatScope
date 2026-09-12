from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseEvaluator(ABC):
    name: str = "base"

    @abstractmethod
    def evaluate(self, case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        """Return {name, passed, details}; never raise for a bad Agent result."""
