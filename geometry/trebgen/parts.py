"""The printable parts, in build123d.

Each part is modelled in its print orientation (flat on z = 0) as `local`,
and placed into the assembly (X throw, Y axle, Z up, axle at (0, 0, H)) by
`placements`. Parts that move in the throw carry a `role` so the page can
animate them: "arm" turns about the axle, "bucket" hangs from the hinge.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from build123d import (Align, Axis, Box, Circle, Cylinder, Location, Plane, Polygon, Pos, Sphere, extrude)

from .params import AXLES, DesignParams, Derived

PART_COLORS = {
    "Frame_Right": (0.20, 0.45, 0.85), "Frame_Left": (0.20, 0.45, 0.85),
    "Cross_Member": (0.30, 0.70, 0.35), "Trough": (0.95, 0.75, 0.15),
    "Arm": (0.85, 0.25, 0.20), "Bucket": (0.60, 0.35, 0.75), "Bucket_Lid": (0.75, 0.55, 0.85),
    "Axle_Spacer": (0.95, 0.50, 0.15), "Trigger_Pin": (0.95, 0.50, 0.15),
    "Pin_Gauge": (0.55, 0.55, 0.58), "Ball": (0.95, 0.95, 0.95),
}
HW_COLOR = (0.62, 0.64, 0.68)

CLEAR_HOLE_M3 = 3.4
PILOT_M3 = 2.6     # M3 / #4 self-tapping screw into plastic
M8_HOLE = 8.4
M4_HOLE = 4.4
PIN_HOLE = 2.1     # release pin: 2 mm nail or straightened paper clip
CORD_HOLE = 2.5
TRIGGER_HOLE = 4.2


@dataclass
class Part:
    name: str
    local: object                 # print orientation, on z = 0
    placements: list              # assembled copies (build123d shapes)
    role: str = "static"          # static | arm | bucket | projectile
    qty: int = 1
    purpose: str = ""
    hardware: bool = False        # preview only (bolts, bearings), not printed

    @property
    def color(self):
        return HW_COLOR if self.hardware else PART_COLORS.get(self.name, (0.7, 0.7, 0.7))


def _plate(pts, t):
    return extrude(Polygon(*pts, align=None), amount=t, dir=(0, 0, 1))


def _disc(x, y, r, t, z0=0.0):
    return Pos(x, y, z0) * Cylinder(r, t, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _bar(p, q, w, t):
    """Flat bar of width w from point p to q (XY), thickness t."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    L = math.hypot(dx, dy)
    nx, ny = -dy / L * w / 2, dx / L * w / 2
    return _plate([(p[0] + nx, p[1] + ny), (q[0] + nx, q[1] + ny), (q[0] - nx, q[1] - ny), (p[0] - nx, p[1] - ny)], t)


def _hole_z(x, y, d, depth=1000.0, z0=-1.0):
    return Pos(x, y, z0) * Cylinder(d / 2, depth, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _hole_axis(origin, direction, d, depth):
    """A drilled hole from origin along direction (unit vector, 3-D)."""
    return Cylinder(d / 2, depth, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(
        Location(Plane(origin=origin, z_dir=direction)))


# ---------------------------------------------------------------- frames
def frame_local(p: DesignParams, d: Derived):
    """Right side frame, flat: the profile is the X-Z side view (local y =
    height). The bearing pocket opens on top (the inside face)."""
    t = p.frame_thickness
    rail = _plate([(d.x_back, 0), (d.x_front, 0), (d.x_front, d.rail_h), (d.x_back, d.rail_h)], t)
    foot_b = max(d.x_back + 10, -0.55 * d.H)
    foot_f = min(d.x_front - 10, 0.55 * d.H)
    legs = _bar((foot_b, d.rail_h / 2), (0, d.H), 11, t) + _bar((foot_f, d.rail_h / 2), (0, d.H), 11, t)
    # A brace across the legs at 40% height stiffens the A.
    zb = 0.4 * d.H
    xb0 = foot_b * (1 - (zb - d.rail_h / 2) / (d.H - d.rail_h / 2))
    xb1 = foot_f * (1 - (zb - d.rail_h / 2) / (d.H - d.rail_h / 2))
    brace = _bar((xb0, zb), (xb1, zb), 8, t)
    boss = _disc(0, d.H, 15.5, t)
    f = rail + legs + brace + boss
    ax = AXLES[p.axle]
    if p.axle == "608":
        f -= _hole_z(0, d.H, ax["lip_d"])
        f -= _hole_z(0, d.H, ax["pocket_d"], z0=t - ax["pocket_depth"])
    else:
        f -= _hole_z(0, d.H, ax["hole_d"])
    for mx in d.members_x:
        f -= _hole_z(mx, d.rail_h / 2, CLEAR_HOLE_M3)
    return f


def frames(p: DesignParams, d: Derived) -> list[Part]:
    local = frame_local(p, d)
    t = p.frame_thickness
    right = local.rotate(Axis.X, 90).translate((0, d.gap / 2 + t, 0))
    left = right.mirror(Plane.XZ)
    return [
        Part("Frame_Right", local, [right], purpose="Side A-frame, holds a bearing at the top"),
        Part("Frame_Left", local.mirror(Plane.YZ), [left], purpose="The other side (a mirror image)"),
    ]


# ---------------------------------------------------------------- base
def cross_members(p: DesignParams, d: Derived) -> Part:
    L, w, h = d.gap - 0.2, 12.0, d.rail_h
    m = Pos(0, 0, 0) * Box(L, w, h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for sx in (-1, 1):
        m -= _hole_axis((sx * (L / 2 + 1), 0, h / 2), (-sx, 0, 0), PILOT_M3, 13)
    for x in (-d.gap / 4, d.gap / 4):
        m -= _hole_z(x, 0, PILOT_M3, depth=8, z0=h - 8)
    placed = [m.rotate(Axis.Z, 90).translate((mx, 0, 0)) for mx in d.members_x]
    return Part("Cross_Member", m, placed, qty=3, purpose="Joins the two frames at table level")


def trough(p: DesignParams, d: Derived) -> Part:
    """Flat plate the projectile slides along, screwed onto the cross members,
    with the trigger post at the side next to the arm's tip."""
    x0, x1 = d.members_x[0] - 6, d.members_x[-1] + 6
    w = d.gap - 0.6
    t = d.plate_t
    tr = Pos(0, 0, 0) * Box(x1 - x0, w, t, align=(Align.MIN, Align.CENTER, Align.MIN))
    tr = tr.translate((x0, 0, 0))
    for mx in d.members_x:
        for y in (-d.gap / 4, d.gap / 4):
            tr -= _hole_z(mx, y, CLEAR_HOLE_M3)
    # Trigger post: beside the sling's path, just ahead of the resting tip.
    post_h = 16.0
    px, py = d.x_tip0 + 8, w / 2 - 5
    post = Pos(px, py, t) * Box(8, 7, post_h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    post -= _hole_axis((px, py - 6, t + post_h - 5), (0, 1, 0), TRIGGER_HOLE, 12)
    tr = tr + post
    placed = tr.translate((0, 0, d.rail_h))
    return Part("Trough", tr, [placed], purpose="The projectile and sling lie here; the trigger post holds the arm down")


# ---------------------------------------------------------------- arm
def arm_local(p: DesignParams, d: Derived):
    """Flat arm: local x runs along the arm (+x = long side, the axle at 0),
    local y across it in the swing plane, z = thickness (along the axle)."""
    a = d.arm
    t = p.arm_thickness
    L1, L2 = d.L1, d.L2
    tip_x = L1 + a["tip_ext"]
    outline = [(-L2, -a["hinge_end"] / 2), (0, -a["hub"] / 2), (tip_x, -a["tip"] / 2),
               (tip_x, a["tip"] / 2), (0, a["hub"] / 2), (-L2, a["hinge_end"] / 2)]
    arm = _plate(outline, t) + _disc(0, 0, a["hub"] / 2, t) + _disc(-L2, 0, a["hinge_end"] / 2, t)
    arm -= _hole_z(0, 0, M8_HOLE)
    arm -= _hole_z(-L2, 0, M4_HOLE)
    arm -= _hole_z(L1 - 4, 0, CORD_HOLE)        # the sling's fixed end ties here
    arm -= _hole_axis((tip_x + 1, 0, t / 2), (-1, 0, 0), PIN_HOLE, 13)  # release pin, along the arm
    return arm


def arm(p: DesignParams, d: Derived) -> Part:
    local = arm_local(p, d)
    theta0 = math.pi + d.alpha
    placed = (local.translate((0, 0, -p.arm_thickness / 2)).rotate(Axis.X, 90)
              .rotate(Axis.Y, -math.degrees(theta0)).translate((0, 0, d.H)))
    return Part("Arm", local, [placed], role="arm", purpose="Throwing arm: axle hole, hinge hole, release pin at the tip")


# ---------------------------------------------------------------- counterweight
def bucket_local(p: DesignParams, d: Derived):
    """Open box with two hanger plates across the middle; the arm's short end
    goes between their ears on the M4 hinge bolt. Hinge hole at local
    (0, 0, H + hinge_drop)."""
    b = d.bucket
    W, D, Hb, wall, floor = b["W"], b["D"], b["H"], b["wall"], b["floor"]
    box = Box(D, W, Hb, align=(Align.CENTER, Align.CENTER, Align.MIN))
    box -= Pos(0, 0, floor) * Box(D - 2 * wall, W - 2 * wall, Hb, align=(Align.CENTER, Align.CENTER, Align.MIN))
    hz = Hb + d.hinge_drop
    for s in (-1, 1):
        y = s * (b["hang_gap"] / 2 + b["hanger_t"] / 2)
        plate = Pos(0, y, 0) * Box(D - wall, b["hanger_t"], Hb, align=(Align.CENTER, Align.CENTER, Align.MIN))
        ear = Pos(0, y, 0) * Box(20, b["hanger_t"], hz, align=(Align.CENTER, Align.CENTER, Align.MIN))
        ear += _hole_axis((0, y - b["hanger_t"] / 2, hz), (0, 1, 0), 14, b["hanger_t"])  # rounded top
        box += plate + ear
    box -= _hole_axis((0, -W, hz), (0, 1, 0), M4_HOLE, 2 * W)
    return box


def lid_local(p: DesignParams, d: Derived):
    """Plug-in lid for one side of the bucket (print two). Printed upside
    down: the cover on the bed, the plug on top."""
    b = d.bucket
    c = p.clearance
    inner_y0 = b["hang_gap"] / 2 + b["hanger_t"]
    inner_y1 = b["W"] / 2 - b["wall"]
    inner_x = b["D"] - 2 * b["wall"]
    cover = Pos(0, (inner_y0 + 0.3 + b["W"] / 2) / 2, 0) * Box(b["D"], b["W"] / 2 - inner_y0 - 0.3, 2.0,
                                                              align=(Align.CENTER, Align.CENTER, Align.MIN))
    plug_w = inner_y1 - inner_y0 - 2 * c
    plug = Pos(0, (inner_y0 + inner_y1) / 2, 2.0) * Box(inner_x - 2 * c, plug_w, b["lid_plug"],
                                                         align=(Align.CENTER, Align.CENTER, Align.MIN))
    plug -= Pos(0, (inner_y0 + inner_y1) / 2, 3.2) * Box(inner_x - 2 * c - 3.2, plug_w - 3.2, b["lid_plug"],
                                                         align=(Align.CENTER, Align.CENTER, Align.MIN))
    lid = cover + plug
    # Thumb tab to pull it out.
    lid += Pos(b["D"] / 2 - 1, (inner_y0 + b["W"] / 2) / 2, 0) * Box(6, 10, 2.0, align=(Align.MIN, Align.CENTER, Align.MIN))
    return lid


def bucket_parts(p: DesignParams, d: Derived) -> list[Part]:
    b = d.bucket
    hz = b["H"] + d.hinge_drop
    hx, hzz = d.L2 * math.cos(d.alpha), d.H + d.L2 * math.sin(d.alpha)
    local = bucket_local(p, d)
    placed = local.translate((hx, 0, hzz - hz))
    lid = lid_local(p, d)
    lid_r = lid.rotate(Axis.X, 180).translate((hx, 0, hzz - hz + b["H"] + 2.0))
    lid_l = lid_r.mirror(Plane.XZ)
    return [
        Part("Bucket", local, [placed], role="bucket",
             purpose=f"Counterweight box, holds about {b['volume_cm3']:.0f} cm³ of fill"),
        Part("Bucket_Lid", lid, [lid_r, lid_l], role="bucket", qty=2, purpose="Plugs into each side of the bucket"),
    ]


# ---------------------------------------------------------------- small parts
def spacers(p: DesignParams, d: Derived) -> Part:
    od = 12.0 if p.axle == "608" else 14.0  # 608: presses on the inner race only
    L = (d.gap - p.arm_thickness) / 2 - 0.5
    s = Cylinder(od / 2, L, align=(Align.CENTER, Align.CENTER, Align.MIN)) - _hole_z(0, 0, M8_HOLE)
    placed = [s.rotate(Axis.X, -90).translate((0, p.arm_thickness / 2 + 0.25, d.H)),
              s.rotate(Axis.X, 90).translate((0, -p.arm_thickness / 2 - 0.25, d.H))]
    return Part("Axle_Spacer", s, placed, qty=2, purpose="Centres the arm on the axle")


def trigger_pin(p: DesignParams, d: Derived) -> Part:
    t = 3.0
    pin = Pos(0, 0, 0) * Box(24, 3.0, t, align=(Align.MIN, Align.CENTER, Align.MIN))
    ring = _disc(-6, 0, 7.5, t) - _hole_z(-6, 0, 9)
    pin = pin + ring
    w = d.gap - 0.6
    py, pz = w / 2 - 5, d.rail_h + d.plate_t + 16.0 - 5
    placed = pin.translate((0, 0, -t / 2)).rotate(Axis.Z, 90).translate((d.x_tip0 + 8, py - 8, pz))
    return Part("Trigger_Pin", pin, [placed], purpose="Pull it to fire: holds the cord loop on the trigger post")


def pin_gauge(p: DesignParams, d: Derived, angle_deg: float) -> Part:
    """A flat wedge for bending the release pin to the suggested angle: lay
    the straight part of the pin along the long edge, bend it to the slope."""
    a = math.radians(max(5.0, min(85.0, angle_deg)))
    L = 40.0
    g = _plate([(0, 0), (L, 0), (L * math.cos(a), L * math.sin(a))], 2.0)
    g += _plate([(-12, -6), (L, -6), (L, 0), (-12, 0)], 2.0)  # straight edge to hold the arm side
    placed = g.translate((d.x_front - 50, -d.gap / 2 - p.frame_thickness - 30, 0))
    return Part("Pin_Gauge", g, [placed], purpose=f"Bend the release pin to {angle_deg:.0f}° with this")


def ball(p: DesignParams, d: Derived) -> Part:
    r = d.r_p
    flat = 0.8  # a small flat so it sticks to the bed
    s = Sphere(r).translate((0, 0, r - flat)) - Box(4 * r, 4 * r, 2 * r, align=(Align.CENTER, Align.CENTER, Align.MAX))
    return Part("Ball", s, [s.translate((d.x_p0, 0, d.z_trough + flat))], role="projectile",
                purpose="Projectile (print 3 or 4: they get lost)")


# ---------------------------------------------------------------- hardware (preview only)
def hardware(p: DesignParams, d: Derived) -> list[Part]:
    axle_len = 2 * p.frame_thickness + d.gap + 6
    axle = Cylinder(4, axle_len).rotate(Axis.X, 90).translate((0, 0, d.H))
    out = [Part("Axle_Bolt", axle, [axle], hardware=True)]
    if p.axle == "608":
        bearings = []
        for s in (-1, 1):
            y = s * (d.gap / 2 + 3.5)
            br = (Cylinder(11, 7) - Cylinder(4, 7)).rotate(Axis.X, 90).translate((0, y, d.H))
            bearings.append(br)
        out.append(Part("Bearings", bearings[0], bearings, hardware=True, qty=2))
    hx, hzz = d.L2 * math.cos(d.alpha), d.H + d.L2 * math.sin(d.alpha)
    hinge = Cylinder(2, d.bucket["hang_gap"] + 2 * d.bucket["hanger_t"] + 6).rotate(Axis.X, 90).translate((hx, 0, hzz))
    out.append(Part("Hinge_Bolt", hinge, [hinge], role="bucket", hardware=True))
    return out
