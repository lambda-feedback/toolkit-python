import pytest

from sympy import Complement as SymComplement
from sympy import FiniteSet as SymFiniteSet
from sympy import Intersection as SymIntersection
from sympy import Symbol as SymSymbol
from sympy import SymmetricDifference as SymSymmetricDifference
from sympy import Union as SymUnion
from sympy import UniversalSet as SymUniversalSet

from lf_toolkit.parse.set import Complement
from lf_toolkit.parse.set import Difference
from lf_toolkit.parse.set import Group
from lf_toolkit.parse.set import Intersection
from lf_toolkit.parse.set import SymmetricDifference
from lf_toolkit.parse.set import SymPyTransformer
from lf_toolkit.parse.set import Term
from lf_toolkit.parse.set import Union


@pytest.fixture(scope="module")
def sympy_transformer():
    return SymPyTransformer()


@pytest.mark.parametrize(
    "input,expected",
    [
        (Term("A"), SymFiniteSet(SymSymbol("A"))),
        (
            Intersection(Term("A"), Term("B")),
            SymIntersection(SymFiniteSet(SymSymbol("A")), SymFiniteSet(SymSymbol("B"))),
        ),
        (
            Union(Term("A"), Term("B")),
            SymUnion(SymFiniteSet(SymSymbol("A")), SymFiniteSet(SymSymbol("B"))),
        ),
        (
            Difference(Term("A"), Term("B")),
            SymComplement(SymFiniteSet(SymSymbol("A")), SymFiniteSet(SymSymbol("B"))),
        ),
        (
            SymmetricDifference(Term("A"), Term("B")),
            SymSymmetricDifference(
                SymFiniteSet(SymSymbol("A")), SymFiniteSet(SymSymbol("B"))
            ),
        ),
        (
            Complement(Term("A")),
            SymComplement(SymUniversalSet, SymFiniteSet(SymSymbol("A"))),
        ),
        (Group(Term("A")), SymFiniteSet(SymSymbol("A"))),
        # ((A \ B) n (C \ (A u B)))'
        (
            # \overline{(A \setminus B) \cap (C \setminus (A \cup B))}
            Complement(
                Intersection(
                    Difference(Term("A"), Term("B")),
                    Difference(Term("C"), Union(Term("A"), Term("B"))),
                )
            ),
            SymComplement(
                SymUniversalSet,
                SymIntersection(
                    SymComplement(
                        SymFiniteSet(SymSymbol("A")), SymFiniteSet(SymSymbol("B"))
                    ),
                    SymComplement(
                        SymFiniteSet(SymSymbol("C")),
                        SymUnion(
                            SymFiniteSet(SymSymbol("A")), SymFiniteSet(SymSymbol("B"))
                        ),
                    ),
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
            SymUnion(
                SymComplement(SymUniversalSet, SymFiniteSet(SymSymbol("A"))),
                SymUnion(
                    SymIntersection(
                        SymComplement(SymUniversalSet, SymFiniteSet(SymSymbol("B"))),
                        SymComplement(SymUniversalSet, SymFiniteSet(SymSymbol("C"))),
                    ),
                    SymIntersection(
                        SymFiniteSet(SymSymbol("C")), SymFiniteSet(SymSymbol("B"))
                    ),
                ),
            ),
        ),
    ],
)
def test_sympy_transformer(
    input: str, expected: str, sympy_transformer: SymPyTransformer
):
    assert sympy_transformer.transform(input) == expected
