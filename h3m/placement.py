"""智能选址: 在已读出的地图上为 N 个新对象挑选坐标.

约束 (一个候选 tile 必须全部满足):
  1. 在地表 (z=0), 且离地图边界 >= MARGIN (大对象 sprite 向左上延伸, 留够余量)
  2. 该 tile 可通行 (非水/岩) 且未被已有对象占用
  3. 其 3x3 邻域全部可通行且未占用 (开阔地, 确保英雄能走到、不卡在缝里)

在所有候选里用"最远点贪心"挑 N 个, 使它们尽量分散 (互不重叠 + 分布在地图各处,
方便玩家在不同区域都能拿到). 候选不足 N 个时抛错, 不硬塞.

注: 新注入的怪兵/神器都是 1x1 footprint, anchor 即落点, 所以"3x3 开阔"足够安全.
"""
from __future__ import annotations

import random
from collections import deque

from .reader import MapData

MARGIN = 4               # 离边界的最小格数
NEIGHBORHOOD = 1         # 3x3 = 半径 1 的开阔检查


def _main_reachable(m: MapData, z: int = 0) -> list[list[bool]]:
    """返回 reachable[y][x]: 是否属于"玩家可达主区".

    可达定义: 地形可通行 且 不被静态对象(非怪物)阻挡, 4 邻接连通.
    怪物=守军视为可打通, 不切断连通性. 取最大连通分量作为主区 —— 被山脉/
    障碍完全围死的孤立空地会被排除, 从根上杜绝"对象落在英雄走不到的点".
    """
    W = m.width
    pas = m.passable[z]
    blocked = m.occupied_static[z] if m.occupied_static else None

    def walkable(x, y):
        if not pas[y][x]:
            return False
        return not (blocked and blocked[y][x])

    comp = [[-1] * W for _ in range(W)]
    sizes: list[int] = []
    for sy in range(W):
        for sx in range(W):
            if comp[sy][sx] != -1 or not walkable(sx, sy):
                continue
            cid = len(sizes)
            q = deque([(sx, sy)])
            comp[sy][sx] = cid
            n = 0
            while q:
                x, y = q.popleft()
                n += 1
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W and 0 <= ny < W and comp[ny][nx] == -1 and walkable(nx, ny):
                        comp[ny][nx] = cid
                        q.append((nx, ny))
            sizes.append(n)

    if not sizes:
        return [[False] * W for _ in range(W)]
    main = sizes.index(max(sizes))
    return [[comp[y][x] == main for x in range(W)] for y in range(W)]


def _candidates(m: MapData, z: int = 0) -> list[tuple[int, int]]:
    W = m.width
    pas = m.passable[z]
    occ = m.occupied[z]
    reachable = _main_reachable(m, z)
    out: list[tuple[int, int]] = []
    r = NEIGHBORHOOD
    for y in range(MARGIN, W - MARGIN):
        for x in range(MARGIN, W - MARGIN):
            if not reachable[y][x]:        # 必须在玩家可达主区
                continue
            ok = True
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if not pas[y + dy][x + dx] or occ[y + dy][x + dx]:
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                out.append((x, y))
    return out


def _farthest_point_sample(cands: list[tuple[int, int]], n: int,
                           rng: random.Random) -> list[tuple[int, int]]:
    """贪心最远点采样: 让选出的点两两尽量分散."""
    if n <= 0:
        return []
    chosen = [rng.choice(cands)]
    # 维护每个候选到已选集合的最近距离平方
    cand = cands
    best = [(_d2(c, chosen[0])) for c in cand]
    while len(chosen) < n:
        # 选离已选集合最远的候选
        idx = max(range(len(cand)), key=lambda i: best[i])
        chosen.append(cand[idx])
        last = cand[idx]
        for i, c in enumerate(cand):
            d = _d2(c, last)
            if d < best[i]:
                best[i] = d
    return chosen


def _d2(a: tuple[int, int], b: tuple[int, int]) -> int:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def find_placements(m: MapData, n: int, *, seed: int | None = None,
                    z: int = 0) -> list[tuple[int, int, int]]:
    """返回 n 个 (x, y, z) 落点. 候选不足时抛 ValueError."""
    cands = _candidates(m, z)
    if len(cands) < n:
        raise ValueError(
            f"开阔候选格只有 {len(cands)} 个, 不足 {n} 个; "
            f"地图过密或过小, 无法保证不重叠放置."
        )
    rng = random.Random(seed)
    picked = _farthest_point_sample(cands, n, rng)
    return [(x, y, z) for (x, y) in picked]
