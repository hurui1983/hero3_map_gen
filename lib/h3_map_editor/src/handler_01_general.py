#!/usr/bin/env python3

import src.file_io as io

from enum import IntEnum

# The general information of a map is stored as follows:
#
# - Map format           | 4 bytes int
# For HotA only:
#   - HotA version       | 4 bytes int
#   - unknown data       | 1 byte ???
#   - is_arena           | 1 byte bool
#   - unknown data       | 8 bytes ???
#   - allowed difficulties | 1 byte (bits)
# Common fields:
# - has_hero             | 1 byte bool
# - map_size             | 4 bytes int
# - is_two_level         | 1 byte bool
# - name length          | 4 bytes int
# - name                 | X bytes str
# - description length   | 4 bytes int
# - description          | X bytes str
# - difficulty           | 1 byte int
# For AB/SoD/HotA only:
# - level_cap            | 1 byte int

class MapFormat(IntEnum):
    RoE  = 0x0E  # 14
    AB   = 0x15  # 21
    SoD  = 0x1C  # 28
    CHR  = 0x1D  # 29
    HotA = 0x20  # 32
    WoG  = 0x33  # 51

class MapSize(IntEnum):
    S  =  36
    M  =  72
    L  = 108
    XL = 144
    H  = 180
    XH = 216
    G  = 252

class Difficulty(IntEnum):
    Easy       = 0
    Normal     = 1
    Hard       = 2
    Expert     = 3
    Impossible = 4

# Global variable to track current map format for other handlers
current_map_format = None

def parse_general() -> dict:
    global current_map_format

    info = {
        "map_format"         : 0,
        "hota_version"       : 0,
        "hota_data_1"        : b'',
        "hota_data_2"        : b'',
        "name"               : "",
        "description"        : "",
        "map_size"           : 0,
        "has_hero"           : False,
        "is_two_level"       : False,
        "is_arena"           : False,
        "difficulty"         : 0,
        "allowed_difficulty" : [],
        "level_cap"          : 0,
    }

    info["map_format"] = MapFormat(io.read_int(4))
    current_map_format = info["map_format"]

    if info["map_format"] == MapFormat.HotA:
        info["hota_version"] = io.read_int(4)
        # PATCHED: Accept any HotA version (original only supported version 6)
        info["hota_data_1"]        =      io.read_raw(1)
        info["is_arena"]           = bool(io.read_int(1))
        info["hota_data_2"]        =      io.read_raw(8)
        info["allowed_difficulty"] =      io.read_bits(1)

    elif info["map_format"] in (MapFormat.RoE, MapFormat.AB, MapFormat.SoD):
        # RoE/AB/SoD: No HotA-specific header fields
        pass

    else:
        raise NotImplementedError(f"Unsupported map format: {info['map_format']}")

    info["has_hero"]     =       bool(io.read_int(1))
    info["map_size"]     =    MapSize(io.read_int(4))
    info["is_two_level"] =       bool(io.read_int(1))
    info["name"]         =            io.read_str(io.read_int(4))
    info["description"]  =            io.read_str(io.read_int(4))
    info["difficulty"]   = Difficulty(io.read_int(1))

    # level_cap only exists in AB, SoD, and HotA (not in RoE)
    if info["map_format"] in (MapFormat.AB, MapFormat.SoD, MapFormat.HotA):
        info["level_cap"] = io.read_int(1)

    return info

def write_general(info: dict) -> None:
    io.write_int(info["map_format"], 4)

    if info["map_format"] == MapFormat.HotA:
        io.write_int( info["hota_version"], 4)
        io.write_raw( info["hota_data_1"])
        io.write_int( info["is_arena"], 1)
        io.write_raw( info["hota_data_2"])
        io.write_bits(info["allowed_difficulty"])

    io.write_int(    info["has_hero"], 1)
    io.write_int(    info["map_size"], 4)
    io.write_int(    info["is_two_level"], 1)
    io.write_int(io.str_byte_len(info["name"]), 4)
    io.write_str(    info["name"])
    io.write_int(io.str_byte_len(info["description"]), 4)
    io.write_str(    info["description"])
    io.write_int(    info["difficulty"], 1)

    # level_cap only exists in AB, SoD, and HotA (not in RoE)
    if info["map_format"] in (MapFormat.AB, MapFormat.SoD, MapFormat.HotA):
        io.write_int(info["level_cap"], 1)
