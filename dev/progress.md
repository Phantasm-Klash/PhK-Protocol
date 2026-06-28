# PhK-Protocol Development Progress

Status date: 2026-06-27

| Area | Status | Notes |
| --- | --- | --- |
| Repository skeleton | Started | Protocol directories, README, licenses, schema, fixture, docs, and checker are present. |
| Protobuf draft | Started | `common`, `business`, `matchmaking`, `battle`, `replay`, and `admin` proto files cover secure envelope, battle ticket, allocation, encrypted packet headers, handshake, input, snapshot, event, result, replay record, server heartbeat, and result submit messages. |
| Ruleset schema | Started | Draft JSON schema covers ruleset version/hash, modes, stages, characters, cards, and bullet patterns. |
| Golden fixtures | Started | Minimal v0.1 flow fixture covers business envelope, battle ticket, input, snapshot, event, and result. |
| Descriptor export | Started | `tools/export_descriptor.py` exports `descriptors/phk_v1_descriptor.json` from the proto draft without requiring `protoc`; `tools/check_protocol.py` verifies the descriptor is in sync with the source proto files. |
| Go manifest export | Started | `tools/export_go_manifest.py` exports `gen/go/phk/v1/manifest.go`, a dependency-light Go binding scaffold with version constants, source digest, and message field manifests. The checker verifies it remains in sync with the descriptor. |
| C++ manifest export | Started | `tools/export_cpp_manifest.py` exports `gen/cpp/phk/v1/manifest.hpp`, a dependency-light C++ binding scaffold with version constants, source digest, ruleset hash, and constexpr message-field lookup helpers. The checker verifies it remains in sync with the descriptor. |
| Codegen | Started | Go and C++ manifest generation are wired as temporary compatibility packages. Full protobuf Go/C++/Godot generation is still pending. |
| Consumer integration | Started | Gensoulkyo and SpellKard now mirror the draft battle allocation/signed-ticket shape through HTTP fallback contract tests. SpellKard loads the shared descriptor for Network Match status/contract validation. PhK-BattleServer now consumes the generated C++ manifest header for version/ruleset constants and message-field gates while still mirroring ticket/header/input structs until generated protobuf bindings are wired. Gensoulkyo consumes the Go manifest for protocol-version compatibility gates; full generated Go/C++/Godot message bindings remain pending. |
