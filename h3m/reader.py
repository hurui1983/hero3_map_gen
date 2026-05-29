"""只读 .h3m 加载器: 复用 lib/h3_map_editor 的 HotA 1.7 解析器.

为什么只读: 该 library 的 parse 是字节对齐可靠的 (3448 对象无报错走到文件尾),
但 write 路径对某些对象类型多吐 ~4KB (round-trip 不一致), 不能用于写盘.
所以这里只用它读结构, 写盘交给 h3m.inject 的字节级 patcher.

提供:
  - load(path) -> MapData   (尺寸/层数/地形/对象 + 派生的 land/occupancy 网格)
  - 地形可通行网格 (避水/避岩)
  - 占用网格 (按每个对象 def 的 red_squares footprint, anchor 在右下)
  - harvest_creature_sprites(): 从地图已有 Monster 收集 creature_id->sprite
"""
from __future__ import annotations

import gzip
import io as _io
import sys
from dataclasses import dataclass
from pathlib import Path

_LIB = Path(__file__).resolve().parent.parent / "lib" / "h3_map_editor"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

import src.file_io as _fio                       # noqa: E402
import src.handler_01_general as _h1             # noqa: E402
import src.handler_02_players_and_teams as _h2   # noqa: E402
import src.handler_03_conditions as _h3          # noqa: E402
import src.handler_04_heroes as _h4              # noqa: E402
import src.handler_05_additional_flags as _h5    # noqa: E402
import src.handler_06_rumors_and_events as _h6   # noqa: E402
import src.handler_07_terrain as _h7             # noqa: E402
import src.handler_08_objects as _h8             # noqa: E402
import data.objects as _od                       # noqa: E402

WATER = 8
ROCK = 9

# 怪物 (守军): 玩家打赢即可通过, 不算"永久障碍". 做可达性分析时放行.
MONSTER_TYPES = {
    _od.ID.Monster, _od.ID.Random_Monster,
    _od.ID.Random_Monster_1, _od.ID.Random_Monster_2, _od.ID.Random_Monster_3,
    _od.ID.Random_Monster_4, _od.ID.Random_Monster_5, _od.ID.Random_Monster_6,
    _od.ID.Random_Monster_7,
}


@dataclass
class MapData:
    width: int                 # 地图边长 (方形)
    levels: int                # 1 = 仅地表, 2 = 含地下
    name: str
    general: dict
    terrain: list              # library 解析的 tile 列表 (z*W*W + y*W + x)
    object_defs: list
    object_data: list
    passable: list             # passable[z][y][x] bool: 非水/岩
    occupied: list             # occupied[z][y][x] bool: 被任意已有对象 footprint 阻挡
    occupied_static: list      # 同上但不含怪物 (守军可打通); 用于可达性分析

    def tile_terrain(self, x: int, y: int, z: int = 0) -> int:
        return int(self.terrain[z * self.width * self.width + y * self.width + x][0])


def load(path: str | Path) -> MapData:
    """解析 .h3m, 返回 MapData. 解析失败会抛异常 (不静默吞)."""
    raw = gzip.open(path, "rb").read()
    _fio.in_file = _io.BytesIO(raw)

    general = _h1.parse_general()
    _h2.parse_player_specs()
    _h3.parse_conditions()
    _h2.parse_teams()
    _h4.parse_starting_heroes(general)
    _h5.parse_flags()
    _h6.parse_rumors()
    _h4.parse_hero_data()
    terrain = _h7.parse_terrain(general)
    object_defs = _h8.parse_object_defs()
    object_data = _h8.parse_object_data(object_defs)

    width = int(general["map_size"])
    levels = 2 if general["is_two_level"] else 1

    passable, occupied, occupied_static = _build_grids(
        width, levels, terrain, object_defs, object_data)
    return MapData(
        width=width, levels=levels, name=general["name"], general=general,
        terrain=terrain, object_defs=object_defs, object_data=object_data,
        passable=passable, occupied=occupied, occupied_static=occupied_static,
    )


def _build_grids(width, levels, terrain, object_defs, object_data):
    """构建 passable + occupied + occupied_static 网格."""
    W = width
    passable = [[[False] * W for _ in range(W)] for _ in range(levels)]
    occupied = [[[False] * W for _ in range(W)] for _ in range(levels)]
    occupied_static = [[[False] * W for _ in range(W)] for _ in range(levels)]

    # 地形可通行: 非水非岩
    for z in range(levels):
        for y in range(W):
            for x in range(W):
                t = int(terrain[z * W * W + y * W + x][0])
                passable[z][y][x] = t not in (WATER, ROCK)

    # 占用: 每个对象 def 的 red_squares (6 行 x 8 列, anchor 右下), bit==0 = 阻挡
    for obj in object_data:
        ax, ay, az = obj["coords"]
        if not (0 <= az < levels):
            continue
        is_monster = obj["type"] in MONSTER_TYPES
        red = object_defs[obj["def_id"]]["red_squares"]  # 48 bit 列表
        for r in range(6):
            for c in range(8):
                if red[r * 8 + c] == 0:  # 0 = 阻挡格
                    tx = ax - (7 - c)
                    ty = ay - (5 - r)
                    if 0 <= tx < W and 0 <= ty < W:
                        occupied[az][ty][tx] = True
                        if not is_monster:
                            occupied_static[az][ty][tx] = True
    return passable, occupied, occupied_static


def harvest_creature_sprites(m: MapData) -> dict[int, str]:
    """从地图已有 Monster 对象收集 creature_id -> sprite def (运行时兜底)."""
    out: dict[int, str] = {}
    for obj in m.object_data:
        if obj["type"] == _od.ID.Monster:
            cid = int(obj["subtype"])
            out.setdefault(cid, m.object_defs[obj["def_id"]]["sprite"])
    return out
