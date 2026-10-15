"""The test-throw page and the plan data it draws the arc from."""

import math

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_throw_page_served():
    r = client.get("/throw")
    assert r.status_code == 200 and "Test throw" in r.text
    # Relative URLs only: the page also runs under /trebuchet/ in the Rocket Builder app.
    assert "fetch('api/plan'" in r.text and "fetch('/api" not in r.text


def test_plan_has_what_the_arc_needs():
    """The arc starts where the swing's last frame puts the ball, ends on the
    table at the reported distance, and peaks at the reported height."""
    r = client.post("/api/plan", json={}).json()
    t, a = r["throw"], r["anim"]
    assert t["ok"] and t["expected_m"][0] < t["range_m"]
    path = t["path"]
    assert abs(path[-1][0] - t["range_m"]) < 0.05 and abs(max(z for _, z in path) - t["peak_height_m"]) < 0.02
    _, th, _, sg = a["frames"][-1]
    k = 1e-3
    ball = (a["L1"] * k * math.cos(th) + a["Ls"] * k * math.cos(sg), a["H"] * k + a["L1"] * k * math.sin(th) + a["Ls"] * k * math.sin(sg))
    assert math.dist(ball, path[0]) < 0.01


def test_more_counterweight_throws_farther():
    near = client.post("/api/plan", json={"cw_mass": 200}).json()["throw"]["range_m"]
    far = client.post("/api/plan", json={"cw_mass": 700}).json()["throw"]["range_m"]
    assert far > near
