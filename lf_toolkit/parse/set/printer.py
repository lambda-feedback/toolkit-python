from .ast import Set
from .ast import SetTransformer


class LatexPrinter(SetTransformer):
    def print(self, node: Set):
        return self.transform(node)

    def Group(self, expr):
        return f"\\left({expr}\\right)"

    def Complement(self, expr):
        return f"\\overline{{{expr}}}"

    def Union(self, left, right):
        return f"{left} \\cup {right}"

    def Intersection(self, left, right):
        return f"{left} \\cap {right}"

    def Difference(self, left, right):
        return f"{left} \\setminus {right}"

    def SymmetricDifference(self, left, right):
        return f"{left} \\triangle {right}"

    def Term(self, value):
        return value


class ASCIIPrinter(SetTransformer):
    def print(self, node: Set):
        return self.transform(node)

    def Group(self, expr):
        return f"({expr})"

    def Complement(self, expr):
        return f"{expr}'"

    def Union(self, left, right):
        return f"{left} u {right}"

    def Intersection(self, left, right):
        return f"{left} n {right}"

    def Difference(self, left, right):
        return f"{left} \\ {right}"

    def SymmetricDifference(self, left, right):
        return f"{left} /\\ {right}"

    def Term(self, value):
        return value


class UnicodePrinter(SetTransformer):
    def print(self, node: Set):
        return self.transform(node)

    def Group(self, expr):
        return f"({expr})"

    def Complement(self, expr):
        return f"{expr}'"

    def Union(self, left, right):
        return f"{left} ∪ {right}"

    def Intersection(self, left, right):
        return f"{left} ∩ {right}"

    def Difference(self, left, right):
        return f"{left} ∖ {right}"

    def SymmetricDifference(self, left, right):
        return f"{left} △ {right}"

    def Term(self, value):
        return value
