from .utils import SymbolDict
from .parse_latex import parse_latex
from .parse_sympy import parse_sympy

def parse_response(response_string: str, is_latex: bool, symbols: SymbolDict):
    if is_latex:
        return parse_latex(response_string, symbols)
    else:
        return parse_sympy(response_string, symbols)

    # # TODO: don't allow all transformations
    # return parse_expr(input_string, transformations='all')

