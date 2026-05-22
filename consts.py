"""
HoMM3 / HotA Constants
Immutable IDs for terrain types and towns.
"""

from enum import IntEnum


class Terrain(IntEnum):
    """Terrain type IDs for HoMM3 and HotA."""
    DIRT = 0
    SAND = 1
    GRASS = 2
    SNOW = 3
    SWAMP = 4
    ROUGH = 5
    SUBTERRANEAN = 6
    LAVA = 7
    WATER = 8
    ROCK = 9
    # HotA Exclusive
    HIGHLANDS = 10
    WASTELAND = 11


class Town(IntEnum):
    """Town type IDs for HoMM3 and HotA."""
    CASTLE = 0
    RAMPART = 1
    TOWER = 2
    INFERNO = 3
    NECROPOLIS = 4
    DUNGEON = 5
    STRONGHOLD = 6
    FORTRESS = 7
    CONFLUX = 8
    # HotA Exclusive
    COVE = 9
    FACTORY = 10


class Resource(IntEnum):
    """Resource type IDs."""
    WOOD = 0
    MERCURY = 1
    ORE = 2
    SULFUR = 3
    CRYSTAL = 4
    GEMS = 5
    GOLD = 6


class Creature(IntEnum):
    """Common creature IDs for quick reference."""
    # Castle
    PIKEMAN = 0
    HALBERDIER = 1
    ARCHER = 2
    MARKSMAN = 3
    GRIFFIN = 4
    ROYAL_GRIFFIN = 5
    SWORDSMAN = 6
    CRUSADER = 7
    MONK = 8
    ZEALOT = 9
    CAVALIER = 10
    CHAMPION = 11
    ANGEL = 12
    ARCHANGEL = 13
    # Rampart
    CENTAUR = 14
    DWARF = 16
    WOOD_ELF = 18
    PEGASUS = 20
    DENDROID_GUARD = 22
    UNICORN = 24
    GREEN_DRAGON = 26
    GOLD_DRAGON = 27
    # Tower
    GREMLIN = 28
    STONE_GARGOYLE = 30
    STONE_GOLEM = 32
    MAGE = 34
    GENIE = 36
    NAGA = 38
    GIANT = 40
    TITAN = 41
    # Inferno
    IMP = 42
    GOG = 44
    HELL_HOUND = 46
    DEMON = 48
    PIT_FIEND = 50
    EFREETI = 52
    DEVIL = 54
    ARCH_DEVIL = 55
    # Necropolis
    SKELETON = 56
    WALKING_DEAD = 58
    WIGHT = 60
    VAMPIRE = 62
    LICH = 64
    BLACK_KNIGHT = 66
    BONE_DRAGON = 68
    GHOST_DRAGON = 69
    # Dungeon
    TROGLODYTE = 70
    HARPY = 72
    BEHOLDER = 74
    MEDUSA = 76
    MINOTAUR = 78
    MANTICORE = 80
    RED_DRAGON = 82
    BLACK_DRAGON = 83
    # Stronghold
    GOBLIN = 84
    WOLF_RIDER = 86
    ORC = 88
    OGRE = 90
    ROC = 92
    CYCLOPS = 94
    BEHEMOTH = 96
    ANCIENT_BEHEMOTH = 97
    # Fortress
    GNOLL = 98
    LIZARDMAN = 100
    GORGON = 102
    SERPENT_FLY = 104
    BASILISK = 106
    WYVERN = 108
    HYDRA = 110
    CHAOS_HYDRA = 111
    # Conflux
    PIXIE = 118
    AIR_ELEMENTAL = 112
    EARTH_ELEMENTAL = 113
    FIRE_ELEMENTAL = 114
    WATER_ELEMENTAL = 115
    PSYCHIC_ELEMENTAL = 120
    FIREBIRD = 130
    PHOENIX = 131
    # Neutral
    AZURE_DRAGON = 132
    CRYSTAL_DRAGON = 133
    FAERIE_DRAGON = 134
    RUST_DRAGON = 135


class Disposition(IntEnum):
    """Monster disposition (attitude)."""
    COMPLIANT = 0   # 顺从
    FRIENDLY = 1    # 友好
    AGGRESSIVE = 2  # 攻击
    HOSTILE = 3     # 敌对
    SAVAGE = 4      # 野蛮
