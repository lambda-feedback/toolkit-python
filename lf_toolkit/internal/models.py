from dataclasses import dataclass
from typing import Dict
from typing import List


@dataclass
class SymbolData:
    latex: str
    aliases: List[str]


SymbolDict = Dict[str, SymbolData]
