#!/usr/bin/env python3
"""Translate Cyberpunk 2077 RVAs into address-hash entries."""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Section:
    index: int
    name: str
    virtual_address: int
    span: int

    def contains(self, rva: int) -> bool:
        return self.virtual_address <= rva < self.virtual_address + self.span

    def format_offset(self, rva: int) -> str:
        return f"{self.index:04d}:{rva - self.virtual_address:08x}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert one or more Cyberpunk 2077 RVAs into address-hash offsets "
            "and look them up in cyberpunk2077_addresses.json."
        )
    )
    parser.add_argument(
        "rvas",
        nargs="+",
        help="RVA values in hex or decimal form, for example 0x102428",
    )
    parser.add_argument(
        "--exe",
        type=Path,
        help="Path to Cyberpunk2077.exe. Defaults to the current directory or %CP2077_PATH%\\bin\\x64\\Cyberpunk2077.exe.",
    )
    parser.add_argument(
        "--addresses",
        type=Path,
        help="Path to cyberpunk2077_addresses.json. Defaults to the current directory or %CP2077_PATH%\\bin\\x64\\cyberpunk2077_addresses.json.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format. Default: text",
    )
    return parser.parse_args()


def parse_int(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer value: {value}") from exc


def candidate_paths(filename: str) -> Iterable[Path]:
    yield Path.cwd() / filename
    env_root = os.environ.get("CP2077_PATH")
    if env_root:
        yield Path(env_root) / "bin" / "x64" / filename


def resolve_existing_path(explicit: Path | None, filename: str) -> Path:
    if explicit is not None:
        resolved = explicit.expanduser().resolve()
        if resolved.is_file():
            return resolved
        raise FileNotFoundError(f"file not found: {resolved}")

    for candidate in candidate_paths(filename):
        if candidate.is_file():
            return candidate.resolve()

    checked = ", ".join(str(path) for path in candidate_paths(filename))
    raise FileNotFoundError(
        f"could not find {filename}; checked {checked}. "
        "Pass an explicit path or set CP2077_PATH."
    )


def load_sections(exe_path: Path) -> list[Section]:
    data = exe_path.read_bytes()
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ValueError(f"{exe_path} is not a PE file")

    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if data[e_lfanew : e_lfanew + 4] != b"PE\0\0":
        raise ValueError(f"{exe_path} has an invalid PE signature")

    number_of_sections = struct.unpack_from("<H", data, e_lfanew + 6)[0]
    optional_header_size = struct.unpack_from("<H", data, e_lfanew + 20)[0]
    section_table = e_lfanew + 24 + optional_header_size

    sections: list[Section] = []
    for idx in range(number_of_sections):
        offset = section_table + idx * 40
        name = data[offset : offset + 8].split(b"\0", 1)[0].decode("ascii", errors="replace")
        virtual_size, virtual_address, size_of_raw_data = struct.unpack_from(
            "<III", data, offset + 8
        )
        span = max(virtual_size, size_of_raw_data)
        sections.append(
            Section(
                index=idx + 1,
                name=name,
                virtual_address=virtual_address,
                span=span,
            )
        )

    return sections


def load_address_index(addresses_path: Path) -> dict[str, list[dict[str, str]]]:
    payload = json.loads(addresses_path.read_text(encoding="utf-8"))
    try:
        entries = payload["Addresses"]
    except KeyError as exc:
        raise ValueError(f"{addresses_path} does not contain an 'Addresses' list") from exc

    if not isinstance(entries, list):
        raise ValueError(f"{addresses_path} field 'Addresses' is not a list")

    index: dict[str, list[dict[str, str]]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        offset = entry.get("offset")
        if not isinstance(offset, str):
            continue
        index.setdefault(offset.lower(), []).append(entry)
    return index


def find_section(sections: Iterable[Section], rva: int) -> Section:
    for section in sections:
        if section.contains(rva):
            return section
    raise LookupError(f"RVA 0x{rva:08x} does not fall inside any PE section")


def build_result(rva: int, section: Section, matches: list[dict[str, str]]) -> dict[str, object]:
    offset = section.format_offset(rva)
    return {
        "rva": f"0x{rva:08x}",
        "section": {
            "index": section.index,
            "name": section.name,
            "virtual_address": f"0x{section.virtual_address:08x}",
        },
        "offset": offset,
        "matches": matches,
    }


def print_text_result(result: dict[str, object]) -> None:
    section = result["section"]
    assert isinstance(section, dict)
    print(f"RVA: {result['rva']}")
    print(
        "Section: "
        f"{section['index']:04d} {section['name']} "
        f"(base {section['virtual_address']})"
    )
    print(f"Offset: {result['offset']}")
    matches = result["matches"]
    assert isinstance(matches, list)
    if not matches:
        print("Matches: none")
        return

    print(f"Matches: {len(matches)}")
    for entry in matches:
        print(
            f"- hash={entry.get('hash')} secondary_hash={entry.get('secondary hash')} "
            f"symbol={entry.get('symbol')}"
        )


def main() -> int:
    args = parse_args()

    try:
        exe_path = resolve_existing_path(args.exe, "Cyberpunk2077.exe")
        addresses_path = resolve_existing_path(args.addresses, "cyberpunk2077_addresses.json")
        sections = load_sections(exe_path)
        address_index = load_address_index(addresses_path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    results: list[dict[str, object]] = []
    for raw_rva in args.rvas:
        try:
            rva = parse_int(raw_rva)
            section = find_section(sections, rva)
        except (argparse.ArgumentTypeError, LookupError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

        offset = section.format_offset(rva)
        matches = address_index.get(offset.lower(), [])
        results.append(build_result(rva, section, matches))

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        for idx, result in enumerate(results):
            if idx:
                print()
            print_text_result(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
