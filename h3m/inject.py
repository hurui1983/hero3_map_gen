"""HotA .h3m 对象注入器 (scan + patch).

策略:
  1. 解 gzip 拿到原始 bytes
  2. 用 ".def" 字符串作为 anchor, 找到 object attributes section 起点
  3. 顺序读 attribute entries 算出 instances section 起点 (= attributes 末尾)
  4. 在 attributes 末尾追加新 entry (object_class + object_number + def 文件名)
  5. 在 instances 开头追加新 instance (引用新 attribute 的 kind 索引)
  6. attributes count + 1, instances count + 1
  7. events 段及后续字节保留, 整体右移
  8. 重新 gzip 写回

  这样我们不需要解析 3448 个 instances 的复杂 type-specific data,
  只要会序列化新追加的 1 个 entry + 1 个 instance.

支持的 HotA 格式: HotA3 (magic 0x20, hota_format1 >= 3 即 HotAv3).
"""
from __future__ import annotations

import gzip
import struct
from dataclasses import dataclass
from pathlib import Path


META_OBJECT_MONSTER_CLASSES = {54, 71, 72, 73, 74, 75, 162, 163, 164}
META_OBJECT_ARTIFACT_CLASSES = {5, 65, 66, 67, 68, 69}


# ============================================================
# Object attribute entry (parse_oa.c)
#   [uint32] def_size
#   [bytes]  def (def_size chars)
#   [6 bytes] passability bitfield
#   [6 bytes] actionability bitfield
#   [uint16]  allowed_landscapes
#   [uint16]  landscape_group
#   [uint32]  object_class
#   [uint32]  object_number  (subclass)
#   [uint8]   object_group  (0 terrain, 1 town, 2 monster, 3 hero, 4 artifact, 5 treasure)
#   [uint8]   is_ground
#   [16 bytes] unknown 0s
# 固定段总 = 6+6+2+2+4+4+1+1+16 = 42 bytes
# ============================================================
OA_FIXED_SIZE = 42


@dataclass(frozen=True)
class AttrSpec:
    """要追加的 object attribute 描述."""
    def_name: bytes           # e.g. b"AVWazur.def"
    passability: bytes        # 6 bytes
    actionability: bytes      # 6 bytes
    allowed_landscapes: int   # uint16 bitfield
    landscape_group: int      # uint16 bitfield
    object_class: int         # uint32, e.g. 54 = Monster, 5 = Artifact
    object_number: int        # uint32, subclass e.g. 132 = Azure Dragon
    object_group: int         # uint8: 2 = Monster, 4 = Artifact
    is_ground: int = 0

    def to_bytes(self) -> bytes:
        assert len(self.passability) == 6 and len(self.actionability) == 6
        return (
            struct.pack("<I", len(self.def_name))
            + self.def_name
            + self.passability
            + self.actionability
            + struct.pack("<HH", self.allowed_landscapes, self.landscape_group)
            + struct.pack("<II", self.object_class, self.object_number)
            + bytes([self.object_group, self.is_ground])
            + b"\x00" * 16
        )


# ============================================================
# Monster object instance (parse_od_monster.c, HotAv3 variant)
# 基础 12 字节 (x, y, z, kind, 5 zeros) + Monster-specific
# ============================================================
def build_monster_instance(
    x: int,
    y: int,
    z: int,
    kind: int,
    count: int = 1,
    disposition: int = 3,  # 3 = hostile (实测原 monster instance 也是 3)
) -> bytes:
    """构造一个 Monster instance 的字节. HotA 1.7+ (HotAv3 + quantityByValue).

    总长 46 bytes. 字节布局通过反向工程实测样本中的 kind=161 Crystal Dragon
    instance 得到, 比 corpus 文档多 2 段字段 (HotA 1.7+ 新增).
    """
    return (
        bytes([x, y, z])
        + struct.pack("<I", kind)
        + b"\x00" * 5  # 5 zero bytes
        # HotA monster header (12-22):
        + struct.pack("<I", 0)  # quest_identifier (实测原 instance 用顺序号, 我们用 0)
        + struct.pack("<H", count)
        + bytes([disposition])
        + bytes([0])  # hasMessage
        + bytes([0])  # neverFlees
        + bytes([0])  # notGrowingTeam
        + b"\x00\x00"  # 2 padding zeros
        # HotAv3 monster join (23-39):
        + struct.pack("<I", 0xFFFFFFFF)  # aggressionExact (default)
        + bytes([1])  # joinOnlyForMoney (实测原 instance 是 1)
        + struct.pack("<I", 50)  # joinPercent (实测原 instance 是 50)
        + struct.pack("<I", 0xFFFFFFFF)  # upgradedStack
        + struct.pack("<I", 0xFFFFFFFF)  # splitStack
        # HotA 1.7+ quantityByValue (40-44):
        + bytes([0])  # quantityMode (0 = use count, 1 = use ai value)
        + struct.pack("<I", 0)  # quantityByAiValue
    )


def build_artifact_instance(x: int, y: int, z: int, kind: int) -> bytes:
    """Artifact instance: 基础 12 字节 + has_guardians=0 (1 字节)."""
    return (
        bytes([x, y, z])
        + struct.pack("<I", kind)
        + b"\x00" * 5
        + bytes([0])  # has_guardians = 0
    )


# ============================================================
# 找 attributes section 起点
# ============================================================
def find_oa_section(data: bytes) -> tuple[int, int]:
    """返回 (oa_count_offset, oa_count). 用 .def anchor 反推."""
    def_first = data.find(b".def")
    if def_first < 0:
        raise ValueError("数据里找不到任何 .def 字符串, 不是有效 .h3m?")
    # 第一个 def 字符串的 def_size 在它的前 4 bytes (uint32 LE = def 字符串总长度)
    for back in range(4, 32):
        spos = def_first + 4 - back
        if spos < 4:
            continue
        size_val = struct.unpack("<I", data[spos - 4:spos])[0]
        if size_val == back:
            count_off = spos - 8
            count = struct.unpack("<I", data[count_off:count_off + 4])[0]
            if 50 < count < 10000:
                return count_off, count
    raise ValueError("无法定位 OA section count")


def find_od_section(data: bytes, oa_count_off: int, oa_count: int) -> tuple[int, int]:
    """顺序解析 oa_count 个 attribute entries, 末尾 = OD count offset."""
    pos = oa_count_off + 4
    for _ in range(oa_count):
        def_size = struct.unpack("<I", data[pos:pos+4])[0]
        if def_size > 200:
            raise ValueError(f"def_size 异常 ({def_size}) at offset {pos}, 解析错位")
        pos += 4 + def_size + OA_FIXED_SIZE
    od_count = struct.unpack("<I", data[pos:pos+4])[0]
    if not (0 < od_count < 100000):
        raise ValueError(f"OD count {od_count} 异常")
    return pos, od_count


# ============================================================
# 主注入函数
# ============================================================
def inject_objects(
    src_path: Path,
    out_path: Path,
    attrs: list[tuple[AttrSpec, bytes]],
) -> dict:
    """注入新对象到 .h3m.

    Args:
        src_path: 输入 .h3m
        out_path: 输出 .h3m
        attrs: 每项是 (AttrSpec, instance_bytes). instance_bytes 由
               build_monster_instance / build_artifact_instance 生成,
               其中 kind 字段必须等于 oa_count + 该项在列表中的索引.

    Returns:
        诊断信息 dict.
    """
    with gzip.open(src_path, "rb") as f:
        data = f.read()

    oa_count_off, oa_count = find_oa_section(data)
    od_count_off, od_count = find_od_section(data, oa_count_off, oa_count)

    info = {
        "src_size_uncompressed": len(data),
        "oa_count_off": oa_count_off,
        "oa_count_before": oa_count,
        "od_count_off_before": od_count_off,
        "od_count_before": od_count,
        "injected": [],
    }

    new_oa_count = oa_count + len(attrs)
    new_od_count = od_count + len(attrs)

    # 构造新数据:
    # [前缀 (含 oa count)] [现有 attrs] [新 attrs] [od count] [新 instances] [现有 instances + events 等]
    new_data = bytearray()
    # 1. header...attributes_count_offset
    new_data += data[:oa_count_off]
    # 2. 新 OA count
    new_data += struct.pack("<I", new_oa_count)
    # 3. 现有 attributes
    new_data += data[oa_count_off + 4:od_count_off]
    # 4. 新 attribute entries
    attr_bytes_list = []
    for spec, _inst in attrs:
        b = spec.to_bytes()
        attr_bytes_list.append(b)
        new_data += b
        info["injected"].append({
            "def": spec.def_name.decode("ascii"),
            "class": spec.object_class,
            "number": spec.object_number,
        })
    # 5. 新 OD count
    new_data += struct.pack("<I", new_od_count)
    # 6. 新 instances (前置)
    for spec, inst in attrs:
        new_data += inst
    # 7. 现有 instances + events 字节级保留
    new_data += data[od_count_off + 4:]

    info["dst_size_uncompressed"] = len(new_data)
    info["delta_bytes"] = len(new_data) - len(data)

    # 8. gzip 重压
    with gzip.open(out_path, "wb", compresslevel=6) as f:
        f.write(bytes(new_data))

    info["dst_size_compressed"] = out_path.stat().st_size
    return info


# ============================================================
# 预设: 常用对象的 AttrSpec
# ============================================================

# 中立 7 级龙 sprite 名 (HoMM3 SoD)
NEUTRAL_DRAGON_SPRITES = {
    132: b"AVWAZUR.def",    # 圣龙 Azure Dragon
    133: b"AVWCDRG.def",    # 水晶龙 Crystal Dragon (HotA 用 AVWCDRG)
    134: b"AVWFDRG.def",    # 仙龙 Faerie Dragon
    135: b"AVWRUST.def",    # 锈龙 Rust Dragon
}

COMBO_ARTIFACT_SPRITES = {
    128: b"AVA0128.def",    # 末日之刃 Armageddon's Blade
    129: b"AVA0129.def",    # 天使联盟 Angelic Alliance
}


def make_neutral_dragon_spec(creature_id: int, sprite: bytes | None = None) -> AttrSpec:
    """构造一个中立龙 attribute spec (class=54 Monster)."""
    sprite = sprite or NEUTRAL_DRAGON_SPRITES.get(creature_id, f"AVWmrnd0.def".encode())
    # passability: 6 bytes 全 0xFF (全部 passable 除了 actionable tile)
    # actionability: 怪兵占 1 tile (右下角), 其他 0
    # 这是猜测值, 实测 attributes section 里 Monster 通常用以下模式
    return AttrSpec(
        def_name=sprite,
        passability=b"\xff\xff\xff\xff\xff\xbf",   # all pass except bottom-right
        actionability=b"\x00\x00\x00\x00\x00\x40", # bottom-right action
        allowed_landscapes=0x017F,  # all terrains except water/rock
        landscape_group=0x017F,
        object_class=54,
        object_number=creature_id,
        object_group=2,  # 2 = monster (editor group)
        is_ground=0,
    )


def make_artifact_spec(artifact_id: int, sprite: bytes | None = None) -> AttrSpec:
    """构造一个 artifact attribute spec (class=5)."""
    sprite = sprite or COMBO_ARTIFACT_SPRITES.get(
        artifact_id, f"AVA{artifact_id:04d}.def".encode()
    )
    return AttrSpec(
        def_name=sprite,
        passability=b"\xff\xff\xff\xff\xff\xbf",
        actionability=b"\x00\x00\x00\x00\x00\x40",
        allowed_landscapes=0x017F,
        landscape_group=0x017F,
        object_class=5,
        object_number=artifact_id,
        object_group=4,  # 4 = artifact
        is_ground=0,
    )
