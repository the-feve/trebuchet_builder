# Roadmap

Steps for building Trebuchet Builder up from a small printable kit. Tick them off and keep `HANDOFF.md` in step.

## Step 1: Small printable trebuchet (in progress: only the test print left)
- [x] Throw physics: hinged counterweight, sling, release angle, flight with drag, efficiency, best release angle
- [x] Printable parts + hardware list + assembly steps + license
- [x] API: options, plan, build, preview GLB, ZIP
- [x] Page (`server/static/index.html`) matching Rocket Builder: Beginner/Advanced, live distance, 3D preview, report cards, guide/glossary
- [x] Throw animation on the 3D model; flight path and release-angle charts
- [x] Tests, CI (the Docker image is Rocket Builder's)
- [x] Test-throw page `/throw`: arm swing (slow motion, close-up inset) and the flight arc, expected-range band, room needed (2026-10-15), linked from the designer's report
- [ ] Wind (head/tail) on the test throw, like Rocket Builder's launch simulator
- [ ] Print and throw the default design; compare with the estimate and set `physics.REAL_WORLD` from it (record in `docs/`)

## Step 2: Make it a product
- [x] Hosting: inside the Rocket Builder Fly app (code done 2026-10-15)
- [ ] Owner: `main` branch here, `TREBUCHET_REPO_TOKEN` in rocket-builder-web, merge its PR, `trebuchet.quiverdesignworks.net` DNS + cert (rocket-builder-web HANDOFF Next steps 8)
- [ ] Order Supplies page with Amazon affiliate links (Store ID `quiverdesig09-20`): copy rocket-builder-web `server/supplies.py` + `gear.json`; match items on `bom[].key` (m8_bolt, 608_bearing, m4_bolt, m3_screw, release_pin, sling_cord, pouch, ring, trigger_cord, fill_*, proj_*, safety_glasses). Disclosure line required.
- [ ] Saved designs, share links, accounts (reuse rocket-builder-web `designs.py`, `accounts.py`)
- [ ] Printed-kit orders through Stripe (reuse rocket-builder-web `orders.py`, `shop.py`; `metadata.store` tag for this store)
- [ ] Link from quiverdesignworks.net apps list

## Step 3: Bigger and different machines
- [ ] Split parts that don't fit the bed (lap joints in the frame rails, two-piece arm)
- [ ] Fixed counterweight and floating-arm (FAT) variants, with a comparison in the report
- [ ] Wheels (a rolling base throws farther)
- [ ] Arm follow-through check / arm stop so the arm can't hit the table
- [ ] Friction model (axle, trough) calibrated from test throws
- [ ] Larger sizes: wood + printed joints, plywood cut lists
