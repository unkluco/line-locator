#!/usr/bin/env python3
r"""
cut.py

A command-line helper for:
- finding line numbers by REGEX only
- finding the next/previous matching line
- matching (), [], {} delimiters while ignoring common comments/strings

QUERY MODEL (regex only)
------------------------
All search queries are Python regular expressions.
There is no separate literal mode.
If you want to match text literally, escape regex metacharacters yourself.
Examples:

    a\.b          # match literal 'a.b'
    foo\(bar\)    # match literal 'foo(bar)'
    public\s+\w+  # common Java-style pattern
    (?i)todo       # case-insensitive match using inline flag

IMPORTANT
---------
This tool uses Python's built-in `re` engine.
That means the supported regex syntax follows Python regex rules, which match
most common developer usage, but are not identical to every PCRE/JS engine.

EXAMPLES
--------
Find many regexes at once:
    python cut.py --file DAO.java -mr "refreshAssemblyPanel" "build(Toa|Connector)" "a\.b"

Find the first match after line 120:
    python cut.py --file DAO.java -n "public\s+void\s+\w+\(" 120

Find the first match before line 200:
    python cut.py --file DAO.java -b "(get|set)\w+" 200

Find the matching closing delimiter for the 3rd '{' on line 12:
    python cut.py --file DAO.java -c "{" 12 3

Find the matching opening delimiter for the 1st '}' on line 40:
    python cut.py --file DAO.java -o "}" 40 1

Emit JSON for agent-friendly parsing:
    python cut.py --file DAO.java -mr "foo\d+" "bar_\w+" --json

If --file is omitted, input is read from stdin.
Line numbers are 1-based.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Tuple, Union

OPEN_TO_CLOSE = {"{": "}", "(": ")", "[": "]"}
CLOSE_TO_OPEN = {v: k for k, v in OPEN_TO_CLOSE.items()}
ResultValue = Union[int, Dict[str, List[int]]]


@dataclass
class DelimiterOccurrence:
    char: str
    line: int
    column: int
    ordinal_on_line: int
    match_line: Optional[int] = None
    match_column: Optional[int] = None


def read_text(file_path: Optional[str]) -> str:
    if file_path:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if not path.is_file():
            raise IsADirectoryError(f"Not a file: {file_path}")
        return path.read_text(encoding="utf-8", errors="replace")

    data = sys.stdin.read()
    if not data:
        raise ValueError("No input provided. Use --file PATH or pipe file content via stdin.")
    return data


def parse_regex(pattern: str) -> Pattern[str]:
    if pattern == "":
        raise ValueError("Regex pattern must not be empty.")
    try:
        return re.compile(pattern)
    except re.error as exc:
        raise ValueError(f"Invalid regex pattern {pattern!r}: {exc}") from exc


def dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def line_matches_regex(line: str, compiled: Pattern[str]) -> bool:
    return compiled.search(line) is not None


def find_many_regex_lines(lines: List[str], patterns: List[str]) -> Dict[str, List[int]]:
    normalized = dedupe_preserve_order(patterns)
    compiled = {pattern: parse_regex(pattern) for pattern in normalized}
    return {
        pattern: [idx for idx, line in enumerate(lines, start=1) if line_matches_regex(line, regex)]
        for pattern, regex in compiled.items()
    }


def find_next_line(lines: List[str], pattern: str, after_line: int) -> int:
    compiled = parse_regex(pattern)
    for idx in range(after_line + 1, len(lines) + 1):
        if line_matches_regex(lines[idx - 1], compiled):
            return idx
    raise ValueError(f"No line matching regex {pattern!r} was found after line {after_line}.")


def find_prev_line(lines: List[str], pattern: str, before_line: int) -> int:
    compiled = parse_regex(pattern)
    for idx in range(before_line - 1, 0, -1):
        if line_matches_regex(lines[idx - 1], compiled):
            return idx
    raise ValueError(f"No line matching regex {pattern!r} was found before line {before_line}.")


def ensure_line_exists(lines: List[str], line_no: int) -> None:
    if not lines:
        raise ValueError("Input has no lines.")
    if line_no < 1 or line_no > len(lines):
        raise ValueError(f"LINE must be between 1 and {len(lines)}.")


def scan_delimiters(text: str) -> Dict[Tuple[int, str], List[DelimiterOccurrence]]:
    """
    Collect (), [], {} outside common comments/strings.

    Ignored regions:
    - // line comments
    - # line comments
    - /* ... */ block comments
    - single, double and backtick strings
    - triple single/double quoted strings
    """
    occurrences: Dict[Tuple[int, str], List[DelimiterOccurrence]] = {}
    stack: List[DelimiterOccurrence] = []

    i = 0
    line = 1
    col = 1
    n = len(text)

    NORMAL = "normal"
    SLASH_COMMENT = "slash_comment"
    HASH_COMMENT = "hash_comment"
    BLOCK_COMMENT = "block_comment"
    SQ = "sq"
    DQ = "dq"
    BQ = "bq"
    TSQ = "tsq"
    TDQ = "tdq"
    state = NORMAL

    def add_occurrence(ch: str, line_no: int, col_no: int) -> DelimiterOccurrence:
        key = (line_no, ch)
        ord_no = len(occurrences.get(key, [])) + 1
        occ = DelimiterOccurrence(char=ch, line=line_no, column=col_no, ordinal_on_line=ord_no)
        occurrences.setdefault(key, []).append(occ)
        return occ

    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        nxt2 = text[i + 2] if i + 2 < n else ""

        if state == NORMAL:
            if ch == "/" and nxt == "/":
                state = SLASH_COMMENT
                i += 2
                col += 2
                continue
            if ch == "/" and nxt == "*":
                state = BLOCK_COMMENT
                i += 2
                col += 2
                continue
            if ch == "#":
                state = HASH_COMMENT
                i += 1
                col += 1
                continue
            if ch == "'" and nxt == "'" and nxt2 == "'":
                state = TSQ
                i += 3
                col += 3
                continue
            if ch == '"' and nxt == '"' and nxt2 == '"':
                state = TDQ
                i += 3
                col += 3
                continue
            if ch == "'":
                state = SQ
                i += 1
                col += 1
                continue
            if ch == '"':
                state = DQ
                i += 1
                col += 1
                continue
            if ch == "`":
                state = BQ
                i += 1
                col += 1
                continue

            if ch in OPEN_TO_CLOSE:
                occ = add_occurrence(ch, line, col)
                stack.append(occ)
            elif ch in CLOSE_TO_OPEN:
                occ = add_occurrence(ch, line, col)
                expected_open = CLOSE_TO_OPEN[ch]
                if stack and stack[-1].char == expected_open:
                    open_occ = stack.pop()
                    open_occ.match_line = occ.line
                    open_occ.match_column = occ.column
                    occ.match_line = open_occ.line
                    occ.match_column = open_occ.column

            if ch == "\n":
                line += 1
                col = 1
            else:
                col += 1
            i += 1
            continue

        if state in (SLASH_COMMENT, HASH_COMMENT):
            if ch == "\n":
                state = NORMAL
                line += 1
                col = 1
            else:
                col += 1
            i += 1
            continue

        if state == BLOCK_COMMENT:
            if ch == "*" and nxt == "/":
                state = NORMAL
                i += 2
                col += 2
                continue
            if ch == "\n":
                line += 1
                col = 1
            else:
                col += 1
            i += 1
            continue

        if state in (SQ, DQ, BQ):
            quote = {SQ: "'", DQ: '"', BQ: "`"}[state]
            if ch == "\\" and i + 1 < n:
                if text[i + 1] == "\n":
                    line += 1
                    col = 1
                else:
                    col += 2
                i += 2
                continue
            if ch == quote:
                state = NORMAL
                i += 1
                col += 1
                continue
            if ch == "\n":
                line += 1
                col = 1
            else:
                col += 1
            i += 1
            continue

        if state == TSQ:
            if ch == "'" and nxt == "'" and nxt2 == "'":
                state = NORMAL
                i += 3
                col += 3
                continue
            if ch == "\n":
                line += 1
                col = 1
            else:
                col += 1
            i += 1
            continue

        if state == TDQ:
            if ch == '"' and nxt == '"' and nxt2 == '"':
                state = NORMAL
                i += 3
                col += 3
                continue
            if ch == "\n":
                line += 1
                col = 1
            else:
                col += 1
            i += 1
            continue

    return occurrences


def get_nth_occurrence_on_line(
    occurrences: Dict[Tuple[int, str], List[DelimiterOccurrence]],
    token: str,
    line_no: int,
    ordinal: int,
) -> DelimiterOccurrence:
    line_items = occurrences.get((line_no, token), [])
    if ordinal < 1:
        raise ValueError("Occurrence index must be >= 1.")
    if ordinal > len(line_items):
        raise ValueError(
            f"Line {line_no} contains only {len(line_items)} valid occurrence(s) of {token!r}, "
            f"cannot get occurrence #{ordinal}."
        )
    return line_items[ordinal - 1]


def match_closing_line(text: str, opener: str, line_no: int, ordinal: int) -> int:
    if opener not in OPEN_TO_CLOSE:
        raise ValueError(f"{opener!r} is not a supported opening delimiter. Use one of {sorted(OPEN_TO_CLOSE)}.")
    occurrences = scan_delimiters(text)
    occ = get_nth_occurrence_on_line(occurrences, opener, line_no, ordinal)
    if occ.match_line is None:
        raise ValueError(
            f"The {ordinal} occurrence of {opener!r} on line {line_no} does not have a valid matching "
            f"{OPEN_TO_CLOSE[opener]!r}."
        )
    return occ.match_line


def match_opening_line(text: str, closer: str, line_no: int, ordinal: int) -> int:
    if closer not in CLOSE_TO_OPEN:
        raise ValueError(f"{closer!r} is not a supported closing delimiter. Use one of {sorted(CLOSE_TO_OPEN)}.")
    occurrences = scan_delimiters(text)
    occ = get_nth_occurrence_on_line(occurrences, closer, line_no, ordinal)
    if occ.match_line is None:
        raise ValueError(
            f"The {ordinal} occurrence of {closer!r} on line {line_no} does not have a valid matching "
            f"{CLOSE_TO_OPEN[closer]!r}."
        )
    return occ.match_line


def format_multi_result(result: Dict[str, List[int]]) -> str:
    return "; ".join(f"{pattern}: {lines}" for pattern, lines in result.items())


def emit_result(result: ResultValue, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False))
        return
    if isinstance(result, dict):
        print(format_multi_result(result))
        return
    print(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Regex-only line finder and delimiter matcher. "
            "All search queries use Python regex syntax. "
            "Use -mr for many patterns, -n/-b for one pattern around a line, and --json for machine-friendly output."
        )
    )
    parser.add_argument(
        "--file",
        "-p",
        help="Path to the input file. If omitted, read content from stdin.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output. Useful for agent/tool integration.",
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-mr",
        nargs="+",
        metavar="PATTERN",
        help=(
            "Return line numbers for one or more regex patterns. "
            "Patterns are Python regexes. Escape metacharacters if you want literal text."
        ),
    )
    group.add_argument(
        "-n",
        nargs=2,
        metavar=("PATTERN", "LINE"),
        help="Return the first line number matching PATTERN after LINE.",
    )
    group.add_argument(
        "-b",
        nargs=2,
        metavar=("PATTERN", "LINE"),
        help="Return the first line number matching PATTERN before LINE.",
    )
    group.add_argument(
        "-c",
        nargs=3,
        metavar=("OPEN", "LINE", "N"),
        help="Return the line number of the valid matching closing delimiter for the Nth OPEN on LINE.",
    )
    group.add_argument(
        "-o",
        nargs=3,
        metavar=("CLOSE", "LINE", "N"),
        help="Return the line number of the valid matching opening delimiter for the Nth CLOSE on LINE.",
    )
    return parser


def parse_positive_line(line_s: str) -> int:
    line_no = int(line_s)
    if line_no < 1:
        raise ValueError("LINE must be >= 1.")
    return line_no


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        text = read_text(args.file)
        lines = text.splitlines()

        if args.mr is not None:
            emit_result(find_many_regex_lines(lines, args.mr), args.json)
            return 0

        if args.n is not None:
            pattern, line_s = args.n
            line_no = parse_positive_line(line_s)
            ensure_line_exists(lines, line_no)
            emit_result(find_next_line(lines, pattern, line_no), args.json)
            return 0

        if args.b is not None:
            pattern, line_s = args.b
            line_no = parse_positive_line(line_s)
            ensure_line_exists(lines, line_no)
            emit_result(find_prev_line(lines, pattern, line_no), args.json)
            return 0

        if args.c is not None:
            opener, line_s, ord_s = args.c
            line_no = parse_positive_line(line_s)
            ensure_line_exists(lines, line_no)
            ordinal = int(ord_s)
            emit_result(match_closing_line(text, opener, line_no, ordinal), args.json)
            return 0

        if args.o is not None:
            closer, line_s, ord_s = args.o
            line_no = parse_positive_line(line_s)
            ensure_line_exists(lines, line_no)
            ordinal = int(ord_s)
            emit_result(match_opening_line(text, closer, line_no, ordinal), args.json)
            return 0

        parser.error("No operation specified.")
        return 2

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
