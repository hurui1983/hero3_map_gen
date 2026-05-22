"""order.py 的单元测试.

覆盖 _validate 的严格模式行为:
  - 全部命中 -> 返回 ValidatedOrder
  - 任一未命中 -> 抛 StrictValidationError, 包含相似建议
"""

import unittest

import order


def _make(**kwargs) -> order.RawOrder:
    """构造 RawOrder, 字段缺省值合理."""
    defaults = {
        "creatures": [],
        "artifacts": [],
        "specials": [],
        "difficulty": None,
        "players": None,
        "map_size": None,
        "description": None,
        "name": None,
    }
    defaults.update(kwargs)
    return order.RawOrder(**defaults)


def _silent(*_args, **_kwargs):
    """log 占位, 测试时不打印."""


class StrictValidationTests(unittest.TestCase):
    def test_all_known_passes(self):
        raw = _make(
            creatures=["金龙"],
            artifacts=["末日之刃"],
            difficulty="hard",
            players=4,
            map_size="M",
        )
        validated = order._validate(raw, _silent)
        self.assertEqual(len(validated.creatures), 1)
        self.assertEqual(validated.creatures[0].key, "gold_dragon")
        self.assertEqual(len(validated.artifacts), 1)
        self.assertEqual(validated.difficulty, "hard")
        self.assertEqual(validated.players, 4)
        self.assertEqual(validated.map_size, "M")

    def test_unknown_creature_raises(self):
        raw = _make(creatures=["金色巨龙"])  # 不在词典
        with self.assertRaises(order.StrictValidationError) as ctx:
            order._validate(raw, _silent)
        self.assertEqual(len(ctx.exception.unresolved), 1)
        category, raw_text, suggestions = ctx.exception.unresolved[0]
        self.assertEqual(category, "生物")
        self.assertEqual(raw_text, "金色巨龙")
        # "金色巨龙" 与 "金龙" 共享 "金" "龙" 两字, 应被推荐
        self.assertIn("金龙", suggestions)

    def test_unknown_artifact_raises(self):
        raw = _make(artifacts=["不存在的神器"])
        with self.assertRaises(order.StrictValidationError) as ctx:
            order._validate(raw, _silent)
        self.assertEqual(ctx.exception.unresolved[0][0], "神器")

    def test_invalid_difficulty_raises(self):
        raw = _make(difficulty="超级地狱")
        with self.assertRaises(order.StrictValidationError) as ctx:
            order._validate(raw, _silent)
        self.assertEqual(ctx.exception.unresolved[0][0], "难度")

    def test_out_of_range_players_raises(self):
        raw = _make(players=10)
        with self.assertRaises(order.StrictValidationError) as ctx:
            order._validate(raw, _silent)
        self.assertEqual(ctx.exception.unresolved[0][0], "玩家数")

    def test_invalid_map_size_raises(self):
        raw = _make(map_size="HUGE")
        with self.assertRaises(order.StrictValidationError) as ctx:
            order._validate(raw, _silent)
        self.assertEqual(ctx.exception.unresolved[0][0], "地图大小")

    def test_multiple_failures_collected(self):
        # 一次性收集所有错, 而不是只报第一个
        raw = _make(
            creatures=["不存在的龙"],
            artifacts=["不存在的剑"],
            difficulty="超难",
        )
        with self.assertRaises(order.StrictValidationError) as ctx:
            order._validate(raw, _silent)
        self.assertEqual(len(ctx.exception.unresolved), 3)
        categories = [c for c, _, _ in ctx.exception.unresolved]
        self.assertIn("生物", categories)
        self.assertIn("神器", categories)
        self.assertIn("难度", categories)

    def test_empty_order_passes(self):
        # 全空也合法 (生成默认模板)
        raw = _make()
        validated = order._validate(raw, _silent)
        self.assertEqual(validated.creatures, [])
        self.assertEqual(validated.artifacts, [])

    def test_name_and_description_pass_through(self):
        raw = _make(
            artifacts=["末日之刃"],
            name="AI 测试",
            description="测试描述",
        )
        validated = order._validate(raw, _silent)
        self.assertEqual(validated.name, "AI 测试")
        self.assertEqual(validated.description, "测试描述")


class CsvParsingTests(unittest.TestCase):
    def test_csv_empty(self):
        self.assertEqual(order._csv_to_list(""), [])
        self.assertEqual(order._csv_to_list(None), [])

    def test_csv_single(self):
        self.assertEqual(order._csv_to_list("金龙"), ["金龙"])

    def test_csv_multiple_with_spaces(self):
        self.assertEqual(
            order._csv_to_list("末日之刃, 天使联盟 ,鬼王斗篷"),
            ["末日之刃", "天使联盟", "鬼王斗篷"],
        )

    def test_csv_drops_empty_segments(self):
        self.assertEqual(order._csv_to_list("a,,b,"), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
