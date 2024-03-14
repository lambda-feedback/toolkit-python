from typing import List, Dict
from dataclasses import dataclass

@dataclass
class SymbolDef:
    latex: str
    aliases: List[str]

SymbolDict = Dict[str, SymbolDef]
