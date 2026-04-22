# Native RED4ext And RedLib Guidance

## Ground Truth

Use RED4ext.SDK for native names, layouts, aliases, generated native includes, plugin exports, RTTI system APIs, containers, handles, jobs, resources, and low-level relocation/address-hash support.

Use RedLib over raw SDK registration and invocation when the task fits its abstractions. RedLib is header-only, included with:

```cpp
#include <RedLib.hpp>
```

RedLib namespace `Red` aliases `RED4ext`, so either spelling works. Prefer one style consistently in a file; existing code style wins.

## RED4ext.SDK Coding Conventions

Follow these conventions for generated or hand-written native code:

- Use C++20.
- Put SDK/reversed types in namespace `RED4ext`.
- Use PascalCase for namespaces, classes, functions, and enum values.
- Use `struct` for reversed/data-carrying game types and `class` for behavior-heavy objects.
- Prefix class data members with `m_`.
- Prefix function parameters with `a`, for example `aValue`, `aContext`, `aFrame`.
- Use camelCase for local variables.
- Prefer `enum class`.
- Prefix macros with `RED4EXT_`.
- Use the repository clang-format/editorconfig style.

## Source Lookup

Generated native types live under:

```text
RED4ext.SDK/include/RED4ext/Scripting/Natives/Generated/
```

Curated native declarations can live under:

```text
RED4ext.SDK/include/RED4ext/Scripting/Natives/
```

A generated type commonly declares:

```cpp
static constexpr const char* NAME = "gameScriptName";
static constexpr const char* ALIAS = "ShortAlias";
RED4EXT_ASSERT_SIZE(Type, 0x123);
RED4EXT_ASSERT_OFFSET(Type, member, 0xABC);
```

For script-facing class/type questions, search `NAME`, `ALIAS`, `RED4EXT_ASSERT_SIZE`, and `RED4EXT_ASSERT_OFFSET`. Prefer the SDK's C++ namespace/type and include path in native code.

## Plugin Lifecycle

Raw RED4ext plugins export these common entrypoints:

- `Query(RED4ext::v1::PluginInfo* aInfo)`: set plugin name, author, version, runtime, and SDK version.
- `Supports()`: return API version support.
- `Main(RED4ext::v1::PluginHandle aHandle, RED4ext::v1::EMainReason aReason, const RED4ext::v1::Sdk* aSdk)`: handle load/unload.
- `RegisterTypes()`: register custom RTTI types.
- `PostRegisterTypes()`: describe/register functions after dependent types exist.

In raw SDK code, hook registration into `CRTTISystem::Get()->AddRegisterCallback(...)` and `AddPostRegisterCallback(...)` on load.

With RedLib definitions, call:

```cpp
Red::TypeInfoRegistrar::RegisterDiscovered();
```

from `Main` on `Load`.

## Prefer RedLib RTTI Definitions

Use RedLib macros instead of hand-building RTTI objects when possible:

- `RTTI_DEFINE_GLOBALS({ RTTI_FUNCTION(Func); })`
- `RTTI_DEFINE_ENUM(MyEnum);`
- `RTTI_DEFINE_FLAGS(MyFlags);`
- `RTTI_DEFINE_CLASS(MyClass, { RTTI_METHOD(Method); RTTI_PROPERTY(field); })`
- `RTTI_EXPAND_CLASS(Red::GameObject, { RTTI_METHOD_FQN(Extension::Method); })`
- `RTTI_IMPL_TYPEINFO(MyClass);`
- `RTTI_IMPL_ALLOCATOR();`
- `RTTI_FWD_CONSTRUCTOR();`

Typical native class pattern:

```cpp
struct MyClass : Red::IScriptable
{
    void AddValue(int32_t aValue)
    {
        m_values.EmplaceBack(aValue);
    }

    Red::DynArray<int32_t> m_values;

    RTTI_IMPL_TYPEINFO(MyClass);
    RTTI_IMPL_ALLOCATOR();
};

RTTI_DEFINE_CLASS(MyClass, {
    RTTI_METHOD(AddValue);
    RTTI_GETTER(m_values);
});
```

Corresponding REDscript shape:

```swift
public native class MyClass {
  public native func AddValue(value: Int32)
  public native func GetValues() -> array<Int32>
}
```

For game systems, define a C++ type deriving `Red::IGameSystem`. RedLib can register it and expose a `GameInstance.GetMyGameSystem()`-style accessor in REDscript.

For scriptable systems or engine paths that reject native members, RedLib supports scripted members backed by native code with `RTTI_SCRIPT_METHOD(...)` and forwarded construction.

## Function Calls And Parameters

Prefer RedLib invocation helpers:

```cpp
float result{};
Red::CallGlobal("MaxF", result, aLeft, aRight);
Red::CallStatic("Vector4", "Rand", aOutVector);
```

For raw native handlers, the low-level signature uses:

```cpp
void Handler(RED4ext::IScriptable* aContext,
             RED4ext::CStackFrame* aFrame,
             ReturnType* aOut,
             int64_t a4)
```

When manually reading parameters, call `RED4ext::GetParameter(aFrame, &value)` for each parameter, then advance `aFrame->code` past `ParamEnd`. Prefer RedLib's normal method signatures or stack-frame parameter support unless a raw handler is specifically needed.

## Handles, References, And Construction

- Use `Red::Handle<T>`/`RED4ext::Handle<T>` for strong script object references.
- Use weak handles when the game may own the lifetime.
- Use `Red::MakeHandle<T>()` for native scriptable allocation where supported.
- Use RedLib handle utilities such as `ToHandle`, `ToWeakHandle`, and `MakeScriptedHandle` when converting between raw instances and script handles.
- Validate handles before dereference. Treat game-owned objects as unstable across delayed callbacks, queued work, load/unload, and world detach.

## TweakDB

RED4ext.SDK exposes `RED4ext::TweakDB` for records, queries, flats, group tags, and record creation/update/remove. Prefer higher-level project helpers if present. Be careful with runtime mutation: shared/default flat storage can affect multiple records, and the SDK implementation contains explicit caution around TweakDB not being designed for arbitrary runtime modification.

## Jobs, Resources, And Threads

Use RedLib `Red::Utils::JobQueues` and `Red::Utils::Resources` helpers for waiting on jobs/resource tokens when available. Avoid blocking the main thread or hot script paths unless the call site proves it is safe.

You can utilize `RED4ext::JobQueue` to schedule asynchronous jobs. In addition, game systems can bind their jobs to certain stages of the frame.

Cyberpunk 2077 and REDscript are multithreading-friendly within engine bounds, but concurrent writes to shared mutable state still require synchronization or thread confinement. Native static state, caches, maps, and script callbacks can race if multiple threads touch them without using their synchronization.

## Reverse-Engineered Members

When adding or relying on newly discovered members:

1. Locate the generated SDK declaration and note `NAME`, `ALIAS`, size, and known offsets.
2. Add explicit padding around the new member.
3. Assert known offsets with `RED4EXT_ASSERT_OFFSET`.
4. Assert type size with `RED4EXT_ASSERT_SIZE`.
5. Confirm with RTTI dumps, executable analysis, or another authoritative artifact.

Do not silently invent layout fields. Use `unk...` padding until a member's identity and type are justified.
