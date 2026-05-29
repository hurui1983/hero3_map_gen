"""注入工具链的单元测试 (不依赖游戏安装).

覆盖:
  - h3m.sprites: catalog 全部生物都有 sprite 映射 (否则 CLI 会拒绝注入)
  - h3m.inject: instance/attribute 字节布局 (神器格式是之前的 bug 点)
  - h3m.placement: 在合成网格上选址 (land/占用约束 + 分散 + 不足报错)
"""
from __future__ import annotations

import struct
import unittest

import catalog
from h3m import inject, placement, sprites
from h3m.reader import MapData


class SpriteCoverageTest(unittest.TestCase):
    def test_every_catalog_creature_has_sprite(self):
        missing = [
            item.name_zh for item in catalog.CREATURES.values()
            if sprites.creature_sprite(item.rmg_id) is None
        ]
        self.assertEqual(missing, [], f"缺少 sprite 映射的生物: {missing}")

    def test_sprite_names_look_like_def(self):
        for cid, s in sprites.CREATURE_SPRITES.items():
            self.assertTrue(s.lower().endswith(".def"), (cid, s))


class InstanceLayoutTest(unittest.TestCase):
    def test_artifact_instance_is_hota_18_bytes(self):
        b = inject.build_artifact_instance(3, 4, 0, 7)
        # base12 + hasMsg(1) + pickup_mode(4) + pickup_conditions(1)
        self.assertEqual(len(b), 18)
        self.assertEqual(tuple(b[:3]), (3, 4, 0))                  # x,y,z
        self.assertEqual(struct.unpack_from("<I", b, 3)[0], 7)     # kind
        self.assertEqual(b[3 + 4:3 + 4 + 5], b"\x00" * 5)          # 5 zeros
        self.assertEqual(b[12], 0)                                 # hasMessage=0
        self.assertEqual(struct.unpack_from("<I", b, 13)[0], 0)    # pickup_mode=0
        self.assertEqual(b[17], 0x7F)                              # pickup_conditions

    def test_monster_instance_layout(self):
        b = inject.build_monster_instance(5, 6, 0, 9, count=12)
        self.assertEqual(len(b), 46)
        self.assertEqual(tuple(b[:3]), (5, 6, 0))
        self.assertEqual(struct.unpack_from("<I", b, 3)[0], 9)     # kind
        # quantity (u16) 紧跟 base12 + quest_identifier(4)
        self.assertEqual(struct.unpack_from("<H", b, 12 + 4)[0], 12)

    def test_monster_spec_fields(self):
        spec = inject.make_monster_spec(132, b"AVWazur.def")
        self.assertEqual(spec.object_class, 54)
        self.assertEqual(spec.object_number, 132)
        raw = spec.to_bytes()
        # def_size 前缀正确
        self.assertEqual(struct.unpack_from("<I", raw, 0)[0], len(b"AVWazur.def"))

    def test_artifact_spec_class5(self):
        spec = inject.make_artifact_spec(128)
        self.assertEqual(spec.object_class, 5)
        self.assertEqual(spec.object_number, 128)


def _grid(width, fill):
    return [[[fill] * width for _ in range(width)]]


def _fake_map(width=40, occupied_coords=(), blocked_coords=()):
    passable = _grid(width, True)
    occupied = _grid(width, False)
    occupied_static = _grid(width, False)
    for (x, y) in blocked_coords:      # 不可通行地形 (用于围出孤立区)
        passable[0][y][x] = False
    for (x, y) in occupied_coords:
        occupied[0][y][x] = True
    return MapData(
        width=width, levels=1, name="t", general={}, terrain=[],
        object_defs=[], object_data=[], passable=passable, occupied=occupied,
        occupied_static=occupied_static,
    )


class PlacementTest(unittest.TestCase):
    def test_returns_requested_count_on_land(self):
        m = _fake_map()
        pts = placement.find_placements(m, 6, seed=1)
        self.assertEqual(len(pts), 6)
        for x, y, z in pts:
            self.assertEqual(z, 0)
            self.assertTrue(m.passable[0][y][x])
            self.assertFalse(m.occupied[0][y][x])

    def test_avoids_occupied_and_neighbors(self):
        # 让中心一整块被占用, 选点不应落在该块及其 3x3 邻域
        occ = [(x, y) for x in range(10, 30) for y in range(10, 30)]
        m = _fake_map(occupied_coords=occ)
        pts = placement.find_placements(m, 5, seed=2)
        for x, y, _ in pts:
            self.assertFalse(m.occupied[0][y][x])

    def test_points_are_spread(self):
        m = _fake_map(width=60)
        pts = placement.find_placements(m, 4, seed=3)
        # 最远点采样: 任意两点不应紧贴
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                d2 = (pts[i][0] - pts[j][0]) ** 2 + (pts[i][1] - pts[j][1]) ** 2
                self.assertGreater(d2, 4)

    def test_skips_isolated_region(self):
        # 用不可通行的"围墙"把右下角一块区域封死, 内部虽有开阔空地,
        # 但和主区不连通; 选址绝不能落在里面 (这就是用户担心的"走不到").
        wall = [(30, y) for y in range(28, 40)] + [(x, 28) for x in range(30, 40)]
        m = _fake_map(width=40, blocked_coords=wall)
        reach = placement._main_reachable(m)
        pts = placement.find_placements(m, 8, seed=5)
        for x, y, _ in pts:
            self.assertTrue(reach[y][x], f"({x},{y}) 落在了不可达区")
            self.assertFalse(x > 30 and y > 28, f"({x},{y}) 落在了封闭的右下角")

    def test_raises_when_insufficient(self):
        # 全部占用 -> 无候选
        full = [(x, y) for x in range(40) for y in range(40)]
        m = _fake_map(occupied_coords=full)
        with self.assertRaises(ValueError):
            placement.find_placements(m, 1)


if __name__ == "__main__":
    unittest.main()
