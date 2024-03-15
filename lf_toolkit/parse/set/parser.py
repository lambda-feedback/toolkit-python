from functools import cache
from functools import lru_cache
from functools import reduce
from os import path

from lark import Lark
from lark import LarkError
from lark import Transformer
from lark import UnexpectedInput

from .ast import Complement
from .ast import Difference
from .ast import Group
from .ast import Intersection
from .ast import Set
from .ast import SymmetricDifference
from .ast import Term
from .ast import Union


class ParseError(Exception):
    response: str

    def __init__(self, response: str):
        self.response = response

    def __str__(self):
        if isinstance(self.__cause__, UnexpectedInput):
            # TODO: check if we can also use `match_examples` to provide useful information?
            return self.__cause__.get_context(response=self.response)
        else:
            return "Parse error"


class SetParser:

    @lru_cache(maxsize=1)
    def instance():
        return SetParser()

    @cache
    def __parser(self, latex: bool = False) -> Lark:
        script_dir = path.dirname(path.abspath(__file__))
        grammar_file_name = "latex.lark" if latex else "ascii.lark"
        grammar_file_path = path.join(script_dir, "grammar", grammar_file_name)

        with open(grammar_file_path) as f:
            return Lark(
                grammar=f,
                parser="lalr",
                transformer=SetTransformer(latex),
            )

    def parse(self, response: str, latex: bool = False) -> Set:
        try:
            return self.__parser(latex).parse(response, start="start")
        except LarkError as e:
            raise ParseError(response=response) from e


class SetTransformer(Transformer):
    latex: bool

    def __init__(self, latex: bool = False):
        self.latex = latex

    def start(self, items):
        return items[0]

    def complement(self, items):
        return reduce(
            lambda acc, _: Complement(acc), "'" if self.latex else items[1], items[0]
        )

    def operation(self, items):
        if items[1].data == "union_op":
            return self.union(items)
        elif items[1].data == "intersection_op":
            return self.intersection(items)
        elif items[1].data == "difference_op":
            return self.difference(items)
        elif items[1].data == "symmetric_difference_op":
            return self.symmetric_difference(items)
        else:
            raise ValueError(f"Unknown operation: {items[1].data}")

    def union(self, items):
        return Union(items[0], items[2])

    def intersection(self, items):
        return Intersection(items[0], items[2])

    def difference(self, items):
        return Difference(items[0], items[2])

    def symmetric_difference(self, items):
        return SymmetricDifference(items[0], items[2])

    def ID(self, items):
        return Term(items[0])

    def group(self, items):
        return Group(items[1] if self.latex else items[0])
