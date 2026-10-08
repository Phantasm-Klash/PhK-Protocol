# Codegen Plan

`PhK-Protocol` v0.1 will generate artifacts for three open-source consumers:

- Go package for Gensoulkyo Nakama runtime and HTTP fallback tests.
- C++ headers/sources for PhK-BattleServer.
- Godot-friendly descriptor JSON or a native networking module binding for SpellKard.

Planned command shape:

```powershell
python tools/export_descriptor.py
python tools/export_go_manifest.py
protoc -I proto --go_out=gen/go proto/phk/v1/*.proto
protoc -I proto --cpp_out=gen/cpp proto/phk/v1/*.proto
python tools/export_godot_descriptors.py
```

The first draft does not require `protoc` so the repository can be validated on a clean machine. `tools/export_descriptor.py` writes `descriptors/phk_v1_descriptor.json`, which is the temporary cross-repository descriptor consumed by SpellKard and checked by PhK-BattleServer until real generated bindings are wired. `tools/export_go_manifest.py` writes `gen/go/phk/v1/manifest.go`, a dependency-light Go package that lets Gensoulkyo validate protocol versions and required fields before full protobuf Go bindings are available. `tools/export_cpp_manifest.py` writes `gen/cpp/phk/v1/manifest.hpp` with matching C++ constants and field lookups. The Go/C++ manifests also export selected golden fixture values, including the replay input stream summary IDs, counts, stream hashes, final state hash, and final tick from `fixtures/v0_1_minimal_flow.json`; `tools/check_protocol.py` verifies those constants remain in sync with the fixture. Once codegen is wired, generated artifacts must include the source protocol tag and checksum.

## Danmaku (千夜追忆) codegen

The danmaku contract (`proto/phk/v1/danmaku.proto`) is generated into C++ and Go without `protoc`:

```powershell
python tools/export_danmaku_data.py    # data/tna_contract.json -> data/danmaku_kinds.json,
                                       #   data/danmaku_motions.json, data/player_loadout.json
python tools/export_danmaku_cpp.py     # -> gen/cpp/phk/v1/danmaku.hpp (enums + POD + lookup tables)
python tools/export_danmaku_go.py      # -> gen/go/phk/v1/danmaku.go  (consts + maps + loadout)
```

- Enum names come from `danmaku.proto` (single source of truth); the info tables
  (frame/atlas/family) come from the derived `data/*.json`.
- `gen/cpp/phk/v1/danmaku.hpp` is header-only (standard library only) and lives in the same
  include root as `manifest.hpp`, so PhK-BattleServer's CMake discovers it unchanged.
- No TypeScript generator exists in this repository (the existing pipeline only emits Go, C++,
  and the JSON descriptor), so no TS artifact is produced.
- `tools/check_protocol.py` verifies: proto enum values == data files, the 28-field
  `BulletSpawnCommand` layout, the new battle payload value, and that both generated artifacts
  match a fresh render. See `docs/danmaku_contract.md` for field/unit semantics.

## Compatibility Rules

- `protocol_version`, `ruleset_version`, and `ruleset_hash` are required on all cross-service payload families.
- A battle ticket binds match id, user id, player id, mode id, deck snapshot hash, ruleset version, battle server id, endpoint, nonce, expiry, and signing key id.
- Battle payloads carry tick, seq, ack, payload type, nonce, and key id before encryption.
- Clients never submit score, graze, hit count, damage, rewards, rank, Boss HP, card results, chest results, replay results, or settlement results.
- Business and battle protocols can version independently, but matchmaking must reject clients whose version tuple is not allowed for the chosen mode.
