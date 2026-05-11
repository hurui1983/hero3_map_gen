"""ai_translator.py 的单元测试.

只测纯函数 (_parse_order_dict, _strip_json_markdown).
真正的 Claude API 调用放在 e2e 验证中, 不在此测试.
"""

import unittest
import os
import tempfile
from pathlib import Path

from ai_translator import (
    TranslatedOrder,
    _load_project_env,
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


class LoadProjectEnvTests(unittest.TestCase):
    ENV_KEYS = {
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "OPENROUTER_API_KEY",
        "ANTHROPIC_BASE_URL",
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "EXISTING_KEY",
        "QUOTED_KEY",
    }

    def setUp(self):
        self._old_env = {key: os.environ.get(key) for key in self.ENV_KEYS}
        for key in self.ENV_KEYS:
            os.environ.pop(key, None)

    def tearDown(self):
        for key in self.ENV_KEYS:
            if self._old_env[key] is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = self._old_env[key]

    def test_loads_env_file_without_overriding_existing_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "\n".join([
                    "# comment",
                    "ANTHROPIC_AUTH_TOKEN=file-token",
                    "ANTHROPIC_BASE_URL=https://openrouter.ai/api/v1",
                    "EXISTING_KEY=file-value",
                ]),
                encoding="utf-8",
            )
            os.environ["EXISTING_KEY"] = "shell-value"

            _load_project_env(env_path)

            self.assertEqual(os.environ["ANTHROPIC_AUTH_TOKEN"], "file-token")
            self.assertEqual(os.environ["ANTHROPIC_BASE_URL"], "https://openrouter.ai/api/v1")
            self.assertEqual(os.environ["EXISTING_KEY"], "shell-value")

    def test_loads_export_prefix_and_quoted_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("export QUOTED_KEY='quoted value'\n", encoding="utf-8")

            _load_project_env(env_path)

            self.assertEqual(os.environ["QUOTED_KEY"], "quoted value")

    def test_malformed_line_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("ANTHROPIC_AUTH_TOKEN\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                _load_project_env(env_path)


if __name__ == "__main__":
    unittest.main()
