#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTO_DIR = ROOT / "proto" / "phk" / "v1"
DESCRIPTOR_DIR = ROOT / "descriptors"
DESCRIPTOR_PATH = DESCRIPTOR_DIR / "phk_v1_descriptor.json"


FIELD_RE = re.compile(
    r"^\s*(?:(repeated)\s+)?(?:(map)<\s*([^,]+)\s*,\s*([^)>\s]+)\s*>\s+|([A-Za-z_][A-Za-z0-9_.]*)\s+)([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\d+)\s*;",
    re.MULTILINE,
)
MESSAGE_RE = re.compile(r"\bmessage\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{", re.MULTILINE)
ENUM_RE = re.compile(r"\benum\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{", re.MULTILINE)
ENUM_VALUE_RE = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*=\s*(\d+)\s*;", re.MULTILINE)
IMPORT_RE = re.compile(r'^\s*import\s+"([^"]+)";', re.MULTILINE)
PACKAGE_RE = re.compile(r"^\s*package\s+([A-Za-z0-9_.]+)\s*;", re.MULTILINE)
GO_PACKAGE_RE = re.compile(r'^\s*option\s+go_package\s*=\s*"([^"]+)";', re.MULTILINE)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def body_for(text: str, keyword: str, name: str) -> str:
    match = re.search(rf"\b{keyword}\s+{re.escape(name)}\s*\{{", text)
    if not match:
        return ""
    start = match.end()
    depth = 1
    index = start
    while index < len(text) and depth > 0:
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
        index += 1
    return text[start : index - 1]


def parse_fields(body: str) -> list[dict[str, object]]:
    fields: list[dict[str, object]] = []
    for match in FIELD_RE.finditer(body):
        is_repeated = bool(match.group(1))
        is_map = bool(match.group(2))
        if is_map:
            field_type = f"map<{match.group(3).strip()},{match.group(4).strip()}>"
        else:
            field_type = match.group(5)
        fields.append(
            {
                "number": int(match.group(7)),
                "name": match.group(6),
                "type": field_type,
                "repeated": is_repeated,
                "map": is_map,
            }
        )
    return fields


def parse_proto(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    package_match = PACKAGE_RE.search(text)
    go_package_match = GO_PACKAGE_RE.search(text)
    messages = []
    for message_name in MESSAGE_RE.findall(text):
        messages.append({"name": message_name, "fields": parse_fields(body_for(text, "message", message_name))})
    enums = []
    for enum_name in ENUM_RE.findall(text):
        body = body_for(text, "enum", enum_name)
        values = [{"name": name, "number": int(number)} for name, number in ENUM_VALUE_RE.findall(body)]
        enums.append({"name": enum_name, "values": values})
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": sha256_text(text),
        "package": package_match.group(1) if package_match else "",
        "go_package": go_package_match.group(1) if go_package_match else "",
        "imports": IMPORT_RE.findall(text),
        "messages": messages,
        "enums": enums,
    }


def build_descriptor() -> dict[str, object]:
    fixture = json.loads((ROOT / "fixtures" / "v0_1_minimal_flow.json").read_text(encoding="utf-8"))
    ruleset_schema = json.loads((ROOT / "schemas" / "ruleset.schema.json").read_text(encoding="utf-8"))
    files = [parse_proto(path) for path in sorted(PROTO_DIR.glob("*.proto"))]
    source_digest_input = json.dumps(
        [{"path": item["path"], "sha256": item["sha256"]} for item in files],
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return {
        "descriptor_version": "0.1.0-draft",
        "package": "phk.v1",
        "protocol_version": int(fixture.get("protocol_version", 0)),
        "business_api_version": str(fixture.get("business_api_version", "")),
        "battle_api_version": str(fixture.get("battle_api_version", "")),
        "ruleset_version": str(fixture.get("ruleset_version", "")),
        "ruleset_hash": str(fixture.get("ruleset_hash", "")),
        "source_digest_sha256": sha256_text(source_digest_input),
        "ruleset_required_keys": list(ruleset_schema.get("required", [])),
        "files": files,
    }


def main() -> None:
    DESCRIPTOR_DIR.mkdir(parents=True, exist_ok=True)
    descriptor = build_descriptor()
    DESCRIPTOR_PATH.write_text(json.dumps(descriptor, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"exported {DESCRIPTOR_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
