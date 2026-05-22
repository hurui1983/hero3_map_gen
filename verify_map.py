"""验证最近一次 RMG 生成的地图含哪些目标神器/对象.

用法:
  python3 verify_map.py              # 自动选 random_maps/ 里最新的 .h3m
  python3 verify_map.py <h3m 路径>   # 指定文件

输出每个目标 sprite 在地图上找到几处. 0 处 = 没出现.
"""
from __future__ import annotations

import gzip
import re
import sys
from pathlib import Path

RANDOM_MAPS = Path(
    "/Applications/英雄无敌3：二合一.app/Contents/drive_c/game/random_maps"
)

# HoMM3 sprite 命名规则: AVA + 4 位 artifact ID + .def
TARGETS = {
    "末日之刃 (Armageddon's Blade)": ["ava0128.def"],
    "天使联盟 (Angelic Alliance)": ["ava0129.def"],
    "鬼王斗篷 (Cloak of the Undead King)": ["ava0130.def"],
    "生命灵药 (Elixir of Life)": ["ava0131.def"],
    "诅咒铠甲 (Armor of the Damned)": ["ava0132.def"],
    "军团雕像 (Statue of Legion)": ["ava0133.def"],
    "龙父神力 (Power of the Dragon Father)": ["ava0134.def"],
    "泰坦之雷 (Titan's Thunder)": ["ava0135.def"],
    "海军上将之帽 (Admiral's Hat)": ["ava0136.def"],
    "神射手之弓 (Bow of the Sharpshooter)": ["ava0137.def"],
    "魔力源泉 (Wizard's Well)": ["ava0138.def"],
    # 中立四大龙 sprite (HoMM3 SoD)
    "圣龙 (Azure Dragon)": ["avwazur.def", "avwk1u0.def"],
    "水晶龙 (Crystal Dragon)": ["avwcryd.def", "avwcdrg.def"],
    "仙龙 (Faerie Dragon)": ["avwfaer.def", "avwfdrg.def"],
    "锈龙 (Rust Dragon)": ["avwrust.def", "avwrdrg.def"],
}


def latest_h3m() -> Path:
    files = sorted(RANDOM_MAPS.glob("*.h3m"), key=lambda p: p.stat().st_mtime)
    if not files:
        sys.exit(f"random_maps/ 目录为空, 先在游戏里启动一次 RMG: {RANDOM_MAPS}")
    return files[-1]


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else latest_h3m()
    print(f"地图: {path.name}")
    print(f"大小: {path.stat().st_size} bytes (压缩)")

    with gzip.open(path, "rb") as f:
        data = f.read()
    print(f"      {len(data)} bytes (解压)\n")

    data_lower = data.lower()

    print("=== 目标对象搜索 (sprite 是否在 attribute table) ===")
    for name, patterns in TARGETS.items():
        hits = sum(data_lower.count(p.encode()) for p in patterns)
        if hits >= 5:
            mark = "[★★★]"  # 多 zone 都有, Object Rules 应该生效
        elif hits > 0:
            mark = "[OK]  "
        else:
            mark = "[----]"
        print(f"  {mark} {name}: sprite hits={hits}")

    # 增强: 真正数地图上的 instance 数量 (不只 sprite 在 attribute table)
    # 用 h3m.inject 的 find_oa/od 找 instance 段, 然后按 kind 引用统计
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from h3m.inject import find_oa_section, find_od_section
        import struct as _s

        oa_count_off, oa_count = find_oa_section(data)
        od_count_off, od_count = find_od_section(data, oa_count_off, oa_count)

        # 解析 attribute table, 建 def_name → kind 映射
        OA_FIXED = 42
        pos = oa_count_off + 4
        kind_by_def: dict[str, int] = {}
        kind_meta: dict[int, tuple[int, int]] = {}  # kind -> (class, subtype)
        for i in range(oa_count):
            def_size = _s.unpack("<I", data[pos:pos + 4])[0]
            pos += 4
            def_name = data[pos:pos + def_size].decode("ascii", errors="replace").lower()
            pos += def_size
            obj_class = _s.unpack("<I", data[pos + 16:pos + 20])[0]
            obj_number = _s.unpack("<I", data[pos + 20:pos + 24])[0]
            kind_by_def[def_name] = i
            kind_meta[i] = (obj_class, obj_number)
            pos += OA_FIXED

        # 在 instance 段搜每个目标 sprite 对应 kind 的引用次数
        # 严格 anchor: instance 起点 = x(1) y(1) z(1) kind(4) zeros(5).
        # 单 needle 容易 false positive (5 个 0 字节 .h3m 里到处都是),
        # 加 x/y/z 合理性校验 (z<=1, x/y<=252) 减少误报.
        instance_blob = data[od_count_off + 4:]
        print("\n=== 地图上实例数量 (按 attribute table kind 引用计数) ===")
        for name, patterns in TARGETS.items():
            total_inst = 0
            coords = []
            for pat in patterns:
                k = kind_by_def.get(pat.lower())
                if k is None:
                    continue
                needle = _s.pack("<I", k) + b"\x00" * 5
                start = 0
                while True:
                    idx = instance_blob.find(needle, start)
                    if idx < 0 or idx < 3:
                        break
                    x, y, z = instance_blob[idx-3], instance_blob[idx-2], instance_blob[idx-1]
                    # 严格筛: z 必 0 或 1, x/y 必 ≤252
                    if z <= 1 and x <= 252 and y <= 252:
                        total_inst += 1
                        coords.append((x, y, z))
                    start = idx + 1
            if total_inst > 0:
                coord_str = ", ".join(f"({x},{y},{z})" for x, y, z in coords[:8])
                if len(coords) > 8:
                    coord_str += f", ... +{len(coords)-8} more"
                print(f"  [实例]  {name}: {total_inst} 个  坐标: {coord_str}")

    except Exception as e:
        print(f"\n(实例数统计失败: {e})")

    # 组合神器组件检查 (HoMM3 SoD)
    # RMG 对 Map.Artifacts +ID 的处理: 可能放完整神器, 也可能散放它的组件.
    COMBO_COMPONENTS = {
        "末日之刃 (Armageddon's Blade)": {
            "components": {49: "Sword of Hellfire", 50: "Hellstorm Helmet",
                           51: "Blade of Armageddon", 52: "Shield of the Yawning Dead",
                           54: "Breastplate of Brimstone"},
            "complete": 128,
        },
        "天使联盟 (Angelic Alliance)": {
            "components": {97: "Sentinel's Shield", 107: "Helm of Heavenly Enlightenment",
                           78: "Lion's Shield of Courage", 88: "Sword of Judgement",
                           98: "Sandals of the Saint"},
            "complete": 129,
        },
    }
    print("\n=== 组合神器组件追踪 ===")
    for name, info in COMBO_COMPONENTS.items():
        complete_id = info["complete"]
        complete_sprite = f"ava{complete_id:04d}.def".encode()
        has_complete = data_lower.count(complete_sprite)
        found_components = []
        for comp_id, comp_name in info["components"].items():
            sprite = f"ava{comp_id:04d}.def".encode()
            if data_lower.count(sprite) > 0:
                found_components.append(f"{comp_id}={comp_name}")
        complete_mark = "✓完整神器" if has_complete else " "
        comp_count = len(found_components)
        total_comp = len(info["components"])
        print(f"  {name}: {complete_mark}, 组件 {comp_count}/{total_comp}")
        for c in found_components:
            print(f"    + {c}")
        if has_complete or comp_count >= 1:
            print(f"    [推断] RMG 已为该神器准备好路径")

    print("\n=== 地图中出现的全部 artifact sprite ===")
    ava_pattern = re.compile(rb"ava\d{4}\.def", re.IGNORECASE)
    artifacts_found = sorted(set(
        m.group(0).decode("ascii").lower() for m in ava_pattern.finditer(data)
    ))
    for a in artifacts_found:
        print(f"  {a}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
