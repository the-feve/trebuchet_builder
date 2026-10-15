"""What to buy besides the printed parts. Each item has a `key` that the
supplies list (Amazon affiliate links, to come) will match on."""

from __future__ import annotations

from .params import FILLS, PROJECTILES, DesignParams, Derived, in_sentence


def bill_of_materials(p: DesignParams, d: Derived, pin_angle: float) -> list[dict]:
    b = d.bolts
    sling_cm = round((2 * d.Ls + 120) / 10)
    items = []

    def add(key, qty, name, spec, why):
        items.append({"key": key, "qty": qty, "name": name, "spec": spec, "why": why})

    m8 = f"M8 × {b['m8_length']} mm" if b["m8_length"] else f"M8 threaded rod, {b['m8_need']:.0f} mm"
    add("m8_bolt", 1, "Axle bolt", f"{m8} hex bolt (or longer), M8 nylon-insert lock nut, 2 M8 washers",
        "The main axle the arm swings on.")
    if p.axle == "608":
        add("608_bearing", 2, "608 bearings", "8 × 22 × 7 mm (skateboard / fidget-spinner size)",
            "Press into the frames so the arm spins freely: the biggest single gain in throw distance.")
    add("m4_bolt", 1, "Hinge bolt", f"M4 × {b['m4_length']} mm bolt, M4 lock nut, 2 M4 washers",
        "Hangs the counterweight bucket from the short end of the arm.")
    add("m3_screw", 10, "Frame screws", "M3 × 12 mm self-tapping screws for plastic (or #4 × 1/2\" sheet-metal screws)",
        "6 hold the cross members to the frames; 4 more hold the trough down (buy a pack).")
    add("release_pin", 1, "Release pin", "A 2 mm nail or a straightened large paper clip, about 20 mm long",
        f"Push it into the hole at the arm's tip and bend it to {pin_angle:.0f}° with the printed gauge.")
    add("sling_cord", 1, "Sling cord", f"Braided fishing line (20 lb+) or thin kite string, about {sling_cm} cm",
        f"Two cords of {d.Ls / 10:.1f} cm (tip to pouch) plus knots.")
    add("pouch", 1, "Sling pouch", "A 30 × 50 mm piece of thin leather, felt or denim",
        "Cradles the projectile; punch a small hole at each end for the cords.")
    add("ring", 1, "Release ring", "A small split key ring (10–12 mm) or a loop tied in the cord",
        "Slides off the release pin to let go of the projectile.")
    add("trigger_cord", 1, "Trigger cord", "About 20 cm of strong string",
        "A loop round the arm near the tip and over the trigger pin.")
    fill = FILLS[p.cw_fill]["label"]
    add(f"fill_{p.cw_fill}", 1, "Counterweight fill", f"{p.cw_mass:.0f} g of {in_sentence(fill)}",
        f"Fills the bucket (about {d.bucket['volume_cm3']:.0f} cm³); weigh it on a kitchen scale.")
    if p.projectile != "printed_ball":
        add(f"proj_{p.projectile}", 1, "Projectiles", PROJECTILES[p.projectile]["label"],
            "What you throw. Several, because they get lost.")
    add("safety_glasses", 1, "Safety glasses", "Any impact-rated pair", "For everyone near the throw.")
    return items
