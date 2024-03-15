from dataclasses import dataclass
from typing import Dict
from typing import List


@dataclass
class SymbolDef:
    latex: str
    aliases: List[str]


SymbolDict = Dict[str, SymbolDef]
