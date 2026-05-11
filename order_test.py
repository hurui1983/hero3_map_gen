"""order.py 的单元测试.

覆盖 _validate 的严格模式行为:
  - 全部命中 -> 返回 ValidatedOrder
  - 任一未命中 -> 抛 StrictValidationError, 包含相似建议
  - LLM 自报的 unrecognized 也算未命中

不测 run() 整体, 因为它会调 LLM (网络/付费). LLM 部分的回归用端到端验证手动跑.
"""

import unittest

import ai_translator
import order


def _make(**kwargs) -> ai_translator.TranslatedOrder:
    """构造 TranslatedOrder, 字段缺省值合理."""
    defaults = {
        "creatures": [],
        "artifacts": [],
        "specials": [],
        "unrecognized": [],
        "difficulty": None,
        "players": None,
        "map_size": None,
        "description": None,
    }
    defaults.update(kwargs)
    return ai_translator.TranslatedOrder(**defaults)


def _silent(*_args, **_kwargs):
    """log 占位, 测试时不打印."""


class StrictValidationTests(unittest.TestCase):
    def test_all_known_passes(self):
        translated = _make(
            creatures=["金龙"],
            artifacts=["末日之刃"],
            difficulty="hard",
            players=4,
            map_size="M",
        )
        validated = order._validate(translated, _silent)
        self.assertEqual(len(validated.creatures), 1)
        self.assertEqual(validated.creatures[0].key, "gold_dragon")
        self.assertEqual(len(validated.artifacts), 1)
        self.assertEqual(validated.difficulty, "hard")
        self.assertEqual(validated.players, 4)
        self.assertEqual(validated.map_size, "M")

    def test_unknown_creature_raises(self):
        translated = _make(creatures=["金色巨龙"])  # 不在词典
        with self.assertRaises(order.StrictValidationError) as ctx:
            order._validate(translated, _silent)
        self.assertEqual(len(ctx.exception.unresolved), 1)
        category, raw, suggestions = ctx.exception.unresolved[0]
        self.assertEqual(category, "生物")
        self.assertEqual(raw, "金色巨龙")
        # "金色巨龙" 与 "金龙" 共享 "金" "龙" 两字, 应被推荐
        self.assertIn("金龙", suggestions)

    def test_unknown_artifact_raises(self):
        translated = _make(artifacts=["不存在的神器"])
        with self.assertRaises(order.StrictValidationError) as ctx:
            order._validate(translated, _silent)
        self.assertEqual(ctx.exception.unresolved[0][0], "神器")

    def test_llm_unrecognized_raises(self):
        # 即使 creatures/artifacts 都通过, LLM 自报的 unrecognized 也要中止
        translated = _make(
            creatures=["金龙"],
            unrecognized=["龙骨胫甲"],
        )
        with self.assertRaises(order.StrictValidationError) as ctx:
            order._validate(translated, _silent)
        self.assertEqual(ctx.exception.unresolved[0][0], "LLM未识别")

    def test_invalid_difficulty_raises(self):
        translated = _make(difficulty="超级地狱")
        with self.assertRaises(order.StrictValidationError) as ctx:
            order._validate(translated, _silent)
        self.assertEqual(ctx.exception.unresolved[0][0], "难度")

    def test_out_of_range_players_raises(self):
        translated = _make(players=10)
        with self.assertRaises(order.StrictValidationError) as ctx:
            order._validate(translated, _silent)
        self.assertEqual(ctx.exception.unresolved[0][0], "玩家数")

    def test_invalid_map_size_raises(self):
        translated = _make(map_size="HUGE")
        with self.assertRaises(order.StrictValidationError) as ctx:
            order._validate(translated, _silent)
        self.assertEqual(ctx.exception.unresolved[0][0], "地图大小")

    def test_multiple_failures_collected(self):
        # 一次性收集所有错, 而不是只报第一个
        translated = _make(
            creatures=["不存在的龙"],
            artifacts=["不存在的剑"],
            unrecognized=["不存在的靴子"],
            difficulty="超难",
        )
        with self.assertRaises(order.StrictValidationError) as ctx:
            order._validate(translated, _silent)
        self.assertEqual(len(ctx.exception.unresolved), 4)
        categories = [c for c, _, _ in ctx.exception.unresolved]
        self.assertIn("生物", categories)
        self.assertIn("神器", categories)
        self.assertIn("LLM未识别", categories)
        self.assertIn("难度", categories)

    def test_empty_order_passes(self):
        # 全空也合法 (生成默认模板)
        translated = _make()
        validated = order._validate(translated, _silent)
        self.assertEqual(validated.creatures, [])
        self.assertEqual(validated.artifacts, [])


if __name__ == "__main__":
    unittest.main()
