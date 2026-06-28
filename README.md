# PhK-Protocol

Shared open-source protocol and ruleset contract for Phantasm Klash.

This repository is the planned source of truth for:

- protobuf messages used by SpellKard, Gensoulkyo, and the C++ Battle Server;
- business secure-envelope field names and versioning;
- battle ticket, KCP payload, snapshot, event, result, and replay contracts;
- ruleset JSON schema and golden fixtures for cross-language compatibility.

The first draft intentionally mirrors the current Gensoulkyo HTTP MVP and the planned Nakama + C++ battle split. It is not generated into the other repositories yet.

## Layout

- `proto/phk/v1/`: protobuf schema draft.
- `descriptors/`: dependency-light JSON descriptor exported from the v0.1 proto draft for early Go/C++/Godot consumers before generated code is wired.
- `gen/go/phk/v1/`: dependency-light Go manifest package generated from the descriptor. It is a temporary Go binding scaffold for version/field compatibility checks until `protoc --go_out` is wired.
- `gen/cpp/phk/v1/`: dependency-light C++ manifest header generated from the descriptor. It is a temporary C++ binding scaffold for version/field compatibility checks until generated protobuf C++ bindings are wired.
- `schemas/`: JSON schema for ruleset and envelope-adjacent documents.
- `fixtures/`: minimal golden fixtures for version, ticket, input, snapshot, event, result, and replay metadata.
- `tools/`: local validation scripts.
- `docs/`: notes for codegen and compatibility policy.
- `dev/`: progress notes.

## Validate

```powershell
python tools/export_descriptor.py
python tools/export_go_manifest.py
python tools/export_cpp_manifest.py
python tools/check_protocol.py
```

The exporters/checker are dependency-light. The checker validates proto package coverage, required security/version fields, fixture JSON syntax, ruleset schema basics, that `descriptors/phk_v1_descriptor.json` is in sync with the proto source files, and that the Go/C++ manifests match the descriptor.
