"""Symbolic equation solver utilities powered by sympy."""

from typing import Dict, List

import sympy as sp


class SymbolicComplexitySolver:
    """Approximate closed-form expressions for loop nests using sympy."""

    def __init__(self):
        self.n = sp.symbols("n", positive=True)

    def solve_loops(self, loop_infos: List[Dict]) -> Dict[str, object]:
        if not loop_infos:
            return {
                "status": "trivial",
                "closed_form": "1",
                "big_o": "O(1)",
                "samples": {10: 1, 100: 1},
            }

        expr = sp.Integer(1)
        solvable = True
        for loop in loop_infos:
            pattern = (loop.get("iteration_pattern") or "n").lower()
            expr_factor = self._pattern_to_expr(pattern)
            if expr_factor is None:
                solvable = False
                break
            expr *= expr_factor

        if not solvable:
            return self._bounded_response(loop_infos)

        simplified = sp.simplify(expr)
        big_o = self._describe_expression(simplified)
        samples = self._sample_expression(simplified)
        return {
            "status": "solved",
            "closed_form": str(expr),
            "simplified": str(simplified),
            "big_o": big_o,
            "samples": samples,
        }

    def _pattern_to_expr(self, pattern: str):
        n = self.n
        if pattern in ("n", "n-1", "n+1"):
            return n
        if pattern in ("n/2", "n / 2", "n/2.0"):
            return n / 2
        if pattern in ("n/3", "n / 3"):
            return n / 3
        if pattern.startswith("constant("):
            try:
                value = float(pattern.replace("constant(", "").rstrip(")"))
            except ValueError:
                value = 1
            return sp.Integer(max(1, int(value)))
        if pattern == "log(n)":
            return sp.log(n, 2)
        if pattern == "sqrt(n)":
            return sp.sqrt(n)
        if pattern == "n^2":
            return n**2
        if pattern == "n^3":
            return n**3
        return None

    def _describe_expression(self, expr) -> str:
        n = self.n
        poly = sp.Poly(expr, n) if expr.is_polynomial(n) else None
        if poly is not None:
            degree = poly.degree()
            if degree == 0:
                return "O(1)"
            if degree == 1:
                return "O(n)"
            return f"O(n^{degree})"
        if expr.has(sp.log(n)) and expr.has(n):
            return "O(n log(n))"
        if expr.has(sp.log(n)):
            return "O(log(n))"
        return f"O({expr})"

    def _sample_expression(self, expr) -> Dict[int, float]:
        samples = {}
        for value in (10, 100, 1000):
            try:
                evaluated = expr.subs(self.n, value)
                samples[value] = float(evaluated)
            except Exception:
                samples[value] = float("nan")
        return samples

    def _bounded_response(self, loop_infos: List[Dict]) -> Dict[str, object]:
        depth = max(loop.get("depth", 1) for loop in loop_infos)
        upper = f"O(n^{depth})" if depth > 1 else "O(n)"
        lower = "O(1)"
        return {
            "status": "bounded",
            "lower": lower,
            "upper": upper,
            "samples": {10: None, 100: None},
        }
