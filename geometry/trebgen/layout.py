"""Lay every printed part out on the build plate(s).

Footprints are rasterised at 1 mm, so small parts can sit inside the open
parts of the frames (a bounding-box packer can't do that, and the kit
wouldn't fit one plate). The two side frames go in first, head to toe (one
in a bottom corner, the other turned round in the opposite top corner); then each part takes the
first free spot by a fill rule, trying the quarter turns (and 15° steps for
long thin parts). The free spots for a whole plate come from one FFT
correlation. A few orders and fill rules are tried and the layout with the
fewest plates kept. Parts keep GAP mm apart and MARGIN mm in from the edge.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

import numpy as np
from build123d import Axis

RES = 1.0      # mm per cell
GAP = 2.0      # between parts
MARGIN = 5.0   # kept clear at the plate edge
MODES = ("contact", "bl", "lb")


@dataclass
class Placed:
    name: str
    copy: int
    solid: object       # in plate coordinates (plate corner at the origin)
    angle: float = 0.0  # turned this much about Z from the print orientation


@dataclass
class Plate:
    side: float
    placed: list = field(default_factory=list)


def _rasterise(V: np.ndarray, T: np.ndarray) -> np.ndarray:
    """Cells (rows = y) whose centre is inside any triangle, or that hold a vertex."""
    x0, y0 = V[:, 0].min(), V[:, 1].min()
    nx = max(1, int(math.ceil((V[:, 0].max() - x0) / RES)))
    ny = max(1, int(math.ceil((V[:, 1].max() - y0) / RES)))
    g = np.zeros((ny, nx), dtype=bool)
    P = (V[:, :2] - (x0, y0)) / RES
    for a, b, c in T:
        (ax, ay), (bx, by), (cx, cy) = P[a], P[b], P[c]
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(d) < 1e-9:
            continue
        i0, i1 = int(max(0, math.floor(min(ax, bx, cx)))), int(min(nx - 1, math.ceil(max(ax, bx, cx))))
        j0, j1 = int(max(0, math.floor(min(ay, by, cy)))), int(min(ny - 1, math.ceil(max(ay, by, cy))))
        X, Y = np.meshgrid(np.arange(i0, i1 + 1) + 0.5, np.arange(j0, j1 + 1) + 0.5)
        l0 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / d
        l1 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / d
        inside = (l0 >= -1e-6) & (l1 >= -1e-6) & (1 - l0 - l1 >= -1e-6)
        g[j0:j1 + 1, i0:i1 + 1] |= inside
    vi = np.clip(P.astype(int), 0, [nx - 1, ny - 1])
    g[vi[:, 1], vi[:, 0]] = True
    return g


def footprint(shape) -> np.ndarray:
    verts, tris = shape.tessellate(0.3, 0.5)
    V = np.array([(v.X, v.Y, v.Z) for v in verts])
    return _rasterise(V, np.array(tris))


def rot_ccw(g: np.ndarray) -> np.ndarray:
    """The grid of the same shape turned 90° counter-clockwise (x, y) -> (-y, x)."""
    return g.T[:, ::-1]


def _dilate(g: np.ndarray, r: int) -> np.ndarray:
    out = np.zeros((g.shape[0] + 2 * r, g.shape[1] + 2 * r), dtype=bool)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r + 1e-9:
                out[r + dy:r + dy + g.shape[0], r + dx:r + dx + g.shape[1]] |= g
    return out


KEYS = {  # sort keys (smallest wins) for each fill rule, from (row, col); "contact" is in _Bed.spot
    "bl": lambda r, c: (r, c), "br": lambda r, c: (r, -c), "tr": lambda r, c: (-r, -c), "tl": lambda r, c: (-r, c),
    "lb": lambda r, c: (c, r), "rb": lambda r, c: (-c, r),
}
# The two frames: fill rule for each and the first one's turn; the second is
# always turned 180° from the first, so they lie head to toe.
FRAME_PAIRS = (("br", "tl", 0.0), ("bl", "tr", 0.0), ("br", "tl", 90.0), ("bl", "tr", 90.0))


class _Bed:
    def __init__(self, side: float):
        self.n = int(side / RES)
        self.occ = np.zeros((self.n, self.n), dtype=bool)
        m = int(math.ceil(MARGIN / RES))
        self.occ[:m, :] = self.occ[-m:, :] = self.occ[:, :m] = self.occ[:, -m:] = True
        self._f = None
        self._e = None

    def spot(self, g: np.ndarray, mode: str = "bl", g_fft=None):
        """(rank, row, col) of the best spot by `mode` where g fits without
        touching anything (lower rank is better), or None. "bl": lowest then leftmost, "tr": highest then
        rightmost, and so on; "lb": leftmost then lowest, "rb": rightmost
        then lowest."""
        h, w = g.shape
        if h > self.n or w > self.n:
            return None
        if self._f is None:
            self._f = np.fft.rfft2(self.occ.astype(float))
        if g_fft is None:
            g_fft = _conj_fft(g, self.n)
        corr = np.fft.irfft2(self._f * g_fft, s=self.occ.shape)
        ok = corr[: self.n - h + 1, : self.n - w + 1] < 0.5
        rows, cols = np.nonzero(ok)
        if not len(rows):
            return None
        if mode == "contact":
            # Most cells against something already there (or the edge), so
            # parts tuck into corners and nooks; then lowest, leftmost.
            if self._e is None:
                edge = _dilate(self.occ, 1)[1:-1, 1:-1] & ~self.occ
                self._e = np.fft.rfft2(edge.astype(float))
            touch = np.round(np.fft.irfft2(self._e * g_fft, s=self.occ.shape)[rows, cols])
            k = np.lexsort((cols, rows, -touch))[0]
            return (-touch[k], rows[k], cols[k]), int(rows[k]), int(cols[k])
        a, b = KEYS[mode](rows, cols)
        k = np.lexsort((b, a))[0]
        return (a[k], b[k]), int(rows[k]), int(cols[k])

    def put(self, g: np.ndarray, row: int, col: int):
        r = int(round(GAP / RES))
        dg = _dilate(g, r)
        r0, c0 = row - r, col - r
        rs, cs = max(0, r0), max(0, c0)
        re, ce = min(self.n, r0 + dg.shape[0]), min(self.n, c0 + dg.shape[1])
        self.occ[rs:re, cs:ce] |= dg[rs - r0:re - r0, cs - c0:ce - c0]
        self._f = None
        self._e = None


def _conj_fft(g: np.ndarray, n: int):
    pad = np.zeros((n, n))
    pad[:g.shape[0], :g.shape[1]] = g
    return np.conj(np.fft.rfft2(pad))


def _grids(shape, g0, n):
    """(grid, turn in degrees, its FFT) for each orientation tried: the
    quarter turns, and 15° steps for long thin parts (they fit corner to
    corner, or slanted in a gap)."""
    out, g = [], g0
    for k in range(4):
        out.append((g, 90.0 * k))
        g = rot_ccw(g)
    h, w = g0.shape
    if max(h, w) > 4 * min(h, w):
        for a in range(15, 180, 15):
            if a % 90:
                out.append((footprint(shape.rotate(Axis.Z, a)), float(a)))
    return [(g, a, _conj_fft(g, n)) if g.shape[0] <= n and g.shape[1] <= n else (g, a, None) for g, a in out]


def _pack_once(prepared, side: float, order, mode: str, frame_modes=FRAME_PAIRS[0]):
    beds: list[_Bed] = []
    plates: list[Plate] = []
    too_big: list[str] = []
    n_frames = 0
    for i in order:
        name, copy, shape, grids = prepared[i]
        m = mode
        if name.startswith("Frame"):
            m = frame_modes[n_frames % 2]
            want = (frame_modes[2] + 180.0 * (n_frames % 2)) % 360
            grids = [x for x in grids if x[1] == want]
            n_frames += 1
        placed = False
        for bi in range(len(beds) + 1):
            if bi == len(beds):
                beds.append(_Bed(side))
                plates.append(Plate(side))
            bed = beds[bi]
            best = None
            for g, ang, gf in grids:
                s = bed.spot(g, m, gf) if gf is not None else None
                if s is not None and (best is None or s[0] < best[0][0]):
                    best = (s, ang, g)
            if best is None:
                if not plates[bi].placed:      # an empty plate it can't fit: too big
                    beds.pop()
                    plates.pop()
                    too_big.append(name)
                    placed = True
                    break
                continue
            (_, row, col), ang, g = best
            bed.put(g, row, col)
            s = shape.rotate(Axis.Z, ang)
            bb = s.bounding_box()
            plates[bi].placed.append(Placed(name, copy, s.translate((col * RES - bb.min.X, row * RES - bb.min.Y,
                                                                     -bb.min.Z)), ang))
            placed = True
            break
        if not placed:
            too_big.append(name)
    return plates, too_big


TIME_BUDGET = 5.0  # s: stop trying more orders after this (keeps the 1 GB server responsive)


def pack(items: list[tuple[str, int, object]], side: float) -> tuple[list[Plate], list[str]]:
    """items: (name, copy, print-orientation solid). Returns the plates and the
    names of parts too big for an empty plate (left off)."""
    t0 = time.monotonic()
    n = int(side / RES)
    prepared = [(name, copy, shape, _grids(shape, footprint(shape), n)) for name, copy, shape in items]
    area = [p[3][0][0].size for p in prepared]
    longest = [max(p[3][0][0].shape) for p in prepared]
    frames = [i for i, p in enumerate(prepared) if p[0].startswith("Frame")]
    rest = [i for i in range(len(prepared)) if i not in frames]
    long_ = [i for i in rest if longest[i] > 0.75 * side]
    others = [i for i in rest if i not in long_]
    blocks = sorted([i for i in others if area[i] > 1000], key=lambda i: -area[i])
    bars = sorted([i for i in others if area[i] <= 1000], key=lambda i: -longest[i])
    orders = [
        # The arm along one edge first, the frames interleaved deep beside it.
        long_ + frames + blocks + bars,
        long_ + frames + sorted(others, key=lambda i: -longest[i]),
        long_ + frames + sorted(others, key=lambda i: -area[i]),
        frames + sorted(rest, key=lambda i: -area[i]),
    ]
    rng = np.random.default_rng(1)  # a few fixed shuffles as a fallback; same layout every time
    for _ in range(6):
        orders.append(long_ + frames + list(rng.permutation(others)))
    best = None
    for order in orders:
        for fm in FRAME_PAIRS:
            for mode in MODES:
                plates, too_big = _pack_once(prepared, side, order, mode, fm)
                score = (len(too_big), len(plates))
                if best is None or score < best[0]:
                    best = (score, plates, too_big)
                if score == (0, 1) or time.monotonic() - t0 > TIME_BUDGET:
                    return best[1], best[2]
    return best[1], best[2]
