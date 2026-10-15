# Handoff

_Last updated 2026-10-15 (first session, paused early at the owner's request). Read this, then `TODO.md`._

## Where things stand

Trebuchet Builder: a web page where someone designs a small 3D-printable desk trebuchet, sees how far it should throw, and downloads STLs plus a hardware list. Built to match Rocket Builder (the-feve/rocket-builder-web).

**Done and working (checked by running it, no tests written yet):**
- `geometry/trebgen/params.py`: design inputs (`DesignParams`) and `derive()`: arm split, sling, counterweight bucket sized from fill mass and bulk density, frame gap, axle height, start angle (default 45°), base extent, bolt lengths. Raises `DesignError` with advice for designs that can't work.
- `geometry/trebgen/physics.py`: hinged-counterweight trebuchet with a sling, three angles (arm, hanger, sling), Lagrange equations from point positions, RK4. Phase 1 the projectile slides on the trough (constraint + normal force), phase 2 swings free, release when the sling-to-arm angle reaches the pin angle, then flight with sphere drag (vectorised over every candidate release, so the best release angle comes for free). No friction: `REAL_WORLD = (0.6, 0.85)` scales the model's distance into the "expect" range. Default design: model 9.4 m, expect 5.6-8.0 m, 64% efficiency, best release about 43°. About 0.25 s per throw.
- `geometry/trebgen/parts.py` (build123d): Frame_Right/Left (A-frames, 608 bearing pocket or plain hole), Cross_Member ×3, Trough (with trigger post), Arm (axle, hinge, sling cord hole, axial 2 mm release-pin hole), Bucket (hanger plates, tall ears so it hangs clear of the axle), Bucket_Lid ×2, Axle_Spacer ×2, Trigger_Pin, Pin_Gauge (bend the release pin to the angle), Ball (printed projectile); preview-only bolts and bearings. All valid single solids; the default builds in about 1 s and fits a 220 mm bed. Renders: `geometry/report/default_iso.png`, `default_side.png`.
- `build.py` (plan + build + bed-fit check), `hardware.py` (bill of materials, each item with a `key` for affiliate links later), `instructions.py` (print notes, assembly steps, safety), `export.py` (STL, GLB, PNG render).
- `server/app.py` (FastAPI): `/api/options`, `/api/plan` (estimate only), `/api/build` (geometry + report + "throw farther" advice), `/api/builds/{id}/preview.glb`, `/api/builds/{id}/trebuchet.zip` (STLs with license header, build_notes.txt, LICENSE.txt, design.json), `/terms`. `/api/plan` smoke-tested (200). `/api/build` and the ZIP are **not exercised yet**.
- `server/terms.py`: Rocket Builder's personal-use license, reworded for trebuchets. three.js r160 vendored in `server/static/vendor/`.

**Not done yet:** `server/static/index.html` (the page) doesn't exist yet, so `/` fails. No tests, CI, Dockerfile or hosting.

## Next steps (in order)

1. Write `server/static/index.html` by adapting rocket-builder-web's page (copy its CSS tokens, header, form/3D/report grid, splitters, theme, progress bar and viewer code). Form: Beginner steps (arm size, counterweight + fill, projectile, sling, printer bed, Build); Advanced adds arm ratio, release angle (blank = best), start angle, bucket width, arm thickness, axle type, infill. Use `/api/plan` for live distance as sliders move, `/api/build` for the model. Report cards: Test throw (expected range, speed, angle, peak, flight-path SVG from `throw.path`, distance-vs-release-angle chart from `throw.sweep`), Your trebuchet (`summary`), How to throw farther (`advice`), What to buy (`bom`), Parts to print (`parts`), Assembly steps, Safety. Animate the throw: GLB nodes are `<Part>#<n>`; parts with role `arm` turn about the axle (0, 0, H) by -(theta - theta0) about +Y, `bucket` parts hang from the hinge and turn by -(psi - psi0); `anim.frames` = [t, theta, psi, sigma]; draw the sling as a line from the tip to the ball.
2. Tests: `geometry/tests` (energy conserved during the free swing; default design builds, valid single solids, fits 220 bed; DesignError cases; release-angle monotonic sanity) and `server/tests` (plan, build, zip contents).
3. CI workflow and Dockerfile copied from rocket-builder-web (swap rocketgen for trebgen).
4. Owner decision: hosting (see TODO).

## Decisions log

- 2026-10-15: Separate repo `the-feve/trebuchet_builder` (owner created it; the Claude app can't create repos). Same stack as Rocket Builder: Python + build123d + FastAPI + vendored three.js.
- 2026-10-15: First machine is a hinged-counterweight trebuchet (hinged throws farther than fixed and is easy to print). Fixed and floating-arm (FAT) variants are later steps.
- 2026-10-15: Hardware chosen for cheapness and availability: M8 axle bolt + 608 skate bearings (option: plain hole), M4 hinge bolt, M3 self-tapping screws, 2 mm nail or paper clip as release pin, fishing line/kite string sling, leather/felt pouch, split ring.
- 2026-10-15: The arm starts at a set angle (45°) with the sling dropping to the trough, and the bucket hangs on tall hanger plates when it would otherwise hit the axle. The first version (arm tip down at the trough) put the bucket through the axle spacers.
- 2026-10-15: Distances are from the axle, on level ground at table height. The model has no friction; the page shows 60-85% of it as "expect" until real test throws calibrate it.

## How to run locally

```
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
cd server && pip install -r requirements.txt
uvicorn app:app --reload        # http://127.0.0.1:8000 (needs index.html, step 1)
```
