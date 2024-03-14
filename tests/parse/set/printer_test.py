import pytest

from lf_toolkit.parse.set import ASCIIPrinter
from lf_toolkit.parse.set import Complement
from lf_toolkit.parse.set import Difference
from lf_toolkit.parse.set import Group
from lf_toolkit.parse.set import Intersection
from lf_toolkit.parse.set import LatexPrinter
from lf_toolkit.parse.set import SymmetricDifference
from lf_toolkit.parse.set import Term
from lf_toolkit.parse.set import UnicodePrinter
from lf_toolkit.parse.set import Union


@pytest.fixture(scope="module")
def latex_printer():
    return LatexPrinter()


@pytest.fixture(scope="module")
def ascii_printer():
    return ASCIIPrinter()


@pytest.fixture(scope="module")
def unicode_printer():
    return UnicodePrinter()


@pytest.mark.parametrize(
    "input,expected",
    [
        (Term("A"), "A"),
        (Intersection(Term("A"), Term("B")), "A \\cap B"),
        (Union(Term("A"), Term("B")), "A \\cup B"),
        (Difference(Term("A"), Term("B")), "A \\setminus B"),
        (SymmetricDifference(Term("A"), Term("B")), "A \\triangle B"),
        (Complement(Term("A")), "\\overline{A}"),
        (Group(Term("A")), "\\left(A\\right)"),
    ],
)
def test_latex_printer(input: str, expected: str, latex_printer: LatexPrinter):
    assert latex_printer.print(input) == expected


@pytest.mark.parametrize(
    "input,expected",
    [
        (Term("A"), "A"),
        (Intersection(Term("A"), Term("B")), "A n B"),
        (Union(Term("A"), Term("B")), "A u B"),
        (Difference(Term("A"), Term("B")), "A \\ B"),
        (SymmetricDifference(Term("A"), Term("B")), "A /\\ B"),
        (Complement(Term("A")), "A'"),
        (Group(Term("A")), "(A)"),
    ],
)
def test_ascii_printer(input: str, expected: str, ascii_printer: ASCIIPrinter):
    assert ascii_printer.print(input) == expected


@pytest.mark.parametrize(
    "input,expected",
    [
        (Term("A"), "A"),
        (Intersection(Term("A"), Term("B")), "A ∩ B"),
        (Union(Term("A"), Term("B")), "A ∪ B"),
        (Difference(Term("A"), Term("B")), "A ∖ B"),
        (SymmetricDifference(Term("A"), Term("B")), "A △ B"),
        (Complement(Term("A")), "A'"),
        (Group(Term("A")), "(A)"),
    ],
)
def test_unicode_printer(input: str, expected: str, unicode_printer: UnicodePrinter):
    assert unicode_printer.print(input) == expected
