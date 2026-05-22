#!/usr/bin/env python3

import src.file_io as io
import src.handler_01_general as h1
import data.heroes as hd
from data.objects import Town

from enum import IntEnum

# The player specs of a map are stored as follows:
#
# For all 8 players:
# - Playable as human     | 1 byte bool
# - Playable as AI        | 1 byte bool
# - AI behaviour          | 1 byte int
# - Customized alignments | 1 byte bool (AB/SoD/HotA only)
# - Allowed alignments    | 1 byte (RoE) or 2 bytes (AB/SoD/HotA) (bits)
# - Random alignment      | 1 byte bool
# - Has main town         | 1 byte bool
#
# IF has_main_town:
# --- Generate hero       | 1 byte bool (AB/SoD/HotA only)
# --- Town type           | 1 byte int
# --- Town coordinates    | 3 bytes int (x, y, z)
#
# - Has random hero       | 1 byte bool
# - Starting hero ID      | 1 byte int
#
# IF starting_hero_id != 255:
# --- Hero face           | 1 byte int
# --- Hero name length    | 4 bytes int
# --- Hero name           | X bytes str
# --- unknown data        | 1 byte ???
# --- Starting heroes     | 4 bytes int
#
# --- FOREACH starting hero:
# ----- Hero ID           | 1 byte int
# ----- Hero name length  | 4 bytes int
# ----- Hero name         | X bytes str
#
# ELSE:
# --- unknown data        | 1 byte ???
# --- Placeholder heroes  | 4 bytes int
#
# --- FOREACH placeholder hero:
# ----- Placeholder ID    | 5 bytes int

# The teams of a map are stored as follows:
#
# - Amount of teams | 1 byte int
#
# IF amount != 0:
# --- Player 1 team | 1 byte int
# --- ...
# --- Player 8 team | 1 byte int

def parse_player_specs() -> list:
    specs = []
    map_format = h1.current_map_format

    for _ in range(8):
        info = {
            "playability_human"    : False,
            "playability_ai"       : False,
            "ai_behavior"          : 0,
            "alignments_customized": False,
            "alignments_allowed"   : [],
            "alignment_is_random"  : False,
            "has_main_town"        : False,
            "generate_hero"        : False,
            "town_type"            : 0,
            "town_coords"          : [0, 0, 0],
            "has_random_hero"      : False,
            "starting_hero_id"     : 255,
            "starting_hero_face"   : 255,
            "starting_hero_name"   : "",
            "available_heroes"     : [],
            "garbage_byte"         : b'\x00',
            "placeholder_heroes"   : []
        }

        info["playability_human"] = bool(io.read_int(1))
        info["playability_ai"]    = bool(io.read_int(1))
        info["ai_behavior"]       =      io.read_int(1)

        # RoE doesn't have customized_alignments field
        if map_format in (h1.MapFormat.AB, h1.MapFormat.SoD, h1.MapFormat.HotA):
            info["alignments_customized"] = bool(io.read_int(1))

        # RoE: 1 byte (8 factions), AB/SoD/HotA: 2 bytes (9+ factions including Conflux)
        if map_format == h1.MapFormat.RoE:
            info["alignments_allowed"] = io.read_bits(1)
        else:
            info["alignments_allowed"] = io.read_bits(2)

        info["alignment_is_random"] = bool(io.read_int(1))
        info["has_main_town"]       = bool(io.read_int(1))

        if info["has_main_town"]:
            # RoE doesn't have generate_hero field
            if map_format in (h1.MapFormat.AB, h1.MapFormat.SoD, h1.MapFormat.HotA):
                info["generate_hero"] = bool(io.read_int(1))

            info["town_type"]      = Town(io.read_int(1))
            info["town_coords"][0] =      io.read_int(1)
            info["town_coords"][1] =      io.read_int(1)
            info["town_coords"][2] =      io.read_int(1)

        info["has_random_hero"]  =  bool(io.read_int(1))
        info["starting_hero_id"] = hd.ID(io.read_int(1))

        if info["starting_hero_id"] != hd.ID.Default:
            info["starting_hero_face"] = hd.ID(io.read_int(1))
            info["starting_hero_name"] = io.read_str(io.read_int(4))

            # RoE doesn't have garbage_byte and available_heroes list
            if map_format in (h1.MapFormat.AB, h1.MapFormat.SoD, h1.MapFormat.HotA):
                info["garbage_byte"]       = io.read_raw(1)

                for _ in range(io.read_int(4)):
                    hero = {}
                    hero["id"]   = hd.ID(io.read_int(1))
                    hero["name"] = io.read_str(io.read_int(4))
                    info["available_heroes"].append(hero)

        else:
            # RoE doesn't have placeholder heroes section
            if map_format in (h1.MapFormat.AB, h1.MapFormat.SoD, h1.MapFormat.HotA):
                io.seek(1)
                for _ in range(io.read_int(4)): # Amount of placeholder heroes
                    info["placeholder_heroes"].append(hd.ID(io.read_int(5)))

        specs.append(info)

    return specs

def write_player_specs(specs: list) -> None:
    map_format = h1.current_map_format

    for info in specs:
        io.write_int(info["playability_human"], 1)
        io.write_int(info["playability_ai"], 1)
        io.write_int(info["ai_behavior"], 1)

        # RoE doesn't have customized_alignments field
        if map_format in (h1.MapFormat.AB, h1.MapFormat.SoD, h1.MapFormat.HotA):
            io.write_int(info["alignments_customized"], 1)

        io.write_bits(info["alignments_allowed"])
        io.write_int(info["alignment_is_random"], 1)
        io.write_int(info["has_main_town"], 1)

        if info["has_main_town"]:
            # RoE doesn't have generate_hero field
            if map_format in (h1.MapFormat.AB, h1.MapFormat.SoD, h1.MapFormat.HotA):
                io.write_int(info["generate_hero"], 1)

            io.write_int(info["town_type"], 1)
            io.write_int(info["town_coords"][0], 1)
            io.write_int(info["town_coords"][1], 1)
            io.write_int(info["town_coords"][2], 1)

        io.write_int(info["has_random_hero"], 1)
        io.write_int(info["starting_hero_id"], 1)

        if info["starting_hero_id"] != 255:
            io.write_int(    info["starting_hero_face"], 1)
            io.write_int(io.str_byte_len(info["starting_hero_name"]), 4)
            io.write_str(    info["starting_hero_name"])

            # RoE doesn't have garbage_byte and available_heroes list
            if map_format in (h1.MapFormat.AB, h1.MapFormat.SoD, h1.MapFormat.HotA):
                io.write_raw(    info["garbage_byte"])
                io.write_int(len(info["available_heroes"]), 4)

                for hero in info["available_heroes"]:
                    io.write_int(    hero["id"], 1)
                    io.write_int(io.str_byte_len(hero["name"]), 4)
                    io.write_str(    hero["name"])
        else:
            # RoE doesn't have placeholder heroes section
            if map_format in (h1.MapFormat.AB, h1.MapFormat.SoD, h1.MapFormat.HotA):
                io.write_int(0, 1)
                io.write_int(len(info["placeholder_heroes"]), 4)

                for hero in info["placeholder_heroes"]:
                    io.write_int(hero, 5)

def parse_teams() -> dict:
    info = {
        "amount_of_teams": 0,
        "Player1": 0,
        "Player2": 0,
        "Player3": 0,
        "Player4": 0,
        "Player5": 0,
        "Player6": 0,
        "Player7": 0,
        "Player8": 0
    }

    info["amount_of_teams"] = io.read_int(1)

    if info["amount_of_teams"] != 0:
        info["Player1"] = io.read_int(1)
        info["Player2"] = io.read_int(1)
        info["Player3"] = io.read_int(1)
        info["Player4"] = io.read_int(1)
        info["Player5"] = io.read_int(1)
        info["Player6"] = io.read_int(1)
        info["Player7"] = io.read_int(1)
        info["Player8"] = io.read_int(1)

    return info

def write_teams(info: dict) -> None:
    io.write_int(info["amount_of_teams"], 1)

    if info["amount_of_teams"] != 0:
        io.write_int(info["Player1"], 1)
        io.write_int(info["Player2"], 1)
        io.write_int(info["Player3"], 1)
        io.write_int(info["Player4"], 1)
        io.write_int(info["Player5"], 1)
        io.write_int(info["Player6"], 1)
        io.write_int(info["Player7"], 1)
        io.write_int(info["Player8"], 1)
