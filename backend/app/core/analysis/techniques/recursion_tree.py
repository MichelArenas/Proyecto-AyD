"""
Recursion Tree Method for Analyzing Divide-and-Conquer Algorithms
"""

import math
from dataclasses import dataclass
from typing import List


@dataclass
class TreeLevel:
    """
    Data class representing a level in the recursion tree.
    """

    level: int
    subproblems: int
    problem_size: str
    work_per_subproblem: str
    total_work_at_level: str


class RecursionTree:
    """
    Class to build and analyze recursion trees for divide-and-conquer algorithms.
    """

    def __init__(
        self,
        branching_factor: int,
        reduction_factor: float,
        work_function: str = "n",
        base_case_size: int = 1,
    ):
        self.branching_factor = branching_factor
        self.reduction_factor = reduction_factor
        self.work_function = work_function
        self.base_case_size = base_case_size
        self.levels: List[TreeLevel] = []
        self.max_depth = 0

    def build_tree(self, initial_size: str = "n", max_levels: int = 20) -> None:
        """
        Build the recursion tree up to a maximum number of levels.
        """
        self.levels = []
        size_expr = initial_size

        if self.reduction_factor > 1:
            self.max_depth = min(
                max_levels,
                int(math.log(1000, self.reduction_factor)) + 2,
            )
        else:
            self.max_depth = min(max_levels, 10)

        for level in range(self.max_depth):
            subproblems = self.branching_factor**level

            if self.reduction_factor > 1:
                size_expr = f"n/{self.reduction_factor**level}"
            else:
                size_expr = f"n-{level}"

            work_per = self._evaluate_work_function(size_expr)

            total_work = self._multiply_work(work_per, subproblems)

            self.levels.append(
                TreeLevel(
                    level=level,
                    subproblems=subproblems,
                    problem_size=size_expr,
                    work_per_subproblem=work_per,
                    total_work_at_level=total_work,
                )
            )

    def _evaluate_work_function(self, size: str) -> str:
        """Evaluate work function for given problem size"""
        work = self.work_function.lower()

        if work in ("1", "o(1)"):
            return "O(1)"
        if work in ("n", "o(n)"):
            return f"O({size})"
        if "n^2" in work or "n^2" in work:
            return f"O(({size})²)"
        if "log" in work:
            return f"O(log({size}))"
        return f"O({work})"

    def _multiply_work(self, work: str, multiplier: int) -> str:
        """Multiply work expression by a multiplier"""
        if multiplier == 1:
            return work

        if "O(1)" in work:
            return f"O({multiplier})"

        if "O(n/" in work and multiplier > 1:
            return f"O({multiplier}*{work[2:-1]})"
        return f"{multiplier}*{work}"

    def calculate_total_complexity(self) -> tuple[str, str, List[str]]:
        """
        Calculate total complexity from the recursion tree.
        """
        if not self.levels:
            return "O(n)", "recursion-tree", ["Tree not built"]

        steps = [
            "Building recursion tree for T(n) = "
            f"{self.branching_factor}T(n/{self.reduction_factor}) + {self.work_function}",
            f"Tree depth: {self.max_depth} levels",
        ]

        level_works = []
        for level in self.levels[:5]:
            steps.append(
                f"Level {level.level}: {level.subproblems} subproblems, "
                f"work = {level.total_work_at_level}"
            )
            level_works.append(level.total_work_at_level)

        complexity = self._analyze_work_pattern(level_works)

        steps.append(f"Total complexity: {complexity}")

        return complexity, "recursion-tree", steps

    def _analyze_work_pattern(self, level_works: List[str]) -> str:
        """Analyze pattern of work across levels to determine total complexity"""
        if not level_works:
            return "O(n)"

        if all("O(n)" in w or "n/" not in w for w in level_works):
            if self.reduction_factor >= 2:
                return "O(n log(n))"
            return "O(n^2)"

        if self.branching_factor < self.reduction_factor:
            return f"O({self.work_function})"

        if self.branching_factor > self.reduction_factor:
            leaf_count = self.branching_factor**self.max_depth
            return f"O({leaf_count})"

        return "O(n log(n))"

    def visualize(self, format_graph: str = "text") -> str:
        """
        Visualize the recursion tree in specified format.
        """
        if not self.levels:
            return "Tree not built"

        if format_graph == "graphviz":
            return self._visualize_graphviz()
        return self._visualize_text()

    def _visualize_text(self) -> str:
        """
        Generate ASCII art visualization of the recursion tree.
        """
        lines = [
            "Recursion Tree Visualization:",
            "=" * 50,
            f"T(n) = {self.branching_factor}T(n/{self.reduction_factor}) + {self.work_function}",
            "",
        ]

        for level in self.levels[:6]:
            indent = "  " * level.level
            lines.append(
                f"{indent}Level {level.level}: "
                f"{level.subproblems} × ({level.work_per_subproblem}) = "
                f"{level.total_work_at_level}"
            )

        if len(self.levels) > 6:
            lines.append("  ...")

        lines.append("")
        lines.append(f"Total depth: {self.max_depth}")
        lines.append(f"Total leaves: {self.branching_factor ** (self.max_depth - 1)}")

        return "\n".join(lines)

    def _visualize_graphviz(self) -> str:
        """
        Generate Graphviz DOT format visualization of the recursion tree.
        """
        lines = [
            "digraph RecursionTree {",
            "    node [shape=box, style=rounded];",
            "    rankdir=TB;",
            "",
        ]

        max_viz_levels = min(4, len(self.levels))
        node_id = 0

        for level_idx in range(max_viz_levels):
            level = self.levels[level_idx]

            for _ in range(min(level.subproblems, 16)):
                node_label = (
                    f"T({level.problem_size})\\nWork: {level.work_per_subproblem}"
                )
                lines.append(f'    node{node_id} [label="{node_label}"];')

                if level_idx < max_viz_levels - 1:
                    children_per_node = self.branching_factor
                    for child_idx in range(min(children_per_node, 4)):
                        child_node_id = (
                            node_id * children_per_node
                            + child_idx
                            + self.branching_factor**level_idx
                        )
                        if child_node_id < 100:
                            lines.append(f"    node{node_id} -> node{child_node_id};")

                node_id += 1

        if len(self.levels) > max_viz_levels:
            lines.append(
                f'    nodeMore [label="... ({len(self.levels)} total levels)", shape=ellipse];'
            )

        lines.append("}")
        lines.append("")
        lines.append("// To generate image: dot -Tpng this_file.dot -o tree.png")

        return "\n".join(lines)

    @staticmethod
    def from_recurrence(
        num_calls: int, reduction_pattern: str, work: str
    ) -> "RecursionTree":
        """
        Create RecursionTree from recurrence relation parameters.
        """
        if "/" in reduction_pattern or "div" in reduction_pattern:
            parts = reduction_pattern.replace("div", "/").split("/")
            if len(parts) == 2:
                reduction_factor = float(parts[1].strip())
            else:
                reduction_factor = 2.0
        else:
            reduction_factor = 1.0

        work_clean = work.replace("O(", "").replace(")", "").strip()

        tree = RecursionTree(
            branching_factor=num_calls,
            reduction_factor=reduction_factor,
            work_function=work_clean,
        )

        tree.build_tree()
        return tree


class RecursionTreeAnalyzer:
    """
    Analyzer for divide-and-conquer algorithms using recursion tree method.
    """

    @staticmethod
    def analyze_divide_and_conquer(
        branching_factor: int,
        reduction_factor: int,
        work_per_level: str,
    ) -> dict:
        """
        Analyze a divide-and-conquer algorithm using recursion tree method.
        """
        tree = RecursionTree(branching_factor, reduction_factor, work_per_level)
        tree.build_tree()

        complexity, method, steps = tree.calculate_total_complexity()
        visualization = tree.visualize()

        return {
            "complexity": complexity,
            "method": method,
            "steps": steps,
            "visualization": visualization,
            "tree": tree,
        }

    @staticmethod
    def should_use_tree_method(num_calls: int, reduction: str) -> bool:
        """
        Determine if recursion tree method is suitable based on recurrence pattern.
        """
        if "/" in reduction or "div" in reduction:
            return True

        if num_calls >= 2:
            return True

        return False
