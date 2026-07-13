"""Deterministic B1 TypeScript REST fixture code fact extractor.

This is intentionally fixture-bounded. It is not a general TypeScript parser.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


EXTRACTOR_ID = "tools/extract_b1_code_facts.py"
EXTRACTOR_VERSION = "0.1.0"
BENCHMARK_ID = "B1-typescript-rest-api"

ALLOWED_EXTENSIONS = {".ts"}


class ExtractError(Exception):
    """Raised when B1 code facts cannot be extracted."""


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def safe_id(value: str) -> str:
    safe = "".join(character.lower() if character.isalnum() else "_" for character in value)
    return "_".join(part for part in safe.split("_") if part) or "empty"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def line_count(text: str) -> int:
    return len(text.splitlines())


def line_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def range_for_match(text: str, match: re.Match[str]) -> dict[str, int]:
    line_start = line_for_offset(text, match.start())
    line_end = line_for_offset(text, match.end())
    line_start_offset = text.rfind("\n", 0, match.start()) + 1
    line_end_offset = text.rfind("\n", 0, match.end()) + 1
    return {
        "lineStart": line_start,
        "lineEnd": line_end,
        "columnStart": match.start() - line_start_offset,
        "columnEnd": match.end() - line_end_offset,
    }


def base_fact(
    fact_id: str,
    kind: str,
    relative_path: str,
    source_digest: str,
    location: dict[str, int] | None,
) -> dict[str, Any]:
    fact: dict[str, Any] = {
        "id": fact_id,
        "kind": kind,
        "benchmarkId": BENCHMARK_ID,
        "sourceFile": relative_path,
        "sourceDigest": source_digest,
        "extractor": EXTRACTOR_ID,
        "extractorVersion": EXTRACTOR_VERSION,
        "confidence": "extracted",
    }
    if location is None:
        fact["sourceLocationStatus"] = "file-level"
    else:
        fact["sourceLocation"] = location
    return fact


def module_id(relative_path: str) -> str:
    return "fact.module." + safe_id(relative_path.removesuffix(".ts"))


def symbol_id(kind: str, name: str) -> str:
    return f"fact.{kind}.{safe_id(name)}"


def relative_import_target(current_file: Path, imported: str, source_root: Path) -> str:
    if not imported.startswith("."):
        return imported
    target = (current_file.parent / imported).resolve()
    if target.suffix != ".ts":
        target = target.with_suffix(".ts")
    try:
        return target.relative_to(source_root.resolve()).as_posix()
    except ValueError:
        return target.as_posix()


def extract_imports(text: str, source_path: Path, source_root: Path, relative_path: str, digest: str) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    pattern = re.compile(r'import\s+\{([^}]+)\}\s+from\s+"([^"]+)";')
    for match in pattern.finditer(text):
        imports = [part.strip() for part in match.group(1).split(",")]
        imported_path = relative_import_target(source_path, match.group(2), source_root)
        for imported in imports:
            is_type_only = imported.startswith("type ")
            name = imported.removeprefix("type ").strip()
            fact = base_fact(
                f"fact.import.{safe_id(relative_path)}.{safe_id(name)}",
                "import",
                relative_path,
                digest,
                range_for_match(text, match),
            )
            fact.update(
                {
                    "module": module_id(relative_path),
                    "importedName": name,
                    "importedPath": imported_path,
                    "typeOnly": is_type_only,
                }
            )
            facts.append(fact)
    return facts


def extract_interfaces(text: str, relative_path: str, digest: str) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    pattern = re.compile(r'export\s+interface\s+([A-Za-z_][A-Za-z0-9_]*)')
    for match in pattern.finditer(text):
        name = match.group(1)
        fact = base_fact(symbol_id("type", name), "type", relative_path, digest, range_for_match(text, match))
        fact.update({"symbol": name, "module": module_id(relative_path)})
        facts.append(fact)
    return facts


def extract_functions(text: str, relative_path: str, digest: str) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    pattern = re.compile(r'export\s+function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(')
    for match in pattern.finditer(text):
        name = match.group(1)
        kind = "test" if relative_path.startswith("tests/") or name.startswith("test") else "function"
        fact = base_fact(symbol_id(kind, name), kind, relative_path, digest, range_for_match(text, match))
        fact.update({"symbol": name, "module": module_id(relative_path)})
        facts.append(fact)
    return facts


def extract_calls(text: str, relative_path: str, digest: str) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    function_pattern = re.compile(r'export\s+function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)[^{]*\{(?P<body>.*?)\n\}', re.DOTALL)
    call_pattern = re.compile(r'\b([A-Za-z_][A-Za-z0-9_]*)\s*\(')
    excluded = {"if", "for", "while", "switch", "function", "Error", "trim"}
    for function_match in function_pattern.finditer(text):
        from_symbol = function_match.group(1)
        body = function_match.group("body")
        for call_match in call_pattern.finditer(body):
            called = call_match.group(1)
            if called in excluded or called == from_symbol:
                continue
            absolute_start = function_match.start("body") + call_match.start()
            absolute_end = function_match.start("body") + call_match.end()
            pseudo_match = _PseudoMatch(absolute_start, absolute_end)
            fact = base_fact(
                f"fact.call.{safe_id(from_symbol)}.{safe_id(called)}",
                "call",
                relative_path,
                digest,
                range_for_match(text, pseudo_match),
            )
            fact.update({"fromSymbol": from_symbol, "toSymbol": called})
            facts.append(fact)
    return facts


class _PseudoMatch:
    def __init__(self, start: int, end: int) -> None:
        self._start = start
        self._end = end

    def start(self) -> int:
        return self._start

    def end(self) -> int:
        return self._end


def extract_routes(text: str, relative_path: str, digest: str) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    pattern = re.compile(
        r'method:\s+"(?P<method>[A-Z]+)",\s*\n\s*path:\s+"(?P<path>[^"]+)",\s*\n\s*handler:\s*(?P<handler>[A-Za-z_][A-Za-z0-9_]*)',
        re.MULTILINE,
    )
    for match in pattern.finditer(text):
        method = match.group("method")
        path = match.group("path")
        handler = match.group("handler")
        fact = base_fact(
            f"fact.route.{safe_id(method)}.{safe_id(path)}",
            "route",
            relative_path,
            digest,
            range_for_match(text, match),
        )
        fact.update({"method": method, "path": path, "handler": handler})
        facts.append(fact)
    return facts


def extract_file(source_path: Path, source_root: Path) -> list[dict[str, Any]]:
    relative_path = source_path.relative_to(source_root).as_posix()
    text = read_text(source_path)
    digest = sha256_text(text)
    facts: list[dict[str, Any]] = []
    file_fact = base_fact("fact.file." + safe_id(relative_path), "file", relative_path, digest, None)
    file_fact.update({"language": "typescript", "lineCount": line_count(text)})
    facts.append(file_fact)
    module_fact = base_fact(module_id(relative_path), "module", relative_path, digest, None)
    module_fact.update({"path": relative_path})
    facts.append(module_fact)
    facts.extend(extract_imports(text, source_path, source_root, relative_path, digest))
    facts.extend(extract_interfaces(text, relative_path, digest))
    facts.extend(extract_functions(text, relative_path, digest))
    facts.extend(extract_calls(text, relative_path, digest))
    facts.extend(extract_routes(text, relative_path, digest))
    return facts


def endpoint_id_for_fact(fact: dict[str, Any]) -> str | None:
    kind = fact.get("kind")
    if kind in {"file", "module", "function", "type", "route", "test"}:
        return str(fact["id"])
    return None


def relation_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_symbol: dict[str, str] = {}
    modules: dict[str, str] = {}
    files: dict[str, str] = {}
    tests: dict[str, str] = {}
    for fact in facts:
        kind = fact.get("kind")
        if kind in {"function", "type"}:
            by_symbol[str(fact["symbol"])] = str(fact["id"])
        if kind == "test":
            tests[str(fact["symbol"])] = str(fact["id"])
        if kind == "module":
            modules[str(fact["sourceFile"])] = str(fact["id"])
        if kind == "file":
            files[str(fact["sourceFile"])] = str(fact["id"])

    relations: list[dict[str, Any]] = []
    for path, file_id in sorted(files.items()):
        module_fact_id = modules.get(path)
        if module_fact_id:
            relations.append({"id": f"rel.contains.{safe_id(path)}", "kind": "contains", "from": file_id, "to": module_fact_id})
    for fact in facts:
        kind = fact.get("kind")
        if kind in {"function", "type", "test"}:
            module_fact_id = modules.get(str(fact["sourceFile"]))
            if module_fact_id:
                relations.append(
                    {
                        "id": f"rel.contains.{safe_id(str(fact['sourceFile']))}.{safe_id(str(fact['id']))}",
                        "kind": "contains",
                        "from": module_fact_id,
                        "to": fact["id"],
                    }
                )
        if kind == "import":
            source_module = modules.get(str(fact["sourceFile"]))
            target_module = modules.get(str(fact["importedPath"]))
            if source_module and target_module:
                relations.append(
                    {
                        "id": f"rel.imports.{safe_id(str(fact['sourceFile']))}.{safe_id(str(fact['importedPath']))}.{safe_id(str(fact['importedName']))}",
                        "kind": "imports",
                        "from": source_module,
                        "to": target_module,
                    }
                )
            imported_symbol = by_symbol.get(str(fact["importedName"]))
            if source_module and imported_symbol:
                relations.append(
                    {
                        "id": f"rel.references.import.{safe_id(str(fact['sourceFile']))}.{safe_id(str(fact['importedName']))}",
                        "kind": "references",
                        "from": source_module,
                        "to": imported_symbol,
                    }
                )
        if kind == "call":
            from_id = by_symbol.get(str(fact["fromSymbol"])) or tests.get(str(fact["fromSymbol"]))
            to_id = by_symbol.get(str(fact["toSymbol"]))
            if from_id and to_id:
                relations.append(
                    {
                        "id": f"rel.calls.{safe_id(str(fact['fromSymbol']))}.{safe_id(str(fact['toSymbol']))}",
                        "kind": "calls",
                        "from": from_id,
                        "to": to_id,
                    }
                )
        if kind == "route":
            route_id = str(fact["id"])
            handler_id = by_symbol.get(str(fact["handler"]))
            if handler_id:
                relations.append(
                    {
                        "id": f"rel.handles_route.{safe_id(str(fact['method']))}.{safe_id(str(fact['path']))}.{safe_id(str(fact['handler']))}",
                        "kind": "handles_route",
                        "from": route_id,
                        "to": handler_id,
                    }
                )
    for test_name, test_id in sorted(tests.items()):
        if "AddTodo" in test_name and "addTodo" in by_symbol:
            relations.append({"id": "rel.tests.test_add_todo_creates_open_todo.add_todo", "kind": "tests", "from": test_id, "to": by_symbol["addTodo"]})
        if "ListTodos" in test_name and "listTodos" in by_symbol:
            relations.append({"id": "rel.tests.test_list_todos_starts_empty.list_todos", "kind": "tests", "from": test_id, "to": by_symbol["listTodos"]})
    return sorted(relations, key=lambda item: item["id"])


def extract(source_root: Path, source_root_id: str | None = None) -> dict[str, Any]:
    if not source_root.exists():
        raise ExtractError(f"source root does not exist: {source_root}")
    source_files = sorted(path for path in source_root.rglob("*") if path.suffix in ALLOWED_EXTENSIONS)
    if not source_files:
        raise ExtractError(f"no TypeScript files found under {source_root}")
    facts: list[dict[str, Any]] = []
    for source_file in source_files:
        facts.extend(extract_file(source_file, source_root))
    facts = sorted(facts, key=lambda item: item["id"])
    relations = relation_facts(facts)
    source_digests = {
        path.relative_to(source_root).as_posix(): sha256_bytes(path.read_bytes())
        for path in source_files
    }
    source_root_metadata: dict[str, str] = {}
    if source_root_id is not None:
        if not source_root_id.startswith("intentgraph://") or ".." in source_root_id or "\\" in source_root_id:
            raise ExtractError("source root id must be an intentgraph:// logical identifier")
        reported_source_root = source_root_id
        source_root_metadata = {"sourceRootKind": "logical-id"}
    else:
        reported_source_root = source_root.as_posix()
    return {
        "artifactRole": "intentgraph-code-facts",
        "status": "intentgraph-code-facts-extracted",
        "scope": "b1-typescript-rest-api-code-facts",
        "benchmarkId": BENCHMARK_ID,
        "codeFactsVersion": "0.1.0",
        "sourceRoot": reported_source_root,
        **source_root_metadata,
        "extractor": {
            "id": EXTRACTOR_ID,
            "version": EXTRACTOR_VERSION,
            "mode": "b1-fixture-bounded-static",
            "deterministic": True,
            "broadExtractor": False,
        },
        "sourceDigests": source_digests,
        "facts": facts,
        "relations": relations,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract B1 fixture code facts.")
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--source-root-id", type=str)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        write_json(args.out, extract(args.source_root, args.source_root_id))
    except (OSError, ExtractError) as error:
        print(f"extract B1 code facts failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
