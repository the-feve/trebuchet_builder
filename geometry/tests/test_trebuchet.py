import math

import numpy as np
import pytest

from trebgen.build import build, fits_bed, plan
from trebgen.hardware import bill_of_materials
from trebgen.params import DesignError, DesignParams, derive
from trebgen.physics import G, Machine, simulate, swing


def energy(m: Machine, q, qd) -> float:
    """Total mechanical energy (J): arm + counterweight + projectile."""
    E = 0.5 * m.I_arm * qd[0] ** 2 + m.m_arm * G * (m.H + m.d_arm * math.sin(q[0]))
    for mass, terms in m._points():
        p = m._pos(terms, q)
        v = m._jac(terms, q) @ qd
        E += 0.5 * mass * (v @ v) + mass * G * (m.H + p[1])
    return E


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
    assert 5 < th.range_m < 15                  # a desk trebuchet: metres, not centimetres or 100 m
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


@pytest.mark.parametrize("kw", [dict(arm_length=100), dict(cw_fill="gold"), dict(arm_length=130, cw_mass=3000, cw_fill="rice")])
def test_impossible_designs_raise(kw):
    with pytest.raises(DesignError):
        plan(DesignParams(**kw))


def test_default_builds_valid_parts_that_fit_a_220_bed():
    t = build(DesignParams())
    assert t.bed_problems == []
    names = {p.name for p in t.printed}
    assert {"Frame_Right", "Frame_Left", "Arm", "Bucket", "Trough", "Cross_Member"} <= names
    for p in t.printed:
        solids = p.local.solids()
        assert len(solids) == 1, p.name
        assert p.local.is_valid, p.name
        bb = p.local.bounding_box()
        assert abs(bb.min.Z) < 0.05, f"{p.name} isn't resting on the bed"
        assert len(p.placements) == p.qty, p.name


def test_bucket_clears_the_axle_at_rest():
    """The first layout put the bucket through the axle spacers."""
    t = build(DesignParams())
    bucket = next(p for p in t.parts if p.name == "Bucket").placements[0]
    for name in ("Axle_Spacer", "Axle_Bolt"):
        for s in next(p for p in t.parts if p.name == name).placements:
            assert (bucket & s).volume < 1e-3, name


def test_big_arm_on_a_small_bed_is_flagged():
    t = build(DesignParams(arm_length=320, print_bed=180))
    assert t.bed_problems


def test_fits_bed_diagonal():
    assert fits_bed(200, 20, 180)       # corner to corner
    assert not fits_bed(250, 150, 220)


def test_bill_of_materials_keys_are_stable():
    pl = plan(DesignParams())
    keys = {i["key"] for i in bill_of_materials(pl.params, pl.derived, pl.pin_angle)}
    assert {"m8_bolt", "608_bearing", "m4_bolt", "m3_screw", "release_pin", "sling_cord", "pouch"} <= keys
