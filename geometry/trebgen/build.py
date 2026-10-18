"""Design -> parts, throw estimate, plate layout, hardware list and checks."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .hardware import bill_of_materials
from .layout import Plate, pack
from .params import DesignError, DesignParams, Derived, derive, eff_density
from .parts import (Part, arm, axle_parts, ball, bucket_parts, cross_member, frames, hardware, hinge_parts,
                    sling_parts, trigger_pin, trough)
from .physics import Machine, Throw, simulate


@dataclass
class Plan:
    """Everything except the solids: fast (well under a second)."""
    params: DesignParams
    derived: Derived
    machine: Machine
    throw: Throw
    pin_angle: float               # what the release hook is set to
    notes: list = field(default_factory=list)


@dataclass
class Trebuchet:
    plan: Plan
    parts: list[Part]
    bed_problems: list[str]
    plates: list[Plate] = field(default_factory=list)

    @property
    def printed(self) -> list[Part]:
        return [p for p in self.parts if not p.hardware]

    def mass_g(self) -> dict[str, float]:
        rho = eff_density(self.plan.params.infill) / 1000
        return {p.name: p.local.volume * rho * p.qty for p in self.printed}


SWING_MARGIN = 2.0  # mm between the swinging bucket and the deck, at its lowest


def plan(p: DesignParams) -> Plan:
    """Dimensions and the throw. The bucket tilts as it swings through the
    bottom, so its corners can dip below where it hangs at rest: if the
    simulated swing brings it within SWING_MARGIN of the deck, the axle goes
    up by the shortfall and it's worked out again."""
    extra = 0.0
    for _ in range(4):
        d = derive(p, extra)
        m = Machine.from_derived(d)
        th = simulate(m, p.release_angle)
        low = bucket_low_point(d, th)
        if low is None or low >= d.z_trough + SWING_MARGIN - 1e-6:
            break
        extra += d.z_trough + SWING_MARGIN - low + 0.5
    else:
        raise DesignError("The counterweight bucket would hit the trough as it swings through. Use a shorter or "
                          "wider bucket (more width, or a denser fill), or a longer arm.")
    pin = p.release_angle if p.release_angle is not None else (th.best_release_angle_deg or 45.0)
    return Plan(p, d, m, th, pin, list(d.notes))


def bucket_low_point(d: Derived, th: Throw) -> float | None:
    """Lowest point (mm above the table) the bucket's bottom corners reach
    during the swing, from the simulated frames (it hangs at angle psi)."""
    if not th.frames:
        return None
    b = d.bucket
    top, bottom = d.hinge_drop, d.hinge_drop + b["H"]
    low = 1e9
    for _, theta, psi, _ in th.frames:
        hx, hz = -d.L2 * math.cos(theta), d.H - d.L2 * math.sin(theta)
        # Bucket axis points along psi (hinge to its centre of mass); its sides are D/2 either side.
        ux, uz = math.cos(psi), math.sin(psi)
        vx, vz = -uz, ux
        for along in (top, bottom):
            for side in (-b["D"] / 2, b["D"] / 2):
                low = min(low, hz + uz * along + vz * side)
    return low


def fits_bed(size_x: float, size_y: float, bed: float) -> bool:
    """Square bed; a part can also lie corner to corner."""
    a, b = max(size_x, size_y), min(size_x, size_y)
    if a <= bed and b <= bed:
        return True
    return (a + b) / math.sqrt(2) <= bed


def make_parts(p: DesignParams, d: Derived, pin_angle: float) -> list[Part]:
    parts: list[Part] = [*frames(p, d), trough(p, d), cross_member(p, d), arm(p, d, pin_angle),
                         *bucket_parts(p, d), *axle_parts(p, d), *hinge_parts(p, d), trigger_pin(p, d),
                         *sling_parts(p, d, pin_angle)]
    if p.projectile == "printed_ball":
        parts.append(ball(p, d))
    return parts + hardware(p, d)


def build(p: DesignParams, pl: Plan | None = None, layout: bool = True) -> Trebuchet:
    pl = pl or plan(p)
    d = pl.derived
    parts = make_parts(p, d, pl.pin_angle)
    problems = []
    for part in parts:
        if part.hardware:
            continue
        bb = part.local.bounding_box()
        if bb.size.Z > p.print_bed:
            problems.append(f"{part.name} is {bb.size.Z:.0f} mm tall; more than the printer's {p.print_bed:.0f} mm.")
    plates: list[Plate] = []
    if layout:
        items = [(part.name, k, part.local) for part in parts if not part.hardware for k in range(part.qty)]
        plates, too_big = pack(items, p.print_bed)
        for name in dict.fromkeys(too_big):
            bb = next(x for x in parts if x.name == name).local.bounding_box()
            problems.append(f"{name} is {bb.size.X:.0f} × {bb.size.Y:.0f} mm and won't fit a {p.print_bed:.0f} mm bed.")
        if len(plates) > 1:
            pl.notes.append(f"The parts need {len(plates)} plates on a {p.print_bed:.0f} mm bed. A shorter arm or "
                            "less counterweight brings it back to one.")
    return Trebuchet(pl, parts, problems, plates)


__all__ = ["DesignError", "DesignParams", "Plan", "Trebuchet", "build", "plan", "bill_of_materials", "fits_bed"]
