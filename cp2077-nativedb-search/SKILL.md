---
name: cp2077-nativedb-search
description: Search the NativeDB Cyberpunk 2077 RTTI dump for classes, structs, aliases, global functions, methods, overload signatures, argument types, return types, and native/static flags. Use when Codex needs authoritative CP2077 type or function names, must verify a REDengine RTTI signature before writing C++/REDscript/Lua code, needs to find APIs by owner or parameter/return type, or wants a scriptable alternative to searching nativedb.red4ext.com manually.
---

# CP2077 NativeDB Search

Use `scripts/search_nativedb.py` to query the same compact `classes.json` and `globals.json` RTTI assets consumed by NativeDB. Prefer this tool over guessing spellings or signatures from memory.

## Workflow

1. Search names broadly, then narrow by category or owner.
2. Search signatures when the desired API is known by an argument or return type.
3. Use `--strict` to verify an exact RTTI name.
4. Use `--format json` when results will feed another script.
5. Treat the dump as version-specific. Mention that results describe the downloaded/local dump when game-version accuracy matters.

The script downloads current assets from `nativedb.red4ext.com` on first use and caches them under the platform cache directory. It falls back to the `rayshader/cp2077-nativedb` raw assets. Use `--refresh` to update the cache, or `--data-dir` to search an RTTIDumper/local repository snapshot without network access.

## Examples

Search types and aliases:

```bash
python scripts/search_nativedb.py ScriptableSystem --category types
```

Find methods on an owner type:

```bash
python scripts/search_nativedb.py Register --category functions --owner ScriptableSystemsContainer --member-only
```

Find functions that consume or return a type:

```bash
python scripts/search_nativedb.py gameObject --category functions --search-in signature --limit 40
```

Verify an exact global function and emit JSON:

```bash
python scripts/search_nativedb.py IsDefined --category functions --global-only --strict --format json
```

Search local dump files:

```bash
python scripts/search_nativedb.py TweakDB --data-dir /path/to/cp2077-nativedb/src/assets/reddump
```

## Query Rules

- Plain text is case-insensitive; every space-separated word must occur in one field.
- `*` enables whole-field glob matching, matching NativeDB's wildcard-oriented search style.
- `--regex` enables a case-insensitive regular expression.
- `--search-in name` searches function names, full RTTI names, and owner-qualified names.
- `--search-in signature` searches the rendered owner, arguments, and return type.
- `--native-only`, `--global-only`, `--member-only`, `--kind`, and `--owner` reduce noisy result sets.

Report the owner-qualified signature and relevant flags for function results. Report both RTTI names and aliases for type results.
