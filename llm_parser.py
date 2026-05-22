"""
LLM Parser - 使用 Claude API 将自然语言描述转换为地图生成指令。
"""

import json
import os

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


SYSTEM_PROMPT = """你是一个英雄无敌3地图生成助手。根据用户的描述，生成地图指令JSON。

## 可用值

地形 (terrain):
- DIRT(0), SAND(1), GRASS(2), SNOW(3), SWAMP(4), ROUGH(5), SUBTERRANEAN(6), LAVA(7), WATER(8), ROCK(9)

城镇类型 (town_type):
- CASTLE(0): 城堡 - 人类骑士派系
- RAMPART(1): 壁垒 - 精灵森林派系
- TOWER(2): 塔楼 - 法师派系
- INFERNO(3): 地狱 - 恶魔派系
- NECROPOLIS(4): 墓园 - 亡灵派系
- DUNGEON(5): 地下城 - 地下生物派系
- STRONGHOLD(6): 据点 - 野蛮人派系
- FORTRESS(7): 要塞 - 沼泽生物派系
- CONFLUX(8): 元素城 - 元素派系
- COVE(9): 海盗湾 - HotA海盗派系

地图大小 (size):
- 36: 小 (S)
- 72: 中 (M)
- 108: 大 (L)
- 144: 超大 (XL)

方位 (用于 area 和 position):
- north: 上半部分
- south: 下半部分
- east: 右半部分
- west: 左半部分
- center: 中心区域
- northeast, northwest, southeast, southwest: 四个角落

常用怪物 (creature):
- PIKEMAN(0), ARCHER(2), GRIFFIN(4), ANGEL(12), ARCHANGEL(13)
- GREEN_DRAGON(26), GOLD_DRAGON(27), BLACK_DRAGON(83)
- SKELETON(56), VAMPIRE(62), LICH(64), BONE_DRAGON(68)
- BEHEMOTH(96), ANCIENT_BEHEMOTH(97)
- PHOENIX(131), AZURE_DRAGON(132)

资源类型 (resource):
- WOOD(0), MERCURY(1), ORE(2), SULFUR(3), CRYSTAL(4), GEMS(5), GOLD(6)

## 输出格式

只输出JSON，不要任何其他文字：

{
  "map_name": "地图名称",
  "map_description": "地图描述",
  "size": 72,
  "terrain_zones": [
    {"area": "north", "terrain": "SNOW"},
    {"area": "south", "terrain": "GRASS"}
  ],
  "players": [
    {"id": 0, "town_type": "CASTLE", "position": "north"},
    {"id": 1, "town_type": "RAMPART", "position": "south"}
  ],
  "monsters": [
    {"creature": "GREEN_DRAGON", "position": "center", "quantity": 5, "disposition": 3}
  ],
  "resources": [
    {"type": "GOLD", "position": "center", "amount": 5000}
  ]
}

## 注意事项

1. position 可以是方位词 (north/south/center等) 或具体坐标 {"x": 10, "y": 20}
2. quantity 为 0 表示随机数量
3. disposition: 0=顺从, 1=友好, 2=攻击, 3=敌对, 4=野蛮
4. 如果用户没有明确指定，使用合理的默认值
5. 确保玩家数量和城镇数量匹配
"""


def parse_with_claude(description: str, api_key: str = None) -> dict:
    """使用 Claude API 解析自然语言描述为地图指令。

    Args:
        description: 用户的地图描述
        api_key: Anthropic API Key (可选，默认从环境变量读取)

    Returns:
        解析后的地图指令字典

    Raises:
        ImportError: 未安装 anthropic 库
        ValueError: API 调用失败或返回无效 JSON
    """
    if not HAS_ANTHROPIC:
        raise ImportError(
            "需要安装 anthropic 库: pip install anthropic"
        )

    # 获取 API Key
    if api_key is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "需要设置 ANTHROPIC_API_KEY 环境变量或传入 api_key 参数"
        )

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": description}]
    )

    # 提取响应文本
    response_text = message.content[0].text.strip()

    # 尝试解析 JSON
    try:
        # 处理可能的 markdown 代码块
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            # 去掉首尾的 ``` 行
            json_lines = []
            in_json = False
            for line in lines:
                if line.startswith("```"):
                    in_json = not in_json
                    continue
                if in_json or not line.startswith("```"):
                    json_lines.append(line)
            response_text = "\n".join(json_lines)

        return json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude 返回的不是有效 JSON: {e}\n响应: {response_text}")


def parse_offline(description: str) -> dict:
    """简单的离线解析器 (基于关键词匹配)。

    这是一个备用方案，当没有 API Key 时使用。
    只能处理非常简单的描述。

    Args:
        description: 用户的地图描述

    Returns:
        解析后的地图指令字典
    """
    import re

    instructions = {
        "map_name": "Generated Map",
        "map_description": description,
        "size": 72,
        "terrain_zones": [],
        "players": [],
        "monsters": [],
        "resources": [],
    }

    desc_lower = description.lower()

    # 解析地图大小
    if any(w in desc_lower for w in ["小", "small", "tiny"]):
        instructions["size"] = 36
    elif any(w in desc_lower for w in ["大", "large", "big"]):
        instructions["size"] = 108
    elif any(w in desc_lower for w in ["超大", "巨大", "huge", "extra"]):
        instructions["size"] = 144

    # 解析玩家数量
    player_match = re.search(r"(\d+)\s*(个|位)?\s*(玩家|player)", desc_lower)
    num_players = int(player_match.group(1)) if player_match else 2

    # 解析城镇类型
    town_map = {
        "城堡": "CASTLE", "castle": "CASTLE", "人类": "CASTLE",
        "壁垒": "RAMPART", "rampart": "RAMPART", "精灵": "RAMPART",
        "塔楼": "TOWER", "tower": "TOWER", "法师": "TOWER",
        "地狱": "INFERNO", "inferno": "INFERNO", "恶魔": "INFERNO",
        "墓园": "NECROPOLIS", "necropolis": "NECROPOLIS", "亡灵": "NECROPOLIS",
        "地下城": "DUNGEON", "dungeon": "DUNGEON",
        "据点": "STRONGHOLD", "stronghold": "STRONGHOLD", "野蛮人": "STRONGHOLD",
        "要塞": "FORTRESS", "fortress": "FORTRESS",
        "元素": "CONFLUX", "conflux": "CONFLUX",
    }

    # 方位-地形解析 (更智能的解析)
    # 匹配 "北方是雪地" 或 "north is snow" 这样的模式
    import re

    terrain_map = {
        "草": "GRASS", "grass": "GRASS", "草地": "GRASS", "草原": "GRASS",
        "雪": "SNOW", "snow": "SNOW", "雪地": "SNOW", "冰": "SNOW",
        "沙": "SAND", "sand": "SAND", "沙漠": "SAND", "desert": "SAND",
        "熔岩": "LAVA", "lava": "LAVA", "火山": "LAVA",
        "沼泽": "SWAMP", "swamp": "SWAMP",
        "泥": "DIRT", "dirt": "DIRT", "泥地": "DIRT",
    }

    position_map = {
        "北": "north", "north": "north", "上": "north",
        "南": "south", "south": "south", "下": "south",
        "东": "east", "east": "east", "右": "east",
        "西": "west", "west": "west", "左": "west",
        "中": "center", "center": "center", "中间": "center", "中央": "center",
    }

    # 尝试匹配 "北方是雪地" 模式
    for pos_key, pos_val in position_map.items():
        for terrain_key, terrain_val in terrain_map.items():
            # 匹配 "北方是雪地" 或 "北方雪地" 或 "北边是雪"
            patterns = [
                f"{pos_key}[方边]?[是有]?{terrain_key}",
                f"{terrain_key}[在于]?{pos_key}",
            ]
            for pattern in patterns:
                if re.search(pattern, description):
                    # 检查是否已经有这个方位的地形
                    existing = [z for z in instructions["terrain_zones"] if z["area"] == pos_val]
                    if not existing:
                        instructions["terrain_zones"].append({
                            "area": pos_val,
                            "terrain": terrain_val
                        })
                    break

    # 如果没有解析到地形，用简单的关键词匹配作为备选
    if not instructions["terrain_zones"]:
        terrains_found = []
        for keyword, terrain in terrain_map.items():
            if keyword in desc_lower and terrain not in terrains_found:
                terrains_found.append(terrain)

        fallback_positions = ["north", "south"]
        for i, terrain in enumerate(terrains_found[:2]):
            pos = fallback_positions[i] if i < len(fallback_positions) else "center"
            instructions["terrain_zones"].append({
                "area": pos,
                "terrain": terrain
            })

    towns_found = []
    for keyword, town in town_map.items():
        if keyword in desc_lower:
            if town not in towns_found:
                towns_found.append(town)

    # 填充玩家
    default_towns = ["CASTLE", "RAMPART", "TOWER", "INFERNO", "NECROPOLIS", "DUNGEON"]
    player_positions = ["north", "south", "east", "west"]
    for i in range(num_players):
        town = towns_found[i] if i < len(towns_found) else default_towns[i % len(default_towns)]
        pos = player_positions[i] if i < len(player_positions) else "center"
        instructions["players"].append({
            "id": i,
            "town_type": town,
            "position": pos
        })

    # 解析怪物
    monster_map = {
        "龙": "GREEN_DRAGON", "dragon": "GREEN_DRAGON",
        "金龙": "GOLD_DRAGON", "gold dragon": "GOLD_DRAGON",
        "黑龙": "BLACK_DRAGON", "black dragon": "BLACK_DRAGON",
        "天使": "ANGEL", "angel": "ANGEL",
        "大天使": "ARCHANGEL", "archangel": "ARCHANGEL",
        "凤凰": "PHOENIX", "phoenix": "PHOENIX",
    }

    for keyword, creature in monster_map.items():
        if keyword in desc_lower:
            instructions["monsters"].append({
                "creature": creature,
                "position": "center",
                "quantity": 0,
                "disposition": 3
            })
            break

    return instructions


def parse_description(description: str, use_api: bool = True, api_key: str = None) -> dict:
    """解析地图描述的统一入口。

    Args:
        description: 用户的地图描述
        use_api: 是否使用 Claude API (默认 True)
        api_key: API Key (可选)

    Returns:
        解析后的地图指令字典
    """
    if use_api:
        try:
            return parse_with_claude(description, api_key)
        except (ImportError, ValueError) as e:
            print(f"警告: Claude API 不可用 ({e})，使用离线解析器")
            return parse_offline(description)
    else:
        return parse_offline(description)


if __name__ == "__main__":
    # 测试
    test_desc = "创建一个中等大小的地图，2个玩家，北方是雪地有城堡派系，南方是草地有壁垒派系，中间放几条龙"
    print("测试描述:", test_desc)
    print()

    # 先测试离线解析器
    print("=== 离线解析结果 ===")
    result = parse_offline(test_desc)
    print(json.dumps(result, indent=2, ensure_ascii=False))
