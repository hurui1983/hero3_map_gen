"""
order.py - AI 点菜式 RMG 模板生成器 CLI

用法:
  python order.py "我想要金龙、末日之刃、4 玩家、强敌"
  python order.py "海岛风、有大天使、容易一点、2 玩家"

环境:
  ANTHROPIC_API_KEY - Anthropic API key (Claude)
"""

from __future__ import annotations

import argparse
import sys

import catalog
import ai_translator
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


def _validate(translated: ai_translator.TranslatedOrder, log) -> o2r.ValidatedOrder:
    """严格白名单校验: 任一菜名未精确命中 catalog 即抛 StrictValidationError.

    校验通过的项会被收录; 任何被 LLM 标 unrecognized 的、或 catalog
    解析失败的, 都会汇总后抛错, 包含相似建议.
    """
    creatures: list[catalog.CatalogItem] = []
    artifacts: list[catalog.CatalogItem] = []
    unresolved: list[tuple[str, str, list[str]]] = []

    for raw_name in translated.creatures:
        item = catalog.resolve_creature(raw_name)
        if item:
            creatures.append(item)
            log(f"  [OK] 生物: {item.name_zh} (ID={item.rmg_id}) "
                f"[NOTE: HotA RMG 不支持指定具体生物, 通过难度间接体现]")
        else:
            suggestions = catalog.suggest_similar(raw_name)
            unresolved.append(("生物", raw_name, suggestions))
            log(f"  [FAIL] 生物 {raw_name!r} 不在词典中")

    for raw_name in translated.artifacts:
        item = catalog.resolve_artifact(raw_name)
        if item:
            artifacts.append(item)
            log(f"  [OK] 神器: {item.name_zh} (ID={item.rmg_id})")
        else:
            suggestions = catalog.suggest_similar(raw_name)
            unresolved.append(("神器", raw_name, suggestions))
            log(f"  [FAIL] 神器 {raw_name!r} 不在词典中")

    for raw_name in translated.specials:
        obj = catalog.resolve_special(raw_name)
        if obj:
            log(f"  [INFO] 特殊对象: {obj.name_zh} - {obj.note}")
        else:
            suggestions = catalog.suggest_similar(raw_name)
            unresolved.append(("特殊对象", raw_name, suggestions))
            log(f"  [FAIL] 特殊对象 {raw_name!r} 不在词典中")

    # LLM 自己回报的"我没识别"
    for raw_name in translated.unrecognized:
        suggestions = catalog.suggest_similar(raw_name)
        unresolved.append(("LLM未识别", raw_name, suggestions))
        log(f"  [FAIL] LLM 未识别 {raw_name!r}")

    difficulty_key: str | None = None
    if translated.difficulty:
        difficulty_key = catalog.resolve_difficulty(translated.difficulty)
        if difficulty_key:
            log(f"  [OK] 难度: {difficulty_key} -> RMG {catalog.difficulty_to_rmg_value(difficulty_key)}")
        else:
            unresolved.append(("难度", translated.difficulty, ["easy", "normal", "hard", "expert", "impossible"]))
            log(f"  [FAIL] 难度 {translated.difficulty!r} 无效")

    players: int | None = None
    if translated.players is not None:
        if 2 <= translated.players <= 8:
            players = translated.players
            log(f"  [OK] 玩家数: {players}")
        else:
            unresolved.append(("玩家数", str(translated.players), ["2", "3", "4", "5", "6", "7", "8"]))
            log(f"  [FAIL] 玩家数 {translated.players} 超出 2~8 范围")

    map_size: str | None = None
    if translated.map_size:
        if translated.map_size.upper() in {"S", "M", "L", "XL"}:
            map_size = translated.map_size.upper()
            log(f"  [OK] 地图大小: {map_size}")
        else:
            unresolved.append(("地图大小", translated.map_size, ["S", "M", "L", "XL"]))
            log(f"  [FAIL] 地图大小 {translated.map_size!r} 无效")

    if unresolved:
        raise StrictValidationError(unresolved)

    description = translated.description

    return o2r.ValidatedOrder(
        creatures=creatures,
        artifacts=artifacts,
        difficulty=difficulty_key,
        players=players,
        map_size=map_size,
        description=description,
    )


def run(user_text: str, *, log=print) -> int:
    """主流程: 翻译 -> 校验 -> 生成 .h3t.

    Returns:
        0 表示成功, 非 0 表示出错
    """
    log(f"[输入] {user_text!r}")

    log("\n[1/3] AI 翻译中...")
    try:
        translated = ai_translator.translate(user_text)
    except (ImportError, RuntimeError, ValueError) as e:
        log(f"  [ERROR] AI 翻译失败: {e}")
        return 2
    except Exception as e:  # 兜底: anthropic SDK 的网络/权限/限流错误
        log(f"  [ERROR] AI 翻译异常 ({type(e).__name__}): {e}")
        return 2

    log(f"  AI 原始输出: creatures={translated.creatures}, artifacts={translated.artifacts}, "
        f"specials={translated.specials}, unrecognized={translated.unrecognized}, "
        f"difficulty={translated.difficulty}, players={translated.players}, "
        f"map_size={translated.map_size}")

    log("\n[2/3] 严格白名单校验:")
    try:
        validated = _validate(translated, log)
    except StrictValidationError as e:
        log("\n[ERROR] 以下输入未能精确识别, 已中止生成:")
        for category, raw, suggestions in e.unresolved:
            sug_text = ", ".join(suggestions) if suggestions else "(无)"
            log(f"  - [{category}] {raw!r}")
            log(f"      类似项: {sug_text}")
        log("\n请在 catalog.py 中补充这些条目, 或修改输入用确切的菜单名后重试.")
        log(f"当前 catalog 包含: {len(catalog.CREATURES)} 生物 + "
            f"{len(catalog.ARTIFACTS)} 神器 + {len(catalog.SPECIAL_OBJECTS)} 特殊对象, "
            f"完整列表见 catalog.py.")
        return 3

    if not (validated.creatures or validated.artifacts or validated.difficulty
            or validated.players or validated.map_size):
        log("\n  [WARN] 没有任何字段被识别, 将生成默认模板")

    log("\n[3/3] 写入模板:")
    out_path = tw.generate_from_order(validated)
    log(f"  生成: {out_path}")
    log(f"  模板显示名: {tw.derive_name_from_order(validated)!r}")

    log("\n[完成] 启动游戏 -> 单人 -> 随机地图 -> 在模板列表里找以 'AI ' 开头的项")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AI 点菜式 HoMM3/HotA 随机地图模板生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python order.py "我想要金龙、末日之刃、4 玩家、强敌"
  python order.py "中等地图, 大天使, 简单点"
  python order.py --list
  python order.py --clean
        """,
    )
    parser.add_argument("text", nargs="?", help="点菜的自然语言文本")
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

    if not args.text:
        parser.print_help()
        return 1

    return run(args.text)


if __name__ == "__main__":
    sys.exit(main())
