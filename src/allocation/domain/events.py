from dataclasses import dataclass
from typing import Optional
from datetime import date


class Event:
    pass


@dataclass
class OutOfStock(Event):
    sku: str
