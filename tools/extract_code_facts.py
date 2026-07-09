"""Deterministic code fact extractor for the CF0 Python calculator fixture."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any


EXTRACTOR_VERSION = "0.1.0"


class ExtractError(Exception):
    """Raised when CF0 code facts cannot be extracted."""


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def line_col_range(node: ast.AST) -> dict[str, int]:
    return {
        "lineStart": int(getattr(node, "lineno", 1)),
        "lineEnd": int(getattr(node, "end_lineno", getattr(node, "lineno", 1))),
        "columnStart": int(getattr(node, "col_offset", 0)),
        "columnEnd": int(getattr(node, "end_col_offset", getattr(node, "col_offset", 0))),
    }


def call_names(node: ast.AST) -> list[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
            names.add(child.func.id)
    return sorted(names)


def return_expressions(function: ast.FunctionDef) -> list[str]:
    expressions: list[str] = []
    for child in ast.walk(function):
        if isinstance(child, ast.Return) and child.value is not None:
            expressions.append(ast.unparse(child.value))
    return sorted(set(expressions))


def function_facts(source_path: Path, function: ast.FunctionDef) -> list[dict[str, Any]]:
    symbol = function.name
    facts: list[dict[str, Any]] = [
        {
            "id": f"fact.function.{symbol}",
            "kind": "function",
            "sourceMode": "ast-extracted",
            "confidence": "deterministic",
            "artifactPath": source_path.name,
            "symbol": symbol,
            "arguments": [arg.arg for arg in function.args.args],
            "location": line_col_range(function),
        }
    ]
    for expression in return_expressions(function):
        expression_id = (
            expression.replace(" ", "_")
            .replace("+", "plus")
            .replace("-", "minus")
            .replace("*", "times")
            .replace("(", "")
            .replace(")", "")
        )
        facts.append(
            {
                "id": f"fact.function.{symbol}.return.{expression_id}",
                "kind": "return-expression",
                "sourceMode": "ast-extracted",
                "confidence": "deterministic",
                "artifactPath": source_path.name,
                "symbol": symbol,
                "expression": expression,
                "location": line_col_range(function),
            }
        )
    for called in call_names(function):
        facts.append(
            {
                "id": f"fact.function.{symbol}.calls.{called}",
                "kind": "call",
                "sourceMode": "ast-extracted",
                "confidence": "deterministic",
                "artifactPath": source_path.name,
                "fromSymbol": symbol,
                "toSymbol": called,
                "location": line_col_range(function),
            }
        )
    return facts


def extract(source_path: Path) -> dict[str, Any]:
    source = read_source(source_path)
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        raise ExtractError(f"{source_path} is not valid Python: {error}") from error
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    facts: list[dict[str, Any]] = [
        {
            "id": "fact.file.calc.py",
            "kind": "file",
            "sourceMode": "filesystem-source",
            "confidence": "deterministic",
            "artifactPath": source_path.name,
            "language": "python",
            "sha256": sha256_text(source),
            "lineCount": len(source.splitlines()),
        }
    ]
    for function in sorted(functions, key=lambda item: item.name):
        facts.extend(function_facts(source_path, function))
    facts = sorted(facts, key=lambda item: item["id"])
    return {
        "codeFactsVersion": EXTRACTOR_VERSION,
        "benchmarkId": "CF0-python-cli-calculator",
        "source": {
            "path": source_path.as_posix(),
            "role": "hand-written",
            "sha256": sha256_text(source),
        },
        "extractor": {
            "name": "tools/extract_code_facts.py",
            "mode": "tiny-cf0-ast-static",
            "deterministic": True,
            "externalExtractor": False,
        },
        "facts": facts,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract CF0 code facts from hand-written Python source.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        write_json(args.out, extract(args.source))
    except (OSError, ExtractError) as error:
        print(f"extract code facts failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
