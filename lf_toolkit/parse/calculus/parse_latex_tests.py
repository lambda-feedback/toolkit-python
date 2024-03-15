from .parse_latex import parse_latex


class TestParseLatex:
    def test_parse_latex(self):
        response = "\\frac{x + x^2 + x}{x}"
        result = parse_latex(response)
        print(result)
