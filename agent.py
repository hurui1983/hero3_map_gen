"""
MapAgent - AI-friendly API for HoMM3/HotA map editing.
"""

import sys
from pathlib import Path
from gzip import open as gzip_open

# Add lib to path for h3_map_editor imports
lib_path = Path(__file__).parent / "lib" / "h3_map_editor"
sys.path.insert(0, str(lib_path))

import src.file_io as io
import src.handler_01_general as h1
import src.handler_02_players_and_teams as h2
import src.handler_03_conditions as h3
import src.handler_04_heroes as h4
import src.handler_05_additional_flags as h5
import src.handler_06_rumors_and_events as h6
import src.handler_07_terrain as h7
import src.handler_08_objects as h8
import data.objects as od
import data.creatures as cd


class MapAgent:
    """Agent for loading, modifying, and saving HoMM3/HotA maps."""

    def __init__(self, map_path: str):
        """Load a map from the given path.

        Args:
            map_path: Path to the .h3m map file.
        """
        self.map_path = map_path
        self.map_data = {
            "general": {},
            "player_specs": [],
            "conditions": {},
            "teams": {},
            "start_heroes": {},
            "ban_flags": {},
            "rumors": [],
            "hero_data": [],
            "terrain": [],
            "object_defs": [],
            "object_data": [],
            "events": [],
            "null_bytes": b''
        }
        self._load_map(map_path)

    def _load_map(self, filename: str) -> None:
        """Load and parse a map file."""
        if not filename.endswith(".h3m"):
            filename += ".h3m"

        with gzip_open(filename, 'rb') as io.in_file:
            self.map_data["general"] = h1.parse_general()
            self.map_data["player_specs"] = h2.parse_player_specs()
            self.map_data["conditions"] = h3.parse_conditions()
            self.map_data["teams"] = h2.parse_teams()
            self.map_data["start_heroes"] = h4.parse_starting_heroes(self.map_data["general"])
            self.map_data["ban_flags"] = h5.parse_flags()
            self.map_data["rumors"] = h6.parse_rumors()
            self.map_data["hero_data"] = h4.parse_hero_data()
            self.map_data["terrain"] = h7.parse_terrain(self.map_data["general"])
            self.map_data["object_defs"] = h8.parse_object_defs()
            self.map_data["object_data"] = h8.parse_object_data(self.map_data["object_defs"])
            self.map_data["events"] = h6.parse_events()
            self.map_data["null_bytes"] = io.in_file.read()

    def get_map_info(self) -> dict:
        """Get basic map information.

        Returns:
            Dict with name, description, size, and version info.
        """
        general = self.map_data["general"]
        return {
            "name": general.get("name", ""),
            "description": general.get("description", ""),
            "size": int(general.get("map_size", 0)),
            "map_format": str(general.get("map_format", "")),
            "hota_version": general.get("hota_version", 0),
            "is_two_level": general.get("is_two_level", False),
        }

    def _get_tile_index(self, x: int, y: int, level: int = 0) -> int:
        """Calculate the flat index for a tile coordinate.

        Coordinate system: (0,0) is Top-Left.
        Level 0 = Surface, Level 1 = Underground.

        Args:
            x: X coordinate (column)
            y: Y coordinate (row)
            level: Map level (0=surface, 1=underground)

        Returns:
            Index into the flat terrain list.
        """
        size = self.map_data["general"]["map_size"]
        base_index = y * size + x
        if level == 1:
            base_index += size * size
        return base_index

    def fill_terrain(self, x1: int, y1: int, x2: int, y2: int, terrain_id: int, level: int = 0) -> None:
        """Fill a rectangular area with a terrain type.

        Args:
            x1, y1: Top-left corner coordinates.
            x2, y2: Bottom-right corner coordinates (inclusive).
            terrain_id: Terrain type ID (use consts.Terrain).
            level: Map level (0=surface, 1=underground). Defaults to 0.
        """
        terrain = self.map_data["terrain"]
        size = self.map_data["general"]["map_size"]

        # Clamp coordinates to valid range
        x1 = max(0, min(x1, size - 1))
        x2 = max(0, min(x2, size - 1))
        y1 = max(0, min(y1, size - 1))
        y2 = max(0, min(y2, size - 1))

        # Ensure x1 <= x2 and y1 <= y2
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1

        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                tile_index = self._get_tile_index(x, y, level)
                # Tile structure: [terrain_type, terrain_picture, river_type, river_picture, road_type, road_picture, mirroring]
                # We only modify terrain_type (index 0)
                terrain[tile_index][0] = h7.TerrainType(terrain_id)

    def save(self, output_path: str) -> None:
        """Save the map to a file.

        Args:
            output_path: Path for the output .h3m file.
        """
        if not output_path.endswith(".h3m"):
            output_path += ".h3m"

        with gzip_open(output_path, 'wb') as io.out_file:
            h1.write_general(self.map_data["general"])
            h2.write_player_specs(self.map_data["player_specs"])
            h3.write_conditions(self.map_data["conditions"])
            h2.write_teams(self.map_data["teams"])
            h4.write_starting_heroes(self.map_data["start_heroes"])
            h5.write_flags(self.map_data["ban_flags"])
            h6.write_rumors(self.map_data["rumors"])
            h4.write_hero_data(self.map_data["hero_data"])
            h7.write_terrain(self.map_data["terrain"])
            h8.write_object_defs(self.map_data["object_defs"])
            h8.write_object_data(self.map_data["object_data"])
            h6.write_events(self.map_data["events"])
            io.out_file.write(self.map_data["null_bytes"])

    # ==================== 对象操作 API ====================

    def list_objects(self, obj_type: int = None) -> list:
        """列出地图中的所有对象。

        Args:
            obj_type: 可选，按类型过滤 (使用 data.objects.ID)

        Returns:
            对象列表，每个包含 index, type, subtype, coords
        """
        result = []
        for i, obj in enumerate(self.map_data["object_data"]):
            if obj_type is None or obj["type"] == obj_type:
                result.append({
                    "index": i,
                    "type": obj["type"],
                    "subtype": obj.get("subtype"),
                    "coords": obj["coords"],
                })
        return result

    def get_objects_at(self, x: int, y: int, level: int = 0) -> list:
        """获取指定坐标的所有对象。

        Args:
            x, y: 坐标
            level: 地图层级 (0=地表, 1=地下)

        Returns:
            该坐标上的对象列表
        """
        result = []
        for i, obj in enumerate(self.map_data["object_data"]):
            coords = obj["coords"]
            if coords[0] == x and coords[1] == y and coords[2] == level:
                result.append({
                    "index": i,
                    "type": obj["type"],
                    "subtype": obj.get("subtype"),
                    "coords": coords,
                })
        return result

    def _find_or_create_object_def(self, obj_type: int, subtype: int, sprite: str) -> int:
        """查找或创建对象定义，返回 def_id。

        Args:
            obj_type: 对象类型 ID
            subtype: 子类型 ID
            sprite: 精灵文件名

        Returns:
            对象定义的索引 (def_id)
        """
        # 先查找已有的定义
        for i, obj_def in enumerate(self.map_data["object_defs"]):
            if obj_def["type"] == obj_type and obj_def["subtype"] == subtype:
                return i

        # 创建新定义
        # bits 格式: list of 0/1 integers, 每字节8位
        new_def = {
            "sprite": sprite,
            "red_squares": [0] * 48,        # 碰撞盒 (6字节 = 48 bits)
            "yellow_squares": [0] * 48,     # 可通行区域
            "placeable_terrain": [1] * 16,  # 可放置地形 (2字节, 全部允许)
            "editor_section": [0] * 16,     # 编辑器分类 (2字节)
            "type": obj_type,
            "subtype": subtype,
            "editor_group": 0,
            "below_ground": False,
            "null_bytes": b'\x00' * 16,
        }
        self.map_data["object_defs"].append(new_def)
        return len(self.map_data["object_defs"]) - 1

    def add_monster(self, creature_id: int, x: int, y: int, level: int = 0,
                    quantity: int = 0, disposition: int = 1) -> int:
        """在指定坐标放置怪物。

        Args:
            creature_id: 怪物ID (使用 data.creatures.ID 或 consts.Creature)
            x, y: 坐标
            level: 0=地表, 1=地下
            quantity: 数量 (0=随机)
            disposition: 态度 (0=顺从, 1=友好, 2=攻击, 3=敌对, 4=野蛮)

        Returns:
            新对象的索引
        """
        # 获取怪物精灵名称
        sprite_name = self._get_monster_sprite(creature_id)

        # 查找或创建对象定义
        def_id = self._find_or_create_object_def(
            od.ID.Monster, creature_id, sprite_name
        )

        # 创建对象数据
        obj_data = {
            "coords": [x, y, level],
            "def_id": def_id,
            "type": od.ID.Monster,
            "subtype": creature_id,
            "start_bytes": b'\x00\x00\x00\x00',
            "quantity": quantity,
            "disposition": h8.Disposition(disposition),
            "monster_never_flees": False,
            "quantity_does_not_grow": False,
            "middle_bytes": b'\x00\x00',
            "precise_disposition": 0,
            "join_only_for_money": False,
            "joining_monster_percent": 100,
            "upgraded_stack": 0,
            "stack_count": 0,
            "is_value": False,
            "ai_value": 0,
        }

        self.map_data["object_data"].append(obj_data)
        return len(self.map_data["object_data"]) - 1

    def _get_monster_sprite(self, creature_id: int) -> str:
        """获取怪物的精灵文件名。"""
        # 精灵命名规则: AvWxxxx.def (xxxx = 怪物名)
        # 简化处理: 使用通用格式
        names = {
            0: "AVWpikm0.def",    # Pikeman
            2: "AVWlcrs0.def",    # Archer
            4: "AVWgrff0.def",    # Griffin
            26: "AVWgdrg0.def",   # Green Dragon
            27: "AVWgoldd.def",   # Gold Dragon
            83: "AVWbdrg0.def",   # Black Dragon
            12: "AVWangl0.def",   # Angel
            13: "AVWarch0.def",   # Archangel
        }
        return names.get(creature_id, f"AVWmons.def")

    def add_resource(self, resource_type: int, x: int, y: int, level: int = 0,
                     amount: int = 0) -> int:
        """放置资源堆。

        Args:
            resource_type: 资源类型 (0=木材, 1=水银, 2=矿石, 3=硫磺, 4=晶体, 5=宝石, 6=金币)
            x, y: 坐标
            level: 0=地表, 1=地下
            amount: 数量 (0=随机)

        Returns:
            新对象的索引
        """
        sprite_names = {
            0: "AVTwood0.def",   # Wood
            1: "AVTmerc0.def",   # Mercury
            2: "AVTore00.def",   # Ore
            3: "AVTsulf0.def",   # Sulfur
            4: "AVTcrys0.def",   # Crystal
            5: "AVTgems0.def",   # Gems
            6: "AVTgold0.def",   # Gold
        }
        sprite = sprite_names.get(resource_type, "AVTres00.def")

        def_id = self._find_or_create_object_def(
            od.ID.Resource, resource_type, sprite
        )

        obj_data = {
            "coords": [x, y, level],
            "def_id": def_id,
            "type": od.ID.Resource,
            "subtype": resource_type,
            "amount": amount,
        }

        self.map_data["object_data"].append(obj_data)
        return len(self.map_data["object_data"]) - 1

    def set_map_name(self, name: str) -> None:
        """设置地图名称。"""
        self.map_data["general"]["name"] = name

    def set_map_description(self, description: str) -> None:
        """设置地图描述。"""
        self.map_data["general"]["description"] = description
