"""
Layer 3 - Order -> RMG 字段修改

输入: 已校验的 Order (Layer 2 输出)
输出: 一个 list of "字段修改动作", 由 template_writer (Layer 4) 应用到表格上.

设计原则:
  - 这一层不读写文件, 不依赖具体模板的内容
  - 只产出"动作": 改第 N 行第 M 列为某值
  - 行的语义 (是 Zone 行还是 Connection 行) 由这一层根据通用列名判断
  - 初版只支持 difficulty (改所有 Zone 行的 Strength 列)
"""

from __future__ import annotations

from dataclasses import dataclass

import catalog


# ============================================================
# 表格列索引常量
# 来源: 直接从 Jebus Cross.h3t 第 3 行 (索引 2) 表头观察得到
# 这些索引在 HotA 的 .h3t 表头里是固定的 (跨模板一致)
# ============================================================

COL_PACK_NAME = 7
COL_PACK_DESCRIPTION = 8
COL_MAP_NAME = 15
COL_MAP_MIN_SIZE = 16
COL_MAP_MAX_SIZE = 17
COL_MAP_ARTIFACTS = 18    # 全图允许/禁止/必出的神器列表, 例: "+128 -72"
COL_MAP_OBJECTS = 22      # 全图对象列表 (圣杯等), 例: "+95 0 d d d 3"

COL_ZONE_ID = 28          # Zone 数据行的判别字段: 非空即为 Zone 行
COL_ZONE_STRENGTH = 84    # Zone 怪物强度: weak / avg / strong

# 玩家数控制 (HotA RMG): 同时存在于 Zone 段 (col 34~37) 和 Connections 段 (col 134~137).
# 我们只动 "total" 范围 (总玩家数), human 范围保持 [1, total] 让用户在游戏 UI 自由调.
COL_ZONE_MIN_TOTAL = 36
COL_ZONE_MAX_TOTAL = 37
COL_ZONE_MIN_HUMAN = 34
COL_ZONE_MAX_HUMAN = 35
COL_CONN_MIN_TOTAL = 136
COL_CONN_MAX_TOTAL = 137
COL_CONN_MIN_HUMAN = 134
COL_CONN_MAX_HUMAN = 135


# ============================================================
# Order 数据类 (校验后)
# ============================================================

@dataclass(frozen=True)
class ValidatedOrder:
    """白名单校验后的点菜.

    生物/神器存的是 CatalogItem (已确认在词典内).
    difficulty 存的是规范 key ("easy"/"normal"/"hard"), 已确认合法.
    """
    creatures: list[catalog.CatalogItem]
    artifacts: list[catalog.CatalogItem]
    difficulty: str | None      # "easy" / "normal" / "hard" / None
    players: int | None
    map_size: str | None        # "S" / "M" / "L" / "XL" / None
    description: str | None
    name: str | None = None     # 模板显示名 (可由 CLI 自动生成)


# ============================================================
# 字段动作 (action)
# ============================================================

@dataclass(frozen=True)
class CellAction:
    """对表格单元格的一次写操作."""
    row: int
    col: int
    value: str
    reason: str  # 给日志用, 解释为什么改这个字段


# ============================================================
# 行类型判别
# ============================================================

def is_zone_row(row: list[str]) -> bool:
    """判断一个数据行是不是 Zone 数据行 (而非纯 Connection 行).

    规则: Id 列 (索引 COL_ZONE_ID) 非空字符串 = Zone 行.
    """
    if COL_ZONE_ID >= len(row):
        return False
    return bool(row[COL_ZONE_ID].strip())


# ============================================================
# 动作生成
# ============================================================

def build_actions(
    order: ValidatedOrder,
    table: list[list[str]],
    first_data_row: int = 3,
) -> list[CellAction]:
    """根据 ValidatedOrder 生成对 table 的修改动作列表.

    Args:
        order: 已校验的点菜
        table: 由 template_writer 解析出的二维表格 (行 x 列)
        first_data_row: 数据起始行 (前 3 行是表头)

    Returns:
        修改动作列表. 调用方按顺序应用即可.
    """
    actions: list[CellAction] = []

    # ---- 模板名 / 描述 (落到 Pack/Map 字段, 只改 first_data_row 那一行) ----
    if order.name:
        actions.append(CellAction(first_data_row, COL_PACK_NAME, order.name,
                                  f"模板 Pack 名 -> {order.name!r}"))
        actions.append(CellAction(first_data_row, COL_MAP_NAME, order.name,
                                  f"模板 Map 名 -> {order.name!r}"))
    if order.description:
        actions.append(CellAction(first_data_row, COL_PACK_DESCRIPTION, order.description,
                                  f"模板描述 -> {order.description!r}"))

    # ---- map_size: 当前骨架 (Jebus Cross) 是 5 zone 设计, 仅 L/XL 能容纳.
    # 把 min/max size 覆盖成用户指定值会出现 "M 容不下 5 zone" 这一类不可加载模板.
    # 在没有按尺寸分骨架前, 不写 size 字段, 由骨架原值决定可选尺寸.
    # order.map_size 仍保留以供未来按尺寸路由不同骨架.

    # ---- difficulty: 改所有 Zone 行的 Strength 列 ----
    if order.difficulty:
        rmg_strength = catalog.difficulty_to_rmg_value(order.difficulty)
        for row_idx in range(first_data_row, len(table)):
            if is_zone_row(table[row_idx]):
                actions.append(CellAction(row_idx, COL_ZONE_STRENGTH, rmg_strength,
                                          f"Zone 难度 -> {rmg_strength}"))

    # ---- players: 不写入 player 字段 ----
    # 实验结论: 把 Jebus Cross 骨架的 (min_human=1, max_human=4, min_total=2, max_total=4)
    # 改成 (1, 4, 4, 4) 强锁 4 人 -> HotA 拒绝创建. 系统模板里没有任何
    # "四值全相等" 的写法 (Skirmish(M) 是 1/2 2/2, mt_Antares 是 1/4 1/4,
    # Jebus Cross 是 1/4 2/4), 说明这种组合 RMG 不接受.
    # 骨架本来就支持 2-4 玩家, 用户在游戏 UI 自己选玩家数即可.
    # order.players 仍保留, 供未来按玩家数路由不同骨架.

    # ---- artifacts: 必出. 写到 Map.Artifacts (col 18), 语法 "+ID +ID ..."
    # HotA RMG 文档: + 表示强制出现, - 表示禁止出现, 空格分隔.
    # 所有神器 (含组合神器, 如末日之刃 ID=128) 都用同一套全局 RMG ID,
    # 不需要区分 col 18 (Artifacts) 和 col 19 (Combo Arts):
    #   - col 18 接受任何 artifact ID, 强制保证它出现在地图上
    #   - col 19 是另一套独立机制, 控制"组合神器的组件强制刷出", 当前不需要
    if order.artifacts:
        existing = (table[first_data_row][COL_MAP_ARTIFACTS]
                    if COL_MAP_ARTIFACTS < len(table[first_data_row]) else "").strip()
        new_tokens = [f"+{a.rmg_id}" for a in order.artifacts]
        merged = " ".join([existing] + new_tokens) if existing else " ".join(new_tokens)
        actions.append(CellAction(first_data_row, COL_MAP_ARTIFACTS, merged,
                                  f"必出神器 -> {[a.name_zh for a in order.artifacts]}"))

    # ---- creatures: HotA RMG 没有"指定具体生物 ID 必出"机制 ----
    # 生物是过程生成的, 由 zone strength + monsters disposition 决定刷什么.
    # _validate 已在 [2/3] 段输出 [NOTE], 这里不生成任何 action.

    # ---- specials (圣杯): RMG 默认通过方尖碑机制保证, 不需要修改字段 ----
    # 见 catalog.SPECIAL_OBJECTS["grail"].note.

    return actions


def apply_actions(table: list[list[str]], actions: list[CellAction]) -> None:
    """就地应用 action 到 table.

    Raises:
        IndexError: action 引用的 row/col 越界
    """
    for a in actions:
        if a.row >= len(table):
            raise IndexError(f"行越界: action.row={a.row}, table 共 {len(table)} 行")
        row = table[a.row]
        if a.col >= len(row):
            raise IndexError(f"列越界: action.col={a.col}, 第 {a.row} 行共 {len(row)} 列")
        row[a.col] = a.value
