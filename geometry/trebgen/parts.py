"""The printable parts, in build123d.

Each part is modelled in its print orientation (flat on z = 0, no supports)
as `local`, and placed into the assembly (X throw, Y axle, Z up, axle at
(0, 0, H)) by `placements`. Parts that move in the throw carry a `role` so
the page can animate them: "arm" turns about the axle, "bucket" hangs from
the hinge, "projectile" flies, "sling" is drawn as a line instead.

How it goes together (no glue, no screws):
- The trough deck and the front cross member end in split "arrow" tenons
  that click through slots in the side frames' rails.
- The axle and the bucket hinge are printed pins with a head at one end and
  a split, barbed end that snaps behind the far side. Spacers on the axle
  and sleeves on the hinge keep the arm centred.
- The bucket has a sloped roof inside its top and a push-in cap.
- A printed trigger pin goes through the side frame into the arm.
- The sling is string with a printed pouch and release ring; the release
  hook is part of the arm's tip, set to the best release angle.

The fits (per side) come from RUN_CLEAR, SLOT_CLEAR and the user's extra
`clearance`; snap strains are kept near 1-2 % (PLA tolerates about 2-3 %),
see docs/design_research.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from build123d import (Align, Axis, Box, Cone, Cylinder, Face, Location, Plane, Polygon, Pos, Sphere, Vector,
                       Wire, extrude)

from .params import AXLES, DECK_SEAT, MEMBER_H, RUN_CLEAR, SLOT_CLEAR, DesignParams, Derived

PART_COLORS = {
    "Frame": (0.20, 0.45, 0.85),
    "Cross_Member": (0.30, 0.70, 0.35), "Trough": (0.95, 0.75, 0.15),
    "Arm": (0.85, 0.25, 0.20), "Bucket": (0.60, 0.35, 0.75), "Bucket_Cap": (0.75, 0.55, 0.85),
    "Axle_Pin": (0.95, 0.50, 0.15), "Hinge_Pin": (0.95, 0.50, 0.15),
    "Axle_Spacer": (0.95, 0.60, 0.25), "Hinge_Sleeve": (0.95, 0.60, 0.25), "Trigger_Pin": (0.95, 0.50, 0.15),
    "Sling_Pouch": (0.55, 0.40, 0.25), "Release_Ring": (0.95, 0.50, 0.15),
    "Ball": (0.95, 0.95, 0.95),
}
HW_COLOR = (0.62, 0.64, 0.68)

CORD_HOLE = 3.0
TENON_BARB = 1.0      # tenon barb, per side: 0.6 mm of catch past a 0.4 mm slot clearance
PIN_BARB = 1.2        # snap-pin barb (radius): 0.85 mm of catch past the running clearance
PIN_SPLIT_LEN = 22.0  # how far the split runs back from the barb: keeps the bend near 1 % strain
SPLIT = 2.0           # the split in tenons and pins
MEMBER_W, MEMBER_T = MEMBER_H, 6.0  # cross members: height (Z) and thickness (X)
PEG = 4.0             # pegs on the cross members that locate the deck (along Y)
PEG_Y = 9.0
PRONG_W, PRONG_T, PRONG_L = 4.5, 5.0, 11.0  # release hook on the arm's tip


@dataclass
class Part:
    name: str
    local: object                 # print orientation, on z = 0
    placements: list              # assembled copies (build123d shapes)
    role: str = "static"          # static | arm | bucket | projectile | sling
    qty: int = 1
    purpose: str = ""
    hardware: bool = False        # preview only (bolts, bearings), not printed

    @property
    def color(self):
        return HW_COLOR if self.hardware else PART_COLORS.get(self.name, (0.7, 0.7, 0.7))


# ---------------------------------------------------------------- helpers
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


def _rect(x0, x1, y0, y1, t, z0=0.0):
    return Pos(x0, y0, z0) * Box(x1 - x0, y1 - y0, t, align=(Align.MIN, Align.MIN, Align.MIN))


def _hole_z(x, y, d, depth=1000.0, z0=-1.0):
    return Pos(x, y, z0) * Cylinder(d / 2, depth, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _xz_prism(pts, y0, y1):
    """A prism from an (x, z) outline, between y0 and y1."""
    face = Face(Wire.make_polygon([Vector(x, y0, z) for x, z in pts], close=True))
    return extrude(face, amount=y1 - y0, dir=(0, 1, 0))


def _teardrop_xz(cx, cz, d, n=24):
    """A horizontal hole's outline, point up, so it prints without support."""
    r = d / 2
    pts = [(cx + r * math.cos(a), cz + r * math.sin(a))
           for a in (math.radians(135 + 270 * i / n) for i in range(n + 1))]
    return pts + [(cx, cz + r * math.sqrt(2))]


def _circle_xz(cx, cz, r, n=32):
    return [(cx + r * math.cos(2 * math.pi * i / n), cz + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def arrow_tenon(root, direction, w, through):
    """A split, barbed tenon in the print plane, as (body, split) faces to
    add and cut. It starts at `root` (where the bar meets the frame's inside
    face), runs `through` mm through the frame, then the barbs catch on the
    outside face; the 45° lead-in squeezes the two prongs together on the way
    in. The split runs 14 mm back into the bar so the prongs bend gently."""
    ux, uy = direction
    vx, vy = -uy, ux
    ox, oy = root

    def at(s, t):
        return (ox + ux * s + vx * t, oy + uy * s + vy * t)

    h, b = w / 2, TENON_BARB
    body = [at(-0.01, -h), at(through, -h), at(through, -h - b), at(through + 1.0, -h - b),
            at(through + 1.0 + 3.5, -h + 1.2), at(through + 1.0 + 3.5, h - 1.2), at(through + 1.0, h + b),
            at(through, h + b), at(through, h), at(-0.01, h)]
    split = [at(-14, -SPLIT / 2), at(through + 6, -SPLIT / 2), at(through + 6, SPLIT / 2), at(-14, SPLIT / 2)]
    return body, split


def _with_tenons(shape, tenons, t, z0=0.0):
    for body, split in tenons:
        shape += Pos(0, 0, z0) * _plate(body, t)
    for body, split in tenons:
        shape -= Pos(0, 0, z0 - 1) * _plate(split, t + 2)
        # A round end on the split so the root doesn't crack.
        (ax, ay), (bx, by) = split[0], split[3]
        shape -= _hole_z((ax + bx) / 2, (ay + by) / 2, SPLIT + 0.6, depth=t + 2, z0=z0 - 1)
    return shape


def snap_pin(d, grip, head_d=None):
    """A pin along +X with its axis on the X axis: a head at x < 0, a plain
    shank through `grip` mm of parts, and a split barbed end that springs out
    behind the far face. Flattened on the bottom so it prints lying down
    (layers along the pin: much stronger than standing up)."""
    r = d / 2
    head_r = (head_d or d + 6) / 2
    g = grip + 0.3
    pin = Cylinder(head_r, 2.5, rotation=(0, 90, 0)).translate((-1.25, 0, 0))
    pin += Cylinder(r, g, rotation=(0, 90, 0)).translate((g / 2, 0, 0))
    pin += Cylinder(r + PIN_BARB, 1.0, rotation=(0, 90, 0)).translate((g + 0.5, 0, 0))
    pin += Cone(r + PIN_BARB, r - 0.6, 3.5, rotation=(0, 90, 0)).translate((g + 1.0 + 1.75, 0, 0))
    k = min(PIN_SPLIT_LEN, grip - 5)
    pin -= Box(k + 4.5 + 1, SPLIT, 3 * d, align=(Align.MIN, Align.CENTER, Align.CENTER)).translate((g - k, 0, 0))
    pin -= Cylinder(SPLIT / 2 + 0.3, 3 * d).translate((g - k, 0, 0))
    flat = r - 0.8
    pin -= Box(4 * grip + 40, 4 * head_r, 4 * head_r, align=(Align.CENTER, Align.CENTER, Align.MAX)).translate(
        (grip / 2, 0, -flat))
    return pin, flat


def _on_bed(shape, lift):
    return shape.translate((0, 0, lift))


# ---------------------------------------------------------------- frames
def frame_local(p: DesignParams, d: Derived):
    """Right side frame, flat: the profile is the X-Z side view (local y =
    height). An upside-down T (rail + tower) with two low braces, so two
    frames nest head to toe on the plate."""
    t, H = d.frame_t, d.H
    rail = _rect(d.x_back, d.x_front, 0, d.rail_h, t)
    tower = _rect(-9, 9, d.rail_h - 1, H, t)
    ax = AXLES[p.axle]
    r_boss = 15.5 if p.axle == "608" else d.pins["axle_hole"] / 2 + 6.0
    boss = _disc(0, H, r_boss, t)
    # Low braces (a third of the way up) leave room for the other frame's
    # top to tuck in beside the tower on the plate.
    zb = 0.32 * H
    fb, ff = max(d.x_back + 10, -0.45 * H), min(d.x_front - 10, 0.45 * H)
    braces = _bar((fb, d.rail_h / 2), (0, zb), 10, t) + _bar((ff, d.rail_h / 2), (0, zb), 10, t)
    # Trigger lobe beside the axle boss: the trigger pin goes through here
    # into the arm (see Derived.s_trigger).
    xt, zt = -d.s_trigger * math.cos(d.alpha), H - d.s_trigger * math.sin(d.alpha)
    lobe = _disc(xt, zt, d.pins["trigger_hole"] / 2 + 4.5, t) + _bar((xt, zt), (0, H), 2 * (d.pins["trigger_hole"] / 2 + 4.5), t)
    f = rail + tower + boss + braces + lobe
    if p.axle == "608":
        f -= _hole_z(0, H, ax["pocket_d"])
    else:
        f -= _hole_z(0, H, d.pins["axle_hole"])
    f -= _hole_z(xt, zt, d.pins["trigger_hole"])
    # Notches on the rail's underside for measuring the sling cords: lay a
    # cord along the rail and tie knots at the first notch and the other two.
    for x in cord_notches(d):
        f -= _plate([(x - 2, -0.01), (x + 2, -0.01), (x, 2.0)], t + 2).translate((0, 0, -1))
    sc = SLOT_CLEAR + p.clearance
    mz = d.rail_h / 2
    for x in d.member_x:
        f -= _rect(x - MEMBER_T / 2 - sc, x + MEMBER_T / 2 + sc, mz - MEMBER_W / 2 - sc, mz + MEMBER_W / 2 + sc,
                   t + 2, -1)
    return f


def cord_notches(d: Derived) -> list[float]:
    x0 = d.x_back + 5
    return [x0, x0 + d.sling["ring_cord"], x0 + d.sling["tip_cord"]]


def frames(p: DesignParams, d: Derived) -> list[Part]:
    """Both sides are the same part, the same way round: every feature goes
    straight through (the 608 bearing seat too), so no mirrored pair is
    needed, and two copies nest far better on the plate."""
    local = frame_local(p, d)
    t = d.frame_t
    right = local.rotate(Axis.X, 90).translate((0, d.gap / 2 + t, 0))
    left = right.translate((0, -d.gap - t, 0))   # the same part, the same way round
    return [Part("Frame", local, [right, left], qty=2,
                 purpose="Side frame (print 2): axle hole at the top, trigger lobe, slots for the snaps")]


# ---------------------------------------------------------------- base
def trough(p: DesignParams, d: Derived) -> Part:
    """The deck the projectile and sling lie on: a plain strip that drops
    onto the cross members' pegs. Modelled in place (X, Y) and flat."""
    t = d.plate_t
    x0, x1 = d.deck_x
    half = max(16.0, d.r_p + 6.0)
    deck = _rect(x0, x1, -half, half, t)
    sc = SLOT_CLEAR + p.clearance
    for x in d.member_x:
        # A channel underneath sits over the member (it bridges cleanly), and
        # the member's two pegs come up through holes.
        deck -= _rect(x - MEMBER_T / 2 - sc, x + MEMBER_T / 2 + sc, -half - 1, half + 1, DECK_SEAT + 1, -1)
        for y in (-PEG_Y, PEG_Y):
            deck -= _rect(x - MEMBER_T / 2 - sc, x + MEMBER_T / 2 + sc, y - PEG / 2 - sc, y + PEG / 2 + sc, t + 2, -1)
    return Part("Trough", deck, [deck.translate((0, 0, d.deck_z0))],
                purpose="Deck the projectile slides on; drops onto the cross members' pegs")


def cross_member(p: DesignParams, d: Derived) -> Part:
    """Ties the frames together under each end of the deck (print 2). Printed
    flat: local x along the bar (assembly Y), local y its height (assembly
    Z, pegs up), thickness along X."""
    h = MEMBER_W / 2
    m = _rect(-d.gap / 2, d.gap / 2, -h, h, MEMBER_T)
    for y in (-PEG_Y, PEG_Y):
        m += _rect(y - PEG / 2, y + PEG / 2, h - 0.01, h + d.plate_t - DECK_SEAT - 0.3, MEMBER_T)
    m = _with_tenons(m, [arrow_tenon((s * d.gap / 2, 0), (s, 0), MEMBER_W, d.frame_t) for s in (-1, 1)], MEMBER_T)
    turned = m.rotate(Axis.X, 90).rotate(Axis.Z, 90)
    placed = [turned.translate((x - MEMBER_T / 2, 0, d.rail_h / 2)) for x in d.member_x]
    local = m.translate((0, h, 0))
    return Part("Cross_Member", local, placed, qty=len(placed),
                purpose="Clicks through both frames (print 2); the deck sits on its pegs")


# ---------------------------------------------------------------- arm
def arm_local(p: DesignParams, d: Derived, pin_angle: float):
    """Flat arm: local x runs along the arm (+x = long side, the axle at 0),
    local y across it in the swing plane (+y is the side the sling hangs
    from at rest), z = thickness (along the axle)."""
    a = d.arm
    t = p.arm_thickness
    L1, L2 = d.L1, d.L2
    tip_x = L1 + a["tip_ext"]
    outline = [(-L2, -a["hinge_end"] / 2), (0, -a["hub"] / 2), (tip_x, -a["tip"] / 2),
               (tip_x, a["tip"] / 2), (0, a["hub"] / 2), (-L2, a["hinge_end"] / 2)]
    arm = _plate(outline, t) + _disc(0, 0, a["hub"] / 2, t) + _disc(-L2, 0, a["hinge_end"] / 2, t)
    # Release hook: a prong off the tip, angled toward the sling side. The
    # ring slides off it when the sling swings round to the same angle.
    ang = math.radians(max(10.0, min(80.0, pin_angle)))
    base = (L1 + 1.0, 0.0)
    end = (base[0] + PRONG_L * math.cos(ang), base[1] + PRONG_L * math.sin(ang))
    arm += _bar(base, end, PRONG_W, PRONG_T) + _disc(end[0], end[1], PRONG_W / 2, PRONG_T)
    pins = d.pins
    arm -= _hole_z(0, 0, pins["axle_hole"])
    arm -= _hole_z(-L2, 0, pins["hinge_hole"])
    arm -= _hole_z(d.s_trigger, 0, pins["trigger_hole"])
    arm -= _hole_z(L1 - 5, 0, CORD_HOLE)        # the sling's tip cord ties here
    return arm


def _arm_place(shape, p: DesignParams, d: Derived):
    theta0 = math.pi + d.alpha
    return (shape.translate((0, 0, -p.arm_thickness / 2)).rotate(Axis.X, 90)
            .rotate(Axis.Y, -math.degrees(theta0)).translate((0, 0, d.H)))


def arm(p: DesignParams, d: Derived, pin_angle: float) -> Part:
    local = arm_local(p, d, pin_angle)
    return Part("Arm", local, [_arm_place(local, p, d)], role="arm",
                purpose=f"Throwing arm: axle and hinge holes, trigger hole, release hook set to {pin_angle:.0f}°")


# ---------------------------------------------------------------- counterweight
def _opening(d: Derived):
    """The fill hole: the roof's top, a 3 mm vertical neck the cap plugs into."""
    b = d.bucket
    return b["D"] - 2 * b["wall"] - 2 * b["roof_h"], b["W"] - 2 * b["wall"] - 2 * b["roof_h"]


def bucket_local(p: DesignParams, d: Derived):
    """Box printed upright, with a 45° roof inside its top (no support) and a
    fill hole that takes a quarter; an ear on each side wall holds the hinge
    pin (teardrop hole, so no support either). Hinge hole at local
    (0, 0, H + hinge_drop)."""
    b = d.bucket
    W, D, Hb, wall, floor, roof = b["W"], b["D"], b["H"], b["wall"], b["floor"], b["roof_h"]
    a, w = D - 2 * wall, W - 2 * wall
    z1 = Hb - 3.0                 # roof top / neck bottom
    z0 = z1 - roof                # roof bottom
    box = Box(D, W, Hb, align=(Align.CENTER, Align.CENTER, Align.MIN))
    box -= Pos(0, 0, floor) * Box(a, w, z0 - floor + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
    if roof > 0.05:
        face = Polygon((-a / 2, -w / 2), (a / 2, -w / 2), (a / 2, w / 2), (-a / 2, w / 2), align=None)
        box -= Pos(0, 0, z0) * extrude(face, amount=roof + 0.01, taper=45)
    oa, ob = _opening(d)
    box -= Pos(0, 0, z1 - 0.02) * Box(oa, ob, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
    hz = Hb + d.hinge_drop
    r_ear = b["ear_w"] / 2
    ear_pts = [(-r_ear, Hb - 18), (r_ear, Hb - 18), (r_ear, hz)] + \
        [(r_ear * math.cos(math.pi * i / 16), hz + r_ear * math.sin(math.pi * i / 16)) for i in range(1, 16)] + \
        [(-r_ear, hz)]
    for s in (-1, 1):
        y0, y1 = sorted((s * (W / 2 - wall), s * (W / 2 + b["ear_t"])))
        box += _xz_prism(ear_pts, y0, y1)
    box -= _xz_prism(_teardrop_xz(0, hz, d.pins["hinge_hole"]), -W, W)
    return box


def cap_local(p: DesignParams, d: Derived):
    """Push-in cap for the fill hole, printed flange down. The plug is a thin
    wall with four slits so it springs into the 3 mm neck and grips."""
    oa, ob = _opening(d)
    t = d.bucket["cap_t"]
    cap = _rect(-oa / 2 - 3, oa / 2 + 3, -ob / 2 - 3, ob / 2 + 3, t)
    cap += _rect(oa / 2 + 2.99, oa / 2 + 8, -5, 5, t)                      # pull tab
    pa, pb = oa - 0.1, ob - 0.1                                            # 0.05 mm press fit a side
    plug = _rect(-pa / 2, pa / 2, -pb / 2, pb / 2, 2.8, t)
    plug -= _rect(-pa / 2 + 1.6, pa / 2 - 1.6, -pb / 2 + 1.6, pb / 2 - 1.6, 4, t)
    for x in (-pa / 4, pa / 4):
        for s in (-1, 1):
            plug -= _rect(x - 0.4, x + 0.4, s * pb / 2 - 2, s * pb / 2 + 2, 4, t + 0.8)
    return cap + plug


def bucket_parts(p: DesignParams, d: Derived) -> list[Part]:
    b = d.bucket
    hz = b["H"] + d.hinge_drop
    hx, hzz = d.L2 * math.cos(d.alpha), d.H + d.L2 * math.sin(d.alpha)
    local = bucket_local(p, d)
    placed = local.translate((hx, 0, hzz - hz))
    cap = cap_local(p, d)
    cap_p = cap.rotate(Axis.X, 180).translate((hx, 0, hzz - hz + b["H"] + b["cap_t"]))
    return [
        Part("Bucket", local, [placed], role="bucket",
             purpose=f"Counterweight box, holds about {b['volume_cm3']:.0f} cm³ of fill"),
        Part("Bucket_Cap", cap, [cap_p], role="bucket", purpose="Pushes into the fill hole"),
    ]


# ---------------------------------------------------------------- pins and spacers
def _tube(od, id_, L):
    return Cylinder(od / 2, L, align=(Align.CENTER, Align.CENTER, Align.MIN)) - _hole_z(0, 0, id_)


def _along_y(shape, x, y, z, sign=1):
    """A part modelled along +X (pins) turned to run along ±Y, its x = 0 at (x, y, z)."""
    return shape.rotate(Axis.Z, 90 * sign).translate((x, y, z))


def _standing_to_y(shape, x, y, z, sign=1):
    """A part modelled standing on z = 0 (tubes) turned to run along ±Y from (x, y, z)."""
    return shape.rotate(Axis.X, -90 * sign).translate((x, y, z))


def axle_parts(p: DesignParams, d: Derived) -> list[Part]:
    pins = d.pins
    out = []
    if p.axle == "printed":
        pin, flat = snap_pin(pins["axle_d"], pins["axle_grip"])
        out.append(Part("Axle_Pin", _on_bed(pin, flat), [_along_y(pin, 0, -d.gap / 2 - d.frame_t, d.H)],
                        purpose="The axle: push it through, the split end clicks behind the far frame"))
    sp = _tube(pins["spacer_od"], pins["axle_hole"], pins["spacer_len"])  # 608: reaches the bearing's inner race
    y0 = p.arm_thickness / 2 + 0.2
    out.append(Part("Axle_Spacer", sp, [_standing_to_y(sp, 0, y0, d.H), _standing_to_y(sp, 0, -y0, d.H, -1)], qty=2,
                    purpose="Keeps the arm in the middle of the axle"))
    return out


def hinge_parts(p: DesignParams, d: Derived) -> list[Part]:
    pins, b = d.pins, d.bucket
    hx, hz = d.L2 * math.cos(d.alpha), d.H + d.L2 * math.sin(d.alpha)
    pin, flat = snap_pin(pins["hinge_d"], pins["hinge_grip"])
    sl = _tube(pins["sleeve_od"], pins["hinge_hole"], pins["sleeve_len"])
    y0 = p.arm_thickness / 2 + 0.2
    return [
        Part("Hinge_Pin", _on_bed(pin, flat), [_along_y(pin, hx, -b["W_out"] / 2, hz)], role="bucket",
             purpose="Hangs the bucket from the short end of the arm"),
        Part("Hinge_Sleeve", sl, [_standing_to_y(sl, hx, y0, hz), _standing_to_y(sl, hx, -y0, hz, -1)], qty=2,
             role="bucket", purpose="Centre the arm between the bucket's ears"),
    ]


def trigger_pin(p: DesignParams, d: Derived) -> Part:
    """Through the right frame's top, beside the axle, into the arm's trigger
    hole; pull it (by a cord tied to the ring) to fire."""
    r = d.pins["trigger_d"] / 2
    L = d.gap / 2 + d.frame_t + p.arm_thickness / 2 - 2
    flat = r - 0.6
    shank = Cylinder(r, L - 2 + 3, rotation=(0, 90, 0)).translate(((L - 2 - 3) / 2, 0, 0))  # starts inside the ring
    shank += Cone(r, r - 1.2, 2, rotation=(0, 90, 0)).translate((L - 1, 0, 0))
    ring = Cylinder(10, 3, align=(Align.CENTER, Align.CENTER, Align.MIN)).translate((-10.5, 0, -flat))
    ring -= Cylinder(5.5, 10).translate((-10.5, 0, 0))
    pin = shank + ring
    pin -= Box(4 * L + 60, 60, 20, align=(Align.CENTER, Align.CENTER, Align.MAX)).translate((0, 0, -flat))
    xt, zt = -d.s_trigger * math.cos(d.alpha), d.H - d.s_trigger * math.sin(d.alpha)
    placed = _along_y(pin, xt, d.gap / 2 + d.frame_t, zt, -1)
    return Part("Trigger_Pin", _on_bed(pin, flat), [placed],
                purpose="Holds the arm down; pull it (with a cord on the ring) to throw")


# ---------------------------------------------------------------- sling
def sling_parts(p: DesignParams, d: Derived, pin_angle: float) -> list[Part]:
    s = d.sling
    L, w, t = s["pouch_L"], s["pouch_w"], 1.2
    pouch = _rect(-L / 2 + w / 2, L / 2 - w / 2, -w / 2, w / 2, t) + _disc(-L / 2 + w / 2, 0, w / 2, t) + \
        _disc(L / 2 - w / 2, 0, w / 2, t)
    pouch -= _hole_z(0, 0, s["pouch_hole"])
    for sx in (-1, 1):
        pouch -= _hole_z(sx * s["cord_hole_off"], 0, CORD_HOLE)
        # Two slits each side let the pouch fold round the ball.
        for k in (0.2, 0.3):
            x = sx * k * L
            pouch -= _rect(x - 0.6, x + 0.6, -w / 2 + 3.5, w / 2 - 3.5, t + 2, -1)
    pouch_p = pouch.translate((d.x_p0, 0, d.z_trough))

    ring = _disc(0, 0, 7.5, 2.4) - _hole_z(0, 0, 9.5)
    ring += _rect(6, 13, -3.5, 3.5, 2.4) + _disc(13, 0, 3.5, 2.4)
    ring -= _hole_z(13, 0, CORD_HOLE)
    ang = math.radians(max(10.0, min(80.0, pin_angle)))
    ux, uy = math.cos(ang), math.sin(ang)
    centre = (d.L1 + 1.0 + 10.0 * ux, 10.0 * uy, PRONG_T / 2)
    on_arm = ring.translate((0, 0, -1.2)).moved(Location(Plane(origin=centre, x_dir=(0, 0, 1), z_dir=(ux, uy, 0))))
    ring_p = _arm_place(on_arm, p, d)

    return [
        Part("Sling_Pouch", pouch, [pouch_p], role="sling",
             purpose="Cradles the projectile; a cord ties through each end"),
        Part("Release_Ring", ring, [ring_p], role="arm", purpose="On the ring cord; slips off the release hook"),
    ]


def ball(p: DesignParams, d: Derived) -> Part:
    r = d.r_p
    flat = 0.8  # a small flat so it sticks to the bed
    s = Sphere(r).translate((0, 0, r - flat)) - Box(4 * r, 4 * r, 2 * r, align=(Align.CENTER, Align.CENTER, Align.MAX))
    return Part("Ball", s, [s.translate((d.x_p0, 0, d.z_trough + flat))], role="projectile",
                purpose="Projectile (print a few: they get lost)")


# ---------------------------------------------------------------- hardware (preview only)
def hardware(p: DesignParams, d: Derived) -> list[Part]:
    if p.axle == "printed":
        return []
    axle_len = 2 * d.frame_t + d.gap + 6
    axle = Cylinder(4, axle_len).rotate(Axis.X, 90).translate((0, 0, d.H))
    out = [Part("Axle_Bolt", axle, [axle], hardware=True)]
    if p.axle == "608":
        bearings = []
        for s in (-1, 1):
            y = s * (d.gap / 2 + d.frame_t / 2)
            br = (Cylinder(11, 7) - Cylinder(4, 7)).rotate(Axis.X, 90).translate((0, y, d.H))
            bearings.append(br)
        out.append(Part("Bearings", bearings[0], bearings, hardware=True, qty=2))
    return out
