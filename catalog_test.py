"""catalog.py 的单元测试.

覆盖:
  - 通过 key / 中文标准名 / 中文别名 / 英文标准名 解析
  - 大小写、空白容错
  - 找不到项返回 None (零信任 LLM 输出的安全网)
  - 难度映射的双向转换
"""

import unittest

import catalog


class CatalogResolveCreatureTests(unittest.TestCase):
    def test_resolve_by_key(self):
        item = catalog.resolve_creature("gold_dragon")
        self.assertIsNotNone(item)
        self.assertEqual(item.rmg_id, 27)

    def test_resolve_by_chinese_standard_name(self):
        item = catalog.resolve_creature("金龙")
        self.assertIsNotNone(item)
        self.assertEqual(item.key, "gold_dragon")

    def test_resolve_by_english_standard_name(self):
        item = catalog.resolve_creature("Gold Dragon")
        self.assertIsNotNone(item)
        self.assertEqual(item.key, "gold_dragon")

    def test_shenglong_is_azure_dragon_not_gold(self):
        """权威核对: 圣龙 = Azure Dragon (ID 132), 不是 Gold Dragon (27).

        来源: heroes.thelazy.net Reference IDs + 萌娘百科兵种表.
        """
        item = catalog.resolve_creature("圣龙")
        self.assertIsNotNone(item)
        self.assertEqual(item.key, "azure_dragon")
        self.assertEqual(item.rmg_id, 132)
        self.assertEqual(item.name_en, "Azure Dragon")

    def test_resolve_case_insensitive(self):
        item = catalog.resolve_creature("ARCHANGEL")
        self.assertIsNotNone(item)
        self.assertEqual(item.rmg_id, 13)

    def test_resolve_with_whitespace(self):
        item = catalog.resolve_creature("  金龙  ")
        self.assertIsNotNone(item)

    def test_resolve_unknown_returns_none(self):
        self.assertIsNone(catalog.resolve_creature("不存在的生物"))
        self.assertIsNone(catalog.resolve_creature("xyzzy"))

    def test_resolve_empty_returns_none(self):
        self.assertIsNone(catalog.resolve_creature(""))


class CatalogResolveArtifactTests(unittest.TestCase):
    def test_resolve_armageddons_blade_zh(self):
        item = catalog.resolve_artifact("末日之刃")
        self.assertIsNotNone(item)
        self.assertEqual(item.key, "armageddons_blade")

    def test_resolve_armageddons_blade_alias(self):
        item = catalog.resolve_artifact("末日剑")
        self.assertIsNotNone(item)
        self.assertEqual(item.key, "armageddons_blade")

    def test_resolve_admirals_hat_alias(self):
        item = catalog.resolve_artifact("海军帽")
        self.assertIsNotNone(item)
        self.assertEqual(item.key, "admirals_hat")

    def test_resolve_unknown_artifact(self):
        self.assertIsNone(catalog.resolve_artifact("圣剑"))


class DifficultyTests(unittest.TestCase):
    def test_resolve_difficulty_zh(self):
        self.assertEqual(catalog.resolve_difficulty("简单"), "easy")
        self.assertEqual(catalog.resolve_difficulty("普通"), "normal")
        self.assertEqual(catalog.resolve_difficulty("困难"), "hard")
        self.assertEqual(catalog.resolve_difficulty("强敌"), "hard")

    def test_resolve_difficulty_en(self):
        self.assertEqual(catalog.resolve_difficulty("easy"), "easy")
        self.assertEqual(catalog.resolve_difficulty("hard"), "hard")
        self.assertEqual(catalog.resolve_difficulty("strong"), "hard")
        self.assertEqual(catalog.resolve_difficulty("weak"), "easy")

    def test_resolve_difficulty_unknown(self):
        self.assertIsNone(catalog.resolve_difficulty("超级困难"))
        self.assertIsNone(catalog.resolve_difficulty(""))

    def test_difficulty_to_rmg_value(self):
        self.assertEqual(catalog.difficulty_to_rmg_value("easy"), "weak")
        self.assertEqual(catalog.difficulty_to_rmg_value("normal"), "avg")
        self.assertEqual(catalog.difficulty_to_rmg_value("hard"), "strong")


class CatalogListingTests(unittest.TestCase):
    def test_all_creature_names_includes_aliases(self):
        names = catalog.all_creature_names_zh()
        self.assertIn("金龙", names)
        self.assertIn("圣龙", names)
        self.assertIn("大天使", names)

    def test_all_artifact_names_includes_aliases(self):
        names = catalog.all_artifact_names_zh()
        self.assertIn("末日之刃", names)
        self.assertIn("末日剑", names)


class AuthoritativeChineseNameTests(unittest.TestCase):
    """权威译名校对: 防止再次出现"圣龙=金龙"这类翻译错误.

    每个 case 都对应一个我们之前犯过的错或可能犯的错.
    数据来源: heroes.thelazy.net Reference IDs + 萌娘百科.
    """

    # ---- 龙系 (高发错误区) ----
    def test_gold_dragon_no_shenglong_alias(self):
        """金龙不能有"圣龙"这个别名 (圣龙是 Azure Dragon)."""
        item = catalog.resolve_creature("gold_dragon")
        self.assertNotIn("圣龙", item.aliases_zh)

    def test_azure_dragon_zh_is_shenglong(self):
        """Azure Dragon 标准中文名是"圣龙"."""
        item = catalog.resolve_creature("azure_dragon")
        self.assertEqual(item.name_zh, "圣龙")

    def test_ghost_dragon_zh_is_guilong(self):
        """Ghost Dragon 标准中文名是"鬼龙" (萌娘百科)."""
        item = catalog.resolve_creature("ghost_dragon")
        self.assertEqual(item.name_zh, "鬼龙")

    def test_red_dragon_alias_chilong(self):
        """红龙别名包含"赤龙" (萌娘百科常用)."""
        item = catalog.resolve_creature("赤龙")
        self.assertIsNotNone(item)
        self.assertEqual(item.key, "red_dragon")

    def test_faerie_dragon_zh_is_xianlong(self):
        """Faerie Dragon 标准中文名是"仙龙" (萌娘百科).

        玩家社区里"仙女龙"、"紫龙"也都指 Faerie Dragon (heroes.thelazy.net 验证).
        """
        item = catalog.resolve_creature("faerie_dragon")
        self.assertEqual(item.name_zh, "仙龙")
        # 所有民间叫法都应解析到同一个生物
        for alias in ["精灵龙", "仙女龙", "紫龙"]:
            resolved = catalog.resolve_creature(alias)
            self.assertIsNotNone(resolved, f"别名 {alias} 应能查到")
            self.assertEqual(resolved.key, "faerie_dragon",
                             f"别名 {alias} 应指向 faerie_dragon")

    def test_rust_dragon_alias_dulong(self):
        """Rust Dragon 萌娘百科用"毒龙"作为别名."""
        item = catalog.resolve_creature("毒龙")
        self.assertIsNotNone(item)
        self.assertEqual(item.key, "rust_dragon")

    # ---- 比蒙 ----
    def test_ancient_behemoth_zh_is_bimengjushou(self):
        """Ancient Behemoth 标准中文名是"比蒙巨兽", 不是"远古比蒙"."""
        item = catalog.resolve_creature("ancient_behemoth")
        self.assertEqual(item.name_zh, "比蒙巨兽")
        # 兼容性: 远古比蒙仍能查到
        self.assertIsNotNone(catalog.resolve_creature("远古比蒙"))

    # ---- 神器 ----
    def test_cloak_undead_king_zh_is_guiwangdoupeng(self):
        """Cloak of the Undead King 标准译名是"鬼王斗篷"."""
        item = catalog.resolve_artifact("cloak_of_the_undead_king")
        self.assertEqual(item.name_zh, "鬼王斗篷")
        # 兼容: 不死之王披风也能查
        self.assertIsNotNone(catalog.resolve_artifact("不死之王披风"))

    def test_armor_damned_zh_is_zuzhoukaijia(self):
        """Armor of the Damned 标准译名是"诅咒铠甲"."""
        item = catalog.resolve_artifact("armor_of_the_damned")
        self.assertEqual(item.name_zh, "诅咒铠甲")

    def test_wizards_well_zh_is_moliyuanquan(self):
        """Wizard's Well 标准译名是"魔力源泉"."""
        item = catalog.resolve_artifact("wizards_well")
        self.assertEqual(item.name_zh, "魔力源泉")
        # 兼容: 法师之井也能查
        self.assertIsNotNone(catalog.resolve_artifact("法师之井"))

    def test_admirals_hat_aliases(self):
        """海军上将之帽支持多种缩略别名."""
        for name in ["海军上将之帽", "海军帽", "海洋之帽", "海将军帽", "上将之帽"]:
            self.assertIsNotNone(catalog.resolve_artifact(name), f"{name} 应该能查到")


class SpecialObjectTests(unittest.TestCase):
    """特殊地图对象 (圣杯等) 解析."""

    def test_grail_resolve_by_zh(self):
        obj = catalog.resolve_special("圣杯")
        self.assertIsNotNone(obj)
        self.assertEqual(obj.key, "grail")

    def test_grail_resolve_by_en(self):
        obj = catalog.resolve_special("Grail")
        self.assertIsNotNone(obj)
        self.assertEqual(obj.key, "grail")

    def test_grail_resolve_unknown_returns_none(self):
        self.assertIsNone(catalog.resolve_special("末日之刃"))
        self.assertIsNone(catalog.resolve_special(""))

    def test_grail_has_note(self):
        """圣杯应有一段说明文字, 给 CLI 显示用."""
        obj = catalog.resolve_special("grail")
        self.assertTrue(obj.note, "圣杯应有 note 说明")
        self.assertIn("RMG", obj.note, "note 应说明 RMG 默认开启")

    def test_all_special_names_includes_grail(self):
        names = catalog.all_special_names_zh()
        self.assertIn("圣杯", names)


class IdSanityTests(unittest.TestCase):
    """关键 ID 必须与 heroes.thelazy.net Reference IDs 一致.

    发现任何错误就直接修, 不要让 LLM 拿着错的 ID 跑.
    """

    EXPECTED_CREATURE_IDS = {
        "angel": 12,
        "archangel": 13,
        "green_dragon": 26,
        "gold_dragon": 27,
        "titan": 41,
        "devil": 54,
        "arch_devil": 55,
        "lich": 64,
        "bone_dragon": 68,
        "ghost_dragon": 69,
        "red_dragon": 82,
        "black_dragon": 83,
        "behemoth": 96,
        "ancient_behemoth": 97,
        "hydra": 110,
        "chaos_hydra": 111,
        "phoenix": 131,
        "azure_dragon": 132,
        "crystal_dragon": 133,
        "faerie_dragon": 134,
        "rust_dragon": 135,
    }

    EXPECTED_ARTIFACT_IDS = {
        "armageddons_blade": 128,
        "angelic_alliance": 129,
        "cloak_of_the_undead_king": 130,
        "elixir_of_life": 131,
        "armor_of_the_damned": 132,
        "statue_of_legion": 133,
        "power_of_the_dragon_father": 134,
        "titans_thunder": 135,
        "admirals_hat": 136,
        "bow_of_the_sharpshooter": 137,
        "wizards_well": 138,
    }

    def test_creature_ids_match_reference(self):
        for key, expected_id in self.EXPECTED_CREATURE_IDS.items():
            with self.subTest(creature=key):
                self.assertIn(key, catalog.CREATURES)
                self.assertEqual(
                    catalog.CREATURES[key].rmg_id, expected_id,
                    f"{key} 的 ID 与 heroes.thelazy.net 不一致",
                )

    def test_artifact_ids_match_reference(self):
        for key, expected_id in self.EXPECTED_ARTIFACT_IDS.items():
            with self.subTest(artifact=key):
                self.assertIn(key, catalog.ARTIFACTS)
                self.assertEqual(
                    catalog.ARTIFACTS[key].rmg_id, expected_id,
                    f"{key} 的 ID 与 heroes.thelazy.net 不一致",
                )


class SuggestSimilarTests(unittest.TestCase):
    """suggest_similar() 给未识别名字找相似项."""

    def test_close_match_finds_canonical(self):
        # "金色巨龙" 不是别名, 但和 "金龙" 共享两个字
        suggestions = catalog.suggest_similar("金色巨龙")
        self.assertIn("金龙", suggestions)

    def test_returns_empty_for_totally_unrelated(self):
        # "披萨" 跟 catalog 里任何项都没共字
        self.assertEqual(catalog.suggest_similar("披萨"), [])

    def test_returns_empty_for_empty_input(self):
        self.assertEqual(catalog.suggest_similar(""), [])
        self.assertEqual(catalog.suggest_similar("   "), [])

    def test_top_k_limits_results(self):
        # "龙" 一字会和很多龙类生物共享, 限 top_k=2
        suggestions = catalog.suggest_similar("龙王", top_k=2)
        self.assertLessEqual(len(suggestions), 2)

    def test_no_duplicates_in_suggestions(self):
        # 即使一个标准名既被生物又被神器关联, 也不应重复出现
        suggestions = catalog.suggest_similar("金龙", top_k=10)
        self.assertEqual(len(suggestions), len(set(suggestions)))


if __name__ == "__main__":
    unittest.main()
