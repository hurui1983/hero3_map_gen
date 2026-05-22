#!/usr/bin/env python3
"""
Hero3 地图生成器 - 从自然语言描述生成 HoMM3 地图文件。

使用方式:
    python generator.py "你的地图描述"
    python generator.py "创建中等地图，2玩家，北方雪地城堡，南方草地壁垒"

环境变量:
    ANTHROPIC_API_KEY: Claude API Key (用于自然语言解析)
"""

import sys
import argparse
from pathlib import Path

from agent import MapAgent
from consts import Terrain, Town, Creature, Resource, Disposition
from llm_parser import parse_description


# 地图目录 (Mac Wineskin 版本)
GAME_MAPS_DIR = "/Applications/英雄无敌3：二合一.app/Contents/drive_c/game/Maps"


def position_to_coords(position, map_size: int) -> tuple:
    """将方位词转换为坐标。

    Args:
        position: 方位词 (north/south/center等) 或 {"x": int, "y": int}
        map_size: 地图大小

    Returns:
        (x, y) 坐标元组
    """
    if isinstance(position, dict):
        return (position.get("x", map_size // 2), position.get("y", map_size // 2))

    # 方位词到坐标的映射
    half = map_size // 2
    quarter = map_size // 4
    three_quarter = map_size * 3 // 4

    positions = {
        "north": (half, quarter),
        "south": (half, three_quarter),
        "east": (three_quarter, half),
        "west": (quarter, half),
        "center": (half, half),
        "northeast": (three_quarter, quarter),
        "northwest": (quarter, quarter),
        "southeast": (three_quarter, three_quarter),
        "southwest": (quarter, three_quarter),
    }

    return positions.get(position, (half, half))


def terrain_str_to_id(terrain_str: str) -> int:
    """将地形字符串转换为 ID。"""
    terrain_map = {
        "DIRT": Terrain.DIRT,
        "SAND": Terrain.SAND,
        "GRASS": Terrain.GRASS,
        "SNOW": Terrain.SNOW,
        "SWAMP": Terrain.SWAMP,
        "ROUGH": Terrain.ROUGH,
        "SUBTERRANEAN": Terrain.SUBTERRANEAN,
        "LAVA": Terrain.LAVA,
        "WATER": Terrain.WATER,
        "ROCK": Terrain.ROCK,
        "HIGHLANDS": Terrain.HIGHLANDS,
        "WASTELAND": Terrain.WASTELAND,
    }
    return terrain_map.get(terrain_str.upper(), Terrain.GRASS)


def creature_str_to_id(creature_str: str) -> int:
    """将怪物字符串转换为 ID。"""
    creature_map = {
        "PIKEMAN": Creature.PIKEMAN,
        "ARCHER": Creature.ARCHER,
        "GRIFFIN": Creature.GRIFFIN,
        "ANGEL": Creature.ANGEL,
        "ARCHANGEL": Creature.ARCHANGEL,
        "GREEN_DRAGON": Creature.GREEN_DRAGON,
        "GOLD_DRAGON": Creature.GOLD_DRAGON,
        "BLACK_DRAGON": Creature.BLACK_DRAGON,
        "SKELETON": Creature.SKELETON,
        "VAMPIRE": Creature.VAMPIRE,
        "LICH": Creature.LICH,
        "BONE_DRAGON": Creature.BONE_DRAGON,
        "GHOST_DRAGON": Creature.GHOST_DRAGON,
        "BEHEMOTH": Creature.BEHEMOTH,
        "ANCIENT_BEHEMOTH": Creature.ANCIENT_BEHEMOTH,
        "PHOENIX": Creature.PHOENIX,
        "AZURE_DRAGON": Creature.AZURE_DRAGON,
        "RED_DRAGON": Creature.RED_DRAGON,
        "TITAN": Creature.TITAN,
        "ARCH_DEVIL": Creature.ARCH_DEVIL,
    }
    return creature_map.get(creature_str.upper(), Creature.GREEN_DRAGON)


def resource_str_to_id(resource_str: str) -> int:
    """将资源字符串转换为 ID。"""
    resource_map = {
        "WOOD": Resource.WOOD,
        "MERCURY": Resource.MERCURY,
        "ORE": Resource.ORE,
        "SULFUR": Resource.SULFUR,
        "CRYSTAL": Resource.CRYSTAL,
        "GEMS": Resource.GEMS,
        "GOLD": Resource.GOLD,
    }
    return resource_map.get(resource_str.upper(), Resource.GOLD)


def fill_terrain_area(agent: MapAgent, area: str, terrain_id: int, map_size: int):
    """根据方位词填充地形区域。"""
    half = map_size // 2

    area_coords = {
        "north": (0, 0, map_size - 1, half - 1),
        "south": (0, half, map_size - 1, map_size - 1),
        "east": (half, 0, map_size - 1, map_size - 1),
        "west": (0, 0, half - 1, map_size - 1),
        "center": (half // 2, half // 2, map_size - half // 2, map_size - half // 2),
        "northeast": (half, 0, map_size - 1, half - 1),
        "northwest": (0, 0, half - 1, half - 1),
        "southeast": (half, half, map_size - 1, map_size - 1),
        "southwest": (0, half, half - 1, map_size - 1),
        "all": (0, 0, map_size - 1, map_size - 1),
    }

    coords = area_coords.get(area.lower(), area_coords["all"])
    agent.fill_terrain(coords[0], coords[1], coords[2], coords[3], terrain_id)


def execute_instructions(agent: MapAgent, instructions: dict) -> None:
    """执行地图生成指令。

    Args:
        agent: MapAgent 实例
        instructions: 解析后的指令字典
    """
    # 使用实际地图大小，而不是指令中的 (因为我们无法改变模板地图大小)
    map_size = agent.get_map_info()["size"]

    # 设置地图信息
    if "map_name" in instructions:
        agent.set_map_name(instructions["map_name"])
    if "map_description" in instructions:
        agent.set_map_description(instructions["map_description"])

    # 填充地形
    for zone in instructions.get("terrain_zones", []):
        terrain_id = terrain_str_to_id(zone["terrain"])
        fill_terrain_area(agent, zone["area"], terrain_id, map_size)

    # 放置怪物
    for monster in instructions.get("monsters", []):
        creature_id = creature_str_to_id(monster["creature"])
        x, y = position_to_coords(monster["position"], map_size)
        quantity = monster.get("quantity", 0)
        disposition = monster.get("disposition", 3)  # 默认敌对
        agent.add_monster(creature_id, x, y, 0, quantity, disposition)

    # 放置资源
    for resource in instructions.get("resources", []):
        resource_id = resource_str_to_id(resource["type"])
        x, y = position_to_coords(resource["position"], map_size)
        amount = resource.get("amount", 0)
        agent.add_resource(resource_id, x, y, 0, amount)

    # TODO: 放置城镇 (需要更复杂的实现)
    # 目前城镇放置比较复杂，因为需要处理玩家配置、建筑等
    # 暂时跳过，后续版本实现


def generate_map(description: str, output_path: str = None,
                 base_map: str = "base.h3m", use_api: bool = True,
                 copy_to_game: bool = False) -> str:
    """从自然语言描述生成地图。

    Args:
        description: 地图描述文本
        output_path: 输出文件路径 (默认 generated_map.h3m)
        base_map: 基础模板地图
        use_api: 是否使用 Claude API
        copy_to_game: 是否复制到游戏目录

    Returns:
        生成的地图文件路径
    """
    if output_path is None:
        output_path = "generated_map.h3m"

    print(f"正在解析描述...")

    # 解析描述
    instructions = parse_description(description, use_api=use_api)
    print(f"解析完成: {instructions.get('map_name', 'Unknown')}")

    # 加载基础地图
    print(f"加载基础模板: {base_map}")
    agent = MapAgent(base_map)

    # 执行指令
    print("正在生成地图...")
    execute_instructions(agent, instructions)

    # 保存地图
    agent.save(output_path)
    print(f"地图已保存: {output_path}")

    # 复制到游戏目录
    if copy_to_game:
        import shutil
        game_path = Path(GAME_MAPS_DIR)
        if game_path.exists():
            dest = game_path / Path(output_path).name
            shutil.copy(output_path, dest)
            print(f"已复制到游戏目录: {dest}")
        else:
            print(f"警告: 游戏目录不存在: {GAME_MAPS_DIR}")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Hero3 地图生成器 - 从自然语言描述生成 HoMM3 地图",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python generator.py "创建中等地图，2玩家，北方雪地，南方草地"
  python generator.py "小地图，北方熔岩放几条黑龙" -o my_map.h3m
  python generator.py "大地图，中间有金龙守护" --copy-to-game
  python generator.py "简单的草地地图" --offline
        """
    )

    parser.add_argument("description", help="地图描述文本")
    parser.add_argument("-o", "--output", default="generated_map.h3m",
                        help="输出文件路径 (默认: generated_map.h3m)")
    parser.add_argument("-b", "--base", default="base.h3m",
                        help="基础模板地图 (默认: base.h3m)")
    parser.add_argument("--offline", action="store_true",
                        help="使用离线解析器 (不调用 Claude API)")
    parser.add_argument("--copy-to-game", action="store_true",
                        help="生成后复制到游戏 Maps 目录")

    args = parser.parse_args()

    try:
        output = generate_map(
            args.description,
            output_path=args.output,
            base_map=args.base,
            use_api=not args.offline,
            copy_to_game=args.copy_to_game
        )
        print(f"\n完成! 地图文件: {output}")
        print("\n下一步:")
        print(f"  1. 复制地图到游戏目录:")
        print(f'     cp "{output}" "{GAME_MAPS_DIR}/"')
        print(f"  2. 启动游戏，在单人游戏中选择该地图")

    except FileNotFoundError as e:
        print(f"错误: 找不到文件 - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
