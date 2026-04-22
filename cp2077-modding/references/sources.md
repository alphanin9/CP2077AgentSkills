# Source Acquisition And Authority

## Required Upstreams

Do not vendor these repositories into the skill. Fetch them into a cache or user-chosen workspace:

- RED4ext.SDK: `https://github.com/wopss/RED4ext.SDK.git`
- RedLib: `https://github.com/psiberx/cp2077-red-lib.git`
- Decompiled Cyberpunk scripts: `https://codeberg.org/adamsmasher/cyberpunk.git`

Use `scripts/fetch_sources.py`:

```powershell
python cp2077-modding/scripts/fetch_sources.py
```

Pass `--dest <path>` to choose a cache directory. The script prints the resolved paths. Use those paths for `rg`, includes, examples, and source inspection.

## Authority Rules

- RED4ext.SDK is the ground truth for native-oriented modding: generated native types, RTTI names, aliases, layout assertions, SDK lifecycle APIs, REDengine containers, handles, job/resource helpers, and examples.
- RedLib is the preferred abstraction layer over raw RED4ext.SDK when it covers the task.
- Decompiled Cyberpunk scripts are the ground truth for script content: class names, method names, hook targets, event usage, system access patterns, and vanilla behavior.
- Redscript wiki content incorporated in [redscript.md](redscript.md) is the built-in language guide; use fetched decompiled scripts for game-specific facts.
- Cyberdoc and NativeDB are useful external lookup aids for in-game API/type browsing, but this skill should first use the fetched repositories and incorporated references.

## Typical Layouts

RED4ext.SDK:

- `include/RED4ext/`: SDK headers.
- `include/RED4ext/Scripting/Natives/Generated/`: generated native C++ types grouped by namespace-like folders.
- `include/RED4ext/Scripting/Natives/`: curated/reversed native declarations that may override generated stubs.
- `examples/`: raw SDK examples for registering functions/classes and calling game functions.
- `CONTRIBUTING.md`: coding conventions and reverse-engineered member declaration workflow.

RedLib:

- `include/RedLib.hpp`: single include for the helper library.
- `include/Red/TypeInfo/`: RTTI definition, registration, resolving, invocation, parameters, properties, and macro helpers.
- `include/Red/Utils/`: handles, resources, and job queue helpers.
- `include/Red/Engine/`: engine-facing helpers and logging/channel utilities.

Decompiled scripts:

- Files use `.swift` in the repository but represent REDscript source.
- `core/`: base gameplay, math, entity, UI, animation, AI, and common script infrastructure.
- `cyberpunk/`: game systems, UI, devices, puppets, vehicles, managers, network, and gameplay implementation.
- `samples/` and `tests/`: examples and test scripts useful for usage patterns.

## Search Patterns

Use targeted searches:

```powershell
rg -n "static constexpr const char\\* NAME|ALIAS|RED4EXT_ASSERT_OFFSET" <RED4ext.SDK>\include\RED4ext\Scripting\Natives
rg -n "RTTI_DEFINE_CLASS|RTTI_DEFINE_GLOBALS|RTTI_METHOD|RTTI_PROPERTY" <RedLib>\include
rg -n "class DamageSystem|func ProcessLocalizedDamage|@wrapMethod|QueueEvent|DelayEvent" <cyberpunk>
rg -n "public .* func <MethodName>|native func <MethodName>|class <ClassName>" <cyberpunk>
```

When mapping a script type to C++:

1. Search decompiled scripts for the script class/method.
2. Search RED4ext.SDK generated natives for `NAME = "<scriptName>"` or `ALIAS = "<shortName>"`.
3. Prefer the generated/native SDK type name and include path in C++.
4. If RedLib can infer or resolve the type cleanly, use RedLib helpers rather than hand-assembling RTTI calls.
