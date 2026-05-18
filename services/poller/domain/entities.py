from dataclasses import dataclass
from typing import Any


@dataclass
class Market:
    condition_id: str
    question: str | None = None
    description: str | None = None
    outcomes: list[dict[str, Any]] | None = None
    volume: float | None = None
    end_date: str | None = None


@dataclass
class TagId:
    id: int
    label: str
