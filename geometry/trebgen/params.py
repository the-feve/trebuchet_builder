"""Design inputs and the dimensions derived from them.

Units are mm and grams here; physics.py works in SI. Assembly axes:
X is the throw direction, Y runs along the main axle, Z is up. The axle
sits at (0, 0, H) and the table is z = 0.

The machine is a hinged-counterweight trebuchet: two flat A-frame sides
joined by cross members at table level, a trough plate the projectile
sits on, a tapered throwing arm on an M8 axle (608 bearings or a plain
hole), and a bucket on an M4 hinge at the short end of the arm.

At rest the long arm points down and back, its tip in line with the
projectile's centre; the sling lies forward along the trough; the
counterweight hangs high on the front side. Pulling the trigger pin lets
the bucket fall, the arm swings up and over, and the sling whips the
projectile off the release pin at the arm's tip.
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
    "608": {"label": "608 skate bearings (smoothest)", "pocket_d": 22.15, "pocket_depth": 7.0, "lip_d": 18.0},
    "plain": {"label": "Plain hole, no bearings", "hole_d": 8.5},
}

# Standard bolt lengths to pick from (mm).
M8_LENGTHS = [40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 180, 200]
M4_LENGTHS = [16, 20, 25, 30, 35, 40, 45, 50]


@dataclass
class DesignParams:
    # The user-facing choices.
    arm_length: float = 200.0         # whole arm, hinge hole to tip (mm)
    arm_ratio: float = 4.0            # long side / short side
    sling_ratio: float = 0.8          # sling length / long side
    cw_mass: float = 350.0            # counterweight fill (g)
    cw_fill: str = "steel_bb"
    projectile: str = "printed_ball"
    projectile_diameter: float = 20.0  # used for "custom"
    projectile_mass: float = 4.0       # used for "custom"
    release_angle: float | None = None  # sling-to-arm angle at release (deg); None = the best one
    start_angle: float = 45.0         # long arm below level at rest (deg)
    axle: str = "608"
    print_bed: float = 220.0          # usable square bed (mm)
    infill: float = 0.25              # 0-1, for the mass estimate
    # Advanced.
    bucket_width: float = 50.0        # across the machine (Y), outside
    arm_thickness: float = 10.0       # along the axle (Y)
    frame_thickness: float = 9.0      # side frames (Y); 7 mm bearing + 2 mm lip
    clearance: float = 0.3            # print clearance for fits

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
    rail_h: float      # base rail height
    plate_t: float     # trough plate thickness
    z_trough: float    # trough top
    gap: float         # inside distance between the side frames
    H: float           # axle height
    alpha: float       # start angle of the long arm below horizontal (rad)
    bucket: dict       # outside sizes and wall
    hinge_drop: float  # hinge to the bucket's rim
    Lc: float          # hinge to the counterweight's centre of mass (filled)
    m_cw: float        # fill + bucket + lids (g)
    m_bucket: float
    arm: dict          # widths and mass properties
    x_back: float      # base extent along X
    x_front: float
    x_tip0: float      # tip at rest
    x_p0: float        # projectile at rest
    members_x: list    # cross member centres
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
    hub = 24.0
    tip = 10.0
    hinge_end = 14.0
    return {"hub": hub, "tip": tip, "hinge_end": hinge_end, "tip_ext": 6.0, "hinge_ext": hinge_end / 2}


def arm_mass_props(p: DesignParams, L1: float, L2: float) -> dict:
    """Mass (g), centre of mass along the long side from the pivot (mm,
    negative = short side) and inertia about the pivot (g·mm²), from the
    outline in arm_widths, integrated in 1 mm strips (holes ignored)."""
    w = arm_widths(p)
    rho = eff_density(p.infill) / 1000.0  # g/mm³
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


def derive(p: DesignParams) -> Derived:
    """All the shared dimensions; raises DesignError for a design that
    can't work, with what to change."""
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
    notes: list[str] = []

    L2 = p.arm_length / (1 + p.arm_ratio)
    L1 = p.arm_length - L2
    Ls = p.sling_ratio * L1
    d_p, m_p = projectile_of(p)
    r_p = d_p / 2

    rail_h, plate_t = 10.0, 3.0
    z_trough = rail_h + plate_t

    # Counterweight bucket: square-ish footprint, as tall as the fill needs.
    wall, floor = 2.4, 2.4
    hanger_t = 3.0                                    # the two hanger plates
    hang_gap = p.arm_thickness + 2 * 0.6              # arm between the plates
    W = p.bucket_width
    if not (30 <= W <= 120):
        raise DesignError("Bucket width should be 30 to 120 mm.")
    D = W                                             # along X
    inner_area = (W - 2 * wall) * (D - 2 * wall) - (hang_gap + 2 * hanger_t) * (D - 2 * wall)
    vol_needed = p.cw_mass / FILLS[p.cw_fill]["density"] * 1000 * 1.12  # mm³, 12% headroom
    fill_h = vol_needed / inner_area
    lid_plug = 4.0
    Hb = max(20.0, fill_h + floor + lid_plug + 1.5)
    if Hb > 1.6 * W:
        # Too tall: grow it along X before it gets silly.
        across = W - 2 * wall - hang_gap - 2 * hanger_t
        target_fill = 1.2 * W - floor - lid_plug - 1.5
        D = max(W, min(2.0 * W, vol_needed / (across * target_fill) + 2 * wall))
        inner_area = (W - 2 * wall - hang_gap - 2 * hanger_t) * (D - 2 * wall)
        fill_h = vol_needed / inner_area
        Hb = max(20.0, fill_h + floor + lid_plug + 1.5)
        notes.append("The counterweight bucket was lengthened along the throw to keep it from getting too tall.")
    # Frames sit just outside the bucket's swing.
    gap = max(W + 2 * 4.0, p.arm_thickness + 2 * 6.0)
    r_spacer = 6.0 if p.axle == "608" else 7.0

    # Start angle and axle height depend on each other: the bucket must hang
    # clear of the axle at rest (on taller hanger plates if it sits under
    # it), its bottom must clear the trough with the short arm straight
    # down, and the arm's tip can't start below the trough.
    if not (25 <= p.start_angle <= 70):
        raise DesignError("Start angle should be 25 to 70 degrees below level.")
    swing_clear = 8.0
    tip_min = z_trough + r_p
    alpha = math.radians(p.start_angle)
    for _ in range(20):
        if L2 * math.cos(alpha) - D / 2 > r_spacer + 3:
            hinge_drop = 8.0
        else:
            hinge_drop = max(8.0, L2 * math.sin(alpha) + r_spacer + 4)
        H = z_trough + swing_clear + hinge_drop + Hb + L2
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
    rho = eff_density(max(p.infill, 0.4)) / 1000  # bucket walls print near solid
    shell_vol = W * D * Hb - (W - 2 * wall) * (D - 2 * wall) * (Hb - floor) + 2 * hanger_t * (D - 2 * wall) * (Hb - floor) \
        + 2 * hanger_t * 20 * (hinge_drop + 7)
    m_bucket = shell_vol * rho
    lid_vol = 2 * ((W - 2 * wall - hang_gap - 2 * hanger_t) / 2 * (D - 2 * wall) * 2.0)
    m_lids = lid_vol * rho
    # Centre of mass below the hinge: fill sits on the floor.
    fill_c = hinge_drop + Hb - floor - fill_h / 2
    shell_c = hinge_drop + Hb * 0.55
    Lc = (p.cw_mass * fill_c + m_bucket * shell_c + m_lids * (hinge_drop + lid_plug)) / (p.cw_mass + m_bucket + m_lids)
    m_cw = p.cw_mass + m_bucket + m_lids

    x_tip0 = -L1 * math.cos(alpha)
    x_p0 = x_tip0 + math.sqrt(Ls ** 2 - drop ** 2)

    # Base: from behind the tip to past the projectile and the bucket at rest.
    x_hinge0 = L2 * math.cos(alpha)
    x_back = x_tip0 - 12
    x_front = max(x_p0 + r_p + 15, x_hinge0 + D / 2 + 10, 0.45 * H + 10)
    members_x = [x_back + 7, 0.0, x_front - 7]

    aw = arm_widths(p)
    arm = {**aw, **arm_mass_props(p, L1, L2)}

    # Bolts. M8 axle: head + washer, frame, spacer, arm, spacer, frame, washer + nyloc.
    m8_need = 2 * p.frame_thickness + gap + 2 * 1.6 + 8 + 2
    m4_need = p.arm_thickness + 1.2 + 2 * hanger_t + 2 * 1.0 + 5 + 1
    bolts = {
        "m8_length": pick_length(m8_need, M8_LENGTHS), "m8_need": round(m8_need, 1),
        "m4_length": pick_length(m4_need, M4_LENGTHS), "m4_need": round(m4_need, 1),
    }
    if bolts["m8_length"] is None:
        notes.append(f"The axle needs {m8_need:.0f} mm of M8 threaded rod (longer than stock bolts).")

    bucket = {"W": W, "D": D, "H": Hb, "wall": wall, "floor": floor, "hanger_t": hanger_t,
              "hang_gap": hang_gap, "fill_h": fill_h, "lid_plug": lid_plug,
              "volume_cm3": vol_needed / 1000}
    return Derived(L1=L1, L2=L2, Ls=Ls, r_p=r_p, m_p=m_p, rail_h=rail_h, plate_t=plate_t, z_trough=z_trough,
                   gap=gap, H=H, alpha=alpha, bucket=bucket, hinge_drop=hinge_drop, Lc=Lc, m_cw=m_cw,
                   m_bucket=m_bucket + m_lids, arm=arm, x_back=x_back, x_front=x_front, x_tip0=x_tip0,
                   x_p0=x_p0, members_x=members_x, bolts=bolts, notes=notes)
