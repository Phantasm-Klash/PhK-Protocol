#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from export_descriptor import build_descriptor


ROOT = Path(__file__).resolve().parents[1]
PROTO_DIR = ROOT / "proto" / "phk" / "v1"
GO_MANIFEST_PATH = ROOT / "gen" / "go" / "phk" / "v1" / "manifest.go"
CPP_MANIFEST_PATH = ROOT / "gen" / "cpp" / "phk" / "v1" / "manifest.hpp"

REQUIRED_PROTO_FILES = {
    "common.proto",
    "business.proto",
    "matchmaking.proto",
    "battle.proto",
    "replay.proto",
    "admin.proto",
}

REQUIRED_MESSAGES = {
    "business.proto": ["BusinessSecureEnvelope", "BusinessEnvelopePlaintext", "BusinessAck"],
    "matchmaking.proto": ["BattleTicket", "SignedBattleTicket", "BattleServerAllocation"],
    "battle.proto": [
        "BattlePacketHeader",
        "BattleEncryptedPacket",
        "BattleHandshakeHello",
        "BattleHandshakeAccept",
        "BattleInput",
        "BattleModeAction",
        "BattleSnapshot",
        "BattleEvent",
        "BattleResult",
        "SignedBattleResult",
    ],
    "replay.proto": ["ReplayInputStreamSummary", "ReplayRecord"],
    "admin.proto": ["BattleServerHeartbeat", "BattleResultSubmitRequest", "BattleResultSubmitResponse"],
}

REQUIRED_FIELD_NAMES = {
    "BusinessSecureEnvelope": [
        "version",
        "session_id",
        "seq",
        "timestamp_ms",
        "nonce",
        "op_code",
        "key_id",
        "aead_alg",
        "body_ciphertext",
        "auth_tag",
    ],
    "BattleTicket": [
        "version",
        "ticket_id",
        "match_id",
        "user_id",
        "player_id",
        "mode_id",
        "battle_server_id",
        "endpoint",
        "deck_snapshot_hash",
        "ruleset_version",
        "ticket_nonce",
        "expires_at_ms",
    ],
    "BattlePacketHeader": [
        "version",
        "match_id",
        "player_id",
        "tick",
        "seq",
        "ack",
        "payload_type",
        "key_id",
        "nonce",
    ],
    "BattleInput": [
        "match_id",
        "player_id",
        "tick",
        "seq",
        "direction_bits",
        "slow",
        "shoot",
        "bomb",
        "card_slot",
    ],
    "BattleModeAction": [
        "match_id",
        "player_id",
        "tick",
        "seq",
        "action_id",
        "action_type",
        "payload_json",
        "client_result_authoritative",
    ],
    "BattleSnapshot": ["match_id", "snapshot_tick", "snapshot_kind", "state_hash", "players", "bullets_delta", "event_cursor"],
    "BattleEvent": ["match_id", "cursor", "tick", "type", "server_authoritative"],
    "BattleResult": ["match_id", "mode_id", "result_hash", "replay_id", "player_ids", "settled_at_ms"],
    "ReplayInputStreamSummary": [
        "version",
        "replay_id",
        "match_id",
        "owner_user_id",
        "input_count",
        "event_count",
        "input_stream_hash",
        "event_stream_hash",
        "final_state_hash",
        "final_tick",
    ],
}


def fail(message: str) -> None:
    print(f"check_protocol failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail(f"missing {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def message_body(proto_text: str, message_name: str) -> str:
    match = re.search(rf"message\s+{re.escape(message_name)}\s*\{{(?P<body>.*?)\n\}}", proto_text, re.S)
    if not match:
        fail(f"missing message {message_name}")
    return match.group("body")


def has_message(proto_text: str, message_name: str) -> bool:
    return re.search(rf"\bmessage\s+{re.escape(message_name)}\s*\{{", proto_text) is not None


def check_proto_files() -> None:
    existing = {path.name for path in PROTO_DIR.glob("*.proto")}
    missing = REQUIRED_PROTO_FILES - existing
    if missing:
        fail(f"missing proto files {sorted(missing)}")
    for proto_name in REQUIRED_PROTO_FILES:
        text = read(PROTO_DIR / proto_name)
        if 'package phk.v1;' not in text:
            fail(f"{proto_name} missing package phk.v1")
        if 'option go_package = ' not in text:
            fail(f"{proto_name} missing go_package option")
        for message_name in REQUIRED_MESSAGES.get(proto_name, []):
            message_body(text, message_name)
        for message_name, fields in REQUIRED_FIELD_NAMES.items():
            if not has_message(text, message_name):
                continue
            body = message_body(text, message_name)
            for field in fields:
                if not re.search(rf"\b{re.escape(field)}\s*=", body):
                    fail(f"{message_name} missing field {field}")


def check_json_files() -> None:
    for path in [ROOT / "schemas" / "ruleset.schema.json", ROOT / "fixtures" / "v0_1_minimal_flow.json"]:
        with path.open("r", encoding="utf-8") as handle:
            json.load(handle)


def check_ruleset_schema() -> None:
    schema = json.loads((ROOT / "schemas" / "ruleset.schema.json").read_text(encoding="utf-8"))
    required = set(schema.get("required", []))
    expected = {"ruleset_version", "ruleset_hash", "modes", "stages", "characters", "cards", "bullet_patterns"}
    missing = expected - required
    if missing:
        fail(f"ruleset schema missing required keys {sorted(missing)}")


def check_fixture() -> None:
    fixture = json.loads((ROOT / "fixtures" / "v0_1_minimal_flow.json").read_text(encoding="utf-8"))
    for key in ["protocol_version", "ruleset_version", "business_envelope", "battle_ticket", "battle_input", "battle_mode_action", "battle_snapshot", "battle_event", "battle_result", "golden_replay_summary", "signed_battle_result_callback"]:
        if key not in fixture:
            fail(f"fixture missing {key}")
    forbidden_client_result_fields = {"score", "graze", "hits", "damage", "rewards", "boss_hp", "rank"}
    if forbidden_client_result_fields & set(fixture["battle_input"].keys()):
        fail("battle_input contains forbidden client-authored result fields")
    mode_action = fixture["battle_mode_action"]
    for key in ["match_id", "player_id", "tick", "seq", "action_id", "action_type", "payload_json", "client_result_authoritative"]:
        if key not in mode_action:
            fail(f"battle_mode_action missing {key}")
    if mode_action.get("client_result_authoritative", True):
        fail("battle_mode_action must not be client result authoritative")
    battle_snapshot = fixture["battle_snapshot"]
    for key in ["match_id", "snapshot_tick", "snapshot_kind", "state_hash", "event_cursor"]:
        if key not in battle_snapshot:
            fail(f"battle_snapshot missing {key}")
    battle_event = fixture["battle_event"]
    for key in ["match_id", "cursor", "tick", "type", "server_authoritative"]:
        if key not in battle_event:
            fail(f"battle_event missing {key}")
    if battle_event.get("server_authoritative") is not True:
        fail("battle_event must be server authoritative")
    replay_summary = fixture["golden_replay_summary"]
    for key in ["replay_id", "match_id", "owner_user_id", "input_count", "event_count", "input_stream_hash", "event_stream_hash", "final_state_hash", "final_tick"]:
        if key not in replay_summary:
            fail(f"golden_replay_summary missing {key}")
    for key in ["input_count", "event_count", "final_tick"]:
        if not isinstance(replay_summary.get(key), int) or replay_summary.get(key, 0) < 0:
            fail(f"golden_replay_summary {key} must be a non-negative integer")
    for key in ["input_stream_hash", "event_stream_hash", "final_state_hash"]:
        if not str(replay_summary.get(key, "")).startswith("sha256:"):
            fail(f"golden_replay_summary {key} must be a sha256 hash label")
    if replay_summary.get("match_id") != fixture["battle_result"].get("match_id"):
        fail("golden_replay_summary match_id must match battle_result")
    if replay_summary.get("final_state_hash") != battle_snapshot.get("state_hash"):
        fail("golden_replay_summary final_state_hash must match battle_snapshot state_hash")
    if replay_summary.get("final_tick") != battle_snapshot.get("snapshot_tick"):
        fail("golden_replay_summary final_tick must match battle_snapshot snapshot_tick")
    if replay_summary.get("event_count") != battle_event.get("cursor"):
        fail("golden_replay_summary event_count must match battle_event cursor")
    callback = fixture["signed_battle_result_callback"]
    result = callback.get("result", {})
    for key in ["match_id", "mode_id", "result_hash", "replay_id", "player_ids", "settled_at_ms"]:
        if key not in result:
            fail(f"signed battle result callback missing result.{key}")
    if callback.get("signature_alg") != "ED25519":
        fail("signed battle result callback must use ED25519")
    if len(str(callback.get("signature_hex", ""))) != 128:
        fail("signed battle result callback signature_hex must be 64 bytes hex")
    if not callback.get("server_authoritative", False):
        fail("signed battle result callback must be server authoritative")
    if replay_summary.get("replay_id") != result.get("replay_id"):
        fail("golden_replay_summary replay_id must match signed battle result callback")
    if replay_summary.get("match_id") != result.get("match_id"):
        fail("golden_replay_summary match_id must match signed battle result callback")


def check_descriptor() -> None:
    descriptor_path = ROOT / "descriptors" / "phk_v1_descriptor.json"
    if not descriptor_path.exists():
        fail("missing descriptors/phk_v1_descriptor.json; run tools/export_descriptor.py")
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    expected = build_descriptor()
    if descriptor != expected:
        fail("descriptor is out of date; run tools/export_descriptor.py")
    message_names = {
        message.get("name")
        for proto_file in descriptor.get("files", [])
        for message in proto_file.get("messages", [])
    }
    for required in ["BusinessSecureEnvelope", "BattleTicket", "BattlePacketHeader", "BattleInput", "BattleModeAction", "BattleSnapshot", "BattleEvent", "BattleResult", "ReplayInputStreamSummary"]:
        if required not in message_names:
            fail(f"descriptor missing message {required}")


def check_go_manifest() -> None:
    if not GO_MANIFEST_PATH.exists():
        fail("missing gen/go/phk/v1/manifest.go; run tools/export_go_manifest.py")
    manifest = GO_MANIFEST_PATH.read_text(encoding="utf-8")
    descriptor = build_descriptor()
    expected_constants = {
        "DescriptorVersion": str(descriptor.get("descriptor_version", "")),
        "PackageName": str(descriptor.get("package", "")),
        "BusinessAPIVersion": str(descriptor.get("business_api_version", "")),
        "BattleAPIVersion": str(descriptor.get("battle_api_version", "")),
        "RulesetVersion": str(descriptor.get("ruleset_version", "")),
        "RulesetHash": str(descriptor.get("ruleset_hash", "")),
        "SourceDigestSHA256": str(descriptor.get("source_digest_sha256", "")),
    }
    fixture = json.loads((ROOT / "fixtures" / "v0_1_minimal_flow.json").read_text(encoding="utf-8"))
    battle_snapshot = fixture["battle_snapshot"]
    battle_event = fixture["battle_event"]
    replay_summary = fixture["golden_replay_summary"]
    expected_constants.update(
        {
            "BattleSnapshotMatchID": str(battle_snapshot.get("match_id", "")),
            "BattleSnapshotSnapshotKind": str(battle_snapshot.get("snapshot_kind", "")),
            "BattleSnapshotStateHash": str(battle_snapshot.get("state_hash", "")),
            "BattleEventMatchID": str(battle_event.get("match_id", "")),
            "BattleEventType": str(battle_event.get("type", "")),
            "GoldenReplaySummaryReplayID": str(replay_summary.get("replay_id", "")),
            "GoldenReplaySummaryMatchID": str(replay_summary.get("match_id", "")),
            "GoldenReplaySummaryOwnerUserID": str(replay_summary.get("owner_user_id", "")),
            "GoldenReplaySummaryInputStreamHash": str(replay_summary.get("input_stream_hash", "")),
            "GoldenReplaySummaryEventStreamHash": str(replay_summary.get("event_stream_hash", "")),
            "GoldenReplaySummaryFinalStateHash": str(replay_summary.get("final_state_hash", "")),
        }
    )
    for name, value in expected_constants.items():
        if f'{name} = "{value}"' not in manifest:
            fail(f"Go manifest {name} is out of sync")
    if f"ProtocolVersion = {int(descriptor.get('protocol_version', 0))}" not in manifest:
        fail("Go manifest ProtocolVersion is out of sync")
    expected_int_constants = {
        "BattleSnapshotSnapshotTick": int(battle_snapshot.get("snapshot_tick", 0)),
        "BattleSnapshotEventCursor": int(battle_snapshot.get("event_cursor", 0)),
        "BattleEventCursor": int(battle_event.get("cursor", 0)),
        "BattleEventTick": int(battle_event.get("tick", 0)),
        "GoldenReplaySummaryInputCount": int(replay_summary.get("input_count", 0)),
        "GoldenReplaySummaryEventCount": int(replay_summary.get("event_count", 0)),
        "GoldenReplaySummaryFinalTick": int(replay_summary.get("final_tick", 0)),
    }
    for name, value in expected_int_constants.items():
        if f"{name} = {value}" not in manifest:
            fail(f"Go manifest {name} is out of sync")
    if f"BattleEventServerAuthoritative = {str(bool(battle_event.get('server_authoritative', False))).lower()}" not in manifest:
        fail("Go manifest BattleEventServerAuthoritative is out of sync")
    for message_name in ["BusinessSecureEnvelope", "BattleTicket", "BattlePacketHeader", "BattleInput", "BattleModeAction", "BattleSnapshot", "BattleEvent", "BattleResult", "ReplayInputStreamSummary"]:
        if f'"{message_name}":' not in manifest:
            fail(f"Go manifest missing message {message_name}")
        for field in REQUIRED_FIELD_NAMES.get(message_name, []):
            if f'"{field}"' not in manifest:
                fail(f"Go manifest {message_name} missing field {field}")


def check_cpp_manifest() -> None:
    if not CPP_MANIFEST_PATH.exists():
        fail("missing gen/cpp/phk/v1/manifest.hpp; run tools/export_cpp_manifest.py")
    manifest = CPP_MANIFEST_PATH.read_text(encoding="utf-8")
    descriptor = build_descriptor()
    expected_constants = {
        "kDescriptorVersion": str(descriptor.get("descriptor_version", "")),
        "kPackageName": str(descriptor.get("package", "")),
        "kBusinessApiVersion": str(descriptor.get("business_api_version", "")),
        "kBattleApiVersion": str(descriptor.get("battle_api_version", "")),
        "kRulesetVersion": str(descriptor.get("ruleset_version", "")),
        "kRulesetHash": str(descriptor.get("ruleset_hash", "")),
        "kSourceDigestSha256": str(descriptor.get("source_digest_sha256", "")),
    }
    fixture = json.loads((ROOT / "fixtures" / "v0_1_minimal_flow.json").read_text(encoding="utf-8"))
    battle_snapshot = fixture["battle_snapshot"]
    battle_event = fixture["battle_event"]
    replay_summary = fixture["golden_replay_summary"]
    expected_constants.update(
        {
            "kBattleSnapshotMatchId": str(battle_snapshot.get("match_id", "")),
            "kBattleSnapshotSnapshotKind": str(battle_snapshot.get("snapshot_kind", "")),
            "kBattleSnapshotStateHash": str(battle_snapshot.get("state_hash", "")),
            "kBattleEventMatchId": str(battle_event.get("match_id", "")),
            "kBattleEventType": str(battle_event.get("type", "")),
            "kGoldenReplaySummaryReplayId": str(replay_summary.get("replay_id", "")),
            "kGoldenReplaySummaryMatchId": str(replay_summary.get("match_id", "")),
            "kGoldenReplaySummaryOwnerUserId": str(replay_summary.get("owner_user_id", "")),
            "kGoldenReplaySummaryInputStreamHash": str(replay_summary.get("input_stream_hash", "")),
            "kGoldenReplaySummaryEventStreamHash": str(replay_summary.get("event_stream_hash", "")),
            "kGoldenReplaySummaryFinalStateHash": str(replay_summary.get("final_state_hash", "")),
        }
    )
    for name, value in expected_constants.items():
        if f'{name} = "{value}"' not in manifest:
            fail(f"C++ manifest {name} is out of sync")
    if f"kProtocolVersion = {int(descriptor.get('protocol_version', 0))}" not in manifest:
        fail("C++ manifest kProtocolVersion is out of sync")
    expected_int_constants = {
        "kBattleSnapshotSnapshotTick": int(battle_snapshot.get("snapshot_tick", 0)),
        "kBattleSnapshotEventCursor": int(battle_snapshot.get("event_cursor", 0)),
        "kBattleEventCursor": int(battle_event.get("cursor", 0)),
        "kBattleEventTick": int(battle_event.get("tick", 0)),
        "kGoldenReplaySummaryInputCount": int(replay_summary.get("input_count", 0)),
        "kGoldenReplaySummaryEventCount": int(replay_summary.get("event_count", 0)),
        "kGoldenReplaySummaryFinalTick": int(replay_summary.get("final_tick", 0)),
    }
    for name, value in expected_int_constants.items():
        if f"{name} = {value}" not in manifest:
            fail(f"C++ manifest {name} is out of sync")
    if f"kBattleEventServerAuthoritative = {str(bool(battle_event.get('server_authoritative', False))).lower()}" not in manifest:
        fail("C++ manifest kBattleEventServerAuthoritative is out of sync")
    for message_name in ["BusinessSecureEnvelope", "BattleTicket", "BattlePacketHeader", "BattleInput", "BattleModeAction", "BattleSnapshot", "BattleEvent", "BattleResult", "ReplayInputStreamSummary"]:
        for field in REQUIRED_FIELD_NAMES.get(message_name, []):
            if f'{{"{message_name}", "{field}"}}' not in manifest:
                fail(f"C++ manifest {message_name} missing field {field}")


def main() -> None:
    check_proto_files()
    check_json_files()
    check_ruleset_schema()
    check_fixture()
    check_descriptor()
    check_go_manifest()
    check_cpp_manifest()
    print("check_protocol ok")


if __name__ == "__main__":
    main()
