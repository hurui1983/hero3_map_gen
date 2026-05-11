"""ai_translator.py 的单元测试.

只测纯函数 (_parse_order_dict, _strip_json_markdown).
真正的 Claude API 调用放在 e2e 验证中, 不在此测试.
"""

import unittest

from ai_translator import (
    TranslatedOrder,
    _parse_order_dict,
    _strip_json_markdown,
)


class StripJsonMarkdownTests(unittest.TestCase):
    def test_no_markdown_unchanged(self):
        self.assertEqual(_strip_json_markdown('{"a": 1}'), '{"a": 1}')

    def test_strip_plain_fence(self):
        self.assertEqual(_strip_json_markdown('```\n{"a": 1}\n```'), '{"a": 1}')

    def test_strip_json_fence(self):
        self.assertEqual(_strip_json_markdown('```json\n{"a": 1}\n```'), '{"a": 1}')

    def test_strip_with_trailing_whitespace(self):
        self.assertEqual(_strip_json_markdown('  ```json\n{"a": 1}\n```  '), '{"a": 1}')


class ParseOrderDictTests(unittest.TestCase):
    def test_full_order(self):
        order = _parse_order_dict({
            "creatures": ["金龙", "黑龙"],
            "artifacts": ["末日之刃"],
            "specials": ["圣杯"],
            "unrecognized": ["龙骨胫甲"],
            "difficulty": "hard",
            "players": 4,
            "map_size": "M",
            "description": "测试地图",
        })
        self.assertEqual(order.creatures, ["金龙", "黑龙"])
        self.assertEqual(order.artifacts, ["末日之刃"])
        self.assertEqual(order.specials, ["圣杯"])
        self.assertEqual(order.unrecognized, ["龙骨胫甲"])
        self.assertEqual(order.difficulty, "hard")
        self.assertEqual(order.players, 4)
        self.assertEqual(order.map_size, "M")
        self.assertEqual(order.description, "测试地图")

    def test_empty_order(self):
        order = _parse_order_dict({})
        self.assertEqual(order.creatures, [])
        self.assertEqual(order.artifacts, [])
        self.assertEqual(order.specials, [])
        self.assertEqual(order.unrecognized, [])
        self.assertIsNone(order.difficulty)
        self.assertIsNone(order.players)
        self.assertIsNone(order.map_size)
        self.assertIsNone(order.description)

    def test_null_fields_become_none(self):
        order = _parse_order_dict({
            "creatures": None,
            "artifacts": None,
            "specials": None,
            "unrecognized": None,
            "difficulty": None,
            "players": None,
            "map_size": None,
            "description": None,
        })
        self.assertEqual(order.creatures, [])
        self.assertEqual(order.specials, [])
        self.assertEqual(order.unrecognized, [])
        self.assertIsNone(order.difficulty)

    def test_empty_strings_in_list_filtered_out(self):
        order = _parse_order_dict({"creatures": ["金龙", "", None, "黑龙"]})
        self.assertEqual(order.creatures, ["金龙", "黑龙"])

    def test_int_as_string_coerced(self):
        order = _parse_order_dict({"players": "4"})
        self.assertEqual(order.players, 4)

    def test_invalid_int_raises(self):
        with self.assertRaises(ValueError):
            _parse_order_dict({"players": "many"})

    def test_non_list_creatures_raises(self):
        with self.assertRaises(ValueError):
            _parse_order_dict({"creatures": "金龙"})

    def test_top_level_not_dict_raises(self):
        with self.assertRaises(ValueError):
            _parse_order_dict([])  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
