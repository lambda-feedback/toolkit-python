from typing import List, Dict
from dataclasses import dataclass

@dataclass
class SymbolData:
    latex: str
    aliases: List[str]

SymbolDict = Dict[str, SymbolData]
