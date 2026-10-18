"""Output: STLs in print orientation, a GLB for the page's preview, and PNG
renders for checking (needs matplotlib)."""

from __future__ import annotations

import io
import math
import tempfile
from pathlib import Path

import numpy as np

from .build import Trebuchet


def _tess(shape, tol=0.05):
    verts, tris = shape.tessellate(tol, 0.2)
    return np.array([(v.X, v.Y, v.Z) for v in verts]), np.array(tris)


def stl_bytes(shape, tol=0.02) -> bytes:
    from build123d import export_stl
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "part.stl"
        export_stl(shape, path, tolerance=tol, angular_tolerance=0.1)
        return path.read_bytes()


def plate_3mf(plate) -> bytes:
    """One plate as a 3MF: one named object per part, in its plate position
    (slicers keep them as separate objects, so each can have its own
    settings). The plate's corner is at the origin."""
    from build123d import Mesher
    mesher = Mesher()
    for pc in plate.placed:
        s = pc.solid
        s.label = f"{pc.name}_{pc.copy + 1}" if pc.copy or pc.name in _multi(plate) else pc.name
        mesher.add_shape(s, linear_deflection=0.02, angular_deflection=0.1)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "plate.3mf"
        mesher.write(str(path))
        return path.read_bytes()


def _multi(plate) -> set:
    names = [pc.name for pc in plate.placed]
    return {n for n in names if names.count(n) > 1}


def plate_stl(plate) -> bytes:
    """The whole plate as one STL (for slicers without 3MF)."""
    from build123d import Compound
    return stl_bytes(Compound([pc.solid for pc in plate.placed]))


def glb(treb: Trebuchet) -> bytes:
    """One node per placed copy, named `<part>#<n>`; the page reads the role
    and pivot from the build response to animate the throw."""
    import trimesh
    scene = trimesh.Scene()
    for part in treb.parts:
        for n, shape in enumerate(part.placements):
            v, t = _tess(shape, 0.1)
            mesh = trimesh.Trimesh(v, t, process=False)
            name = f"{part.name}#{n}"
            scene.add_geometry(mesh, node_name=name, geom_name=name)
    return scene.export(file_type="glb")


def render_png(treb: Trebuchet, path: Path | None = None, elev=18, azim=-60, px=900) -> bytes:
    """Shaded z-buffer render of the assembly, orthographic."""
    return _render([(s, part.color) for part in treb.parts for s in part.placements], path, elev, azim, px)


def render_plate_png(plate, path: Path | None = None, px=900) -> bytes:
    """The plate seen from above (and a little in front), parts in their colours."""
    from build123d import Box
    from .parts import PART_COLORS
    bed = Box(plate.side, plate.side, 0.4).translate((plate.side / 2, plate.side / 2, -0.2))
    items = [(bed, (0.86, 0.86, 0.84))] + [(pc.solid, PART_COLORS.get(pc.name, (0.7, 0.7, 0.7))) for pc in plate.placed]
    return _render(items, path, 70, -90, px)


def _render(items, path, elev, azim, px) -> bytes:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    a, e = math.radians(azim), math.radians(elev)
    fwd = -np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])
    right = np.cross(fwd, [0, 0, 1.0]); right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    light = -fwd + 0.6 * up - 0.4 * right; light /= np.linalg.norm(light)
    meshes = []
    for shape, color in items:
        v, t = _tess(shape, 0.2)
        meshes.append((v, t, np.array(color)))
    allv = np.vstack([m[0] for m in meshes])
    u, w = allv @ right, allv @ up
    span = max(u.max() - u.min(), w.max() - w.min()) * 1.06
    cu, cw = (u.max() + u.min()) / 2, (w.max() + w.min()) / 2
    img = np.ones((px, px, 3))
    zbuf = np.full((px, px), np.inf)
    for v, t, rgb in meshes:
        su = ((v @ right - cu) / span + 0.5) * px
        sw = (0.5 - (v @ up - cw) / span) * px
        depth = v @ fwd
        for tri in t:
            p0, p1, p2 = v[tri]
            nrm = np.cross(p1 - p0, p2 - p0)
            ln = np.linalg.norm(nrm)
            if ln == 0:
                continue
            nrm /= ln
            shade = 0.35 + 0.65 * abs(nrm @ light)
            xs, ys, zs = su[tri], sw[tri], depth[tri]
            x0, x1 = int(max(0, np.floor(xs.min()))), int(min(px - 1, np.ceil(xs.max())))
            y0, y1 = int(max(0, np.floor(ys.min()))), int(min(px - 1, np.ceil(ys.max())))
            if x1 < x0 or y1 < y0:
                continue
            X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
            if abs(d) < 1e-12:
                continue
            l0 = ((ys[1] - ys[2]) * (X - xs[2]) + (xs[2] - xs[1]) * (Y - ys[2])) / d
            l1 = ((ys[2] - ys[0]) * (X - xs[2]) + (xs[0] - xs[2]) * (Y - ys[2])) / d
            l2 = 1 - l0 - l1
            inside = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
            z = l0 * zs[0] + l1 * zs[1] + l2 * zs[2]
            sub = zbuf[y0:y1 + 1, x0:x1 + 1]
            closer = inside & (z < sub)
            sub[closer] = z[closer]
            img[y0:y1 + 1, x0:x1 + 1][closer] = rgb * shade
    buf = io.BytesIO()
    plt.imsave(buf, np.clip(img, 0, 1), format="png")
    if path:
        Path(path).write_bytes(buf.getvalue())
    return buf.getvalue()
