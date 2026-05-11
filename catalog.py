"""
菜单词典 (Layer 2): AI 翻译输出的"菜名" -> RMG 内部 ID

设计原则:
  - 每一项菜支持多个中文/英文别名 (用户/AI 可能用不同说法)
  - 解析函数 (resolve_*) 找不到时返回 None, 由调用方决定如何处理
  - 这是 AI 的"白名单": AI 输出的菜品必须在这里能找到, 否则被拒绝
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CatalogItem:
    """词典里一个可点的"菜"."""
    key: str                  # 内部规范 key (英文 snake_case)
    rmg_id: int               # RMG 模板里使用的数字 ID
    name_zh: str              # 中文标准名 (展示给用户看)
    name_en: str              # 英文标准名
    aliases_zh: list[str] = field(default_factory=list)
    aliases_en: list[str] = field(default_factory=list)


# ============================================================
# 生物 (Creatures)
# 选取范围: 各派系最有代表性的英雄/明星生物 (7 级 + 几个标志性低级)
# ID 来源: consts.py 中的 Creature 枚举
# ============================================================

CREATURES: dict[str, CatalogItem] = {
    # Castle (城堡)
    "archangel": CatalogItem(
        key="archangel", rmg_id=13, name_zh="大天使", name_en="Archangel",
        aliases_zh=["天使长", "圣天使"], aliases_en=["arch angel"],
    ),
    "angel": CatalogItem(
        key="angel", rmg_id=12, name_zh="天使", name_en="Angel",
    ),
    # Rampart (壁垒)
    "gold_dragon": CatalogItem(
        key="gold_dragon", rmg_id=27, name_zh="金龙", name_en="Gold Dragon",
    ),
    "green_dragon": CatalogItem(
        key="green_dragon", rmg_id=26, name_zh="绿龙", name_en="Green Dragon",
    ),
    # Tower (塔楼)
    "titan": CatalogItem(
        key="titan", rmg_id=41, name_zh="泰坦", name_en="Titan",
        aliases_zh=["泰坦巨人"],
    ),
    # Inferno (地狱)
    "arch_devil": CatalogItem(
        key="arch_devil", rmg_id=55, name_zh="大恶魔", name_en="Arch Devil",
        aliases_en=["archdevil"],
    ),
    "devil": CatalogItem(
        key="devil", rmg_id=54, name_zh="恶魔", name_en="Devil",
    ),
    # Necropolis (墓园)
    "ghost_dragon": CatalogItem(
        key="ghost_dragon", rmg_id=69, name_zh="鬼龙", name_en="Ghost Dragon",
        aliases_zh=["幽灵龙", "魂龙"],
    ),
    "bone_dragon": CatalogItem(
        key="bone_dragon", rmg_id=68, name_zh="骨龙", name_en="Bone Dragon",
    ),
    "lich": CatalogItem(
        key="lich", rmg_id=64, name_zh="巫妖", name_en="Lich",
    ),
    # Dungeon (地下城)
    "black_dragon": CatalogItem(
        key="black_dragon", rmg_id=83, name_zh="黑龙", name_en="Black Dragon",
    ),
    "red_dragon": CatalogItem(
        key="red_dragon", rmg_id=82, name_zh="红龙", name_en="Red Dragon",
        aliases_zh=["赤龙"],
    ),
    # Stronghold (据点)
    "ancient_behemoth": CatalogItem(
        key="ancient_behemoth", rmg_id=97, name_zh="比蒙巨兽", name_en="Ancient Behemoth",
        aliases_zh=["远古比蒙", "古比蒙"],
    ),
    "behemoth": CatalogItem(
        key="behemoth", rmg_id=96, name_zh="比蒙", name_en="Behemoth",
    ),
    # Fortress (要塞)
    "chaos_hydra": CatalogItem(
        key="chaos_hydra", rmg_id=111, name_zh="混乱九头蛇", name_en="Chaos Hydra",
        aliases_zh=["混乱九头怪"],
    ),
    "hydra": CatalogItem(
        key="hydra", rmg_id=110, name_zh="九头蛇", name_en="Hydra",
        aliases_zh=["九头怪"],
    ),
    # Conflux (元素城)
    "phoenix": CatalogItem(
        key="phoenix", rmg_id=131, name_zh="凤凰", name_en="Phoenix",
        aliases_zh=["不死鸟"],
    ),
    "firebird": CatalogItem(
        key="firebird", rmg_id=130, name_zh="火鸟", name_en="Firebird",
    ),
    # Neutral (中立)
    "azure_dragon": CatalogItem(
        key="azure_dragon", rmg_id=132, name_zh="圣龙", name_en="Azure Dragon",
        aliases_zh=["碧蓝龙", "蓝龙"],
    ),
    "crystal_dragon": CatalogItem(
        key="crystal_dragon", rmg_id=133, name_zh="水晶龙", name_en="Crystal Dragon",
    ),
    "faerie_dragon": CatalogItem(
        key="faerie_dragon", rmg_id=134, name_zh="仙龙", name_en="Faerie Dragon",
        aliases_zh=["精灵龙", "仙女龙", "紫龙"], aliases_en=["fairy dragon"],
    ),
    "rust_dragon": CatalogItem(
        key="rust_dragon", rmg_id=135, name_zh="锈龙", name_en="Rust Dragon",
        aliases_zh=["毒龙"],
    ),
}


# ============================================================
# 神器 (Artifacts)
# 选取范围: 标志性 / 玩家最常知道的几件
# ID 来源: HoMM3 神器 ID 表 (常用值, 后续按需扩充)
# ============================================================

ARTIFACTS: dict[str, CatalogItem] = {
    "armageddons_blade": CatalogItem(
        key="armageddons_blade", rmg_id=128, name_zh="末日之刃", name_en="Armageddon's Blade",
        aliases_zh=["末日剑", "末日神剑"], aliases_en=["armageddon blade"],
    ),
    "angelic_alliance": CatalogItem(
        key="angelic_alliance", rmg_id=129, name_zh="天使联盟", name_en="Angelic Alliance",
    ),
    "cloak_of_the_undead_king": CatalogItem(
        key="cloak_of_the_undead_king", rmg_id=130, name_zh="鬼王斗篷", name_en="Cloak of the Undead King",
        aliases_zh=["不死之王披风", "亡灵王披风"],
    ),
    "elixir_of_life": CatalogItem(
        key="elixir_of_life", rmg_id=131, name_zh="生命灵药", name_en="Elixir of Life",
        aliases_zh=["永生灵药", "神圣血瓶"],
    ),
    "armor_of_the_damned": CatalogItem(
        key="armor_of_the_damned", rmg_id=132, name_zh="诅咒铠甲", name_en="Armor of the Damned",
        aliases_zh=["诅咒之甲"],
    ),
    "statue_of_legion": CatalogItem(
        key="statue_of_legion", rmg_id=133, name_zh="军团雕像", name_en="Statue of Legion",
    ),
    "power_of_the_dragon_father": CatalogItem(
        key="power_of_the_dragon_father", rmg_id=134, name_zh="龙父神力", name_en="Power of the Dragon Father",
        aliases_zh=["龙父之力", "龙王之力", "龙父"],
    ),
    "titans_thunder": CatalogItem(
        key="titans_thunder", rmg_id=135, name_zh="泰坦之雷", name_en="Titan's Thunder",
        aliases_zh=["巨人之雷"], aliases_en=["titans thunder"],
    ),
    "admirals_hat": CatalogItem(
        key="admirals_hat", rmg_id=136, name_zh="海军上将之帽", name_en="Admiral's Hat",
        aliases_zh=["海洋之帽", "海将军帽", "海军帽", "上将之帽"], aliases_en=["admiral hat"],
    ),
    "bow_of_the_sharpshooter": CatalogItem(
        key="bow_of_the_sharpshooter", rmg_id=137, name_zh="神射手之弓", name_en="Bow of the Sharpshooter",
        aliases_zh=["幻影神弓", "神射手弓"],
    ),
    "wizards_well": CatalogItem(
        key="wizards_well", rmg_id=138, name_zh="魔力源泉", name_en="Wizard's Well",
        aliases_zh=["法师之井", "魔水桶"],
    ),
}


# ============================================================
# 特殊地图对象 (Special Objects)
# 这些对象不属于"神器白名单"系统, 而是 RMG 的内置机制.
# 用户能"点"它们, AI 能识别, CLI 给出友好反馈, 但不一定会落到字段动作.
# 详见各项的 note.
# ============================================================

@dataclass(frozen=True)
class SpecialObject:
    """特殊地图对象 (与普通神器/生物的区别: 没有 ID, 由 RMG 内置机制控制)."""
    key: str
    name_zh: str
    name_en: str
    aliases_zh: list[str] = field(default_factory=list)
    aliases_en: list[str] = field(default_factory=list)
    note: str = ""  # 给 CLI 显示用的说明 (例如 "RMG 默认开启, 无需配置")


SPECIAL_OBJECTS: dict[str, SpecialObject] = {
    "grail": SpecialObject(
        key="grail", name_zh="圣杯", name_en="Grail",
        aliases_zh=["圣杯神器", "神圣圣杯"],
        note="RMG 默认开启 (通过方尖碑机制). 无需额外配置.",
    ),
}


def resolve_special(name: str) -> SpecialObject | None:
    """根据任意名字解析特殊对象. 找不到返回 None.

    注: 依赖下面定义的 _normalize, Python 运行时解析符号, 顺序无关.
    """
    if not name:
        return None
    n = _normalize(name)
    for obj in SPECIAL_OBJECTS.values():
        if n == obj.key.lower():
            return obj
        if n == obj.name_zh.lower() or n == obj.name_en.lower():
            return obj
        for alias in obj.aliases_zh:
            if n == alias.lower():
                return obj
        for alias in obj.aliases_en:
            if n == alias.lower():
                return obj
    return None


# ============================================================
# 难度档位 (Difficulty)
# 对应 RMG Zone 表里 "Strength" 列的合法值
# ============================================================

DIFFICULTY_TO_RMG: dict[str, str] = {
    "easy": "weak",
    "normal": "avg",
    "hard": "strong",
}

DIFFICULTY_ALIASES_ZH: dict[str, str] = {
    "简单": "easy", "容易": "easy", "弱": "easy",
    "普通": "normal", "中等": "normal", "正常": "normal", "平均": "normal",
    "困难": "hard", "强": "hard", "强敌": "hard", "硬核": "hard",
}


# ============================================================
# 解析函数 (resolve_*)
# 输入: 用户/AI 给的"任意名字" (可能是规范 key、中英文别名、大小写不一)
# 输出: CatalogItem 或 None
# ============================================================

def _normalize(s: str) -> str:
    """规范化字符串: 小写 + 去首尾空白 + 全角转半角."""
    return s.strip().lower()


def _resolve(name: str, catalog: dict[str, CatalogItem]) -> CatalogItem | None:
    """通用解析: 按 key/中英文标准名/别名查找."""
    if not name:
        return None
    n = _normalize(name)

    for item in catalog.values():
        if n == item.key.lower():
            return item
        if n == item.name_zh.lower() or n == item.name_en.lower():
            return item
        for alias in item.aliases_zh:
            if n == alias.lower():
                return item
        for alias in item.aliases_en:
            if n == alias.lower():
                return item
    return None


def resolve_creature(name: str) -> CatalogItem | None:
    """根据任意名字解析生物. 找不到返回 None."""
    return _resolve(name, CREATURES)


def resolve_artifact(name: str) -> CatalogItem | None:
    """根据任意名字解析神器. 找不到返回 None."""
    return _resolve(name, ARTIFACTS)


def resolve_difficulty(name: str) -> str | None:
    """根据任意名字解析难度.

    Returns:
        规范的 difficulty key ("easy"/"normal"/"hard"), 找不到返回 None
    """
    if not name:
        return None
    n = _normalize(name)
    if n in DIFFICULTY_TO_RMG:
        return n
    if n in DIFFICULTY_ALIASES_ZH:
        return DIFFICULTY_ALIASES_ZH[n]
    en_normalized = {"weak": "easy", "avg": "normal", "average": "normal", "strong": "hard"}
    if n in en_normalized:
        return en_normalized[n]
    return None


def difficulty_to_rmg_value(difficulty_key: str) -> str:
    """把规范 difficulty key 转成 RMG 字段值.

    Raises:
        KeyError: difficulty_key 不在 DIFFICULTY_TO_RMG 中
    """
    return DIFFICULTY_TO_RMG[difficulty_key]


# ============================================================
# 列举所有可点项目 (供 AI prompt 使用)
# ============================================================

def all_creature_names_zh() -> list[str]:
    """返回所有生物的中文标准名 + 别名, 用于喂给 AI prompt."""
    names = []
    for item in CREATURES.values():
        names.append(item.name_zh)
        names.extend(item.aliases_zh)
    return names


def all_artifact_names_zh() -> list[str]:
    """返回所有神器的中文标准名 + 别名, 用于喂给 AI prompt."""
    names = []
    for item in ARTIFACTS.values():
        names.append(item.name_zh)
        names.extend(item.aliases_zh)
    return names


def all_special_names_zh() -> list[str]:
    """返回所有特殊对象的中文标准名 + 别名, 用于喂给 AI prompt."""
    names = []
    for obj in SPECIAL_OBJECTS.values():
        names.append(obj.name_zh)
        names.extend(obj.aliases_zh)
    return names


# ============================================================
# 模糊匹配建议 (用于"未识别"时给用户提示)
# ============================================================

def _zh_jaccard(a: str, b: str) -> float:
    """两个中文字符串的字符 Jaccard 相似度.

    取共同字符数 / 总字符数 (并集). 不区分顺序, 适合中文短词.
    例: "龙骨胫甲" vs "龙父神力" -> {龙} 共有 / {龙骨胫甲父神力} = 1/7 ≈ 0.14
        "金龙" vs "金色巨龙"   -> {金,龙} / {金,色,巨,龙}      = 2/4 = 0.5
    """
    set_a = set(a)
    set_b = set(b)
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union


def suggest_similar(name: str, top_k: int = 3, min_score: float = 0.3) -> list[str]:
    """给一个未识别的名字, 找出 catalog 里最相似的几个建议.

    Args:
        name: 未识别的输入
        top_k: 最多返回几个建议
        min_score: 最低相似度阈值, 低于此值不推荐

    Returns:
        相似度从高到低的标准中文名列表 (可能为空)
    """
    if not name or not name.strip():
        return []

    candidates: list[str] = []
    candidates.extend(all_creature_names_zh())
    candidates.extend(all_artifact_names_zh())
    candidates.extend(all_special_names_zh())

    scored: list[tuple[float, str]] = []
    seen: set[str] = set()
    for cand in candidates:
        if cand in seen:
            continue
        seen.add(cand)
        score = _zh_jaccard(name, cand)
        if score >= min_score:
            scored.append((score, cand))

    scored.sort(key=lambda x: (-x[0], x[1]))
    return [name for _, name in scored[:top_k]]
