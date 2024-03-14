from sympy import Complement
from sympy import FiniteSet
from sympy import Intersection
from sympy import Symbol
from sympy import SymmetricDifference
from sympy import Union
from sympy import UniversalSet

from .ast import SetTransformer


class SymPyTransformer(SetTransformer):
    def Group(self, expr):
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
