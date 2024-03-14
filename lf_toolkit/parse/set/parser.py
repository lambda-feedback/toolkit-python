from functools import cache
from os import path

from lark import Lark
from lark import Transformer

from .ast import Complement
from .ast import Difference
from .ast import Group
from .ast import Intersection
from .ast import Set
from .ast import SymmetricDifference
from .ast import Term
from .ast import Union


class SetParser:

    @cache
    def __parser(self, latex: bool = False) -> Lark:
        script_dir = path.dirname(path.abspath(__file__))
        grammar_file_name = "latex.lark" if latex else "ascii.lark"
        grammar_file_path = path.join(script_dir, "grammar", grammar_file_name)

        with open(grammar_file_path) as f:
            return Lark(f)

    def parse(self, response: str, latex: bool = False) -> Set:
        tree = self.__parser(latex).parse(response, start="start")

        transformer = SetTransformer(latex)
        ast = transformer.transform(tree)

        return ast


class SetTransformer(Transformer):
    latex: bool

    def __init__(self, latex: bool = False):
        self.latex = latex

    def start(self, items):
        return items[0]

    def complement(self, items):
        return Complement(items[0])

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
