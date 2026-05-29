"""完整对象注入 CLI: 向 HotA RMG 生成的 .h3m 精确注入指定生物 + 神器.

与 RMG 模板 (order.py) 的区别: 模板只能"调守军强度", 不保证具体生物/神器出现;
本工具直接在地图字节里追加对象, 100% 保证指定的生物和神器精确落在地图上.

用法:
  python3 inject_cli.py \
      --add-creature 圣龙:1 --add-creature 水晶龙:1 \
      --add-creature 仙龙:1 --add-creature 锈龙:1 \
      --add-artifact 末日之刃 --add-artifact 天使联盟 \
      --name 终极对战图

  python3 inject_cli.py --add-creature 金龙:5 --src "<某张.h3m>"

参数:
  --add-creature 名:数量   生物中文名:数量 (数量可省, 默认 1). 可重复.
  --add-artifact 名        神器中文名. 可重复.
  --src PATH               源 .h3m (默认: random_maps/ 里最新一张)
  --name NAME              输出文件名 (不含扩展名; 默认自动生成)
  --out-dir PATH           输出目录 (默认: 游戏 Maps/ 目录, 即单人场景列表)
  --seed N                 选址随机种子 (换种子可重新分散坐标)
"""
from __future__ import annotations

import argparse
import gzip
import sys
from pathlib import Path

import catalog
from h3m import inject, placement, reader, sprites

GAME = Path("/Applications/英雄无敌3：二合一.app/Contents/drive_c/game")
RANDOM_MAPS = GAME / "random_maps"
MAPS = GAME / "Maps"


def latest_random_map() -> Path:
    files = [p for p in RANDOM_MAPS.glob("*.h3m") if p.stat().st_size > 5000]
    if not files:
        sys.exit(f"[错误] {RANDOM_MAPS} 里没有可用 .h3m, 先在游戏里跑一次 RMG.")
    return max(files, key=lambda p: p.stat().st_mtime)


def parse_creature_arg(arg: str) -> tuple[str, int]:
    """'圣龙:3' -> ('圣龙', 3); '圣龙' -> ('圣龙', 1)."""
    if ":" in arg:
        name, _, cnt = arg.rpartition(":")
        name = name.strip()
        try:
            count = int(cnt)
        except ValueError:
            sys.exit(f"[错误] 生物数量无法解析: {arg!r} (应为 名:数量)")
        if count < 1:
            sys.exit(f"[错误] 生物数量必须 >=1: {arg!r}")
        return name, count
    return arg.strip(), 1


def main() -> int:
    ap = argparse.ArgumentParser(
        description="向 HotA .h3m 精确注入生物 + 神器 (100% 保证出现)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--add-creature", action="append", default=[], metavar="名:数量",
                    help="生物中文名:数量 (可重复)")
    ap.add_argument("--add-artifact", action="append", default=[], metavar="名",
                    help="神器中文名 (可重复)")
    ap.add_argument("--src", default=None, help="源 .h3m (默认最新 RMG)")
    ap.add_argument("--name", default=None, help="输出文件名 (不含扩展名)")
    ap.add_argument("--out-dir", default=str(MAPS), help="输出目录")
    ap.add_argument("--seed", type=int, default=None, help="选址随机种子")
    args = ap.parse_args()

    if not args.add_creature and not args.add_artifact:
        ap.print_help()
        return 1

    # --- 1. 解析生物 / 神器 (严格白名单: 任一名字不在 catalog 即中止) ---
    creatures: list[tuple[catalog.CatalogItem, int, str]] = []  # (item, count, sprite)
    artifacts: list[catalog.CatalogItem] = []
    errors: list[str] = []

    for raw in args.add_creature:
        name, count = parse_creature_arg(raw)
        item = catalog.resolve_creature(name)
        if not item:
            sug = ", ".join(catalog.suggest_similar(name)) or "(无相似项)"
            errors.append(f"生物 {name!r} 不在词典; 类似: {sug}")
            continue
        sprite = sprites.creature_sprite(item.rmg_id)
        if not sprite:
            errors.append(f"生物 {item.name_zh} (ID={item.rmg_id}) 缺少 sprite 映射, "
                          f"无法注入; 请在 h3m/sprites.py 补充")
            continue
        creatures.append((item, count, sprite))

    for raw in args.add_artifact:
        item = catalog.resolve_artifact(raw.strip())
        if not item:
            sug = ", ".join(catalog.suggest_similar(raw.strip())) or "(无相似项)"
            errors.append(f"神器 {raw!r} 不在词典; 类似: {sug}")
            continue
        artifacts.append(item)

    if errors:
        print("[错误] 以下输入无法处理, 已中止:")
        for e in errors:
            print(f"  - {e}")
        return 3

    n_objects = len(creatures) + len(artifacts)

    # --- 2. 读源图 + 智能选址 ---
    src = Path(args.src) if args.src else latest_random_map()
    if not src.exists():
        sys.exit(f"[错误] 源文件不存在: {src}")
    print(f"[源图] {src.name}")
    m = reader.load(src)
    print(f"       尺寸 {m.width}x{m.width}, {'含地下' if m.levels == 2 else '仅地表'}, "
          f"已有对象 {len(m.object_data)} 个")

    coords = placement.find_placements(m, n_objects, seed=args.seed)
    print(f"[选址] 为 {n_objects} 个对象挑选了开阔分散坐标")

    # --- 3. 构造 attribute + instance (kind = oa_count + 序号) ---
    with gzip.open(src, "rb") as f:
        raw = f.read()
    _, oa_count = inject.find_oa_section(raw)

    attrs: list[tuple[inject.AttrSpec, bytes]] = []
    plan: list[str] = []
    ci = 0
    for item, count, sprite in creatures:
        x, y, z = coords[ci]
        kind = oa_count + ci
        spec = inject.make_monster_spec(item.rmg_id, sprite.encode("ascii"))
        inst = inject.build_monster_instance(x, y, z, kind, count=count)
        attrs.append((spec, inst))
        plan.append(f"  生物 {item.name_zh} x{count} (ID={item.rmg_id}, {sprite}) -> ({x},{y},{z})")
        ci += 1
    for item in artifacts:
        x, y, z = coords[ci]
        kind = oa_count + ci
        spec = inject.make_artifact_spec(item.rmg_id)
        inst = inject.build_artifact_instance(x, y, z, kind)
        attrs.append((spec, inst))
        plan.append(f"  神器 {item.name_zh} (ID={item.rmg_id}) -> ({x},{y},{z})")
        ci += 1

    print("[注入计划]")
    for line in plan:
        print(line)

    # --- 4. 写出 ---
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = (args.name or _auto_name(creatures, artifacts)).strip()
    if not fname.endswith(".h3m"):
        fname += ".h3m"
    out_path = out_dir / fname

    info = inject.inject_objects(src, out_path, attrs)
    print(f"[完成] 写出 {out_path}")
    print(f"       地图对象数 {info['od_count_before']} -> {info['od_count_before'] + len(attrs)} "
          f"(+{len(attrs)}), 压缩后 {info['dst_size_compressed']} bytes")

    # --- 5. 自检: 重新解析输出图, 确认新对象就位 + 地形完好 ---
    ok = _self_verify(out_path, m, creatures, artifacts, coords)
    if not ok:
        print("[自检] ✗ 失败 (见上). 输出图可能无法加载, 请勿使用.")
        return 4
    print("[自检] ✓ 通过: 新对象数量/坐标/类型正确, 地形未被破坏.")
    print(f"\n下一步: 启动游戏 -> 单人 -> 场景 -> 选 '{out_path.stem}'")
    return 0


def _auto_name(creatures, artifacts) -> str:
    parts = [it.name_zh for it, _, _ in creatures] + [it.name_zh for it in artifacts]
    return "inject_" + "_".join(parts)[:50]


def _self_verify(out_path, src_map, creatures, artifacts, coords) -> bool:
    """重解析输出图, 校验注入结果. 任一不符即返回 False."""
    try:
        m2 = reader.load(out_path)
    except Exception as e:
        print(f"[自检] 重新解析输出图失败: {e}")
        return False

    # 对象数应恰好 +N
    expected = len(src_map.object_data) + len(creatures) + len(artifacts)
    if len(m2.object_data) != expected:
        print(f"[自检] 对象数不符: 期望 {expected}, 实得 {len(m2.object_data)}")
        return False

    # 地形完好 (尺寸 + tile 数不变)
    if m2.width != src_map.width or len(m2.terrain) != len(src_map.terrain):
        print("[自检] 地形尺寸被破坏")
        return False

    # 逐个核对注入对象: 坐标 + 类型 + subtype
    import data.objects as od  # lib 已在 sys.path
    want = []
    ci = 0
    for item, count, _ in creatures:
        want.append((coords[ci], od.ID.Monster, item.rmg_id)); ci += 1
    for item in artifacts:
        want.append((coords[ci], od.ID.Artifact, item.rmg_id)); ci += 1

    placed = {(tuple(o["coords"]), int(o["type"]), int(o["subtype"])) for o in m2.object_data}
    for (x, y, z), typ, sub in want:
        if ((x, y, z), int(typ), sub) not in placed:
            print(f"[自检] 未找到注入对象 type={typ} subtype={sub} @ ({x},{y},{z})")
            return False
    return True


if __name__ == "__main__":
    sys.exit(main())
