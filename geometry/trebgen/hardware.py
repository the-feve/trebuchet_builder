"""What to buy besides the printed parts. Each item has a `key` that the
supplies list (server/treb_gear.json, Amazon links) matches on.

The default kit needs no hardware at all: printed snap pins, printed
trigger, printed sling pouch and ring. Only string, the counterweight fill
and (if not printed) the projectiles are bought. The M8 bolt and 608
bearings are options for a smoother axle."""

from __future__ import annotations

from .params import FILLS, PROJECTILES, DesignParams, Derived, in_sentence


def bill_of_materials(p: DesignParams, d: Derived, pin_angle: float) -> list[dict]:
    b = d.bolts
    s = d.sling
    items = []

    def add(key, qty, name, spec, why, household=False):
        """household: something most people have (coins, string): no shop link needed."""
        items.append({"key": key, "qty": qty, "name": name, "spec": spec, "why": why, "household": household})

    if p.axle != "printed":
        m8 = f"M8 × {b['m8_length']} mm" if b["m8_length"] else f"M8 threaded rod, {b['m8_need']:.0f} mm"
        add("m8_bolt", 1, "Axle bolt", f"{m8} hex bolt (or longer), M8 nylon-insert lock nut, 2 M8 washers",
            "The axle the arm swings on (instead of the printed pin).")
    if p.axle == "608":
        add("608_bearing", 2, "608 bearings", "8 × 22 × 7 mm (skateboard / fidget-spinner size)",
            "Press into the frames so the arm spins freely: the biggest single gain in throw distance.")
    cord_cm = round((s["tip_cord"] + s["ring_cord"] + 120) / 10)
    add("sling_cord", 1, "Sling cord", f"Braided fishing line (20 lb+) or thin kite string, about {cord_cm} cm",
        f"Two cords: {s['tip_cord'] / 10:.1f} cm (arm tip to pouch) and {s['ring_cord'] / 10:.1f} cm (pouch to "
        "ring), knot to knot, plus some for the knots. The notches under a frame rail measure them.")
    add("trigger_cord", 1, "Trigger cord", "About 1 m of any strong string",
        "Tied to the trigger pin's ring, so you can pull it from beside the machine.")
    fill = FILLS[p.cw_fill]["label"]
    add(f"fill_{p.cw_fill}", 1, "Counterweight fill", f"{p.cw_mass:.0f} g of {in_sentence(fill)}",
        f"Fills the bucket (about {d.bucket['volume_cm3']:.0f} cm³); weigh it on a kitchen scale.",
        household=p.cw_fill == "coins")
    if p.projectile != "printed_ball":
        add(f"proj_{p.projectile}", 1, "Projectiles", PROJECTILES[p.projectile]["label"],
            "What you throw. Several, because they get lost.")
    add("safety_glasses", 1, "Safety glasses", "Any impact-rated pair", "For everyone near the throw.")
    return items
