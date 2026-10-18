"""Design inputs and the dimensions derived from them.

Units are mm and grams here; physics.py works in SI. Assembly axes:
X is the throw direction, Y runs along the main axle, Z is up. The axle
sits at (0, 0, H) and the table is z = 0.

The machine is a hinged-counterweight trebuchet that prints on one plate
and snaps together (see docs/design_research.md): two identical side
frames (a rail on the table and a tower to the axle), two cross members
whose split tenons click through the rails, a deck strip on their pegs,
a tapered arm on a printed snap pin (or an M8 bolt, optionally in 608
bearings), and a roofed bucket on a printed hinge pin at the short end.

At rest the long arm points down and back, held by a trigger pin through
the frame beside the axle; the sling (two cords, printed pouch and ring)
lies forward along the deck; the counterweight hangs high on the front
side. Pulling the trigger pin lets the bucket fall, the arm swings up and
over, and the sling whips the projectile off the release hook printed on
the arm's tip.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

PLA_DENSITY = 1.24  # g/cm³, solid

# Counterweight fill: bulk density as poured (g/cm³), with the gaps.
FILLS = {
    "steel_bb": {"label": "Steel BBs (4.5 mm)", "density": 4.6},
    "coins": {"label": "Coins (pennies)", "density": 4.4},
    "nuts": {"label": "Steel nuts and washers", "density": 3.6},
    "sand": {"label": "Dry sand", "density": 1.6},
    "rice": {"label": "Rice (light, for testing)", "density": 0.85},
}

# Projectiles: diameter (mm) and mass (g). "printed_ball" is printed with
# the kit; its mass comes from the infill estimate.
PROJECTILES = {
    "printed_ball": {"label": "3D-printed ball (in the kit)", "diameter": 20.0, "mass": None},
    "marble": {"label": "Glass marble (16 mm)", "diameter": 16.0, "mass": 5.5},
    "ping_pong": {"label": "Ping-pong ball", "diameter": 40.0, "mass": 2.7},
    "foam_ball": {"label": "Foam ball (25 mm)", "diameter": 25.0, "mass": 1.0},
    "mini_marshmallow": {"label": "Mini marshmallow", "diameter": 15.0, "mass": 0.5},
    "custom": {"label": "Custom", "diameter": None, "mass": None},
}

AXLES = {
    "printed": {"label": "Printed snap pin (no hardware)", "pin_d": 10.0},
    "m8": {"label": "M8 bolt (smoother, stronger)", "pin_d": 8.0},
    # 608: the bearing presses into a hole straight through the 9 mm frame and
    # sits in the middle; the spacer inside and the washer outside clamp its
    # inner race. Through-holes keep both frames the same part.
    "608": {"label": "M8 bolt + 608 skate bearings (smoothest)", "pin_d": 8.0, "pocket_d": 22.15},
}

# Fits for FDM PLA, 0.4 mm nozzle (mm, per side). See docs/design_research.md.
RUN_CLEAR = 0.25   # a pin turning in a printed hole
SLOT_CLEAR = 0.2   # a tenon in its slot
BARB = 0.6         # snap barb overhang, per side
HINGE_PIN_D = 8.0
TRIGGER_PIN_D = 6.0
MEMBER_H = 8.0     # cross members: height (Z); 6 mm thick along X
DECK_SEAT = 2.0    # depth of the channels under the deck that sit over the members
FILL_HOLE = 27.0   # square fill hole in the bucket's roof: takes a US quarter (24.3 mm)

# Standard bolt lengths to pick from (mm), for the M8 options.
M8_LENGTHS = [40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 180, 200]


@dataclass
class DesignParams:
    # The user-facing choices.
    arm_length: float = 180.0         # whole arm, hinge hole to tip (mm)
    arm_ratio: float = 4.0            # long side / short side
    sling_ratio: float = 0.8          # sling length / long side
    cw_mass: float = 300.0            # counterweight fill (g)
    cw_fill: str = "coins"
    projectile: str = "printed_ball"
    projectile_diameter: float = 20.0  # used for "custom"
    projectile_mass: float = 4.0       # used for "custom"
    release_angle: float | None = None  # sling-to-arm angle at release (deg); None = the best one
    start_angle: float = 45.0         # long arm below level at rest (deg)
    axle: str = "printed"
    print_bed: float = 220.0          # usable square bed (mm)
    infill: float = 0.25              # 0-1, for the mass estimate
    # Advanced.
    bucket_width: float = 50.0        # across the machine (Y), outside, not counting the ears
    arm_thickness: float = 10.0       # along the axle (Y)
    frame_thickness: float = 6.0      # side frames (Y); 9 mm is used with 608 bearings
    clearance: float = 0.1            # extra print clearance added to every fit (per side)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Derived:
    """Every dimension the parts and the physics share (mm, g)."""
    L1: float          # pivot to tip (long side)
    L2: float          # pivot to hinge (short side)
    Ls: float          # sling, tip to projectile centre
    r_p: float         # projectile radius
    m_p: float         # projectile mass (g)
    rail_h: float      # frame rail height
    plate_t: float     # trough deck thickness
    deck_z0: float     # deck underside
    z_trough: float    # deck top
    frame_t: float     # side frame thickness
    gap: float         # inside distance between the side frames
    H: float           # axle height
    alpha: float       # start angle of the long arm below horizontal (rad)
    bucket: dict       # outside sizes and wall
    hinge_drop: float  # hinge to the bucket's rim
    Lc: float          # hinge to the counterweight's centre of mass (filled)
    m_cw: float        # fill + bucket + cap (g)
    m_bucket: float
    arm: dict          # widths and mass properties
    x_back: float      # base extent along X
    x_front: float
    x_tip0: float      # tip at rest
    x_p0: float        # projectile at rest
    s_trigger: float   # trigger hole, from the axle along the long side
    deck_x: tuple      # trough deck, back and front ends
    member_x: list     # the two cross members, under the deck's ends
    pins: dict         # pin and hole diameters, spacer and sleeve sizes
    sling: dict        # pouch and cord sizes
    bolts: dict
    notes: list = field(default_factory=list)


def in_sentence(label: str) -> str:
    """'Steel BBs (4.5 mm)' -> 'steel BBs (4.5 mm)': lower-case the first word only."""
    return label[:1].lower() + label[1:]


class DesignError(ValueError):
    """A design that can't be built; the message is shown to the user."""


def eff_density(infill: float) -> float:
    """Printed PLA, g/cm³: walls and skins are solid, the rest is infill.
    Small parts are mostly shell, so this leans solid."""
    return PLA_DENSITY * (0.45 + 0.55 * max(0.0, min(1.0, infill)))


def projectile_of(p: DesignParams) -> tuple[float, float]:
    """(diameter mm, mass g)."""
    spec = PROJECTILES.get(p.projectile)
    if spec is None:
        raise DesignError(f"Unknown projectile {p.projectile!r}.")
    if p.projectile == "custom":
        d, m = p.projectile_diameter, p.projectile_mass
    elif p.projectile == "printed_ball":
        d = spec["diameter"]
        m = 4 / 3 * math.pi * (d / 20) ** 3 * eff_density(p.infill)
    else:
        d, m = spec["diameter"], spec["mass"]
    if not (5 <= d <= 60):
        raise DesignError("Projectiles from 5 to 60 mm across fit this trough.")
    if not (0.2 <= m <= 100):
        raise DesignError("Projectile mass should be 0.2 to 100 g.")
    return d, m


def arm_widths(p: DesignParams) -> dict:
    """The arm's outline (in the swing plane): a hub round the axle tapering
    to the tip, and a rounded end round the hinge hole."""
    return {"hub": 24.0, "tip": 12.0, "hinge_end": 18.0, "tip_ext": 6.0, "hinge_ext": 9.0}


def arm_mass_props(p: DesignParams, L1: float, L2: float) -> dict:
    """Mass (g), centre of mass along the long side from the pivot (mm,
    negative = short side) and inertia about the pivot (g·mm²), from the
    outline in arm_widths, integrated in 1 mm strips (holes ignored)."""
    w = arm_widths(p)
    rho = eff_density(max(p.infill, 0.4)) / 1000.0  # g/mm³; the arm prints with 4 walls, 40 %
    t = p.arm_thickness
    s0, s1 = -(L2 + w["hinge_ext"]), L1 + w["tip_ext"]
    n = max(50, int(s1 - s0))
    ds = (s1 - s0) / n
    m = ms = I = 0.0
    for i in range(n):
        s = s0 + (i + 0.5) * ds
        if s >= 0:
            width = w["hub"] + (w["tip"] - w["hub"]) * min(1.0, s / L1)
        else:
            width = w["hub"] + (w["hinge_end"] - w["hub"]) * min(1.0, -s / L2)
        dm = rho * t * width * ds
        m += dm
        ms += dm * s
        I += dm * (s * s + width * width / 12)
    return {"mass": m, "com": ms / m, "inertia": I}


def pick_length(need: float, options: list[int]) -> int | None:
    return next((L for L in options if L >= need), None)


def _seg_dist(px, pz, ax, az, bx, bz) -> tuple[float, float]:
    """Distance from a point to segment a-b, and how far along it (0-1)."""
    dx, dz = bx - ax, bz - az
    u = max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / (dx * dx + dz * dz)))
    return math.hypot(px - ax - u * dx, pz - az - u * dz), u


def bucket_clear_at(L2: float, alpha: float, D: float, hd: float, hw_hinge: float, hw_hub: float,
                    r_axle: float, top: float = 0.0) -> float:
    """Smallest gap (mm) at rest between the bucket's top (`top` mm above its
    rim: the cap) and the arm or whatever sits on the axle. The bucket hangs
    straight down from the hinge; the arm runs from the hinge down to the
    axle at alpha and on past it (the long side), which a long bucket can
    reach under."""
    ax, az = -L2 * math.cos(alpha), -L2 * math.sin(alpha)  # the axle, from the hinge
    bx, bz = 2 * ax, 2 * az                                  # a way along the long side
    pts = [(-D / 2 + D * i / 20, -hd + top) for i in range(21)]
    pts += [(-D / 2, -hd - i * 4.0) for i in range(11)]       # the back wall
    worst = 1e9
    for px, pz in pts:
        dist, u = _seg_dist(px, pz, 0.0, 0.0, ax, az)
        worst = min(worst, dist - (hw_hinge + (hw_hub - hw_hinge) * u))
        dist, _ = _seg_dist(px, pz, ax, az, bx, bz)
        worst = min(worst, dist - hw_hub)
        worst = min(worst, math.hypot(px - ax, pz - az) - r_axle)
    return worst


def derive(p: DesignParams, extra_clear: float = 0.0) -> Derived:
    """All the shared dimensions; raises DesignError for a design that
    can't work, with what to change. `extra_clear` raises the axle when the
    simulated swing shows the bucket dipping too close to the deck."""
    if p.cw_fill not in FILLS:
        raise DesignError(f"Unknown counterweight fill {p.cw_fill!r}.")
    if p.axle not in AXLES:
        raise DesignError(f"Unknown axle option {p.axle!r}.")
    if not (120 <= p.arm_length <= 400):
        raise DesignError("Arm length should be 120 to 400 mm for the desk-size kit.")
    if not (2.0 <= p.arm_ratio <= 6.0):
        raise DesignError("Arm ratio should be between 2:1 and 6:1.")
    if not (0.4 <= p.sling_ratio <= 1.4):
        raise DesignError("Sling length should be 0.4 to 1.4 times the long side of the arm.")
    if not (50 <= p.cw_mass <= 3000):
        raise DesignError("Counterweight should be 50 to 3000 g.")
    if not (0.0 <= p.clearance <= 0.6):
        raise DesignError("Extra clearance should be 0 to 0.6 mm.")
    notes: list[str] = []
    c = p.clearance

    L2 = p.arm_length / (1 + p.arm_ratio)
    L1 = p.arm_length - L2
    Ls = p.sling_ratio * L1
    d_p, m_p = projectile_of(p)
    r_p = d_p / 2

    # Base: two cross members snap through slots in the frame rails, and the
    # trough deck (a plain 3 mm strip) sits on pegs on top of them, flush with
    # the rail tops. Strip and members make a ladder that holds the frames square.
    rail_h, plate_t = 14.0, 3.0
    deck_z0 = rail_h / 2 + MEMBER_H / 2 - DECK_SEAT   # channels under the deck drop it over the members
    z_trough = deck_z0 + plate_t
    frame_t = max(p.frame_thickness, 9.0) if p.axle == "608" else p.frame_thickness
    if not (5.0 <= frame_t <= 12.0):
        raise DesignError("Frame thickness should be 5 to 12 mm.")
    aw = arm_widths(p)

    # Pins and the holes they turn in.
    axle_d = AXLES[p.axle]["pin_d"]
    pins = {
        "axle_d": axle_d, "axle_hole": axle_d + 2 * (RUN_CLEAR + c),
        "hinge_d": HINGE_PIN_D, "hinge_hole": HINGE_PIN_D + 2 * (RUN_CLEAR + c),
        "trigger_d": TRIGGER_PIN_D, "trigger_hole": TRIGGER_PIN_D + 2 * (RUN_CLEAR + c),
        "head_t": 2.5, "barb_len": 5.3,  # how far a snap pin sticks out past what it holds
    }
    pins["spacer_od"] = 12.0 if p.axle == "608" else axle_d + 8.0   # 608: the inner race only
    pins["sleeve_od"] = HINGE_PIN_D + 6.0

    # Counterweight bucket: a box with a 45° "hip roof" inside its top (prints
    # without support) and a fill hole big enough for a quarter, closed by a
    # push-in cap; an ear on each side wall holds the hinge pin. Sleeves on the
    # pin centre the arm between the ears. As wide as asked, as tall as the
    # fill needs. (A full sliding lid took 3000 mm² of plate the kit can't spare.)
    wall, floor, ear_t, cap_t = 2.4, 2.4, 1.6, 1.6  # ear_t: added outside the wall
    W = p.bucket_width
    if not (30 <= W <= 120):
        raise DesignError("Bucket width should be 30 to 120 mm.")
    if W - 2 * wall < p.arm_thickness + 10:
        raise DesignError("The bucket is too narrow for the arm between its ears; make it wider.")
    vol_needed = p.cw_mass / FILLS[p.cw_fill]["density"] * 1000 * 1.12  # mm³, 12% headroom

    def bucket_height(D):
        a, b = D - 2 * wall, W - 2 * wall
        roof = max(0.0, (min(a, b) - FILL_HOLE) / 2)
        v_roof = a * b * roof - (a + b) * roof ** 2 + 4 * roof ** 3 / 3
        level = max(0.0, vol_needed - v_roof) / (a * b)
        return max(22.0, floor + level + roof + 3.0 + 1.0), roof, level  # 3 mm neck, 1 mm headroom

    D = W
    Hb, roof_h, fill_h = bucket_height(D)
    if Hb > 1.1 * W:
        # Too tall: grow it along X (it hangs lower and the axle goes up otherwise).
        while Hb > 1.1 * W and D < 1.6 * W:
            D += 1.0
            Hb, roof_h, fill_h = bucket_height(D)
        notes.append("The counterweight bucket was lengthened along the throw to keep it from getting too tall.")
    W_out = W + 2 * ear_t
    # The frames sit outside the bucket, its pin's head and snap end, with room to swing.
    gap = max(W_out + 2 * (pins["barb_len"] + 2.5), p.arm_thickness + 2 * 6.0)
    r_axle = max(pins["spacer_od"] / 2, aw["hub"] / 2) + 3.0

    # Start angle and axle height depend on each other. The bucket hangs from
    # the hinge low enough that its rim clears the arm's short side and the
    # axle spacers at rest (the first design put the bucket through them),
    # its bottom clears the deck with the short arm straight down, and the
    # arm's tip can't start below the trough.
    if not (25 <= p.start_angle <= 70):
        raise DesignError("Start angle should be 25 to 70 degrees below level.")
    swing_clear = 5.0 + extra_clear  # plan() checks the real lowest point from the simulated swing
    tip_min = z_trough + r_p
    hd_min = aw["hinge_end"] / 2 + cap_t + 2.0   # the arm's hinge end clears the cap
    alpha = math.radians(p.start_angle)
    for _ in range(30):
        hd = hd_min
        while bucket_clear_at(L2, alpha, D, hd, aw["hinge_end"] / 2, aw["hub"] / 2, r_axle, cap_t) < 3.0 and hd < 400:
            hd += 0.5
        H = z_trough + swing_clear + hd + Hb + L2
        if H - L1 * math.sin(alpha) >= tip_min - 1e-6:
            break
        if H - tip_min >= L1 - 5:
            raise DesignError(
                f"The long side of the arm ({L1:.0f} mm) can't reach down to the trough from an axle {H:.0f} mm up "
                "(the counterweight bucket needs that height to swing clear). Make the arm longer or the arm ratio "
                "higher, use less counterweight or a denser fill, or widen the bucket so it is shorter.")
        alpha = math.asin((H - tip_min) / L1)
    if abs(math.degrees(alpha) - p.start_angle) > 0.5:
        notes.append(f"The arm starts {math.degrees(alpha):.0f}° below level (not {p.start_angle:.0f}°) so its tip "
                     "stays above the trough.")
    tip_z0 = H - L1 * math.sin(alpha)
    drop = tip_z0 - (z_trough + r_p)
    if drop > Ls - 10:
        raise DesignError(
            f"The sling ({Ls:.0f} mm) is too short to reach the trough from the arm's tip ({tip_z0:.0f} mm up). "
            "Make the sling longer or the start angle steeper.")

    # Masses: bucket walls print near solid.
    rho = eff_density(max(p.infill, 0.4)) / 1000
    shell_vol = W * D * Hb - (W - 2 * wall) * (D - 2 * wall) * (Hb - floor - roof_h) \
        - FILL_HOLE ** 2 * 3.0 + 2 * ear_t * 18 * (Hb + hd)
    m_bucket = shell_vol * rho
    m_cap = (FILL_HOLE + 6) ** 2 * cap_t * rho + FILL_HOLE ** 2 * 1.5 * rho
    # Centre of mass below the hinge: fill sits on the floor.
    fill_c = hd + Hb - floor - fill_h / 2
    shell_c = hd + Hb * 0.5
    Lc = (p.cw_mass * fill_c + m_bucket * shell_c + m_cap * hd) / (p.cw_mass + m_bucket + m_cap)
    m_cw = p.cw_mass + m_bucket + m_cap

    x_tip0 = -L1 * math.cos(alpha)
    x_p0 = x_tip0 + math.sqrt(Ls ** 2 - drop ** 2)

    # Base: the rails run from behind the tip to past the projectile and the
    # bucket at rest; the tower stands on them under the axle.
    x_hinge0 = L2 * math.cos(alpha)
    x_back = x_tip0 - 8
    x_front = max(x_p0 + r_p + 20, x_hinge0 + D / 2 + 10, 0.5 * H)
    # The projectile only slides a little way before the sling lifts it (about
    # 25 mm for the default), so the deck starts 40 mm behind it and ends a
    # little past it; the cords can lie on the table. The two cross members
    # under its ends are what tie the frames together.
    deck_x = (max(x_back + 16, x_p0 - r_p - 40), min(x_front - 4, x_p0 + r_p + 15))
    if deck_x[1] - deck_x[0] < 50:
        deck_x = (deck_x[1] - 50, deck_x[1])
    member_x = [deck_x[0] + 6, deck_x[1] - 6]
    # Trigger: a printed pin through the frame's top into a hole in the arm,
    # 22 mm out along the long side. Near the axle it holds about 5 N for the
    # default design, and the frame needs no lug sticking up at the back
    # (with one, two frames don't nest on one plate beside a full-length arm).
    s_trigger = 22.0

    arm = {**aw, **arm_mass_props(p, L1, L2)}

    # Sling: printed pouch (the ball sits in its hole) and two cords. Knot to
    # knot, the tip cord runs from the hole at the arm's tip to the pouch, and
    # the ring cord from the pouch to the release ring on the hook.
    pouch_L = 2.2 * d_p + 14
    pouch_w = max(22.0, 1.2 * d_p)
    hole_off = pouch_L / 2 - 4
    tip_cord = max(30.0, Ls - hole_off)
    ring_cord = max(25.0, tip_cord - 9)
    sling = {"pouch_L": pouch_L, "pouch_w": pouch_w, "pouch_hole": 0.55 * d_p, "cord_hole_off": hole_off,
             "tip_cord": tip_cord, "ring_cord": ring_cord}

    # Bolts, for the M8 options. Head + washer, frame, spacer, arm, spacer, frame, washer + nyloc.
    m8_need = 2 * frame_t + gap + 2 * 1.6 + 8 + 2
    bolts = {"m8_length": pick_length(m8_need, M8_LENGTHS), "m8_need": round(m8_need, 1)}
    if p.axle != "printed" and bolts["m8_length"] is None:
        notes.append(f"The axle needs {m8_need:.0f} mm of M8 threaded rod (longer than stock bolts).")

    pins["axle_grip"] = 2 * frame_t + gap
    pins["hinge_grip"] = W_out
    pins["spacer_len"] = (gap - p.arm_thickness) / 2 - 0.4 + ((frame_t - 7.0) / 2 if p.axle == "608" else 0.0)
    pins["sleeve_len"] = (W - 2 * wall - p.arm_thickness) / 2 - 0.4

    bucket = {"W": W, "W_out": W_out, "D": D, "H": Hb, "wall": wall, "floor": floor, "ear_t": ear_t,
              "ear_w": 18.0, "cap_t": cap_t, "roof_h": roof_h, "hole": FILL_HOLE, "fill_h": fill_h,
              "volume_cm3": vol_needed / 1000}
    return Derived(L1=L1, L2=L2, Ls=Ls, r_p=r_p, m_p=m_p, rail_h=rail_h, plate_t=plate_t, deck_z0=deck_z0,
                   z_trough=z_trough, frame_t=frame_t, gap=gap, H=H, alpha=alpha, bucket=bucket, hinge_drop=hd,
                   Lc=Lc, m_cw=m_cw, m_bucket=m_bucket + m_cap, arm=arm, x_back=x_back, x_front=x_front,
                   x_tip0=x_tip0, x_p0=x_p0, s_trigger=s_trigger, deck_x=deck_x, member_x=member_x,
                   pins=pins, sling=sling, bolts=bolts, notes=notes)
