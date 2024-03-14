import pytest

from lf_toolkit.parse.set import Complement
from lf_toolkit.parse.set import Difference
from lf_toolkit.parse.set import Group
from lf_toolkit.parse.set import Intersection
from lf_toolkit.parse.set import Set
from lf_toolkit.parse.set import SetParser
from lf_toolkit.parse.set import SymmetricDifference
from lf_toolkit.parse.set import Term
from lf_toolkit.parse.set import Union


@pytest.fixture(scope="module")
def parser():
    return SetParser()


@pytest.mark.parametrize(
    "input,expected",
    [
        # terms
        ("A", Term("A")),
        # intersections
        ("A n B", Intersection(Term("A"), Term("B"))),
        ("A ∩ B", Intersection(Term("A"), Term("B"))),
        ("A nn B", Intersection(Term("A"), Term("B"))),
        ("A intersect B", Intersection(Term("A"), Term("B"))),
        # unions
        ("A u B", Union(Term("A"), Term("B"))),
        ("A ∪ B", Union(Term("A"), Term("B"))),
        ("A uu B", Union(Term("A"), Term("B"))),
        ("A union B", Union(Term("A"), Term("B"))),
        # differences
        ("A - B", Difference(Term("A"), Term("B"))),
        ("A diff B", Difference(Term("A"), Term("B"))),
        ("A without B", Difference(Term("A"), Term("B"))),
        ("A \\ B", Difference(Term("A"), Term("B"))),
        # symmetric differences
        ("A ^ B", SymmetricDifference(Term("A"), Term("B"))),
        ("A △ B", SymmetricDifference(Term("A"), Term("B"))),
        ("A /\\ B", SymmetricDifference(Term("A"), Term("B"))),
        ("A symdiff B", SymmetricDifference(Term("A"), Term("B"))),
        # complements
        ("A'", Complement(Term("A"))),
        # groups
        ("(A)", Group(Term("A"))),
        ("(A')", Group(Complement(Term("A")))),
        ("(A u B)", Group(Union(Term("A"), Term("B")))),
        ("(A)'", Complement(Group(Term("A")))),
        # complex
        (
            "(A n B) u (C - D)",
            Union(
                Group(Intersection(Term("A"), Term("B"))),
                Group(Difference(Term("C"), Term("D"))),
            ),
        ),
        (
            "(A - B) ^ C'",
            SymmetricDifference(
                Group(Difference(Term("A"), Term("B"))), Complement(Term("C"))
            ),
        ),
    ],
)
def test_parse_ascii(input: str, expected: Set, parser: SetParser):
    result = parser.parse(input)

    assert result == expected


@pytest.mark.parametrize(
    "input,expected",
    [
        # terms
        ("A", Term("A")),
        # intersections
        ("A \\cap B", Intersection(Term("A"), Term("B"))),
        # unions
        ("A \\cup B", Union(Term("A"), Term("B"))),
        # differences
        ("A \\backslash B", Difference(Term("A"), Term("B"))),
        # symmetric differences
        ("A \\triangle B", SymmetricDifference(Term("A"), Term("B"))),
        # complements
        ("\\bar{A}", Complement(Term("A"))),
        # groups
        ("(A)", Group(Term("A"))),
        ("(\\bar{A})", Group(Complement(Term("A")))),
        (
            "\\overline{(A \\cap B)}",
            Complement(Group(Intersection(Term("A"), Term("B")))),
        ),
        ("(A \\cup B)", Group(Union(Term("A"), Term("B")))),
        # complex
        (
            "(A \\cap B) \\cup (C \\backslash D)",
            Union(
                Group(Intersection(Term("A"), Term("B"))),
                Group(Difference(Term("C"), Term("D"))),
            ),
        ),
        (
            "(A \\backslash B) \\triangle \\bar{C}",
            SymmetricDifference(
                Group(Difference(Term("A"), Term("B"))), Complement(Term("C"))
            ),
        ),
    ],
)
def test_parse_latex(input: str, expected: Set, parser: SetParser):
    result = parser.parse(input, latex=True)

    assert result == expected
