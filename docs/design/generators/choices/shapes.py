"""The (r, z) shapes of the panels: the protein, the membrane, the half-disc reservoir, a graded mesh. Not to scale."""

import math

import numpy as np
from scipy.spatial import Delaunay
from shapely.geometry import Point, Polygon

AX, CZ, R = 20.0, 150.0, 140.0
RAW = [(64, 34), (214, 34), (214, 98), (126, 112), (112, 272), (84, 272), (78, 124), (60, 104)]
PROT = [(AX + (x - AX) * 0.55, CZ + (y - CZ) * 0.55) for x, y in RAW]


def arc_x(y):
    return AX + math.sqrt(R * R - (y - CZ) ** 2)


MEM_TOP, MEM_BOT = CZ + (196 - CZ) * 0.55, CZ + (240 - CZ) * 0.55
MEM = [(AX + (121 - AX) * 0.55, MEM_TOP), (arc_x(MEM_TOP), MEM_TOP), (arc_x(MEM_BOT), MEM_BOT), (AX + (113 - AX) * 0.55, MEM_BOT)]


def pts(p):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in p)


ARC = f"M{AX} {CZ - R} A{R} {R} 0 0 1 {AX} {CZ + R}"
PROTEIN = f'<polygon points="{pts(PROT)}" fill="currentColor" fill-opacity=".32" stroke="currentColor"/>'
MEMBRANE = f'<polygon points="{pts(MEM)}" fill="currentColor" fill-opacity=".14" stroke="currentColor" stroke-opacity=".7"/>'
AXIS = f'<line x1="{AX}" y1="{CZ - R}" x2="{AX}" y2="{CZ + R}" stroke="currentColor" stroke-width="1.5" stroke-dasharray="6 4"/>'
RESERVOIR = f'<path d="{ARC}" fill="none" stroke="currentColor" stroke-opacity=".7"/>'

# The graded mesh: fine at the wall, coarse towards the reservoir's arc.
_rng = np.random.default_rng(7)
_prot, _mem = Polygon(PROT), Polygon(MEM)
_solid = _prot.union(_mem)
_disc = Polygon([(AX, CZ - R)] + [(AX + R * math.cos(t), CZ + R * math.sin(t)) for t in np.linspace(-math.pi / 2, math.pi / 2, 90)] + [(AX, CZ + R)])
_dom = _disc.difference(_solid)


def _h(x, y):
    return min(2.2 + 0.16 * _solid.exterior.distance(Point(x, y)), 16.0)


_p = []
for ring in (_prot.exterior, _mem.exterior, _disc.exterior):
    s = 0.0
    while s < ring.length:
        q = ring.interpolate(s)
        _p.append((q.x, q.y))
        s += _h(q.x, q.y)
for _ in range(40000):
    x, y = _rng.uniform(AX, AX + R), _rng.uniform(CZ - R, CZ + R)
    q = Point(x, y)
    if not _dom.contains(q):
        continue
    h = _h(x, y)
    if all((x - a) ** 2 + (y - b) ** 2 > (0.8 * h) ** 2 for a, b in _p[-400:]) and \
       all((x - a) ** 2 + (y - b) ** 2 > (0.8 * h) ** 2 for a, b in _p if abs(a - x) < h and abs(b - y) < h):
        _p.append((x, y))
_P = np.array(_p)
_T = [t for t in Delaunay(_P).simplices if _dom.buffer(0.3).contains(Point(_P[t].mean(axis=0)))]


def _min_angle(t):
    a, b, c = _P[t]
    out = []
    for p, q, r in ((a, b, c), (b, c, a), (c, a, b)):
        u, v = q - p, r - p
        out.append(math.degrees(math.acos(max(-1, min(1, u @ v / (np.linalg.norm(u) * np.linalg.norm(v)))))))
    return min(out)


QUALITY = [0.32 + 0.68 * _min_angle(t) / 60.0 for t in _T]  # a stand-in for SICN: 1 for an equilateral element, all above the 0.3 gate
TRIS = "".join(f"M{_P[t[0]][0]:.1f} {_P[t[0]][1]:.1f}L{_P[t[1]][0]:.1f} {_P[t[1]][1]:.1f}L{_P[t[2]][0]:.1f} {_P[t[2]][1]:.1f}Z" for t in _T)
_order = sorted(range(len(_T)), key=lambda i: QUALITY[i])
WORST = "".join(f"M{_P[_T[i][0]][0]:.1f} {_P[_T[i][0]][1]:.1f}L{_P[_T[i][1]][0]:.1f} {_P[_T[i][1]][1]:.1f}L{_P[_T[i][2]][0]:.1f} {_P[_T[i][2]][1]:.1f}Z" for i in _order[:6])
_VIR = ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"]
COLOURED = "".join(
    f'<path d="M{_P[t[0]][0]:.1f} {_P[t[0]][1]:.1f}L{_P[t[1]][0]:.1f} {_P[t[1]][1]:.1f}L{_P[t[2]][0]:.1f} {_P[t[2]][1]:.1f}Z" fill="{_VIR[min(4, int((q - 0.3) / 0.7 * 5))]}"/>'
    for t, q in zip(_T, QUALITY))
HIST = np.histogram(QUALITY, bins=10, range=(0, 1))[0].tolist()
WORST_POS = tuple(_P[_T[_order[0]]].mean(axis=0))

_buf = _prot.buffer(-1.6)
PROBE = pts(list(_buf.exterior.coords))
