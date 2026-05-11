"""
Layer 4 - HotA RMG 模板 (.h3t) 写入器

策略:
  以现有的 Jebus Cross.h3t 为骨架, 由 order_to_rmg 给出"字段动作", 应用后写出.

提供两种入口:
  - generate_basic(name, ...): 程序化指定字段, 用于离线测试 / 直接调用
  - generate_from_order(order): 从 ValidatedOrder (CLI 主流程使用)

字段索引常量定义在 order_to_rmg, 这里仅引用, 避免双份定义漂移.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import order_to_rmg as o2r

GAME_DIR = Path("/Applications/英雄无敌3：二合一.app/Contents/drive_c/game")
RMG_DIR = GAME_DIR / "HotA_RMGTemplates"
SKELETON_TEMPLATE = RMG_DIR / "Jebus Cross.h3t"

AI_PREFIX = "ai_"
FIRST_DATA_ROW = 3

# HotA 是 Windows 简体中文应用, 模板/地图里的中文用 GBK (CP936) 编码.
# 我们写出 .h3t 时必须用同一编码, 否则游戏内中文会变乱码.
# 读骨架时也用 GBK (Jebus Cross 没中文, ASCII 是 GBK 子集, 兼容).
TEMPLATE_ENCODING = "gbk"

MAP_SIZE_S = 36
MAP_SIZE_M = 72
MAP_SIZE_L = 108
MAP_SIZE_XL = 144


def _read_skeleton() -> list[list[str]]:
    """读取骨架模板并解析为二维表格 (行 x 列). 保留末尾空行."""
    raw = SKELETON_TEMPLATE.read_bytes().decode(TEMPLATE_ENCODING)
    lines = raw.split("\r\n")
    return [line.split("\t") for line in lines]


def _serialize(table: list[list[str]]) -> bytes:
    """序列化回 TAB 分隔 + CRLF 行尾的字节, 用 GBK 编码."""
    text = "\r\n".join("\t".join(row) for row in table)
    return text.encode(TEMPLATE_ENCODING)


def _ensure_filename(filename: str) -> str:
    if not filename.startswith(AI_PREFIX):
        filename = AI_PREFIX + filename
    if not filename.endswith(".h3t"):
        filename += ".h3t"
    return filename


def _write_template(content: bytes, filename: str) -> Path:
    out_path = RMG_DIR / _ensure_filename(filename)
    out_path.write_bytes(content)
    return out_path


# ============================================================
# 直接 API
# ============================================================

def generate_basic(
    name: str,
    filename: str,
    description: str = "",
    min_size: int = MAP_SIZE_M,
    max_size: int = MAP_SIZE_L,
) -> Path:
    """生成一个基础参数化的模板 (用于直接调用 / 离线测试).

    Args:
        name: 显示名称 (同时用于 Pack name 和 Map name)
        filename: 输出文件名 (自动加 ai_ 前缀 + .h3t 后缀)
        description: 地图描述
        min_size: 最小地图边长
        max_size: 最大地图边长

    Returns:
        生成的 .h3t 文件路径
    """
    if min_size > max_size:
        raise ValueError(f"min_size ({min_size}) 不能大于 max_size ({max_size})")

    table = _read_skeleton()
    data_row = table[FIRST_DATA_ROW]
    data_row[o2r.COL_PACK_NAME] = name
    data_row[o2r.COL_PACK_DESCRIPTION] = description
    data_row[o2r.COL_MAP_NAME] = name
    data_row[o2r.COL_MAP_MIN_SIZE] = str(min_size)
    data_row[o2r.COL_MAP_MAX_SIZE] = str(max_size)
    return _write_template(_serialize(table), filename)


# ============================================================
# 从 ValidatedOrder 生成
# ============================================================

def derive_filename_from_order(order: o2r.ValidatedOrder) -> str:
    """从 order 内容衍生一个有信息量的文件名.

    格式: ai_<关键字片段>_<HHMM>.h3t
    例: ai_金龙_末日之刃_2342.h3t

    关键字片段最多取 2 个生物 + 2 个神器 + 难度.
    """
    parts: list[str] = []
    for c in order.creatures[:2]:
        parts.append(c.name_zh)
    for a in order.artifacts[:2]:
        parts.append(a.name_zh)
    if order.difficulty:
        parts.append(order.difficulty)
    if not parts:
        parts.append("template")

    timestamp = time.strftime("%H%M")
    raw = "_".join(parts) + "_" + timestamp
    safe = re.sub(r"[^\w\u4e00-\u9fff]+", "_", raw)
    return safe


def derive_name_from_order(order: o2r.ValidatedOrder) -> str:
    """从 order 衍生一个游戏内显示名 (中文友好)."""
    if order.name:
        return order.name
    parts: list[str] = ["AI"]
    for c in order.creatures[:2]:
        parts.append(c.name_zh)
    for a in order.artifacts[:2]:
        parts.append(a.name_zh)
    if order.difficulty:
        zh = {"easy": "简单", "normal": "普通", "hard": "困难"}
        parts.append(zh.get(order.difficulty, order.difficulty))
    if len(parts) == 1:
        parts.append("默认模板")
    return " ".join(parts)


def generate_from_order(order: o2r.ValidatedOrder, filename: str | None = None) -> Path:
    """根据已校验的 ValidatedOrder 生成 .h3t.

    Args:
        order: 已经过白名单校验的点菜
        filename: 可选, 不给则从 order 自动衍生

    Returns:
        生成的 .h3t 文件路径
    """
    if order.name is None:
        order = o2r.ValidatedOrder(
            creatures=order.creatures, artifacts=order.artifacts,
            difficulty=order.difficulty, players=order.players,
            map_size=order.map_size, description=order.description,
            name=derive_name_from_order(order),
        )

    table = _read_skeleton()
    actions = o2r.build_actions(order, table, first_data_row=FIRST_DATA_ROW)
    o2r.apply_actions(table, actions)

    if filename is None:
        filename = derive_filename_from_order(order)
    return _write_template(_serialize(table), filename)


# ============================================================
# 管理工具
# ============================================================

def list_ai_templates() -> list[Path]:
    return sorted(RMG_DIR.glob(f"{AI_PREFIX}*.h3t"))


def clean_ai_templates() -> int:
    count = 0
    for p in list_ai_templates():
        p.unlink()
        count += 1
    return count


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        n = clean_ai_templates()
        print(f"已删除 {n} 个 AI 模板")
        sys.exit(0)

    if len(sys.argv) > 1 and sys.argv[1] == "list":
        for p in list_ai_templates():
            print(f"  - {p.name}")
        sys.exit(0)

    out = generate_basic(
        name="AI Demo Large",
        filename="demo_large",
        description="AI 生成测试: 强制大地图 (108x108)",
        min_size=MAP_SIZE_L,
        max_size=MAP_SIZE_L,
    )
    print(f"已生成: {out}")

    print("\n当前所有 AI 模板:")
    for p in list_ai_templates():
        print(f"  - {p.name}")
