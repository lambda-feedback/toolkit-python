from dataclasses import dataclass

from ..internal.models import SymbolDict


@dataclass
class Params:
    is_latex: bool
    simplify: bool
    symbols: SymbolDict


@dataclass
class Preview:
    latex: str
    sympy: str
    feedback: str


@dataclass
class Result:
    preview: Preview
