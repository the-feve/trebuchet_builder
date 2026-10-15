# Handoff

_Last updated 2026-10-15 (second session: the page, tests, hosting in the Rocket Builder Fly app). Read this, then `TODO.md`._

## Where things stand

Trebuchet Builder: a web page where someone designs a small 3D-printable desk trebuchet, sees how far it should throw, and downloads STLs plus a hardware list. Built to match Rocket Builder (the-feve/rocket-builder-web).

**Done and working (checked by running it, no tests written yet):**
- `geometry/trebgen/params.py`: design inputs (`DesignParams`) and `derive()`: arm split, sling, counterweight bucket sized from fill mass and bulk density, frame gap, axle height, start angle (default 45°), base extent, bolt lengths. Raises `DesignError` with advice for designs that can't work.
- `geometry/trebgen/physics.py`: hinged-counterweight trebuchet with a sling, three angles (arm, hanger, sling), Lagrange equations from point positions, RK4. Phase 1 the projectile slides on the trough (constraint + normal force), phase 2 swings free, release when the sling-to-arm angle reaches the pin angle, then flight with sphere drag (vectorised over every candidate release, so the best release angle comes for free). No friction: `REAL_WORLD = (0.6, 0.85)` scales the model's distance into the "expect" range. Default design: model 9.4 m, expect 5.6-8.0 m, 64% efficiency, best release about 43°. About 0.25 s per throw.
- `geometry/trebgen/parts.py` (build123d): Frame_Right/Left (A-frames, 608 bearing pocket or plain hole), Cross_Member ×3, Trough (with trigger post), Arm (axle, hinge, sling cord hole, axial 2 mm release-pin hole), Bucket (hanger plates, tall ears so it hangs clear of the axle), Bucket_Lid ×2, Axle_Spacer ×2, Trigger_Pin, Pin_Gauge (bend the release pin to the angle), Ball (printed projectile); preview-only bolts and bearings. All valid single solids; the default builds in about 1 s and fits a 220 mm bed. Renders: `geometry/report/default_iso.png`, `default_side.png`.
- `build.py` (plan + build + bed-fit check), `hardware.py` (bill of materials, each item with a `key` for affiliate links later), `instructions.py` (print notes, assembly steps, safety), `export.py` (STL, GLB, PNG render).
- `server/app.py` (FastAPI): `/api/options`, `/api/plan` (estimate only), `/api/build` (geometry + report + "throw farther" advice), `/api/builds/{id}/preview.glb`, `/api/builds/{id}/trebuchet.zip` (STLs with license header, build_notes.txt, LICENSE.txt, design.json), `/terms`. `/api/plan` smoke-tested (200). `/api/build` and the ZIP are **not exercised yet**.
- `server/terms.py`: Rocket Builder's personal-use license, reworded for trebuchets. three.js r160 vendored in `server/static/vendor/`.

- `server/static/index.html` (2026-10-15, second session): the page, in Rocket Builder's look. Beginner/Advanced; six numbered steps (arm size, printer bed, counterweight + fill, projectile picture buttons, sling length, build); live estimate under Build from `/api/plan` as you type (no geometry); 3D preview with an animated throw (▶ Throw, slow motion; arm turns about the axle, bucket hangs from the hinge, sling drawn as a line, the ball follows its flight path with a dashed trail); guide with a diagram, how-to, what makes it throw farther, key terms, about the estimate, safety. Report cards: Test throw (expected range, flight-path chart, release speed, angle, peak, efficiency, sling pull), Release angle (distance-vs-angle chart), Your trebuchet, How to throw farther (each with *Try it*), Parts to print, What else you need, Putting it together, Safety. Checked in headless Chromium: no console errors, build and animation work. **All URLs are relative** so it runs at `/` and under `/trebuchet/`.
- **Test-throw page (2026-10-15, owner's request):** `throw` (`server/static/throw.html`, at `/throw` and `/trebuchet/throw`, standalone, styled like Rocket Builder). Side view at one scale: the machine at the axle, the dashed full arc and a live trail, release and peak labels, landing marker, the 60–85% "expect" band on a metre ruler; a close-up inset shows the arm, hanger, counterweight and sling swinging (frames from `anim`, played 5× slow, after a 0.6 s pause), then the flight in real time. Controls: counterweight, arm length, projectile, best/fixed release angle; it calls `api/plan` (relative URLs, like the designer) and keeps the design in the query string; the designer's Test throw card links `throw?<fields>` with the current design (*See the arc*). Stat tiles and "Room you need" (a lane of 1.2 × the model's distance, ceiling = peak + 0.75 m table). Tests: `server/tests/test_throw_page.py` (page served; arc starts where the last frame puts the ball, ends at the range, peaks at the peak height; more counterweight throws farther).
- `server/terms.py` is now `server/treb_terms.py`: the Rocket Builder app imports this server, and its own `terms` module would clash.
- Tests: `geometry/tests` (13: energy conserved through the swing, sensible default throw, release angle and counterweight effects, DesignErrors, valid parts on the bed, bucket clear of the axle, bed check, BOM keys) and `server/tests` (5: options/page, plan, 422, build + GLB + ZIP, 404). CI in `.github/workflows/ci.yml`.

**Hosting (owner chose 2026-10-15):** inside Rocket Builder's Fly app `rocket-fevergeon`, at `/trebuchet/` and (once DNS is set) `trebuchet.quiverdesignworks.net`. rocket-builder-web's `server/trebuchet_mount.py` loads this repo from a checkout made at deploy time (its `deploy.yml` checks out **this repo's `main`**). `.github/workflows/deploy.yml` here asks rocket-builder-web to redeploy after a push to `main` (needs `ROCKET_DEPLOY_TOKEN`; skips with a notice without it). Owner steps are in rocket-builder-web `HANDOFF.md`, Next steps 8: make a `main` branch here, add the read token there, merge its PR, DNS.

Rules that follow from sharing the app: keep page URLs relative; don't add server modules whose names clash with rocket-builder-web's `server/` (`app` is loaded under another name; `terms`, `designs`, `accounts`, `orders`, `shop`, `supplies`, `notify` are taken); one 1 GB machine runs both, so keep builds light.

## Next steps (in order)

1. Owner: the hosting steps above. Then open https://rocket.quiverdesignworks.net/trebuchet/ and try it on a phone.
2. Print the default design and throw it: note distance, what broke or rubbed, and set `physics.REAL_WORLD` from it (record in `docs/`).
3. Supplies page with Amazon links (TODO step 2); the report's "What else you need" says links are coming.
4. Saved designs / share links, then orders (reuse Rocket Builder's code; mind the module-name rule above).

## Decisions log

- 2026-10-15: Separate repo `the-feve/trebuchet_builder` (owner created it; the Claude app can't create repos). Same stack as Rocket Builder: Python + build123d + FastAPI + vendored three.js.
- 2026-10-15: First machine is a hinged-counterweight trebuchet (hinged throws farther than fixed and is easy to print). Fixed and floating-arm (FAT) variants are later steps.
- 2026-10-15: Hardware chosen for cheapness and availability: M8 axle bolt + 608 skate bearings (option: plain hole), M4 hinge bolt, M3 self-tapping screws, 2 mm nail or paper clip as release pin, fishing line/kite string sling, leather/felt pouch, split ring.
- 2026-10-15: The arm starts at a set angle (45°) with the sling dropping to the trough, and the bucket hangs on tall hanger plates when it would otherwise hit the axle. The first version (arm tip down at the trough) put the bucket through the axle spacers.
- 2026-10-15: Hosted inside Rocket Builder's Fly app (no second app), not a separate one.
- 2026-10-15: Distances are from the axle, on level ground at table height. The model has no friction; the page shows 60-85% of it as "expect" until real test throws calibrate it.

## How to run locally

```
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
cd server && pip install -r requirements.txt
uvicorn app:app --reload        # http://127.0.0.1:8000
```
