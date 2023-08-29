
from dataclasses import dataclass

@dataclass
class OpenDocument:
    document: object
    filename: str
    page_count: int

@dataclass
class BeginPage:
    document: object
    page_number: int
    page_count: int


@dataclass
class EndPage:
    document: object

@dataclass
class Element:
    document: object
