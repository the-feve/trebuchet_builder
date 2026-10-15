# trebuchet_builder — working rules

- Read `HANDOFF.md` first (state, next steps, decisions), then `TODO.md` (the roadmap). Keep both up to date.
- Sister project: the-feve/rocket-builder-web. Match its look (palette, layout, Beginner/Advanced, report cards) and reuse its server patterns (terms, rate limits, orders, supplies) rather than reinventing them.
- Units are mm and grams in `trebgen/params.py` and the parts; `physics.py` is SI.
- A design that can't work raises `DesignError` with a user-facing message saying what to change.
- Check geometry by rendering (`trebgen.export.render_png`) as well as `is_valid`: the first bucket placement was valid but collided with the axle.
- Run `python -m pytest -q` in `geometry/` and `server/` before every push.
- The owner's budget is tight: zero running costs where possible, batch changes.
