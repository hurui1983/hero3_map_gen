"""order_to_rmg.py 的单元测试.

覆盖:
  - 行类型判别 (Zone vs Connection-only)
  - 各种 Order 字段生成正确数量和位置的 CellAction
  - apply_actions 的就地修改 + 越界保护
"""

import unittest

import catalog
import order_to_rmg as o2r


def make_empty_row(n_cols: int = 200) -> list[str]:
    return [""] * n_cols


def make_zone_row(zone_id: str, n_cols: int = 200) -> list[str]:
    row = make_empty_row(n_cols)
    row[o2r.COL_ZONE_ID] = zone_id
    row[o2r.COL_ZONE_STRENGTH] = "avg"
    return row


def make_connection_only_row(n_cols: int = 200) -> list[str]:
    """Id 列为空 + 末尾 Connection 区有数据."""
    row = make_empty_row(n_cols)
    row[125] = "1"  # Zone 1 列, 标志这是个连接行
    return row


def make_table(zone_count: int, conn_only_count: int = 0) -> list[list[str]]:
    """造一张假表: 3 行表头 + N 个 Zone 行 + M 个纯 Connection 行."""
    table: list[list[str]] = [make_empty_row() for _ in range(3)]
    for i in range(zone_count):
        table.append(make_zone_row(str(i + 1)))
    for _ in range(conn_only_count):
        table.append(make_connection_only_row())
    return table


class IsZoneRowTests(unittest.TestCase):
    def test_row_with_id_is_zone(self):
        row = make_zone_row("1")
        self.assertTrue(o2r.is_zone_row(row))

    def test_row_without_id_is_not_zone(self):
        row = make_empty_row()
        self.assertFalse(o2r.is_zone_row(row))

    def test_connection_only_row_is_not_zone(self):
        row = make_connection_only_row()
        self.assertFalse(o2r.is_zone_row(row))

    def test_too_short_row_is_not_zone(self):
        row = ["only", "a", "few"]
        self.assertFalse(o2r.is_zone_row(row))


class BuildActionsDifficultyTests(unittest.TestCase):
    def test_difficulty_strong_modifies_all_zone_rows(self):
        order = o2r.ValidatedOrder(
            creatures=[], artifacts=[], difficulty="hard",
            players=None, map_size=None, description=None,
        )
        table = make_table(zone_count=3, conn_only_count=2)
        actions = o2r.build_actions(order, table)

        strength_actions = [a for a in actions if a.col == o2r.COL_ZONE_STRENGTH]
        self.assertEqual(len(strength_actions), 3, "应只改 3 个 Zone 行, 不动 2 个 Connection 行")
        for a in strength_actions:
            self.assertEqual(a.value, "strong")

    def test_difficulty_easy_maps_to_weak(self):
        order = o2r.ValidatedOrder(
            creatures=[], artifacts=[], difficulty="easy",
            players=None, map_size=None, description=None,
        )
        table = make_table(zone_count=2)
        actions = o2r.build_actions(order, table)
        self.assertEqual(actions[0].value, "weak")

    def test_difficulty_normal_maps_to_avg(self):
        order = o2r.ValidatedOrder(
            creatures=[], artifacts=[], difficulty="normal",
            players=None, map_size=None, description=None,
        )
        table = make_table(zone_count=1)
        actions = o2r.build_actions(order, table)
        self.assertEqual(actions[0].value, "avg")

    def test_no_difficulty_no_action(self):
        order = o2r.ValidatedOrder(
            creatures=[], artifacts=[], difficulty=None,
            players=None, map_size=None, description=None,
        )
        table = make_table(zone_count=3)
        actions = o2r.build_actions(order, table)
        # 没指定任何字段, 应该 0 个 action
        self.assertEqual(actions, [])


class BuildActionsNameAndDescriptionTests(unittest.TestCase):
    def test_name_writes_pack_and_map_name(self):
        order = o2r.ValidatedOrder(
            creatures=[], artifacts=[], difficulty=None,
            players=None, map_size=None, description=None, name="测试名",
        )
        table = make_table(zone_count=1)
        actions = o2r.build_actions(order, table)
        cols = {a.col for a in actions}
        self.assertIn(o2r.COL_PACK_NAME, cols)
        self.assertIn(o2r.COL_MAP_NAME, cols)
        # 都应该写在 first_data_row (即 row=3)
        for a in actions:
            self.assertEqual(a.row, 3)
            self.assertEqual(a.value, "测试名")

    def test_description_writes_pack_description(self):
        order = o2r.ValidatedOrder(
            creatures=[], artifacts=[], difficulty=None,
            players=None, map_size=None, description="一个测试图", name=None,
        )
        table = make_table(zone_count=1)
        actions = o2r.build_actions(order, table)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].col, o2r.COL_PACK_DESCRIPTION)
        self.assertEqual(actions[0].value, "一个测试图")


class BuildActionsArtifactsTests(unittest.TestCase):
    def _art(self, key: str) -> catalog.CatalogItem:
        item = catalog.resolve_artifact(key)
        assert item is not None, f"测试 fixture 损坏: catalog 没有 {key!r}"
        return item

    def test_single_artifact_writes_plus_id(self):
        order = o2r.ValidatedOrder(
            creatures=[], artifacts=[self._art("末日之刃")], difficulty=None,
            players=None, map_size=None, description=None,
        )
        table = make_table(zone_count=1)
        actions = o2r.build_actions(order, table)
        art_actions = [a for a in actions if a.col == o2r.COL_MAP_ARTIFACTS]
        self.assertEqual(len(art_actions), 1)
        self.assertEqual(art_actions[0].value, "+128")  # 末日之刃 RMG ID

    def test_multiple_artifacts_space_joined(self):
        order = o2r.ValidatedOrder(
            creatures=[], artifacts=[self._art("末日之刃"), self._art("天使联盟")],
            difficulty=None, players=None, map_size=None, description=None,
        )
        table = make_table(zone_count=1)
        actions = o2r.build_actions(order, table)
        art_actions = [a for a in actions if a.col == o2r.COL_MAP_ARTIFACTS]
        self.assertEqual(len(art_actions), 1)
        self.assertEqual(art_actions[0].value, "+128 +129")

    def test_artifacts_preserves_existing_value(self):
        # 模板原本 col 18 已有内容时, 应追加而不是覆盖 (例如 -72)
        order = o2r.ValidatedOrder(
            creatures=[], artifacts=[self._art("末日之刃")], difficulty=None,
            players=None, map_size=None, description=None,
        )
        table = make_table(zone_count=1)
        table[3][o2r.COL_MAP_ARTIFACTS] = "-72"
        actions = o2r.build_actions(order, table)
        art_actions = [a for a in actions if a.col == o2r.COL_MAP_ARTIFACTS]
        self.assertEqual(art_actions[0].value, "-72 +128")

    def test_no_artifacts_no_action(self):
        order = o2r.ValidatedOrder(
            creatures=[], artifacts=[], difficulty=None,
            players=None, map_size=None, description=None,
        )
        table = make_table(zone_count=1)
        actions = o2r.build_actions(order, table)
        art_actions = [a for a in actions if a.col == o2r.COL_MAP_ARTIFACTS]
        self.assertEqual(art_actions, [])


class BuildActionsMapSizeTests(unittest.TestCase):
    def test_map_size_M(self):
        order = o2r.ValidatedOrder(
            creatures=[], artifacts=[], difficulty=None,
            players=None, map_size="M", description=None,
        )
        table = make_table(zone_count=1)
        actions = o2r.build_actions(order, table)
        size_actions = [a for a in actions if a.col in (o2r.COL_MAP_MIN_SIZE, o2r.COL_MAP_MAX_SIZE)]
        self.assertEqual(len(size_actions), 2)
        for a in size_actions:
            self.assertEqual(a.value, "4")  # M = bit 2 = 4

    def test_map_size_XL(self):
        order = o2r.ValidatedOrder(
            creatures=[], artifacts=[], difficulty=None,
            players=None, map_size="XL", description=None,
        )
        table = make_table(zone_count=1)
        actions = o2r.build_actions(order, table)
        size_actions = [a for a in actions if a.col in (o2r.COL_MAP_MIN_SIZE, o2r.COL_MAP_MAX_SIZE)]
        for a in size_actions:
            self.assertEqual(a.value, "16")  # XL = bit 4 = 16

    def test_players_writes_zone_total_min_max(self):
        order = o2r.ValidatedOrder(
            creatures=[], artifacts=[], difficulty=None,
            players=2, map_size=None, description=None,
        )
        table = make_table(zone_count=2)
        actions = o2r.build_actions(order, table)
        # 两个 Zone 行 x 4 actions (min/max total + min/max human) = 8 个
        # Connection 段在测试 fixture 里全空, 所以不会同步
        player_actions = [a for a in actions
                          if a.col in (o2r.COL_ZONE_MIN_TOTAL, o2r.COL_ZONE_MAX_TOTAL,
                                       o2r.COL_ZONE_MIN_HUMAN, o2r.COL_ZONE_MAX_HUMAN)]
        self.assertEqual(len(player_actions), 8)
        # 总玩家数应被设成 "2"
        for a in player_actions:
            if a.col in (o2r.COL_ZONE_MIN_TOTAL, o2r.COL_ZONE_MAX_TOTAL, o2r.COL_ZONE_MAX_HUMAN):
                self.assertEqual(a.value, "2")
            elif a.col == o2r.COL_ZONE_MIN_HUMAN:
                self.assertEqual(a.value, "1")

    def test_players_skips_connection_section_when_empty(self):
        # Zone 行的 connection 段原本全空时, 不应往那里写
        order = o2r.ValidatedOrder(
            creatures=[], artifacts=[], difficulty=None,
            players=4, map_size=None, description=None,
        )
        table = make_table(zone_count=1)
        actions = o2r.build_actions(order, table)
        conn_actions = [a for a in actions
                        if a.col in (o2r.COL_CONN_MIN_TOTAL, o2r.COL_CONN_MAX_TOTAL,
                                     o2r.COL_CONN_MIN_HUMAN, o2r.COL_CONN_MAX_HUMAN)]
        self.assertEqual(conn_actions, [])

    def test_players_syncs_connection_section_when_populated(self):
        # 模拟 Jebus Cross 那样 connection 段有数据的 Zone 行
        order = o2r.ValidatedOrder(
            creatures=[], artifacts=[], difficulty=None,
            players=3, map_size=None, description=None,
        )
        table = make_table(zone_count=1)
        # 给第一个 Zone 行的 connection 段填上原值, 模拟 Jebus Cross
        row = table[3]
        row[o2r.COL_CONN_MIN_HUMAN] = "1"
        row[o2r.COL_CONN_MAX_HUMAN] = "4"
        row[o2r.COL_CONN_MIN_TOTAL] = "2"
        row[o2r.COL_CONN_MAX_TOTAL] = "4"
        actions = o2r.build_actions(order, table)
        conn_actions = [a for a in actions
                        if a.col in (o2r.COL_CONN_MIN_TOTAL, o2r.COL_CONN_MAX_TOTAL,
                                     o2r.COL_CONN_MIN_HUMAN, o2r.COL_CONN_MAX_HUMAN)]
        self.assertEqual(len(conn_actions), 4)

    def test_invalid_map_size_silently_ignored(self):
        # 计划没要求严格校验 map_size, 给个奇怪值不应崩
        order = o2r.ValidatedOrder(
            creatures=[], artifacts=[], difficulty=None,
            players=None, map_size="HUGE", description=None,
        )
        table = make_table(zone_count=1)
        actions = o2r.build_actions(order, table)
        size_actions = [a for a in actions if a.col in (o2r.COL_MAP_MIN_SIZE, o2r.COL_MAP_MAX_SIZE)]
        self.assertEqual(len(size_actions), 0)


class ApplyActionsTests(unittest.TestCase):
    def test_apply_modifies_in_place(self):
        table = make_table(zone_count=2)
        actions = [
            o2r.CellAction(3, o2r.COL_ZONE_STRENGTH, "strong", "test"),
            o2r.CellAction(4, o2r.COL_ZONE_STRENGTH, "weak", "test"),
        ]
        o2r.apply_actions(table, actions)
        self.assertEqual(table[3][o2r.COL_ZONE_STRENGTH], "strong")
        self.assertEqual(table[4][o2r.COL_ZONE_STRENGTH], "weak")

    def test_row_out_of_range_raises(self):
        table = make_table(zone_count=1)
        actions = [o2r.CellAction(99, 0, "x", "bad")]
        with self.assertRaises(IndexError):
            o2r.apply_actions(table, actions)

    def test_col_out_of_range_raises(self):
        table = make_table(zone_count=1)
        actions = [o2r.CellAction(3, 9999, "x", "bad")]
        with self.assertRaises(IndexError):
            o2r.apply_actions(table, actions)


class FullOrderIntegrationTests(unittest.TestCase):
    def test_full_order_generates_all_expected_actions(self):
        gold_dragon = catalog.resolve_creature("金龙")
        ab_blade = catalog.resolve_artifact("末日之刃")
        self.assertIsNotNone(gold_dragon)
        self.assertIsNotNone(ab_blade)

        order = o2r.ValidatedOrder(
            creatures=[gold_dragon],
            artifacts=[ab_blade],
            difficulty="hard",
            players=4,
            map_size="M",
            description="完整测试",
            name="AI 完整测试",
        )
        table = make_table(zone_count=4, conn_only_count=2)
        actions = o2r.build_actions(order, table)

        # 应至少包含: name(2) + description(1) + size(2) + strength(4) = 9
        self.assertGreaterEqual(len(actions), 9)

        # 全部应用不报错
        o2r.apply_actions(table, actions)
        self.assertEqual(table[3][o2r.COL_PACK_NAME], "AI 完整测试")
        self.assertEqual(table[3][o2r.COL_MAP_NAME], "AI 完整测试")
        self.assertEqual(table[3][o2r.COL_PACK_DESCRIPTION], "完整测试")
        self.assertEqual(table[3][o2r.COL_MAP_MIN_SIZE], "4")  # M = bit 2
        # 4 个 Zone 行的 strength 应该都是 strong
        for r in range(3, 7):
            self.assertEqual(table[r][o2r.COL_ZONE_STRENGTH], "strong")
        # 2 个 Connection 行的 strength 不应被改 (保持空)
        for r in range(7, 9):
            self.assertEqual(table[r][o2r.COL_ZONE_STRENGTH], "")


if __name__ == "__main__":
    unittest.main()
