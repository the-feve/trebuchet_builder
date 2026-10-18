import io
import zipfile

from fastapi.testclient import TestClient

import app

c = TestClient(app.app)


def test_options_and_page():
    o = c.get("/api/options").json()
    assert "steel_bb" in o["fills"] and "coins" in o["fills"] and "marble" in o["projectiles"]
    assert o["defaults"]["axle"] == "printed" and "printed" in o["axles"]
    page = c.get("/").text
    assert "Trebuchet Builder" in page
    # Relative URLs only: the page also runs under /trebuchet/ in the Rocket Builder app.
    assert 'fetch(\'/api' not in page and '"/static' not in page


def test_pages_are_standalone_beta_with_brand_assets():
    """No Rocket/Trebuchet switcher (each app is its own page, linked from the
    other); Trebuchet Builder is marked beta; fonts and icons are served from
    this app's own static folder, by relative URL."""
    for path in ("/", "/throw", "/supplies"):
        page = c.get(path).text
        assert 'class="apps"' not in page, path
        assert "Beta" in page and "https://rocket.quiverdesignworks.net/" in page, path
        assert "url(/static" not in page and 'href="/static' not in page, path
    assert "in beta" in c.get("/").text
    for f in ("fonts/inter.woff2", "fonts/space-grotesk.woff2", "fonts/LICENSE-inter.txt",
              "brand/tb-favicon.svg", "brand/tb-favicon-32.png", "brand/tb-apple-touch-icon-180.png"):
        assert c.get(f"/static/{f}").status_code == 200, f


def test_plan():
    r = c.post("/api/plan", json={"cw_mass": 400})
    assert r.status_code == 200
    t = r.json()["throw"]
    assert t["ok"] and t["expected_m"][0] < t["range_m"]


def test_plan_rejects_impossible_design():
    r = c.post("/api/plan", json={"arm_length": 130, "cw_mass": 3000, "cw_fill": "rice"})
    assert r.status_code == 422 and "arm" in r.json()["detail"]


def test_build_preview_and_zip():
    r = c.post("/api/build", json={})
    assert r.status_code == 200
    b = r.json()
    assert b["parts"] and b["anim"]["frames"] and b["plastic_g"] > 50
    assert c.get(f"/api/builds/{b['id']}/preview.glb").content[:4] == b"glTF"
    z = zipfile.ZipFile(io.BytesIO(c.get(f"/api/builds/{b['id']}/trebuchet.zip").content))
    names = z.namelist()
    assert "Arm.stl" in names and "Cross_Member_x2.stl" in names and "Frame_x2.stl" in names and "LICENSE.txt" in names
    assert "plate_1.3mf" in names and b["plates"] == 1
    assert z.read("Arm.stl").startswith(b"(c)")  # licence notice in the STL header
    assert "Estimated throw" in z.read("build_notes.txt").decode()


def test_unknown_build_404():
    assert c.get("/api/builds/nope/preview.glb").status_code == 404
