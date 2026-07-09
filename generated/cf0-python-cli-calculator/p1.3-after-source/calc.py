"""Hand-written CF0 calculator source for the code-first overlay probe."""

from __future__ import annotations

import sys


def add(left: int, right: int) -> int:
    return left + right


def sub(left: int, right: int) -> int:
    return left - right


def mul(left: int, right: int) -> int:
    return left * right


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) != 3:
        print("usage: calc {add|sub|mul} LEFT RIGHT", file=sys.stderr)
        return 2
    operation, left_raw, right_raw = argv
    try:
        left = int(left_raw)
        right = int(right_raw)
    except ValueError:
        print("LEFT and RIGHT must be integers", file=sys.stderr)
        return 2
    if operation == "add":
        print(add(left, right))
        return 0
    if operation == "sub":
        print(sub(left, right))
        return 0
    if operation == "mul":
        print(mul(left, right))
        return 0
    print(f"unsupported operation: {operation}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
