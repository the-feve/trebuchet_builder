import io
import itertools
import math
import zipfile

import numpy as np
import pytest
from build123d import Axis, Box

from trebgen import layout
from trebgen.build import SWING_MARGIN, bucket_low_point, build, fits_bed, plan
from trebgen.export import plate_3mf
from trebgen.hardware import bill_of_materials
from trebgen.params import MEMBER_H, RUN_CLEAR, SLOT_CLEAR, DesignError, DesignParams, derive
from trebgen.parts import PIN_BARB, PIN_SPLIT_LEN, PRONG_L, SPLIT, TENON_BARB, arm_local, cord_notches
from trebgen.physics import G, Machine, simulate, swing


@pytest.fixture(scope="module")
def default():
    return build(DesignParams())


def energy(m: Machine, q, qd) -> float:
    """Total mechanical energy (J): arm + counterweight + projectile."""
    E = 0.5 * m.I_arm * qd[0] ** 2 + m.m_arm * G * (m.H + m.d_arm * math.sin(q[0]))
    for mass, terms in m._points():
        p = m._pos(terms, q)
        v = m._jac(terms, q) @ qd
        E += 0.5 * mass * (v @ v) + mass * G * (m.H + p[1])
    return E


# ---------------------------------------------------------------- physics
def test_energy_is_conserved_through_the_swing():
    """No friction in the model: the trough's push does no work (it is
    perpendicular to the motion), so energy must stay constant."""
    d = derive(DesignParams())
    m = Machine.from_derived(d)
    sw = swing(m)
    E = [energy(m, q, qd) for q, qd in zip(sw.q, sw.qd)]
    assert sw.liftoff_t is not None
    assert max(E) - min(E) < 1e-4 * abs(E[0]) + 1e-5


def test_default_throw_is_sensible():
    pl = plan(DesignParams())
    th = pl.throw
    assert th.ok, th.problem
    assert 4 < th.range_m < 15                  # a desk trebuchet: metres, not centimetres or 100 m
    assert 0.4 < th.efficiency < 0.85           # hinged counterweights manage 60-75 %
    assert 20 < th.launch_angle_deg < 55
    assert th.range_m <= th.best_range_m + 1e-9  # the default releases at the best angle


def test_release_angle_matters():
    best = plan(DesignParams()).throw
    early = plan(DesignParams(release_angle=best.best_release_angle_deg + 40)).throw
    assert (early.range_m or 0) < best.range_m


def test_more_counterweight_throws_farther():
    a = plan(DesignParams(cw_mass=250)).throw.range_m
    b = plan(DesignParams(cw_mass=500)).throw.range_m
    assert b > a


def test_too_light_counterweight_reports_a_problem():
    th = plan(DesignParams(cw_mass=50, projectile="custom", projectile_mass=60, projectile_diameter=40)).throw
    assert not th.ok and th.problem


@pytest.mark.parametrize("kw", [dict(arm_length=100), dict(cw_fill="gold"), dict(arm_length=130, cw_mass=3000, cw_fill="rice"),
                                dict(axle="nail"), dict(clearance=2)])
def test_impossible_designs_raise(kw):
    with pytest.raises(DesignError):
        plan(DesignParams(**kw))


# ---------------------------------------------------------------- parts
def test_default_parts_are_valid_flat_and_supportless(default):
    names = {p.name for p in default.printed}
    assert {"Frame", "Arm", "Bucket", "Bucket_Cap", "Trough", "Cross_Member", "Axle_Pin", "Hinge_Pin",
            "Trigger_Pin", "Sling_Pouch", "Release_Ring"} <= names
    for p in default.printed:
        assert len(p.local.solids()) == 1, p.name
        assert p.local.is_valid, p.name
        assert p.local.tessellate(0.1, 0.3)[1], p.name    # OpenCascade's is_valid alone isn't enough
        bb = p.local.bounding_box()
        assert abs(bb.min.Z) < 0.05, f"{p.name} isn't resting on the bed"
        assert len(p.placements) == p.qty, p.name


def test_no_hardware_in_the_default_kit(default):
    assert not [p for p in default.parts if p.hardware and p.role != "cord"]  # the cords are string
    keys = {i["key"] for i in bill_of_materials(default.plan.params, default.plan.derived, default.plan.pin_angle)}
    assert "m8_bolt" not in keys and "608_bearing" not in keys
    assert {"sling_cord", "trigger_cord", "fill_coins", "safety_glasses"} <= keys


@pytest.mark.parametrize("kw", [dict(), dict(axle="608"), dict(cw_mass=600), dict(bucket_width=40),
                                dict(arm_ratio=5), dict(arm_length=150), dict(projectile="ping_pong")])
def test_assembled_parts_dont_intersect(kw):
    """The first versions were valid solids that went through each other (the
    bucket through the axle spacers, then the arm through the bucket)."""
    t = build(DesignParams(**kw), layout=False)
    placed = [(f"{p.name}#{i}", s) for p in t.parts if p.role != "cord" for i, s in enumerate(p.placements)]
    clash = [(a, b) for (a, sa), (b, sb) in itertools.combinations(placed, 2) if (sa & sb).volume > 0.5]
    assert not clash, clash


def test_bucket_clears_the_deck_through_the_swing():
    for kw in (dict(), dict(bucket_width=60), dict(cw_mass=600)):
        pl = plan(DesignParams(**kw))
        assert bucket_low_point(pl.derived, pl.throw) >= pl.derived.z_trough + SWING_MARGIN - 1e-6, kw


def test_snaps_catch_and_bend_gently(default):
    """Each barb must stand proud of its slot or hole (or it won't hold), and
    the prong's bend to get in must stay well under PLA's ~3 % strain."""
    d, c = default.plan.derived, default.plan.params.clearance
    # Tenons: per side, the barb past the slot's edge is also how far each prong bends.
    catch = TENON_BARB - (SLOT_CLEAR + c)
    assert catch >= 0.4
    prong_w, flex_len = (MEMBER_H - SPLIT) / 2, 14 + d.frame_t
    assert 1.5 * prong_w * catch / flex_len ** 2 < 0.015
    # Pins: the barb's radius past the hole's.
    catch = PIN_BARB - (RUN_CLEAR + c)
    assert catch >= 0.6
    for dia in (d.pins["axle_d"], d.pins["hinge_d"]):
        half = (dia - SPLIT) / 2
        assert 1.5 * half * catch / PIN_SPLIT_LEN ** 2 < 0.015


def test_pins_turn_freely_in_their_holes(default):
    pins = default.plan.derived.pins
    for pin, hole in (("axle_d", "axle_hole"), ("hinge_d", "hinge_hole"), ("trigger_d", "trigger_hole")):
        assert pins[hole] - pins[pin] >= 2 * RUN_CLEAR - 1e-9


def test_release_hook_points_at_the_release_angle(default):
    """The prong leaves the tip at the pin angle toward the sling's side (+y)."""
    p, d = default.plan.params, default.plan.derived
    a = arm_local(p, d, 40.0)
    probe = Box(1, 1, 1).translate((d.L1 + 1 + (PRONG_L - 2) * math.cos(math.radians(40)),
                                    (PRONG_L - 2) * math.sin(math.radians(40)), 2.5))
    assert (a & probe).volume > 0.9
    off = Box(1, 1, 1).translate((d.L1 + 1 + (PRONG_L - 2) * math.cos(math.radians(40)),
                                  -(PRONG_L - 2) * math.sin(math.radians(40)), 2.5))
    assert (a & off).volume < 1e-6


def test_cord_notches_measure_the_sling(default):
    d = default.plan.derived
    x0, x_ring, x_tip = cord_notches(d)
    assert x_ring - x0 == pytest.approx(d.sling["ring_cord"])
    assert x_tip - x0 == pytest.approx(d.sling["tip_cord"])
    assert d.x_back < x0 and x_tip < d.x_front


# ---------------------------------------------------------------- the plate
def test_default_kit_fits_one_220_plate(default):
    assert default.bed_problems == []
    assert len(default.plates) == 1
    plate = default.plates[0]
    want = sum(p.qty for p in default.printed)
    assert len(plate.placed) == want
    for pc in plate.placed:
        bb = pc.solid.bounding_box()
        assert bb.min.X >= layout.MARGIN - 0.6 and bb.min.Y >= layout.MARGIN - 0.6, pc.name
        assert bb.max.X <= 220 - layout.MARGIN + 0.6 and bb.max.Y <= 220 - layout.MARGIN + 0.6, pc.name
        assert abs(bb.min.Z) < 0.05, pc.name
    for a, b in itertools.combinations(plate.placed, 2):
        assert (a.solid & b.solid).volume < 1e-3, (a.name, b.name)


def test_plate_3mf_has_one_named_object_per_part(default):
    z = zipfile.ZipFile(io.BytesIO(plate_3mf(default.plates[0])))
    model = z.read("3D/3dmodel.model").decode()
    import re
    names = set(re.findall(r'<object [^>]*name="([^"]+)"', model))
    assert len(names) == len(default.plates[0].placed)
    assert 'name="Arm"' in model and 'name="Frame_1"' in model and 'name="Frame_2"' in model


def test_raster_turn_matches_the_solid_turn(default):
    """layout.rot_ccw must turn a footprint the way Shape.rotate(Z, 90) turns the part."""
    arm = next(p for p in default.printed if p.name == "Arm").local
    g = layout.rot_ccw(layout.footprint(arm))
    h = layout.footprint(arm.rotate(Axis.Z, 90))
    n = min(g.shape[0], h.shape[0]), min(g.shape[1], h.shape[1])
    assert np.mean(g[:n[0], :n[1]] == h[:n[0], :n[1]]) > 0.97


def test_big_design_spills_to_more_plates_or_is_flagged():
    t = build(DesignParams(arm_length=320, print_bed=180))
    assert t.bed_problems or len(t.plates) > 1


def test_fits_bed_diagonal():
    assert fits_bed(200, 20, 180)       # corner to corner
    assert not fits_bed(250, 150, 220)


def test_bill_of_materials_options():
    for axle, want in (("m8", {"m8_bolt"}), ("608", {"m8_bolt", "608_bearing"})):
        pl = plan(DesignParams(axle=axle))
        keys = {i["key"] for i in bill_of_materials(pl.params, pl.derived, pl.pin_angle)}
        assert want <= keys


def test_sling_cords_join_the_arm_to_the_pouch(default):
    """The preview shows how the sling ties on: the tip cord from the hole by
    the tip to the pouch's back end, the ring cord from the release ring's
    tab (on the hook) to its front end."""
    from trebgen.parts import arm_point, sling_anchors
    from build123d import Vector
    p, d = default.plan.params, default.plan.derived
    parts = {x.name: x for x in default.parts}
    an = sling_anchors(p, d, default.plan.pin_angle)
    arm, ring, pouch = parts["Arm"].placements[0], parts["Release_Ring"].placements[0], parts["Sling_Pouch"].placements[0]
    assert arm.distance_to(Vector(*arm_point(d, *an["tip"]))) < 1.6      # in the tip hole (3 mm)
    assert ring.distance_to(Vector(*arm_point(d, *an["ring"]))) < 1.6    # in the ring's tab hole
    cords = parts["Sling_Cords"].placements
    assert len(cords) == 2 and all(c.distance_to(pouch) < 0.7 for c in cords)
