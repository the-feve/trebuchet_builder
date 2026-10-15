"""Print settings and assembly steps, in plain words, for the report and
build_notes.txt."""

from __future__ import annotations

from .params import FILLS, DesignParams, Derived, in_sentence

PRINT_NOTES = {
    "Frame_Right": "Flat, as exported. 4 walls, 30% infill: it carries the axle.",
    "Frame_Left": "Flat, as exported (it is the mirror image of the right frame).",
    "Cross_Member": "Print 3, standing as exported. 3 walls so the screws bite.",
    "Trough": "Flat. Any infill.",
    "Arm": "Flat, as exported. 4 walls, 40% infill: it takes the most force.",
    "Bucket": "Upright, open side up. 3 walls; no supports needed.",
    "Bucket_Lid": "Print 2, cover side down.",
    "Axle_Spacer": "Print 2, standing.",
    "Trigger_Pin": "Flat, 100% infill.",
    "Pin_Gauge": "Flat. Any settings.",
    "Ball": "Flat side down. Print a few: they get lost.",
}


def assembly_steps(p: DesignParams, d: Derived, pin_angle: float) -> list[str]:
    steps = [
        "Print the parts (settings in the parts list). PLA is fine. Clean any strings out of the holes.",
    ]
    if p.axle == "608":
        steps.append("Press a 608 bearing into the pocket on the inside of each frame (a vise or a flat board "
                     "helps). The lip on the outside stops it going through.")
    steps += [
        "Screw the three cross members between the frames' bottom rails (M3 screws through the frames into the "
        "member ends). The bearing pockets face each other.",
        "Lay the trough plate on the cross members, trigger post to the back, and screw it down (4 screws).",
        "Bolt the bucket to the short end of the arm: M4 bolt through one hanger plate, the arm, the other plate; "
        "washers both sides; lock nut just snug so the bucket swings freely.",
        "Slide the arm onto the M8 bolt with a spacer each side, then the bolt through both bearings (head on "
        "one side, washer and lock nut on the other). Tighten until the frames are square, no more: the arm "
        "must swing freely.",
        f"Push the release pin (2 mm nail or paper clip) into the hole at the arm's tip, leave about 12 mm "
        f"sticking out, and bend it to {pin_angle:.0f}° using the printed gauge. Bend it toward the side the "
        "sling hangs from when the arm is down.",
        f"Make the sling: two cords about {d.Ls / 10:.1f} cm long, each tied to one end of the pouch. Tie one cord "
        "through the small hole near the arm's tip; put a small ring (or a tied loop) on the other cord's end.",
        f"Fill the bucket with {p.cw_mass:.0f} g of {in_sentence(FILLS[p.cw_fill]['label'])} (weigh it) and press "
        "the lids in. Tape them if they're loose.",
        "To load: pull the arm down, loop the trigger cord round the arm near the tip and over the trigger pin "
        "in the post. Put the projectile in the pouch on the trough, the ring over the release pin, and lay "
        "the sling straight forward along the trough.",
        "Everyone behind the machine and to the side, safety glasses on, nothing in front for 15 m. Pull the "
        "trigger pin.",
        "Tuning: if the shot goes high or backwards it let go too early: bend the pin straighter (smaller "
        "angle). If it slams into the ground it let go too late: bend it more. Change the sling length in "
        "small steps too.",
    ]
    return steps


SAFETY = [
    "Grown-up supervision. Safety glasses for everyone nearby.",
    "Never aim at people, animals, windows or anything breakable.",
    "Keep hands and faces out of the arm's swing; the arm swings hard and fast.",
    "Load it with the trigger in place, and only when everyone is behind the machine.",
    "Throw soft or light things indoors; use marbles only outdoors with a clear field.",
]
