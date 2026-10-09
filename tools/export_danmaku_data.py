#!/usr/bin/env python3
"""Derive codegen-friendly danmaku data files from the reverse-engineering contract.

Inputs (authoritative):
  - data/tna_contract.json          (rev/tools/gen_contract.py output: bullet kinds/species/motions/player shots)
  - rev/patterns/player_shots_disasm.md  (13 player bombs; not present in the contract JSON)

Outputs:
  - data/danmaku_kinds.json         216 enemy bullet kinds (type -> species/frame/atlas)
  - data/danmaku_motions.json       79 enemy bullet motion primitives (bulletFuncN)
  - data/player_loadout.json        52 player shots + 13 player bombs

The reverse-engineering artifacts describe 千夜追忆 (Touhou: Thousand Night Anamnesis) 1.40
and are used here only for a self-developed derivative game mode. See docs/danmaku_contract.md.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "data" / "tna_contract.json"
KINDS_PATH = ROOT / "data" / "danmaku_kinds.json"
MOTIONS_PATH = ROOT / "data" / "danmaku_motions.json"
LOADOUT_PATH = ROOT / "data" / "player_loadout.json"

SCHEMA_VERSION = "1.0.0"
SOURCE_CONTRACT = "data/tna_contract.json (千夜追忆 1.40 libMyGame.so 逆向)"
SOURCE_BOMBS = "rev/patterns/player_shots_disasm.md §3.3"

FRAME_RE = re.compile(r"^(?P<species>.+)_(?P<frame>\d+)$")

# --- Player bombs (transcribed from rev/patterns/player_shots_disasm.md §3.1 + §3.3) ---
# `total_frames` = MyShip #1368 (bombRemainTime, table 0xb23d50);
# `invuln_frames` = MyShip #1372 (bombMutekiCnt, table 0xb23d0b);
# `types`/`sprites` list the 1..N MyBomb sprites in creation order (§3.3).
# `bullets` counts the number of MyBomb instances created per activation.
BOMBS: list[dict[str, object]] = [
    {"name": "createBombReimu", "character": "Reimu", "total_frames": 320, "invuln_frames": 440,
     "types": [62, 62], "sprites": ["mybomb_reimu_01"]},
    {"name": "createBombMarisa", "character": "Marisa", "total_frames": 200, "invuln_frames": 320,
     "types": [64, 64, 64, 64, 64, 64, 63, 63, 64],
     "sprites": ["mybomb_marisa_02", "mybomb_marisa_01"]},
    {"name": "createBombSanae", "character": "Sanae", "total_frames": 250, "invuln_frames": 370,
     "types": [65, 65, 65], "sprites": ["mybomb_sanae_01"]},
    {"name": "createBombSakuya", "character": "Sakuya", "total_frames": 200, "invuln_frames": 320,
     "types": [66, 67, 66, 66], "sprites": ["mybomb_sakuya_01", "mybomb_sakuya_02"]},
    {"name": "createBombReisen", "character": "Reisen", "total_frames": 400, "invuln_frames": 520,
     "types": [68, 69, 70],
     "sprites": ["mybomb_reisen_01", "mybomb_reisen_02", "mybomb_reisen_03"]},
    {"name": "createBombYoumu", "character": "Youmu", "total_frames": 260, "invuln_frames": 380,
     "types": [71], "sprites": ["mybomb_youmu_01"]},
    {"name": "createBombAya", "character": "Aya", "total_frames": 400, "invuln_frames": 520,
     "types": [72], "sprites": ["mybomb_aya_01"]},
    {"name": "createBombSeija", "character": "Seija", "total_frames": 200, "invuln_frames": 320,
     "types": [73], "sprites": ["mybomb_seija_01"]},
    {"name": "createBombCirno", "character": "Cirno", "total_frames": 300, "invuln_frames": 420,
     "types": [74, 75], "sprites": ["mybomb_cirno_01", "mybomb_cirno_02"]},
    {"name": "createBombYukari", "character": "Yukari", "total_frames": 200, "invuln_frames": 440,
     "types": [76, 77, 76, 76, 76],
     "sprites": ["mybomb_yukari_01", "mybomb_yukari_02"]},
    {"name": "createBombAlice", "character": "Alice", "total_frames": 200, "invuln_frames": 320,
     "types": [78, 79], "sprites": ["mybomb_alice_01"]},
    {"name": "createBombRemillia", "character": "Remillia", "total_frames": 200, "invuln_frames": 320,
     "types": [80, 80, 80], "sprites": ["mybomb_remillia_01"]},
    {"name": "createBombYuyuko", "character": "Yuyuko", "total_frames": 300, "invuln_frames": 420,
     "types": [81, 82, 81], "sprites": ["mybomb_yuyuko_01", "mybomb_yuyuko_02"]},
]


def family_code(family_group: str) -> str:
    """Return the coarse family letter (A..M), or '' for the unclassified bucket."""
    group = (family_group or "").strip()
    if group and group[0] in "ABCDEFGHIJKLM":
        return group[0]
    return ""


def split_frame(frame: str) -> tuple[str, int]:
    stem = frame[:-4] if frame.endswith(".png") else frame
    match = FRAME_RE.match(stem)
    if not match:
        return stem, 0
    return match.group("species"), int(match.group("frame"))


def build_kinds(contract: dict[str, object]) -> list[dict[str, object]]:
    kinds: list[dict[str, object]] = []
    for item in contract["bullet_kinds"]:
        species, frame = split_frame(str(item["frame"]))
        kinds.append(
            {
                "type": int(item["type"]),
                "species": species,
                "frame": frame,
                "frame_name": str(item["frame"])[:-4] if str(item["frame"]).endswith(".png") else str(item["frame"]),
                "atlas": str(item["atlas"]),
            }
        )
    kinds.sort(key=lambda k: k["type"])
    return kinds


def build_motions(contract: dict[str, object]) -> list[dict[str, object]]:
    motions: list[dict[str, object]] = []
    for item in contract["bullet_motions"]:
        group = str(item.get("family_group", ""))
        motions.append(
            {
                "func": int(item["func"]),
                "addr": str(item["addr"]),
                "size_bytes": int(item["size_bytes"]),
                "family": str(item.get("family", "")),
                "family_group": group,
                "family_code": family_code(group),
            }
        )
    motions.sort(key=lambda m: m["func"])
    return motions


def build_shots(contract: dict[str, object]) -> list[dict[str, object]]:
    shots: list[dict[str, object]] = []
    for item in contract["player_shots"]:
        shots.append(
            {
                "name": str(item["name"]),
                "character": str(item["chara"]),
                "mode": str(item["mode"]),
                "variant": int(item["variant"]),
                "volley_count": int(item["volley_n"]),
                "bullet_types": [int(t) for t in item.get("tex_types", [])],
                "angles_deg": [float(a) for a in item.get("angles_deg", [])],
                "speed": item.get("speed_n"),
                "muzzle": str(item.get("muzzle", "")),
                "resolved": bool(item.get("resolved", False)),
                "raw": {
                    "tex_type": str(item.get("tex_type", "")),
                    "angle": str(item.get("angle", "")),
                    "speed": str(item.get("speed", "")),
                    "volley": str(item.get("volley", "")),
                },
            }
        )
    return shots


def build_bombs() -> list[dict[str, object]]:
    bombs: list[dict[str, object]] = []
    for item in BOMBS:
        bombs.append(
            {
                "name": item["name"],
                "character": item["character"],
                "total_frames": int(item["total_frames"]),
                "invuln_frames": int(item["invuln_frames"]),
                "bullet_count": len(item["types"]),
                "bullet_types": [int(t) for t in item["types"]],
                "sprites": list(item["sprites"]),
                "notes": "w1..w5 参数语义未确定（见 player_shots_disasm.md §5）",
            }
        )
    return bombs


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"exported {path.relative_to(ROOT)}")


def main() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    playfield = contract["playfield"]
    kinds = build_kinds(contract)
    motions = build_motions(contract)
    shots = build_shots(contract)
    bombs = build_bombs()

    write_json(
        KINDS_PATH,
        {
            "schema_version": SCHEMA_VERSION,
            "source": SOURCE_CONTRACT,
            "unit": "degree; positions in milli (1/1000 px) server-side",
            "playfield": playfield,
            "tick_rate_hz": int(contract["tick_rate_hz"]),
            "count": len(kinds),
            "kinds": kinds,
        },
    )
    write_json(
        MOTIONS_PATH,
        {
            "schema_version": SCHEMA_VERSION,
            "source": "rev/patterns/bullet_funcs_disasm.md, rev/patterns/create_bullet_command.md",
            "note": "func == 原版 EnemyBullet::bulletFuncN 编号 == 运行期状态号 (+0x5B4, 1..85)",
            "count": len(motions),
            "motions": motions,
        },
    )
    write_json(
        LOADOUT_PATH,
        {
            "schema_version": SCHEMA_VERSION,
            "source": [SOURCE_CONTRACT, SOURCE_BOMBS],
            "note": "angle 单位=度；cocos2d 原点在左下，angle=90 朝正上",
            "shot_count": len(shots),
            "bomb_count": len(bombs),
            "shots": shots,
            "bombs": bombs,
        },
    )

    print(f"danmaku data: {len(kinds)} kinds, {len(motions)} motions, {len(shots)} shots, {len(bombs)} bombs")


if __name__ == "__main__":
    main()
