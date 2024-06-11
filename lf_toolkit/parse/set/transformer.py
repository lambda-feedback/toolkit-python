from sympy import And
from sympy import Complement
from sympy import FiniteSet
from sympy import Intersection
from sympy import Not
from sympy import Or
from sympy import Symbol
from sympy import SymmetricDifference
from sympy import Union
from sympy import UniversalSet
from sympy import Xor

from .ast import SetTransformer


class SymPyTransformer(SetTransformer):
    def Group(self, expr):
        # TODO: sympy has no concept of parentheses for sets,
        #       so we just return the child expression for now.
        #       If we want to check correctness of parenthesis,
        #       we probably need to check the syntax tree we're
        #       building, not using sympy at all.
        return expr

    def Complement(self, expr):
        return Complement(UniversalSet, expr)

    def Union(self, left, right):
        return Union(left, right)

    def Intersection(self, left, right):
        return Intersection(left, right)

    def Difference(self, left, right):
        return Complement(left, right)

    def SymmetricDifference(self, left, right):
        return SymmetricDifference(left, right)

    def Term(self, expr):
        return FiniteSet(Symbol(expr))

    def Universe(self):
        return UniversalSet


class SymPyBooleanTransformer(SetTransformer):
    def __init__(self):
        self._symbol_map = {}

    def _get_symbol(self, expr):
        if expr not in self._symbol_map:
            self._symbol_map[expr] = Symbol(expr)
        return self._symbol_map[expr]

    def Group(self, expr):
        return expr

    def Complement(self, expr):
        return Not(expr)

    def Union(self, left, right):
        return Or(left, right)

    def Intersection(self, left, right):
        return And(left, right)

    def Difference(self, left, right):
        return And(left, Not(right))

    def SymmetricDifference(self, left, right):
        return Xor(left, right)

    def Term(self, expr):
        return self._get_symbol(expr)

    def Universe(self):
        return Or(*self._symbol_map.values())
