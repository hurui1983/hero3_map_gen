"""creature_id (= catalog rmg_id = h3m Monster subtype) -> 冒险地图 sprite def 名.

来源: 从游戏 random_maps/ 里 173 种已存在的 Monster object_def 收集到的真实
sprite 名 (HotA 自己写出来的, 权威). 仅 azure_dragon(132) 在已生成地图里没出现过,
取自 PoC 实测可用值 AVWazur.def.

注入 Monster 时:
  - object_number (subtype) = creature_id  -> 决定实际生物
  - object_def sprite       = 这里的 def   -> 决定冒险地图贴图
两者必须配套, sprite 错了 HotA 会显示错图或找不到贴图.
"""
from __future__ import annotations

# catalog 全部 22 个生物的权威 sprite (creature_id -> def 名).
CREATURE_SPRITES: dict[int, str] = {
    12:  "AvWAngl.def",   # 天使 Angel
    13:  "AvWArch.def",   # 大天使 Archangel
    26:  "AVWdrag0.def",  # 绿龙 Green Dragon
    27:  "AVWdrax0.def",  # 金龙 Gold Dragon
    41:  "AVWtitx0.def",  # 泰坦 Titan
    54:  "AVWdevl0.def",  # 恶魔 Devil
    55:  "AVWdevx0.def",  # 大恶魔 Arch Devil
    64:  "AVWlich0.def",  # 巫妖 Lich
    68:  "AVWbone0.def",  # 骨龙 Bone Dragon
    69:  "AVWbonx0.def",  # 鬼龙 Ghost Dragon
    82:  "AvWRDrg.def",   # 红龙 Red Dragon
    83:  "AVWddrx0.def",  # 黑龙 Black Dragon
    96:  "AVWbhmt0.def",  # 比蒙 Behemoth
    97:  "AVWbhmx0.def",  # 远古比蒙 Ancient Behemoth
    110: "AvWHydr.def",   # 九头蛇 Hydra
    111: "AVWhydx0.def",  # 混乱九头蛇 Chaos Hydra
    130: "AVWfbird.def",  # 火鸟 Firebird
    131: "AVWphx.def",    # 凤凰 Phoenix
    132: "AVWazur.def",   # 圣龙 Azure Dragon  (PoC 实测值)
    133: "AVWcdrg.def",   # 水晶龙 Crystal Dragon
    134: "AVWfdrg.def",   # 仙龙 Faerie Dragon
    135: "AVWrust.def",   # 锈龙 Rust Dragon
}


def creature_sprite(creature_id: int) -> str | None:
    """返回生物的 sprite def 名, 未知返回 None (由调用方决定如何 fail)."""
    return CREATURE_SPRITES.get(creature_id)
