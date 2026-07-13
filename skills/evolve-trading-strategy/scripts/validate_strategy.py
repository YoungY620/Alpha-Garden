#!/usr/bin/env python3
"""Perform conservative static validation of a bar-v1 strategy module."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


ALLOWED_IMPORTS = {"__future__", "math", "numpy", "pandas"}
FORBIDDEN_NAMES = {"open", "eval", "exec", "compile", "input", "__import__", "getattr", "setattr", "delattr"}
FORBIDDEN_MODULES = {"os", "sys", "subprocess", "socket", "requests", "urllib", "pathlib", "shutil", "pickle", "importlib"}
FORBIDDEN_ATTRIBUTES = {
    "read_csv", "read_parquet", "read_pickle", "read_json", "read_excel", "read_sql",
    "to_csv", "to_parquet", "to_pickle", "to_json", "to_excel", "to_sql",
    "load", "save", "savez", "dump", "dumps", "loads",
}


class Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.issues: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root = alias.name.split(".")[0]
            if root not in ALLOWED_IMPORTS:
                self.issues.append(f"import is not allowed: {alias.name}")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        root = (node.module or "").split(".")[0]
        if root not in ALLOWED_IMPORTS:
            self.issues.append(f"import is not allowed: {node.module}")

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_NAMES:
            self.issues.append(f"forbidden call: {node.func.id}")
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id in FORBIDDEN_MODULES:
                self.issues.append(f"forbidden module use: {node.func.value.id}")
            if node.func.attr in {"shift", "pct_change", "diff"} and node.args:
                value = _literal_number(node.args[0])
                if value is not None and value < 0:
                    self.issues.append(f"future-looking {node.func.attr} argument")
            if node.func.attr == "rolling":
                for keyword in node.keywords:
                    if keyword.arg == "center" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                        self.issues.append("centered rolling window is forbidden")
            if node.func.attr in FORBIDDEN_ATTRIBUTES:
                self.issues.append(f"file or serialization operation is forbidden: {node.func.attr}")
        self.generic_visit(node)


def _literal_number(node: ast.AST) -> float | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        value = _literal_number(node.operand)
        return -value if value is not None else None
    return None


def validate(code: str) -> dict:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return {"accepted": False, "issues": [f"syntax error: {exc}"]}
    visitor = Visitor()
    visitor.visit(tree)
    names = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assigned = {target.id for node in tree.body if isinstance(node, ast.Assign) for target in node.targets if isinstance(target, ast.Name)}
    if "generate_target_positions" not in names:
        visitor.issues.append("missing generate_target_positions")
    if "STRATEGY_METADATA" not in assigned:
        visitor.issues.append("missing STRATEGY_METADATA")
    if "PARAMETER_SPACE" not in assigned:
        visitor.issues.append("missing PARAMETER_SPACE")
    return {"accepted": not visitor.issues, "issues": list(dict.fromkeys(visitor.issues))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("strategy", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = {"schema_version": "strategy-static-audit/v1", **validate(args.strategy.read_text(encoding="utf-8"))}
    payload = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
