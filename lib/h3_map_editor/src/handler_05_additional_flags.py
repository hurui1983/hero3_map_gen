#!/usr/bin/env python3

import src.file_io as io
import src.handler_01_general as h1

# The banned artifacts/spells/skills of a map are stored as follows:
#
# RoE:       Enabled/banned artifacts | 18 bytes (bits)  (128 + 16 = 144 artifacts)
# AB:        Enabled/banned artifacts | 17 bytes (bits)
# SoD:       Enabled/banned artifacts | 18 bytes (bits)
# HotA:      Enabled/banned artifacts | 21 bytes (bits)  (168 artifacts)
#
# All:       Enabled/banned spells    | 9 bytes (bits)
# All:       Enabled/banned skills    | 4 bytes (bits)

def parse_flags() -> dict:
    info = {
        "artifacts": [],
        "spells"   : [],
        "skills"   : []
    }

    map_format = h1.current_map_format

    # Artifact ban flags differ by version
    if map_format == h1.MapFormat.RoE:
        info["artifacts"] = io.read_bits(18)
    elif map_format == h1.MapFormat.AB:
        info["artifacts"] = io.read_bits(17)
    elif map_format == h1.MapFormat.SoD:
        info["artifacts"] = io.read_bits(18)
    else:  # HotA
        info["artifacts"] = io.read_bits(21)

    info["spells"]    = io.read_bits(9)
    info["skills"]    = io.read_bits(4)

    return info

def write_flags(info: dict) -> None:
    io.write_bits(info["artifacts"])
    io.write_bits(info["spells"])
    io.write_bits(info["skills"])
