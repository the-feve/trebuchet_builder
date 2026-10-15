"""Design -> parts, throw estimate, hardware list and checks."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .hardware import bill_of_materials
from .params import DesignError, DesignParams, Derived, derive, eff_density
from .parts import (Part, arm, ball, bucket_parts, cross_members, frames, hardware, pin_gauge, spacers,
                    trigger_pin, trough)
from .physics import Machine, Throw, simulate


@dataclass
class Plan:
    """Everything except the solids: fast (well under a second)."""
    params: DesignParams
    derived: Derived
    machine: Machine
    throw: Throw
    pin_angle: float               # what the gauge is cut to
    notes: list = field(default_factory=list)


@dataclass
class Trebuchet:
    plan: Plan
    parts: list[Part]
    bed_problems: list[str]

    @property
    def printed(self) -> list[Part]:
        return [p for p in self.parts if not p.hardware]

    def mass_g(self) -> dict[str, float]:
        rho = eff_density(self.plan.params.infill) / 1000
        return {p.name: p.local.volume * rho * p.qty for p in self.printed}


def plan(p: DesignParams) -> Plan:
    d = derive(p)
    m = Machine.from_derived(d)
    th = simulate(m, p.release_angle)
    pin = p.release_angle if p.release_angle is not None else (th.best_release_angle_deg or 45.0)
    return Plan(p, d, m, th, pin, list(d.notes))


def fits_bed(size_x: float, size_y: float, bed: float) -> bool:
    """Square bed; a part can also lie corner to corner."""
    a, b = max(size_x, size_y), min(size_x, size_y)
    if a <= bed and b <= bed:
        return True
    return (a + b) / math.sqrt(2) <= bed


def build(p: DesignParams, pl: Plan | None = None) -> Trebuchet:
    pl = pl or plan(p)
    d = pl.derived
    parts: list[Part] = [*frames(p, d), cross_members(p, d), trough(p, d), arm(p, d), *bucket_parts(p, d),
                         spacers(p, d), trigger_pin(p, d), pin_gauge(p, d, pl.pin_angle)]
    if p.projectile == "printed_ball":
        parts.append(ball(p, d))
    parts += hardware(p, d)
    problems = []
    for part in parts:
        if part.hardware:
            continue
        bb = part.local.bounding_box()
        if not fits_bed(bb.size.X, bb.size.Y, p.print_bed):
            problems.append(f"{part.name} is {bb.size.X:.0f} × {bb.size.Y:.0f} mm and won't fit a {p.print_bed:.0f} mm bed.")
        if bb.size.Z > p.print_bed:
            problems.append(f"{part.name} is {bb.size.Z:.0f} mm tall; more than the printer's {p.print_bed:.0f} mm.")
    return Trebuchet(pl, parts, problems)


__all__ = ["DesignError", "DesignParams", "Plan", "Trebuchet", "build", "plan", "bill_of_materials", "fits_bed"]
