#!/usr/bin/env python3
"""Fetch required Cyberpunk 2077 modding source references without vendoring them."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


REPOS = {
    "RED4ext.SDK": "https://github.com/wopss/RED4ext.SDK.git",
    "cp2077-red-lib": "https://github.com/psiberx/cp2077-red-lib.git",
    "cyberpunk": "https://codeberg.org/adamsmasher/cyberpunk.git",
}


def default_dest() -> Path:
    base = os.environ.get("CODEX_CP2077_SOURCES")
    if base:
        return Path(base).expanduser()

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "Codex" / "cp2077-modding-sources"

    return Path.home() / ".cache" / "codex" / "cp2077-modding-sources"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def fetch_repo(name: str, url: str, dest: Path, depth: int, refresh: bool) -> None:
    target = dest / name
    if target.exists():
        if not (target / ".git").exists():
            raise SystemExit(f"{target} exists but is not a git checkout")
        if refresh:
            run(["git", "fetch", "--depth", str(depth), "origin"], cwd=target)
            run(["git", "pull", "--ff-only"], cwd=target)
        return

    run(["git", "clone", "--depth", str(depth), url, str(target)])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=default_dest(), help="Destination cache directory")
    parser.add_argument("--depth", type=int, default=1, help="Git clone/fetch depth")
    parser.add_argument("--refresh", action="store_true", help="Fetch and fast-forward existing checkouts")
    args = parser.parse_args()

    dest = args.dest.expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)

    for name, url in REPOS.items():
        fetch_repo(name, url, dest, args.depth, args.refresh)

    print("\nResolved source paths:")
    for name in REPOS:
        print(f"{name}: {dest / name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
