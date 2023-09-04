
from dataclasses import dataclass, field

@dataclass
class OpenDocument:
    document: object = None
    filename: str = ""
    page_count: int = 0

@dataclass
class BeginPage:
    document: object = None
    page_number: int = 0
    page_count: int = 0


@dataclass
class EndPage:
    document: object = None

@dataclass
class Element:
    document: object = None
    reader: object = None
    writer: object = None
    builder: object = None
    page_number: int = 0
    page_elements : list = field(default_factory=list)
    ele_idx : int = 0
    ele_type : int = 0
    ele_type_str : str = ""
    element : object = None
