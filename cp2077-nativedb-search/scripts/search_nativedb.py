#!/usr/bin/env python3
"""Search Cyberpunk 2077 RTTI types and functions from NativeDB JSON dumps."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LIVE_BASE = "https://nativedb.red4ext.com/assets/reddump"
RAW_BASE = "https://raw.githubusercontent.com/rayshader/cp2077-nativedb/master/src/assets/reddump"
FILES = ("classes.json", "globals.json")

PRIMITIVES = [
    "Void", "Bool", "Int8", "Uint8", "Int16", "Uint16", "Int32", "Uint32",
    "Int64", "Uint64", "Float", "Double", "String", "LocalizationString", "CName",
    "TweakDBID", "NodeRef", "DataBuffer", "serializationDeferredDataBuffer",
    "SharedDataBuffer", "CDateTime", "CGUID", "CRUID", "EditorObjectID",
    "MessageResourcePath", "Variant",
]
TEMPLATES = ["ref", "wref", "script_ref", "ResRef", "ResAsyncRef", "array", "curveData", "multiChannelCurve"]


class NativeDBError(RuntimeError):
    pass


@dataclass(frozen=True)
class Match:
    score: tuple[int, int, str]
    data: dict[str, Any]


def cache_dir() -> Path:
    root = os.environ.get("XDG_CACHE_HOME")
    return Path(root) / "cp2077-nativedb" if root else Path.home() / ".cache" / "cp2077-nativedb"


def download(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": "CP2077AgentSkills-NativeDB/1.0"})
    try:
        with urlopen(request, timeout=60) as response:
            payload = response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise NativeDBError(f"failed to download {url}: {exc}") from exc

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    temporary.replace(destination)


def ensure_cached(name: str, root: Path, refresh: bool) -> Path:
    destination = root / name
    if destination.is_file() and not refresh:
        return destination

    failures: list[str] = []
    for base in (LIVE_BASE, RAW_BASE):
        try:
            download(f"{base}/{name}", destination)
            return destination
        except NativeDBError as exc:
            failures.append(str(exc))
    raise NativeDBError("; ".join(failures))


def resolve_files(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.classes or args.globals:
        if not (args.classes and args.globals):
            raise NativeDBError("use --classes and --globals together")
        return Path(args.classes), Path(args.globals)

    if args.data_dir:
        root = Path(args.data_dir)
        return root / "classes.json", root / "globals.json"

    root = Path(args.cache_dir) if args.cache_dir else cache_dir()
    return tuple(ensure_cached(name, root, args.refresh) for name in FILES)  # type: ignore[return-value]


def load_array(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except FileNotFoundError as exc:
        raise NativeDBError(f"NativeDB dump not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise NativeDBError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, list):
        raise NativeDBError(f"expected a JSON array in {path}")
    return value


def type_name(value: Any) -> str:
    if not isinstance(value, dict):
        return "?"
    flag = value.get("a")
    if flag is None:
        name = str(value.get("b", "?"))
    elif isinstance(flag, int) and 0 <= flag < len(PRIMITIVES):
        name = PRIMITIVES[flag]
    elif isinstance(flag, int) and len(PRIMITIVES) <= flag < len(PRIMITIVES) + len(TEMPLATES):
        name = TEMPLATES[flag - len(PRIMITIVES)]
    else:
        name = f"type#{flag}"

    inner = value.get("c")
    if inner is None:
        return name
    inner_name = type_name(inner)
    if value.get("d") is not None:
        return f"[{inner_name}; {value['d']}]"
    return f"{name}<{inner_name}>"


def visibility(flags: int) -> str:
    if flags & 1:
        return "private"
    if flags & 2:
        return "protected"
    return "public"


def origin(flags: int) -> str:
    if flags & (1 << 3):
        return "native"
    if flags & (1 << 4):
        return "import-only"
    return "script"


def function_record(raw: dict[str, Any], owner: dict[str, Any] | None) -> dict[str, Any]:
    flags = int(raw.get("d", 0))
    args = []
    for argument in raw.get("e") or []:
        arg_flags = int(argument.get("c", 0))
        qualifier = "const" if arg_flags & 1 else "out" if arg_flags & 2 else "opt" if arg_flags & 4 else None
        args.append({
            "name": argument.get("b", ""),
            "type": type_name(argument.get("a")),
            "qualifier": qualifier,
        })
    name = str(raw.get("b") or raw.get("a") or "")
    return_type = type_name(raw["c"]) if "c" in raw else "Void"
    rendered_args = ", ".join(
        f"{(arg['qualifier'] + ' ') if arg['qualifier'] else ''}{arg['name']}: {arg['type']}" for arg in args
    )
    owner_name = owner.get("b") if owner else None
    qualified_name = f"{owner_name}.{name}" if owner_name else name
    owner_alias = owner.get("c") if owner else None
    qualified_alias = f"{owner_alias}.{name}" if owner_alias else None
    record = {
        "kind": "method" if owner else "global-function",
        "name": name,
        "full_name": raw.get("a", name),
        "qualified_name": qualified_name,
        "qualified_alias": qualified_alias,
        "owner": owner_name,
        "signature": f"{qualified_name}({rendered_args}) -> {return_type}",
        "arguments": args,
        "return_type": return_type,
        "visibility": visibility(flags),
        "flags": {
            "native": bool(flags & (1 << 2)),
            "static": bool(flags & (1 << 3)) or bool(owner and owner.get("g")),
            "final": bool(flags & (1 << 4)),
            "thread_safe": bool(flags & (1 << 5)),
            "callback": bool(flags & (1 << 6)),
            "const": bool(flags & (1 << 7)),
            "quest": bool(flags & (1 << 8)),
            "timer": bool(flags & (1 << 9)),
        },
    }
    if owner:
        record["owner_alias"] = owner_alias
    return record


def type_record(raw: dict[str, Any]) -> dict[str, Any]:
    flags = int(raw.get("d", 0))
    return {
        "kind": "struct" if raw.get("g") is True else "class",
        "name": raw.get("b", ""),
        "alias": raw.get("c"),
        "parent": raw.get("a"),
        "visibility": visibility(flags),
        "origin": origin(flags),
        "abstract": bool(flags & (1 << 2)),
        "property_count": len(raw.get("e") or []),
        "function_count": len(raw.get("f") or []),
    }


def query_score(query: str, fields: Iterable[str], wildcard: bool, strict: bool) -> tuple[int, int, str] | None:
    normalized = query.casefold()
    usable = [field for field in fields if field]
    folded = [field.casefold() for field in usable]
    if wildcard:
        matches = [field for field in folded if fnmatch.fnmatchcase(field, normalized)]
        if not matches:
            return None
        return (0, min(len(field) for field in matches), min(matches))
    if strict:
        matches = [field for field in folded if field == normalized]
        if not matches:
            return None
        return (0, min(len(field) for field in matches), min(matches))

    words = normalized.split()
    candidates = [field for field in folded if all(word in field for word in words)]
    if not candidates:
        return None
    best = min(candidates, key=lambda field: (0 if field == normalized else 1 if field.startswith(normalized) else 2, len(field), field))
    rank = 0 if best == normalized else 1 if best.startswith(normalized) else 2
    return (rank, len(best), best)


def regex_score(pattern: re.Pattern[str], fields: Iterable[str]) -> tuple[int, int, str] | None:
    matches = [field for field in fields if field and pattern.search(field)]
    if not matches:
        return None
    best = min(matches, key=lambda value: (len(value), value.casefold()))
    return (0, len(best), best.casefold())


def search(args: argparse.Namespace, classes: list[dict[str, Any]], globals_: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matcher = None
    if args.regex:
        try:
            matcher = re.compile(args.query, re.IGNORECASE)
        except re.error as exc:
            raise NativeDBError(f"invalid regular expression: {exc}") from exc

    matches: list[Match] = []
    if args.category in ("types", "all"):
        for raw in classes:
            record = type_record(raw)
            if args.kind != "any" and record["kind"] != args.kind:
                continue
            fields = [record["name"], record.get("alias") or ""]
            score = regex_score(matcher, fields) if matcher else query_score(args.query, fields, "*" in args.query, args.strict)
            if score:
                matches.append(Match(score, record))

    if args.category in ("functions", "all"):
        owners: list[dict[str, Any] | None] = [] if args.global_only else list(classes)
        if not args.member_only:
            owners.append(None)
        for owner in owners:
            if owner is not None and args.owner:
                owner_fields = [str(owner.get("b", "")), str(owner.get("c", ""))]
                if query_score(args.owner, owner_fields, "*" in args.owner, args.owner_strict) is None:
                    continue
            functions = globals_ if owner is None else owner.get("f") or []
            for raw in functions:
                record = function_record(raw, owner)
                if args.native_only and not record["flags"]["native"]:
                    continue
                fields = [record["name"], record["full_name"], record["qualified_name"], record.get("qualified_alias") or ""]
                if args.search_in in ("signature", "all"):
                    fields.append(record["signature"])
                if args.search_in == "signature":
                    fields = [record["signature"]]
                score = regex_score(matcher, fields) if matcher else query_score(args.query, fields, "*" in args.query, args.strict)
                if score:
                    matches.append(Match(score, record))

    matches.sort(key=lambda match: (match.score, match.data.get("qualified_name", match.data["name"]).casefold()))
    return [match.data for match in matches[: args.limit]]


def print_text(results: list[dict[str, Any]]) -> None:
    if not results:
        print("No matches.")
        return
    for item in results:
        if item["kind"] in ("class", "struct"):
            alias = f" (alias: {item['alias']})" if item.get("alias") else ""
            parent = f" : {item['parent']}" if item.get("parent") else ""
            print(f"[{item['kind']}] {item['name']}{alias}{parent}")
            print(f"  {item['visibility']} {item['origin']}; {item['property_count']} properties, {item['function_count']} functions")
        else:
            enabled = [name.replace("_", "-") for name, value in item["flags"].items() if value]
            print(f"[{item['kind']}] {item['signature']}")
            print(f"  {item['visibility']}; flags: {', '.join(enabled) if enabled else 'none'}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="case-insensitive text, glob containing '*', or regex with --regex")
    parser.add_argument("--category", choices=("types", "functions", "all"), default="all")
    parser.add_argument("--kind", choices=("any", "class", "struct"), default="any", help="type filter")
    parser.add_argument("--search-in", choices=("name", "signature", "all"), default="name", help="function fields")
    parser.add_argument("--strict", action="store_true", help="require an exact case-insensitive field match")
    parser.add_argument("--regex", action="store_true", help="interpret query as a case-insensitive regular expression")
    parser.add_argument("--owner", help="limit methods to owner type name/alias (substring or glob)")
    parser.add_argument("--owner-strict", action="store_true", help="require exact owner match")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--global-only", action="store_true")
    group.add_argument("--member-only", action="store_true")
    parser.add_argument("--native-only", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--data-dir", help="directory containing classes.json and globals.json")
    parser.add_argument("--classes", help="explicit classes.json path")
    parser.add_argument("--globals", help="explicit globals.json path")
    parser.add_argument("--cache-dir", help="download/cache directory")
    parser.add_argument("--refresh", action="store_true", help="redownload cached NativeDB dumps")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be at least 1")
    try:
        classes_path, globals_path = resolve_files(args)
        results = search(args, load_array(classes_path), load_array(globals_path))
    except NativeDBError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        json.dump({"query": args.query, "count": len(results), "results": results}, sys.stdout, indent=2)
        print()
    else:
        print_text(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
