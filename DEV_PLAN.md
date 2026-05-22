请分析这个 GitHub 仓库：https://github.com/Shakajiub/h3_map_editor


Execution Roadmap
Phase 1: Infrastructure & Patching (Critical)
Objective: Setup environment and bypass HotA version checks.

Initialize project directory homm3-ai-agent.

Clone https://github.com/Shakajiub/h3_map_editor.git into lib/.

Create lib/__init__.py to make it a package.

PATCHING ACTION:

Locate lib/h3_map_editor/map_model.py.

Find the _read_header method.

Comment out the assertion line: assert self.version == ... or similar.

Reason: HotA 1.7.2 uses a newer version header that the library rejects by default. We must bypass this to prevent crashes.

Phase 2: The Semantic Layer
Objective: Create the vocabulary and toolset for the AI.

Task 2.1: Create consts.py Define the immutable IDs for HoMM3.

Terrain IDs:

Dirt=0, Sand=1, Grass=2, Snow=3, Swamp=4, Rough=5, Subterranean=6, Lava=7, Water=8, Rock=9.

HotA Exclusive: Highlands=10, Wasteland=11.

Town IDs:

Castle=0, Rampart=1, Tower=2, Inferno=3, Necropolis=4, Dungeon=5, Stronghold=6, Fortress=7, Conflux=8.

HotA Exclusive: Cove=9. (Note: Factory ID needs verification, skip for MVP).

Task 2.2: Create agent.py Implement the MapAgent class with the following simplified API:

__init__(self, map_path): Loads the map.

get_map_info(self): Returns a dict with name, description, size, and version.

fill_terrain(self, x1, y1, x2, y2, terrain_id): Fills a rectangular area on the surface level (level 0).

Logic: Loop through x and y, access self.model.map_levels[0].tiles[x][y], set .terrain_type.

save(self, output_path): Saves the binary file.

Phase 3: Validation (The MVP Run)
Objective: Prove the loop works.

Create usage_demo.py.

Import MapAgent and consts.

Load base.h3m.

Print map info.

Change a 10x10 block at (0,0) to Terrain.WASTELAND (ID 11).

Save as result_mvp.h3m.

User Action: User will manually check result_mvp.h3m in the game editor.

5. Domain Knowledge (For Claude Context)
Coordinate System: (0,0) is Top-Left.

Map Levels: map_levels[0] is Surface, map_levels[1] is Underground.

HotA Compatibility: The library is designed for SoD (Shadow of Death). HotA maps have extra bytes at the end of some structures. If the parser crashes on reading objects, we strictly focus on Terrain for the MVP, as terrain data structure is identical.

Instruction to Claude Code: Start by executing Phase 1. Clone the repo and apply the patch immediately. Confirm when done.