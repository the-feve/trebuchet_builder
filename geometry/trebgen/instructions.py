"""Print settings and assembly steps, in plain words, for the report and
build_notes.txt."""

from __future__ import annotations

from .params import FILLS, DesignParams, Derived, in_sentence

PRINT_NOTES = {
    "Frame": "Print 2, flat. 4 walls, 30% infill: they carry the axle. The two are the same part.",
    "Trough": "Flat, channels down. Any infill.",
    "Cross_Member": "Print 2, flat. 4 walls so the snap tenons are solid plastic.",
    "Arm": "Flat. 4 walls, 40% infill: it takes the most force. The release hook is part of it.",
    "Bucket": "Upright, as exported. 3 walls; the roof inside the top and the teardrop hinge holes need no support.",
    "Bucket_Cap": "Flange down.",
    "Axle_Pin": "Lying down, as exported (the flat on the bed). 100% infill. Layers along a pin make it strong.",
    "Hinge_Pin": "Lying down, as exported. 100% infill.",
    "Axle_Spacer": "Print 2, standing.",
    "Hinge_Sleeve": "Print 2, standing.",
    "Trigger_Pin": "Lying down, as exported. 100% infill.",
    "Sling_Pouch": "Flat. PLA works; TPU (flexible) wraps the ball better if you have it.",
    "Release_Ring": "Flat, 100% infill.",
    "Ball": "Flat side down. Print a few: they get lost.",
}

PLATE_NOTE = ("Everything is laid out on one plate in plate_1.3mf (open it in your slicer; each part keeps its "
              "name, so you can give the arm and pins their own settings). PLA, 0.2 mm layers, no supports, "
              "no brim needed. If the snaps are too tight or too loose, change Clearance and build again.")


def assembly_steps(p: DesignParams, d: Derived, pin_angle: float) -> list[str]:
    s = d.sling
    steps = [
        "Print the parts (one plate; settings in the parts list). Clean any strings out of the holes and slots.",
        f"Make the sling first, while the frames are flat: lay the cord along the underside of a frame rail and "
        f"tie knots at the notches. The tip cord runs from the first notch to the far one "
        f"({s['tip_cord'] / 10:.1f} cm), the ring cord from the first to the middle one ({s['ring_cord'] / 10:.1f} cm). "
        "Tie the tip cord to one end of the pouch and the ring cord to the other; tie the release ring onto the "
        "ring cord's free end.",
    ]
    if p.axle == "608":
        steps.append("Press a 608 bearing into the hole at the top of each frame, centred in its thickness "
                     "(a vise or a flat board helps).")
    steps += [
        "Stand the two frames up facing each other, trigger lobes at the same end. Push the two cross members "
        "through the slots in the rails until the split ends click out behind the frames.",
        "Drop the trough deck onto the cross members: the channels underneath sit over them and the pegs come "
        "through the holes.",
        f"Fill the bucket with {p.cw_mass:.0f} g of {in_sentence(FILLS[p.cw_fill]['label'])} (weigh it) through "
        "the hole in its top, and push the cap in.",
        "Hang the bucket on the arm: hinge pin through one ear, a sleeve, the arm's small hole, the other sleeve "
        "and the other ear, until its split end clicks. The bucket should swing freely.",
        "Hold the arm between the frames' top holes with a spacer either side, and push the axle pin through "
        "frame, spacer, arm, spacer, frame until it clicks." if p.axle == "printed" else
        "Hold the arm between the frames with a spacer either side, and push the M8 bolt through; washer and "
        "lock nut on the far side, just snug so the arm turns freely.",
        "Tie the tip cord through the small hole at the arm's tip.",
        f"To load: swing the arm's long end down to the back until the hole near the axle lines up with the "
        f"frame's trigger hole, and push the trigger pin through the frame into the arm. Put the projectile in "
        f"the pouch on the deck, hook the release ring over the arm's release hook (set to {pin_angle:.0f}°), and "
        "lay the sling straight forward along the deck. Tie the trigger cord to the pin's ring.",
        "Everyone behind the machine and to the side, safety glasses on, nothing in front for 15 m. Pull the "
        "trigger cord.",
        "Tuning: if the shot goes high or backwards it let go too early: build again with a smaller release "
        "angle (5° at a time; only the arm needs reprinting). If it slams into the ground it let go too late: "
        "use a bigger angle. A longer sling throws farther until it starts to drag.",
    ]
    return steps


SAFETY = [
    "Grown-up supervision. Safety glasses for everyone nearby.",
    "Never aim at people, animals, windows or anything breakable.",
    "Keep hands and faces out of the arm's swing; the arm swings hard and fast.",
    "Load it with the trigger pin in, and only when everyone is behind the machine. Fire with the cord.",
    "Throw soft or light things indoors; use marbles only outdoors with a clear field.",
]
