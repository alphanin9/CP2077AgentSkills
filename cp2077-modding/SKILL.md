---
name: cp2077-modding
description: Assistance for Cyberpunk 2077 native and script-oriented modding, REDengine 4 reverse engineering, RED4ext plugin work, RedLib abstractions, REDscript hooks, decompiled game-script analysis, RTTI/native type lookup, and cross-boundary C++/REDscript implementations. Use when Codex works on Cyberpunk 2077 mods, RED4ext.SDK or RedLib code, .reds/.swift decompiled scripts, native function/class registration, game systems, TweakDB/native types, or reverse-engineering tasks for Cyberpunk 2077.
---

# Cyberpunk 2077 Modding

Use this skill for Cyberpunk 2077 native RED4ext work, RedLib-based plugin code, REDscript mods, and reverse-engineering-assisted analysis.

## Source Priority

Use the bundled references before relying on general memory:

- [references/sources.md](references/sources.md): how to fetch and use the required upstream repositories without vendoring them into this skill.
- [references/native.md](references/native.md): RED4ext.SDK and RedLib native modding guidance, type lookup, RTTI registration, coding style, and threading notes.
- [references/redscript.md](references/redscript.md): incorporated REDscript documentation from the intro page and its linked startup resources, plus decompiled script workflow.
- [references/reverse-engineering.md](references/reverse-engineering.md): workflow for IDA/reverse-engineering MCPs, address hashes, and connecting disassembly to SDK/script names.

Ground truth order:

1. Use local project code and user-provided artifacts first.
2. Use fetched upstream source trees for authoritative symbols and examples.
3. For native C++ types, typenames, layouts, RTTI names, and RED4ext plugin mechanics, prefer RED4ext.SDK.
4. For native helper abstractions, prefer RedLib over raw SDK calls when it cleanly covers the task.
5. For REDscript behavior, hooks, class names, method bodies, event flow, and usage examples, prefer the decompiled Cyberpunk scripts.
6. Use reverse-engineering MCPs when source-level references are insufficient or the task is about executable behavior.

## Working Rules

- Fetch upstream sources with `scripts/fetch_sources.py` when the required source tree is absent. Do not copy the full upstream repositories into this skill.
- Prefer `rg`/`rg --files` for symbol discovery across RED4ext.SDK, RedLib, and decompiled scripts.
- In C++ code, follow RED4ext.SDK conventions: C++20, `RED4ext` namespace for SDK/reversed types, PascalCase classes/functions, `m_` class members, `a`-prefixed function parameters such as `aValue`, and camelCase locals.
- Prefer RedLib macros and helpers for RTTI definitions, registration, type resolution, calls, handles, resources, and job helpers when they fit the implementation.
- Treat Cyberpunk 2077 as multithreading-friendly within normal game-engine constraints. REDscript can run concurrently on multiple threads; shared mutable state still needs synchronization or confinement.
- When writing hooks, be explicit about whether behavior wraps, replaces, or adds functionality. For REDscript, call `wrappedMethod(...)` in `@wrapMethod` hooks unless intentionally changing control flow before or after the original call.
- Preserve game stability: validate null/ref handles, avoid blocking hot paths, avoid unsynchronized writes to shared structures, and avoid assumptions about call thread unless proven.

## Task Routing

- Native plugin, RTTI, C++, RED4ext lifecycle, or RedLib: read [references/native.md](references/native.md).
- REDscript syntax, hooks, scripts, decompiled game code, or `.reds` output: read [references/redscript.md](references/redscript.md).
- Binary analysis, RVA/address hashes, IDA, executable offsets, or unknown native behavior: read [references/reverse-engineering.md](references/reverse-engineering.md).
- Source setup or missing upstream trees: read [references/sources.md](references/sources.md) and run the fetch script.
