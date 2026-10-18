# Handoff

_Last updated 2026-10-18 (kit redesign: one plate, snap-fit, no hardware; branch `claude/trusting-babbage-seog9z`). Read this, then `TODO.md`._

## Where things stand

- **Kit redesign (2026-10-18, owner's request, branch `claude/trusting-babbage-seog9z`, not merged yet):** the first kit didn't fit one plate (about 2.2 plates), needed an M8 bolt, 608 bearings, an M4 bolt and ten M3 screws, had no sling parts, and the arm went through the bucket. Research, fit numbers and every decision are in `docs/design_research.md`. Now:
  - **Fits and hardware:** the default (180 mm arm, 300 g coins) prints on **one 220 mm plate** (`plate_1.3mf` in the ZIP) and **snaps together with no hardware**: only string and coins.
  - **Parts:** two identical T-frames, two snap cross members, a deck on their pegs, the arm with a printed release hook at the best release angle, printed snap pins (axle Ø10, hinge Ø8) with spacers and sleeves, a roofed bucket with a push-in cap, a trigger pin beside the axle, a sling pouch and release ring, and the ball. The cord notches are under a frame rail.
  - **Optional hardware:** M8 bolt or M8 + 608 bearings (`axle` option).
  - **New code and fields:** `trebgen/layout.py` (raster + FFT nesting packer; ~1 s), `Trebuchet.plates`, `export.plate_3mf`/`render_plate_png`, `clearance` field (Advanced), report `plates`.
  - **Tests:** 30 geometry tests (incl. no assembled parts intersecting across 7 variants, the bucket clearing the deck through the simulated swing, snap catch and strain, one plate, plate parts apart). 13 server tests.
  - **Page:** guide text updated; the `sling` role is hidden in the 3D view (the line is the sling).
  - **Still to do:** the owner's test print of the snaps; see the open questions in the docs page. The other session was moving the page/hosting at the same time: merge after that lands (conflicts, if any, are in `server/static/index.html` guide text).

Trebuchet Builder: a web page where someone designs a small 3D-printable desk trebuchet, sees how far it should throw, and downloads STLs plus a hardware list. Built to match Rocket Builder (the-feve/rocket-builder-web).

**Done and working (checked by running it, no tests written yet):**
- `geometry/trebgen/params.py`: design inputs (`DesignParams`) and `derive()`: arm split, sling, counterweight bucket sized from fill mass and bulk density, frame gap, axle height, start angle (default 45°), base extent, bolt lengths. Raises `DesignError` with advice for designs that can't work.
- `geometry/trebgen/physics.py`: hinged-counterweight trebuchet with a sling, three angles (arm, hanger, sling), Lagrange equations from point positions, RK4. Phase 1 the projectile slides on the trough (constraint + normal force), phase 2 swings free, release when the sling-to-arm angle reaches the pin angle, then flight with sphere drag (vectorised over every candidate release, so the best release angle comes for free). No friction: `REAL_WORLD = (0.6, 0.85)` scales the model's distance into the "expect" range. Default design: model 9.4 m, expect 5.6-8.0 m, 64% efficiency, best release about 43°. About 0.25 s per throw.
- `geometry/trebgen/parts.py` (build123d): Frame_Right/Left (A-frames, 608 bearing pocket or plain hole), Cross_Member ×3, Trough (with trigger post), Arm (axle, hinge, sling cord hole, axial 2 mm release-pin hole), Bucket (hanger plates, tall ears so it hangs clear of the axle), Bucket_Lid ×2, Axle_Spacer ×2, Trigger_Pin, Pin_Gauge (bend the release pin to the angle), Ball (printed projectile); preview-only bolts and bearings. All valid single solids; the default builds in about 1 s and fits a 220 mm bed. Renders: `geometry/report/default_iso.png`, `default_side.png`.
- `build.py` (plan + build + bed-fit check), `hardware.py` (bill of materials, each item with a `key` for affiliate links later), `instructions.py` (print notes, assembly steps, safety), `export.py` (STL, GLB, PNG render).
- `server/app.py` (FastAPI): `/api/options`, `/api/plan` (estimate only), `/api/build` (geometry + report + "throw farther" advice), `/api/builds/{id}/preview.glb`, `/api/builds/{id}/trebuchet.zip` (STLs with license header, build_notes.txt, LICENSE.txt, design.json), `/terms`. `/api/plan` smoke-tested (200). `/api/build` and the ZIP are **not exercised yet**.
- `server/terms.py`: Rocket Builder's personal-use license, reworded for trebuchets. three.js r160 vendored in `server/static/vendor/`.

- **Test-throw page (other session) (2026-10-15, owner's request):** `/throw` (`server/static/throw.html`, standalone, styled like Rocket Builder). Side view at one scale: the machine at the axle, the dashed full arc and a live trail, release and peak labels, landing marker, the 60–85% "expect" band on a metre ruler; a close-up inset shows the arm, hanger, counterweight and sling swinging (frames from `anim`, played 5× slow, after a 0.6 s pause), then the flight in real time. Controls: counterweight, arm length, projectile, best/fixed release angle; it calls `/api/plan` and keeps the design in the query string, and the designer's Test throw card links to it (`throw?<fields>`, relative). Stat tiles and "Room you need" (a lane of 1.2 × the model's distance, ceiling = peak + 0.75 m table). Tests: `server/tests/test_throw_page.py` (page served; arc starts where the last frame puts the ball, ends at the range, peaks at the peak height; more counterweight throws farther).
- `server/static/index.html` (2026-10-15, second session): the page, in Rocket Builder's look. Beginner/Advanced; six numbered steps (arm size, printer bed, counterweight + fill, projectile picture buttons, sling length, build); live estimate under Build from `/api/plan` as you type (no geometry); 3D preview with an animated throw (▶ Throw, slow motion; arm turns about the axle, bucket hangs from the hinge, sling drawn as a line, the ball follows its flight path with a dashed trail); guide with a diagram, how-to, what makes it throw farther, key terms, about the estimate, safety. Report cards: Test throw (expected range, flight-path chart, release speed, angle, peak, efficiency, sling pull), Release angle (distance-vs-angle chart), Your trebuchet, How to throw farther (each with *Try it*), Parts to print, What else you need, Putting it together, Safety. Checked in headless Chromium: no console errors, build and animation work. **All URLs are relative** so it runs at `/` and under `/trebuchet/`.
- `server/terms.py` is now `server/treb_terms.py`: the Rocket Builder app imports this server, and its own `terms` module would clash.
- Tests: `geometry/tests` (13: energy conserved through the swing, sensible default throw, release angle and counterweight effects, DesignErrors, valid parts on the bed, bucket clear of the axle, bed check, BOM keys) and `server/tests` (5: options/page, plan, 422, build + GLB + ZIP, 404). CI in `.github/workflows/ci.yml`.

- **Second pass (2026-10-15):** the page now matches Rocket Builder's layout: drag handles between the form and the 3D view and between the view and the report (sizes in `localStorage` as `treb.formWidth` / `treb.reportHeight`, since this page can share an origin with Rocket Builder; arrow keys nudge, double-click resets; hidden on phones). Header: a *Rocket Builder | Trebuchet Builder* switcher (`nav.apps`, also on Rocket Builder's header and supplies page, `/throw` and `/supplies`) and *Order Trebuchet Supplies*. The guide is a full user guide: quick start, what a trebuchet is, how it works, the parts, printing tips, throwing farther, a tuning/troubleshooting table, experiments, the estimate, key terms, safety, your files.
- **Order Trebuchet Supplies (2026-10-15):** `/supplies` (`server/treb_supplies.py` + `server/treb_gear.json`, same layout as Rocket Builder's `/ordersupplies`): a hardware-kit box and six categories, Store ID `quiverdesig09-20`, the disclosure at the top and bottom, no prices or Amazon images. **Most items are Amazon search links** (`"search"`), not specific products: no product IDs were looked up. Swap `"search"` for `"asin"` to link a product (the filament items already use the rocket list's Sunlu ASINs). Items list the shopping-list `keys` they cover; `/api/options → supply_links` feeds a *Find on Amazon* link per row of the report's *What else you need*, and the report has big *Order trebuchet supplies* / *Watch the test throw* buttons. Tests: `server/tests/test_supplies.py` (every default shopping-list item has a link; every link has the Store ID).

**Hosting: live since 2026-10-15** at https://trebuchet.quiverdesignworks.net (A/AAAA DNS-only in Cloudflare, same addresses as `rocket.`; Fly cert issued) and https://rocket.quiverdesignworks.net/trebuchet/, inside Rocket Builder's Fly app `rocket-fevergeon` (rocket-builder-web PR #31). rocket-builder-web's `server/trebuchet_mount.py` loads this repo from a checkout made at deploy time (its `deploy.yml` checks out **this repo's `main`**). `.github/workflows/deploy.yml` here asks rocket-builder-web to redeploy after a push to `main` (needs `ROCKET_DEPLOY_TOKEN`; skips with a notice without it). Owner setup done 2026-10-15: `main` here, `TREBUCHET_REPO_TOKEN` there (first saved in the wrong place: the deploy skipped the checkout and shipped the rocket app alone, so check its *Check out Trebuchet Builder* step if `/trebuchet/` 404s), `ROCKET_DEPLOY_TOKEN` here.

Rules that follow from sharing the app: keep page URLs relative; don't add server modules whose names clash with rocket-builder-web's `server/` (`app` is loaded under another name; `terms`, `designs`, `accounts`, `orders`, `shop`, `supplies`, `notify` are taken); one 1 GB machine runs both, so keep builds light.

## Next steps (in order)

0. Owner: print the default plate (`plate_1.3mf`) and report how the snaps, pins and cap fit; then tune `RUN_CLEAR`/`SLOT_CLEAR`/barbs in `params.py`/`parts.py` (or the default `clearance`). Then merge this branch (after the hosting/page-move work).

1. Owner: try it on a phone; pick specific products for the supplies list (each `"search"` item → an `"asin"`).
2. Print the default design and throw it: note distance, what broke or rubbed, and set `physics.REAL_WORLD` from it (record in `docs/`).
3. Wind on the test throw; saved designs / share links (TODO).
4. Orders (reuse Rocket Builder's code; mind the module-name rule above).

## Decisions log

- 2026-10-18: Kit redesigned for one plate and snap-fit (owner). Frames are upside-down Ts so two nest head to toe beside the arm; the trigger moved next to the axle (a lug at the back stopped the frames nesting); the deck shrank to where the ball actually slides; the bucket got a roof and a cap instead of a lid (plate area). Release hook printed into the arm at the best angle (reprint the arm to retune). Coins are the default fill (everyone has them). Fits from published FDM guidance, not yet test-printed.

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
