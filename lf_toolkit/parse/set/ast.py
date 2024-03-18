from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass


@dataclass
class Set:
    pass


@dataclass
class NamedSet(Set):
    name: str


@dataclass
class Group(Set):
    expr: Set


@dataclass
class UnaryOp(Set):
    expr: Set


@dataclass
class BinaryOp(Set):
    left: Set
    right: Set


@dataclass
class Complement(UnaryOp):
    pass


@dataclass
class Union(BinaryOp):
    pass


@dataclass
class Intersection(BinaryOp):
    pass


@dataclass
class Difference(BinaryOp):
    pass


@dataclass
class SymmetricDifference(BinaryOp):
    pass


@dataclass
class Term(Set):
    value: str


class Universe(Set):
    pass


class SetTransformer(ABC):
    def transform(self, node: Set):
        transformed_children = []

        if isinstance(node, Term):
            transformed_children.append(node.value)

        if isinstance(node, Group):
            transformed_children.append(self.transform(node.expr))

        if isinstance(node, UnaryOp):
            transformed_children.append(self.transform(node.expr))

        if isinstance(node, BinaryOp):
            transformed_children.append(self.transform(node.left))
            transformed_children.append(self.transform(node.right))

        # Dispatch to the specific transformation method based on node type
        method_name = type(node).__name__
        transformer = getattr(self, method_name, self.__unhandled_node)
        return transformer(*transformed_children)

    def __unhandled_node(self, node: Set):
        raise Exception(f"No transform method defined for {type(node).__name__}")

    @abstractmethod
    def Group(self, expr):
        pass

    @abstractmethod
    def Complement(self, expr):
        pass

    @abstractmethod
    def Union(self, left, right):
        pass

    @abstractmethod
    def Intersection(self, left, right):
        pass

    @abstractmethod
    def Difference(self, left, right):
        pass

    @abstractmethod
    def SymmetricDifference(self, left, right):
        pass

    @abstractmethod
    def Term(self, value):
        pass

    @abstractmethod
    def Universe(self):
        pass
