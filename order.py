"""
order.py - 结构化 CLI HotA RMG 模板生成器

用法:
  python order.py --artifacts 末日之刃,天使联盟 --creatures 金龙 \
      --difficulty hard --players 4
  python order.py --list
  python order.py --clean

自然语言交互在 Claude Code 对话里完成: 让 Claude 把"我想要 X"拆成
具体的 catalog 条目, 然后调用这个 CLI 生成 .h3t.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

import catalog
import order_to_rmg as o2r
import template_writer as tw


class StrictValidationError(Exception):
    """有任何用户提到的名字未能精确命中 catalog 时抛出.

    与 ValueError/RuntimeError 不同, 这是用户输入问题, 不是程序 bug,
    main() 会用退出码 3 报告.
    """

    def __init__(self, unresolved: list[tuple[str, str, list[str]]]):
        # 每项: (类别, 原话, 相似建议列表)
        self.unresolved = unresolved
        super().__init__(f"{len(unresolved)} 个输入项未能精确识别")


@dataclass(frozen=True)
class RawOrder:
    """CLI 解析或测试构造后的结构化输入. 尚未经过 catalog 校验."""
    creatures: list[str]
    artifacts: list[str]
    specials: list[str]
    difficulty: str | None
    players: int | None
    map_size: str | None
    description: str | None
    name: str | None


def _validate(raw: RawOrder, log) -> o2r.ValidatedOrder:
    """严格白名单校验: 任一菜名未精确命中 catalog 即抛 StrictValidationError."""
    creatures: list[catalog.CatalogItem] = []
    artifacts: list[catalog.CatalogItem] = []
    unresolved: list[tuple[str, str, list[str]]] = []

    for raw_name in raw.creatures:
        item = catalog.resolve_creature(raw_name)
        if item:
            creatures.append(item)
            log(f"  [OK] 生物: {item.name_zh} (ID={item.rmg_id}) "
                f"[NOTE: HotA RMG 没有'指定具体生物必出'字段, 模板只能调'野外守军强度', "
                f"不保证地图上出现这只龙; 要强保证请用地图编辑器手放]")
        else:
            suggestions = catalog.suggest_similar(raw_name)
            unresolved.append(("生物", raw_name, suggestions))
            log(f"  [FAIL] 生物 {raw_name!r} 不在词典中")

    for raw_name in raw.artifacts:
        item = catalog.resolve_artifact(raw_name)
        if item:
            artifacts.append(item)
            log(f"  [OK] 神器: {item.name_zh} (ID={item.rmg_id})")
        else:
            suggestions = catalog.suggest_similar(raw_name)
            unresolved.append(("神器", raw_name, suggestions))
            log(f"  [FAIL] 神器 {raw_name!r} 不在词典中")

    for raw_name in raw.specials:
        obj = catalog.resolve_special(raw_name)
        if obj:
            log(f"  [INFO] 特殊对象: {obj.name_zh} - {obj.note}")
        else:
            suggestions = catalog.suggest_similar(raw_name)
            unresolved.append(("特殊对象", raw_name, suggestions))
            log(f"  [FAIL] 特殊对象 {raw_name!r} 不在词典中")

    difficulty_key: str | None = None
    if raw.difficulty:
        difficulty_key = catalog.resolve_difficulty(raw.difficulty)
        if difficulty_key:
            log(f"  [OK] 难度: {difficulty_key} -> Zone.Strength="
                f"{catalog.difficulty_to_rmg_value(difficulty_key)} "
                f"[NOTE: 这是'野外守军强度', 不是游戏开局难度 (Easy/Hard/Impossible 等)]")
        else:
            unresolved.append(("难度", raw.difficulty, ["easy", "normal", "hard", "expert", "impossible"]))
            log(f"  [FAIL] 难度 {raw.difficulty!r} 无效")

    players: int | None = None
    if raw.players is not None:
        if 2 <= raw.players <= 8:
            players = raw.players
            log(f"  [OK] 玩家数: {players} "
                f"[NOTE: 骨架 (Jebus Cross) 支持 2-4 人, 此字段当前不写入, 可在游戏 UI 内选择]")
        else:
            unresolved.append(("玩家数", str(raw.players), ["2", "3", "4", "5", "6", "7", "8"]))
            log(f"  [FAIL] 玩家数 {raw.players} 超出 2~8 范围")

    map_size: str | None = None
    if raw.map_size:
        if raw.map_size.upper() in {"S", "M", "L", "XL"}:
            map_size = raw.map_size.upper()
            log(f"  [OK] 地图大小: {map_size} "
                f"[NOTE: 骨架 (Jebus Cross) 仅支持 L/XL, 此字段当前不写入, 可在游戏 UI 内选择]")
        else:
            unresolved.append(("地图大小", raw.map_size, ["S", "M", "L", "XL"]))
            log(f"  [FAIL] 地图大小 {raw.map_size!r} 无效")

    if unresolved:
        raise StrictValidationError(unresolved)

    return o2r.ValidatedOrder(
        creatures=creatures,
        artifacts=artifacts,
        difficulty=difficulty_key,
        players=players,
        map_size=map_size,
        description=raw.description,
        name=raw.name,
    )


def run(raw: RawOrder, *, log=print) -> int:
    """主流程: 校验 -> 生成 .h3t.

    Returns:
        0 表示成功, 非 0 表示出错
    """
    log(f"[输入] creatures={raw.creatures} artifacts={raw.artifacts} "
        f"specials={raw.specials} difficulty={raw.difficulty} players={raw.players} "
        f"map_size={raw.map_size} name={raw.name!r} description={raw.description!r}")

    log("\n[1/2] 严格白名单校验:")
    try:
        validated = _validate(raw, log)
    except StrictValidationError as e:
        log("\n[ERROR] 以下输入未能精确识别, 已中止生成:")
        for category, raw_text, suggestions in e.unresolved:
            sug_text = ", ".join(suggestions) if suggestions else "(无)"
            log(f"  - [{category}] {raw_text!r}")
            log(f"      类似项: {sug_text}")
        log("\n请在 catalog.py 中补充这些条目, 或修改参数用确切的菜单名后重试.")
        log(f"当前 catalog 包含: {len(catalog.CREATURES)} 生物 + "
            f"{len(catalog.ARTIFACTS)} 神器 + {len(catalog.SPECIAL_OBJECTS)} 特殊对象, "
            f"完整列表见 catalog.py.")
        return 3

    if not (validated.creatures or validated.artifacts or validated.difficulty
            or validated.players or validated.map_size):
        log("\n  [WARN] 没有任何字段被识别, 将生成默认模板")

    log("\n[2/2] 写入模板:")
    out_path = tw.generate_from_order(validated)
    log(f"  生成: {out_path}")
    log(f"  模板显示名: {tw.derive_name_from_order(validated)!r}")

    log("\n[完成] 启动游戏 -> 单人 -> 随机地图 -> 在模板列表里找以 'AI ' 开头的项")
    return 0


def _csv_to_list(s: str | None) -> list[str]:
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="结构化 CLI HotA RMG 模板生成器 (无 LLM 依赖)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python order.py --artifacts 末日之刃,天使联盟 --creatures 金龙 \\
      --difficulty hard --players 4
  python order.py --creatures 圣龙,水晶龙,仙龙,锈龙 \\
      --artifacts 末日之刃,天使联盟 --difficulty hard --players 4 \\
      --name "AI 四大龙 末日之刃 天使联盟"
  python order.py --list
  python order.py --clean

自然语言交互在 Claude Code 对话里完成: 让 Claude 把意图拆成
catalog 条目后再调本 CLI.
        """,
    )
    parser.add_argument("--creatures", default="",
                        help="逗号分隔的生物中文名, 例: 金龙,圣龙")
    parser.add_argument("--artifacts", default="",
                        help="逗号分隔的神器中文名, 例: 末日之刃,天使联盟")
    parser.add_argument("--specials", default="",
                        help="逗号分隔的特殊对象, 例: 圣杯")
    parser.add_argument("--difficulty", default=None,
                        help="难度: easy / normal / hard")
    parser.add_argument("--players", type=int, default=None,
                        help="玩家数 2~8")
    parser.add_argument("--map-size", dest="map_size", default=None,
                        help="地图大小 S / M / L / XL (当前不写入字段, 仅记录)")
    parser.add_argument("--name", default=None,
                        help="模板显示名 (默认自动衍生)")
    parser.add_argument("--description", default=None,
                        help="模板描述")
    parser.add_argument("--list", action="store_true", help="列出已生成的所有 AI 模板")
    parser.add_argument("--clean", action="store_true", help="删除所有 AI 模板")
    args = parser.parse_args()

    if args.list:
        templates = tw.list_ai_templates()
        if not templates:
            print("(无 AI 模板)")
        else:
            for p in templates:
                print(f"  {p.name}")
        return 0

    if args.clean:
        n = tw.clean_ai_templates()
        print(f"已删除 {n} 个 AI 模板")
        return 0

    raw = RawOrder(
        creatures=_csv_to_list(args.creatures),
        artifacts=_csv_to_list(args.artifacts),
        specials=_csv_to_list(args.specials),
        difficulty=args.difficulty,
        players=args.players,
        map_size=args.map_size,
        description=args.description,
        name=args.name,
    )

    if not (raw.creatures or raw.artifacts or raw.specials or raw.difficulty
            or raw.players or raw.map_size or raw.name or raw.description):
        parser.print_help()
        return 1

    return run(raw)


if __name__ == "__main__":
    sys.exit(main())
