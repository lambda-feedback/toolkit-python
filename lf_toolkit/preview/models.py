from dataclasses import dataclass


@dataclass
class Preview:
    latex: str
    sympy: str
    feedback: str


@dataclass
class Result:
    preview: Preview
