# Reverse-Engineering Workflow

Use reverse engineering when SDK/script sources do not answer a question, when a task names an executable address/RVA, or when native behavior must be validated against Cyberpunk2077.exe.

## Tool Preference

Use available reverse-engineering MCPs when possible:

- IDA MCP tools for functions, decompilation, xrefs, names, types, strings, and patch-free analysis.
- Redscript-related MCP/tools for script database lookups if available.
- GitHub or source tools only for repository inspection, not as a substitute for binary facts when the user asks about an executable address.

Do not patch the executable or alter the runtime unless the user explicitly asks. Prefer static inspection, decompilation, xrefs, runtime-neutral reasoning, and user-input-driven validation.

## Connecting Script, SDK, And Binary

For a native behavior question:

1. Start from the user-facing name, script class, method, event, or TweakDB record.
2. Search decompiled scripts for callers, lifecycle, and event flow.
3. Search RED4ext.SDK generated natives for matching `NAME`/`ALIAS` and C++ layout.
4. Search RedLib for helper abstractions that avoid raw RTTI or stack work.
5. Use IDA xrefs/decompilation for implementation details absent from sources.
6. Record confidence: script-confirmed, SDK-confirmed, RTTI-confirmed, or binary-confirmed.

## Address Hashes And RVAs

Cyberpunk modding commonly uses address hashes so relocations remain update-aware. If an RVA is provided:

1. Convert the executable RVA into the linker-map section-relative format required by the address-hash database.
2. Look up the hash in `cyberpunk2077_addresses.json` when available.
3. Prefer `RED4ext::UniversalRelocFunc` with the address hash over hardcoded RVAs.
4. If a dedicated address-hash skill/tool is available, use it for the conversion and lookup.

Use hardcoded offsets only as a last resort and mark them as version-sensitive.

## IDA Checks

When inspecting an IDB:

- Rename functions/types only if it helps the current task and the user expects analysis artifacts.
- Check callers/callees around suspected game functions.
- Compare decompiled argument order and types with SDK declarations and script signatures.
- Look for CName strings, RTTI names, and NativeDB/SDK typenames in xrefs.
- Verify calling convention and return type before suggesting a native hook or relocation call.

## Safety And Concurrency

Native plugins can run on game threads, worker jobs, callback dispatch, and script execution paths. Treat unknown callbacks as potentially concurrent until proven otherwise.

For shared native state:

- protect maps/vectors/caches with locks or engine-safe queues;
- prefer immutable tables after initialization;
- avoid blocking in render/UI/input/hot gameplay paths;
- avoid retaining raw pointers across world detach, save/load, or delayed callbacks unless lifetime is proven.

For script/native boundaries, assume callbacks can arrive reentrantly or from more than one thread if multiple systems trigger them.
