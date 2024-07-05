from typing import Dict
from typing import List
from typing import TypedDict


class SymbolData(TypedDict):
    latex: str
    aliases: List[str]


SymbolDict = Dict[str, SymbolData]


class Params(TypedDict):
    is_latex: bool
    simplify: bool
    symbols: SymbolDict
