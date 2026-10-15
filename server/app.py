"""Trebuchet Builder web app: one page with a three.js preview, backed by
trebgen (geometry + throw physics).

  uvicorn app:app --reload      # http://127.0.0.1:8000

Endpoints:
  GET  /api/options                      choices and defaults for the form
  POST /api/plan                         throw estimate only (fast, no geometry)
  POST /api/build                        geometry + estimate; returns a build id
  GET  /api/builds/{id}/preview.glb      assembled model for the preview
  GET  /api/builds/{id}/trebuchet.zip    print files, build notes, design.json
  GET  /throw                            test-throw page: arm swing and flight arc
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import math
import threading
import time
import zipfile
from collections import OrderedDict, defaultdict, deque
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from trebgen.build import Plan, build as build_trebuchet, plan as plan_trebuchet
from trebgen.export import glb, stl_bytes
from trebgen.hardware import bill_of_materials
from trebgen.instructions import PRINT_NOTES, SAFETY, assembly_steps
from trebgen.params import AXLES, FILLS, PROJECTILES, DesignError, DesignParams, eff_density, projectile_of
from trebgen.physics import REAL_WORLD

import terms

GENERATOR_VERSION = "0.1.0"
SCHEMA_VERSION = 1
HERE = Path(__file__).parent
log = logging.getLogger("trebuchet")

app = FastAPI(title="Trebuchet Builder")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")


class BuildRequest(BaseModel):
    arm_length: float = Field(200, ge=120, le=400)
    arm_ratio: float = Field(4.0, ge=2, le=6)
    sling_ratio: float = Field(0.8, ge=0.4, le=1.4)
    cw_mass: float = Field(350, ge=50, le=3000)
    cw_fill: str = "steel_bb"
    projectile: str = "printed_ball"
    projectile_diameter: float = Field(20, ge=5, le=60)
    projectile_mass: float = Field(4, ge=0.2, le=100)
    release_angle: float | None = Field(None, ge=5, le=120)
    start_angle: float = Field(45, ge=25, le=70)
    axle: str = "608"
    print_bed: float = Field(220, ge=120, le=500)
    infill: float = Field(0.25, ge=0, le=1)
    bucket_width: float = Field(50, ge=30, le=120)
    arm_thickness: float = Field(10, ge=6, le=20)

    def design(self) -> DesignParams:
        return DesignParams(**self.model_dump())


# ---------------------------------------------------------------- guards
_hits: dict[tuple[str, str], deque] = defaultdict(deque)


def _client(request: Request) -> str:
    fwd = request.headers.get("fly-client-ip") or request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "?")


def _rate_limit(request: Request, kind: str, limit: int, window_s: float):
    q = _hits[(_client(request), kind)]
    now = time.monotonic()
    while q and now - q[0] > window_s:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(429, "Too many requests; wait a minute and try again.")
    q.append(now)


_lock = threading.Lock()  # one OpenCascade build at a time
_builds: OrderedDict[str, dict] = OrderedDict()  # newest 40


def _key(params: dict) -> str:
    return hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]


# ---------------------------------------------------------------- reports
def _r(x, n=1):
    return None if x is None else round(x, n)


@lru_cache(maxsize=256)
def _plan_cached(params_json: str) -> Plan:
    return plan_trebuchet(DesignParams(**json.loads(params_json)))


def _plan(p: DesignParams) -> Plan:
    try:
        return _plan_cached(json.dumps(p.to_dict(), sort_keys=True))
    except DesignError as e:
        raise HTTPException(422, str(e)) from None


def _throw(pl: Plan) -> dict:
    th = pl.throw
    lo_hi = th.expected_range()
    return {
        "ok": th.ok, "problem": th.problem,
        "range_m": _r(th.range_m, 2), "best_range_m": _r(th.best_range_m, 2),
        "expected_m": [round(lo_hi[0], 1), round(lo_hi[1], 1)] if lo_hi else None,
        "real_world": list(REAL_WORLD),
        "release_angle_deg": th.release_angle_deg, "best_release_angle_deg": th.best_release_angle_deg,
        "auto_release": pl.params.release_angle is None,
        "release_speed_ms": _r(th.release_speed, 2), "launch_angle_deg": _r(th.launch_angle_deg),
        "release_height_m": _r(th.release_height_m, 3), "flight_time_s": _r(th.flight_time, 2),
        "peak_height_m": _r(th.peak_height_m, 2), "release_t": _r(th.release_t, 3), "liftoff_t": _r(th.liftoff_t, 3),
        "sling_pull_n": _r(th.max_sling_pull_n, 1), "energy_j": _r(th.energy_j, 3),
        "efficiency": _r(th.efficiency, 3), "range_efficiency": _r(th.range_efficiency, 3),
        "sweep": th.sweep, "path": th.path,
    }


def _summary(pl: Plan) -> dict:
    p, d = pl.params, pl.derived
    d_p, m_p = projectile_of(p)
    return {
        "axle_height_mm": round(d.H), "base_length_mm": round(d.x_front - d.x_back),
        "width_mm": round(d.gap + 2 * p.frame_thickness),
        "height_mm": round(max(d.H + 15.5, d.H + d.L2 * math.sin(d.alpha) + 7)),
        "long_arm_mm": round(d.L1), "short_arm_mm": round(d.L2), "sling_mm": round(d.Ls),
        "start_angle_deg": round(math.degrees(d.alpha)), "hinge_to_weight_mm": round(d.Lc),
        "counterweight_g": round(d.m_cw), "fill_g": round(p.cw_mass), "fill": FILLS[p.cw_fill]["label"],
        "bucket_mm": [round(d.bucket["D"]), round(d.bucket["W"]), round(d.bucket["H"])],
        "arm_g": round(d.arm["mass"], 1), "projectile": PROJECTILES[p.projectile]["label"],
        "projectile_g": round(m_p, 1), "projectile_mm": round(d_p, 1),
        "mass_ratio": round(d.m_cw / m_p), "pin_angle_deg": round(pl.pin_angle),
        "bolts": d.bolts,
    }


def _anim(pl: Plan) -> dict:
    """What the page needs to play the throw on the 3D model (mm, rad)."""
    m, d = pl.machine, pl.derived
    return {"H": d.H, "L1": d.L1, "L2": d.L2, "Lc": d.Lc, "Ls": d.Ls, "r_p": d.r_p,
            "theta0": math.pi + d.alpha, "psi0": -math.pi / 2, "frames": pl.throw.frames, "path": pl.throw.path}


ADVICE_TRIES = [
    ("cw_mass", 1.5, "Use {v:.0f} g of counterweight (half as much again)"),
    ("cw_mass", 2.0, "Double the counterweight to {v:.0f} g"),
    ("sling_ratio", None, "Make the sling {v:.2f} × the long arm ({mm:.0f} mm)"),
    ("arm_ratio", None, "Change the arm ratio to {v:.1f} : 1"),
    ("start_angle", None, "Start the arm {v:.0f}° below level"),
]


def _advice(pl: Plan) -> list[dict]:
    """Changes that throw farther, best first, each with the model's
    distance. Only changes that still build."""
    p = pl.params
    base = pl.throw.range_m if pl.throw.ok else 0.0
    out = []
    if p.release_angle is not None and pl.throw.best_release_angle_deg is not None:
        gain = (pl.throw.best_range_m or 0) - base
        if gain > 0.05:
            out.append({"change": f"Bend the release pin to {pl.throw.best_release_angle_deg:.0f}°",
                        "field": "release_angle", "value": pl.throw.best_release_angle_deg,
                        "range_m": round(pl.throw.best_range_m, 2)})
    candidates = {
        "sling_ratio": [0.6, 0.7, 0.9, 1.0, 1.1],
        "arm_ratio": [3.0, 3.5, 4.5, 5.0],
        "start_angle": [35.0, 40.0, 50.0, 55.0],
    }
    for field, factor, text in ADVICE_TRIES:
        values = [getattr(p, field) * factor] if factor else candidates[field]
        best = None
        for v in values:
            if abs(v - getattr(p, field)) < 1e-6:
                continue
            try:
                q = DesignParams(**{**p.to_dict(), field: v})
                alt = _plan(q)
            except HTTPException:
                continue
            if alt.throw.ok and (best is None or alt.throw.range_m > best[1]):
                best = (v, alt.throw.range_m, alt)
        if best and best[1] > base * 1.04:
            v, r, alt = best
            mm = alt.derived.Ls
            out.append({"change": text.format(v=v, mm=mm), "field": field, "value": round(v, 3), "range_m": round(r, 2)})
    seen, uniq = set(), []
    for a in sorted(out, key=lambda a: -a["range_m"]):
        if a["field"] not in seen:
            seen.add(a["field"])
            uniq.append(a)
    return uniq[:4]


def _report(pl: Plan) -> dict:
    p, d = pl.params, pl.derived
    return {
        "summary": _summary(pl), "throw": _throw(pl), "notes": list(pl.notes),
        "bom": bill_of_materials(p, d, pl.pin_angle), "steps": assembly_steps(p, d, pl.pin_angle),
        "safety": SAFETY, "anim": _anim(pl),
    }


# ---------------------------------------------------------------- endpoints
@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def index():
    return (HERE / "static" / "index.html").read_text()


@app.get("/throw", response_class=HTMLResponse)
def throw_page():
    """Test throw: the arm swing and the arc, from /api/plan. Takes any design
    field in the query string (/throw?cw_mass=500&arm_length=250)."""
    return (HERE / "static" / "throw.html").read_text()


@app.get("/terms", response_class=HTMLResponse)
def terms_page():
    body = terms.LICENSE_TEXT.replace("&", "&amp;").replace("<", "&lt;")
    return (f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>Terms · Trebuchet Builder</title><body style='font:15px/1.5 system-ui;max-width:760px;"
            f"margin:24px auto;padding:0 16px'><pre style='white-space:pre-wrap;font:inherit'>{body}</pre>"
            f"<p><a href='/'>Back to Trebuchet Builder</a></p>")


@app.get("/api/options")
def options():
    return {
        "fills": {k: v["label"] for k, v in FILLS.items()},
        "fill_density": {k: v["density"] for k, v in FILLS.items()},
        "projectiles": {k: {"label": v["label"], "diameter": v["diameter"], "mass": v["mass"]}
                        for k, v in PROJECTILES.items()},
        "axles": {k: v["label"] for k, v in AXLES.items()},
        "defaults": BuildRequest().model_dump(),
        "real_world": list(REAL_WORLD),
        "license": terms.SHORT,
    }


@app.post("/api/plan")
def plan_endpoint(req: BuildRequest, request: Request):
    _rate_limit(request, "plan", 240, 600)
    pl = _plan(req.design())
    return _report(pl)


@app.post("/api/build")
def build_endpoint(req: BuildRequest, request: Request):
    params = req.model_dump()
    key = _key(params)
    if key in _builds:
        _builds.move_to_end(key)
        b = _builds[key]
        return {"id": key, **b["report"]}
    _rate_limit(request, "build", 30, 600)
    pl = _plan(req.design())
    if not _lock.acquire(timeout=60):
        raise HTTPException(503, "The builder is busy; try again in a moment.")
    try:
        t0 = time.monotonic()
        treb = build_trebuchet(pl.params, pl)
        preview = glb(treb)
    except DesignError as e:
        raise HTTPException(422, str(e)) from None
    except Exception:
        log.exception("build failed: %s", params)
        raise HTTPException(500, "Something went wrong building those parts; try other settings.") from None
    finally:
        _lock.release()
    rho = eff_density(pl.params.infill) / 1000
    parts = []
    for part in treb.parts:
        bb = part.local.bounding_box()
        parts.append({
            "name": part.name, "qty": part.qty, "role": part.role, "hardware": part.hardware,
            "color": list(part.color), "purpose": part.purpose, "print": PRINT_NOTES.get(part.name, ""),
            "mass_g": None if part.hardware else round(part.local.volume * rho, 1),
            "size_mm": [round(bb.size.X), round(bb.size.Y), round(bb.size.Z)],
        })
    printed = [x for x in parts if not x["hardware"]]
    report = {**_report(pl), "parts": parts, "bed_problems": treb.bed_problems,
              "plastic_g": round(sum(x["mass_g"] * x["qty"] for x in printed)),
              "build_s": round(time.monotonic() - t0, 1), "advice": _advice(pl)}
    _builds[key] = {"treb": treb, "glb": preview, "report": report, "params": params, "stls": None}
    while len(_builds) > 40:
        _builds.popitem(last=False)
    return {"id": key, **report}


def _get(build_id: str) -> dict:
    b = _builds.get(build_id)
    if not b:
        raise HTTPException(404, "Build not found; press Build again.")
    return b


@app.get("/api/builds/{build_id}/preview.glb")
def preview(build_id: str):
    return Response(_get(build_id)["glb"], media_type="model/gltf-binary")


def _notes(b: dict) -> str:
    r, s, t = b["report"], b["report"]["summary"], b["report"]["throw"]
    L = ["Trebuchet Builder build notes", "", terms.SHORT, "(See LICENSE.txt in this ZIP.)", "",
         f"Size: {s['base_length_mm']} × {s['width_mm']} mm base, axle {s['axle_height_mm']} mm up.",
         f"Arm: {s['long_arm_mm']} mm long side, {s['short_arm_mm']} mm short side; sling {s['sling_mm']} mm.",
         f"Counterweight: {s['fill_g']} g of {s['fill'].lower()} ({s['counterweight_g']} g with the bucket).",
         f"Projectile: {s['projectile']}, {s['projectile_g']} g.", ""]
    if t["ok"]:
        L += [f"Estimated throw: {t['expected_m'][0]}-{t['expected_m'][1]} m on the table "
              f"(the model, without friction, says {t['range_m']} m).",
              f"Release: pin bent to {s['pin_angle_deg']}°, about {t['release_speed_ms']} m/s at {t['launch_angle_deg']}° up; "
              f"peak height {t['peak_height_m']} m, {t['flight_time_s']} s in the air.",
              f"Efficiency: {round(100 * t['efficiency'])}% of the counterweight's drop ends up in the projectile."]
    else:
        L += [f"Throw: {t['problem']}"]
    L += [f"Note: {n}" for n in r["notes"]]
    L += ["", "Parts to print (STLs are in print orientation, on z = 0):"]
    L += [f"  {p['name']} × {p['qty']}: {p['mass_g']} g each. {p['print']}" for p in r["parts"] if not p["hardware"]]
    L += [f"  Plastic: about {r['plastic_g']} g.", "", "What else you need:"]
    L += [f"  {i['qty']} × {i['name']}: {i['spec']}" for i in r["bom"]]
    L += ["", "Assembly:"]
    L += [f"  {n}. {step}" for n, step in enumerate(r["steps"], 1)]
    L += ["", "Safety:"] + [f"  - {x}" for x in r["safety"]]
    return "\n".join(L) + "\n"


@app.get("/api/builds/{build_id}/trebuchet.zip")
def download(build_id: str):
    b = _get(build_id)
    if b["report"]["bed_problems"]:
        raise HTTPException(409, "Some parts don't fit your printer; see the report.")
    if b["stls"] is None:
        with _lock:
            b["stls"] = {p.name: terms.stl_with_header(stl_bytes(p.local)) for p in b["treb"].printed}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in b["stls"].items():
            qty = next(p.qty for p in b["treb"].printed if p.name == name)
            z.writestr(f"{name}{f'_x{qty}' if qty > 1 else ''}.stl", data)
        z.writestr("build_notes.txt", _notes(b))
        z.writestr("LICENSE.txt", terms.LICENSE_TEXT)
        z.writestr("design.json", json.dumps({"generatorVersion": GENERATOR_VERSION, "schemaVersion": SCHEMA_VERSION,
                                              "license": terms.SHORT, "params": b["params"]}, indent=2))
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="trebuchet.zip"'})


@app.exception_handler(DesignError)
def design_error(_: Request, e: DesignError):
    return JSONResponse({"detail": str(e)}, status_code=422)
