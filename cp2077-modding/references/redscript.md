# REDscript And Decompiled Script Guidance

This reference incorporates the REDscript intro page and the resources it points new modders to: setup, the quick language overview, hook creation, example patch orientation, Cyberdoc/API browsing, decompiled game code, and NativeDB-oriented type lookup.

## Setup Model

REDscript mods are loaded from:

```text
Cyberpunk 2077/r6/scripts/
```

On a working installation, redscript setup can be confirmed by logs under:

```text
Cyberpunk 2077/r6/logs/
```

The VSCode/IDE workflow is:

1. Install redscript into the game directory so its `engine` and `r6` folders merge with the game's folders.
2. Start the game once so redscript initializes.
3. Install a REDscript IDE extension or language server integration.
4. Point the IDE setting at the Cyberpunk 2077 install.
5. Write `.reds` files in a mod-development folder, then deploy or package them under `r6/scripts`.

`red-cli` is an optional packaging helper. It can pack a project into a release archive under `r6/scripts`, and can merge scripts by module for distribution.

## Source Of Truth For Script Content

Use the decompiled Cyberpunk repository as the ground truth for script behavior. It stores files with `.swift` extensions, but the contents are REDscript-like decompiled game scripts.

When designing a hook:

1. Search decompiled scripts for the system/class/function related to the desired behavior.
2. Read the original method body and nearby helper methods.
3. Search for event classes, queued events, delay callbacks, and systems used by the vanilla code.
4. Hook the closest stable method, not a broad hot path, unless the mod explicitly needs broad coverage.
5. Copy only the validation/setup logic that is necessary; avoid duplicating large vanilla bodies.

Useful search examples:

```powershell
rg -n "class DamageSystem|func ProcessLocalizedDamage" <cyberpunk>
rg -n "ApplyRagdollImpulseEvent|CreateForceRagdollEvent|QueueEvent|DelayEvent" <cyberpunk>
rg -n "class .*System|extends ScriptableSystem|QueueScriptableSystemRequest" <cyberpunk>
rg -n "LogChannel|Log\\(" <cyberpunk>
```

## Quick Language Notes

REDscript is statically typed and object oriented. It supports:

- line and block comments;
- global functions;
- local variables with explicit types or inferred types;
- arithmetic and mutation;
- casts with `Cast(...)`;
- arrays and `for item in array` iteration;
- classes with fields, instance methods, and static methods;
- game API calls, events, and scriptable systems;
- annotations for adding, wrapping, and replacing game code.

Primitive and common names are case-sensitive. Use `Bool`, not `bool`; `Int32`, `Float`, `String`, `CName`, `TweakDBID`, `StatsObjectID`, `Vector4`, `ref<T>`, `wref<T>`, `array<T>`, and `script_ref<T>` as appropriate.

String/name literals include:

```swift
let name: CName = n"DEBUG";
let text: String = s"value=\(value)";
```

Typical function/class shape:

```swift
func Add2(x: Int32, y: Int32) -> Int32 {
  return x + y;
}

public class MyData extends IScriptable {
  private let value: Int32;

  public final func GetValue() -> Int32 {
    return this.value;
  }
}
```

## Hook Types

`@wrapMethod(TargetClass)` wraps an existing non-native game method. Define the wrapper at file root, with the same signature. Call `wrappedMethod(...)` to invoke the original method.

```swift
@wrapMethod(CraftingSystem)
private final func ProcessCraftSkill(xpAmount: Int32, craftedItem: StatsObjectID) -> Void {
  wrappedMethod(xpAmount, craftedItem);
  // extra behavior after vanilla logic
}
```

`@replaceMethod(TargetClass)` replaces the original method. Use it only when suppressing or fully rewriting vanilla behavior is intended.

```swift
@replaceMethod(SomeSystem)
private final func ShouldDoThing() -> Bool {
  return false;
}
```

`@addMethod(TargetClass)` adds methods visible to other script code:

```swift
@addMethod(GameObject)
public final func MyMod_HasUsefulTag(tag: CName) -> Bool {
  return this.HasTag(tag);
}
```

`@addField(TargetClass)` adds script-visible fields to a script class when supported:

```swift
@addField(NPCPuppet)
private let myModState: Int32;
```

Native functions/classes declared from RED4ext/RedLib are declared with `native`:

```swift
public static native func MakeArray(count: Int32) -> array<Int32>

public native class MyNativeClass {
  public native func DoWork(value: Int32) -> Bool
}
```

Do not wrap native methods with REDscript hooks; the hook documentation calls out native-marked functions/classes as an exception to normal wrapper behavior.

## Hook Selection Example Pattern

For an effect such as ragdolling an NPC after bullet damage:

1. Find the damage-processing class in decompiled scripts.
2. Inspect the method that receives the hit event and already filters hit data.
3. Use API/type browsing or SDK/native lookup for event/helper names.
4. Write a `@wrapMethod` hook on that method.
5. Call `wrappedMethod(hitEvent)` first if vanilla damage must still happen.
6. Keep vanilla guard checks such as "instigator is player", "not area effect", and "hit user data exists".
7. Put the actual extra behavior in a helper method to keep the hook readable.

## Events, Delays, And Systems

Common script interaction patterns in decompiled code:

- `object.QueueEvent(evt)` to send events to game objects.
- `GameInstance.GetDelaySystem(game).DelayEvent(target, evt, seconds)` for delayed delivery.
- `GameInstance.GetScriptableSystemsContainer(game).Get(n"SystemName") as SystemType` for scriptable systems.
- `GameInstance.QueueScriptableSystemRequest(game, n"SystemName", request)` for queued system requests.
- UI events often go through `GameInstance.GetUISystem(game).QueueEvent(evt)`.

Validate `ref<T>` values with `IsDefined(value)` before use. Delayed events and queued work can run later, so re-check object validity at execution time.

## Logging

Use `Log(...)` for simple output and `LogChannel(n"CHANNEL", text)` for categorized debug output. Prefer a mod-specific channel name for nontrivial diagnostics.

## Threading Note

Multiple threads can execute REDscript concurrently. This is normal. Do not use that as a reason to avoid REDscript solutions. Do avoid unsynchronized writes to the same shared data structure from multiple call paths or delayed callbacks.

## API Browsing Resources Incorporated From Intro

- Cyberdoc/API documentation is useful for searchable in-game classes, native functions, and API signatures.
- Decompiled game code is the definitive source for vanilla script behavior.
- NativeDB is useful for classes, enums, bitfields, functions, and fields, especially when API docs are incomplete.

When a local fetched repository can answer a question, use it before opening external sites. Use Cyberdoc/NativeDB as secondary lookup aids for symbol discovery or cross-checking.
