#!/usr/bin/env python3
"""
测试不同格式地图的加载功能
Test loading maps of different formats (RoE/AB/SoD/HotA)
"""

import sys
from pathlib import Path

# Add lib to path
lib_path = Path(__file__).parent / "lib" / "h3_map_editor"
sys.path.insert(0, str(lib_path))

from gzip import open as gzip_open
import src.file_io as io
import src.handler_01_general as h1
import src.handler_02_players_and_teams as h2
import src.handler_03_conditions as h3
import src.handler_04_heroes as h4
import src.handler_05_additional_flags as h5
import src.handler_06_rumors_and_events as h6
import src.handler_07_terrain as h7
import src.handler_08_objects as h8


def test_map(filename: str) -> bool:
    """Test loading a map file."""
    print(f"\n{'='*50}")
    print(f"Testing: {filename}")
    print('='*50)

    try:
        with gzip_open(filename, 'rb') as io.in_file:
            general = h1.parse_general()
            print(f"Format: {general['map_format']}")
            print(f"Name: {general['name']}")
            print(f"Size: {general['map_size']}")

            player_specs = h2.parse_player_specs()
            print(f"Players: OK ({len(player_specs)} slots)")

            conditions = h3.parse_conditions()
            print(f"Conditions: OK")

            teams = h2.parse_teams()
            print(f"Teams: OK ({teams['amount_of_teams']} teams)")

            start_heroes = h4.parse_starting_heroes(general)
            print(f"Starting Heroes: OK (flags={len(start_heroes['hero_flags'])} bits)")

            ban_flags = h5.parse_flags()
            print(f"Ban Flags: OK (artifacts={len(ban_flags['artifacts'])} bits)")

            rumors = h6.parse_rumors()
            print(f"Rumors: OK ({len(rumors)} rumors)")

            hero_data = h4.parse_hero_data()
            print(f"Hero Data: OK ({len(hero_data)} heroes)")

            terrain = h7.parse_terrain(general)
            print(f"Terrain: OK ({len(terrain)} tiles)")

            object_defs = h8.parse_object_defs()
            print(f"Object Defs: OK ({len(object_defs)} definitions)")

            object_data = h8.parse_object_data(object_defs)
            print(f"Object Data: OK ({len(object_data)} objects)")

            events = h6.parse_events()
            print(f"Events: OK ({len(events)} events)")

            remaining = io.in_file.read()
            print(f"Remaining bytes: {len(remaining)}")

            if len(remaining) > 0:
                print(f"WARNING: {len(remaining)} unread bytes!")
                return False

            print(f"\n✓ SUCCESS: Map parsed completely!")
            return True

    except Exception as e:
        print(f"\n✗ FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Test all available map files."""
    # Find all .h3m files
    map_files = list(Path(".").glob("*.h3m"))

    if not map_files:
        print("No .h3m files found in current directory!")
        return

    print(f"Found {len(map_files)} map file(s)")

    results = {}
    for map_file in map_files:
        results[str(map_file)] = test_map(str(map_file))

    # Summary
    print(f"\n{'='*50}")
    print("SUMMARY")
    print('='*50)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for filename, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {filename}")

    print(f"\nTotal: {passed}/{total} passed")


if __name__ == "__main__":
    main()
