#!/usr/bin/env python3
"""
Phase 3: Validation - The MVP Run
Demonstrates the MapAgent API by loading a map, modifying terrain, and saving.
"""

from agent import MapAgent
from consts import Terrain


def main():
    # 1. Load the base map
    print("Loading base.h3m...")
    agent = MapAgent("base.h3m")

    # 2. Print map info
    info = agent.get_map_info()
    print("\n=== Map Info ===")
    print(f"Name: {info['name']}")
    print(f"Description: {info['description']}")
    print(f"Size: {info['size']}x{info['size']}")
    print(f"Format: {info['map_format']}")
    print(f"HotA Version: {info['hota_version']}")
    print(f"Two Levels: {info['is_two_level']}")

    # 3. Modify terrain: Change a 10x10 block at (0,0) to WASTELAND
    print("\n=== Modifying Terrain ===")
    print("Filling 10x10 area at (0,0) with WASTELAND terrain...")
    agent.fill_terrain(0, 0, 9, 9, Terrain.WASTELAND)

    # 4. Save the modified map
    output_path = "result_mvp.h3m"
    print(f"\nSaving to {output_path}...")
    agent.save(output_path)

    print("\n=== Done! ===")
    print(f"Please open {output_path} in the HoMM3 map editor to verify the changes.")


if __name__ == "__main__":
    main()
