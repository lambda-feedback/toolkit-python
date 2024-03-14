import re

from sympy import Symbol, Basic
from latex2sympy.latex2sympy import process_sympy as latex2sympy

from .utils import SymbolDict

LATEX_SYMBOL_REGEX = re.compile(
    r"(?P<start>\\\(|\$\$|\$)(?P<latex>.*?)(?P<end>\\\)|\$\$|\$)"
)

def extract_latex(symbol):
    """Returns the latex portion of a symbol string.

    Note:
        Only the first matched expression is returned.

    Args:
        symbol (str): The string to extract latex from.

    Returns:
        str: The latex string.
    """
    if (match := LATEX_SYMBOL_REGEX.search(symbol)) is None:
        return symbol

    return match.group("latex")


def parse_latex(response: str, symbols: SymbolDict = {}) -> Basic:
    sympy_symbol_map = {}

    for sym, symDef in symbols.items():
        latex_symbol_str = extract_latex(symDef.latex)

        try:
            latex_symbol = latex2sympy(latex_symbol_str)
        except Exception:
            raise ValueError(
                f"Couldn't parse latex symbol {latex_symbol_str} "
                f"to sympy symbol."
            )

        sympy_symbol_map[latex_symbol] = Symbol(sym)

    expression = latex2sympy(response, sympy_symbol_map)

    if isinstance(expression, list):
        expression = expression.pop()

    return expression.xreplace(sympy_symbol_map)


