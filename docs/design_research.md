# Kit redesign: research and decisions (2026-10-18)

The owner's brief: the first kit "isn't very well put together from a design-feature perspective. There's no clear way to build the sling, the parts are just sort of intersecting, and it's not a buildable prototype. It should be buildable on a single plate, and snap together with minimal hardware. Optional material to use a string if needed for the sling. Parts should be easy to print and not overly small, but simple in design."

This page records what other printed trebuchets do, the rules of thumb and fit numbers we used, and what changed. Numbers marked *(est)* are ours; the others come from the source.

## What was wrong with the first kit

Measured on the default design (arm 200 mm, 350 g of BBs):

- **Plate area:** the parts' bounding boxes added up to about 2.2 full 220 mm plates. The two A-frames alone (214 × 190 mm each) can't share a plate.
- **Hardware:** an M8 bolt, two 608 bearings, an M4 bolt, ten M3 self-tapping screws, a nail or paper clip, a split ring and a leather pouch.
- **Collisions:** the arm cut into the bucket's hanger plates at rest (52 mm³). Nothing in the tests checked assembled parts against each other.
- **Sling:** the kit had no parts for it. The page said "leather pouch, string, ring" and nothing more.
- **Release:** a nail bent with a printed gauge, which is hard to repeat.

## Other printed trebuchets

The model sites (Thingiverse, Printables, MakerWorld) answered 403 to our fetches, so the figures below come from search excerpts of those pages.

| Design | Plates | Joinery and hardware | Sling and release | What we took from it |
|---|---|---|---|---|
| [Kit Crafters handheld kit](https://makerworld.com/en/models/81784) | 1 (A1 mini, 180 mm) | Snap-fit, no glue, no supports, no hardware | No sling; a compliant latch holds the arm | One plate and snap-fit are both achievable |
| [OwenTF tabletop toy](https://makerworld.com/en/models/756525) | 4 | Printed throughout; coins under 28 mm for the counterweight (40 quarters ≈ 224 g) | A ratcheting hook at the arm tip tunes the range | Coins as the counterweight; a tunable release hook |
| [Novera print-in-place](https://makerworld.com/en/models/794638) | 1 (6.9 h) | Print-in-place hinges, no hardware; pennies | — | Single plate, coins |
| [COMRADE_ZACH whipper](https://makerworld.com/en/models/1293616) | — | Printed; nickels | A printed latch instead of a string sling ("string slings … can be frustrating") | A fully printed sling is possible but awkward |
| [Doom Trebuchet](https://www.thingiverse.com/thing:3424509) | Several | M8 axle, M5 rod and fender washers for the counterweight | A metal ring on the sling slips off the arm pin. "Folded sling ≈ arm length." Tune by bending the pin | The ring idea; our sling ratio |
| [F2K floating arm](https://www.thingiverse.com/thing:2764236) | Several (305 mm long) | Some hardware | String sling | Floating-arm machines throw farthest but need a track and wheels (a later variant) |
| [Isaac Curley](https://www.myminifactory.com/object/3d-print-fully-working-trebuchet-54214) | — | PLA, no supports | Craft string and a gauze pouch; 450 g throws an eraser about 1.7 m | Without tuning, the range is short |
| [Printed TPU sling](https://www.printables.com/model/404146-trebuchet-sling) | — | — | A flat-printed flexible pouch with tie tabs, string lines | A printed pouch plus string works |

[TeachEngineering uot-1536](https://www.teachengineering.org/activities/uot-1536-trebuchet-design-build-engineering-challenge), the owner's example, is a grade-8 design challenge rather than a reference design:

- PVC pipe, 3.78 L buckets, mason twine and a tennis ball;
- base at most 1 × 1 m, height at most 1.2 m;
- it must pack into a 38 × 30 × 25 cm box and cost no more than $45;
- students simulate first (virtualtrebuchet.com), then build, film and fit the flight.

What carries over is the process: "simulate, build, test, improve" (the designer plus the `/throw` page). It also confirms that a kit of parts which packs small is the right shape for a classroom.

## Rules of thumb used

- **Arm ratio** (long : short, from the pivot): 3.75–5 : 1. We kept a default of 4 : 1.
- **Counterweight : projectile:** about 100 : 1, with 80–130 useful. The default is 112 : 1 (300 g of coins against a 3 g printed ball).
- **Sling:** 0.75–1.0 × the long arm. The default is 0.8.
- **Release:** 20–45° off the arm. A ring slides off a prong.
  - Shot goes high or backwards: it let go too early, so use a smaller angle.
  - Shot hits the ground: it let go too late, so use a bigger angle.
- **Cocked angle:** the long arm about 45° below level.

## FDM fits used (PLA, 0.4 mm nozzle, per side)

| Fit | Value | In the code |
|---|---|---|
| Pin turning in a printed hole | 0.25 mm + `clearance` (0.1 default) | `RUN_CLEAR` |
| Tenon in a slot | 0.2 mm + `clearance` | `SLOT_CLEAR` |
| Cantilever snaps | Root strain ε ≈ 1.5·h·y / L², kept under 1.5% (PLA tolerates about 2–3%). Snaps flex in the print plane (layers along the prong) | `TENON_BARB`, `PIN_BARB`, `PIN_SPLIT_LEN` |
| Printed pins | Ø10 axle and Ø8 hinge, printed **lying down** with a 0.8 mm flat, so the layers run along the pin. 100% infill | `snap_pin` |
| Walls | 2.4 mm or more; pins and snap prongs 3 mm or more | |

The *Clearance* field in Advanced adds to every fit, for printers that run tight.

## The new kit (default: 180 mm arm, 300 g of coins)

- **One 220 × 220 mm plate.** The download has `plate_1.3mf`, with one named object per part. A footprint packer (`trebgen/layout.py`) places the parts, so small parts sit inside the frames' open spaces.
- **No hardware.** You need about 2.3 m of string and the coins. An M8 bolt, and optionally 608 bearings, are offered for a smoother axle.

| Part | Why it is shaped this way |
|---|---|
| **Frame ×2 (the same part)** | An upside-down T: a rail on the table, a tower to the axle, two low braces. Two copies nest head to toe on the plate; the old A-frames could not. Every feature goes through the plate, so no mirrored pair is needed. Notches under the rail measure the two sling cords. |
| **Cross member ×2** | 8 × 6 mm bars whose split "arrow" tenons click through slots in both rails: a 0.6 mm catch, about 0.8% strain to push in. Two pegs on top locate the deck. |
| **Trough (deck)** | A plain 75 × 32 mm strip. It covers only where the ball slides before the sling lifts it (about 25 mm in the simulation). Channels underneath drop it over the members, so it sits low. |
| **Arm** | Flat, 10 mm thick. Axle and hinge holes, a trigger hole 22 mm from the axle, and a cord hole at the tip. The **release hook** is printed into the tip at the design's best release angle; to change the angle you reprint the arm. |
| **Axle pin, hinge pin** | Head, plain shank and a split barbed end that clicks out behind the far face: 0.85 mm catch, about 1% strain. Spacers on the axle and sleeves on the hinge centre the arm. |
| **Bucket + cap** | One compartment, with ears on the outside walls (the arm hangs between them on sleeves). A 45° roof inside the top needs no support. Coins up to a quarter go in through a 27 mm hole closed by a slotted push-in cap. The old sliding-lid idea needed about 3000 mm² of plate the kit couldn't spare. |
| **Trigger pin** | Through a lobe on the frame beside the axle, into the arm. It holds about 5 N; tie the 1 m cord to its ring and pull. Putting the trigger by the axle instead of at the tip removed a lug that stopped the frames nesting. |
| **Sling** | A printed pouch: the ball sits in its centre hole, and slits let it fold. The printed release ring slips off the hook. Tip cord and ring cord are tied to length at the rail notches. |

## How it is checked (tests in `geometry/tests`)

- Every part is one valid solid that tessellates and lies flat on the bed.
- The default kit fits one 220 mm plate, and no two parts on the plate touch.
- No two assembled parts intersect, across seven variants. This test was missing before, and it is how the old arm-through-bucket collision got through.
- The bucket clears the deck at every frame of the simulated swing, because it tilts at the bottom. If it doesn't, the axle goes up.
- Snap catches are big enough to hold, and strains stay under 1.5%.
- Pins clear their holes; the release hook points the right way; the cord notches match the cord lengths.
- The 3MF has one named object per part.

## Open questions for the owner

1. **A test print.** The fits are the research numbers, not yet printed. Print the default plate and tell us:
   - do the arrow tenons and pin snaps go in and hold?
   - does the 0.05 mm press fit of the cap hold?
   - is the PLA pouch flexible enough?
2. **Release tuning.** Changing the angle means reprinting the arm (about 25 g). Options:
   - a swappable tip, or
   - three printed hooks at 30°, 40° and 50° in the kit (+1 small part each).
3. **Bigger beds.** Several non-default designs need 2 plates on 220 mm: 200 mm arm, 400 g counterweight, ping-pong balls, 608 bearings. The report says so. Should the default track the bed size? (256 mm beds fit a 180 mm arm easily.)
4. **Fully printed sling (no string).** No proven printed chain sling exists. A whipper-style printed latch is the alternative. Worth a variant?
