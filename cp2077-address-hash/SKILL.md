---
name: cp2077-address-hash
description: Translate Cyberpunk 2077 executable RVAs into address-hash entries by converting each RVA into the linker-map offset format `section_number:rva_from_base_of_section` and looking it up in `cyberpunk2077_addresses.json`. Use when Codex needs to resolve CP2077 function or symbol hashes from RVAs, compare disassembly addresses against the address-hash database, or automate lookups with the bundled Python script. Address hashes are used to keep executable offsets update-agnostic and can be used with `RED4ext::UniversalRelocFunc`.
---

# CP2077 Address Hash

## Overview

Use the bundled script to convert one or more RVAs from `Cyberpunk2077.exe` into the address file's `offset` format and return every matching address-hash entry.

Prefer the script over reimplementing PE parsing. It handles PE section discovery, offset formatting, and JSON lookup with only the standard library.

## Workflow

1. Resolve the input value type.
   If the user gives a virtual address instead of an RVA, subtract the image base first. The sample address file reports the preferred load address as `0x140000000`.
2. Resolve the input files.
   Prefer explicit `--exe` and `--addresses` arguments when the user gives paths.
   Otherwise let the script auto-discover `Cyberpunk2077.exe` and `cyberpunk2077_addresses.json` from the current working directory or `%CP2077_PATH%\\bin\\x64\\`.
3. Run the bundled script.
   Use `scripts/rva_to_address_hash.py` with one or more RVAs.
4. Report both forms.
   Return the original RVA, the computed `offset` string, and every matching entry's `hash`, `secondary hash`, and `symbol`.

## Quick Start

Translate a single RVA:

```powershell
python .\scripts\rva_to_address_hash.py 0x102428
```

Translate multiple RVAs with explicit files:

```powershell
python .\scripts\rva_to_address_hash.py 0x102428 0x10fc2c `
  --exe "C:\Games\Cyberpunk 2077\bin\x64\Cyberpunk2077.exe" `
  --addresses "C:\Games\Cyberpunk 2077\bin\x64\cyberpunk2077_addresses.json"
```

Emit machine-readable JSON:

```powershell
python .\scripts\rva_to_address_hash.py 0x102428 --format json
```

## Notes

- The address file stores entries under `Addresses`, each with an `offset` like `0001:00101428`.
- The section number is 1-based and follows the PE section table order in `Cyberpunk2077.exe`.
- The right-hand side of the offset is the RVA relative to the start of the containing section, not the image base.
- A missing match does not mean the conversion failed. The script still reports the computed offset so it can be compared manually or against another address file revision.
