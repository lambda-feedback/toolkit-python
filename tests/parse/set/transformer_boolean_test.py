import pytest

from sympy import And
from sympy import Not
from sympy import Or
from sympy import Symbol
from sympy import Xor

from lf_toolkit.parse.set import Complement
from lf_toolkit.parse.set import Difference
from lf_toolkit.parse.set import Group
from lf_toolkit.parse.set import Intersection
from lf_toolkit.parse.set import SymmetricDifference
from lf_toolkit.parse.set import SymPyBooleanTransformer
from lf_toolkit.parse.set import Term
from lf_toolkit.parse.set import Union


@pytest.fixture(scope="module")
def sympy_transformer():
    return SymPyBooleanTransformer()


@pytest.mark.parametrize(
    "input,expected",
    [
        (Term("A"), Symbol("A")),
        (
            Intersection(Term("A"), Term("B")),
            And(Symbol("A"), Symbol("B")),
        ),
        (
            Union(Term("A"), Term("B")),
            Or(Symbol("A"), Symbol("B")),
        ),
        (
            Difference(Term("A"), Term("B")),
            And(Symbol("A"), Not(Symbol("B"))),
        ),
        (
            SymmetricDifference(Term("A"), Term("B")),
            Xor(Symbol("A"), Symbol("B")),
        ),
        (
            Complement(Term("A")),
            Not(Symbol("A")),
        ),
        (Group(Term("A")), Symbol("A")),
        # ((A \ B) n (C \ (A u B)))'
        (
            # \overline{(A \setminus B) \cap (C \setminus (A \cup B))}
            Complement(
                Intersection(
                    Difference(Term("A"), Term("B")),
                    Difference(Term("C"), Union(Term("A"), Term("B"))),
                )
            ),
            Not(
                And(
                    And(Symbol("A"), Not(Symbol("B"))),
                    And(Symbol("C"), Not(Or(Symbol("A"), Symbol("B")))),
                ),
            ),
        ),
        # A' u (B' n C') u (C n B)
        (
            Union(
                Complement(Term("A")),
                Union(
                    Group(Intersection(Complement(Term("B")), Complement(Term("C")))),
                    Group(Intersection(Term("C"), Term("B"))),
                ),
            ),
            Or(
                Not(Symbol("A")),
                Or(
                    And(Not(Symbol("B")), Not(Symbol("C"))),
                    And(Symbol("C"), Symbol("B")),
                ),
            ),
        ),
    ],
)
def test_sympy_boolean_transformer(
    input, expected, sympy_transformer: SymPyBooleanTransformer
):
    assert sympy_transformer.transform(input) == expected
